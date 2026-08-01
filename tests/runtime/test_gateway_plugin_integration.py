from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import shutil
import site
import subprocess
import sys
from pathlib import Path
from types import MethodType, SimpleNamespace

import pytest

CORE = Path("/Users/kann/.hermes/hermes-agent")
CORE_SITE_PACKAGES = (
    CORE
    / "venv"
    / "lib"
    / f"python{sys.version_info.major}.{sys.version_info.minor}"
    / "site-packages"
)
REPO = Path(__file__).resolve().parents[2]
RUNTIME = REPO / "runtime"
PLUGIN = REPO / ".hermes" / "plugins" / "harness-gateway"
for module_root in (CORE_SITE_PACKAGES, CORE, RUNTIME):
    assert module_root.is_dir(), f"required integration-test module root is absent: {module_root}"
    if module_root == CORE_SITE_PACKAGES:
        # The test exercises the checked-out Hermes core. Resolve its exact
        # installed runtime dependencies from the same core venv instead of
        # duplicating Hermes dependencies in the harness test extra.
        site.addsitedir(str(module_root))
    if str(module_root) not in sys.path:
        sys.path.insert(0, str(module_root))

from gateway.config import Platform, load_gateway_config
from gateway.platforms.base import MessageEvent
from gateway.run import GatewayRunner
from gateway.session import SessionSource
from agent.turn_finalizer import finalize_turn
from hermes_cli import plugins as hermes_plugins
from hermes_cli.middleware import apply_llm_request_middleware
from hermes_cli import projects_db
from hermes_constants import reset_hermes_home_override, set_hermes_home_override


def _git(path: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(path), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _project(path: Path, manifest: str | None) -> Path:
    path.mkdir()
    _git(path, "init")
    _git(path, "config", "user.name", "Test User")
    _git(path, "config", "user.email", "test@example.com")
    if manifest is not None:
        (path / "manifest.yml").write_text(manifest, encoding="utf-8")
    destination = path / ".hermes" / "plugins" / "harness-gateway"
    destination.parent.mkdir(parents=True)
    shutil.copytree(PLUGIN, destination)
    _git(path, "add", ".")
    _git(path, "commit", "--allow-empty", "-m", "fixture")
    assert not (path / ".harness").exists()
    return path.resolve()


@pytest.fixture
def loaded_project_plugin(tmp_path, monkeypatch, request):
    def load(
        manifest: str | None = "schema: harness.project.v1\n",
        *,
        binding_slug: str = "project-test",
        route_runtime_enabled: bool = False,
    ):
        project = _project(tmp_path / "project", manifest)
        hermes_home = tmp_path / "hermes-home"
        hermes_home.mkdir()
        receipt_dir = tmp_path / "receipts"
        (hermes_home / "config.yaml").write_text(
            "plugins:\n"
            "  enabled:\n"
            "    - harness-gateway\n"
            "  entries:\n"
            "    harness-gateway:\n"
            f"      receipt_dir: {receipt_dir}\n"
            f"      route_runtime_enabled: {str(route_runtime_enabled).lower()}\n"
            "platforms:\n"
            "  discord:\n"
            "    extra:\n"
            "      channel_project_bindings:\n"
            f"        bound-parent: {binding_slug}\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(project)
        monkeypatch.setenv("HERMES_ENABLE_PROJECT_PLUGINS", "1")
        token = set_hermes_home_override(hermes_home)
        request.addfinalizer(lambda: reset_hermes_home_override(token))
        with projects_db.connect_closing() as connection:
            projects_db.create_project(
                connection,
                name="Project Test",
                slug="project-test",
                primary_path=str(project),
                folders=[str(project)],
            )
        manager = hermes_plugins.PluginManager()
        monkeypatch.setattr(hermes_plugins, "_plugin_manager", manager)
        manager.discover_and_load()
        loaded = manager._plugins["harness-gateway"]
        assert loaded.enabled
        assert manager.has_hook("pre_gateway_dispatch")
        assert manager.has_hook("pre_llm_call")
        assert manager.has_hook("post_llm_call")
        assert manager.has_middleware("llm_request")
        module = loaded.module
        reader_calls = []

        def observation(source_kind, result):
            def read(**kwargs):
                reader_calls.append(source_kind)
                return result

            return read

        class GuardedSourceReaders(dict):
            def __getitem__(self, source_kind):
                if source_kind == "gbrain":
                    pytest.fail("automatic path dispatched the GBrain reader")
                return super().__getitem__(source_kind)

        module._SOURCE_READERS = GuardedSourceReaders({
            "honcho": observation("honcho", {
                "source_kind": "honcho",
                "status": "match",
                "evidence": {
                    "record_count": 1,
                    "content_digest": "a" * 64,
                    "source_receipt": "session=test-session",
                },
                "readback_metadata": {"source_identity": "honcho:test-session"},
                "candidate": {
                    "clue": "matching preference within the active project",
                    "source_ref": "honcho:test-session",
                    "source_receipt": "session=test-session",
                    "lifecycle": "candidate",
                    "observed_at": "2026-07-24T03:00:00Z",
                },
            }),
            "harness_brain": observation("harness_brain", {
                "source_kind": "harness_brain",
                "status": "unavailable",
                "evidence": {"record_count": 0, "source_receipt": "absent"},
                "source_ref": "projects/project/decisions/cps-equation-ssot.md",
            }),
        })
        return SimpleNamespace(
            project=project,
            receipt_dir=receipt_dir,
            manager=manager,
            config=load_gateway_config(),
            reader_calls=reader_calls,
        )

    return load


def _event(
    message_id: str,
    *,
    channel_id: str = "bound-parent",
    parent_channel_id: str | None = None,
) -> MessageEvent:
    source = SessionSource(
        platform=Platform.DISCORD,
        chat_id=channel_id,
        chat_type="thread" if parent_channel_id else "channel",
        user_id="owner",
        thread_id=channel_id if parent_channel_id else None,
        parent_chat_id=parent_channel_id,
        message_id=message_id,
    )
    return MessageEvent(text=f"intent:{message_id}", source=source, message_id=message_id)


class _SessionStore:
    def __init__(self):
        self.entries = {}

    def bind(self, session_id, source):
        self.entries[session_id] = SimpleNamespace(session_id=session_id, origin=source)

    def lookup_by_session_id(self, session_id):
        return self.entries.get(session_id)


class _FinalizerAgent:
    def __init__(self, session_id, cached_system_prompt):
        self.max_iterations = 90
        self.iteration_budget = SimpleNamespace(used=1, max_total=90, remaining=89)
        self.context_compressor = SimpleNamespace(last_prompt_tokens=0)
        self.model = "test-model"
        self.provider = "test"
        self.base_url = "http://test"
        self.session_id = session_id
        self.quiet_mode = True
        self.platform = "discord"
        self._cached_system_prompt = cached_system_prompt
        self._interrupt_message = None
        self._tool_guardrail_halt_decision = None
        self._response_was_previewed = False
        self._skill_nudge_interval = 0
        self._iters_since_skill = 0
        self.session_cost_status = "ok"
        self.session_cost_source = "test"
        for attr in (
            "session_input_tokens", "session_output_tokens", "session_cache_read_tokens",
            "session_cache_write_tokens", "session_reasoning_tokens", "session_prompt_tokens",
            "session_completion_tokens", "session_total_tokens", "session_estimated_cost_usd",
        ):
            setattr(self, attr, 0)

    def _save_trajectory(self, *args, **kwargs):
        pass

    def _cleanup_task_resources(self, *args, **kwargs):
        pass

    def _drop_trailing_empty_response_scaffolding(self, *args, **kwargs):
        pass

    def _persist_session(self, *args, **kwargs):
        pass

    def _emit_status(self, *args, **kwargs):
        pass

    def _safe_print(self, *args, **kwargs):
        pass

    def _file_mutation_verifier_enabled(self):
        return False

    def _turn_completion_explainer_enabled(self):
        return False

    def _drain_pending_steer(self):
        return None

    def clear_interrupt(self):
        pass

    def _sync_external_memory_for_turn(self, **kwargs):
        pass


def _hook_runner(config, session_store=None) -> GatewayRunner:
    runner = GatewayRunner.__new__(GatewayRunner)
    runner.config = config
    runner.session_store = session_store or _SessionStore()
    runner._startup_restore_in_progress = False
    runner._scale_to_zero_note_real_inbound = lambda: None
    return runner


def _runner_reaching_agent(config, captured: list[dict]) -> GatewayRunner:
    session_store = _SessionStore()
    runner = _hook_runner(config, session_store)

    async def run_agent(*, message, source, session_id, **kwargs):
        turn_id = f"turn:{session_id}"
        history = []
        cached_system_prompt = "SYSTEM PROMPT BYTES"
        results = hermes_plugins.invoke_hook(
            "pre_llm_call",
            session_id=session_id,
            task_id=f"task:{session_id}",
            turn_id=turn_id,
            user_message=message,
            conversation_history=history,
            is_first_turn=True,
            model="test-model",
            platform=source.platform.value,
            sender_id=source.user_id,
        )
        context = "\n\n".join(
            result["context"]
            for result in results
            if isinstance(result, dict) and isinstance(result.get("context"), str)
        )
        captured.append({
            "message": message,
            "context": context,
            "api_input": message + ("\n\n" + context if context else ""),
            "session_id": session_id,
            "history": history,
            "cached_system_prompt": cached_system_prompt,
        })
        result = {"final_response": "generic"}
        hermes_plugins.invoke_hook(
            "post_llm_call",
            session_id=session_id,
            task_id=f"task:{session_id}",
            turn_id=turn_id,
            user_message=message,
            assistant_response=result["final_response"],
            conversation_history=[],
            model="test-model",
            platform=source.platform.value,
        )
        return result

    async def with_agent(self, event, source, session_key, run_generation):
        session_id = f"session:{source.chat_id}"
        session_store.bind(session_id, source)
        return await self._run_agent(message=event.text, source=source, session_id=session_id)

    runner._run_agent = run_agent
    runner._handle_message_with_agent = MethodType(with_agent, runner)
    runner._is_user_authorized = lambda source: True
    runner._session_key_for_source = lambda source: f"discord:{source.chat_id}"
    runner._update_prompt_pending = {}
    runner._running_agents = {}
    runner._running_agents_ts = {}
    runner._pending_messages = {}
    runner._queued_events = {}
    runner._draining = False
    runner._external_drain_active = False
    runner._is_telegram_topic_root_lobby = lambda source: False
    runner._claim_active_session_slot = lambda key, source: (None, None)
    runner._persist_active_agents = lambda: None
    runner._begin_session_run_generation = lambda key: 1
    runner._release_active_session_slot = lambda *args, **kwargs: None
    runner._post_turn_goal_continuation = lambda **kwargs: None
    return runner


def _receipt(receipt_dir: Path) -> dict:
    paths = list(receipt_dir.glob("*.json"))
    assert len(paths) == 1
    return json.loads(paths[0].read_text(encoding="ascii"))


def _stage_evidence(receipt: dict, stage: str) -> dict:
    return next(entry["evidence"] for entry in receipt["entries"] if entry["stage"] == stage)


@pytest.mark.parametrize(
    ("channel_id", "parent_channel_id", "route_runtime_enabled"),
    [
        ("bound-parent", None, False),
        ("thread-ready", "bound-parent", False),
        ("bound-parent", None, True),
        ("thread-ready", "bound-parent", True),
    ],
)
def test_actual_gateway_handler_keeps_ingress_packet_out_of_user_message(
    loaded_project_plugin,
    channel_id,
    parent_channel_id,
    route_runtime_enabled,
):
    loaded = loaded_project_plugin(route_runtime_enabled=route_runtime_enabled)
    captured: list[dict] = []
    runner = _runner_reaching_agent(loaded.config, captured)
    result = asyncio.run(
        GatewayRunner._handle_message(
            runner,
            _event("ready", channel_id=channel_id, parent_channel_id=parent_channel_id),
        )
    )

    assert result == {"final_response": "generic"}
    assert captured == [{
        "message": "intent:ready",
        "context": "",
        "api_input": "intent:ready",
        "session_id": f"session:{channel_id}",
        "history": [],
        "cached_system_prompt": "SYSTEM PROMPT BYTES",
    }]
    assert loaded.reader_calls == ["honcho", "harness_brain"]
    receipt = _receipt(loaded.receipt_dir)
    assert [entry["stage"] for entry in receipt["entries"]] == [
        "received", "intake-ready", "route", "running", "terminal",
    ]
    route = receipt["entries"][2]["evidence"]
    assert route["schema"] == "harness.gateway.ingress-packet.v1"
    assert route["target_profile"] == "default"
    assert len(route["packet_sha256"]) == 64
    compact_c = route["compact_C"]
    assert [(item["source"], item["status"]) for item in compact_c["E"]] == [
        ("honcho", "match"),
        ("harness_brain", "unavailable"),
    ]
    assert all("candidate" not in item for item in compact_c["E"])
    assert "gbrain" not in json.dumps(compact_c)
    terminal = receipt["entries"][-1]["evidence"]
    assert terminal == {
        "response_length": len("generic"),
        "response_sha256": hashlib.sha256(b"generic").hexdigest(),
        "session_id": f"session:{channel_id}",
        "status": "completed",
        "target_profile": "default",
        "turn_id": f"turn:session:{channel_id}",
    }
    assert "generic" not in json.dumps(receipt)


@pytest.mark.parametrize("route_runtime_enabled", [False, True])
def test_actual_gateway_hook_hold_allows_generic_agent(
    loaded_project_plugin, route_runtime_enabled
):
    loaded = loaded_project_plugin(
        manifest="", route_runtime_enabled=route_runtime_enabled
    )
    captured: list[dict] = []
    runner = _runner_reaching_agent(loaded.config, captured)

    result = asyncio.run(GatewayRunner._handle_message(runner, _event("held")))

    assert result == {"final_response": "generic"}
    assert captured[0]["message"] == "intent:held"
    receipt = _receipt(loaded.receipt_dir)
    assert [entry["stage"] for entry in receipt["entries"]] == ["received", "intake-hold", "terminal"]
    assert receipt["entries"][-1]["evidence"]["status"] == "HOLD"


def test_resolved_binding_bootstraps_absent_manifest(loaded_project_plugin):
    loaded = loaded_project_plugin(manifest=None)
    captured: list[dict] = []
    runner = _runner_reaching_agent(loaded.config, captured)

    result = asyncio.run(GatewayRunner._handle_message(runner, _event("bootstrap")))

    manifest = loaded.project / "manifest.yml"
    assert result == {"final_response": "generic"}
    assert manifest.read_bytes() == b"schema: harness.project.v1\n"
    assert _stage_evidence(
        _receipt(loaded.receipt_dir), "intake-ready"
    )["binding_evidence"]["manifest_created"] is True


@pytest.mark.parametrize("route_runtime_enabled", [False, True])
def test_held_binding_keeps_native_conversation_and_does_not_bootstrap_manifest(
    loaded_project_plugin, route_runtime_enabled
):
    loaded = loaded_project_plugin(
        manifest=None,
        binding_slug="missing-project",
        route_runtime_enabled=route_runtime_enabled,
    )
    captured: list[dict] = []
    runner = _runner_reaching_agent(loaded.config, captured)

    result = asyncio.run(GatewayRunner._handle_message(runner, _event("binding-held")))

    assert result == {"final_response": "generic"}
    assert captured[0]["message"] == "intent:binding-held"
    assert not (loaded.project / "manifest.yml").exists()


def test_null_binding_does_not_bootstrap_manifest(loaded_project_plugin):
    loaded = loaded_project_plugin(manifest=None)
    captured: list[dict] = []
    runner = _runner_reaching_agent(loaded.config, captured)

    result = asyncio.run(
        GatewayRunner._handle_message(runner, _event("null-binding", channel_id="other-channel"))
    )

    assert result == {"final_response": "generic"}
    assert not (loaded.project / "manifest.yml").exists()


def test_actual_gateway_hook_unbound_allows_generic_run_agent(loaded_project_plugin):
    loaded = loaded_project_plugin()
    captured: list[dict] = []
    runner = _runner_reaching_agent(loaded.config, captured)

    result = asyncio.run(
        GatewayRunner._handle_message(runner, _event("unbound", channel_id="other-channel"))
    )

    assert result == {"final_response": "generic"}
    assert captured == [{
        "message": "intent:unbound",
        "context": "",
        "api_input": "intent:unbound",
        "session_id": "session:other-channel",
        "history": [],
        "cached_system_prompt": "SYSTEM PROMPT BYTES",
    }]
    assert list(loaded.receipt_dir.glob("*.json")) == []


def test_pre_llm_uses_task_local_packet_despite_transformed_runtime_projections(
    loaded_project_plugin,
):
    loaded = loaded_project_plugin()
    runner = _hook_runner(loaded.config)
    event = _event("transformed")
    event.text = "original ingress"
    assert loaded.manager.invoke_hook(
        "pre_gateway_dispatch", event=event, gateway=runner, session_store=runner.session_store
    ) == [{"action": "allow"}]

    result = loaded.manager.invoke_hook(
        "pre_llm_call",
        session_id="transformed-session",
        turn_id="transformed-turn",
        user_message="transformed message",
        platform="transformed-source",
        sender_id="transformed-sender",
    )

    assert result == []
    receipt = _receipt(loaded.receipt_dir)
    assert _stage_evidence(receipt, "received")["event_id"] == "transformed"
    assert _stage_evidence(receipt, "route")["compact_C"]["C"]["intent_sha256"] == hashlib.sha256(
        b"original ingress"
    ).hexdigest()
    loaded.manager.invoke_hook(
        "post_llm_call",
        session_id="another-session",
        turn_id="another-turn",
        assistant_response="done",
    )


def test_bound_ingress_injects_project_root_only_into_agy_request(loaded_project_plugin):
    loaded = loaded_project_plugin()
    runner = _hook_runner(loaded.config)
    event = _event("agy-cwd")
    assert loaded.manager.invoke_hook(
        "pre_gateway_dispatch", event=event, gateway=runner, session_store=runner.session_store
    ) == [{"action": "allow"}]
    loaded.manager.invoke_hook(
        "pre_llm_call",
        session_id="agy-cwd-session",
        turn_id="agy-cwd-turn",
        user_message=event.text,
        platform="discord",
        sender_id="owner",
    )

    agy_request = apply_llm_request_middleware(
        {"messages": [{"role": "user", "content": event.text}]},
        provider="agy-router",
        session_id="agy-cwd-session",
    )
    assert agy_request.payload["extra_headers"] == {
        "X-Hermes-Project-Root": str(loaded.project)
    }
    assert agy_request.trace == [{
        "source": "harness-gateway", "reason": "trusted-bound-project-root"
    }]
    other_request = apply_llm_request_middleware(
        {"messages": []}, provider="openai-codex", session_id="agy-cwd-session"
    )
    assert "extra_headers" not in other_request.payload

    loaded.manager.invoke_hook(
        "post_llm_call",
        session_id="agy-cwd-session",
        turn_id="agy-cwd-turn",
        assistant_response="done",
    )


def test_pre_llm_without_task_local_context_does_nothing(loaded_project_plugin):
    loaded = loaded_project_plugin()

    assert loaded.manager.invoke_hook(
        "pre_llm_call",
        session_id="absent",
        turn_id="absent",
        user_message="must not fabricate",
        platform="discord",
        sender_id="owner",
    ) == []
    assert list(loaded.receipt_dir.glob("*.json")) == []


def test_reader_exception_is_layer_local_and_turn_continues(loaded_project_plugin):
    loaded = loaded_project_plugin()
    module = loaded.manager._plugins["harness-gateway"].module

    def fail(**kwargs):
        raise RuntimeError("raw secret failure")

    module._SOURCE_READERS["honcho"] = fail
    captured = []
    runner = _runner_reaching_agent(loaded.config, captured)

    result = asyncio.run(GatewayRunner._handle_message(runner, _event("reader-error")))

    assert result == {"final_response": "generic"}
    assert captured[0]["context"] == ""
    observations = _stage_evidence(
        _receipt(loaded.receipt_dir), "route"
    )["compact_C"]["E"]
    assert [(item["source"], item["status"]) for item in observations] == [
        ("honcho", "unavailable"),
        ("harness_brain", "unavailable"),
    ]
    assert "gbrain" not in json.dumps(observations)
    assert loaded.reader_calls == ["harness_brain"]
    assert "raw secret failure" not in captured[0]["context"]


def test_no_direct_finding_reads_canonical_cps_once_and_selects_its_single_clue(
    loaded_project_plugin,
):
    loaded = loaded_project_plugin()
    module = loaded.manager._plugins["harness-gateway"].module
    calls = []

    def direct(**kwargs):
        calls.append("honcho")
        return {
            "source_kind": "honcho",
            "status": "no_match",
            "evidence": {"record_count": 0},
        }

    def canonical(**kwargs):
        calls.append("harness_brain")
        return {
            "source_kind": "harness_brain",
            "status": "match",
            "evidence": {
                "record_count": 1,
                "content_digest": "b" * 64,
                "source_receipt": "canonical-cps-readback",
            },
            "readback_metadata": {"source_identity": "harness-brain:canonical-cps"},
            "candidate": {
                "clue": "CPS retrieval uses the bound-project C-boundary for gateway ingress.",
                "source_ref": "harness-brain:canonical-cps",
                "source_receipt": "canonical-cps-readback",
                "lifecycle": "candidate",
                "observed_at": "2026-07-24T03:00:00Z",
            },
        }

    module._SOURCE_READERS = {"honcho": direct, "harness_brain": canonical}
    result = module._gateway_ingress_retrieval_provider(
        original_user_message="CPS retrieval gateway C-boundary",
        session_id="session",
        session_key="discord:bound-parent",
        platform="discord",
        sender_id="owner",
    )

    assert calls == ["honcho", "harness_brain"]
    assert [item["source"] for item in result["E"]] == ["honcho", "harness_brain"]
    clues = [item["candidate"] for item in result["E"] if "candidate" in item]
    assert len(clues) == 1
    assert clues[0]["source_ref"] == "harness-brain:canonical-cps"
    assert clues[0]["clue"] == "CPS retrieval uses the bound-project C-boundary for gateway ingress."


def test_harness_brain_fallback_uses_canonical_cps_decision_ref(
    loaded_project_plugin,
    monkeypatch,
):
    loaded = loaded_project_plugin()
    module = loaded.manager._plugins["harness-gateway"].module
    captured = {}

    def retrieve(source_ref, root, **kwargs):
        captured.update(source_ref=source_ref, root=root, kwargs=kwargs)
        return {"source_kind": "harness_brain", "status": "no_match", "evidence": {"record_count": 0}}

    monkeypatch.setattr(
        module,
        "_retrieval_adapter",
        lambda: SimpleNamespace(retrieve_harness_brain_source=retrieve),
    )
    module._read_harness_brain(
        query="unmatched direct context",
        session_key="ignored",
        reader_context={"request_ref": "probe"},
    )

    assert captured["source_ref"] == "projects/project/decisions/cps-equation-ssot.md"
    assert captured["root"] == loaded.project.parent / "harness-brain"


def test_declared_concrete_source_reaches_reader_once_and_suppresses_fallback(
    loaded_project_plugin,
):
    loaded = loaded_project_plugin()
    module = loaded.manager._plugins["harness-gateway"].module
    calls = []

    def canonical(**kwargs):
        calls.append(kwargs.get("source_ref"))
        return {
            "source_kind": "harness_brain",
            "status": "match",
            "source_ref": kwargs["source_ref"],
            "evidence": {
                "record_count": 1,
                "content_digest": "d" * 64,
                "source_receipt": "direct-policy-readback",
            },
            "readback_metadata": {"source_identity": kwargs["source_ref"]},
            "candidate": {
                "clue": "Gateway retrieval retains the declared project source boundary.",
                "source_ref": kwargs["source_ref"],
                "source_receipt": "direct-policy-readback",
                "lifecycle": "candidate",
                "observed_at": "2026-07-24T03:00:00Z",
            },
        }

    module._SOURCE_READERS = {"honcho": pytest.fail, "harness_brain": canonical}
    source_ref = "projects/project/decisions/current-policy.md"
    result = module._gateway_ingress_retrieval_provider(
        original_user_message=(
            "request_class: settled_project_policy\n"
            f'direct_source_refs: ["{source_ref}"]\n'
            "gateway retrieval project source boundary"
        ),
        session_id="session",
        session_key="discord:bound-parent",
        platform="discord",
        sender_id="owner",
    )

    assert calls == [source_ref]
    assert [(item["source"], item["source_ref"]) for item in result["E"]] == [
        ("harness_brain", source_ref)
    ]
    assert sum("candidate" in item for item in result["E"]) == 1


def test_honcho_candidate_requires_durable_pointer_readback_and_never_suppresses_canonical(
    loaded_project_plugin,
):
    loaded = loaded_project_plugin()
    module = loaded.manager._plugins["harness-gateway"].module
    calls = []
    pointer = "projects/project/decisions/current-policy.md"

    def honcho(**kwargs):
        calls.append("honcho")
        return {
            "source_kind": "honcho",
            "status": "match",
            "evidence": {
                "record_count": 1,
                "content_digest": "e" * 64,
                "source_receipt": "honcho-hit",
            },
            "readback_metadata": {"source_identity": "honcho:derived"},
            "candidate": {
                "clue": "Gateway retrieval retains the project source boundary.",
                "source_ref": "honcho:derived",
                "canonical_ref": pointer,
                "source_receipt": "honcho-hit",
                "lifecycle": "candidate",
                "observed_at": "2026-07-24T03:00:00Z",
            },
        }

    def canonical(**kwargs):
        calls.append(kwargs.get("source_ref") or "fallback")
        return {
            "source_kind": "harness_brain",
            "status": "no_match",
            "source_ref": kwargs.get("source_ref"),
            "evidence": {"record_count": 0, "source_receipt": "none"},
        }

    module._SOURCE_READERS = {"honcho": honcho, "harness_brain": canonical}
    result = module._gateway_ingress_retrieval_provider(
        original_user_message="recent session continuity",
        session_id="session",
        session_key="discord:bound-parent",
        platform="discord",
        sender_id="owner",
    )

    assert calls == ["honcho", pointer, "fallback"]
    assert all("candidate" not in item for item in result["E"])
    assert module._HONCHO_ADVISORY.get() == (
        "Gateway retrieval retains the project source boundary.",
    )
    assert "gbrain" not in json.dumps(result)


def test_no_verified_finding_returns_no_clue_without_retry_or_other_source(
    loaded_project_plugin,
):
    loaded = loaded_project_plugin()
    module = loaded.manager._plugins["harness-gateway"].module
    calls = []

    def adversarial_observation(source_kind, status):
        source_ref = f"{source_kind}:adversarial"
        return {
            "source_kind": source_kind,
            "status": status,
            "evidence": {
                "record_count": 1,
                "content_digest": "f" * 64,
                "source_receipt": "adversarial",
            },
            "readback_metadata": {"source_identity": source_ref},
            "candidate": {
                "clue": "Adversarial non-finding must not become a direct finding.",
                "source_ref": source_ref,
                "source_receipt": "adversarial",
                "lifecycle": "candidate",
                "observed_at": "2026-07-24T03:00:00Z",
            },
        }

    observations = {
        "honcho": adversarial_observation("honcho", "no_match"),
        "harness_brain": adversarial_observation("harness_brain", "unavailable"),
    }

    def no_finding(source_kind):
        def read(**kwargs):
            calls.append(source_kind)
            return observations[source_kind]

        return read

    module._SOURCE_READERS = {
        source_kind: no_finding(source_kind) for source_kind in observations
    }
    assert all(
        "candidate" not in module._normalize_observation(source_kind, observation)
        for source_kind, observation in observations.items()
    )
    result = module._gateway_ingress_retrieval_provider(
        original_user_message="no finding variation",
        session_id="session",
        session_key="discord:bound-parent",
        platform="discord",
        sender_id="owner",
    )

    assert calls == ["honcho", "harness_brain"]
    assert len(result["E"]) == 2
    assert sum("candidate" in item for item in result["E"]) == 0
    assert "gbrain" not in json.dumps(result)


@pytest.mark.parametrize(
    "clue",
    [
        "the setting changed because the owner approved it",
        "you should restart the gateway",
        'the source says "use this route"',
        "the official verdict is final",
    ],
)
def test_non_vector_candidate_is_not_a_finding_and_cannot_suppress_cps(
    loaded_project_plugin,
    clue,
):
    loaded = loaded_project_plugin()
    module = loaded.manager._plugins["harness-gateway"].module
    calls = []

    def direct(**kwargs):
        calls.append("honcho")
        return {
            "source_kind": "honcho",
            "status": "match",
            "evidence": {
                "record_count": 1,
                "content_digest": "c" * 64,
                "source_receipt": "direct-readback",
            },
            "readback_metadata": {"source_identity": "honcho:direct"},
            "candidate": {
                "clue": clue,
                "source_ref": "honcho:direct",
                "source_receipt": "direct-readback",
                "lifecycle": "candidate",
                "observed_at": "2026-07-24T03:00:00Z",
            },
        }

    def canonical(**kwargs):
        calls.append("harness_brain")
        return {
            "source_kind": "harness_brain",
            "status": "no_match",
            "evidence": {"record_count": 0},
        }

    module._SOURCE_READERS = {"honcho": direct, "harness_brain": canonical}
    result = module._gateway_ingress_retrieval_provider(
        original_user_message="unsafe variation",
        session_id="session",
        session_key="discord:bound-parent",
        platform="discord",
        sender_id="owner",
    )

    assert calls == ["honcho", "harness_brain"]
    assert sum("candidate" in item for item in result["E"]) == 0


@pytest.mark.parametrize(
    ("provider", "expected_status"),
    [
        (lambda **kwargs: (_ for _ in ()).throw(RuntimeError("secret")), "provider_error"),
        (lambda **kwargs: {"unexpected": "route"}, "malformed_result"),
    ],
)
def test_provider_failure_preserves_bound_packet_and_ordinary_turn(
    loaded_project_plugin, monkeypatch, provider, expected_status
):
    loaded = loaded_project_plugin()
    module = loaded.manager._plugins["harness-gateway"].module
    runner = _hook_runner(loaded.config)
    event = _event(f"provider-{expected_status}")
    loaded.manager.invoke_hook(
        "pre_gateway_dispatch", event=event, gateway=runner, session_store=runner.session_store
    )
    monkeypatch.setattr(module, "_gateway_ingress_retrieval_provider", provider)

    result = loaded.manager.invoke_hook(
        "pre_llm_call",
        session_id="provider-session",
        turn_id="provider-turn",
        user_message=event.text,
        platform="discord",
        sender_id="owner",
    )

    assert result == []
    compact_c = _stage_evidence(
        _receipt(loaded.receipt_dir), "route"
    )["compact_C"]
    assert compact_c["E"] == []
    assert compact_c["uncertainty"] == [
        {"source": "provider", "status": expected_status}
    ]
    loaded.manager.invoke_hook(
        "post_llm_call",
        session_id="provider-session",
        turn_id="provider-turn",
        assistant_response="ordinary response",
    )


def test_pre_llm_transition_error_clears_task_local_packet(
    loaded_project_plugin,
    monkeypatch,
):
    loaded = loaded_project_plugin()
    runner = _hook_runner(loaded.config)
    event = _event("transition-error")
    loaded.manager.invoke_hook(
        "pre_gateway_dispatch",
        event=event,
        gateway=runner,
        session_store=runner.session_store,
    )

    def fail_transition(*args, **kwargs):
        raise RuntimeError("write failed")

    with monkeypatch.context() as patcher:
        patcher.setattr(
            loaded.manager._plugins["harness-gateway"].module.ExecutionReceipts,
            "transition",
            fail_transition,
        )
        assert loaded.manager.invoke_hook(
            "pre_llm_call",
            session_id="error",
            turn_id="error",
            user_message=event.text,
            platform="discord",
            sender_id="owner",
        ) == []

    assert loaded.manager.invoke_hook(
        "pre_llm_call",
        session_id="replay",
        turn_id="replay",
        user_message=event.text,
        platform="discord",
        sender_id="owner",
    ) == []


def test_post_llm_finalization_error_still_clears_task_local_packet(
    loaded_project_plugin,
    monkeypatch,
):
    loaded = loaded_project_plugin()
    runner = _hook_runner(loaded.config)
    event = _event("finalization-error")
    loaded.manager.invoke_hook(
        "pre_gateway_dispatch",
        event=event,
        gateway=runner,
        session_store=runner.session_store,
    )
    assert loaded.manager.invoke_hook(
        "pre_llm_call",
        session_id="running",
        turn_id="running",
        user_message=event.text,
        platform="discord",
        sender_id="owner",
    ) == []

    def fail_transition(*args, **kwargs):
        raise RuntimeError("write failed")

    with monkeypatch.context() as patcher:
        patcher.setattr(
            loaded.manager._plugins["harness-gateway"].module.ExecutionReceipts,
            "transition",
            fail_transition,
        )
        assert loaded.manager.invoke_hook(
            "post_llm_call",
            session_id="running",
            turn_id="running",
            assistant_response="response",
        ) == []

    assert loaded.manager.invoke_hook(
        "post_llm_call",
        session_id="running",
        turn_id="running",
        assistant_response="replay",
    ) == []


@pytest.mark.parametrize(
    ("case", "final_response", "interrupted", "expected_completed", "turn_exit_reason", "expected_terminal_entries"),
    [
        ("normal", "done", False, True, "text_response(finish_reason=stop)", 1),
        ("empty_response", None, False, False, "empty_response", 0),
        ("interrupted", "partial", True, True, "interrupted_by_user", 0),
    ],
)
def test_finalize_turn_observes_current_core_post_llm_contract(
    loaded_project_plugin,
    case,
    final_response,
    interrupted,
    expected_completed,
    turn_exit_reason,
    expected_terminal_entries,
):
    loaded = loaded_project_plugin()
    runner = _hook_runner(loaded.config)
    event = _event(case)
    session_id = f"session:{case}"
    turn_id = f"turn:{case}"
    original_message = event.text
    cached_system_prompt = b"SYSTEM PROMPT BYTES"
    messages = [
        {"role": "user", "content": "prior"},
        {"role": "assistant", "content": "prior answer"},
        {"role": "user", "content": original_message},
    ]
    history_before = copy.deepcopy(messages)

    assert loaded.manager.invoke_hook(
        "pre_gateway_dispatch",
        event=event,
        gateway=runner,
        session_store=runner.session_store,
    ) == [{"action": "allow"}]
    assert loaded.manager.invoke_hook(
        "pre_llm_call",
        session_id=session_id,
        task_id=f"task:{case}",
        turn_id=turn_id,
        user_message=original_message,
        conversation_history=messages,
        is_first_turn=False,
        model="test-model",
        platform="discord",
        sender_id="owner",
    ) == []

    agent = _FinalizerAgent(session_id, cached_system_prompt)
    result = finalize_turn(
        agent,
        final_response=final_response,
        api_call_count=1,
        interrupted=interrupted,
        failed=False,
        messages=messages,
        conversation_history=None,
        effective_task_id=f"task:{case}",
        turn_id=turn_id,
        user_message=original_message,
        original_user_message=original_message,
        _should_review_memory=False,
        _turn_exit_reason=turn_exit_reason,
    )

    receipt = _receipt(loaded.receipt_dir)
    terminal_entries = [entry for entry in receipt["entries"] if entry["stage"] == "terminal"]
    assert len(terminal_entries) == expected_terminal_entries
    assert result["final_response"] == final_response
    assert result["interrupted"] is interrupted
    assert result["completed"] is expected_completed
    assert result["turn_exit_reason"] == turn_exit_reason
    assert messages[:len(history_before)] == history_before
    assert original_message == event.text
    assert agent._cached_system_prompt == cached_system_prompt
    assert loaded.manager.invoke_hook(
        "pre_llm_call",
        session_id=session_id,
        turn_id="replay",
        user_message=original_message,
        platform="discord",
        sender_id="owner",
    ) == []


def test_pre_llm_runtime_identity_does_not_replace_event_source_identity(loaded_project_plugin):
    loaded = loaded_project_plugin()
    runner = _hook_runner(loaded.config)
    event = _event("runtime-identity")
    assert loaded.manager.invoke_hook(
        "pre_gateway_dispatch", event=event, gateway=runner, session_store=runner.session_store
    ) == [{"action": "allow"}]
    runner.session_store.bind("session:runtime-identity", event.source)

    result = loaded.manager.invoke_hook(
        "pre_llm_call", session_id="session:runtime-identity", turn_id="runtime",
        user_message="intent:runtime-identity", platform="agent-runtime", sender_id="runtime-agent",
    )

    assert result == []
    assert _stage_evidence(
        _receipt(loaded.receipt_dir), "received"
    )["event_id"] == "runtime-identity"


def test_pre_llm_matches_original_message_without_session_identity(loaded_project_plugin):
    loaded = loaded_project_plugin()
    runner = _hook_runner(loaded.config)
    event = _event("matched")
    loaded.manager.invoke_hook(
        "pre_gateway_dispatch", event=event, gateway=runner, session_store=runner.session_store
    )
    result = loaded.manager.invoke_hook(
        "pre_llm_call", session_id="session:other", turn_id="other",
        user_message="intent:matched", platform="discord", sender_id="owner",
    )

    assert result == []
    assert _stage_evidence(
        _receipt(loaded.receipt_dir), "received"
    )["event_id"] == "matched"


def test_sequential_calls_do_not_reuse_a_terminalized_packet(loaded_project_plugin):
    loaded = loaded_project_plugin()
    captured: list[dict] = []
    runner = _runner_reaching_agent(loaded.config, captured)

    async def run_sequentially():
        first = await GatewayRunner._handle_message(runner, _event("once"))
        second = await GatewayRunner._handle_message(
            runner,
            _event("unbound-after-ready", channel_id="other-channel"),
        )
        return first, second

    assert asyncio.run(run_sequentially()) == (
        {"final_response": "generic"},
        {"final_response": "generic"},
    )
    assert captured[0]["context"] == ""
    assert captured[1]["context"] == ""
    assert _stage_evidence(
        _receipt(loaded.receipt_dir), "received"
    )["event_id"] == "once"
    assert loaded.manager.invoke_hook(
        "pre_llm_call", session_id="session:bound-parent", turn_id="replay",
        user_message="intent:once", platform="discord", sender_id="owner",
    ) == []
    assert len(list(loaded.receipt_dir.glob("*.json"))) == 1


def test_concurrent_asyncio_tasks_keep_ingress_envelopes_isolated(loaded_project_plugin):
    loaded = loaded_project_plugin()
    runner = _hook_runner(loaded.config)
    first = _event("first", channel_id="thread-one", parent_channel_id="bound-parent")
    second = _event("second", channel_id="thread-two", parent_channel_id="bound-parent")
    ready = asyncio.Event()
    dispatched = 0

    async def handle(event, session_id, turn_id, response):
        nonlocal dispatched
        assert loaded.manager.invoke_hook(
            "pre_gateway_dispatch", event=event, gateway=runner, session_store=runner.session_store
        ) == [{"action": "allow"}]
        dispatched += 1
        if dispatched == 2:
            ready.set()
        await ready.wait()
        result = loaded.manager.invoke_hook(
            "pre_llm_call",
            session_id=session_id,
            turn_id=turn_id,
            user_message="transformed",
            platform="transformed",
            sender_id="transformed",
        )
        assert result == []
        await asyncio.sleep(0)
        loaded.manager.invoke_hook(
            "post_llm_call",
            session_id="post-projection",
            turn_id="post-projection",
            assistant_response=response,
        )
        return event.message_id

    async def run_concurrently():
        return await asyncio.gather(
            handle(first, "session:first", "one", "first result"),
            handle(second, "session:second", "two", "second result"),
        )

    event_ids = asyncio.run(run_concurrently())
    assert event_ids == ["first", "second"]

    receipts = {
        receipt["entries"][0]["evidence"]["event_id"]: receipt
        for receipt in (
            json.loads(path.read_text(encoding="ascii"))
            for path in loaded.receipt_dir.glob("*.json")
        )
    }
    assert set(receipts) == {"first", "second"}
    assert all(
        [entry["stage"] for entry in receipt["entries"]]
        == ["received", "intake-ready", "route", "running", "terminal"]
        for receipt in receipts.values()
    )
    assert receipts["first"]["entries"][-1]["evidence"]["response_sha256"] == hashlib.sha256(
        b"first result"
    ).hexdigest()
    assert receipts["second"]["entries"][-1]["evidence"]["response_sha256"] == hashlib.sha256(
        b"second result"
    ).hexdigest()


def test_gateway_plugin_has_no_background_route_execution_surface(loaded_project_plugin):
    loaded = loaded_project_plugin()
    module = loaded.manager._plugins["harness-gateway"].module

    for name in (
        "_issue_ptah_transport", "_write_route_job", "_launch_route_job", "_stop_route_jobs",
        "_deliver_route_result", "_terminal_runtime_response", "_run_route_job",
    ):
        assert not hasattr(module, name)


def test_gateway_hook_enabled_runtime_keeps_native_handling_without_route_job(
    loaded_project_plugin
):
    loaded = loaded_project_plugin(route_runtime_enabled=True)
    module = loaded.manager._plugins["harness-gateway"].module
    captured: list[dict] = []
    runner = _runner_reaching_agent(loaded.config, captured)

    result = asyncio.run(GatewayRunner._handle_message(runner, _event("native-enabled")))

    assert result == {"final_response": "generic"}
    assert captured[0]["message"] == "intent:native-enabled"
    assert not (loaded.receipt_dir / "route-jobs").exists()
    receipt = _receipt(loaded.receipt_dir)
    route = _stage_evidence(receipt, "route")
    assert route["schema"] == "harness.gateway.ingress-packet.v1"
    assert route["target_profile"] == "default"
    assert "job_ref" not in route
    assert "ptah" not in json.dumps(receipt)


def test_gateway_hook_allows_native_stop_command_without_creating_route_job(
    loaded_project_plugin
):
    loaded = loaded_project_plugin(route_runtime_enabled=True)
    runner = _hook_runner(loaded.config)
    event = _event("/stop")

    result = loaded.manager.invoke_hook(
        "pre_gateway_dispatch", event=event, gateway=runner, session_store=runner.session_store
    )

    assert result == [{"action": "allow"}]
    assert list(loaded.receipt_dir.glob("cps-*/current.json")) == []


def test_agy_request_injects_bounded_honcho_advisory_only(loaded_project_plugin):
    loaded = loaded_project_plugin()
    module = loaded.manager._plugins["harness-gateway"].module
    module._INGRESS.set(module._IngressEnvelope(
        receipt_id="receipt",
        canonical_json='{"intent":"test"}',
        receipt_dir=loaded.receipt_dir,
        project_cwd=str(loaded.project),
        state="running",
        session_id="session",
        honcho_advisory=module._format_honcho_advisory(("Prior continuity clue.",)),
    ))
    try:
        result = module._llm_request_middleware(
            request={"messages": [{"role": "user", "content": "current request"}]},
            provider="agy-router",
            session_id="session",
        )
    finally:
        module._INGRESS.set(None)

    messages = result["request"]["messages"]
    assert messages[0]["role"] == "system"
    assert messages[1] == {"role": "user", "content": "current request"}
    assert "advisory only" in messages[0]["content"]
    assert "Prior continuity clue." in messages[0]["content"]
    assert result["request"]["extra_headers"] == {
        "X-Hermes-Project-Root": str(loaded.project)
    }
