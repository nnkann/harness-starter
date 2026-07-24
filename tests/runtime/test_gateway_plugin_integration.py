from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import MethodType, SimpleNamespace

import pytest

CORE = Path("/Users/kann/.hermes/hermes-agent")
REPO = Path(__file__).resolve().parents[2]
RUNTIME = REPO / "runtime"
PLUGIN = REPO / ".hermes" / "plugins" / "harness-gateway"
for module_root in (CORE, RUNTIME):
    if str(module_root) not in sys.path:
        sys.path.insert(0, str(module_root))

from gateway.config import Platform, load_gateway_config
from gateway.ingress_retrieval import GatewayIngressRetrievalAdapter
from gateway.platforms.base import MessageEvent
from gateway.run import GatewayRunner, _bind_gateway_ingress_retrieval
from gateway.session import SessionSource
from agent.turn_finalizer import finalize_turn
from hermes_cli import plugins as hermes_plugins
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
        assert manager._gateway_ingress_retrieval_provider is not None
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
        agent = SimpleNamespace(session_id=session_id, _cached_system_prompt=cached_system_prompt)
        _bind_gateway_ingress_retrieval(
            agent,
            session_id=session_id,
            session_key=f"discord:{source.chat_id}",
            platform=source.platform.value,
            sender_id=source.user_id,
        )
        retrieval = agent._gateway_ingress_retrieve
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
            gateway_ingress_retrieve=retrieval,
        )
        context = "\n\n".join(result["context"] for result in results)
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


@pytest.mark.parametrize(
    ("channel_id", "parent_channel_id"),
    [("bound-parent", None), ("thread-ready", "bound-parent")],
)
def test_actual_gateway_handler_injects_byte_exact_canonical_packet_once(
    loaded_project_plugin,
    channel_id,
    parent_channel_id,
):
    loaded = loaded_project_plugin()
    captured: list[dict] = []
    runner = _runner_reaching_agent(loaded.config, captured)
    result = asyncio.run(
        GatewayRunner._handle_message(
            runner,
            _event("ready", channel_id=channel_id, parent_channel_id=parent_channel_id),
        )
    )

    assert result == {"final_response": "generic"}
    assert len(captured) == 1
    packet = captured[0]["context"]
    assert captured[0]["api_input"] == f"intent:ready\n\n{packet}"
    assert captured[0]["api_input"].encode("ascii").endswith(packet.encode("ascii"))
    decoded = json.loads(packet)
    assert decoded["schema"] == "harness.gateway.ingress-packet.v1"
    assert decoded["event_ref"]["event_id"] == "ready"
    assert decoded["intent"] == "intent:ready"
    assert json.dumps(decoded, sort_keys=True, separators=(",", ":"), ensure_ascii=True) == packet
    compact_c = decoded["compact_C"]
    assert set(compact_c) == {"C", "E", "uncertainty"}
    assert [(item["source"], item["status"]) for item in compact_c["E"]] == [
        ("honcho", "match"),
    ]
    assert compact_c["E"][0]["candidate"] == {
        "clue": "matching preference within the active project",
        "source_ref": "honcho:test-session",
        "source_receipt": "session=test-session",
        "lifecycle": "candidate",
        "observed_at": "2026-07-24T03:00:00Z",
    }
    assert "gbrain" not in json.dumps(compact_c)
    assert loaded.reader_calls == ["honcho"]
    prohibited = {
        "P", "S", "owner", "selected_agents", "actor_binding", "route", "verdict",
        "hold", "HOLD", "task_AC", "graph", "transition", "mutation", "closure",
        "learning", "promotion",
    }

    def keys(value):
        if isinstance(value, dict):
            return set(value).union(*(keys(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(keys(item) for item in value))
        return set()

    assert not keys(compact_c) & prohibited
    assert captured[0]["history"] == []
    assert captured[0]["cached_system_prompt"] == "SYSTEM PROMPT BYTES"
    receipt = _receipt(loaded.receipt_dir)
    assert [entry["stage"] for entry in receipt["entries"]] == [
        "received",
        "intake-ready",
        "route",
        "running",
        "terminal",
    ]
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


def test_actual_gateway_hook_hold_skips_generic_agent(loaded_project_plugin):
    loaded = loaded_project_plugin(manifest="")
    runner = _hook_runner(loaded.config)
    generic_calls: list[str] = []

    async def generic(*args, **kwargs):
        generic_calls.append("called")
        return "generic"

    runner._run_agent = generic
    result = asyncio.run(GatewayRunner._handle_message(runner, _event("held")))

    assert result is None
    assert generic_calls == []
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
    assert json.loads(captured[0]["context"])["binding_evidence"]["manifest_created"] is True


def test_held_binding_does_not_bootstrap_manifest(loaded_project_plugin):
    loaded = loaded_project_plugin(manifest=None, binding_slug="missing-project")
    runner = _hook_runner(loaded.config)

    result = asyncio.run(GatewayRunner._handle_message(runner, _event("binding-held")))

    assert result is None
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

    assert len(result) == 1
    packet = json.loads(result[0]["context"])
    assert packet["event_ref"]["event_id"] == "transformed"
    assert packet["intent"] == "original ingress"
    loaded.manager.invoke_hook(
        "post_llm_call",
        session_id="another-session",
        turn_id="another-turn",
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
    observations = json.loads(captured[0]["context"])["compact_C"]["E"]
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


def test_no_verified_finding_returns_no_clue_without_retry_or_other_source(
    loaded_project_plugin,
):
    loaded = loaded_project_plugin()
    module = loaded.manager._plugins["harness-gateway"].module
    calls = []

    def no_finding(source_kind, status):
        def read(**kwargs):
            calls.append(source_kind)
            return {
                "source_kind": source_kind,
                "status": status,
                "evidence": {"record_count": 0, "source_receipt": "none"},
            }

        return read

    module._SOURCE_READERS = {
        "honcho": no_finding("honcho", "no_match"),
        "harness_brain": no_finding("harness_brain", "unavailable"),
    }
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
        (None, "unavailable"),
        (lambda **kwargs: (_ for _ in ()).throw(RuntimeError("secret")), "provider_error"),
        (lambda **kwargs: {"unexpected": "route"}, "malformed_result"),
    ],
)
def test_provider_failure_preserves_bound_packet_and_ordinary_turn(
    loaded_project_plugin, provider, expected_status
):
    loaded = loaded_project_plugin()
    runner = _hook_runner(loaded.config)
    event = _event(f"provider-{expected_status}")
    loaded.manager.invoke_hook(
        "pre_gateway_dispatch", event=event, gateway=runner, session_store=runner.session_store
    )
    retrieval = GatewayIngressRetrievalAdapter(provider)

    result = loaded.manager.invoke_hook(
        "pre_llm_call",
        session_id="provider-session",
        turn_id="provider-turn",
        user_message=event.text,
        platform="discord",
        sender_id="owner",
        gateway_ingress_retrieve=retrieval,
    )

    packet = json.loads(result[0]["context"])
    assert packet["intent"] == event.text
    assert packet["event_ref"]["event_id"] == event.message_id
    assert packet["compact_C"]["E"] == []
    assert packet["compact_C"]["uncertainty"] == [
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
    assert len(loaded.manager.invoke_hook(
        "pre_llm_call",
        session_id="running",
        turn_id="running",
        user_message=event.text,
        platform="discord",
        sender_id="owner",
    )) == 1

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
    ("case", "final_response", "interrupted", "expected_completed", "turn_exit_reason"),
    [
        ("normal", "done", False, True, "text_response(finish_reason=stop)"),
        ("empty_response", None, False, False, "empty_response"),
        ("interrupted", "partial", True, True, "interrupted_by_user"),
    ],
)
def test_finalize_turn_terminalizes_and_cleans_ingress_for_all_terminal_paths(
    loaded_project_plugin,
    case,
    final_response,
    interrupted,
    expected_completed,
    turn_exit_reason,
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
    assert len(loaded.manager.invoke_hook(
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
    )) == 1

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
    assert len(terminal_entries) == 1
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

    assert len(result) == 1
    assert json.loads(result[0]["context"])["event_ref"]["event_id"] == "runtime-identity"


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

    assert len(result) == 1
    assert json.loads(result[0]["context"])["event_ref"]["event_id"] == "matched"


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
    assert json.loads(captured[0]["context"])["event_ref"]["event_id"] == "once"
    assert captured[1]["context"] == ""
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
        packet = result[0]["context"]
        await asyncio.sleep(0)
        loaded.manager.invoke_hook(
            "post_llm_call",
            session_id="post-projection",
            turn_id="post-projection",
            assistant_response=response,
        )
        return packet

    async def run_concurrently():
        return await asyncio.gather(
            handle(first, "session:first", "one", "first result"),
            handle(second, "session:second", "two", "second result"),
        )

    packets = asyncio.run(run_concurrently())
    assert [json.loads(packet)["event_ref"]["event_id"] for packet in packets] == [
        "first",
        "second",
    ]

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
