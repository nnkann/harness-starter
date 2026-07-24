#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

TERMINAL_STATUSES = {"pass", "fail", "blocked"}
OBSERVED_EVENTS = {"dispatch", "poll", "blocker"}
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
    "native_profile_ref",
    "native_correlation_id",
    "native_runs",
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
HERMES_MAX_TURNS = 8
HERMES_TOOLSET = "file"
TERMINAL_RETENTION_SECONDS = 7 * 24 * 60 * 60
_last_prune_at: dict[Path, float] = {}
PRUNE_INTERVAL_SECONDS = 5 * 60


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


def prune_terminal_cases(record_root: Path, *, retention_seconds: float = TERMINAL_RETENTION_SECONDS) -> int:
    """Remove only terminal external-runtime cases older than the retention window."""
    if retention_seconds < 0:
        raise ValueError("retention_seconds must be non-negative")
    cases = Path(record_root) / "external-runtime" / "cases"
    if not cases.is_dir():
        return 0
    cutoff = datetime.now(timezone.utc).timestamp() - retention_seconds
    removed = 0
    for case_dir in cases.iterdir():
        current_path = case_dir / "current.json"
        try:
            current = json.loads(current_path.read_text(encoding="utf-8"))
            recorded_at = datetime.fromisoformat(current["recorded_at"]).timestamp()
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
        if current.get("status") not in TERMINAL_STATUSES or recorded_at > cutoff:
            continue
        try:
            shutil.rmtree(case_dir)
            removed += 1
        except OSError:
            continue
    return removed


def _prune_terminal_cases_if_due(record_root: Path) -> None:
    root = Path(record_root).resolve()
    now = datetime.now(timezone.utc).timestamp()
    if now - _last_prune_at.get(root, 0.0) < PRUNE_INTERVAL_SECONDS:
        return
    prune_terminal_cases(root)
    _last_prune_at[root] = now


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


def _canonical_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


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
    if not isinstance(facts["native_profile_ref"], str) or not facts["native_profile_ref"]:
        raise ValueError("invalid runtime facts: native_profile_ref")
    correlation = facts["native_correlation_id"]
    if not isinstance(correlation, str) or re.fullmatch(r"[0-9a-f]{64}", correlation) is None:
        raise ValueError("invalid runtime facts: native_correlation_id")
    runs = facts["native_runs"]
    if not isinstance(runs, list):
        raise ValueError("invalid runtime facts: native_runs")
    expected_profiles = (facts["native_profile_ref"], "anubis", "maat")
    for index, run in enumerate(runs):
        if not isinstance(run, dict) or set(run) != {
            "profile", "correlation_id", "session_ref", "session_digest",
            "exit_status", "output_digest", "gate_status", "tool_evidence",
        }:
            raise ValueError("invalid runtime facts: native_runs")
        if index >= len(expected_profiles) or run["profile"] != expected_profiles[index] or run["correlation_id"] != correlation:
            raise ValueError("invalid runtime facts: native run correlation")
        if not isinstance(run["session_ref"], str) or not run["session_ref"]:
            raise ValueError("invalid runtime facts: native run session_ref")
        for key in ("session_digest", "output_digest"):
            if not isinstance(run[key], str) or re.fullmatch(r"[0-9a-f]{64}", run[key]) is None:
                raise ValueError(f"invalid runtime facts: native run {key}")
        if isinstance(run["exit_status"], bool) or not isinstance(run["exit_status"], int):
            raise ValueError("invalid runtime facts: native run exit_status")
        if run["gate_status"] not in (None, "pass", "hold", "fail"):
            raise ValueError("invalid runtime facts: native run gate_status")
        if not isinstance(run["tool_evidence"], list):
            raise ValueError("invalid runtime facts: native run tool_evidence")
        for tool in run["tool_evidence"]:
            if not isinstance(tool, dict) or set(tool) != {"tool_name", "canonical_input_digest", "exit_status", "output_digest"}:
                raise ValueError("invalid runtime facts: native tool evidence")
            if not isinstance(tool["tool_name"], str) or not tool["tool_name"]:
                raise ValueError("invalid runtime facts: native tool_name")
            if any(not isinstance(tool[key], str) or re.fullmatch(r"[0-9a-f]{64}", tool[key]) is None for key in ("canonical_input_digest", "output_digest")):
                raise ValueError("invalid runtime facts: native tool digest")
            if isinstance(tool["exit_status"], bool) or not isinstance(tool["exit_status"], int):
                raise ValueError("invalid runtime facts: native tool exit_status")
    return dict(facts)


def _native_argv(consumer_ref: str, body: bytes, correlation_id: str) -> list[str]:
    try:
        query = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("immutable body must be UTF-8 text") from exc
    return [
        "hermes", "-p", consumer_ref, "chat", "-Q", "--pass-session-id",
        "--source", f"harness:{correlation_id}", "--max-turns",
        str(HERMES_MAX_TURNS), "-t", HERMES_TOOLSET, "-q", query,
    ]


def _tool_exit_status(content: str) -> int:
    try:
        value = json.loads(content)
    except (TypeError, json.JSONDecodeError):
        return 0
    if isinstance(value, dict):
        exit_code = value.get("exit_code")
        if isinstance(exit_code, int) and not isinstance(exit_code, bool):
            return exit_code
        if value.get("error") not in (None, ""):
            return 1
    return 0


def _native_verdict(profile: str, output: str) -> str | None:
    try:
        value = json.loads(output)
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict):
        return None
    status = str(value.get("status", "")).lower()
    if profile == "anubis":
        verdict = str(value.get("verdict", status)).lower()
        return verdict if verdict in {"pass", "hold", "fail"} else None
    if profile == "maat":
        closure = value.get("Goal_closure")
        if status == "pass" and isinstance(closure, dict) and closure.get("status") == "pass":
            return "pass"
        return status if status in {"hold", "fail"} else None
    return "pass" if status == "pass" else None


def _native_run_evidence(profile: str, body: bytes, correlation_id: str, exit_status: int) -> dict[str, Any]:
    state_path = Path.home() / ".hermes" / "profiles" / profile / "state.db"
    if not state_path.is_file():
        raise RuntimeError("native session store absent")
    try:
        query = body.decode("utf-8")
        uri = f"file:{state_path.as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=2.0) as connection:
            connection.row_factory = sqlite3.Row
            sessions = connection.execute(
                "SELECT * FROM sessions WHERE source = ? ORDER BY started_at",
                (f"harness:{correlation_id}",),
            ).fetchall()
            if len(sessions) != 1:
                raise RuntimeError("native correlation absent or duplicated")
            session = sessions[0]
            messages = connection.execute(
                "SELECT id, role, content, tool_call_id, tool_calls, tool_name FROM messages "
                "WHERE session_id = ? ORDER BY id", (session["id"],),
            ).fetchall()
        users = [row for row in messages if row["role"] == "user" and row["content"] == query]
        if len(users) != 1:
            raise RuntimeError("native session body mismatch")
        results = {row["tool_call_id"]: row for row in messages if row["role"] == "tool" and row["tool_call_id"]}
        tool_evidence: list[dict[str, Any]] = []
        for row in messages:
            if row["role"] != "assistant" or not row["tool_calls"]:
                continue
            calls = json.loads(row["tool_calls"])
            if not isinstance(calls, list):
                raise RuntimeError("malformed native tool calls")
            for call in calls:
                function = call.get("function", {}) if isinstance(call, dict) else {}
                call_id = call.get("id") or call.get("call_id") if isinstance(call, dict) else None
                result = results.get(call_id)
                if not isinstance(function, dict) or not function.get("name") or result is None:
                    raise RuntimeError("native tool evidence incomplete")
                try:
                    arguments = json.loads(function.get("arguments") or "{}")
                except json.JSONDecodeError as exc:
                    raise RuntimeError("native tool input malformed") from exc
                content = result["content"] or ""
                if result["tool_name"] != function["name"]:
                    raise RuntimeError("native tool name mismatch")
                tool_evidence.append({
                    "tool_name": function["name"],
                    "canonical_input_digest": _canonical_digest(arguments),
                    "exit_status": _tool_exit_status(content),
                    "output_digest": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                })
        outputs = [row["content"] for row in messages if row["role"] == "assistant" and row["content"]]
        if not outputs:
            raise RuntimeError("native session output absent")
        output = outputs[-1]
        session_value = dict(session)
        return {
            "profile": profile,
            "correlation_id": correlation_id,
            "session_ref": f"{state_path}:sessions:{session['id']}",
            "session_digest": _canonical_digest(session_value),
            "exit_status": exit_status,
            "output_digest": hashlib.sha256(output.encode("utf-8")).hexdigest(),
            "gate_status": _native_verdict(profile, output),
            "tool_evidence": tool_evidence,
        }
    except (OSError, sqlite3.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("native evidence read failed") from exc


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
    record_root: Path,
    *,
    identity: dict[str, Any],
    process_runner: Callable[[list[str]], int] | None = None,
) -> dict[str, Any]:
    record_root = Path(record_root)
    if not isinstance(body, bytes):
        raise TypeError("body must be bytes")
    _prune_terminal_cases_if_due(record_root)
    identity = _validate_identity(identity, body)
    if not isinstance(consumer_ref, str) or not consumer_ref or consumer_ref != identity["owner_ref"]:
        raise ValueError("consumer_ref must match identity.owner_ref")
    correlation_id = _canonical_digest(identity)
    argv = _native_argv(consumer_ref, body, correlation_id)
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
        facts.update({
            "native_profile_ref": consumer_ref,
            "native_correlation_id": correlation_id,
            "native_runs": [],
        })
        _append_locked(identity, record_root, consumer_ref, "observed", facts)
    try:
        pid = (process_runner or _background_runner)(_runner_argv(current_path))
    except Exception as exc:
        return append_terminal_receipt(identity, record_root, "blocked", errors=[f"launch:{type(exc).__name__}:{exc}"])
    try:
        # Process creation is a durable state transition.  Do not turn liveness
        # polling into a stream of synthetic heartbeat receipts.
        return _append_observed(identity, record_root, "poll", {"pid": pid})
    except RuntimeError as exc:
        if str(exc) != "terminal receipt already recorded":
            raise
        terminal = poll_external_runtime(identity, record_root)
        if terminal is None:
            raise RuntimeError("terminal receipt disappeared after launch")
        return terminal


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
        native_runs = []
        body_bytes = body_path.read_bytes()
        profiles = (current["external_runtime_receipt"]["consumer_ref"], "anubis", "maat")
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            for profile in profiles:
                argv = _native_argv(profile, body_bytes, facts["native_correlation_id"])
                with body_path.open("rb") as body:
                    process = subprocess.Popen(argv, stdin=body, stdout=stdout, stderr=stderr)
                    exit_code = process.wait()
                run = _native_run_evidence(profile, body_bytes, facts["native_correlation_id"], exit_code)
                native_runs.append(run)
                facts["native_runs"] = list(native_runs)
                facts["exit_code"] = exit_code
                if exit_code != 0 or (profile in {"anubis", "maat"} and run["gate_status"] != "pass"):
                    raise RuntimeError(f"native {profile} verification hold")
            for output in (stdout, stderr):
                output.flush()
                os.fsync(output.fileno())
        status = "pass"
    except Exception as exc:
        status = "blocked"
        errors.append(f"runtime:{type(exc).__name__}:{exc}")
    facts.update(_artifact_facts("stdout", stdout_path, case_dir))
    facts.update(_artifact_facts("stderr", stderr_path, case_dir))
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
            return current
        if alive:
            assert stale_after_seconds is not None
            recorded_at = datetime.fromisoformat(current["recorded_at"])
            age_seconds = (datetime.now(timezone.utc) - recorded_at).total_seconds()
            if age_seconds <= stale_after_seconds:
                return current
            facts["event"] = "blocker"
            return _append_locked(identity, record_root, consumer_ref, "observed", facts, ["runtime:stale"])
        facts["event"] = "blocker"
        return _append_locked(identity, record_root, consumer_ref, "observed", facts, ["runtime:lost"])


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--run-job":
        run_job(Path(sys.argv[2]))
    else:
        raise SystemExit("usage: external_runtime_dispatcher.py --run-job JOB_PATH")
