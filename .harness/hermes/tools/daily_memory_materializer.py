#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Mapping
from zoneinfo import ZoneInfo

TOOLS_DIR = str(Path(__file__).resolve().parent)
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)
from daily_memory_pipeline_invariant import validate_layers

SCHEMA = "harness.memory.daily-declaration.v1"
SEOUL = ZoneInfo("Asia/Seoul")
ROOT = Path("/Users/kann/projects/harness-starter")
EQUATION = Path("/Users/kann/projects/harness-brain/projects/harness-starter/decisions/cps-equation-ssot.md")
HANDOFF = Path("/Users/kann/projects/harness-brain/projects/harness-starter/handoffs/2026-07-24-sia-memory-stewardship-operating-contract.md")
MANIFEST = ROOT / "manifest.yml"
CANONICAL_INPUTS = (EQUATION, HANDOFF, MANIFEST)
DECLARATION_KEYS = {"schema", "collection_ref", "materialized_date", "layers"}
LAYER_KEYS = {
    "layer_id",
    "availability",
    "canonical_source_ref",
    "canonical_revision",
    "pointer_ref",
    "pointer_digest",
    "pointer_integrity",
    "canonical_index_ref",
    "canonical_index_revision",
    "canonical_index_aligned",
    "verified_outcome_eligible",
    "conflicts",
}



class MaterializationError(ValueError):
    pass


def canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def _read_bounded(path: Path, limit: int = 1_000_000) -> tuple[bytes, str]:
    try:
        size = path.stat().st_size
    except OSError as error:
        raise MaterializationError(f"unavailable canonical input: {path}") from error
    if size <= 0 or size > limit:
        raise MaterializationError(f"canonical input outside bounded size: {path}")
    payload = path.read_bytes()
    if len(payload) != size:
        raise MaterializationError(f"canonical input changed during read: {path}")
    return payload, hashlib.sha256(payload).hexdigest()


def _line_present(payload: bytes, expected: str) -> bool:
    try:
        lines = payload.decode("utf-8").splitlines()
    except UnicodeDecodeError as error:
        raise MaterializationError("canonical input is not UTF-8") from error
    return expected in lines


def _available_layer(
    layer_id: str,
    source: Path,
    source_digest: str,
    pointer: Path,
    pointer_digest: str,
    pointer_valid: bool,
    index: Path,
    index_digest: str,
    index_aligned: bool,
) -> dict[str, Any]:
    return {
        "layer_id": layer_id,
        "availability": "available",
        "canonical_source_ref": str(source),
        "canonical_revision": f"sha256:{source_digest}",
        "pointer_ref": str(pointer),
        "pointer_digest": pointer_digest,
        "pointer_integrity": "valid" if pointer_valid else "invalid",
        "canonical_index_ref": str(index),
        "canonical_index_revision": f"sha256:{index_digest}",
        "canonical_index_aligned": index_aligned,
        "verified_outcome_eligible": False,
        "conflicts": [],
    }


def _unavailable_layer(layer_id: str) -> dict[str, Any]:
    return {
        "layer_id": layer_id,
        "availability": "unavailable",
        "canonical_source_ref": None,
        "canonical_revision": None,
        "pointer_ref": None,
        "pointer_digest": None,
        "pointer_integrity": "unknown",
        "canonical_index_ref": None,
        "canonical_index_revision": None,
        "canonical_index_aligned": None,
        "verified_outcome_eligible": None,
        "conflicts": [],
    }


def materialize(now: datetime | None = None) -> dict[str, Any]:
    current = now.astimezone(SEOUL) if now is not None else datetime.now(SEOUL)
    day = current.date().isoformat()
    equation, equation_digest = _read_bounded(EQUATION)
    handoff, handoff_digest = _read_bounded(HANDOFF)
    manifest, manifest_digest = _read_bounded(MANIFEST)

    pointer_valid = _line_present(handoff, f"  - {EQUATION}")
    manifest_aligned = (
        _line_present(manifest, "project_slug: harness-starter")
        and _line_present(manifest, f"  canonical_cwd: {ROOT}")
    )
    layers = [
        _available_layer(
            "harness_brain",
            EQUATION,
            equation_digest,
            HANDOFF,
            handoff_digest,
            pointer_valid,
            MANIFEST,
            manifest_digest,
            manifest_aligned,
        ),
        _unavailable_layer("honcho"),
        _unavailable_layer("gbrain"),
    ]
    return {
        "schema": SCHEMA,
        "collection_ref": f"daily:{day}",
        "materialized_date": day,
        "layers": layers,
    }


def validate_declaration(value: Mapping[str, Any]) -> None:
    if not isinstance(value, Mapping) or set(value) != DECLARATION_KEYS:
        raise MaterializationError("invalid declaration shape")
    if value.get("schema") != SCHEMA:
        raise MaterializationError("invalid materialization schema")
    collection_ref = value.get("collection_ref")
    materialized_date = value.get("materialized_date")
    if not isinstance(collection_ref, str) or re.fullmatch(r"daily:[0-9]{4}-[0-9]{2}-[0-9]{2}", collection_ref) is None:
        raise MaterializationError("invalid collection reference")
    if not isinstance(materialized_date, str):
        raise MaterializationError("invalid materialized date")
    try:
        datetime.strptime(materialized_date, "%Y-%m-%d")
    except ValueError as error:
        raise MaterializationError("invalid materialized date") from error

    layers = value.get("layers")
    validate_layers(layers, MaterializationError)

    for layer in layers:
        if set(layer) != LAYER_KEYS or layer.get("availability") not in {"available", "unavailable"}:
            raise MaterializationError("invalid layer shape")
        if layer.get("conflicts") != []:
            raise MaterializationError("layer conflicts must be empty")


def validate_fresh(value: Mapping[str, Any], now: datetime | None = None) -> None:
    current = now.astimezone(SEOUL) if now is not None else datetime.now(SEOUL)
    expected = current.date().isoformat()
    if value.get("schema") != SCHEMA:
        raise MaterializationError("invalid materialization schema")
    if value.get("materialized_date") != expected or value.get("collection_ref") != f"daily:{expected}":
        raise MaterializationError("stale daily materialization")


def atomic_write(value: Mapping[str, Any], destination: Path) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_bytes(value)
    temporary = destination.with_name(destination.name + ".tmp")
    try:
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
        readback = destination.read_bytes()
        digest = hashlib.sha256(readback).hexdigest()
        if readback != payload or digest != hashlib.sha256(payload).hexdigest():
            raise OSError("materialization readback mismatch")
        return {"sha256": digest, "bytes": len(readback), "readback_verified": True}
    finally:
        temporary.unlink(missing_ok=True)


def run(destination: str | Path, now: datetime | None = None) -> dict[str, Any]:
    declaration = materialize(now)
    validate_declaration(declaration)
    validate_fresh(declaration, now)
    return atomic_write(declaration, Path(destination))


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("output")
    args = parser.parse_args()
    try:
        run(args.output)
        return 0
    except (MaterializationError, OSError, TypeError, ValueError):
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
