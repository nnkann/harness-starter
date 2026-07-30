#!/usr/bin/env python3
"""Execute the bounded Skill Live Reference C1 -> C2 -> C3 native lane."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid
from typing import Any, Mapping

SCHEMA_DISPATCH = "harness.skill-live-reference.c4-dispatch.v1"
SCHEMA_TERMINAL = "harness.skill-live-reference.c4-terminal.v1"
SCHEMA_BODY = "harness.skill-live-reference.c4-body.v1"
C1_SCHEMA = "harness.skill-live-reference.c1-result.v1"
C2_SCHEMA = "harness.skill-live-reference.c2-result.v1"
REPO_ROOT = Path(__file__).resolve().parents[3]
READERS_DIR = REPO_ROOT / ".harness/hermes/readers"
COLLECTOR = REPO_ROOT / ".harness/hermes/tools/skill_live_reference_sia_audit.py"
DEFAULT_BRAIN_ROOT = Path("/Users/kann/projects/harness-brain")
DEFAULT_GBRAIN = Path("/Users/kann/.bun/bin/gbrain")
_MAX_OUTPUT_BYTES = 256 * 1024
_MAX_GIT_OUTPUT_BYTES = 4 * 1024 * 1024
_MAX_INPUT_BYTES = 256 * 1024
_MAX_ENV_NAMES = 128
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._/@+-]{0,255}$")
_RESULT_KEYS = {
    "schema", "result_id", "source_receipt", "availability", "pointer_digest",
    "pointer_integrity", "source_backed_conflicts", "verified_outcome_eligible",
}


class RunnerError(RuntimeError):
    pass


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _external_state_dir(value: str | Path | None, brain_root: Path) -> Path:
    if value is None or not str(value).strip():
        raise RunnerError("HARNESS_STATE_DIR is required")
    try:
        state = Path(value).expanduser().resolve(strict=False)
        repo = REPO_ROOT.resolve(strict=True)
        brain = brain_root.expanduser().resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        raise RunnerError("state or source root is invalid") from exc
    if _inside(state, repo) or _inside(state, brain):
        raise RunnerError("HARNESS_STATE_DIR must be external to repo and harness-brain")
    return state


def _read_json(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        if not path.is_file() or path.stat().st_size > _MAX_INPUT_BYTES:
            raise RunnerError("input artifact is missing or exceeds the byte bound")
        payload = path.read_bytes()
        value = json.loads(payload)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RunnerError("input artifact is unreadable") from exc
    if not isinstance(value, dict):
        raise RunnerError("input artifact must be an object")
    return value, payload


def _validate_c2(value: Mapping[str, Any]) -> dict[str, Any]:
    if set(value) != _RESULT_KEYS or value.get("schema") != C2_SCHEMA:
        raise RunnerError("C2 artifact does not match the strict C2 schema")
    if not isinstance(value.get("result_id"), str) or _ID.fullmatch(value["result_id"]) is None:
        raise RunnerError("C2 result_id is invalid")
    if not isinstance(value.get("source_receipt"), str) or _ID.fullmatch(value["source_receipt"]) is None:
        raise RunnerError("C2 source_receipt is invalid")
    if (
        value.get("availability") != "unavailable"
        or value.get("pointer_digest") is not None
        or value.get("pointer_integrity") != "unknown"
        or value.get("source_backed_conflicts") != []
        or value.get("verified_outcome_eligible") is not None
    ):
        raise RunnerError("C2 must be caller-recorded native unavailable evidence")
    return dict(value)


def _run(argv: list[str], *, cwd: Path, env: Mapping[str, str], timeout: float,
         output_limit: int = _MAX_OUTPUT_BYTES) -> subprocess.CompletedProcess[bytes]:
    try:
        completed = subprocess.run(
            argv, cwd=cwd, env=dict(env), stdin=subprocess.DEVNULL,
            capture_output=True, text=False, shell=False, check=False, timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RunnerError(f"bounded subprocess failed: {argv[0]}") from exc
    if len(completed.stdout) > output_limit or len(completed.stderr) > output_limit:
        raise RunnerError(f"bounded subprocess output exceeded: {argv[0]}")
    return completed


def _git(repo: Path, args: list[str]) -> bytes:
    completed = _run(
        ["git", "-C", str(repo), *args], cwd=repo,
        env=_child_env(None), timeout=15, output_limit=_MAX_GIT_OUTPUT_BYTES,
    )
    if completed.returncode != 0:
        raise RunnerError(f"git read failed for {repo.name}")
    return completed.stdout


def _dirty_digest(repo: Path) -> tuple[str, int]:
    status = _git(repo, ["status", "--porcelain=v1", "-z", "--untracked-files=all"])
    records = [item for item in status.split(b"\0") if item]
    paths: set[bytes] = set()
    index = 0
    while index < len(records):
        record = records[index]
        if len(record) < 4:
            raise RunnerError("malformed git status record")
        code, path = record[:2], record[3:]
        paths.add(path)
        if b"R" in code or b"C" in code:
            index += 1
            if index >= len(records):
                raise RunnerError("malformed git rename record")
            paths.add(records[index])
        index += 1
    digest = hashlib.sha256(status)
    for raw in sorted(paths):
        relative = raw.decode("utf-8", "surrogateescape")
        candidate = repo / relative
        digest.update(b"\0path\0" + raw)
        try:
            if candidate.is_symlink():
                digest.update(b"symlink\0" + os.readlink(candidate).encode("utf-8", "surrogateescape"))
            elif candidate.is_file():
                digest.update(b"file\0" + _sha256_file(candidate).encode())
            elif candidate.exists():
                digest.update(b"other")
            else:
                digest.update(b"absent")
        except OSError as exc:
            raise RunnerError("dirty file read failed") from exc
    return digest.hexdigest(), len(paths)


def _git_snapshot(repo: Path) -> dict[str, Any]:
    head = _git(repo, ["rev-parse", "HEAD"]).decode().strip()
    tree = _git(repo, ["rev-parse", "HEAD^{tree}"]).decode().strip()
    dirty_digest, dirty_count = _dirty_digest(repo)
    if re.fullmatch(r"[0-9a-f]{40,64}", head) is None or re.fullmatch(r"[0-9a-f]{40,64}", tree) is None:
        raise RunnerError("git identity is malformed")
    return {
        "head": head,
        "tree": tree,
        "dirty_files_digest": dirty_digest,
        "dirty_file_count": dirty_count,
    }


def _child_env(state_dir: Path | None) -> dict[str, str]:
    names = ("HOME", "LANG", "LC_ALL", "PATH", "TMPDIR")
    env = {name: os.environ[name] for name in names if name in os.environ}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if state_dir is not None:
        env["HARNESS_STATE_DIR"] = str(state_dir)
    return env


def _environment_receipt(env: Mapping[str, str]) -> dict[str, Any]:
    names = sorted(env)
    if len(names) > _MAX_ENV_NAMES:
        raise RunnerError("environment name bound exceeded")
    encoded = _canonical_bytes(names)
    return {
        "basis": "names_only_no_values",
        "name_count": len(names),
        "names_sha256": _sha256_bytes(encoded),
    }


def _write_verified(path: Path, payload: bytes) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("wb") as target:
        target.write(payload)
        target.flush()
        os.fsync(target.fileno())
    os.replace(temporary, path)
    readback = path.read_bytes()
    if readback != payload:
        raise RunnerError("artifact readback failed")
    return {"path": str(path), "sha256": _sha256_bytes(readback), "bytes": len(readback), "readback_verified": True}


def _worker(body_path: Path) -> int:
    body, _ = _read_json(body_path)
    required = {"schema", "run_id", "query", "c2_artifact", "brain_root", "gbrain_executable", "run_dir", "timeout"}
    if set(body) != required or body.get("schema") != SCHEMA_BODY:
        raise RunnerError("worker body schema is invalid")
    run_dir = Path(body["run_dir"]).resolve(strict=True)
    brain_root = Path(body["brain_root"]).resolve(strict=True)
    state_root = _external_state_dir(run_dir, brain_root)
    c2_path = Path(body["c2_artifact"]).expanduser().resolve(strict=True)
    c2_value, c2_bytes = _read_json(c2_path)
    c2 = _validate_c2(c2_value)
    timeout = float(body["timeout"])
    if not 0 < timeout <= 30:
        raise RunnerError("timeout must be at most 30 seconds")

    sys.dont_write_bytecode = True
    sys.path.insert(0, str(READERS_DIR))
    gbrain_search_reader = importlib.import_module("gbrain_search_reader")
    gbrain_skill_reference_resolver = importlib.import_module("gbrain_skill_reference_resolver")

    def bounded_search(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        completed = _run(argv, cwd=REPO_ROOT, env=kwargs["env"], timeout=float(kwargs["timeout"]))
        return subprocess.CompletedProcess(
            argv, completed.returncode,
            completed.stdout.decode("utf-8"), completed.stderr.decode("utf-8"),
        )

    search = gbrain_search_reader.create_gbrain_search_reader(
        executable=str(Path(body["gbrain_executable"])), limit=5, timeout=timeout, runner=bounded_search,
    )
    resolved = gbrain_skill_reference_resolver.resolve_skill_live_reference(
        body["query"], search_reader=search, harness_brain_root=brain_root,
    )
    clues = resolved.get("usable_clues")
    if resolved.get("status") != "match" or not isinstance(clues, list) or not clues:
        raise RunnerError("C1 canonical resolver did not produce an actual match")
    clue = clues[0]
    if clue.get("status") != "available" or not _HEX64.fullmatch(str(clue.get("content_digest", ""))):
        raise RunnerError("C1 canonical readback is malformed")
    c1_value = {
        "schema": C1_SCHEMA,
        "result_id": f"c1:canonical-resolver:{clue['content_digest'][:16]}",
        "source_receipt": f"c1:canonical-readback:{clue['content_digest'][:16]}",
        "availability": "available",
        "pointer_digest": clue["content_digest"],
        "pointer_integrity": "valid",
        "source_backed_conflicts": [],
        "verified_outcome_eligible": False,
    }
    c1_path = state_root / "inputs" / "c1-canonical-resolver.json"
    c1_artifact = _write_verified(c1_path, _canonical_bytes(c1_value))

    c3_state = state_root / "c3"
    collector_argv = [
        sys.executable, str(COLLECTOR),
        "--harness-brain-root", str(brain_root),
        "--gbrain-executable", str(Path(body["gbrain_executable"])),
        "--source-id", "harness-brain",
        "--c1-result", str(c1_path),
        "--c2-result", str(c2_path),
        "--timeout", str(timeout),
    ]
    collector_env = _child_env(c3_state)
    completed = _run(collector_argv, cwd=REPO_ROOT, env=collector_env, timeout=min(60.0, timeout * 3))
    if completed.returncode != 0:
        raise RunnerError("C3 collector failed closed")
    try:
        c3 = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RunnerError("C3 collector stdout is malformed") from exc
    if not isinstance(c3, dict):
        raise RunnerError("C3 collector receipt is malformed")
    c3_path = c3_state / "receipts" / f"{c3.get('run_id')}.json"
    persisted, persisted_bytes = _read_json(c3_path)
    if persisted != c3:
        raise RunnerError("C3 receipt readback differs from stdout")
    if not (
        c3.get("delta") is False
        and c3.get("delta_classes") == []
        and c3.get("sia_invoked") is False
        and c3.get("review_packet") is None
        and c3.get("failure_reason") is None
    ):
        raise RunnerError("C3 collector was not clean/no-action")

    result = {
        "run_id": body["run_id"],
        "c1": {
            "source": "gbrain_search_reader->gbrain_skill_reference_resolver->canonical_readback",
            "query": body["query"],
            "search_argv": [str(Path(body["gbrain_executable"])), "search", body["query"], "--limit", "5"],
            "source_ref": clue["source_ref"],
            "canonical_repo": clue["canonical_repo"],
            "canonical_path": clue["repo_relative_path"],
            "canonical_revision": clue["current_source_revision"],
            "canonical_digest": clue["content_digest"],
            "source_receipt": clue["source_receipt"],
            "artifact": c1_artifact,
        },
        "c2": {
            "artifact_result_source": "caller_supplied",
            "artifact": {"path": str(c2_path), "sha256": _sha256_bytes(c2_bytes), "bytes": len(c2_bytes), "readback_verified": c2_path.read_bytes() == c2_bytes},
            "result_id": c2["result_id"],
            "source_receipt": c2["source_receipt"],
            "evidence_mode": "native",
            "availability": "unavailable",
            "provider_capability_boundary": {
                "provider": "honcho",
                "invocation_scope_parameters": [],
                "unsupported_scope_parameters": ["thread", "project", "profile"],
            },
        },
        "c3": {
            "source": "skill_live_reference_sia_audit",
            "location": str(c3_path),
            "receipt_sha256": _sha256_bytes(persisted_bytes),
            "readback_verified": True,
            "clean": True,
            "delta": False,
            "delta_classes": [],
            "sia_invoked": False,
            "review_packet": None,
            "failure_reason": None,
            "receipt_id": c3["receipt_id"],
        },
        "conclusion": {
            "status": "partial",
            "missing_capability": ["native_available_pointer", "native_source_backed_conflict"],
        },
    }
    sys.stdout.buffer.write(_canonical_bytes(result))
    return 0


def execute(*, query: str, c2_artifact: Path, brain_root: Path, gbrain_executable: Path,
            state_dir: Path | None, timeout: float) -> tuple[dict[str, Any], int]:
    if not isinstance(query, str) or not query or query != query.strip() or len(query) > 512 or "\x00" in query:
        raise RunnerError("query is invalid")
    if not 0 < timeout <= 30:
        raise RunnerError("timeout must be at most 30 seconds")
    state_root = _external_state_dir(state_dir, brain_root)
    c2_path = c2_artifact.expanduser().resolve(strict=True)
    _validate_c2(_read_json(c2_path)[0])
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:12]
    run_dir = state_root / "skill-live-reference" / "c4-runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    body_path = run_dir / "body.json"
    dispatch_path = run_dir / "dispatch.json"
    terminal_path = run_dir / "terminal.json"
    stdout_path = run_dir / "stdout.json"
    stderr_path = run_dir / "stderr.txt"
    body = {
        "schema": SCHEMA_BODY,
        "run_id": run_id,
        "query": query,
        "c2_artifact": str(c2_path),
        "brain_root": str(brain_root.expanduser().resolve(strict=True)),
        "gbrain_executable": str(gbrain_executable.expanduser().resolve(strict=True)),
        "run_dir": str(run_dir),
        "timeout": timeout,
    }
    body_artifact = _write_verified(body_path, _canonical_bytes(body))
    before = {"repo": _git_snapshot(REPO_ROOT), "harness_brain": _git_snapshot(Path(body["brain_root"]))}
    worker_argv = [sys.executable, str(Path(__file__).resolve()), "--worker", str(body_path)]
    worker_env = _child_env(run_dir)
    dispatch = {
        "schema": SCHEMA_DISPATCH,
        "run_id": run_id,
        "linked_terminal_path": str(terminal_path),
        "argv": worker_argv,
        "cwd": str(REPO_ROOT),
        "environment_digest": _environment_receipt(worker_env),
        "git_before": before,
        "artifacts": {
            "body": body_artifact,
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
        },
    }
    dispatch_artifact = _write_verified(dispatch_path, _canonical_bytes(dispatch))

    error = None
    try:
        completed = _run(worker_argv, cwd=REPO_ROOT, env=worker_env, timeout=min(120.0, timeout * 4))
        worker_exit = completed.returncode
        stdout, stderr = completed.stdout, completed.stderr
    except RunnerError as exc:
        worker_exit, stdout, stderr, error = 2, b"", b"", str(exc)
    stdout_artifact = _write_verified(stdout_path, stdout)
    stderr_artifact = _write_verified(stderr_path, stderr)
    after = {"repo": _git_snapshot(REPO_ROOT), "harness_brain": _git_snapshot(Path(body["brain_root"]))}
    source_unchanged = before == after
    lane = None
    if worker_exit == 0:
        try:
            lane = json.loads(stdout)
        except json.JSONDecodeError:
            error = "worker stdout is malformed"
            worker_exit = 2
    if not source_unchanged:
        error = "repo or harness-brain changed during execution"
        worker_exit = 2
    terminal = {
        "schema": SCHEMA_TERMINAL,
        "run_id": run_id,
        "linked_dispatch_path": str(dispatch_path),
        "dispatch_sha256": dispatch_artifact["sha256"],
        "argv": worker_argv,
        "cwd": str(REPO_ROOT),
        "environment_digest": _environment_receipt(worker_env),
        "git_before": before,
        "git_after": after,
        "source_trees_unchanged": source_unchanged,
        "exit_code": worker_exit,
        "artifacts": {"body": body_artifact, "stdout": stdout_artifact, "stderr": stderr_artifact},
        "lane": lane,
        "conclusion": lane.get("conclusion") if isinstance(lane, dict) else {"status": "blocked", "reason": error or "worker_failed"},
    }
    terminal_artifact = _write_verified(terminal_path, _canonical_bytes(terminal))
    summary = {
        "run_id": run_id,
        "dispatch_path": str(dispatch_path),
        "dispatch_sha256": dispatch_artifact["sha256"],
        "terminal_path": str(terminal_path),
        "terminal_sha256": terminal_artifact["sha256"],
        "exit_code": worker_exit,
        "conclusion": terminal["conclusion"],
    }
    return summary, worker_exit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query")
    parser.add_argument("--c2-artifact", type=Path)
    parser.add_argument("--harness-brain-root", type=Path, default=DEFAULT_BRAIN_ROOT)
    parser.add_argument("--gbrain-executable", type=Path, default=DEFAULT_GBRAIN)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        if args.worker:
            return _worker(args.worker)
        if args.query is None or args.c2_artifact is None:
            parser.error("--query and --c2-artifact are required")
        summary, exit_code = execute(
            query=args.query,
            c2_artifact=args.c2_artifact,
            brain_root=args.harness_brain_root,
            gbrain_executable=args.gbrain_executable,
            state_dir=Path(os.environ["HARNESS_STATE_DIR"]) if os.environ.get("HARNESS_STATE_DIR") else None,
            timeout=args.timeout,
        )
        print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
        return exit_code
    except (KeyError, OSError, RunnerError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
