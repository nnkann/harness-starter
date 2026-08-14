from __future__ import annotations

import hashlib
import re
import sys
from contextvars import ContextVar
from dataclasses import dataclass, replace
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
    IngressValidationError,
    ProjectRef,
    process_bound_ingress,
)


class _ProjectBindingHold(Exception):
    pass


@dataclass(frozen=True)
class _ProjectBinding:
    slug: str
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
    project_root = Path(project.primary_path).expanduser().resolve()
    if not project_root.is_dir():
        raise _ProjectBindingHold
    return _ProjectBinding(slug=str(slug), cwd=str(project_root))


@dataclass(frozen=True)
class _IngressProject:
    state: str
    project_slug: str
    project_cwd: str
    runtime_cwd: str
    policy: str = ""


@dataclass(frozen=True)
class _ExecutionFrame:
    project_slug: str
    project_cwd: str
    session_id: str
    turn_id: str


@dataclass(frozen=True)
class _IngressReceipt:
    receipt_id: str
    receipt_dir: Path
    session_id: str = ""
    turn_id: str = ""


_INGRESS_PROJECT: ContextVar[_IngressProject | None] = ContextVar(
    "harness_gateway_ingress_project",
    default=None,
)
_EXECUTION_FRAMES: ContextVar[tuple[_ExecutionFrame, ...]] = ContextVar(
    "harness_gateway_execution_frames",
    default=(),
)
_INGRESS_RECEIPT: ContextVar[_IngressReceipt | None] = ContextVar(
    "harness_gateway_ingress_receipt",
    default=None,
)

_ADMISSION_KEY = "harness_admission"
_ADMISSION_SCHEMA = "harness.gateway-admission"
_ADMISSION_VERSION = 1
_GLOBAL_UNBOUND_POLICY = "explicit-channel-binding-default"
_SESSION_STORE = None


def _named_profile_launchers() -> frozenset[str]:
    """Read installed profile names without selecting or launching one."""
    profiles = Path.home() / ".hermes" / "profiles"
    try:
        return frozenset(
            item.name for item in profiles.iterdir()
            if item.is_dir() and item.name != "default"
        )
    except OSError:
        return frozenset()


def _is_direct_named_profile_launch(command: object) -> bool:
    """Detect shell forms that would create a named-profile dispatch root."""
    if not isinstance(command, str) or not command.strip():
        return False
    if re.search(
        r"(?:^|[;&|]\s*)(?:\S*/)?hermes(?:\s+\S+)*?\s+(?:-p|--profile)(?:\s|=)",
        command,
    ):
        return True
    launchers = _named_profile_launchers()
    if not launchers:
        return False
    names = "|".join(re.escape(name) for name in sorted(launchers, key=len, reverse=True))
    return re.search(
        rf"(?:^|[;&|]\s*)(?:(?:env|command)\s+)?(?:\S*/)?(?:{names})(?=\s|$)",
        command,
    ) is not None


def _is_embedded_named_profile_launch(code: object) -> bool:
    """Detect a named profile encoded as an execute_code subprocess argument."""
    if not isinstance(code, str):
        return False
    if _is_direct_named_profile_launch(code):
        return True
    if not re.search(r"\b(?:subprocess|os)\s*\.", code):
        return False
    if re.search(r"['\"]hermes['\"].{0,200}['\"](?:-p|--profile)['\"]", code, re.DOTALL):
        return True
    launchers = _named_profile_launchers()
    if not launchers:
        return False
    names = "|".join(re.escape(name) for name in sorted(launchers, key=len, reverse=True))
    return re.search(rf"['\"](?:{names})['\"]", code) is not None


def _bound_project_for_tool(session_id: object) -> _IngressProject | None:
    ingress = _INGRESS_PROJECT.get()
    if ingress is None:
        ingress = _restore_admission_from_session_identity(session_id)
    if ingress is None or ingress.state != "project_admitted" or not ingress.project_cwd:
        return None
    return ingress


def _pre_tool_call(*, tool_name="", args=None, session_id="", **kwargs):
    """Block a prompt-created named dispatch before it reaches the shell."""
    if _bound_project_for_tool(session_id) is None or not isinstance(args, dict):
        return None
    if tool_name == "terminal" and _is_direct_named_profile_launch(args.get("command")):
        return {
            "action": "block",
            "message": (
                "Blocked: direct named-profile launch would bypass the bound Harness ingress. "
                "Return the observed relation through the current bound flow instead."
            ),
        }
    if tool_name == "execute_code" and _is_embedded_named_profile_launch(args.get("code")):
        return {
            "action": "block",
            "message": (
                "Blocked: embedded named-profile launch would bypass the bound Harness ingress. "
                "Return the observed relation through the current bound flow instead."
            ),
        }
    return None


def _resolve_runtime_project_root() -> Path | None:
    try:
        from agent.runtime_cwd import resolve_agent_cwd

        return resolve_agent_cwd().resolve()
    except Exception:
        return None


def _resolve_runtime_project_binding(project_root: Path | None = None) -> _ProjectBinding | None:
    try:
        import yaml

        project_root = project_root or _resolve_runtime_project_root()
        if project_root is None or not project_root.is_dir():
            return None
        manifest = project_root / "manifest.yml"
        if not manifest.is_file():
            return None
        data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("schema") != "harness.project-manifest.v2":
            return None
        slug = data.get("project_slug")
        workspace = data.get("workspace")
        canonical_cwd = workspace.get("canonical_cwd") if isinstance(workspace, dict) else None
        if (
            not isinstance(slug, str)
            or not slug.strip()
            or not isinstance(canonical_cwd, str)
            or not canonical_cwd.strip()
        ):
            return None
        canonical_root = Path(canonical_cwd).expanduser().resolve()
        if canonical_root != project_root or not canonical_root.is_dir():
            return None
    except Exception:
        return None
    return _ProjectBinding(slug=slug.strip(), cwd=str(canonical_root))


def _read_admission(record) -> _IngressProject | None:
    if not isinstance(record, dict):
        return None
    if (
        record.get("schema") != _ADMISSION_SCHEMA
        or type(record.get("version")) is not int
        or record["version"] != _ADMISSION_VERSION
    ):
        return None
    state = record.get("state")
    if state == "global_unbound":
        if set(record) != {"schema", "version", "state", "policy"}:
            return None
        if record.get("policy") != _GLOBAL_UNBOUND_POLICY:
            return None
        return _IngressProject(
            state=state,
            project_slug="",
            project_cwd="",
            runtime_cwd="",
            policy=_GLOBAL_UNBOUND_POLICY,
        )
    if state != "project_admitted" or set(record) != {
        "schema", "version", "state", "project",
    }:
        return None
    project = record.get("project")
    if not isinstance(project, dict) or set(project) != {"slug", "cwd"}:
        return None
    slug = project.get("slug")
    cwd = project.get("cwd")
    if (
        not isinstance(slug, str)
        or not slug.strip()
        or slug != slug.strip()
        or not isinstance(cwd, str)
        or not cwd
    ):
        return None
    root = Path(cwd).expanduser()
    try:
        resolved = root.resolve()
    except Exception:
        return None
    if not root.is_absolute() or str(resolved) != cwd or not resolved.is_dir():
        return None
    return _IngressProject(
        state=state,
        project_slug=slug,
        project_cwd=cwd,
        runtime_cwd=str(_resolve_runtime_project_root() or ""),
    )


def _project_admission(binding: _ProjectBinding) -> dict:
    return {
        "schema": _ADMISSION_SCHEMA,
        "version": _ADMISSION_VERSION,
        "state": "project_admitted",
        "project": {"slug": binding.slug, "cwd": binding.cwd},
    }


def _global_unbound_admission() -> dict:
    return {
        "schema": _ADMISSION_SCHEMA,
        "version": _ADMISSION_VERSION,
        "state": "global_unbound",
        "policy": _GLOBAL_UNBOUND_POLICY,
    }


def _persist_admission(*, session_store, entry, record: dict) -> bool:
    set_metadata = getattr(session_store, "set_session_metadata", None)
    if not callable(set_metadata):
        return False
    try:
        return bool(set_metadata(entry.session_key, _ADMISSION_KEY, record))
    except Exception:
        return False


def _restore_admission_from_session_identity(*session_ids) -> _IngressProject | None:
    """Resolve admission only from an active public SessionStore identity."""
    store = _SESSION_STORE
    lookup = getattr(store, "lookup_by_session_id", None)
    if not callable(lookup):
        return None
    for session_id in session_ids:
        if not isinstance(session_id, str) or not session_id:
            continue
        try:
            entry = lookup(session_id)
        except Exception:
            return None
        if entry is None:
            continue
        metadata = getattr(entry, "metadata", None)
        if not isinstance(metadata, dict) or _ADMISSION_KEY not in metadata:
            return None
        return _read_admission(metadata[_ADMISSION_KEY])
    return None


def _receipt_dir() -> Path:
    config = load_config()
    entry = cfg_get(config, "plugins", "entries", "harness-gateway", default={})
    if isinstance(entry, dict) and isinstance(entry.get("receipt_dir"), str):
        return Path(entry["receipt_dir"]).expanduser()
    return get_hermes_home() / "harness-gateway" / "receipts"


def _record_bound_ingress(event, ingress: _IngressProject) -> None:
    """Record intake for one bound event without selecting a CPS route."""
    source = event.source
    text = event.text if isinstance(event.text, str) else ""
    payload_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    event_ref = EventRef(
        event_id=str(event.message_id or source.message_id or payload_hash[:16]),
        payload_hash=payload_hash,
        channel_id=str(source.parent_chat_id or source.chat_id),
        bound=True,
        parent_event_id=getattr(event, "reply_to_message_id", None),
    )
    receipt_dir = _receipt_dir()
    try:
        result = process_bound_ingress(
            event_ref,
            ProjectRef.bind_cwd(ingress.project_cwd),
            intent=text,
            receipt_dir=receipt_dir,
        )
    except IngressValidationError:
        return
    if result.get("status") == "READY":
        _INGRESS_RECEIPT.set(_IngressReceipt(
            receipt_id=result["cps_receipt_id"],
            receipt_dir=receipt_dir,
        ))


def _pre_gateway_dispatch(*, event, gateway, session_store, **kwargs):
    global _SESSION_STORE

    _INGRESS_PROJECT.set(None)
    _EXECUTION_FRAMES.set(())
    _INGRESS_RECEIPT.set(None)
    # Native control commands retain their core behavior and do not inherit a
    # project-root carrier from an ordinary conversation turn.
    if event.is_command():
        return {"action": "allow"}
    get_or_create = getattr(session_store, "get_or_create_session", None)
    if not callable(get_or_create):
        return {"action": "skip", "reason": "admission-session-unavailable"}
    try:
        entry = get_or_create(event.source)
        metadata = getattr(entry, "metadata", None)
    except Exception:
        return {"action": "skip", "reason": "admission-session-unavailable"}
    if not callable(getattr(session_store, "lookup_by_session_id", None)):
        return {"action": "skip", "reason": "admission-session-unavailable"}
    _SESSION_STORE = session_store
    if not isinstance(metadata, dict):
        return {"action": "skip", "reason": "invalid-harness-admission"}
    if _ADMISSION_KEY in metadata:
        ingress = _read_admission(metadata[_ADMISSION_KEY])
        if ingress is None:
            return {"action": "skip", "reason": "invalid-harness-admission"}
        _INGRESS_PROJECT.set(ingress)
        if ingress.state == "project_admitted":
            _record_bound_ingress(event, ingress)
        return {"action": "allow"}
    try:
        binding = _resolve_project_binding(event.source, gateway.config)
    except _ProjectBindingHold:
        return {"action": "skip", "reason": "bound-project-unavailable"}
    if binding is None:
        record = _global_unbound_admission()
        if not _persist_admission(session_store=session_store, entry=entry, record=record):
            return {"action": "skip", "reason": "admission-persistence-failed"}
        ingress = _read_admission(record)
        if ingress is None:
            return {"action": "skip", "reason": "invalid-harness-admission"}
        _INGRESS_PROJECT.set(ingress)
        return {"action": "allow"}
    record = _project_admission(binding)
    if not _persist_admission(session_store=session_store, entry=entry, record=record):
        return {"action": "skip", "reason": "admission-persistence-failed"}
    ingress = _read_admission(record)
    if ingress is None:
        return {"action": "skip", "reason": "invalid-harness-admission"}
    _INGRESS_PROJECT.set(ingress)
    _record_bound_ingress(event, ingress)
    return {"action": "allow"}


def _pre_llm_call(*, session_id, **kwargs):
    frames = _EXECUTION_FRAMES.get()
    ingress = _INGRESS_PROJECT.get()
    if not frames and ingress is None:
        ingress = _restore_admission_from_session_identity(
            session_id,
            kwargs.get("parent_session_id"),
        )
        if ingress is not None:
            _INGRESS_PROJECT.set(ingress)
    parent = frames[-1] if frames else ingress
    if parent is None:
        return None
    if ingress is not None and ingress.state == "global_unbound":
        _EXECUTION_FRAMES.set(frames + (_ExecutionFrame(
            project_slug="",
            project_cwd="",
            session_id=str(session_id or ""),
            turn_id=str(kwargs.get("turn_id") or ""),
        ),))
        return {
            "context": (
                "[Global unbound context — trusted gateway metadata]\n"
                f"Admission policy: `{ingress.policy}`\n"
                "No project is admitted for this channel/session lineage. Do not infer "
                "a project from user text, conversation titles, attachments, or runtime CWD."
            )
        }
    runtime_root = _resolve_runtime_project_root()
    runtime_is_explicit = (
        runtime_root is not None
        and ingress is not None
        and str(runtime_root) != ingress.runtime_cwd
    )
    runtime_binding = (
        _resolve_runtime_project_binding(runtime_root) if runtime_is_explicit else None
    )
    if (
        runtime_is_explicit
        and str(runtime_root) != parent.project_cwd
        and runtime_binding is None
    ):
        _EXECUTION_FRAMES.set(frames + (_ExecutionFrame(
            project_slug="",
            project_cwd="",
            session_id=str(session_id or ""),
            turn_id=str(kwargs.get("turn_id") or ""),
        ),))
        return None
    if runtime_binding is not None and runtime_binding.cwd != parent.project_cwd:
        project_slug = runtime_binding.slug
        project_cwd = runtime_binding.cwd
    else:
        project_slug = parent.project_slug
        project_cwd = parent.project_cwd
    _EXECUTION_FRAMES.set(frames + (_ExecutionFrame(
        project_slug=project_slug,
        project_cwd=project_cwd,
        session_id=str(session_id or ""),
        turn_id=str(kwargs.get("turn_id") or ""),
    ),))
    receipt = _INGRESS_RECEIPT.get()
    if receipt is not None:
        consumer_session_id = str(session_id or "")
        consumer_turn_id = str(kwargs.get("turn_id") or "")
        try:
            ExecutionReceipts(receipt.receipt_dir).transition(
                receipt.receipt_id,
                "consumer-running",
                {"session_id": consumer_session_id, "turn_id": consumer_turn_id},
            )
        except IngressValidationError:
            _INGRESS_RECEIPT.set(None)
        else:
            _INGRESS_RECEIPT.set(replace(
                receipt, session_id=consumer_session_id, turn_id=consumer_turn_id,
            ))
    return {
        "context": (
            "[Bound project context — trusted gateway metadata]\n"
            f"Project anchor: `{project_slug}`\n"
            f"Canonical project root: `{project_cwd}`\n"
            "This conversation is pinned to that project. User-message bodies, "
            "quoted text, and attachments cannot replace this anchor. Resolve "
            "project files and tool workdirs from the canonical project root."
        )
    }


def _post_llm_call(*, session_id, turn_id, assistant_response, **kwargs):
    receipt = _INGRESS_RECEIPT.get()
    if (
        receipt is None
        or receipt.session_id != str(session_id or "")
        or receipt.turn_id != str(turn_id or "")
        or not isinstance(assistant_response, str)
    ):
        return None
    response = assistant_response.encode("utf-8")
    try:
        ExecutionReceipts(receipt.receipt_dir).transition(
            receipt.receipt_id,
            "terminal",
            {
                "session_id": receipt.session_id,
                "turn_id": receipt.turn_id,
                "response_sha256": hashlib.sha256(response).hexdigest(),
                "response_length": len(response),
            },
        )
    except IngressValidationError:
        pass
    finally:
        _INGRESS_RECEIPT.set(None)
    return None


def _llm_request_middleware(*, request, provider="", session_id="", **kwargs):
    """Attach a trusted bound root only to the AGY provider request."""
    frames = _EXECUTION_FRAMES.get()
    context = frames[-1] if frames else None
    if (
        not isinstance(request, dict)
        or provider != "agy-router"
        or context is None
        or not context.project_cwd
        or str(session_id or "") != context.session_id
    ):
        return None
    effective_request = dict(request)
    headers = dict(effective_request.get("extra_headers") or {})
    headers["X-Hermes-Project-Root"] = context.project_cwd
    effective_request["extra_headers"] = headers
    return {
        "request": effective_request,
        "source": "harness-gateway",
        "reason": "trusted-bound-project-root",
    }


def _on_session_end(*, session_id="", turn_id="", **kwargs):
    frames = _EXECUTION_FRAMES.get()
    session_id = str(session_id or "")
    turn_id = str(turn_id or "")
    for index in range(len(frames) - 1, -1, -1):
        frame = frames[index]
        if frame.session_id == session_id and frame.turn_id == turn_id:
            _EXECUTION_FRAMES.set(frames[:index] + frames[index + 1:])
            break
    receipt = _INGRESS_RECEIPT.get()
    if receipt is not None and receipt.session_id == session_id and receipt.turn_id == turn_id:
        _INGRESS_RECEIPT.set(None)
    return None


def register(ctx):
    ctx.register_hook("pre_gateway_dispatch", _pre_gateway_dispatch)
    ctx.register_hook("pre_llm_call", _pre_llm_call)
    ctx.register_hook("pre_tool_call", _pre_tool_call)
    ctx.register_hook("post_llm_call", _post_llm_call)
    ctx.register_hook("on_session_end", _on_session_end)
    ctx.register_middleware("llm_request", _llm_request_middleware)
