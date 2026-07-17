"""Standalone Harness runtime API.

This package intentionally has no Hermes import or live-state fallback.
"""

from .runtime import ReceiptValidationError, analysis_input, execute, readback, schema_text

__all__ = ["ReceiptValidationError", "analysis_input", "execute", "readback", "schema_text"]
__version__ = "0.1.1"
