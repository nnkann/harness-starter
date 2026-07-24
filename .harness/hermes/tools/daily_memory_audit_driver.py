#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping

TOOLS_DIR = str(Path(__file__).resolve().parent)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)
from daily_memory_pipeline_invariant import LAYER_IDS, validate_layers

INPUT_SCHEMA = "harness.memory.daily-receipt.v1"
RECEIPT_SCHEMA = "harness.memory.daily-dispatch-receipt.v1"
INTENT = "bounded_sia_daily_memory_delta_review"
ARGV = ["hermes", "-p", "sia"]
DELTA_CLASSES = {
    "canonical_source_change",
    "pointer_integrity_transition",
    "canonical_index_alignment_change",
    "verified_outcome_eligibility",
    "layer_availability_transition",
    "new_source_backed_conflict",
    "resolved_source_backed_conflict",
}
ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT = ROOT / ".harness/hermes/state/daily-memory/c2-receipt.json"
DEFAULT_RECEIPT = ROOT / ".harness/hermes/state/daily-memory/c3-dispatch-receipt.json"


class DispatchError(ValueError):
    pass


def canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def _exact_keys(value: Any, keys: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise DispatchError(f"invalid {label}")
    return value


def _bounded_string(value: Any) -> bool:
    return isinstance(value, str) and 0 < len(value) <= 256


def _valid_digest(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _validate_state(value: Any) -> None:
    state = _exact_keys(value, {"collection_ref", "layers"}, "state")
    if not _bounded_string(state["collection_ref"]):
        raise DispatchError("invalid collection_ref")
    layers = state["layers"]
    validate_layers(layers, DispatchError)
    layer_keys = {
        "layer_id", "availability", "canonical_source_ref", "canonical_revision", "pointer_ref",
        "pointer_digest", "pointer_integrity", "canonical_index_ref", "canonical_index_revision",
        "canonical_index_aligned", "verified_outcome_eligible", "source_backed_conflicts",
    }
    seen: set[str] = set()
    for raw in layers:
        layer = _exact_keys(raw, layer_keys, "layer")
        layer_id = layer["layer_id"]
        if not _bounded_string(layer_id) or layer_id in seen or layer["availability"] not in {"available", "unavailable"}:
            raise DispatchError("invalid layer identity")
        seen.add(layer_id)
        for key in ("canonical_source_ref", "canonical_revision", "pointer_ref", "canonical_index_ref", "canonical_index_revision"):
            if layer[key] is not None and not _bounded_string(layer[key]):
                raise DispatchError(f"invalid {key}")
        if layer["pointer_digest"] is not None and not _valid_digest(layer["pointer_digest"]):
            raise DispatchError("invalid pointer_digest")
        if layer["pointer_integrity"] not in {"valid", "invalid", "unknown", None}:
            raise DispatchError("invalid pointer_integrity")
        for key in ("canonical_index_aligned", "verified_outcome_eligible"):
            if layer[key] is not None and not isinstance(layer[key], bool):
                raise DispatchError(f"invalid {key}")
        conflicts = layer["source_backed_conflicts"]
        if not isinstance(conflicts, list) or len(conflicts) > 128:
            raise DispatchError("invalid conflicts")
        for raw_conflict in conflicts:
            conflict = _exact_keys(raw_conflict, {"conflict_ref", "source_digest"}, "conflict")
            if not _bounded_string(conflict["conflict_ref"]) or not _valid_digest(conflict["source_digest"]):
                raise DispatchError("invalid conflict")


def _validate_packet(value: Any, collection_ref: str) -> dict[str, Any]:
    packet = dict(_exact_keys(value, {"intent", "collection_ref", "changes", "packet_digest"}, "packet"))
    if packet["intent"] != INTENT or packet["collection_ref"] != collection_ref:
        raise DispatchError("invalid packet routing")
    changes = packet["changes"]
    if not isinstance(changes, list) or len(changes) != len(LAYER_IDS):
        raise DispatchError("invalid packet changes")
    seen: set[str] = set()
    for raw in changes:
        change = _exact_keys(raw, {"layer_id", "classes"}, "change")
        classes = change["classes"]
        if not _bounded_string(change["layer_id"]) or change["layer_id"] in seen:
            raise DispatchError("invalid change identity")
        if not isinstance(classes, list) or len(classes) != len(set(classes)) or any(item not in DELTA_CLASSES for item in classes):
            raise DispatchError("invalid change classes")
        seen.add(change["layer_id"])
    if seen != LAYER_IDS:
        raise DispatchError("packet changes must contain the exact pipeline layer set")
    body = {key: packet[key] for key in ("intent", "collection_ref", "changes")}
    expected = hashlib.sha256(canonical_bytes(body)).hexdigest()
    if packet["packet_digest"] != expected:
        raise DispatchError("packet digest mismatch")
    return packet


def validate_input(value: Any) -> dict[str, Any] | None:
    receipt = _exact_keys(value, {"schema", "state", "comparison", "consumer"}, "input receipt")
    if receipt["schema"] != INPUT_SCHEMA:
        raise DispatchError("invalid input schema")
    _validate_state(receipt["state"])
    comparison = _exact_keys(receipt["comparison"], {"baseline", "meaningful_delta", "delta_classes", "disposition"}, "comparison")
    consumer = _exact_keys(receipt["consumer"], {"intent", "invocation_count", "packet"}, "consumer")
    classes = comparison["delta_classes"]
    if not isinstance(comparison["baseline"], bool) or not isinstance(comparison["meaningful_delta"], bool):
        raise DispatchError("invalid comparison flags")
    if not isinstance(classes, list) or len(classes) != len(set(classes)) or any(item not in DELTA_CLASSES for item in classes):
        raise DispatchError("invalid delta classes")
    if comparison["meaningful_delta"]:
        if comparison["baseline"] or comparison["disposition"] != "delta" or not classes:
            raise DispatchError("inconsistent delta comparison")
        if consumer["intent"] != INTENT or consumer["invocation_count"] != 1:
            raise DispatchError("invalid delta consumer")
        packet = _validate_packet(consumer["packet"], receipt["state"]["collection_ref"])
        packet_classes = {item for change in packet["changes"] for item in change["classes"]}
        if set(classes) != packet_classes:
            raise DispatchError("packet classes mismatch")
        return packet
    if comparison["disposition"] != "clean" or classes or consumer != {"intent": None, "invocation_count": 0, "packet": None}:
        raise DispatchError("inconsistent clean receipt")
    return None


def atomic_write(value: Mapping[str, Any], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_bytes(value)
    temporary = destination.with_name(destination.name + ".tmp")
    with temporary.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, destination)
    directory_fd = os.open(destination.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    if destination.read_bytes() != payload:
        raise OSError("dispatch receipt readback mismatch")


def _dispatch_receipt(input_digest: str, packet_digest: str, terminal_status: str | None, exit_code: int | None) -> dict[str, Any]:
    return {
        "schema": RECEIPT_SCHEMA,
        "input_receipt_digest": input_digest,
        "packet_digest": packet_digest,
        "actor": "hermes",
        "selector": "sia",
        "argv": ARGV,
        "terminal_status": terminal_status,
        "exit_code": exit_code,
    }


def _validate_dispatch_receipt(value: Any) -> Mapping[str, Any]:
    receipt = _exact_keys(value, {
        "schema", "input_receipt_digest", "packet_digest", "actor", "selector", "argv",
        "terminal_status", "exit_code",
    }, "existing dispatch receipt")
    if (
        receipt["schema"] != RECEIPT_SCHEMA
        or not _valid_digest(receipt["input_receipt_digest"])
        or not _valid_digest(receipt["packet_digest"])
        or receipt["actor"] != "hermes"
        or receipt["selector"] != "sia"
        or receipt["argv"] != ARGV
        or receipt["terminal_status"] not in {"pending", "succeeded", "failed", "unknown"}
        or (receipt["exit_code"] is not None and type(receipt["exit_code"]) is not int)
    ):
        raise DispatchError("invalid existing dispatch receipt")
    status, exit_code = receipt["terminal_status"], receipt["exit_code"]
    if (status in {"pending", "unknown"} and exit_code is not None) or (status == "succeeded" and exit_code != 0):
        raise DispatchError("inconsistent existing dispatch receipt")
    if status == "failed" and exit_code is not None and not 1 <= exit_code <= 255:
        raise DispatchError("inconsistent existing dispatch receipt")
    return receipt


def _normalized_outcome(returncode: int) -> tuple[str, int | None]:
    if returncode == 0:
        return "succeeded", 0
    if 1 <= returncode <= 255:
        return "failed", returncode
    return "failed", None


def run(input_path: str | Path = DEFAULT_INPUT, receipt_path: str | Path = DEFAULT_RECEIPT) -> int:
    source = Path(input_path)
    destination = Path(receipt_path)
    raw = source.read_bytes()
    value = json.loads(raw.decode("utf-8"))
    packet = validate_input(value)
    if packet is None:
        return 0

    input_digest = hashlib.sha256(raw).hexdigest()
    packet_digest = packet["packet_digest"]
    if destination.exists():
        existing = _validate_dispatch_receipt(json.loads(destination.read_text(encoding="utf-8")))
        if existing["packet_digest"] == packet_digest:
            if existing["terminal_status"] == "pending":
                atomic_write(
                    _dispatch_receipt(existing["input_receipt_digest"], packet_digest, "unknown", None),
                    destination,
                )
            return 0

    atomic_write(_dispatch_receipt(input_digest, packet_digest, "pending", None), destination)
    try:
        completed = subprocess.run(
            ARGV,
            input=canonical_bytes(packet),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        atomic_write(_dispatch_receipt(input_digest, packet_digest, "failed", None), destination)
        return 1
    status, exit_code = _normalized_outcome(completed.returncode)
    atomic_write(_dispatch_receipt(input_digest, packet_digest, status, exit_code), destination)
    return exit_code if exit_code is not None else 1


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--receipt", default=str(DEFAULT_RECEIPT))
    args = parser.parse_args()
    try:
        return run(args.input, args.receipt)
    except (DispatchError, OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError):
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
