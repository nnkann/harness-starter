from __future__ import annotations

import json
import os
import stat
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from harness_runtime import capability_transport
from harness_runtime import guided_capability
from harness_runtime.project_binding import BindingInputs, apply_binding


HOST = {"profile": "ptah", "session_id": "session-1", "task_id": "task-1"}
CAPABILITY_REF = "railway.deploy"


def _git_repo(path: Path) -> Path:
    path.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True)
    (path / "README.md").write_text("project\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "README.md"], check=True)
    subprocess.run(
        [
            "git", "-C", str(path), "-c", "user.name=Harness Test",
            "-c", "user.email=harness@example.invalid", "commit", "-qm", "initial",
        ],
        check=True,
    )
    apply_binding(BindingInputs("project-test", path, "main", "service-test"))
    return path


@pytest.fixture
def transport(tmp_path, monkeypatch):
    project = _git_repo(tmp_path / "project")
    state = tmp_path / "state"
    monkeypatch.chdir(project)
    monkeypatch.setenv("HARNESS_STATE_DIR", str(state))
    return project, state


def _successful_delivery(calls):
    def deliver(argv):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout="consumer receipt", stderr="")

    return deliver


def _consume(monkeypatch, calls):
    monkeypatch.setattr(capability_transport, "_run_delivery", _successful_delivery(calls))
    return capability_transport.consume_capability(CAPABILITY_REF, host_context=HOST)


def _claim_file(state: Path) -> Path:
    files = list((state / "capability-readiness-transport-foundation-v1" / "claims").glob("*.json"))
    assert len(files) == 1
    return files[0]


def _schema() -> dict:
    path = Path(__file__).resolve().parents[2] / "contracts" / "capability-transport.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_bounded_repair(result, reason="state_dir_unavailable"):
    assert result["status"] == "foundation_repair_required"
    assert result["repair"] == {"ref": CAPABILITY_REF, "reason": reason}
    Draft202012Validator(_schema()).validate(result)


def test_normal_consume_is_zero_gate_single_exact_continuation_and_same_call_result(
    transport, monkeypatch,
):
    _, state = transport
    calls = []
    gate_calls = {name: 0 for name in ("discovery", "status", "readmission", "checklist")}

    def gate(name):
        def fail_if_called(*args, **kwargs):
            gate_calls[name] += 1
            pytest.fail(f"normal transport called {name}")

        return fail_if_called

    monkeypatch.setattr(guided_capability, "discover_capability", gate("discovery"))
    monkeypatch.setattr(guided_capability, "status_capability", gate("status"))
    monkeypatch.setattr(guided_capability, "plan_capability", gate("readmission"))
    monkeypatch.setattr(guided_capability, "apply_capability", gate("checklist"))

    result = _consume(monkeypatch, calls)

    assert gate_calls == {"discovery": 0, "status": 0, "readmission": 0, "checklist": 0}
    assert len(calls) == 1
    receipt = json.loads(calls[0][-1])
    assert calls[0] == [
        "hermes", "-p", "railway.deploy.consumer.v1", "chat", "--resume", "session-1",
        "-Q", "-q", json.dumps(receipt, sort_keys=True, separators=(",", ":")),
    ]
    assert receipt["producer"] == "railway.deploy.preflight.v1"
    assert receipt["recipient"] == "railway.deploy.consumer.v1"
    assert receipt["action"] == "deploy"
    assert receipt["correlation"]["project_id"] == "project-test"
    assert receipt["correlation"]["profile"] == "ptah"
    assert receipt["correlation"]["session_id"] == "session-1"
    assert receipt["correlation"]["task_id"] == "task-1"
    assert receipt["correlation"]["action"] == "deploy"
    assert result["status"] == "delivered"
    assert result["assessment"] == "consumer_delivered"
    assert result["size"] == len("consumer receipt".encode())
    assert result["repair"] is None
    assert "stdout" not in json.dumps(result)
    root = state / "capability-readiness-transport-foundation-v1"
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    assert stat.S_IMODE(_claim_file(state).stat().st_mode) == 0o600


def test_duplicate_and_restart_return_identical_persisted_terminal_without_delivery(
    transport, monkeypatch,
):
    calls = []
    first = _consume(monkeypatch, calls)
    monkeypatch.setattr(
        capability_transport,
        "_run_delivery",
        lambda argv: pytest.fail("duplicate delivery must not run"),
    )

    duplicate = capability_transport.consume_capability(CAPABILITY_REF, host_context=HOST)

    assert len(calls) == 1
    assert duplicate == first


def test_concurrent_duplicates_share_one_atomic_claim_and_delivery(transport, monkeypatch):
    calls = []

    def deliver(argv):
        calls.append(argv)
        time.sleep(0.05)
        return subprocess.CompletedProcess(argv, 0, stdout="one result", stderr="")

    monkeypatch.setattr(capability_transport, "_run_delivery", deliver)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(
            lambda _: capability_transport.consume_capability(CAPABILITY_REF, host_context=HOST),
            range(2),
        ))

    assert len(calls) == 1
    assert results[0] == results[1]


def test_missing_and_malformed_preseal_state_repair_from_binding(transport, monkeypatch):
    _, state = transport
    calls = []
    monkeypatch.setattr(capability_transport, "_run_delivery", _successful_delivery(calls))
    claim = capability_transport._claim_path(CAPABILITY_REF, HOST)
    claim.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    claim.write_text(
        json.dumps({"schema": capability_transport.CLAIM_SCHEMA, "status": "prepared"}),
        encoding="utf-8",
    )
    os.chmod(claim, 0o600)

    result = capability_transport.consume_capability(CAPABILITY_REF, host_context=HOST)

    assert result["status"] == "delivered"
    assert len(calls) == 1
    assert json.loads(claim.read_text(encoding="utf-8"))["status"] == "terminal"
    assert claim.is_relative_to(state / "capability-readiness-transport-foundation-v1")


@pytest.mark.parametrize("mode", ["expired", "corrupt"])
def test_expired_or_corrupt_sealed_claim_recovers_without_spawn(
    transport, monkeypatch, mode,
):
    _, state = transport
    calls = []
    _consume(monkeypatch, calls)
    path = _claim_file(state)
    claim = json.loads(path.read_text(encoding="utf-8"))
    claim["status"] = "sealed"
    claim.pop("terminal", None)
    if mode == "expired":
        monkeypatch.setattr(
            capability_transport,
            "_now",
            lambda: capability_transport.datetime(2100, 1, 1, tzinfo=capability_transport.timezone.utc),
        )
        reason = "sealed_claim_expired"
    else:
        claim.pop("recipient")
        reason = "sealed_claim_corrupt"
    path.write_text(json.dumps(claim), encoding="utf-8")
    os.chmod(path, 0o600)
    monkeypatch.setattr(
        capability_transport,
        "_run_delivery",
        lambda argv: pytest.fail("sealed recovery must not spawn"),
    )

    result = capability_transport.consume_capability(CAPABILITY_REF, host_context=HOST)

    assert result["status"] == "foundation_repair_required"
    assert result["repair"] == {"ref": CAPABILITY_REF, "reason": reason}
    assert len(calls) == 1


@pytest.mark.parametrize("outcome", ["failure", "timeout", "signal"])
def test_delivery_failure_is_terminal_bounded_and_never_replayed(
    transport, monkeypatch, outcome,
):
    calls = []

    def deliver(argv):
        calls.append(argv)
        if outcome == "timeout":
            raise subprocess.TimeoutExpired(argv, 30, output="private output", stderr="private error")
        return subprocess.CompletedProcess(
            argv,
            -15 if outcome == "signal" else 7,
            stdout="private output",
            stderr="private error",
        )

    monkeypatch.setattr(capability_transport, "_run_delivery", deliver)
    first = capability_transport.consume_capability(CAPABILITY_REF, host_context=HOST)
    second = capability_transport.consume_capability(CAPABILITY_REF, host_context=HOST)

    assert len(calls) == 1
    assert first == second
    assert first["status"] == "failed"
    assert first["assessment"] == f"delivery_{outcome}"
    serialized = json.dumps(first)
    assert "private output" not in serialized
    assert "private error" not in serialized


def test_binding_or_host_context_failure_returns_exact_bounded_repair(transport, monkeypatch):
    project, _ = transport
    (project / ".harness/project-binding.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        capability_transport,
        "_run_delivery",
        lambda argv: pytest.fail("invalid binding must not spawn"),
    )

    result = capability_transport.consume_capability(CAPABILITY_REF, host_context=HOST)
    invalid_host = capability_transport.consume_capability(
        CAPABILITY_REF,
        host_context={**HOST, "producer": "model-controlled"},
    )

    assert result["status"] == "foundation_repair_required"
    assert result["repair"] == {"ref": CAPABILITY_REF, "reason": "binding_invalid"}
    assert invalid_host["repair"] == {"ref": CAPABILITY_REF, "reason": "host_context_invalid"}


@pytest.mark.parametrize("component", ["state", "namespace", "claims", "claim", "lock"])
def test_existing_state_symlink_components_are_rejected_without_spawn_or_escape(
    transport, monkeypatch, component,
):
    _, state = transport
    outside = state.parent / f"outside-{component}"
    outside.mkdir()
    namespace = state / capability_transport.STATE_NAMESPACE
    claims = namespace / "claims"
    key = capability_transport._claim_key(CAPABILITY_REF, HOST, "project-test")
    if component == "state":
        state.symlink_to(outside, target_is_directory=True)
    else:
        state.mkdir(mode=0o700)
        if component == "namespace":
            namespace.symlink_to(outside, target_is_directory=True)
        else:
            namespace.mkdir(mode=0o700)
            if component == "claims":
                claims.symlink_to(outside, target_is_directory=True)
            else:
                claims.mkdir(mode=0o700)
                (claims / f"{key}.{'json' if component == 'claim' else 'lock'}").symlink_to(
                    outside / "escaped"
                )
    monkeypatch.setattr(
        capability_transport,
        "_run_delivery",
        lambda argv: pytest.fail("symlinked state must not spawn"),
    )

    result = capability_transport.consume_capability(CAPABILITY_REF, host_context=HOST)

    _assert_bounded_repair(result)
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize("operation", ["lock_open", "lock_chmod", "claim_write", "fsync", "replace", "permissions"])
def test_pre_delivery_state_io_failures_preserve_prepared_claim_and_never_spawn(
    transport, monkeypatch, operation,
):
    _, state = transport
    claim = capability_transport._claim_path(CAPABILITY_REF, HOST)
    prepared = {"schema": capability_transport.CLAIM_SCHEMA, "status": "prepared"}
    claim.write_text(json.dumps(prepared), encoding="utf-8")
    os.chmod(claim, 0o600)
    calls = []
    monkeypatch.setattr(capability_transport, "_run_delivery", _successful_delivery(calls))

    if operation == "lock_open":
        original_open = capability_transport.os.open

        def fail_lock(path, flags, mode=0o777, *, dir_fd=None):
            if str(path).endswith(".lock"):
                raise OSError("lock open denied")
            return original_open(path, flags, mode, dir_fd=dir_fd)

        monkeypatch.setattr(capability_transport.os, "open", fail_lock)
    elif operation == "lock_chmod":
        original_fchmod = capability_transport.os.fchmod

        def fail_lock_permissions(fd, mode):
            if mode == 0o600:
                raise PermissionError("lock permissions denied")
            return original_fchmod(fd, mode)

        monkeypatch.setattr(capability_transport.os, "fchmod", fail_lock_permissions)
    elif operation == "claim_write":
        monkeypatch.setattr(
            capability_transport,
            "_atomic_write",
            lambda *args, **kwargs: (_ for _ in ()).throw(OSError("claim write denied")),
        )
    elif operation == "fsync":
        monkeypatch.setattr(
            capability_transport.os,
            "fsync",
            lambda fd: (_ for _ in ()).throw(OSError("fsync denied")),
        )
    elif operation == "replace":
        monkeypatch.setattr(
            capability_transport.os,
            "replace",
            lambda *args, **kwargs: (_ for _ in ()).throw(OSError("replace denied")),
        )
    else:
        original_fchmod = capability_transport.os.fchmod
        file_permissions = 0

        def fail_claim_permissions(fd, mode):
            nonlocal file_permissions
            if mode == 0o600:
                file_permissions += 1
                if file_permissions == 2:
                    raise PermissionError("claim permissions denied")
            return original_fchmod(fd, mode)

        monkeypatch.setattr(
            capability_transport.os,
            "fchmod",
            fail_claim_permissions,
        )

    result = capability_transport.consume_capability(CAPABILITY_REF, host_context=HOST)

    _assert_bounded_repair(result)
    assert calls == []
    assert json.loads(claim.read_text(encoding="utf-8")) == prepared


def test_atomic_temporary_symlink_collision_is_bounded_without_following(
    transport, monkeypatch,
):
    _, state = transport
    claim = capability_transport._claim_path(CAPABILITY_REF, HOST)
    prepared = {"schema": capability_transport.CLAIM_SCHEMA, "status": "prepared"}
    claim.write_text(json.dumps(prepared), encoding="utf-8")
    os.chmod(claim, 0o600)
    outside = state.parent / "outside-atomic"
    outside.mkdir()
    temporary = claim.parent / f".{claim.name}.{'a' * 16}"
    temporary.symlink_to(outside / "escaped")
    monkeypatch.setattr(capability_transport.secrets, "token_hex", lambda size: "a" * 16)
    monkeypatch.setattr(
        capability_transport,
        "_run_delivery",
        lambda argv: pytest.fail("atomic symlink collision must not spawn"),
    )

    result = capability_transport.consume_capability(CAPABILITY_REF, host_context=HOST)

    _assert_bounded_repair(result)
    assert temporary.is_symlink()
    assert list(outside.iterdir()) == []
    assert json.loads(claim.read_text(encoding="utf-8")) == prepared


@pytest.mark.parametrize("source", ["profile", "session_id", "task_id"])
def test_oversize_host_correlation_is_rejected_with_schema_valid_repair(
    transport, monkeypatch, source,
):
    monkeypatch.setattr(
        capability_transport,
        "_run_delivery",
        lambda argv: pytest.fail("oversize host context must not spawn"),
    )

    result = capability_transport.consume_capability(
        CAPABILITY_REF,
        host_context={**HOST, source: "x" * 257},
    )

    _assert_bounded_repair(result, "host_context_invalid")


@pytest.mark.parametrize("source", ["project_id", "producer", "recipient", "action"])
def test_oversize_binding_transport_is_rejected_before_sealing(
    transport, monkeypatch, source,
):
    project, _ = transport
    path = project / ".harness/project-binding.json"
    binding = json.loads(path.read_text(encoding="utf-8"))
    if source == "project_id":
        binding["project"]["id"] = "x" * 257
    else:
        capability = binding["capability_graph"]["capabilities"][0]
        target = {"producer": "preflight", "recipient": "consumer", "action": "operation"}[source]
        if target == "operation":
            capability[target] = "x" * 257
        else:
            capability["profiles"][target] = "x" * 257
        graph = binding["capability_graph"]
        graph["digest"] = capability_transport._digest({key: value for key, value in graph.items() if key != "digest"})
    path.write_text(json.dumps(binding), encoding="utf-8")
    monkeypatch.setattr(
        capability_transport,
        "_run_delivery",
        lambda argv: pytest.fail("oversize binding must not spawn"),
    )

    result = capability_transport.consume_capability(CAPABILITY_REF, host_context=HOST)

    _assert_bounded_repair(result, "binding_invalid")


def test_corrupt_terminal_is_replaced_by_bounded_repair_without_spawn(transport, monkeypatch):
    _, state = transport
    calls = []
    _consume(monkeypatch, calls)
    path = _claim_file(state)
    claim = json.loads(path.read_text(encoding="utf-8"))
    claim["terminal"] = {"status": "delivered", "stdout": "must-not-return"}
    path.write_text(json.dumps(claim), encoding="utf-8")
    monkeypatch.setattr(
        capability_transport,
        "_run_delivery",
        lambda argv: pytest.fail("terminal repair must not spawn"),
    )

    result = capability_transport.consume_capability(CAPABILITY_REF, host_context=HOST)

    assert result["repair"] == {"ref": CAPABILITY_REF, "reason": "terminal_claim_corrupt"}
    assert "must-not-return" not in json.dumps(result)
    assert len(calls) == 1


def test_unknown_claim_shape_never_replays(transport, monkeypatch):
    path = capability_transport._claim_path(CAPABILITY_REF, HOST)
    path.write_text('{"status":"seale"}', encoding="utf-8")
    os.chmod(path, 0o600)
    monkeypatch.setattr(
        capability_transport,
        "_run_delivery",
        lambda argv: pytest.fail("unknown claim must not spawn"),
    )

    result = capability_transport.consume_capability(CAPABILITY_REF, host_context=HOST)

    assert result["repair"] == {"ref": CAPABILITY_REF, "reason": "claim_malformed"}
    assert json.loads(path.read_text(encoding="utf-8"))["status"] == "terminal"


def test_invalid_utf8_claim_is_bounded_and_never_replayed(transport, monkeypatch):
    path = capability_transport._claim_path(CAPABILITY_REF, HOST)
    path.write_bytes(b"\xff")
    os.chmod(path, 0o600)
    calls = []
    monkeypatch.setattr(capability_transport, "_run_delivery", _successful_delivery(calls))

    first = capability_transport.consume_capability(CAPABILITY_REF, host_context=HOST)
    second = capability_transport.consume_capability(CAPABILITY_REF, host_context=HOST)

    _assert_bounded_repair(first, "claim_malformed")
    assert first["repair"] == {"ref": CAPABILITY_REF, "reason": "claim_malformed"}
    assert second == first
    assert calls == []


def test_contract_validates_all_terminal_envelopes(transport, monkeypatch):
    calls = []
    result = _consume(monkeypatch, calls)
    schema = _schema()
    receipt = json.loads(calls[0][-1])

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(result)
    receipt_schema = {**schema["$defs"]["immutableReceipt"], "$defs": schema["$defs"]}
    Draft202012Validator(receipt_schema).validate(receipt)
