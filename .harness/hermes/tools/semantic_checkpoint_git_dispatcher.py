#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import unicodedata
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

GIT_WORKER_STATUSES = {"git_pending", "git_committed", "git_pushed", "git_failed", "rejected_dispatch"}
RUNTIME_RECEIPT_STATUSES = {"observed", "pass", "fail", "blocked"}
SEMANTIC_RECEIPT_KEYS = {"verdict", "C", "P", "S", "AC", "task_AC", "closure"}
MAX_RECEIPT_ERRORS = 8
SCHEMA = "harness.cps.semantic-checkpoint-git-closure.v1"
EXECUTION_INSTRUCTION = "Perform only the scoped Git closure described by this packet: remove only exact lifecycle_declaration.ephemeral_generated_paths that baseline marks absent, never directories or recursive sweeps; preserve source_mutations, persistent_evidence_paths, pre-existing, ambiguous, and unrelated paths; run verification_command if present; stage only scoped_paths; create the exact commit_message; push only repository.branch to repository.upstream; then report bounded cleanup facts."
LIFECYCLE_KEYS = {"baseline", "source_mutations", "ephemeral_generated_paths", "persistent_evidence_paths"}
MAX_LIFECYCLE_PATHS = 128
TOP_KEYS = {
    "schema", "checkpoint_id", "work_id", "graph_source", "repository",
    "scoped_paths", "excluded_dirty_paths", "prohibited_actions", "owner_approval", "execution_instruction", "commit_message",
    "verification_command", "lifecycle_declaration", "closure_AC_ref", "CPS_refs",
}
PROVIDER = "openai-codex"
MODEL = "gpt-5.3-codex-spark"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


@contextmanager
def _job_lock(job_path: Path):
    import fcntl

    lock_path = job_path.with_suffix(job_path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield
        fcntl.flock(lock, fcntl.LOCK_UN)


def build_worker_argv(packet_path: Path) -> list[str]:
    """Use the contract-pinned native Hermes executor."""
    return [
        "hermes", "chat", "--provider", PROVIDER, "-m", MODEL,
        "-t", "terminal,file", "-Q", "-q", f"@{packet_path}",
    ]


def build_executor_local_packet(
    *,
    work_id: str,
    graph_ref: str,
    local_nodes: Iterable[Any],
    local_edges: Iterable[Any],
    source_refs: Iterable[str],
    task_AC: Iterable[Any],
    evidence_requirements: Iterable[Any],
) -> dict[str, Any]:
    packet = {
        "family": "executor_local_packet",
        "work_id": work_id,
        "graph_ref": graph_ref,
        "local_nodes": list(local_nodes),
        "local_edges": list(local_edges),
        "source_refs": list(source_refs),
        "task_AC": list(task_AC),
        "evidence_requirements": list(evidence_requirements),
    }
    if not all((packet["work_id"], packet["graph_ref"], packet["local_nodes"], packet["source_refs"], packet["task_AC"], packet["evidence_requirements"])):
        raise ValueError("executor packet requires selected refs and execution requirements")
    return packet


def _contains_semantic_key(value: Any) -> bool:
    if isinstance(value, dict):
        return bool(set(value).intersection(SEMANTIC_RECEIPT_KEYS)) or any(
            _contains_semantic_key(item) for item in value.values()
        )
    if isinstance(value, (list, tuple, set, frozenset)):
        return any(_contains_semantic_key(item) for item in value)
    return False


def _build_receipt(
    packet: dict[str, Any], family: str, allowed_statuses: set[str], status: str,
    *, errors: Iterable[str] = (), **observations: Any
) -> dict[str, Any]:
    if status not in allowed_statuses:
        raise ValueError(f"unsupported receipt status: {status}")
    if _contains_semantic_key(observations):
        raise ValueError("execution receipt cannot contain semantic judgment")
    receipt = {
        "family": family,
        "work_id": packet.get("work_id"),
        "checkpoint_id": packet.get("checkpoint_id"),
        "status": status,
        "recorded_at": _now(),
    }
    bounded = [str(error)[:500] for error in errors][:MAX_RECEIPT_ERRORS]
    if bounded:
        receipt["errors"] = bounded
    receipt.update(observations)
    return receipt


def build_git_worker_receipt(
    packet: dict[str, Any], status: str, *, errors: Iterable[str] = (), **observations: Any
) -> dict[str, Any]:
    return _build_receipt(
        packet, "git_worker_receipt", GIT_WORKER_STATUSES, status,
        errors=errors, **observations,
    )


def build_runtime_receipt(
    packet: dict[str, Any], status: str, *, facts: dict[str, Any] | None = None,
    errors: Iterable[str] = (),
) -> dict[str, Any]:
    if facts is not None and not isinstance(facts, dict):
        raise ValueError("runtime receipt facts must be an object")
    observations = {"facts": facts} if facts is not None else {}
    return _build_receipt(
        packet, "execution_receipt", RUNTIME_RECEIPT_STATUSES, status,
        errors=errors, **observations,
    )


def _exact_mapping(packet: dict[str, Any], key: str, keys: set[str], errors: list[str]) -> dict[str, Any] | None:
    value = packet.get(key)
    if not isinstance(value, dict) or set(value) != keys:
        errors.append(f"{key}:invalid_shape")
        return None
    return value


def _valid_repo_relative_path(value: Any) -> bool:
    if not isinstance(value, str) or not value or "\\" in value or value.startswith("/"):
        return False
    if any(character in value for character in "*?[]") or unicodedata.normalize("NFC", value) != value:
        return False
    parts = value.split("/")
    return all(part not in {"", ".", ".."} for part in parts) and Path(value).as_posix() == value


def _path_has_symlink(repo: Path, relative_path: str) -> bool:
    current = repo
    for part in relative_path.split("/"):
        current = current / part
        try:
            if stat.S_ISLNK(current.lstat().st_mode):
                return True
        except FileNotFoundError:
            return False
    return False


def _validate_lifecycle(packet: dict[str, Any], errors: list[str]) -> None:
    declaration = _exact_mapping(packet, "lifecycle_declaration", LIFECYCLE_KEYS, errors)
    if declaration is None:
        return
    baseline = declaration["baseline"]
    if not isinstance(baseline, dict) or any(state not in {"present", "absent"} for state in baseline.values()):
        errors.append("lifecycle_declaration.baseline:invalid")
        return
    classes: list[list[str]] = []
    for key in ("source_mutations", "ephemeral_generated_paths", "persistent_evidence_paths"):
        paths = declaration[key]
        if not isinstance(paths, list) or any(not _valid_repo_relative_path(path) for path in paths):
            errors.append(f"lifecycle_declaration.{key}:invalid")
            return
        if len(paths) != len(set(paths)):
            errors.append(f"lifecycle_declaration.{key}:duplicate")
        classes.append(paths)
    all_paths = [path for paths in classes for path in paths]
    if len(all_paths) > MAX_LIFECYCLE_PATHS:
        errors.append("lifecycle_declaration:too_many_paths")
    if len(all_paths) != len(set(all_paths)):
        errors.append("lifecycle_declaration:cross_class_path")
    if any(not _valid_repo_relative_path(path) for path in baseline) or set(baseline) != set(all_paths):
        errors.append("lifecycle_declaration.baseline:path_set_mismatch")
    ephemeral = declaration["ephemeral_generated_paths"]
    if any(baseline.get(path) != "absent" for path in ephemeral):
        errors.append("lifecycle_declaration.ephemeral_generated_paths:not_proven_absent")
    repository = packet.get("repository")
    if not isinstance(repository, dict) or not isinstance(repository.get("root"), str):
        return
    repo = Path(repository["root"])
    for path in all_paths:
        if _path_has_symlink(repo, path):
            errors.append(f"lifecycle_declaration:path_ambiguous:{path}")
    for path in ephemeral:
        target = repo / path
        try:
            if stat.S_ISDIR(target.lstat().st_mode):
                errors.append(f"lifecycle_declaration:ephemeral_directory:{path}")
        except FileNotFoundError:
            pass


def validate_checkpoint_packet(packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_keys = TOP_KEYS - {"closure_AC_ref", "CPS_refs"}
    if not isinstance(packet, dict) or not required_keys <= set(packet) or not set(packet) <= TOP_KEYS:
        errors.append("packet:invalid_shape")
        if isinstance(packet, dict) and "lifecycle_declaration" not in packet:
            errors.append("lifecycle_declaration:required")
        return errors
    if packet["schema"] != SCHEMA:
        errors.append("schema:invalid")
    work_id = packet["work_id"]
    checkpoint_id = packet["checkpoint_id"]
    if not isinstance(work_id, str) or not work_id:
        errors.append("work_id:invalid")
    if not isinstance(checkpoint_id, str) or not re.fullmatch(r"[^/@]+@r[1-9][0-9]*", checkpoint_id) or checkpoint_id.rsplit("@r", 1)[0] != work_id:
        errors.append("checkpoint_id:invalid")

    graph = _exact_mapping(packet, "graph_source", {"ref", "digest", "expected_prior_revision"}, errors)
    if graph:
        if not isinstance(graph["ref"], str) or not graph["ref"]:
            errors.append("graph_source.ref:invalid")
        if not isinstance(graph["digest"], str) or not re.fullmatch(r"[0-9a-f]{64}", graph["digest"]):
            errors.append("graph_source.digest:invalid")
        if graph["expected_prior_revision"] is not None and (not isinstance(graph["expected_prior_revision"], int) or graph["expected_prior_revision"] < 1):
            errors.append("graph_source.expected_prior_revision:invalid")

    repository = _exact_mapping(packet, "repository", {"root", "branch", "upstream"}, errors)
    if repository and any(not isinstance(repository[key], str) or not repository[key] for key in repository):
        errors.append("repository:invalid_value")
    _validate_lifecycle(packet, errors)

    has_cps_binding = "CPS_refs" in packet
    has_closure_binding = "closure_AC_ref" in packet
    if has_cps_binding != has_closure_binding:
        errors.append("CPS_binding:partial")
    refs = None
    if has_cps_binding:
        refs = _exact_mapping(packet, "CPS_refs", {"C", "P", "S", "AC", "packet"}, errors)
        if refs:
            if not isinstance(refs["P"], list) or any(not isinstance(item, str) for item in refs["P"]):
                errors.append("CPS_refs.P:invalid")
            if any(not isinstance(refs[key], str) or not refs[key] for key in {"C", "S", "AC", "packet"}):
                errors.append("CPS_refs:invalid_value")
    if has_closure_binding and (not isinstance(packet["closure_AC_ref"], str) or not packet["closure_AC_ref"]):
        errors.append("closure_AC_ref:invalid")
    for key in ("scoped_paths", "excluded_dirty_paths", "prohibited_actions"):
        if not isinstance(packet[key], list) or any(not isinstance(item, str) or not item for item in packet[key]):
            errors.append(f"{key}:invalid")
    if packet["owner_approval"] is not True:
        errors.append("owner_approval:required")
    if packet["execution_instruction"] != EXECUTION_INSTRUCTION:
        errors.append("execution_instruction:invalid")
    if not isinstance(packet["commit_message"], str) or not packet["commit_message"]:
        errors.append("commit_message:invalid")
    if packet["verification_command"] is not None and not isinstance(packet["verification_command"], str):
        errors.append("verification_command:invalid")
    return errors[:MAX_RECEIPT_ERRORS]


def _background_runner(argv: list[str]) -> int:
    process = subprocess.Popen(
        argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return process.pid


def _idempotency_key(packet: dict[str, Any]) -> str:
    raw = "\0".join((packet["checkpoint_id"], packet["graph_source"]["digest"], packet["repository"]["upstream"]))
    return hashlib.sha256(raw.encode()).hexdigest()


def _runner_argv(job_path: Path) -> list[str]:
    return [sys.executable, str(Path(__file__).resolve()), "--run-job", str(job_path.resolve())]


def poll_checkpoint(checkpoint_id: str, record_root: Path) -> dict[str, Any] | None:
    path = Path(record_root) / "jobs" / f"{checkpoint_id}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _default_worker_runner(argv: list[str], stdout_path: Path, stderr_path: Path) -> int:
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        return subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, check=False).returncode


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode:
        reason = result.stderr.strip().replace("\n", " ")[:300]
        raise RuntimeError(f"git {' '.join(args)}: {reason or 'failed'}")
    return result.stdout.strip()


def _path_readback(repo: Path, relative_path: str) -> dict[str, Any]:
    target = repo / relative_path
    try:
        mode = target.lstat().st_mode
        exists = True
        kind = "symlink" if stat.S_ISLNK(mode) else "directory" if stat.S_ISDIR(mode) else "file"
    except FileNotFoundError:
        exists = False
        kind = "absent"
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", "--", relative_path], cwd=repo,
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, check=False,
    )
    if ignored.returncode not in {0, 1}:
        reason = ignored.stderr.strip().replace("\n", " ")[:300]
        raise RuntimeError(f"git check-ignore {relative_path}: {reason or 'failed'}")
    return {"path": relative_path, "exists": exists, "kind": kind, "ignored": ignored.returncode == 0}


def _postcheck(packet: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    repo = Path(packet["repository"]["root"])
    observations: dict[str, Any] = {}
    errors: list[str] = []
    try:
        head = _git(repo, "rev-parse", "HEAD")
        observations["head_sha"] = head
        try:
            upstream = _git(repo, "rev-parse", packet["repository"]["upstream"])
            observations["upstream_sha"] = upstream
            if upstream != head:
                errors.append("postcheck:upstream_sha_mismatch")
        except RuntimeError as exc:
            errors.append(f"postcheck:upstream_unavailable:{exc}")
        message = _git(repo, "log", "-1", "--format=%B")
        if message != packet["commit_message"]:
            errors.append("postcheck:commit_message_mismatch")
        refs = packet.get("CPS_refs")
        if refs:
            trailer = f"CPS-Packet: {refs['packet']}"
            if trailer not in message.splitlines():
                errors.append("postcheck:cps_packet_trailer_missing")
        declaration = packet["lifecycle_declaration"]
        ephemeral = [_path_readback(repo, path) for path in declaration["ephemeral_generated_paths"]]
        persistent = [_path_readback(repo, path) for path in declaration["persistent_evidence_paths"]]
        observations["cleanup_observations"] = {"ephemeral": ephemeral, "persistent": persistent}
        for item in ephemeral:
            if item["exists"]:
                errors.append(f"postcheck:ephemeral_survived:{item['path']}")
        for item in persistent:
            if not item["exists"] or item["kind"] != "file":
                errors.append(f"postcheck:persistent_missing_or_ambiguous:{item['path']}")
    except Exception as exc:
        errors.append(f"postcheck:{type(exc).__name__}:{exc}")
    return observations, [error[:500] for error in errors[:MAX_RECEIPT_ERRORS]]


def run_job(job_path: Path, *, worker_runner: Callable[[list[str], Path, Path], int] | None = None) -> dict[str, Any]:
    job_path = Path(job_path)
    receipt = json.loads(job_path.read_text(encoding="utf-8"))
    packet: dict[str, Any] = receipt
    observations = {key: value for key, value in receipt.items() if key not in {"family", "work_id", "checkpoint_id", "status", "recorded_at", "errors"}}
    try:
        packet_path = Path(receipt["packet_path"])
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        stdout_path = Path(receipt["stdout_log_path"])
        stderr_path = Path(receipt["stderr_log_path"])
        runner = worker_runner or _default_worker_runner
        exit_code = runner(build_worker_argv(packet_path.resolve()), stdout_path, stderr_path)
        errors = [] if exit_code == 0 else [f"worker:exit_code:{exit_code}"]
        observations["worker_exit_code"] = exit_code
        status = "git_failed"
        if exit_code == 0:
            postcheck, postcheck_errors = _postcheck(packet)
            observations.update(postcheck)
            errors.extend(postcheck_errors)
            if not errors:
                status = "git_pushed"
        final = build_git_worker_receipt(packet, status, errors=errors, **observations)
        with _job_lock(job_path):
            _write_json(job_path, final)
    except Exception as exc:
        observations["worker_exit_code"] = locals().get("exit_code")
        final = build_git_worker_receipt(
            packet, "git_failed", errors=[f"run_job:{type(exc).__name__}:{exc}"], **observations,
        )
        with _job_lock(job_path):
            _write_json(job_path, final)
    return final


def _pid_is_alive(pid: Any) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def reconcile_checkpoint(checkpoint_id: str, record_root: Path) -> dict[str, Any] | None:
    job_path = Path(record_root) / "jobs" / f"{checkpoint_id}.json"
    if not job_path.is_file():
        return None
    with _job_lock(job_path):
        receipt = json.loads(job_path.read_text(encoding="utf-8"))
        if receipt.get("status") != "git_pending" or receipt.get("pid") is None or _pid_is_alive(receipt.get("pid")):
            return receipt
        observations = {key: value for key, value in receipt.items() if key not in {"family", "work_id", "checkpoint_id", "status", "recorded_at", "errors"}}
        try:
            packet = json.loads(Path(receipt["packet_path"]).read_text(encoding="utf-8"))
            postcheck, errors = _postcheck(packet)
            observations.update(postcheck)
            observations["reconciliation"] = {"dead_pid_postcheck": True, "pid": receipt.get("pid")}
            status = "git_pushed" if not errors else "git_failed"
        except Exception as exc:
            packet = receipt
            errors = [f"reconcile:{type(exc).__name__}:{exc}"]
            status = "git_failed"
        final = build_git_worker_receipt(packet, status, errors=errors, **observations)
        _write_json(job_path, final)
        return final


def dispatch_checkpoint(packet: dict[str, Any], record_root: Path, *, process_runner: Callable[[list[str]], int] | None = None) -> dict[str, Any]:
    errors = validate_checkpoint_packet(packet)
    if errors:
        status = "git_failed" if any(error.startswith("lifecycle_declaration") for error in errors) else "rejected_dispatch"
        return build_git_worker_receipt(packet, status, errors=errors)
    record_root = Path(record_root)
    checkpoint_id = packet["checkpoint_id"]
    job_path = record_root / "jobs" / f"{checkpoint_id}.json"
    key = _idempotency_key(packet)
    if job_path.exists():
        prior = json.loads(job_path.read_text(encoding="utf-8"))
        if prior.get("idempotency_key") == key:
            return prior
        return build_git_worker_receipt(packet, "rejected_dispatch", errors=["checkpoint_id:conflicting_digest_or_upstream"])
    packet_path = record_root / "packets" / f"{checkpoint_id}-{key}.json"
    stdout_path = record_root / "logs" / f"{checkpoint_id}-{key}.stdout.log"
    stderr_path = record_root / "logs" / f"{checkpoint_id}-{key}.stderr.log"
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_path.touch()
    stderr_path.touch()
    _write_json(packet_path, packet)
    evidence_artifact_paths = [str(path.resolve()) for path in (packet_path, job_path, stdout_path, stderr_path)]
    pending = build_git_worker_receipt(packet, "git_pending", pid=None, packet_path=str(packet_path.resolve()), job_path=str(job_path.resolve()), provider=PROVIDER, model=MODEL, stdout_log_path=str(stdout_path.resolve()), stderr_log_path=str(stderr_path.resolve()), idempotency_key=key, evidence_artifact_paths=evidence_artifact_paths)
    _write_json(job_path, pending)
    runner = process_runner or _background_runner
    try:
        pid = runner(_runner_argv(job_path))
        with _job_lock(job_path):
            current = json.loads(job_path.read_text(encoding="utf-8"))
            if current.get("status") == "git_pending":
                current["pid"] = pid
                current["recorded_at"] = _now()
                _write_json(job_path, current)
        receipt = current
    except Exception as exc:
        failure = build_git_worker_receipt(packet, "git_failed", errors=[f"launch:{type(exc).__name__}:{exc}"], packet_path=str(packet_path.resolve()), job_path=str(job_path.resolve()), provider=PROVIDER, model=MODEL, stdout_log_path=str(stdout_path.resolve()), stderr_log_path=str(stderr_path.resolve()), idempotency_key=key)
        with _job_lock(job_path):
            current = json.loads(job_path.read_text(encoding="utf-8"))
            if current.get("status") == "git_pending":
                _write_json(job_path, failure)
                receipt = failure
            else:
                receipt = current
    return receipt


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--run-job":
        run_job(Path(sys.argv[2]))
    else:
        raise SystemExit("usage: semantic_checkpoint_git_dispatcher.py --run-job JOB_PATH")
