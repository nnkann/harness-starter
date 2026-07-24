#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping

ROOT = Path("/Users/kann/projects/harness-starter")
TOOLS = ROOT / ".harness/hermes/tools"
STATE = ROOT / ".harness/hermes/state/daily-memory"
DECLARATION = STATE / "declaration.json"
C2_RECEIPT = STATE / "c2-receipt.json"
C3_RECEIPT = STATE / "c3-dispatch-receipt.json"


class DailyRunError(RuntimeError):
    pass


def _load(name: str) -> ModuleType:
    path = TOOLS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise DailyRunError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _atomic_promote(source: Path, destination: Path) -> str:
    payload = source.read_bytes()
    expected = hashlib.sha256(payload).hexdigest()
    destination.parent.mkdir(parents=True, exist_ok=True)
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
        if readback != payload or hashlib.sha256(readback).hexdigest() != expected:
            raise OSError("C2 receipt readback mismatch")
        return expected
    finally:
        temporary.unlink(missing_ok=True)


def _successful_delta_dispatch(receipt_path: Path, packet_digest: str) -> bool:
    try:
        value: Mapping[str, Any] = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError):
        return False
    return (
        value.get("schema") == "harness.memory.daily-dispatch-receipt.v1"
        and value.get("packet_digest") == packet_digest
        and value.get("terminal_status") == "succeeded"
        and value.get("exit_code") == 0
    )


def run(
    declaration_path: Path = DECLARATION,
    c2_path: Path = C2_RECEIPT,
    c3_path: Path = C3_RECEIPT,
) -> int:
    os.chdir(ROOT)
    materializer = _load("daily_memory_materializer")
    collector = _load("daily_memory_collector")
    driver = _load("daily_memory_audit_driver")

    declaration_path.parent.mkdir(parents=True, exist_ok=True)
    staged_c2 = c2_path.with_name(c2_path.name + ".stage")
    try:
        materializer.run(declaration_path)
        declaration = json.loads(declaration_path.read_text(encoding="utf-8"))
        materializer.validate_fresh(declaration)
        prior = c2_path if c2_path.exists() else None
        result = collector.run(declaration_path, staged_c2, prior)
        receipt = result["receipt"]
        if receipt["comparison"]["meaningful_delta"]:
            packet_digest = receipt["consumer"]["packet"]["packet_digest"]
            if driver.run(staged_c2, c3_path) != 0:
                return 1
            if not _successful_delta_dispatch(c3_path, packet_digest):
                return 1
        _atomic_promote(staged_c2, c2_path)
        return 0
    finally:
        declaration_path.unlink(missing_ok=True)
        staged_c2.unlink(missing_ok=True)


def main() -> int:
    try:
        return run()
    except (DailyRunError, OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
