#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable, Mapping

_HERMES = Path(__file__).resolve().parents[1]
for _module_dir in (_HERMES / "contracts", _HERMES / "readers"):
    if str(_module_dir) not in sys.path:
        sys.path.insert(0, str(_module_dir))

from cps_advisory_reader_contract import AdvisoryReaderBinding, retrieve_advisory  # type: ignore[import-not-found]
from gbrain_search_reader import create_gbrain_search_reader  # type: ignore[import-not-found]
from harness_brain_source_reader import DEFAULT_MAX_BYTES, read_harness_brain_source  # type: ignore[import-not-found]
from honcho_session_reader import configured_honcho_session_binding  # type: ignore[import-not-found]


class RetrievalError(ValueError):
    pass


_REQUIRED = {"request_ref", "binding_ref", "C_shape", "direct_source_refs"}
_C_SHAPE_REQUIRED = {
    "intent",
    "continuity",
    "boundary_hint",
    "cardinality_hint",
    "source_current_state_need",
}
_C_SHAPE_DOMAINS = {
    "continuity": {"new", "follow_up", "rework", "linked", "incident"},
    "boundary_hint": {"single", "linked", "unknown"},
    "cardinality_hint": {"single", "multiple", "uncertain"},
    "source_current_state_need": {"required", "not_required", "uncertain"},
}
_CANDIDATE_METADATA = ("score", "summary", "source", "current_state")
SOURCE_KINDS = ("honcho", "gbrain", "harness_brain")
_MAX_DIGEST_BYTES = 65536
_GBRAIN_PRODUCER = "adapter:gbrain-search-reader:v1"
_GBRAIN_SOURCE_IDENTITY = "gbrain-cli:search"
_HARNESS_BRAIN_PRODUCER = "adapter:harness-brain-source-reader:v1"
_HARNESS_BRAIN_UNAVAILABLE_REASONS = {"invalid", "unavailable", "absent", "unreadable", "out_of_bound"}


def _timestamp(value: str | None) -> str:
    return value or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _redact_ref(value: Any, source_kind: str) -> str:
    if not isinstance(value, str) or not value:
        return f"{source_kind}:advisory"
    if "/" not in value and "\\" not in value and "?" not in value:
        return value
    label = Path(value.split("?", 1)[0]).name or source_kind
    suffix = hashlib.sha256(value.encode()).hexdigest()[:12]
    return f"{source_kind}:{label}#{suffix}"


def _path_binding(binding: Path, source_ref: str | None) -> dict[str, Any]:
    if source_ref is None:
        return {"matches": []}
    path = Path(source_ref)
    if not path.is_absolute():
        path = binding / path
    try:
        content = path.read_bytes()
    except OSError:
        raise
    return {"matches": [{"source_ref": str(path), "content": content}]}


def _normalize_observation(source_kind: str, source_ref: str | None, raw: Any, timestamp: str) -> dict[str, Any]:
    evidence: dict[str, Any] = {"count": 0, "timestamp": timestamp}
    observation = {
        "source_kind": source_kind,
        "status": "unavailable",
        "source_ref": _redact_ref(source_ref, source_kind),
        "evidence": evidence,
    }
    if not isinstance(raw, dict) or set(raw) != {"matches"} or not isinstance(raw["matches"], list):
        return observation
    matches = raw["matches"]
    if not matches:
        observation["status"] = "no_match"
        return observation
    chunks = []
    for match in matches:
        if not isinstance(match, dict) or not isinstance(match.get("content"), (str, bytes)):
            return observation
        content = match["content"]
        chunks.append(content.encode() if isinstance(content, str) else content)
    digest_input = b"\x00".join(chunks)[:_MAX_DIGEST_BYTES]
    evidence.update(count=len(matches), digest=hashlib.sha256(digest_input).hexdigest())
    if source_ref is None:
        observation["source_ref"] = _redact_ref(matches[0].get("source_ref"), source_kind)
    observation["status"] = "match"
    return observation


def configured_live_bindings(
    gbrain_root: str | Path,
    harness_brain_root: str | Path,
    honcho_command: tuple[str, ...] = ("hermes", "honcho", "status"),
    *,
    subprocess_runner: Callable[..., Any] = subprocess.run,
) -> dict[str, Callable[[str | None, str | None], Any] | Path]:
    """Create adapter-owned, read-only bindings for configured live sources."""
    command = tuple(honcho_command)

    def read_honcho(source_ref: str | None, query: str | None) -> dict[str, Any]:
        completed = subprocess_runner(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if completed.returncode != 0:
            raise OSError("configured Honcho status is unavailable")
        return {"matches": [{"source_ref": "honcho:status", "content": completed.stdout}]}

    return {
        "honcho": read_honcho,
        "gbrain": Path(gbrain_root),
        "harness_brain": Path(harness_brain_root),
    }


def observe_sources(
    bindings: Mapping[str, Callable[[str | None, str | None], Any] | str | Path],
    *,
    direct_refs: list[dict[str, str]] | None = None,
    advisory_bindings: Mapping[str, Callable[[str | None, str | None], Any] | str | Path] | None = None,
    query: str | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Read bound sources without writing or producing CPS-semantic output."""
    advisory_bindings = advisory_bindings or {}
    unknown = (set(bindings) | set(advisory_bindings)) - set(SOURCE_KINDS)
    if unknown:
        raise RetrievalError("undeclared source kind")
    refs = direct_refs or []
    for ref in refs:
        if not isinstance(ref, dict) or set(ref) != {"source_kind", "source_ref"}:
            raise RetrievalError("direct source ref has invalid shape")
        if ref["source_kind"] not in SOURCE_KINDS or not isinstance(ref["source_ref"], str) or not ref["source_ref"]:
            raise RetrievalError("undeclared source kind or invalid source ref")
        if ref["source_kind"] not in bindings:
            raise RetrievalError("direct source has no binding")

    observed_at = _timestamp(timestamp)
    requests: list[tuple[str, str | None, Mapping[str, Callable[[str | None, str | None], Any] | str | Path]]] = [
        (ref["source_kind"], ref["source_ref"], bindings) for ref in refs
    ]
    requests.extend((kind, None, advisory_bindings) for kind in SOURCE_KINDS if kind in advisory_bindings)
    observations = []
    for source_kind, source_ref, request_bindings in requests:
        binding = request_bindings[source_kind]
        try:
            raw = binding(source_ref, query) if callable(binding) else _path_binding(Path(binding), source_ref)
        except Exception:
            raw = None
        observations.append(_normalize_observation(source_kind, source_ref, raw, observed_at))
    return {"observations": observations}


def retrieve_gbrain_search_source(
    *,
    query: str,
    reader_context: Mapping[str, Any],
    source_revision: str | None = None,
    timeout: float = 10.0,
    reader_factory: Callable[..., Callable[[str, Any], Mapping[str, Any]]] = create_gbrain_search_reader,
) -> dict[str, Any]:
    """Read GBrain search through the advisory contract without exposing search output."""
    try:
        search_reader = reader_factory(timeout=timeout)
    except Exception:
        search_reader = None

    def read(request: Any) -> dict[str, Any]:
        state = "unavailable"
        evidence: dict[str, Any] = {
            "record_count": 0,
            "source_receipt": "gbrain-search-reader:command_error",
        }
        if search_reader is not None:
            try:
                raw = search_reader(request.query, None)
            except Exception:
                raw = None
            else:
                if (
                    not isinstance(raw, Mapping)
                    or set(raw) != {"query", "stdout", "stderr", "returncode"}
                    or raw.get("query") != request.query
                    or not isinstance(raw.get("stdout"), str)
                    or not isinstance(raw.get("stderr"), str)
                    or not isinstance(raw.get("returncode"), int)
                    or isinstance(raw.get("returncode"), bool)
                ):
                    evidence["source_receipt"] = "gbrain-search-reader:malformed_output"
                elif raw["returncode"] != 0:
                    evidence["source_receipt"] = "gbrain-search-reader:nonzero_exit"
                elif not raw["stdout"].strip():
                    state = "no_match"
                    evidence = {"record_count": 0}
                else:
                    content = raw["stdout"].encode()[:_MAX_DIGEST_BYTES]
                    state = "match"
                    evidence = {
                        "record_count": 1,
                        "content_digest": hashlib.sha256(content).hexdigest(),
                    }
        return {
            "state": state,
            "producer_ref": _GBRAIN_PRODUCER,
            "source_identity": _GBRAIN_SOURCE_IDENTITY,
            "source_revision": source_revision,
            "evidence": evidence,
            "reader_context": request.reader_context,
        }

    binding = AdvisoryReaderBinding(
        producer_ref=_GBRAIN_PRODUCER,
        source_identity=_GBRAIN_SOURCE_IDENTITY,
        source_revision=source_revision,
        reader=read,
    )
    readback = retrieve_advisory(binding, query, reader_context)
    return {
        "family": "c1_advisory_observation",
        "source_kind": "gbrain",
        "status": readback.state,
        "evidence": readback.evidence,
        "readback_metadata": {
            "producer_ref": readback.producer_ref,
            "source_identity": readback.source_identity,
            "source_revision": readback.source_revision,
        },
    }


def retrieve_harness_brain_source(
    source_ref: str,
    harness_brain_root: str | Path,
    *,
    query: str,
    reader_context: Mapping[str, Any],
    source_revision: str | None = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
    source_reader: Callable[..., Any] = read_harness_brain_source,
) -> dict[str, Any]:
    """Read one explicit Harness Brain source through the advisory contract."""
    try:
        receipt = source_reader(source_ref, harness_brain_root, max_bytes=max_bytes)
    except Exception:
        receipt = {
            "status": "unavailable",
            "source_ref": source_ref,
            "source_identity": source_ref,
            "readback": None,
            "reason": "unavailable",
        }

    state = "query_error"
    source_identity = source_ref if isinstance(source_ref, str) and source_ref else "harness_brain:unresolved"
    evidence: dict[str, Any] = {"record_count": 0, "source_receipt": "malformed_reader_result"}
    if isinstance(receipt, dict) and receipt.get("source_ref") == source_ref:
        identity = receipt.get("source_identity")
        if isinstance(identity, str) and identity:
            source_identity = identity
        source_readback = receipt.get("readback")
        if (
            set(receipt) == {"status", "source_ref", "source_identity", "readback"}
            and receipt["status"] == "available"
            and isinstance(receipt["source_identity"], str)
            and bool(receipt["source_identity"])
            and isinstance(source_readback, dict)
            and set(source_readback) == {"content", "byte_count"}
            and isinstance(source_readback["content"], bytes)
            and isinstance(source_readback["byte_count"], int)
            and not isinstance(source_readback["byte_count"], bool)
            and source_readback["byte_count"] == len(source_readback["content"])
        ):
            state = "match"
            evidence = {
                "record_count": 1,
                "content_digest": hashlib.sha256(source_readback["content"]).hexdigest(),
            }
        elif (
            set(receipt) == {"status", "source_ref", "source_identity", "readback", "reason"}
            and receipt["status"] == "unavailable"
            and source_readback is None
            and isinstance(receipt["reason"], str)
            and receipt["reason"] in _HARNESS_BRAIN_UNAVAILABLE_REASONS
        ):
            state = "unavailable"
            evidence = {"record_count": 0, "source_receipt": receipt["reason"]}

    binding = AdvisoryReaderBinding(
        producer_ref=_HARNESS_BRAIN_PRODUCER,
        source_identity=source_identity,
        source_revision=source_revision,
        reader=lambda request: {
            "state": state,
            "producer_ref": _HARNESS_BRAIN_PRODUCER,
            "source_identity": source_identity,
            "source_revision": source_revision,
            "evidence": evidence,
            "reader_context": request.reader_context,
        },
    )
    readback = retrieve_advisory(binding, query, reader_context)
    return {
        "family": "c1_advisory_observation",
        "source_kind": "harness_brain",
        "status": readback.state,
        "source_ref": source_ref,
        "evidence": readback.evidence,
        "readback_metadata": {
            "producer_ref": readback.producer_ref,
            "source_identity": readback.source_identity,
            "source_revision": readback.source_revision,
            "reader_context": readback.reader_context,
        },
    }


def retrieve_honcho_session_source(
    *,
    query: str,
    reader_context: Mapping[str, Any],
    session_key: str | None = None,
    binding_factory: Callable[[str | None], AdvisoryReaderBinding] = configured_honcho_session_binding,
) -> dict[str, Any]:
    """Read the configured Honcho session through the advisory contract."""
    binding = binding_factory(session_key)
    readback = retrieve_advisory(binding, query, reader_context)
    return {
        "family": "c1_advisory_observation",
        "source_kind": "honcho",
        "status": readback.state,
        "evidence": readback.evidence,
        "readback_metadata": {
            "producer_ref": readback.producer_ref,
            "source_identity": readback.source_identity,
            "source_revision": readback.source_revision,
        },
    }


def validate_compact_c(compact_c: dict[str, Any]) -> None:
    if not isinstance(compact_c, dict) or set(compact_c) != _REQUIRED:
        raise RetrievalError("compact_C has invalid contract shape")
    if any(not isinstance(compact_c[key], str) or not compact_c[key] for key in ("request_ref", "binding_ref")):
        raise RetrievalError("compact_C refs must be non-empty strings")
    c_shape = compact_c["C_shape"]
    if not isinstance(c_shape, dict) or set(c_shape) != _C_SHAPE_REQUIRED:
        raise RetrievalError("compact_C C_shape has invalid contract shape")
    if not isinstance(c_shape["intent"], str) or not c_shape["intent"]:
        raise RetrievalError("compact_C C_shape intent must be a non-empty string")
    if any(c_shape[key] in (None, "", []) for key in _C_SHAPE_DOMAINS):
        raise RetrievalError("compact_C C_shape values must be populated")
    if any(not isinstance(c_shape[key], str) or c_shape[key] not in values for key, values in _C_SHAPE_DOMAINS.items()):
        raise RetrievalError("compact_C C_shape value is outside its declared domain")
    direct_refs = compact_c["direct_source_refs"]
    if not isinstance(direct_refs, list) or any(not isinstance(ref, str) or not ref for ref in direct_refs):
        raise RetrievalError("compact_C direct_source_refs must be strings")


def _candidate(value: Any, source_kind: str) -> dict[str, Any]:
    if isinstance(value, str):
        value = {"ref": value}
    if not isinstance(value, dict) or not isinstance(value.get("ref"), str) or not value["ref"]:
        raise RetrievalError("source candidate requires ref")
    candidate = {"ref": value["ref"], "source_kind": source_kind}
    candidate.update({key: value[key] for key in _CANDIDATE_METADATA if key in value})
    return candidate


def retrieve(
    compact_c: dict[str, Any],
    advisory_source: Callable[[dict[str, Any]], dict[str, Any]],
    *,
    direct_reader: Callable[[str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    validate_compact_c(compact_c)
    candidates = []
    for ref in compact_c["direct_source_refs"]:
        value = direct_reader(ref) if direct_reader else {"ref": ref}
        if not isinstance(value, dict):
            raise RetrievalError("direct reader must return an object")
        candidates.append(_candidate({**value, "ref": ref}, "direct"))

    metadata: dict[str, Any] = {"direct_source_refs": list(compact_c["direct_source_refs"])}
    try:
        raw = advisory_source(dict(compact_c["C_shape"]))
    except (OSError, ConnectionError, TimeoutError) as exc:
        metadata["advisory_error"] = f"{type(exc).__name__}: {exc}"
        status = "unavailable"
    else:
        if not isinstance(raw, dict) or not isinstance(raw.get("matches", []), list):
            raise RetrievalError("advisory source must return matches array")
        candidates.extend(_candidate(match, "advisory_recall") for match in raw.get("matches", []))
        status = "match" if candidates else "no_match"

    return {
        "family": "c1_advisory_observation",
        "request_ref": compact_c["request_ref"],
        "binding_ref": compact_c["binding_ref"],
        "status": status,
        "source_candidates": candidates,
        "ref_metadata": metadata,
    }
