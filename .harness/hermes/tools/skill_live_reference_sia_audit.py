#!/usr/bin/env python3
"""Collect a bounded, read-only Skill Live Reference C1/C2 delta receipt."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Mapping

SCHEMA = "harness.skill-live-reference.sia-audit-receipt.v2"
STATE_SCHEMA = "harness.skill-live-reference.sia-audit-state.v2"
C1_SCHEMA = "harness.skill-live-reference.c1-result.v1"
C2_SCHEMA = "harness.skill-live-reference.c2-result.v1"
PRODUCER = "skill_live_reference_sia_audit"
_MAX_ARTIFACT_BYTES = 256 * 1024
_MAX_OUTPUT_BYTES = 256 * 1024
_MAX_CONFLICTS = 128
_DEFAULT_TIMEOUT = 15.0
_GBRAIN_BIN_DIRECTORY = "/Users/kann/.bun/bin"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_REVISION = re.compile(r"^[0-9a-f]{40,64}$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._/@+-]{0,255}$")
_INTEGRITY = {"valid", "invalid", "unknown"}
_AVAILABILITY = {"available", "unavailable"}
_CLONE_STATES = {
    "healthy", "missing", "not-a-dir", "no-git", "url-drift", "corrupted", "not-applicable",
}
_RESULT_KEYS = {
    "schema", "result_id", "source_receipt", "availability", "pointer_digest",
    "pointer_integrity", "source_backed_conflicts", "verified_outcome_eligible",
}
_CONFLICT_KEYS = {"conflict_id", "source_receipt", "source_digest"}


class AuditError(RuntimeError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def _digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _identifier(value: Any) -> bool:
    return isinstance(value, str) and _ID.fullmatch(value) is not None


def _run_bounded(argv: list[str], *, cwd: Path, timeout: float, env: Mapping[str, str] | None = None) -> str:
    kwargs: dict[str, Any] = {} if env is None else {"env": env}
    try:
        completed = subprocess.run(
            argv, cwd=cwd, stdin=subprocess.DEVNULL, capture_output=True, text=False,
            timeout=timeout, check=False, shell=False, **kwargs,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        raise AuditError("gbrain_unavailable" if argv[0] != "git" else "canonical_revision_unavailable") from exc
    if len(completed.stdout) > _MAX_OUTPUT_BYTES or len(completed.stderr) > _MAX_OUTPUT_BYTES:
        raise AuditError("bounded_query_output_exceeded")
    if completed.returncode != 0:
        raise AuditError("gbrain_query_failed" if argv[0] != "git" else "canonical_revision_unavailable")
    try:
        return completed.stdout.decode()
    except UnicodeDecodeError as exc:
        raise AuditError("gbrain_malformed_response") from exc


def _canonical_revision(root: Path, timeout: float) -> str:
    revision = _run_bounded(["git", "-C", str(root), "rev-parse", "HEAD"], cwd=root, timeout=timeout).strip()
    if not _REVISION.fullmatch(revision):
        raise AuditError("canonical_revision_unavailable")
    return revision


def _source_status(executable: Path, source_id: str, root: Path, timeout: float) -> dict[str, Any]:
    env = {**os.environ, "PATH": f"{_GBRAIN_BIN_DIRECTORY}:{os.environ.get('PATH', '')}"}
    raw = _run_bounded(
        [str(executable), "call", "sources_status", json.dumps({"id": source_id}, separators=(",", ":"))],
        cwd=root, timeout=timeout, env=env,
    )
    try:
        status = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AuditError("gbrain_malformed_response") from exc
    if not isinstance(status, dict):
        raise AuditError("gbrain_malformed_response")
    required = {"id", "local_path", "last_commit", "clone_state"}
    if not required <= status.keys():
        raise AuditError("gbrain_malformed_response")
    if (
        status["id"] != source_id
        or not isinstance(status["local_path"], str)
        or len(status["local_path"]) > 4096
        or status["last_commit"] is not None and not isinstance(status["last_commit"], str)
        or status["last_commit"] is not None and not _REVISION.fullmatch(status["last_commit"])
        or status["clone_state"] not in _CLONE_STATES
    ):
        raise AuditError("gbrain_malformed_response")
    return status


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _external_state_dir(value: str | Path | None, repo_root: Path, brain_root: Path) -> Path:
    if value is None or not str(value).strip():
        raise ValueError("HARNESS_STATE_DIR is required")
    try:
        state_dir = Path(value).expanduser().resolve(strict=False)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValueError("HARNESS_STATE_DIR is invalid") from exc
    if _inside(state_dir, repo_root) or _inside(state_dir, brain_root):
        raise ValueError("HARNESS_STATE_DIR must be external to harness-starter and harness-brain")
    return state_dir


def _read_json(path: str | Path, reason: str) -> dict[str, Any]:
    artifact = Path(path).expanduser()
    try:
        if artifact.stat().st_size > _MAX_ARTIFACT_BYTES:
            raise AuditError(reason)
        value = json.loads(artifact.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuditError(reason) from exc
    if not isinstance(value, dict):
        raise AuditError(reason)
    return value


def _validate_result(value: dict[str, Any], schema: str, reason: str) -> dict[str, Any]:
    if set(value) != _RESULT_KEYS or value["schema"] != schema:
        raise AuditError(reason)
    if not _identifier(value["result_id"]) or not _identifier(value["source_receipt"]):
        raise AuditError(reason)
    availability = value["availability"]
    pointer_digest = value["pointer_digest"]
    integrity = value["pointer_integrity"]
    eligible = value["verified_outcome_eligible"]
    if availability not in _AVAILABILITY or integrity not in _INTEGRITY:
        raise AuditError(reason)
    if pointer_digest is not None and (not isinstance(pointer_digest, str) or not _HEX64.fullmatch(pointer_digest)):
        raise AuditError(reason)
    if eligible is not None and not isinstance(eligible, bool):
        raise AuditError(reason)
    if availability == "unavailable" and (pointer_digest is not None or integrity != "unknown" or eligible is not None):
        raise AuditError(reason)
    conflicts = value["source_backed_conflicts"]
    if not isinstance(conflicts, list) or len(conflicts) > _MAX_CONFLICTS:
        raise AuditError(reason)
    normalized_conflicts = []
    seen = set()
    for conflict in conflicts:
        if not isinstance(conflict, dict) or set(conflict) != _CONFLICT_KEYS:
            raise AuditError(reason)
        if not _identifier(conflict["conflict_id"]) or not _identifier(conflict["source_receipt"]):
            raise AuditError(reason)
        if not isinstance(conflict["source_digest"], str) or not _HEX64.fullmatch(conflict["source_digest"]):
            raise AuditError(reason)
        key = (conflict["conflict_id"], conflict["source_receipt"], conflict["source_digest"])
        if key in seen:
            raise AuditError(reason)
        seen.add(key)
        normalized_conflicts.append(dict(conflict))
    if availability == "unavailable" and normalized_conflicts:
        raise AuditError(reason)
    return {
        "result_id": value["result_id"],
        "source_receipt": value["source_receipt"],
        "availability": availability,
        "pointer_digest": pointer_digest,
        "pointer_integrity": integrity,
        "source_backed_conflicts": sorted(normalized_conflicts, key=lambda item: tuple(item.values())),
        "verified_outcome_eligible": eligible,
    }


def _semantic(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "availability": result["availability"],
        "pointer_digest": result["pointer_digest"],
        "pointer_integrity": result["pointer_integrity"],
        "source_backed_conflicts": result["source_backed_conflicts"],
        "verified_outcome_eligible": result["verified_outcome_eligible"],
    }


def _state_snapshot(c1: Mapping[str, Any], c2: Mapping[str, Any], canonical: str, projection: str | None,
                    path_matches: bool, clone_state: str) -> dict[str, Any]:
    return {
        "c1": _semantic(c1),
        "c2": _semantic(c2),
        "canonical_revision": canonical,
        "projection_revision": projection,
        "source_local_path_matches": path_matches,
        "clone_state": clone_state,
    }


def _validate_snapshot(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "c1", "c2", "canonical_revision", "projection_revision", "source_local_path_matches", "clone_state"
    }:
        raise AuditError("prior_state_malformed")
    # Reuse the result validator with state-only identifiers added temporarily.
    for key, schema in (("c1", C1_SCHEMA), ("c2", C2_SCHEMA)):
        layer = value[key]
        if not isinstance(layer, dict):
            raise AuditError("prior_state_malformed")
        _validate_result({"schema": schema, "result_id": "state", "source_receipt": "state", **layer}, schema,
                         "prior_state_malformed")
    if not isinstance(value["canonical_revision"], str) or not _REVISION.fullmatch(value["canonical_revision"]):
        raise AuditError("prior_state_malformed")
    projection = value["projection_revision"]
    if projection is not None and (not isinstance(projection, str) or not _REVISION.fullmatch(projection)):
        raise AuditError("prior_state_malformed")
    if not isinstance(value["source_local_path_matches"], bool) or value["clone_state"] not in _CLONE_STATES:
        raise AuditError("prior_state_malformed")
    return value


def _read_prior_state(path: Path, source_id: str) -> tuple[dict[str, Any] | None, str | None, list[str]]:
    if not path.exists():
        return None, None, []
    value = _read_json(path, "prior_state_malformed")
    if set(value) != {"schema", "source_id", "snapshot", "snapshot_digest", "source_receipts"}:
        raise AuditError("prior_state_malformed")
    if value["schema"] != STATE_SCHEMA or value["source_id"] != source_id:
        raise AuditError("prior_state_malformed")
    snapshot = _validate_snapshot(value["snapshot"])
    if value["snapshot_digest"] != _digest(snapshot):
        raise AuditError("prior_state_malformed")
    receipts = value["source_receipts"]
    if not isinstance(receipts, list) or len(receipts) != 2 or any(not _identifier(item) for item in receipts):
        raise AuditError("prior_state_malformed")
    return snapshot, value["snapshot_digest"], receipts


def _conflict_keys(layer: Mapping[str, Any]) -> set[tuple[str, str, str]]:
    return {(item["conflict_id"], item["source_receipt"], item["source_digest"])
            for item in layer["source_backed_conflicts"]}


def _compare(previous: Mapping[str, Any] | None, current: Mapping[str, Any]) -> list[str]:
    classes: set[str] = set()
    if previous is not None:
        for key in ("c1", "c2"):
            before, after = previous[key], current[key]
            if before["pointer_integrity"] != after["pointer_integrity"] or before["pointer_digest"] != after["pointer_digest"]:
                classes.add("pointer_integrity_change")
            if before["verified_outcome_eligible"] != after["verified_outcome_eligible"]:
                classes.add("verified_outcome_eligibility_change")
            old_conflicts, new_conflicts = _conflict_keys(before), _conflict_keys(after)
            if new_conflicts - old_conflicts:
                classes.add("source_backed_conflict_new")
            if old_conflicts - new_conflicts:
                classes.add("source_backed_conflict_resolved")
        if previous["c2"]["availability"] != current["c2"]["availability"]:
            classes.add("honcho_availability_transition")
        if previous["canonical_revision"] != current["canonical_revision"]:
            classes.add("canonical_revision_change")
        if previous["projection_revision"] != current["projection_revision"]:
            classes.add("projection_revision_change")
        if previous["source_local_path_matches"] != current["source_local_path_matches"]:
            classes.add("source_pointer_integrity_change")
        if previous["clone_state"] != current["clone_state"]:
            classes.add("projection_health_change")
    if current["projection_revision"] != current["canonical_revision"]:
        classes.add("projection_canonical_mismatch")
    if not current["source_local_path_matches"] or current["clone_state"] != "healthy":
        classes.add("resolver_audit_issue")
    return sorted(classes)


def _write_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    payload = _canonical_bytes(value)
    try:
        with temporary.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    if path.read_bytes() != payload:
        raise AuditError("artifact_readback_failed")


def _timestamp(now: datetime | None) -> str:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def collect(*, harness_brain_root: str | Path, gbrain_executable: str | Path, source_id: str,
            c1_result_path: str | Path, c2_result_path: str | Path,
            harness_state_dir: str | Path | None = None, timeout: float = _DEFAULT_TIMEOUT,
            now: datetime | None = None) -> tuple[dict[str, Any], int]:
    if not _identifier(source_id):
        raise ValueError("source_id must be a bounded ID")
    if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or not 0 < timeout <= 60:
        raise ValueError("timeout must be greater than zero and at most 60 seconds")
    repo_root = Path(__file__).resolve().parents[3]
    try:
        brain_root = Path(harness_brain_root).expanduser().resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError("harness_brain_root must be an existing directory") from exc
    if not brain_root.is_dir():
        raise ValueError("harness_brain_root must be an existing directory")
    state_dir = _external_state_dir(harness_state_dir, repo_root, brain_root)
    state_path = state_dir / "state.json"
    timestamp = _timestamp(now)
    failure_reason = None
    exit_code = 0
    delta_classes: list[str] = []
    current_digest = None
    previous_digest = None
    source_receipts: list[str] = []
    prior_receipts: list[str] = []
    review_packet = None
    canonical_revision = None
    projection_revision = None
    path_matches = None
    clone_state = None
    try:
        c1 = _validate_result(_read_json(c1_result_path, "c1_result_malformed"), C1_SCHEMA, "c1_result_malformed")
        c2 = _validate_result(_read_json(c2_result_path, "c2_result_malformed"), C2_SCHEMA, "c2_result_malformed")
        source_receipts = [c1["source_receipt"], c2["source_receipt"]]
        canonical_revision = _canonical_revision(brain_root, timeout)
        status = _source_status(Path(gbrain_executable).expanduser(), source_id, brain_root, timeout)
        projection_revision = status["last_commit"]
        try:
            path_matches = Path(status["local_path"]).expanduser().resolve(strict=False) == brain_root
        except (OSError, RuntimeError, ValueError) as exc:
            raise AuditError("gbrain_malformed_response") from exc
        clone_state = status["clone_state"]
        previous, previous_digest, prior_receipts = _read_prior_state(state_path, source_id)
        current = _state_snapshot(c1, c2, canonical_revision, projection_revision, path_matches, clone_state)
        current_digest = _digest(current)
        delta_classes = _compare(previous, current)
        delta = bool(delta_classes)
        if delta and previous_digest is not None:
            review_packet = {
                "before_digest": previous_digest,
                "after_digest": current_digest,
                "source_receipts": sorted(set(prior_receipts + source_receipts)),
            }
        state = {
            "schema": STATE_SCHEMA,
            "source_id": source_id,
            "snapshot": current,
            "snapshot_digest": current_digest,
            "source_receipts": source_receipts,
        }
    except AuditError as exc:
        delta = False
        failure_reason = exc.reason
        exit_code = 2
        state = None

    run_id = hashlib.sha256(_canonical_bytes({
        "source_id": source_id, "timestamp": timestamp, "digest": current_digest, "failure": failure_reason,
    })).hexdigest()[:24]
    receipt_path = state_dir / "receipts" / f"{run_id}.json"
    receipt = {
        "schema": SCHEMA,
        "run_id": run_id,
        "timestamp": timestamp,
        "producer": PRODUCER,
        "source_id": source_id,
        "input_digests": {
            "c1": hashlib.sha256(Path(c1_result_path).read_bytes()).hexdigest() if failure_reason != "c1_result_malformed" else None,
            "c2": hashlib.sha256(Path(c2_result_path).read_bytes()).hexdigest() if failure_reason not in {"c1_result_malformed", "c2_result_malformed"} else None,
        },
        "source_receipts": source_receipts,
        "canonical_revision": canonical_revision,
        "projection_revision": projection_revision,
        "state_before_digest": previous_digest,
        "state_after_digest": current_digest,
        "delta": delta,
        "delta_classes": delta_classes,
        "sia_invoked": False,
        "review_packet": review_packet,
        "failure_reason": failure_reason,
        "receipt_id": f"receipt:{run_id}",
    }
    _write_atomic(receipt_path, receipt)
    if state is not None:
        _write_atomic(state_path, state)
    return receipt, exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness-brain-root", required=True)
    parser.add_argument("--gbrain-executable", required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--c1-result", required=True)
    parser.add_argument("--c2-result", required=True)
    parser.add_argument("--timeout", type=float, default=_DEFAULT_TIMEOUT)
    args = parser.parse_args(argv)
    try:
        receipt, exit_code = collect(
            harness_brain_root=args.harness_brain_root,
            gbrain_executable=args.gbrain_executable,
            source_id=args.source_id,
            c1_result_path=args.c1_result,
            c2_result_path=args.c2_result,
            harness_state_dir=os.environ.get("HARNESS_STATE_DIR"),
            timeout=args.timeout,
        )
    except (AuditError, OSError, ValueError) as exc:
        print(json.dumps({"error": getattr(exc, "reason", str(exc))}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
