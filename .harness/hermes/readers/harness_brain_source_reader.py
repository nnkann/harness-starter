"""Bounded, read-only reader for explicitly named Harness Brain sources."""
from __future__ import annotations

from pathlib import Path
from typing import Any


DEFAULT_MAX_BYTES = 64 * 1024


def read_harness_brain_source(
    source_ref: str,
    harness_brain_root: str | Path,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> dict[str, Any]:
    """Read one explicit source ref without searching, traversing, or writing.

    The returned ``source_ref`` is the caller's original identity.  The
    ``source_identity`` is the resolved file identity when it can be safely
    established.  Every non-readable input is an explicit unavailable receipt.
    """
    receipt: dict[str, Any] = {
        "status": "unavailable",
        "source_ref": source_ref,
        "source_identity": source_ref,
        "readback": None,
    }
    if not isinstance(source_ref, str) or not source_ref or not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes < 1:
        receipt["reason"] = "invalid"
        return receipt

    try:
        root = Path(harness_brain_root).resolve(strict=True)
    except (OSError, RuntimeError, TypeError, ValueError):
        receipt["reason"] = "unavailable"
        return receipt
    if not root.is_dir():
        receipt["reason"] = "unavailable"
        return receipt

    requested = Path(source_ref)
    if ".." in requested.parts:
        receipt["reason"] = "invalid"
        return receipt
    candidate = requested if requested.is_absolute() else root / requested
    try:
        identity = candidate.resolve(strict=True)
    except FileNotFoundError:
        receipt["reason"] = "absent"
        return receipt
    except (OSError, RuntimeError, ValueError):
        receipt["reason"] = "unreadable"
        return receipt

    try:
        identity.relative_to(root)
    except ValueError:
        receipt["reason"] = "out_of_bound"
        return receipt
    receipt["source_identity"] = str(identity)
    if not identity.is_file():
        receipt["reason"] = "unreadable"
        return receipt

    try:
        with identity.open("rb") as source:
            content = source.read(max_bytes + 1)
    except OSError:
        receipt["reason"] = "unreadable"
        return receipt
    if len(content) > max_bytes:
        receipt["reason"] = "out_of_bound"
        return receipt

    return {
        "status": "available",
        "source_ref": source_ref,
        "source_identity": str(identity),
        "readback": {"content": content, "byte_count": len(content)},
    }
