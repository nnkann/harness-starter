#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any, Iterable, Mapping, Optional

RESULTS = {"eligible", "rejected", "duplicate", "superseding"}
MAX_REASONS = 8
PROHIBITED_FIELDS = frozenset({
    "graph", "raw_graph", "receipt", "raw_receipt", "log", "logs",
    "transcript", "transcripts", "retry", "retries", "retry_count",
    "poll", "polls", "polling", "route_projection", "route_projections",
    "transport", "worker_claim", "test_claim", "prior_body", "history",
})
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@-]*$")
_INPUT_FIELDS = {"identity", "pattern", "outcome", "execution_evidence", "source_refs", "lifecycle", "timestamp", "supersedes_ref"}
_IDENTITY_FIELDS = {"namespace", "name", "revision"}
_PATTERN_FIELDS = {"C", "P", "S", "AC"}
_PROOF_FIELDS = {"digest", "state", "terminal", "verifier"}
_OUTCOME_FIELDS = _PROOF_FIELDS | {"outcome_ref"}
_EVIDENCE_FIELDS = _PROOF_FIELDS | {"evidence_ref"}
_VERIFIER_FIELDS = {"kind", "independent"}


class CandidateContractError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _nonempty(value: Any, maximum: int = 512) -> bool:
    return isinstance(value, str) and 0 < len(value) <= maximum


def _valid_ref(value: Any) -> bool:
    return _nonempty(value, 512) and bool(_REF.fullmatch(value))


def _closed(value: Any, fields: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == fields


def _has_prohibited(value: Any) -> bool:
    if isinstance(value, dict):
        if set(value) & PROHIBITED_FIELDS:
            return True
        if value.get("fixture") == "live":
            return True
        fixture = value.get("fixture")
        if isinstance(fixture, dict) and fixture.get("live") is True:
            return True
        return any(_has_prohibited(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_prohibited(item) for item in value)
    return False


def _valid_verifier(value: Any) -> bool:
    return (
        _closed(value, _VERIFIER_FIELDS)
        and value["kind"] == "maat"
        and value["independent"] is True
    )


def _valid_proof(value: Any, ref_key: str, fields: set[str]) -> bool:
    return (
        _closed(value, fields)
        and _valid_ref(value[ref_key])
        and isinstance(value["digest"], str)
        and bool(_DIGEST.fullmatch(value["digest"]))
        and value["state"] == "verified"
        and value["terminal"] is True
        and _valid_verifier(value["verifier"])
    )


def _valid_pattern(value: Any) -> bool:
    if not _closed(value, _PATTERN_FIELDS) or not _nonempty(value["C"]):
        return False
    for key in ("P", "S", "AC"):
        items = value[key]
        if not isinstance(items, list) or not 1 <= len(items) <= 16:
            return False
        if any(not _nonempty(item) for item in items):
            return False
    return len(_canonical(value)) <= 8192


def _reasons(packet: Any) -> list[str]:
    reasons: list[str] = []
    if not isinstance(packet, dict):
        return ["invalid_input"]
    if _has_prohibited(packet):
        reasons.append("prohibited_input_class")
    unknown = set(packet) - _INPUT_FIELDS
    if unknown:
        reasons.append("unknown_input_field")
    identity = packet.get("identity")
    if not _closed(identity, _IDENTITY_FIELDS) or not _valid_ref(identity.get("namespace")) or not _valid_ref(identity.get("name")) or not isinstance(identity.get("revision"), int) or isinstance(identity.get("revision"), bool) or identity.get("revision", 0) < 1:
        reasons.append("invalid_identity")
    if not _valid_pattern(packet.get("pattern")):
        reasons.append("invalid_pattern")
    if not _valid_proof(packet.get("outcome"), "outcome_ref", _OUTCOME_FIELDS):
        reasons.append("outcome_not_independently_verified_terminal")
    evidence = packet.get("execution_evidence")
    if not isinstance(evidence, list) or not 1 <= len(evidence) <= 16 or any(not _valid_proof(item, "evidence_ref", _EVIDENCE_FIELDS) for item in evidence):
        reasons.append("execution_not_independently_verified_terminal")
    source_refs = packet.get("source_refs")
    if not isinstance(source_refs, list) or not 1 <= len(source_refs) <= 32 or any(not _valid_ref(ref) for ref in source_refs):
        reasons.append("invalid_source_refs")
    if packet.get("lifecycle") != "candidate":
        reasons.append("invalid_lifecycle")
    return reasons[:MAX_REASONS]


def project_learning_candidate(packet: Mapping[str, Any], supersedes_ref: Optional[str] = None) -> dict[str, Any]:
    """Return the canonical immutable body; callers must validate admission first."""
    source = copy.deepcopy(dict(packet))
    semantic = {
        "identity": source["identity"],
        "pattern": source["pattern"],
        "outcome_binding": source["outcome"],
        "execution_evidence": source["execution_evidence"],
        "source_refs": sorted(set(source["source_refs"])),
        "lifecycle": "candidate",
    }
    dedupe_key = _digest({"identity": semantic["identity"], "pattern": semantic["pattern"]})
    candidate_id = "lc_" + _digest(semantic)
    body = {"candidate_id": candidate_id, **semantic, "dedupe_key": dedupe_key}
    if supersedes_ref is not None:
        body["supersedes_ref"] = supersedes_ref
    return body


def admit_learning_candidate(
    packet: Mapping[str, Any],
    *,
    existing: Optional[Iterable[Mapping[str, Any]]] = None,
    supersedes_ref: Optional[str] = None,
) -> dict[str, Any]:
    """Pure admission/projection function. It performs no external reads or writes."""
    source = copy.deepcopy(packet)
    reasons = _reasons(source)
    requested_ref = supersedes_ref if supersedes_ref is not None else source.get("supersedes_ref") if isinstance(source, dict) else None
    if requested_ref is not None and not _valid_ref(requested_ref):
        reasons.append("invalid_supersession_ref")
    if reasons:
        return {"result": "rejected", "reasons": reasons[:MAX_REASONS]}

    bodies = [copy.deepcopy(dict(item)) for item in (existing or [])]
    projected = project_learning_candidate(source)
    equivalent = next((item for item in bodies if item.get("dedupe_key") == projected["dedupe_key"]), None)
    if equivalent is not None:
        return {
            "result": "duplicate",
            "reasons": ["equivalent_candidate_exists"],
            "candidate_ref": equivalent.get("candidate_id", "unknown"),
        }

    if bodies:
        if requested_ref is None:
            return {"result": "rejected", "reasons": ["supersession_ref_required"]}
        prior = next((item for item in bodies if item.get("candidate_id") == requested_ref), None)
        if prior is None:
            return {"result": "rejected", "reasons": ["supersession_ref_unknown"]}
        projected = project_learning_candidate(source, requested_ref)
        return {"result": "superseding", "reasons": ["material_pattern_change"], "candidate": projected}

    if requested_ref is not None:
        return {"result": "rejected", "reasons": ["supersession_ref_unknown"]}
    return {"result": "eligible", "reasons": ["admission_contract_satisfied"], "candidate": projected}
