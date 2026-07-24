from __future__ import annotations

import hashlib
import importlib
import json
import logging
import sys
import time
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path

_RUNTIME = Path(__file__).resolve().parents[3] / "runtime"
if _RUNTIME.is_dir() and str(_RUNTIME) not in sys.path:
    sys.path.insert(0, str(_RUNTIME))

from hermes_cli import projects_db
from hermes_cli.config import cfg_get, load_config
from hermes_constants import get_hermes_home
from harness_runtime import (
    EventRef,
    ExecutionReceipts,
    IngressIntake,
    IngressValidationError,
    ProjectRef,
    process_bound_ingress,
)

_INTAKE = IngressIntake()
_LOG = logging.getLogger(__name__)
_SOURCE_KINDS = ("honcho", "harness_brain")
_SOURCE_STATUSES = {"available", "match", "no_match", "unavailable", "query_error"}
_EVIDENCE_KEYS = {"content_digest", "count", "digest", "record_count", "source_receipt"}
_READBACK_KEYS = {"producer_ref", "source_identity", "source_revision"}
_CANDIDATE_KEYS = {"clue", "source_ref", "source_receipt", "lifecycle", "observed_at"}
_PROHIBITED_CLUE_FRAGMENTS = (
    " because ", " due to ", " therefore ", " thus ", " causes ", " caused ",
    " leads to ", " must ", " should ", " need to ", " please ", " instruct ",
    " implement ", " change ", " restart ", " run ", " use ", " ensure ",
    " conclusion", " verdict", " proves ", " confirmed ", " authoritative",
    " authority", " official ", " approved ", " mandated ",
)


class _ProjectBindingHold(Exception):
    pass


@dataclass(frozen=True)
class _ProjectBinding:
    cwd: str


def _resolve_project_binding(source, config):
    if getattr(source.platform, "value", source.platform) != "discord":
        return None
    platform_config = config.platforms.get(source.platform)
    extra = getattr(platform_config, "extra", {}) if platform_config else {}
    bindings = extra.get("channel_project_bindings") if isinstance(extra, dict) else None
    if bindings is None:
        return None
    if not isinstance(bindings, dict):
        raise _ProjectBindingHold
    for identifier in (
        source.thread_id,
        source.chat_id,
        source.parent_chat_id,
        source.chat_name,
    ):
        key = str(identifier) if identifier is not None else None
        if key is not None and key in bindings:
            slug = bindings[key]
            break
    else:
        return None
    if not isinstance(slug, str) or not slug.strip():
        raise _ProjectBindingHold
    try:
        with projects_db.connect_closing() as conn:
            project = projects_db.get_project(conn, str(slug))
    except Exception as exc:
        raise _ProjectBindingHold from exc
    if project is None or project.archived or not project.primary_path:
        raise _ProjectBindingHold
    return _ProjectBinding(cwd=project.primary_path)


@dataclass(frozen=True)
class _IngressEnvelope:
    receipt_id: str
    canonical_json: str
    receipt_dir: Path
    state: str = "ready"
    session_id: str = ""
    turn_id: str = ""
    target_profile: str = "default"


_INGRESS: ContextVar[_IngressEnvelope | None] = ContextVar(
    "harness_gateway_ingress",
    default=None,
)


def _retrieval_adapter():
    tools = Path(__file__).resolve().parents[3] / ".harness" / "hermes" / "tools"
    if not tools.is_dir():
        raise RuntimeError("project retrieval adapter unavailable")
    if str(tools) not in sys.path:
        sys.path.insert(0, str(tools))
    return importlib.import_module("cps_c1_retrieval_adapter")


def _read_honcho(*, query, session_key, reader_context):
    return _retrieval_adapter().retrieve_honcho_session_source(
        query=query, reader_context=reader_context, session_key=session_key
    )


def _read_harness_brain(*, query, session_key, reader_context):
    del session_key
    project_root = Path(__file__).resolve().parents[3]
    return _retrieval_adapter().retrieve_harness_brain_source(
        f"projects/{project_root.name}/decisions/cps-equation-ssot.md",
        project_root.parent / "harness-brain",
        query=query,
        reader_context=reader_context,
    )


_SOURCE_READERS = {
    "honcho": _read_honcho,
    "harness_brain": _read_harness_brain,
}


def _unavailable_observation(source_kind, receipt="reader_unavailable"):
    return {
        "source": source_kind,
        "status": "unavailable",
        "evidence": {"record_count": 0, "source_receipt": receipt},
    }


def _bounded_candidate(value, evidence, source_identity=None):
    if (
        not isinstance(value, dict)
        or set(value) != _CANDIDATE_KEYS
        or value.get("lifecycle") != "candidate"
        or value.get("source_receipt") != evidence.get("source_receipt")
        or source_identity is not None and value.get("source_ref") != source_identity
        or not isinstance(evidence.get("record_count"), int)
        or isinstance(evidence.get("record_count"), bool)
        or evidence["record_count"] < 1
        or not isinstance(evidence.get("content_digest"), str)
        or len(evidence["content_digest"]) != 64
        or any(
            not isinstance(value.get(key), str)
            or not value[key]
            or len(value[key]) > 256
            for key in _CANDIDATE_KEYS - {"lifecycle"}
        )
    ):
        return None
    clue = " ".join(value["clue"].split())
    folded = f" {clue.casefold()} "
    if (
        not clue
        or any(mark in clue for mark in '"\'“”‘’')
        or any(fragment in folded for fragment in _PROHIBITED_CLUE_FRAGMENTS)
    ):
        return None
    candidate = dict(value)
    candidate["clue"] = clue
    return candidate


def _normalize_observation(source_kind, result):
    if not isinstance(result, dict) or result.get("source_kind") != source_kind:
        return _unavailable_observation(source_kind, "malformed_result")
    status = result.get("status")
    evidence = result.get("evidence")
    if status not in _SOURCE_STATUSES or not isinstance(evidence, dict):
        return _unavailable_observation(source_kind, "malformed_result")
    bounded_evidence = {
        key: value
        for key, value in evidence.items()
        if key in _EVIDENCE_KEYS
        and (
            isinstance(value, int) and not isinstance(value, bool) and value >= 0
            or isinstance(value, str) and 0 < len(value) <= 256
            or value is None
        )
    }
    observation = {"source": source_kind, "status": status, "evidence": bounded_evidence}
    metadata = result.get("readback_metadata")
    if isinstance(metadata, dict):
        bounded_metadata = {
            key: value
            for key, value in metadata.items()
            if key in _READBACK_KEYS
            and (value is None or isinstance(value, str) and 0 < len(value) <= 256)
        }
        if bounded_metadata:
            observation["readback"] = bounded_metadata
    source_ref = result.get("source_ref")
    if isinstance(source_ref, str) and 0 < len(source_ref) <= 256:
        observation["source_ref"] = source_ref
    candidate = _bounded_candidate(
        result.get("candidate"), bounded_evidence,
        observation.get("readback", {}).get("source_identity"),
    )
    if candidate is not None:
        observation["candidate"] = candidate
    return observation


def _gateway_ingress_retrieval_provider(
    *, original_user_message, session_id, session_key, platform, sender_id
):
    del session_id, platform, sender_id
    if not isinstance(original_user_message, str):
        raise TypeError("original_user_message must be a string")
    message_bytes = original_user_message.encode("utf-8")
    reader_context = {
        "request_ref": "gateway-ingress:" + hashlib.sha256(message_bytes).hexdigest()[:16]
    }
    def read_once(source_kind):
        started = time.perf_counter()
        try:
            result = _SOURCE_READERS[source_kind](
                query=original_user_message,
                session_key=session_key,
                reader_context=reader_context,
            )
        except Exception:
            observation = _unavailable_observation(source_kind)
        else:
            observation = _normalize_observation(source_kind, result)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
        _LOG.warning(
            "[memory-retrieval] source=%s session=%s query_sha=%s status=%s record_count=%s elapsed_ms=%s",
            source_kind,
            session_key,
            reader_context["request_ref"].rsplit(":", 1)[-1],
            observation.get("status"),
            observation.get("evidence", {}).get("record_count"),
            elapsed_ms,
        )
        return observation

    direct = read_once("honcho")
    observations = [direct]
    if "candidate" not in direct:
        observations.append(read_once("harness_brain"))
    return {
        "C": {
            "boundary": "bound_project_ingress",
            "cardinality": "uncertain",
            "continuity": "unknown",
            "current_state_need": "required",
            "intent_length": len(original_user_message),
            "intent_sha256": hashlib.sha256(message_bytes).hexdigest(),
        },
        "E": observations,
        "uncertainty": [
            {"source": item["source"], "status": item["status"]}
            for item in observations
            if item["status"] in {"unavailable", "query_error"}
        ],
    }


def _base_compact_c(envelope, status):
    intent = json.loads(envelope.canonical_json)["intent"]
    intent_bytes = intent.encode("utf-8")
    return {
        "C": {
            "boundary": "bound_project_ingress",
            "cardinality": "uncertain",
            "continuity": "unknown",
            "current_state_need": "required",
            "intent_length": len(intent),
            "intent_sha256": hashlib.sha256(intent_bytes).hexdigest(),
        },
        "E": [],
        "uncertainty": [{"source": "provider", "status": status}],
    }


def _validated_compact_c(value):
    if not isinstance(value, dict) or set(value) != {"C", "E", "uncertainty"}:
        return None
    expected_c = {
        "boundary", "cardinality", "continuity", "current_state_need",
        "intent_length", "intent_sha256",
    }
    if not isinstance(value["C"], dict) or set(value["C"]) != expected_c:
        return None
    if not isinstance(value["E"], list) or not 1 <= len(value["E"]) <= len(_SOURCE_KINDS):
        return None
    if [item.get("source") for item in value["E"] if isinstance(item, dict)] != list(_SOURCE_KINDS[:len(value["E"])]):
        return None
    if any(
        not isinstance(item, dict)
        or set(item) - {"source", "status", "evidence", "readback", "source_ref", "candidate"}
        or item.get("status") not in _SOURCE_STATUSES
        or not isinstance(item.get("evidence"), dict)
        or set(item["evidence"]) - _EVIDENCE_KEYS
        or "readback" in item
        and (
            not isinstance(item["readback"], dict)
            or set(item["readback"]) - _READBACK_KEYS
        )
        or "candidate" in item
        and _bounded_candidate(
            item["candidate"], item["evidence"],
            item.get("readback", {}).get("source_identity"),
        ) is None
        for item in value["E"]
    ):
        return None
    if (
        value["C"].get("boundary") != "bound_project_ingress"
        or value["C"].get("cardinality") not in {"single", "multiple", "uncertain"}
        or value["C"].get("continuity") not in {"new", "follow_up", "rework", "linked", "incident", "unknown"}
        or value["C"].get("current_state_need") not in {"required", "not_required", "uncertain"}
        or not isinstance(value["C"].get("intent_length"), int)
        or isinstance(value["C"]["intent_length"], bool)
        or value["C"]["intent_length"] < 0
        or not isinstance(value["C"].get("intent_sha256"), str)
        or len(value["C"]["intent_sha256"]) != 64
    ):
        return None
    if not isinstance(value["uncertainty"], list) or any(
        not isinstance(item, dict)
        or set(item) != {"source", "status"}
        or item["source"] not in {*_SOURCE_KINDS, "provider"}
        or item["status"] not in {"unavailable", "query_error", "provider_error", "malformed_result"}
        for item in value["uncertainty"]
    ):
        return None
    return value


def _receipt_dir() -> Path:
    config = load_config()
    entry = cfg_get(config, "plugins", "entries", "harness-gateway", default={})
    if isinstance(entry, dict) and isinstance(entry.get("receipt_dir"), str):
        return Path(entry["receipt_dir"]).expanduser()
    return get_hermes_home() / "harness-gateway" / "receipts"


def _pre_gateway_dispatch(*, event, gateway, session_store, **kwargs):
    _INGRESS.set(None)
    try:
        binding = _resolve_project_binding(event.source, gateway.config)
    except _ProjectBindingHold:
        return {"action": "skip", "reason": "harness-project-binding-hold"}
    if binding is None:
        return {"action": "allow"}

    payload_hash = hashlib.sha256(event.text.encode("utf-8")).hexdigest()
    event_id = event.message_id or event.source.message_id or payload_hash[:16]
    channel_id = event.source.parent_chat_id or event.source.chat_id
    event_ref = EventRef(
        event_id=str(event_id),
        payload_hash=payload_hash,
        channel_id=str(channel_id),
        bound=True,
        parent_event_id=event.reply_to_message_id,
    )
    receipt_dir = _receipt_dir()
    try:
        result = process_bound_ingress(
            event_ref,
            ProjectRef.bind_cwd(binding.cwd, allow_bootstrap_manifest=True),
            intent=event.text,
            receipt_dir=receipt_dir,
            intake=_INTAKE,
        )
    except IngressValidationError as exc:
        return {"action": "skip", "reason": f"harness-ingress-rejected:{exc}"}
    if result["status"] == "READY":
        _INGRESS.set(
            _IngressEnvelope(
                receipt_id=result["cps_receipt_id"],
                canonical_json=result["canonical_packet"],
                receipt_dir=receipt_dir,
            )
        )
        return {"action": "allow"}
    return {
        "action": "skip",
        "reason": f"harness-ingress-{result['status'].lower()}",
        "cps_receipt_id": result["cps_receipt_id"],
    }


def _pre_llm_call(
    *,
    session_id,
    user_message,
    platform,
    sender_id,
    **kwargs,
):
    envelope = _INGRESS.get()
    if envelope is None or envelope.state != "ready":
        return None
    session_id = str(session_id or "")
    turn_id = str(kwargs.get("turn_id") or "")
    retrieve = kwargs.get("gateway_ingress_retrieve")
    if callable(retrieve):
        try:
            retrieval = retrieve(original_user_message=user_message)
        except Exception:
            compact_c = _base_compact_c(envelope, "provider_error")
        else:
            status = getattr(retrieval, "status", None)
            if status == "available":
                compact_c = _validated_compact_c(getattr(retrieval, "results", None))
                if compact_c is None:
                    compact_c = _base_compact_c(envelope, "malformed_result")
            elif status in {"unavailable", "provider_error"}:
                compact_c = _base_compact_c(envelope, status)
            else:
                compact_c = _base_compact_c(envelope, "malformed_result")
    else:
        compact_c = _base_compact_c(envelope, "unavailable")
    receipts = ExecutionReceipts(envelope.receipt_dir)
    try:
        receipts.transition(
            envelope.receipt_id,
            "route",
            {
                "schema": "harness.gateway.ingress-packet.v1",
                "target_profile": envelope.target_profile,
            },
        )
        receipts.transition(
            envelope.receipt_id,
            "running",
            {
                "profile": envelope.target_profile,
                "session_id": session_id,
                "turn_id": turn_id,
            },
        )
    except IngressValidationError:
        _INGRESS.set(None)
        return None
    except BaseException:
        _INGRESS.set(None)
        raise
    _INGRESS.set(
        _IngressEnvelope(
            receipt_id=envelope.receipt_id,
            canonical_json=envelope.canonical_json,
            receipt_dir=envelope.receipt_dir,
            state="running",
            session_id=session_id,
            turn_id=turn_id,
            target_profile=envelope.target_profile,
        )
    )
    packet = json.loads(envelope.canonical_json)
    packet["compact_C"] = compact_c
    context = json.dumps(packet, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return {"context": context}


def _post_llm_call(*, session_id, turn_id, assistant_response, **kwargs):
    envelope = _INGRESS.get()
    if envelope is None or envelope.state != "running":
        return None
    if not isinstance(assistant_response, str):
        evidence = {"status": "rejected", "reason": "transport-response-invalid"}
    else:
        response_bytes = assistant_response.encode("utf-8")
        evidence = {
            "status": "completed",
            "response_sha256": hashlib.sha256(response_bytes).hexdigest(),
            "response_length": len(assistant_response),
            "session_id": envelope.session_id,
            "turn_id": envelope.turn_id,
            "target_profile": envelope.target_profile,
        }
    try:
        ExecutionReceipts(envelope.receipt_dir).transition(
            envelope.receipt_id,
            "terminal",
            evidence,
        )
    finally:
        _INGRESS.set(None)
    return None


def register(ctx):
    if not ctx.register_gateway_ingress_retrieval_provider(
        _gateway_ingress_retrieval_provider
    ):
        raise RuntimeError("gateway ingress retrieval provider registration conflict")
    ctx.register_hook("pre_gateway_dispatch", _pre_gateway_dispatch)
    ctx.register_hook("pre_llm_call", _pre_llm_call)
    ctx.register_hook("post_llm_call", _post_llm_call)
