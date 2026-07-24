"""Source-neutral, read-only contract for CPS advisory readers.

This module dispatches only an explicitly bound producer.  It does not provide
source bindings or interpret advisory content as CPS semantics.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, Mapping, Optional, Tuple


STATES: Tuple[str, ...] = (
    "available",
    "unavailable",
    "query_error",
    "match",
    "no_match",
)
_SEMANTIC_KEYS = frozenset(
    {
        "route",
        "verdict",
        "selected_agents",
        "actor_binding",
        "graph_revision",
        "hold",
        "mutation",
        "task_ac",
        "closure",
        "learning_candidate",
        "promotion",
    }
)
_EVIDENCE_KEYS = frozenset({"record_count", "content_digest", "source_receipt"})
_MAX_CONTEXT_ITEMS = 16
_MAX_CONTEXT_TEXT = 256
_MAX_EVIDENCE_RECORDS = 10000


class AdvisoryContractError(ValueError):
    """Raised when a caller tries to treat a non-retrieval as retrieval."""


@dataclass(frozen=True)
class AdvisoryReadRequest:
    query: str
    reader_context: Dict[str, Any]


@dataclass(frozen=True)
class AdvisoryReaderBinding:
    """An explicit, real producer binding; no source-specific implementation."""

    producer_ref: str
    source_identity: str
    reader: Callable[[AdvisoryReadRequest], Mapping[str, Any]]
    source_revision: Optional[str] = None


@dataclass(frozen=True)
class AdvisoryReadback:
    state: str
    producer_ref: str
    source_identity: str
    source_revision: Optional[str]
    evidence: Dict[str, Any]
    reader_context: Dict[str, Any]
    candidate: Optional[Dict[str, str]] = None


def retrieve_advisory(
    binding: Optional[AdvisoryReaderBinding], query: str, reader_context: Mapping[str, Any]
) -> AdvisoryReadback:
    """Read one advisory response through an explicit binding and validate it.

    A missing binding, fixture, command/status surrogate, or ``None`` result is
    rejected rather than normalized into an availability state.
    """
    binding = _validated_binding(binding)
    if not isinstance(query, str) or not query.strip():
        raise AdvisoryContractError("query must be a non-empty string")
    context = _validated_context(reader_context)
    request = AdvisoryReadRequest(query=query, reader_context=dict(context))
    raw = binding.reader(request)
    if raw is None:
        raise AdvisoryContractError("None is not a retrieval response")
    if not isinstance(raw, Mapping):
        raise AdvisoryContractError("reader response must be a mapping, not a command or placeholder")
    return _normalize_response(binding, raw, context)


def _validated_binding(binding: Optional[AdvisoryReaderBinding]) -> AdvisoryReaderBinding:
    if not isinstance(binding, AdvisoryReaderBinding):
        raise AdvisoryContractError("an explicit AdvisoryReaderBinding is required")
    for name, value in (("producer_ref", binding.producer_ref), ("source_identity", binding.source_identity)):
        if not isinstance(value, str) or not value.strip():
            raise AdvisoryContractError(f"binding {name} must be a non-empty string")
        if "fixture" in value.casefold():
            raise AdvisoryContractError("fixture bindings are not retrieval")
    if binding.source_revision is not None and (not isinstance(binding.source_revision, str) or not binding.source_revision.strip()):
        raise AdvisoryContractError("source_revision must be omitted or a non-empty string")
    if not callable(binding.reader) or getattr(binding.reader, "__advisory_fixture__", False):
        raise AdvisoryContractError("binding reader must be a real callable, not a fixture or command")
    return binding


def _normalize_response(
    binding: AdvisoryReaderBinding, raw: Mapping[str, Any], context: Dict[str, Any]
) -> AdvisoryReadback:
    required = {"state", "producer_ref", "source_identity", "evidence", "reader_context"}
    unknown = set(raw) - (required | {"source_revision", "candidate"})
    if unknown or not required.issubset(raw):
        raise AdvisoryContractError("response must be a complete readback, not a status-only command")
    state = raw["state"]
    if state not in STATES:
        raise AdvisoryContractError(f"unsupported advisory state: {state!r}")
    if raw["producer_ref"] != binding.producer_ref or raw["source_identity"] != binding.source_identity:
        raise AdvisoryContractError("response producer reference and source identity must match its binding")
    source_revision = raw.get("source_revision", binding.source_revision)
    if binding.source_revision is not None and source_revision != binding.source_revision:
        raise AdvisoryContractError("response source_revision must match its binding when bound")
    if source_revision is not None and (not isinstance(source_revision, str) or not source_revision.strip()):
        raise AdvisoryContractError("source_revision must be omitted or a non-empty string")
    readback_context = _validated_context(raw["reader_context"])
    if readback_context != context:
        raise AdvisoryContractError("reader_context readback must exactly match the request")
    evidence = _validated_evidence(raw["evidence"])
    if state == "match" and (evidence.get("record_count", 0) == 0 or "content_digest" not in evidence):
        raise AdvisoryContractError("match requires bounded producer evidence")
    if state == "no_match" and evidence.get("record_count") != 0:
        raise AdvisoryContractError("no_match must have zero producer records")
    candidate = _validated_candidate(raw.get("candidate"), state, evidence, binding.source_identity)
    return AdvisoryReadback(
        state, binding.producer_ref, binding.source_identity, source_revision,
        evidence, readback_context, candidate,
    )


def _validated_context(value: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(value, Mapping) or len(value) > _MAX_CONTEXT_ITEMS:
        raise AdvisoryContractError("reader_context must be a bounded mapping")
    normalized: Dict[str, Any] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key or len(key) > 64 or key.casefold() in _SEMANTIC_KEYS:
            raise AdvisoryContractError("reader_context may not carry semantic control fields")
        if not isinstance(item, (str, int, bool)) or (isinstance(item, str) and len(item) > _MAX_CONTEXT_TEXT):
            raise AdvisoryContractError("reader_context values must be bounded scalar readback values")
        normalized[key] = item
    return normalized


def _validated_evidence(value: Any) -> Dict[str, Any]:
    if not isinstance(value, Mapping) or not value or set(value) - _EVIDENCE_KEYS:
        raise AdvisoryContractError("evidence must be a non-empty bounded nonsemantic mapping")
    if any(str(key).casefold() in _SEMANTIC_KEYS for key in value):
        raise AdvisoryContractError("evidence may not carry CPS semantic fields")
    count = value.get("record_count")
    if not isinstance(count, int) or isinstance(count, bool) or not 0 <= count <= _MAX_EVIDENCE_RECORDS:
        raise AdvisoryContractError("evidence record_count must be bounded")
    digest = value.get("content_digest")
    if digest is not None and (not isinstance(digest, str) or len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest)):
        raise AdvisoryContractError("evidence content_digest must be a lowercase sha256 hex digest")
    receipt = value.get("source_receipt")
    if receipt is not None and (not isinstance(receipt, str) or not receipt or len(receipt) > _MAX_CONTEXT_TEXT):
        raise AdvisoryContractError("evidence source_receipt must be bounded text")
    return dict(value)


def _validated_candidate(
    value: Any, state: str, evidence: Mapping[str, Any], source_identity: str
) -> Optional[Dict[str, str]]:
    if value is None:
        return None
    required = {"clue", "source_ref", "source_receipt", "lifecycle", "observed_at"}
    if not isinstance(value, Mapping) or set(value) != required:
        raise AdvisoryContractError("candidate must have the bounded semantic readback shape")
    for key in ("clue", "source_ref", "source_receipt", "observed_at"):
        item = value[key]
        if not isinstance(item, str) or not item or len(item) > _MAX_CONTEXT_TEXT:
            raise AdvisoryContractError(f"candidate {key} must be bounded text")
    if value["lifecycle"] != "candidate":
        raise AdvisoryContractError("advisory semantic delivery must remain a candidate")
    if state not in {"available", "match"} or evidence.get("record_count", 0) == 0:
        raise AdvisoryContractError("candidate requires direct producer readback")
    if value["source_receipt"] != evidence.get("source_receipt"):
        raise AdvisoryContractError("candidate source_receipt must match producer evidence")
    if value["source_ref"] != source_identity:
        raise AdvisoryContractError("candidate source_ref must match the direct producer binding")
    try:
        observed_at = datetime.fromisoformat(value["observed_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise AdvisoryContractError("candidate observed_at must be an ISO-8601 timestamp") from exc
    if observed_at.tzinfo is None:
        raise AdvisoryContractError("candidate observed_at must include a timezone")
    return dict(value)
