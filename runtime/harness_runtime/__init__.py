"""Standalone Harness runtime API.

This package intentionally has no Hermes import or live-state fallback.
"""

from .ingress import (
    EventRef,
    ExecutionReceipts,
    IngressIntake,
    IngressPacket,
    IngressValidationError,
    IntakeResult,
    ProjectRef,
    canonical_packet_json,
    process_bound_ingress,
)
from .runtime import ReceiptValidationError, analysis_input, execute, readback, schema_text

__all__ = [
    "EventRef",
    "ExecutionReceipts",
    "IngressIntake",
    "IngressPacket",
    "IngressValidationError",
    "IntakeResult",
    "ProjectRef",
    "ReceiptValidationError",
    "analysis_input",
    "canonical_packet_json",
    "execute",
    "process_bound_ingress",
    "readback",
    "schema_text",
]
__version__ = "0.1.1"
