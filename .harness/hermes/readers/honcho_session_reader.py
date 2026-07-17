"""Read-only CPS advisory binding for the configured Hermes Honcho session."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Tuple


_CONTRACTS = Path(__file__).resolve().parents[1] / "contracts"
if str(_CONTRACTS) not in sys.path:
    sys.path.insert(0, str(_CONTRACTS))

from cps_advisory_reader_contract import AdvisoryReadRequest, AdvisoryReaderBinding


DEFAULT_HERMES_AGENT_ROOT = Path.home() / ".hermes" / "hermes-agent"
SEARCH_TOKEN_LIMIT = 256


def configured_honcho_session_binding(
    session_key: Optional[str] = None,
    *,
    agent_root: Path = DEFAULT_HERMES_AGENT_ROOT,
    config_loader: Optional[Callable[[], Any]] = None,
    client_factory: Optional[Callable[[Any], Any]] = None,
    manager_factory: Optional[Callable[..., Any]] = None,
) -> AdvisoryReaderBinding:
    """Bind the configured SDK client to one resolved Honcho session.

    Construction resolves the real configured session identity once. The bound
    reader only calls the SDK session-context and semantic-search read APIs; it
    never adds messages, saves, flushes, or creates conclusions.
    """
    try:
        config_loader, client_factory, manager_factory = _runtime_factories(
            agent_root, config_loader, client_factory, manager_factory
        )
        config = config_loader()
        resolved_key = session_key or config.resolve_session_name()
        if not isinstance(resolved_key, str) or not resolved_key:
            return _unavailable_binding("session_key_absent")
        if not bool(getattr(config, "enabled", False)):
            return _unavailable_binding("config_disabled", resolved_key)
        manager = manager_factory(honcho=client_factory(config), config=config)
        session = manager.get_or_create(resolved_key)
        return _available_binding(manager, resolved_key, session, config)
    except Exception:
        return _unavailable_binding("sdk_or_session_failure", session_key)


def _runtime_factories(
    agent_root: Path,
    config_loader: Optional[Callable[[], Any]],
    client_factory: Optional[Callable[[Any], Any]],
    manager_factory: Optional[Callable[..., Any]],
) -> Tuple[Callable[[], Any], Callable[[Any], Any], Callable[..., Any]]:
    if config_loader is not None and client_factory is not None and manager_factory is not None:
        return config_loader, client_factory, manager_factory
    if agent_root.exists() and str(agent_root) not in sys.path:
        sys.path.insert(0, str(agent_root))
    from plugins.memory.honcho.client import HonchoClientConfig, get_honcho_client
    from plugins.memory.honcho.session import HonchoSessionManager

    return (
        config_loader or HonchoClientConfig.from_global_config,
        client_factory or get_honcho_client,
        manager_factory or HonchoSessionManager,
    )


def _available_binding(manager: Any, session_key: str, session: Any, config: Any) -> AdvisoryReaderBinding:
    session_id = _identity_part(getattr(session, "honcho_session_id", None), session_key)
    producer_ref = "honcho-sdk:{0}:{1}".format(
        _identity_part(getattr(config, "workspace_id", None), "unknown-workspace"),
        _identity_part(getattr(config, "host", None), "unknown-host"),
    )
    source_identity = "honcho-sdk-session:{0}".format(session_id)

    def read(request: AdvisoryReadRequest) -> Mapping[str, Any]:
        try:
            context = manager.get_session_context(session_key, peer="user")
            search = manager.search_context(
                session_key, query=request.query, max_tokens=SEARCH_TOKEN_LIMIT, peer="user"
            )
            payload = {"context": context, "search": search}
            return {
                "state": "available",
                "producer_ref": producer_ref,
                "source_identity": source_identity,
                "evidence": {
                    "record_count": _record_count(context, search),
                    "content_digest": _digest(payload),
                    "source_receipt": _receipt(session),
                },
                "reader_context": dict(request.reader_context),
            }
        except Exception:
            return _unavailable_response(producer_ref, source_identity, request, "read_failure")

    return AdvisoryReaderBinding(producer_ref, source_identity, read)


def _unavailable_binding(reason: str, session_key: Optional[str] = None) -> AdvisoryReaderBinding:
    key = _identity_part(session_key, "unresolved")
    producer_ref = "honcho-sdk:unavailable"
    source_identity = "honcho-sdk-session:{0}".format(key)

    def read(request: AdvisoryReadRequest) -> Mapping[str, Any]:
        return _unavailable_response(producer_ref, source_identity, request, reason)

    return AdvisoryReaderBinding(producer_ref, source_identity, read)


def _unavailable_response(
    producer_ref: str, source_identity: str, request: AdvisoryReadRequest, reason: str
) -> Mapping[str, Any]:
    return {
        "state": "unavailable",
        "producer_ref": producer_ref,
        "source_identity": source_identity,
        "evidence": {"record_count": 0, "source_receipt": "honcho-session-reader:{0}".format(reason)},
        "reader_context": dict(request.reader_context),
    }


def _identity_part(value: Any, fallback: str) -> str:
    text = str(value).strip() if value is not None else ""
    return text or fallback


def _receipt(session: Any) -> str:
    parts = [
        "session={0}".format(_identity_part(getattr(session, "honcho_session_id", None), "unknown")),
        "user_peer={0}".format(_identity_part(getattr(session, "user_peer_id", None), "unknown")),
        "assistant_peer={0}".format(_identity_part(getattr(session, "assistant_peer_id", None), "unknown")),
    ]
    return ";".join(parts)[:256]


def _record_count(context: Any, search: Any) -> int:
    count = 0
    if isinstance(context, Mapping):
        recent = context.get("recent_messages")
        if isinstance(recent, list):
            count += len(recent)
        count += sum(1 for key, value in context.items() if key != "recent_messages" and value not in (None, "", [], {}))
    elif context not in (None, "", [], {}):
        count += 1
    if search not in (None, "", [], {}):
        count += 1
    return count


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
