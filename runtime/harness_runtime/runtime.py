from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path
from typing import Any, Sequence

SCHEMA_NAME = "harness.runtime.execution-receipt.v1"
_CASE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class ReceiptValidationError(ValueError):
    """The isolated runtime input or persisted receipt is invalid."""


def schema_text() -> str:
    return resources.files("contracts").joinpath("execution-receipt.v1.schema.json").read_text(encoding="utf-8")


def _state_root() -> Path:
    """Return an external state root; source-tree state is never a fallback."""
    override = os.environ.get("HARNESS_STATE_DIR")
    if override:
        return Path(override).expanduser().resolve()
    profile = os.environ.get("HARNESS_PROFILE", "default")
    project_slug = os.environ.get("HARNESS_PROJECT_SLUG", "harness-starter")
    canonical_cwd = Path(os.environ.get("HARNESS_CANONICAL_CWD", os.getcwd())).expanduser().resolve()
    if not _CASE_RE.fullmatch(profile) or not _CASE_RE.fullmatch(project_slug):
        raise ReceiptValidationError("HARNESS_PROFILE and HARNESS_PROJECT_SLUG must be safe identifiers")
    cwd_hash = hashlib.sha256(str(canonical_cwd).encode("utf-8")).hexdigest()
    return Path.home() / ".harness" / "state" / profile / project_slug / cwd_hash


def _case_dir(case_id: str) -> Path:
    if not _CASE_RE.fullmatch(case_id):
        raise ReceiptValidationError("case_id must be 1-128 safe filename characters")
    return _state_root() / "receipts" / hashlib.sha256(case_id.encode("utf-8")).hexdigest()


def _artifact(path: Path, case_dir: Path) -> dict[str, Any]:
    content = path.read_bytes()
    return {
        "ref": path.relative_to(case_dir).as_posix(),
        "sha256": hashlib.sha256(content).hexdigest(),
        "bytes": len(content),
    }


def _write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def _append(case_dir: Path, receipt: dict[str, Any]) -> None:
    receipt_path = case_dir / "receipts.jsonl"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    with receipt_path.open("a", encoding="utf-8") as output:
        output.write(json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n")
        output.flush()
        os.fsync(output.fileno())
    projection = case_dir / "current.json"
    temporary = projection.with_suffix(".tmp")
    temporary.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    temporary.replace(projection)


def _receipt(sequence: int, event: str, status: str, case_id: str, consumer: str, artifacts: dict[str, Any], exit_code: int | None) -> dict[str, Any]:
    return {
        "schema": SCHEMA_NAME,
        "sequence": sequence,
        "event": event,
        "status": status,
        "case_id": case_id,
        "consumer": consumer,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "exit_code": exit_code,
        "artifacts": artifacts,
    }


def execute(case_id: str, consumer: str, body: bytes, command: Sequence[str]) -> dict[str, Any]:
    if not consumer:
        raise ReceiptValidationError("consumer is required")
    if not isinstance(body, bytes):
        raise ReceiptValidationError("body must be bytes")
    argv = list(command)
    if not argv or any(not isinstance(item, str) or not item for item in argv):
        raise ReceiptValidationError("command must contain non-empty strings")
    case_dir = _case_dir(case_id)
    if (case_dir / "current.json").exists():
        raise ReceiptValidationError("case_id already has a receipt; choose a new isolated case")
    artifacts_dir = case_dir / "artifacts"
    body_path = artifacts_dir / "body.bin"
    stdout_path = artifacts_dir / "stdout.bin"
    stderr_path = artifacts_dir / "stderr.bin"
    _write(body_path, body)
    _write(stdout_path, b"")
    _write(stderr_path, b"")
    artifacts = {"body": _artifact(body_path, case_dir), "stdout": _artifact(stdout_path, case_dir), "stderr": _artifact(stderr_path, case_dir)}
    _append(case_dir, _receipt(1, "dispatch", "observed", case_id, consumer, artifacts, None))
    completed = subprocess.run(argv, input=body, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    _write(stdout_path, completed.stdout)
    _write(stderr_path, completed.stderr)
    artifacts = {"body": _artifact(body_path, case_dir), "stdout": _artifact(stdout_path, case_dir), "stderr": _artifact(stderr_path, case_dir)}
    terminal = _receipt(2, "terminal", "pass" if completed.returncode == 0 else "fail", case_id, consumer, artifacts, completed.returncode)
    _append(case_dir, terminal)
    return terminal


def readback(case_id: str, expected_consumer: str | None = None) -> dict[str, Any]:
    case_dir = _case_dir(case_id)
    path = case_dir / "current.json"
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReceiptValidationError("receipt readback is unavailable") from exc
    if receipt.get("schema") != SCHEMA_NAME or receipt.get("event") != "terminal":
        raise ReceiptValidationError("terminal receipt is required for consumer readback")
    if expected_consumer is not None and receipt.get("consumer") != expected_consumer:
        raise ReceiptValidationError("consumer does not match receipt")
    artifacts = receipt.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ReceiptValidationError("receipt artifacts are invalid")
    for name in ("body", "stdout", "stderr"):
        item = artifacts.get(name)
        if not isinstance(item, dict) or not isinstance(item.get("ref"), str):
            raise ReceiptValidationError("receipt artifacts are invalid")
        artifact_path = (case_dir / item["ref"]).resolve()
        if case_dir not in artifact_path.parents:
            raise ReceiptValidationError("artifact escapes isolated state")
        if _artifact(artifact_path, case_dir) != item:
            raise ReceiptValidationError("artifact readback does not match receipt")
    return {"consumer": receipt["consumer"], "receipt": receipt, "artifacts": artifacts, "receipt_path": str(path)}
