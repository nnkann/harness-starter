#!/usr/bin/env python3
"""Persisted reducer and local staging boundary for session-close snapshots."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

SCHEMA = "harness.session_close_state.v1"
VERSION = 1
STATES = ("requested", "snapshot_staged", "durable_pending", "propagated", "close_eligible")
_REQUIRED_COMPONENTS = {"session", "database", "transcript", "route"}
_SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:@+-]{0,127}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_GIT_SHA = re.compile(r"[0-9a-f]{40}\Z")
_REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
_REMOTE_REF = re.compile(r"refs/heads/[A-Za-z0-9][A-Za-z0-9._/-]*\Z")
_TOP_LEVEL = {
    "schema", "version", "lifecycle_id", "session_id", "state", "created_at", "updated_at",
    "repo_path", "canonical_target", "snapshot", "durable_receipt", "propagation_receipt",
    "component_close_receipts", "unresolved_holds", "transition_history",
}
_TARGET_FIELDS = {"repository", "remote_ref", "canonical_path"}
_SNAPSHOT_FIELDS = {
    "lifecycle_id", "session_id", "payload", "snapshot_id", "sha256", "byte_length",
    "relative_path", "readback",
}
_READBACK_FIELDS = {"sha256", "byte_length"}
_CANONICAL_TUPLE_FIELDS = {
    "repository", "remote_ref", "canonical_path", "pushed_sha", "snapshot_id",
    "snapshot_sha256", "independent_readback_sha256",
}
_DURABLE_FIELDS = _CANONICAL_TUPLE_FIELDS | {
    "verified_at", "writer_identity", "reader_identity", "receipt_hash",
}
_PROPAGATION_FIELDS = _CANONICAL_TUPLE_FIELDS | {
    "durable_receipt_hash", "propagated_at", "propagator_identity", "reader_identity",
    "receipt_hash",
}
_COMPONENT_FIELDS = {
    "component", "status", "lifecycle_id", "session_id", "snapshot_id", "snapshot_sha256",
    "verified_at",
}
_HISTORY_FIELDS = {
    "sequence", "from_state", "to_state", "transitioned_at", "previous_transition_hash",
    "transition_hash",
}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
        return True
    except ValueError:
        return False


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value[:-1] + "+00:00")


def _exact_fields(value: Any, fields: set[str], name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(f"{name} fields do not match schema")
    return value


def _validate_id(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise ValueError(f"{name} must be a path-safe identifier")
    return value


def _validate_relative_path(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be repo-relative")
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in ("", ".", "..") for part in value.split("/")):
        raise ValueError(f"{name} must be repo-relative")
    return value


def _validate_target(value: Any) -> dict[str, Any]:
    target = _exact_fields(value, _TARGET_FIELDS, "canonical_target")
    repository = str(target["repository"])
    if not _REPOSITORY.fullmatch(repository) or any(part in (".", "..") for part in repository.split("/")):
        raise ValueError("canonical target repository must be owner/name")
    remote_ref = str(target["remote_ref"])
    if not _REMOTE_REF.fullmatch(remote_ref) or any(part in (".", "..") for part in remote_ref.split("/")):
        raise ValueError("canonical target remote_ref must be a refs/heads/* ref")
    canonical_path = _validate_relative_path(target["canonical_path"], "canonical target canonical_path")
    if "session_close_staging" in canonical_path.split("/"):
        raise ValueError("canonical target cannot use session_close_staging")
    return target


def _repo_path(state: Mapping[str, Any]) -> Path:
    value = state.get("repo_path")
    if not isinstance(value, str) or not Path(value).is_absolute():
        raise ValueError("repo_path must be absolute")
    return Path(value).resolve()


def _staging_root(repo: Path) -> Path:
    root = repo / ".harness/project/runs/session_close_staging"
    current = repo
    for part in (".harness", "project", "runs", "session_close_staging"):
        current = current / part
        if current.is_symlink():
            raise ValueError("staging path substitution is not allowed")
    root.mkdir(parents=True, exist_ok=True)
    if root.is_symlink() or root.resolve() != root:
        raise ValueError("staging root must be an in-repo directory")
    return root


def _lifecycle_dir(state: Mapping[str, Any], create: bool = False) -> Path:
    root = _staging_root(_repo_path(state))
    directory = root / _validate_id(state.get("lifecycle_id"), "lifecycle_id")
    if directory.is_symlink():
        raise ValueError("lifecycle path substitution is not allowed")
    if create:
        directory.mkdir(mode=0o700)
    if directory.resolve() != directory or directory.parent.resolve() != root:
        raise ValueError("lifecycle directory escaped staging root")
    return directory


def _state_path(state: Mapping[str, Any]) -> Path:
    return _lifecycle_dir(state) / "state.json"


def _transition_hash(entry: Mapping[str, Any]) -> str:
    return _sha256({key: entry[key] for key in _HISTORY_FIELDS if key != "transition_hash"})


def _append_transition(state: dict[str, Any], to_state: str) -> None:
    history = state["transition_history"]
    entry = {
        "sequence": len(history),
        "from_state": history[-1]["to_state"] if history else None,
        "to_state": to_state,
        "transitioned_at": _now(),
        "previous_transition_hash": history[-1]["transition_hash"] if history else None,
    }
    entry["transition_hash"] = _transition_hash(entry)
    history.append(entry)
    state["state"] = to_state
    state["updated_at"] = entry["transitioned_at"]


def _receipt_hash(receipt: Mapping[str, Any]) -> str:
    return _sha256({key: value for key, value in receipt.items() if key != "receipt_hash"})


def _canonical_tuple(state: Mapping[str, Any], pushed_sha: str) -> dict[str, Any]:
    snapshot = state["snapshot"]
    return {
        "repository": state["canonical_target"]["repository"],
        "remote_ref": state["canonical_target"]["remote_ref"],
        "pushed_sha": pushed_sha,
        "canonical_path": state["canonical_target"]["canonical_path"],
        "snapshot_id": snapshot["snapshot_id"],
        "snapshot_sha256": snapshot["sha256"],
        "independent_readback_sha256": snapshot["readback"]["sha256"],
    }


def _candidate_path(state: Mapping[str, Any]) -> Path:
    snapshot = state["snapshot"]
    relative_path = _validate_relative_path(snapshot["relative_path"], "snapshot relative_path")
    candidate = _repo_path(state) / relative_path
    expected = _lifecycle_dir(state) / f"{snapshot['snapshot_id']}.json"
    if candidate.is_symlink() or candidate.resolve() != expected:
        raise ValueError("candidate identity or path does not match state")
    return candidate


def _rehash_candidate(state: Mapping[str, Any]) -> None:
    if STATES.index(state["state"]) < STATES.index("snapshot_staged"):
        return
    snapshot = state["snapshot"]
    candidate = _candidate_path(state)
    payload = candidate.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if (
        payload != _canonical_bytes(snapshot["payload"])
        or digest != snapshot["sha256"]
        or digest != snapshot["snapshot_id"]
        or len(payload) != snapshot["byte_length"]
    ):
        raise ValueError("candidate readback does not match canonical snapshot")
    if STATES.index(state["state"]) >= STATES.index("durable_pending") and snapshot["readback"] != {
        "sha256": digest, "byte_length": len(payload)
    }:
        raise ValueError("nested snapshot readback identity is invalid")


def _read_persisted(state: Mapping[str, Any]) -> dict[str, Any] | None:
    path = _state_path(state)
    if not path.exists():
        return None
    raw = path.read_bytes()
    persisted = json.loads(raw.decode("utf-8"))
    validated = _validate_state(persisted)
    _rehash_candidate(validated)
    if raw != _canonical_bytes(validated):
        raise ValueError("persisted state is not canonical JSON")
    return validated


def _assert_persisted_prefix(old: Mapping[str, Any], new: Mapping[str, Any]) -> None:
    history = new["transition_history"]
    if history[:len(old["transition_history"])] != old["transition_history"]:
        raise ValueError("persisted transition history prefix is immutable")
    if old["canonical_target"] != new["canonical_target"]:
        raise ValueError("persisted canonical target is immutable")
    for field in ("lifecycle_id", "session_id", "payload", "snapshot_id", "sha256", "byte_length", "relative_path"):
        if old["snapshot"][field] is not None and old["snapshot"][field] != new["snapshot"][field]:
            raise ValueError("persisted snapshot evidence is immutable")
    for field in ("sha256", "byte_length"):
        if old["snapshot"]["readback"][field] is not None and old["snapshot"]["readback"][field] != new["snapshot"]["readback"][field]:
            raise ValueError("persisted readback evidence is immutable")
    for field in ("durable_receipt", "propagation_receipt"):
        if old[field] is not None and old[field] != new[field]:
            raise ValueError(f"persisted {field} is immutable")
    if new["component_close_receipts"][:len(old["component_close_receipts"])] != old["component_close_receipts"]:
        raise ValueError("persisted component evidence prefix is immutable")


def _write_state(state: Mapping[str, Any]) -> None:
    validated = load_and_validate_state(state)
    old = _read_persisted(validated)
    if old is not None:
        _assert_persisted_prefix(old, validated)
    _state_path(validated).write_bytes(_canonical_bytes(validated))


def _require_state(state: Mapping[str, Any], expected: str) -> dict[str, Any]:
    current = load_and_validate_state(state)
    persisted = _read_persisted(current)
    if persisted is None or persisted != current:
        raise ValueError("reducer input must match immutable persisted state")
    if current["state"] != expected:
        raise ValueError(f"expected state {expected}, got {current['state']}")
    return current


def request_close(
    repo: Path | str,
    lifecycle_id: str,
    snapshot: Mapping[str, Any],
    canonical_target: Mapping[str, Any],
) -> dict[str, Any]:
    lifecycle_id = _validate_id(lifecycle_id, "lifecycle_id")
    payload = copy.deepcopy(dict(snapshot))
    session_id = _validate_id(payload.get("session_id"), "session_id")
    target = copy.deepcopy(_validate_target(dict(canonical_target)))
    holds = payload.get("unresolved_holds", [])
    if not isinstance(holds, list) or not all(isinstance(item, str) for item in holds):
        raise ValueError("unresolved_holds must contain strings")
    timestamp = _now()
    state = {
        "schema": SCHEMA,
        "version": VERSION,
        "lifecycle_id": lifecycle_id,
        "session_id": session_id,
        "state": "requested",
        "created_at": timestamp,
        "updated_at": timestamp,
        "repo_path": str(Path(repo).resolve()),
        "canonical_target": target,
        "snapshot": {
            "lifecycle_id": lifecycle_id,
            "session_id": session_id,
            "payload": payload,
            "snapshot_id": None,
            "sha256": None,
            "byte_length": None,
            "relative_path": None,
            "readback": {"sha256": None, "byte_length": None},
        },
        "durable_receipt": None,
        "propagation_receipt": None,
        "component_close_receipts": [],
        "unresolved_holds": copy.deepcopy(holds),
        "transition_history": [],
    }
    _append_transition(state, "requested")
    state["created_at"] = state["transition_history"][0]["transitioned_at"]
    validated = load_and_validate_state(state)
    _lifecycle_dir(validated, create=True)
    _write_state(validated)
    return validated


def stage_snapshot(state: Mapping[str, Any]) -> dict[str, Any]:
    current = _require_state(state, "requested")
    payload = _canonical_bytes(current["snapshot"]["payload"])
    digest = hashlib.sha256(payload).hexdigest()
    candidate = _lifecycle_dir(current) / f"{digest}.json"
    if candidate.is_symlink():
        raise ValueError("candidate path substitution is not allowed")
    with candidate.open("xb") as handle:
        handle.write(payload)
        handle.flush()
    updated = copy.deepcopy(current)
    updated["snapshot"].update({
        "snapshot_id": digest,
        "sha256": digest,
        "byte_length": len(payload),
        "relative_path": candidate.relative_to(_repo_path(current)).as_posix(),
    })
    _append_transition(updated, "snapshot_staged")
    _write_state(updated)
    return updated


def verify_snapshot_readback(state: Mapping[str, Any]) -> dict[str, Any]:
    current = _require_state(state, "snapshot_staged")
    candidate = _candidate_path(current)
    readback = candidate.read_bytes()
    digest = hashlib.sha256(readback).hexdigest()
    snapshot = current["snapshot"]
    if readback != _canonical_bytes(snapshot["payload"]) or digest != snapshot["sha256"] or len(readback) != snapshot["byte_length"]:
        raise ValueError("candidate readback does not match canonical snapshot")
    updated = copy.deepcopy(current)
    updated["snapshot"]["readback"] = {"sha256": digest, "byte_length": len(readback)}
    _append_transition(updated, "durable_pending")
    _write_state(updated)
    return updated


def _validate_canonical_receipt_tuple(
    receipt: Mapping[str, Any],
    state: Mapping[str, Any],
    expected: Mapping[str, Any] | None = None,
) -> None:
    pushed_sha = receipt.get("pushed_sha")
    if not isinstance(pushed_sha, str) or not _GIT_SHA.fullmatch(pushed_sha):
        raise ValueError("pushed_sha must be a full git SHA")
    expected_tuple = _canonical_tuple(state, pushed_sha) if expected is None else {
        field: expected[field] for field in _CANONICAL_TUPLE_FIELDS
    }
    if {field: receipt.get(field) for field in _CANONICAL_TUPLE_FIELDS} != expected_tuple:
        raise ValueError("receipt canonical tuple mismatch")


def _validate_durable(receipt: Any, state: Mapping[str, Any]) -> dict[str, Any]:
    value = _exact_fields(receipt, _DURABLE_FIELDS, "durable_receipt")
    _validate_canonical_receipt_tuple(value, state)
    if not _valid_timestamp(value["verified_at"]):
        raise ValueError("verified_at must be an RFC3339 UTC timestamp")
    if (
        not isinstance(value["writer_identity"], str)
        or not isinstance(value["reader_identity"], str)
        or not value["writer_identity"]
        or not value["reader_identity"]
        or value["writer_identity"] == value["reader_identity"]
    ):
        raise ValueError("durable readback must use a distinct reader")
    if value["receipt_hash"] != _receipt_hash(value):
        raise ValueError("durable receipt hash mismatch")
    return value


def record_durable_receipt(state: Mapping[str, Any], receipt: Mapping[str, Any]) -> dict[str, Any]:
    current = _require_state(state, "durable_pending")
    if current["durable_receipt"] is not None:
        raise ValueError("durable receipt is append-only")
    value = copy.deepcopy(dict(receipt))
    if set(value) != _DURABLE_FIELDS - {"receipt_hash"}:
        raise ValueError("durable_receipt fields do not match schema")
    value["receipt_hash"] = _receipt_hash(value)
    _validate_durable(value, current)
    updated = copy.deepcopy(current)
    updated["durable_receipt"] = value
    updated["updated_at"] = _now()
    _write_state(updated)
    return updated


def _validate_propagation(receipt: Any, state: Mapping[str, Any]) -> dict[str, Any]:
    value = _exact_fields(receipt, _PROPAGATION_FIELDS, "propagation_receipt")
    durable = state["durable_receipt"]
    _validate_canonical_receipt_tuple(value, state, durable)
    if value["durable_receipt_hash"] != durable["receipt_hash"]:
        raise ValueError("propagation durable evidence mismatch")
    if (
        not _valid_timestamp(value["propagated_at"])
        or not isinstance(value["propagator_identity"], str)
        or not isinstance(value["reader_identity"], str)
        or not value["propagator_identity"]
        or not value["reader_identity"]
        or value["reader_identity"] in {durable["writer_identity"], value["propagator_identity"]}
    ):
        raise ValueError("propagation requires an independent canonical reader")
    if value["receipt_hash"] != _receipt_hash(value):
        raise ValueError("propagation receipt hash mismatch")
    return value


def record_propagation_receipt(state: Mapping[str, Any], receipt: Mapping[str, Any]) -> dict[str, Any]:
    current = _require_state(state, "durable_pending")
    if current["durable_receipt"] is None or current["propagation_receipt"] is not None:
        raise ValueError("one durable receipt must precede propagation")
    value = copy.deepcopy(dict(receipt))
    if set(value) != _PROPAGATION_FIELDS - {"receipt_hash"}:
        raise ValueError("propagation_receipt fields do not match schema")
    value["receipt_hash"] = _receipt_hash(value)
    _validate_propagation(value, current)
    updated = copy.deepcopy(current)
    updated["propagation_receipt"] = value
    _append_transition(updated, "propagated")
    _write_state(updated)
    return updated


def _validate_components(receipts: Any, state: Mapping[str, Any], require_all: bool) -> list[dict[str, Any]]:
    if not isinstance(receipts, list):
        raise ValueError("component_close_receipts must be a list")
    seen = set()
    for receipt in receipts:
        value = _exact_fields(receipt, _COMPONENT_FIELDS, "component receipt")
        component = value["component"]
        if component not in _REQUIRED_COMPONENTS or component in seen or value["status"] != "preserved":
            raise ValueError("component receipt is malformed or duplicated")
        if (
            value["lifecycle_id"] != state["lifecycle_id"]
            or value["session_id"] != state["session_id"]
            or value["snapshot_id"] != state["snapshot"]["snapshot_id"]
            or value["snapshot_sha256"] != state["snapshot"]["sha256"]
            or not _valid_timestamp(value["verified_at"])
        ):
            raise ValueError("component receipt identity mismatch")
        seen.add(component)
    if require_all and seen != _REQUIRED_COMPONENTS:
        raise ValueError("all component receipts are required")
    return receipts


def mark_close_eligible(state: Mapping[str, Any], component_receipts: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
    current = _require_state(state, "propagated")
    if current["unresolved_holds"]:
        raise ValueError("unresolved holds prevent close eligibility")
    receipts = copy.deepcopy(list(component_receipts))
    _validate_components(receipts, current, True)
    updated = copy.deepcopy(current)
    updated["component_close_receipts"] = receipts
    _append_transition(updated, "close_eligible")
    _write_state(updated)
    return updated


def mark_prune_eligible(state: Mapping[str, Any]) -> bool:
    if isinstance(state, Mapping):
        _rehash_candidate(state)
    try:
        current = load_and_validate_state(state)
        persisted = _read_persisted(current)
        return persisted == current and current["state"] == "close_eligible" and {
            receipt["component"] for receipt in current["component_close_receipts"]
        } == _REQUIRED_COMPONENTS
    except ValueError:
        return False


def _validate_history(state: Mapping[str, Any]) -> None:
    history = state["transition_history"]
    expected_states = STATES[:STATES.index(state["state"]) + 1]
    if len(history) != len(expected_states):
        raise ValueError("transition history does not match current state")
    previous_hash = None
    previous_state = None
    previous_time = None
    for sequence, (entry, expected_state) in enumerate(zip(history, expected_states)):
        _exact_fields(entry, _HISTORY_FIELDS, "transition history entry")
        if entry["sequence"] != sequence or entry["from_state"] != previous_state or entry["to_state"] != expected_state or entry["previous_transition_hash"] != previous_hash:
            raise ValueError("transition history is not append-only sequential history")
        if not _valid_timestamp(entry["transitioned_at"]) or entry["transition_hash"] != _transition_hash(entry):
            raise ValueError("transition history hash or timestamp is invalid")
        transitioned_at = _timestamp(entry["transitioned_at"])
        if previous_time is not None and transitioned_at <= previous_time:
            raise ValueError("transition history timestamps are not strictly increasing")
        previous_hash = entry["transition_hash"]
        previous_state = expected_state
        previous_time = transitioned_at
    if state["created_at"] != history[0]["transitioned_at"] or _timestamp(state["updated_at"]) < _timestamp(history[-1]["transitioned_at"]):
        raise ValueError("state timestamps do not match history")


def _validate_snapshot(state: Mapping[str, Any]) -> None:
    snapshot = _exact_fields(state["snapshot"], _SNAPSHOT_FIELDS, "snapshot")
    readback = _exact_fields(snapshot["readback"], _READBACK_FIELDS, "snapshot readback")
    if snapshot["lifecycle_id"] != state["lifecycle_id"] or snapshot["session_id"] != state["session_id"] or not isinstance(snapshot["payload"], dict):
        raise ValueError("snapshot identity mismatch")
    if snapshot["payload"].get("session_id") != state["session_id"] or snapshot["payload"].get("unresolved_holds", []) != state["unresolved_holds"]:
        raise ValueError("snapshot payload identity mismatch")
    index = STATES.index(state["state"])
    identity = (snapshot["snapshot_id"], snapshot["sha256"], snapshot["byte_length"], snapshot["relative_path"])
    if index == 0:
        if identity != (None, None, None, None) or readback != {"sha256": None, "byte_length": None}:
            raise ValueError("requested snapshot cannot have staged identity")
        return
    payload = _canonical_bytes(snapshot["payload"])
    digest = hashlib.sha256(payload).hexdigest()
    expected_path = Path(".harness/project/runs/session_close_staging") / state["lifecycle_id"] / f"{digest}.json"
    if snapshot["snapshot_id"] != digest or snapshot["sha256"] != digest or snapshot["byte_length"] != len(payload) or Path(snapshot["relative_path"]) != expected_path:
        raise ValueError("snapshot canonical identity is invalid")
    if index == 1:
        if readback != {"sha256": None, "byte_length": None}:
            raise ValueError("staged snapshot cannot claim readback")
    elif readback != {"sha256": digest, "byte_length": len(payload)}:
        raise ValueError("snapshot readback identity is invalid")


def _validate_state(state: dict[str, Any]) -> dict[str, Any]:
    _exact_fields(state, _TOP_LEVEL, "state")
    if state["schema"] != SCHEMA or state["version"] != VERSION or state["state"] not in STATES:
        raise ValueError("unsupported session-close state")
    _validate_id(state["lifecycle_id"], "lifecycle_id")
    _validate_id(state["session_id"], "session_id")
    _repo_path(state)
    _validate_target(state["canonical_target"])
    if not _valid_timestamp(state["created_at"]) or not _valid_timestamp(state["updated_at"]):
        raise ValueError("state timestamps are invalid")
    if not isinstance(state["unresolved_holds"], list) or not all(isinstance(item, str) for item in state["unresolved_holds"]):
        raise ValueError("unresolved_holds must contain strings")
    if not isinstance(state["transition_history"], list) or not state["transition_history"]:
        raise ValueError("transition_history is required")
    _validate_history(state)
    _validate_snapshot(state)
    if state["durable_receipt"] is not None:
        _validate_durable(state["durable_receipt"], state)
    if state["propagation_receipt"] is not None:
        if state["durable_receipt"] is None:
            raise ValueError("propagation requires durable receipt")
        _validate_propagation(state["propagation_receipt"], state)
    _validate_components(state["component_close_receipts"], state, state["state"] == "close_eligible")
    if state["state"] != "close_eligible" and state["component_close_receipts"]:
        raise ValueError("component receipts appear before close eligibility")
    index = STATES.index(state["state"])
    if index < STATES.index("durable_pending") and state["durable_receipt"] is not None:
        raise ValueError("durable receipt appears before durable_pending")
    if index < STATES.index("propagated") and state["propagation_receipt"] is not None:
        raise ValueError("propagation receipt appears before propagated")
    if index >= STATES.index("propagated") and (state["durable_receipt"] is None or state["propagation_receipt"] is None):
        raise ValueError("propagated state lacks receipts")
    if state["state"] == "close_eligible" and state["unresolved_holds"]:
        raise ValueError("close_eligible state contains unresolved holds")
    return state


def load_and_validate_state(source: Mapping[str, Any] | Path | str, lifecycle_id: str | None = None) -> dict[str, Any]:
    raw = None
    if isinstance(source, Mapping):
        state = copy.deepcopy(dict(source))
    else:
        source_path = Path(source)
        if lifecycle_id is None:
            if source_path.name != "state.json":
                raise ValueError("lifecycle_id is required when loading from a repo")
            path = source_path
        else:
            probe = {"repo_path": str(source_path.resolve()), "lifecycle_id": _validate_id(lifecycle_id, "lifecycle_id")}
            path = _lifecycle_dir(probe) / "state.json"
        raw = path.read_bytes()
        state = json.loads(raw.decode("utf-8"))
    validated = _validate_state(state)
    _rehash_candidate(validated)
    if raw is not None and raw != _canonical_bytes(validated):
        raise ValueError("persisted state is not canonical JSON")
    return validated
