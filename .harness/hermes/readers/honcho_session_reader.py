"""Read-only CPS advisory binding for the configured Hermes Honcho session."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Mapping, Optional, Tuple


_CONTRACTS = Path(__file__).resolve().parents[1] / "contracts"
if str(_CONTRACTS) not in sys.path:
    sys.path.insert(0, str(_CONTRACTS))

from cps_advisory_reader_contract import AdvisoryReadRequest, AdvisoryReaderBinding


DEFAULT_HERMES_AGENT_ROOT = Path.home() / ".hermes" / "hermes-agent"
DEFAULT_PROJECT_ENV = Path(__file__).resolve().parents[3] / ".env"
def configured_honcho_session_binding(
    session_key: Optional[str] = None,
    *,
    agent_root: Path = DEFAULT_HERMES_AGENT_ROOT,
    config_loader: Optional[Callable[[], Any]] = None,
    client_factory: Optional[Callable[[Any], Any]] = None,
    manager_factory: Optional[Callable[..., Any]] = None,
    env_loader: Optional[Callable[..., Any]] = None,
) -> AdvisoryReaderBinding:
    """Bind the configured SDK client to one resolved Honcho session.

    Construction resolves the real configured session identity once. The bound
    reader only calls the SDK session-context and semantic-search read APIs; it
    never adds messages, saves, flushes, or creates conclusions.
    """
    try:
        load_runtime_env = env_loader is not None or config_loader is None
        config_loader, client_factory, manager_factory = _runtime_factories(
            agent_root, config_loader, client_factory, manager_factory
        )
        if load_runtime_env:
            _load_honcho_runtime_env(agent_root, env_loader)
        config = config_loader()
        resolved_key = _resolve_honcho_session_key(config, session_key)
        if not isinstance(resolved_key, str) or not resolved_key:
            return _unavailable_binding("session_key_absent")
        if not bool(getattr(config, "enabled", False)):
            return _unavailable_binding("config_disabled", resolved_key)
        client = client_factory(config)
        manager = manager_factory(honcho=client, config=config)
        session = _lookup_existing_session(client, manager, resolved_key)
        if session is None:
            return _unavailable_binding("session_absent", resolved_key)
        return _available_binding(client, manager, resolved_key, session, config)
    except Exception:
        return _unavailable_binding("sdk_or_session_failure", session_key)


def _resolve_honcho_session_key(config: Any, gateway_session_key: Optional[str]) -> Any:
    if gateway_session_key:
        try:
            return config.resolve_session_name(gateway_session_key=gateway_session_key)
        except TypeError:
            # Older config test doubles expose the pre-gateway signature.
            return config.resolve_session_name()
    return config.resolve_session_name()


def _lookup_existing_session(client: Any, manager: Any, session_key: str) -> Any:
    """Read the SDK sessions-list endpoint without its workspace upsert wrapper."""
    if not hasattr(client, "_http"):
        raise ValueError("sessions lookup unavailable")
    try:
        from honcho.http import routes

        route = routes.sessions_list(client.workspace_id)
    except ImportError:
        route = "sessions:list"
    session_id = getattr(manager, "_sanitize_id", lambda value: value)(session_key)
    data = client._http.post(
        route,
        body={"filters": {"id": session_id}},
        query={"page": 1, "size": 1},
    )
    items = data.get("items") if isinstance(data, Mapping) else None
    if not isinstance(items, list):
        raise ValueError("malformed sessions lookup")
    for item in items:
        item_id = item.get("id") if isinstance(item, Mapping) else getattr(item, "id", None)
        if item_id == session_id:
            return SimpleNamespace(honcho_session_id=session_id)
    return None


def _load_honcho_runtime_env(
    agent_root: Path,
    env_loader: Optional[Callable[..., Any]],
) -> None:
    """Load canonical and bound-project dotenv before resolving Honcho config."""
    if agent_root.exists() and str(agent_root) not in sys.path:
        sys.path.insert(0, str(agent_root))
    if env_loader is None:
        from hermes_cli.env_loader import load_hermes_dotenv

        env_loader = load_hermes_dotenv
    assert env_loader is not None
    env_loader(project_env=DEFAULT_PROJECT_ENV)


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


def _available_binding(client: Any, manager: Any, session_key: str, session: Any, config: Any) -> AdvisoryReaderBinding:
    session_id = _identity_part(getattr(session, "honcho_session_id", None), session_key)
    producer_ref = "honcho-sdk:{0}:{1}".format(
        _identity_part(getattr(config, "workspace_id", None), "unknown-workspace"),
        _identity_part(getattr(config, "host", None), "unknown-host"),
    )
    user_peer = _identity_part(getattr(config, "peer_name", None), "user")
    source_identity = "honcho-sdk-semantic-peer:{0}".format(user_peer)

    def read(request: AdvisoryReadRequest) -> Mapping[str, Any]:
        try:
            search = _semantic_search(client, request.query, user_peer)
            payload = {"search": search}
            candidate = _candidate(search, request.query, source_identity)
            source_receipt = (
                candidate["source_receipt"] if candidate is not None
                else "semantic-query-session={0};peer={1}".format(session_id, user_peer)
            )
            return {
                "state": "available" if search else "no_match",
                "producer_ref": producer_ref,
                "source_identity": source_identity,
                "evidence": {
                    "record_count": len(search),
                    "content_digest": _digest(payload),
                    "source_receipt": source_receipt,
                },
                "reader_context": dict(request.reader_context),
                "candidate": candidate,
            }
        except Exception:
            return _unavailable_response(producer_ref, source_identity, request, "read_failure")

    return AdvisoryReaderBinding(producer_ref, source_identity, read)


def _semantic_search(client: Any, query: str, peer: str) -> list[Mapping[str, str]]:
    messages = client.search(query[:4000], filters={"peer_perspective": peer}, limit=3)
    return [
        {
            "content": getattr(message, "content", "") or "",
            "session_id": getattr(message, "session_id", "") or "",
            "message_id": getattr(message, "id", "") or "",
        }
        for message in messages or []
    ]


def _candidate(
    search: list[Mapping[str, str]],
    query: str = "",
    source_ref: str = "",
) -> Mapping[str, str] | None:
    query_terms = _terms(query)
    for hit in search:
        session_id = hit.get("session_id", "").strip()
        if not session_id:
            continue
        for sentence in _sentences(hit.get("content", "")):
            if len(sentence) <= 256 and query_terms & _terms(sentence):
                message_id = hit.get("message_id", "").strip()
                receipt = "semantic-session={0}".format(session_id)
                if message_id:
                    receipt += ";message={0}".format(message_id)
                return {
                    "clue": sentence,
                    "source_ref": source_ref[:256],
                    "source_receipt": receipt[:256],
                    "lifecycle": "candidate",
                    "observed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                }
    return None


def _terms(value: str) -> set[str]:
    return {
        token for token in re.findall(r"[\w-]+", value.casefold())
        if len(token) > 2 and token not in {"the", "and", "for", "with", "from", "this", "that"}
    }


def _sentences(value: str) -> list[str]:
    text = " ".join(value.split())
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text) if sentence.strip()]


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


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
