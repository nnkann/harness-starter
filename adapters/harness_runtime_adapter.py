"""Thin project adapter for the isolated artifact API.

This module deliberately has no Hermes import, gateway client, or source-state fallback.
"""

from __future__ import annotations

from typing import Sequence

from harness_runtime import execute, readback


def dispatch(case_id: str, consumer: str, body: bytes, command: Sequence[str]) -> dict:
    """Produce the external receipt consumed by the supplied consumer identity."""
    return execute(case_id, consumer, body, command)


def consume(case_id: str, consumer: str) -> dict:
    """Read and verify the terminal receipt for that consumer."""
    return readback(case_id, expected_consumer=consumer)
