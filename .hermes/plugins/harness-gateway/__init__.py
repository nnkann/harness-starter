from __future__ import annotations

import hashlib
import sys
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path

_RUNTIME = Path(__file__).resolve().parents[3] / "runtime"
if _RUNTIME.is_dir() and str(_RUNTIME) not in sys.path:
    sys.path.insert(0, str(_RUNTIME))

from gateway.session import ProjectSessionBindingHold, resolve_project_session_binding
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


def _receipt_dir() -> Path:
    config = load_config()
    entry = cfg_get(config, "plugins", "entries", "harness-gateway", default={})
    if isinstance(entry, dict) and isinstance(entry.get("receipt_dir"), str):
        return Path(entry["receipt_dir"]).expanduser()
    return get_hermes_home() / "harness-gateway" / "receipts"


def _pre_gateway_dispatch(*, event, gateway, session_store, **kwargs):
    _INGRESS.set(None)
    try:
        binding = resolve_project_session_binding(event.source, gateway.config)
    except ProjectSessionBindingHold:
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
    return {"context": envelope.canonical_json}


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
    ctx.register_hook("pre_gateway_dispatch", _pre_gateway_dispatch)
    ctx.register_hook("pre_llm_call", _pre_llm_call)
    ctx.register_hook("post_llm_call", _post_llm_call)
