#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

TERMINAL_STATUSES = {"pass", "fail", "blocked"}
OBSERVED_EVENTS = {"dispatch", "heartbeat", "poll", "blocker"}
SEMANTIC_KEYS = {"verdict", "C", "P", "S", "AC", "task_AC", "closure"}
RUNTIME_FACT_KEYS = {
    "event",
    "argv",
    "pid",
    "exit_code",
    "body_artifact_ref",
    "body_digest",
    "body_byte_count",
    "stdout_artifact_ref",
    "stdout_digest",
    "stdout_byte_count",
    "stderr_artifact_ref",
    "stderr_digest",
    "stderr_byte_count",
}
IDENTITY_KEYS = (
    "work_id",
    "graph_ref",
    "graph_revision",
    "graph_digest",
    "stage_ref",
    "owner_ref",
    "parent_edge_ref",
    "return_to_node_ref",
    "run_handle",
    "attempt",
    "immutable_body_digest",
)
PRODUCER_REF = "external_runtime_dispatcher"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _contains_semantic_key(value: Any) -> bool:
    if isinstance(value, dict):
        return bool(set(value).intersection(SEMANTIC_KEYS)) or any(_contains_semantic_key(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_semantic_key(item) for item in value)
    return False


def _validate_identity(identity: dict[str, Any], body: bytes | None = None) -> dict[str, Any]:
    if not isinstance(identity, dict) or set(identity) != set(IDENTITY_KEYS):
        raise ValueError(f"receipt identity must contain exactly: {', '.join(IDENTITY_KEYS)}")
    for key in ("work_id", "graph_ref", "stage_ref", "owner_ref", "parent_edge_ref", "return_to_node_ref", "run_handle"):
        if not isinstance(identity[key], str) or not identity[key]:
            raise ValueError(f"invalid receipt identity: {key}")
    for key in ("graph_revision", "attempt"):
        if isinstance(identity[key], bool) or not isinstance(identity[key], int) or identity[key] < 1:
            raise ValueError(f"invalid receipt identity: {key}")
    for key in ("graph_digest", "immutable_body_digest"):
        if not isinstance(identity[key], str) or re.fullmatch(r"[0-9a-f]{64}", identity[key]) is None:
            raise ValueError(f"invalid receipt identity: {key}")
    if body is not None and hashlib.sha256(body).hexdigest() != identity["immutable_body_digest"]:
        raise ValueError("immutable_body_digest does not match body")
    return dict(identity)


def _case_dir(identity: dict[str, Any], record_root: Path) -> Path:
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    case_key = hashlib.sha256(encoded).hexdigest()
    return Path(record_root) / "external-runtime" / "cases" / case_key


def _paths(identity: dict[str, Any], record_root: Path) -> tuple[Path, Path, Path]:
    case_dir = _case_dir(identity, record_root)
    return case_dir / "receipts.jsonl", case_dir / "current.json", case_dir / "receipt.lock"


@contextmanager
def _case_lock(identity: dict[str, Any], record_root: Path):
    import fcntl

    _, _, lock_path = _paths(identity, record_root)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield
        fcntl.flock(lock, fcntl.LOCK_UN)


def _read_current_unlocked(identity: dict[str, Any], record_root: Path) -> dict[str, Any] | None:
    _, current_path, _ = _paths(identity, record_root)
    if not current_path.is_file():
        return None
    try:
        current = json.loads(current_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("malformed current projection") from exc
    if not isinstance(current, dict):
        raise RuntimeError("malformed current projection")
    return current


def _validate_event_status(event: Any, status: Any) -> None:
    if not ((event in OBSERVED_EVENTS and status == "observed") or (event == "terminal" and status in TERMINAL_STATUSES)):
        raise ValueError(f"unsupported runtime event/status combination: {event}/{status}")


def _validate_runtime_facts(facts: Any) -> dict[str, Any]:
    if not isinstance(facts, dict) or set(facts) != RUNTIME_FACT_KEYS:
        raise ValueError("runtime facts must contain only the closed allowlist")
    argv = facts["argv"]
    if not isinstance(argv, list) or not argv or any(not isinstance(item, str) or not item for item in argv):
        raise ValueError("invalid runtime facts: argv")
    pid = facts["pid"]
    if pid is not None and (isinstance(pid, bool) or not isinstance(pid, int) or pid < 1):
        raise ValueError("invalid runtime facts: pid")
    exit_code = facts["exit_code"]
    if exit_code is not None and (isinstance(exit_code, bool) or not isinstance(exit_code, int)):
        raise ValueError("invalid runtime facts: exit_code")
    for stream in ("body", "stdout", "stderr"):
        artifact_ref = facts[f"{stream}_artifact_ref"]
        digest = facts[f"{stream}_digest"]
        byte_count = facts[f"{stream}_byte_count"]
        if not isinstance(artifact_ref, str) or not artifact_ref:
            raise ValueError(f"invalid runtime facts: {stream}_artifact_ref")
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ValueError(f"invalid runtime facts: {stream}_digest")
        if isinstance(byte_count, bool) or not isinstance(byte_count, int) or byte_count < 0:
            raise ValueError(f"invalid runtime facts: {stream}_byte_count")
    return dict(facts)


def _read_chain_unlocked(identity: dict[str, Any], record_root: Path) -> list[dict[str, Any]]:
    chain_path, _, _ = _paths(identity, record_root)
    if not chain_path.is_file():
        return []
    records: list[dict[str, Any]] = []
    try:
        lines = chain_path.read_text(encoding="utf-8").splitlines()
        for line in lines:
            if line:
                record = json.loads(line)
                if not isinstance(record, dict):
                    raise ValueError
                records.append(record)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError("malformed receipt chain") from exc
    previous_ref = None
    for sequence, record in enumerate(records, 1):
        if any(record.get(key) != value for key, value in identity.items()):
            raise RuntimeError("receipt identity changed in chain")
        expected_ref = f"{identity['run_handle']}:{sequence}"
        if record.get("receipt_ref") != expected_ref or record.get("transition_from_ref") != previous_ref:
            raise RuntimeError("broken receipt transition")
        try:
            _validate_event_status(record.get("facts", {}).get("event"), record.get("status"))
        except (AttributeError, ValueError) as exc:
            raise RuntimeError("malformed receipt chain") from exc
        previous_ref = expected_ref
    return records


def _write_projection(path: Path, receipt: dict[str, Any]) -> None:
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as output:
        json.dump(receipt, output, indent=2, sort_keys=True)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    temporary.replace(path)
    directory_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _write_artifact(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as output:
        output.write(content)
        output.flush()
        os.fsync(output.fileno())
    temporary.replace(path)
    directory_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _artifact_facts(name: str, path: Path, case_dir: Path) -> dict[str, Any]:
    content = path.read_bytes()
    return {
        f"{name}_artifact_ref": path.resolve().relative_to(case_dir.resolve()).as_posix(),
        f"{name}_digest": hashlib.sha256(content).hexdigest(),
        f"{name}_byte_count": len(content),
    }


def _artifact_path(case_dir: Path, artifact_ref: Any) -> Path:
    if not isinstance(artifact_ref, str) or not artifact_ref:
        raise RuntimeError("invalid artifact ref")
    path = (case_dir / artifact_ref).resolve()
    try:
        path.relative_to(case_dir.resolve())
    except ValueError as exc:
        raise RuntimeError("artifact ref escapes case directory") from exc
    return path


def _receipt(
    identity: dict[str, Any],
    consumer_ref: str,
    status: str,
    facts: dict[str, Any],
    sequence: int,
    transition_from_ref: str | None,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    event = facts.get("event")
    _validate_event_status(event, status)
    if _contains_semantic_key(facts):
        raise ValueError("execution receipt facts cannot contain semantic judgment")
    receipt: dict[str, Any] = {
        "family": "execution_receipt",
        "receipt_ref": f"{identity['run_handle']}:{sequence}",
        "transition_from_ref": transition_from_ref,
        **identity,
        "checkpoint_id": None,
        "status": status,
        "recorded_at": _now(),
        "external_runtime_receipt": {
            "producer_ref": PRODUCER_REF,
            "runtime_receipt": identity["run_handle"],
            "consumer_ref": consumer_ref,
        },
        "facts": facts,
    }
    if errors:
        receipt["errors"] = [str(error)[:500] for error in errors[:8]]
    return receipt


def _append_locked(
    identity: dict[str, Any],
    record_root: Path,
    consumer_ref: str,
    status: str,
    facts: dict[str, Any],
    errors: list[str] | None = None,
) -> dict[str, Any]:
    _validate_event_status(facts.get("event") if isinstance(facts, dict) else None, status)
    facts = _validate_runtime_facts(facts)
    chain_path, current_path, _ = _paths(identity, record_root)
    chain = _read_chain_unlocked(identity, record_root)
    current = _read_current_unlocked(identity, record_root)
    if bool(chain) != bool(current) or (chain and current != chain[-1]):
        raise RuntimeError("current projection does not match chain tail")
    if current and current["status"] in TERMINAL_STATUSES:
        raise RuntimeError("terminal receipt already recorded")
    if current is None and facts.get("event") != "dispatch":
        raise RuntimeError("dispatch receipt not recorded")
    if current is not None and facts.get("event") == "dispatch":
        raise RuntimeError("dispatch receipt already recorded")
    sequence = len(chain) + 1
    transition_from_ref = chain[-1]["receipt_ref"] if chain else None
    receipt = _receipt(identity, consumer_ref, status, facts, sequence, transition_from_ref, errors)
    chain_path.parent.mkdir(parents=True, exist_ok=True)
    with chain_path.open("a", encoding="utf-8") as chain:
        chain.write(json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n")
        chain.flush()
        os.fsync(chain.fileno())
    _write_projection(current_path, receipt)
    return receipt


def _append_observed(
    identity: dict[str, Any],
    record_root: Path,
    event: str,
    updates: dict[str, Any] | None = None,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    identity = _validate_identity(identity)
    with _case_lock(identity, record_root):
        current = _read_current_unlocked(identity, record_root)
        if current is None:
            raise RuntimeError("dispatch receipt not recorded")
        facts = dict(current["facts"])
        facts.update(updates or {})
        facts["event"] = event
        consumer_ref = current["external_runtime_receipt"]["consumer_ref"]
        return _append_locked(identity, record_root, consumer_ref, "observed", facts, errors)


def load_receipt_chain(identity: dict[str, Any], record_root: Path) -> list[dict[str, Any]]:
    identity = _validate_identity(identity)
    with _case_lock(identity, record_root):
        return _read_chain_unlocked(identity, record_root)


def _runner_argv(job_path: Path) -> list[str]:
    return [sys.executable, str(Path(__file__).resolve()), "--run-job", str(job_path.resolve())]


def _background_runner(argv: list[str]) -> int:
    return subprocess.Popen(
        argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    ).pid


def dispatch_external_runtime(
    consumer_ref: str,
    body: bytes,
    argv: list[str],
    record_root: Path,
    *,
    identity: dict[str, Any],
    process_runner: Callable[[list[str]], int] | None = None,
) -> dict[str, Any]:
    if not isinstance(body, bytes):
        raise TypeError("body must be bytes")
    identity = _validate_identity(identity, body)
    if not consumer_ref or not isinstance(argv, list) or not argv or any(not isinstance(item, str) or not item for item in argv):
        raise ValueError("consumer_ref and argv are required")
    case_dir = _case_dir(identity, record_root)
    body_path = case_dir / "artifacts" / "body.bin"
    stdout_path = case_dir / "artifacts" / "stdout.bin"
    stderr_path = case_dir / "artifacts" / "stderr.bin"
    _, current_path, _ = _paths(identity, record_root)
    with _case_lock(identity, record_root):
        if _read_current_unlocked(identity, record_root) is not None or _read_chain_unlocked(identity, record_root):
            raise RuntimeError("dispatch receipt already recorded")
        _write_artifact(body_path, body)
        _write_artifact(stdout_path, b"")
        _write_artifact(stderr_path, b"")
        facts = {"event": "dispatch", "argv": list(argv), "pid": None, "exit_code": None}
        facts.update(_artifact_facts("body", body_path, case_dir))
        facts.update(_artifact_facts("stdout", stdout_path, case_dir))
        facts.update(_artifact_facts("stderr", stderr_path, case_dir))
        _append_locked(identity, record_root, consumer_ref, "observed", facts)
    try:
        pid = (process_runner or _background_runner)(_runner_argv(current_path))
    except Exception as exc:
        return append_terminal_receipt(identity, record_root, "blocked", errors=[f"launch:{type(exc).__name__}:{exc}"])
    try:
        return append_heartbeat(identity, record_root, pid=pid)
    except RuntimeError as exc:
        if str(exc) != "terminal receipt already recorded":
            raise
        terminal = poll_external_runtime(identity, record_root)
        if terminal is None:
            raise RuntimeError("terminal receipt disappeared after launch")
        return terminal


def append_heartbeat(identity: dict[str, Any], record_root: Path, *, pid: int | None = None) -> dict[str, Any]:
    updates = {"pid": pid} if pid is not None else {}
    return _append_observed(identity, record_root, "heartbeat", updates)


def append_terminal_receipt(
    identity: dict[str, Any],
    record_root: Path,
    status: str,
    *,
    facts: dict[str, Any] | None = None,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    if status not in TERMINAL_STATUSES:
        raise ValueError("terminal status must be pass, fail, or blocked")
    identity = _validate_identity(identity)
    with _case_lock(identity, record_root):
        current = _read_current_unlocked(identity, record_root)
        if current is None:
            raise RuntimeError("dispatch receipt not recorded")
        terminal_facts = dict(current["facts"])
        terminal_facts.update(facts or {})
        terminal_facts["event"] = "terminal"
        consumer_ref = current["external_runtime_receipt"]["consumer_ref"]
        return _append_locked(identity, record_root, consumer_ref, status, terminal_facts, errors)


def run_job(job_path: Path) -> dict[str, Any]:
    job_path = Path(job_path)
    record_root = job_path.parents[3]
    candidate = json.loads(job_path.read_text(encoding="utf-8"))
    identity = _validate_identity({key: candidate[key] for key in IDENTITY_KEYS})
    chain = load_receipt_chain(identity, record_root)
    if not chain or candidate != chain[-1]:
        raise RuntimeError("current projection does not match chain tail")
    current = chain[-1]
    if current["status"] in TERMINAL_STATUSES:
        return current
    facts = dict(current["facts"])
    case_dir = job_path.parent
    body_path = _artifact_path(case_dir, facts.get("body_artifact_ref"))
    stdout_path = _artifact_path(case_dir, facts.get("stdout_artifact_ref"))
    stderr_path = _artifact_path(case_dir, facts.get("stderr_artifact_ref"))
    errors: list[str] = []
    try:
        if _artifact_facts("body", body_path, case_dir) != {
            key: facts[key] for key in ("body_artifact_ref", "body_digest", "body_byte_count")
        }:
            raise RuntimeError("body artifact metadata mismatch")
        with body_path.open("rb") as body, stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            result = subprocess.run(facts["argv"], stdin=body, stdout=stdout, stderr=stderr, check=False)
            for output in (stdout, stderr):
                output.flush()
                os.fsync(output.fileno())
        facts["exit_code"] = result.returncode
        facts.update(_artifact_facts("stdout", stdout_path, case_dir))
        facts.update(_artifact_facts("stderr", stderr_path, case_dir))
        status = "pass" if result.returncode == 0 else "fail"
        if result.returncode:
            errors.append(f"runtime:exit_code:{result.returncode}")
    except Exception as exc:
        status = "blocked"
        errors.append(f"runtime:{type(exc).__name__}:{exc}")
    return append_terminal_receipt(identity, record_root, status, facts=facts, errors=errors)


def poll_external_runtime(identity: dict[str, Any], record_root: Path) -> dict[str, Any] | None:
    identity = _validate_identity(identity)
    with _case_lock(identity, record_root):
        current = _read_current_unlocked(identity, record_root)
        if current is None or current["status"] in TERMINAL_STATUSES:
            return current
        facts = dict(current["facts"])
        facts["event"] = "poll"
        consumer_ref = current["external_runtime_receipt"]["consumer_ref"]
        return _append_locked(identity, record_root, consumer_ref, "observed", facts)


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


def reconcile_external_runtime(
    identity: dict[str, Any],
    record_root: Path,
    *,
    pid_is_alive: Callable[[Any], bool] | None = None,
    stale_after_seconds: float | None = None,
) -> dict[str, Any] | None:
    identity = _validate_identity(identity)
    with _case_lock(identity, record_root):
        current = _read_current_unlocked(identity, record_root)
        if current is None:
            return None
        if current["status"] in TERMINAL_STATUSES:
            raise RuntimeError("terminal receipt already recorded")
        facts = dict(current["facts"])
        consumer_ref = current["external_runtime_receipt"]["consumer_ref"]
        alive = (pid_is_alive or _pid_is_alive)(facts.get("pid"))
        if alive and stale_after_seconds is None:
            facts["event"] = "heartbeat"
            return _append_locked(identity, record_root, consumer_ref, "observed", facts)
        if alive:
            assert stale_after_seconds is not None
            recorded_at = datetime.fromisoformat(current["recorded_at"])
            age_seconds = (datetime.now(timezone.utc) - recorded_at).total_seconds()
            if age_seconds <= stale_after_seconds:
                facts["event"] = "heartbeat"
                return _append_locked(identity, record_root, consumer_ref, "observed", facts)
            facts["event"] = "blocker"
            return _append_locked(identity, record_root, consumer_ref, "observed", facts, ["runtime:stale"])
        facts["event"] = "blocker"
        return _append_locked(identity, record_root, consumer_ref, "observed", facts, ["runtime:lost"])


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--run-job":
        run_job(Path(sys.argv[2]))
    else:
        raise SystemExit("usage: external_runtime_dispatcher.py --run-job JOB_PATH")
