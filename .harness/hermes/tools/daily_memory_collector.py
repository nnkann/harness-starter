#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping

TOOLS_DIR = str(Path(__file__).resolve().parent)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)
from daily_memory_pipeline_invariant import LAYER_IDS, validate_layers

SCHEMA = "harness.memory.daily-receipt.v1"
DECLARATION_SCHEMA = "harness.memory.daily-declaration.v1"
MEANINGFUL_DELTA_CLASSES = (
    "canonical_source_change",
    "pointer_integrity_transition",
    "canonical_index_alignment_change",
    "verified_outcome_eligibility",
    "layer_availability_transition",
    "new_source_backed_conflict",
    "resolved_source_backed_conflict",
)
_MAX_CONFLICTS = 128
_MAX_REF_LENGTH = 256


class CollectorError(ValueError):
    pass


def _require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or len(value) > _MAX_REF_LENGTH:
        raise CollectorError(f"{label} must be a bounded non-empty string")
    return value


def _optional_string(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return _require_string(value, label)


def _optional_bool(value: Any, label: str) -> bool | None:
    if value is not None and not isinstance(value, bool):
        raise CollectorError(f"{label} must be boolean or null")
    return value


def _digest(value: Any, label: str) -> str | None:
    value = _optional_string(value, label)
    if value is not None and (len(value) != 64 or any(char not in "0123456789abcdef" for char in value)):
        raise CollectorError(f"{label} must be a lowercase sha256 digest")
    return value


def _normalize_conflicts(value: Any, layer_id: str) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > _MAX_CONFLICTS:
        raise CollectorError(f"{layer_id}.conflicts must be a bounded array")
    conflicts: dict[str, dict[str, str]] = {}
    for item in value:
        if not isinstance(item, Mapping):
            raise CollectorError(f"{layer_id}.conflicts entries must be objects")
        conflict_ref = _require_string(item.get("conflict_ref"), "conflict_ref")
        source_digest = _digest(item.get("source_digest"), "source_digest")
        if source_digest is not None:
            conflicts[conflict_ref] = {"conflict_ref": conflict_ref, "source_digest": source_digest}
    return [conflicts[key] for key in sorted(conflicts)]


def normalize_declaration(declaration: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(declaration, Mapping) or declaration.get("schema") != DECLARATION_SCHEMA:
        raise CollectorError("invalid daily declaration schema")
    collection_ref = _require_string(declaration.get("collection_ref"), "collection_ref")
    raw_layers = declaration.get("layers")
    validate_layers(raw_layers, CollectorError)

    layers: dict[str, dict[str, Any]] = {}
    for raw in raw_layers:
        if not isinstance(raw, Mapping):
            raise CollectorError("layer must be an object")
        layer_id = _require_string(raw.get("layer_id"), "layer_id")
        if layer_id in layers:
            raise CollectorError("layer_id must be unique")
        availability = raw.get("availability")
        pointer_integrity = raw.get("pointer_integrity")
        layers[layer_id] = {
            "layer_id": layer_id,
            "availability": availability,
            "canonical_source_ref": _optional_string(raw.get("canonical_source_ref"), "canonical_source_ref"),
            "canonical_revision": _optional_string(raw.get("canonical_revision"), "canonical_revision"),
            "pointer_ref": _optional_string(raw.get("pointer_ref"), "pointer_ref"),
            "pointer_digest": _digest(raw.get("pointer_digest"), "pointer_digest"),
            "pointer_integrity": pointer_integrity,
            "canonical_index_ref": _optional_string(raw.get("canonical_index_ref"), "canonical_index_ref"),
            "canonical_index_revision": _optional_string(raw.get("canonical_index_revision"), "canonical_index_revision"),
            "canonical_index_aligned": _optional_bool(raw.get("canonical_index_aligned"), "canonical_index_aligned"),
            "verified_outcome_eligible": _optional_bool(raw.get("verified_outcome_eligible"), "verified_outcome_eligible"),
            "source_backed_conflicts": _normalize_conflicts(
                raw.get("conflicts", raw.get("source_backed_conflicts")), layer_id
            ),
        }
    normalized = {"collection_ref": collection_ref, "layers": [layers[key] for key in sorted(layers)]}
    validate_layers(normalized["layers"], CollectorError)
    return normalized


def _prior_state(prior_receipt: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if prior_receipt is None:
        return None
    if not isinstance(prior_receipt, Mapping) or prior_receipt.get("schema") != SCHEMA:
        raise CollectorError("prior receipt has invalid schema")
    state = prior_receipt.get("state")
    if not isinstance(state, Mapping) or not isinstance(state.get("layers"), list):
        raise CollectorError("prior receipt has invalid state")
    return normalize_declaration({"schema": DECLARATION_SCHEMA, **state})


def _classify(previous: Mapping[str, Any], current: Mapping[str, Any]) -> list[str]:
    classes = []
    if any(previous.get(key) != current.get(key) for key in ("canonical_source_ref", "canonical_revision")):
        classes.append("canonical_source_change")
    if previous.get("pointer_integrity") != current.get("pointer_integrity"):
        classes.append("pointer_integrity_transition")
    if any(previous.get(key) != current.get(key) for key in (
        "canonical_index_ref", "canonical_index_revision", "canonical_index_aligned"
    )):
        classes.append("canonical_index_alignment_change")
    if previous.get("verified_outcome_eligible") != current.get("verified_outcome_eligible"):
        classes.append("verified_outcome_eligibility")
    if previous.get("availability") != current.get("availability"):
        classes.append("layer_availability_transition")

    old_conflicts = {item["conflict_ref"]: item["source_digest"] for item in previous["source_backed_conflicts"]}
    new_conflicts = {item["conflict_ref"]: item["source_digest"] for item in current["source_backed_conflicts"]}
    if new_conflicts.keys() - old_conflicts.keys() or any(
        ref in old_conflicts and old_conflicts[ref] != digest for ref, digest in new_conflicts.items()
    ):
        classes.append("new_source_backed_conflict")
    if old_conflicts.keys() - new_conflicts.keys():
        classes.append("resolved_source_backed_conflict")
    return classes


def _delta(previous: dict[str, Any] | None, current: dict[str, Any]) -> list[dict[str, Any]]:
    if previous is None:
        return []
    old_layers = {layer["layer_id"]: layer for layer in previous["layers"]}
    changes = []
    for layer in current["layers"]:
        prior = old_layers.get(layer["layer_id"])
        classes = ["layer_availability_transition"] if prior is None else _classify(prior, layer)
        if classes:
            changes.append({"layer_id": layer["layer_id"], "classes": classes})
    for layer_id in sorted(old_layers.keys() - {layer["layer_id"] for layer in current["layers"]}):
        changes.append({"layer_id": layer_id, "classes": ["layer_availability_transition"]})
    return changes


def canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def collect(declaration: Mapping[str, Any], prior_receipt: Mapping[str, Any] | None = None) -> dict[str, Any]:
    state = normalize_declaration(declaration)
    previous = _prior_state(prior_receipt)
    changes = _delta(previous, state)
    meaningful_delta = bool(changes)
    packet = None
    if meaningful_delta:
        classes_by_layer = {change["layer_id"]: change["classes"] for change in changes}
        packet_body = {
            "intent": "bounded_sia_daily_memory_delta_review",
            "collection_ref": state["collection_ref"],
            "changes": [
                {"layer_id": layer_id, "classes": classes_by_layer.get(layer_id, [])}
                for layer_id in sorted(LAYER_IDS)
            ],
        }
        packet = {**packet_body, "packet_digest": hashlib.sha256(canonical_bytes(packet_body)).hexdigest()}
    return {
        "schema": SCHEMA,
        "state": state,
        "comparison": {
            "baseline": previous is None,
            "meaningful_delta": meaningful_delta,
            "delta_classes": sorted({name for change in changes for name in change["classes"]}),
            "disposition": "delta" if meaningful_delta else "clean",
        },
        "consumer": {
            "intent": "bounded_sia_daily_memory_delta_review" if meaningful_delta else None,
            "invocation_count": 1 if meaningful_delta else 0,
            "packet": packet,
        },
    }


def write_receipt(receipt: Mapping[str, Any], path: str | Path) -> dict[str, Any]:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_bytes(receipt)
    temporary = destination.with_name(destination.name + ".tmp")
    with temporary.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, destination)
    readback = destination.read_bytes()
    expected = hashlib.sha256(payload).hexdigest()
    actual = hashlib.sha256(readback).hexdigest()
    if readback != payload or actual != expected:
        raise OSError("receipt readback verification failed")
    return {"receipt_sha256": actual, "bytes": len(readback), "readback_verified": True}


def run(declaration_path: str | Path, receipt_path: str | Path, prior_path: str | Path | None = None) -> dict[str, Any]:
    declaration = json.loads(Path(declaration_path).read_text(encoding="utf-8"))
    prior = json.loads(Path(prior_path).read_text(encoding="utf-8")) if prior_path else None
    receipt = collect(declaration, prior)
    return {"receipt": receipt, "write_verification": write_receipt(receipt, receipt_path)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect normalized daily memory state into a deterministic receipt")
    parser.add_argument("declaration")
    parser.add_argument("receipt")
    parser.add_argument("--prior")
    args = parser.parse_args()
    result = run(args.declaration, args.receipt, args.prior)
    print(json.dumps(result["write_verification"], sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
