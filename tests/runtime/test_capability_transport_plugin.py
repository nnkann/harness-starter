from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

from harness_runtime import capability_transport, guided_capability
from harness_runtime.project_binding import BindingInputs, apply_binding


REPO = Path(__file__).resolve().parents[2]
PLUGIN = REPO / ".hermes" / "plugins" / "harness-capability-transport" / "__init__.py"


def _load_plugin():
    spec = importlib.util.spec_from_file_location("harness_capability_transport_plugin", PLUGIN)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Context:
    profile_name = "host-profile"

    def __init__(self):
        self.tools = []

    def register_tool(self, **kwargs):
        self.tools.append(kwargs)


def test_plugin_registers_exact_single_sync_opaque_tool(monkeypatch):
    plugin = _load_plugin()
    ctx = _Context()
    monkeypatch.setattr(
        plugin,
        "consume_capability",
        lambda capability_ref, *, host_context: {
            "capability_ref": capability_ref,
            "host_context": host_context,
        },
    )

    plugin.register(ctx)

    assert len(ctx.tools) == 1
    tool = ctx.tools[0]
    assert tool["name"] == "harness_capability_consume"
    assert tool["toolset"] == "harness-capability-transport"
    assert tool["is_async"] is False
    assert tool["schema"] == {
        "name": "harness_capability_consume",
        "description": "Consume an opaque bound capability readiness reference.",
        "parameters": {
            "type": "object",
            "required": ["capability_ref"],
            "additionalProperties": False,
            "properties": {
                "capability_ref": {"type": "string", "minLength": 1, "maxLength": 256},
            },
        },
    }


def test_plugin_forwards_only_host_profile_session_task_context(monkeypatch):
    plugin = _load_plugin()
    ctx = _Context()
    captured = {}

    def consume(capability_ref, *, host_context):
        captured.update({"capability_ref": capability_ref, "host_context": host_context})
        return {"status": "delivered"}

    monkeypatch.setattr(plugin, "consume_capability", consume)
    plugin.register(ctx)
    result = json.loads(ctx.tools[0]["handler"](
        {"capability_ref": "opaque-ref"},
        session_id="host-session",
        task_id="host-task",
        producer="model-producer",
        recipient="model-recipient",
        nonce="model-nonce",
    ))

    assert result == {"status": "delivered"}
    assert captured == {
        "capability_ref": "opaque-ref",
        "host_context": {
            "profile": "host-profile",
            "session_id": "host-session",
            "task_id": "host-task",
        },
    }


def test_plugin_rejects_non_exact_arguments_before_runtime(monkeypatch):
    plugin = _load_plugin()
    ctx = _Context()
    monkeypatch.setattr(
        plugin,
        "consume_capability",
        lambda *args, **kwargs: pytest.fail("invalid tool args must not reach runtime"),
    )
    plugin.register(ctx)

    result = json.loads(ctx.tools[0]["handler"]({
        "capability_ref": "opaque-ref",
        "return_target": "model-controlled",
    }, session_id="host-session", task_id="host-task"))

    assert result["status"] == "foundation_repair_required"
    assert result["repair"] == {"ref": "opaque-ref", "reason": "tool_arguments_invalid"}


def test_registered_handler_runs_runtime_delivery_and_returns_same_call_terminal_result(
    tmp_path, monkeypatch,
):
    project = tmp_path / "project"
    project.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(project)], check=True)
    (project / "README.md").write_text("project\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(project), "add", "README.md"], check=True)
    subprocess.run(
        [
            "git", "-C", str(project), "-c", "user.name=Harness Test",
            "-c", "user.email=harness@example.invalid", "commit", "-qm", "initial",
        ],
        check=True,
    )
    apply_binding(BindingInputs("project-test", project, "main", "service-test"))
    monkeypatch.chdir(project)
    monkeypatch.setenv("HARNESS_STATE_DIR", str(tmp_path / "state"))
    calls = []

    def deliver(argv):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout="terminal output", stderr="")

    monkeypatch.setattr(capability_transport, "_run_delivery", deliver)
    gate_calls = {name: 0 for name in ("readiness", "status", "readmission", "checklist")}

    def blocked_gate(name):
        def called(*args, **kwargs):
            gate_calls[name] += 1
            pytest.fail(f"handler called {name}")

        return called

    monkeypatch.setattr(guided_capability, "discover_capability", blocked_gate("readiness"))
    monkeypatch.setattr(guided_capability, "status_capability", blocked_gate("status"))
    monkeypatch.setattr(guided_capability, "plan_capability", blocked_gate("readmission"))
    monkeypatch.setattr(guided_capability, "apply_capability", blocked_gate("checklist"))
    plugin = _load_plugin()
    ctx = _Context()
    plugin.register(ctx)

    result = json.loads(ctx.tools[0]["handler"](
        {"capability_ref": "railway.deploy"},
        session_id="host-session",
        task_id="host-task",
    ))

    assert len(calls) == 1
    assert calls[0][1:7] == ["-p", "railway.deploy.consumer.v1", "chat", "--resume", "host-session", "-Q"]
    assert result["status"] == "delivered"
    assert result["assessment"] == "consumer_delivered"
    assert gate_calls == {"readiness": 0, "status": 0, "readmission": 0, "checklist": 0}
