import hashlib
import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT / "adapters"))

from hermes_scheduled_consumer_provisioner import (  # noqa: E402
    PROVISIONER_IDENTITY,
    ProvisioningError,
    reconcile_scheduled_consumer,
)
from scheduled_readonly_consumer_adapter import (  # noqa: E402
    ChildExecutionError,
    run_scheduled_consumer_child,
)
from harness_runtime.scheduled_consumer import validate_scheduled_consumer


REQUIRED_NAMES = ["SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_URL"]
RECEIPT_KEYS = {
    "schema",
    "action",
    "provisioner",
    "owner",
    "job_id",
    "declaration_digest",
    "source",
}


def write_bound_project(root: Path) -> Path:
    root.mkdir()
    managed = [".harness/project-binding.json", ".harness/runtime.lock.json"]
    (root / ".harness").mkdir()
    (root / ".harness/runtime.lock.json").write_text("{}\n", encoding="utf-8")
    binding = {
        "schema": "harness.project-binding.v1",
        "managed_by": "harness-project-binding",
        "project": {"id": "stagelink", "root": str(root.resolve())},
        "managed_files": managed,
    }
    (root / ".harness/project-binding.json").write_text(json.dumps(binding) + "\n", encoding="utf-8")
    return root


def declaration(root: Path, *, schedule: str = "0 6 * * *", script_seed: bytes = b"v1") -> dict:
    return {
        "schema": "harness.scheduled-readonly-consumer.v1",
        "project": {"id": "stagelink", "root": str(root.resolve())},
        "job": {
            "identity": "stagelink-public-catalog-refresh",
            "schedule": schedule,
            "delivery": "local",
        },
        "script": {
            "identity": "stagelink/refresh_public_catalog.py",
            "digest": "sha256:" + hashlib.sha256(script_seed).hexdigest(),
        },
        "no_agent": True,
        "capability": {"class": "scheduled_readonly_consumer", "access": "read_only"},
        "required_names": REQUIRED_NAMES,
        "source": {
            "class": "injected_fixture",
            "ref": "stagelink:test-fixture:readonly",
            "availability": {name: True for name in REQUIRED_NAMES},
        },
    }


def project_instance_declaration(root: Path) -> dict:
    declared = declaration(root)
    declared["source"] = {
        "class": "project_instance_adapter",
        "ref": "stagelink:project-instance:supabase-readonly",
        "availability": {name: True for name in REQUIRED_NAMES},
    }
    return declared


class Spy:
    def __init__(self, results):
        self.results = iter(results)
        self.calls = []

    def __call__(self, argv):
        self.calls.append(argv)
        return next(self.results)


def test_create_update_and_noop_use_supported_exact_job_id_argv(tmp_path):
    root = write_bound_project(tmp_path / "stagelink")
    create_spy = Spy([{"job_id": "job-123"}])

    created = reconcile_scheduled_consumer(root, declaration(root), jobs=[], receipt=None, invoke=create_spy)

    assert create_spy.calls == [[
        "hermes", "cron", "create", "0 6 * * *", "--no-agent",
        "--script", "stagelink/refresh_public_catalog.py",
        "--deliver", "local", "--name", "stagelink-public-catalog-refresh",
    ]]
    assert created["operation"] == "create"
    receipt = created["receipt"]
    assert receipt["job_id"] == "job-123"

    changed = declaration(root, schedule="0 7 * * *", script_seed=b"v2")
    update_spy = Spy([{"job_id": "job-123"}])
    updated = reconcile_scheduled_consumer(
        root,
        changed,
        jobs=[{"id": "job-123", "name": "stagelink-public-catalog-refresh"}],
        receipt=receipt,
        invoke=update_spy,
    )

    assert update_spy.calls == [[
        "hermes", "cron", "edit", "job-123", "--schedule", "0 7 * * *", "--no-agent",
        "--script", "stagelink/refresh_public_catalog.py",
        "--deliver", "local", "--name", "stagelink-public-catalog-refresh",
    ]]
    assert updated["operation"] == "update"

    noop_spy = Spy([])
    noop = reconcile_scheduled_consumer(
        root,
        changed,
        jobs=[{"id": "job-123", "name": "stagelink-public-catalog-refresh"}],
        receipt=updated["receipt"],
        invoke=noop_spy,
    )
    expected_noop_receipt = deepcopy(updated["receipt"])
    expected_noop_receipt["action"] = "noop"
    assert noop == {"operation": "noop", "receipt": expected_noop_receipt, "invocations": []}
    assert noop_spy.calls == []
    trace = {"create": create_spy.calls, "update": update_spy.calls, "noop": noop_spy.calls}
    assert all(call[2] in {"create", "edit"} for calls in trace.values() for call in calls)
    print("FAKE_CRON_TRACE=" + json.dumps(trace, sort_keys=True))


def valid_receipt(root: Path) -> dict:
    created = reconcile_scheduled_consumer(
        root, declaration(root), jobs=[], receipt=None, invoke=Spy([{"job_id": "job-123"}])
    )
    return created["receipt"]


def strict_receipt(root: Path) -> dict:
    receipt = valid_receipt(root)
    receipt["action"] = "created"
    receipt["provisioner"] = PROVISIONER_IDENTITY
    return receipt


@pytest.mark.parametrize(
    ("case", "mutate_receipt"),
    [
        ("missing action", lambda receipt: receipt.pop("action")),
        ("missing provisioner", lambda receipt: receipt.pop("provisioner")),
        ("wrong provisioner", lambda receipt: receipt.update(provisioner="forged-provisioner")),
        ("extra top-level field", lambda receipt: receipt.update(forged="value")),
        ("extra owner field", lambda receipt: receipt["owner"].update(forged="value")),
        ("extra source field", lambda receipt: receipt["source"].update(forged="value")),
        (
            "extra availability field",
            lambda receipt: receipt["source"]["availability"].update(UNRELATED_TOKEN=True),
        ),
        (
            "forged secret sentinel field",
            lambda receipt: receipt["source"].update(secret="receipt-secret-sentinel"),
        ),
    ],
)
def test_forged_receipts_are_rejected_before_invocation(tmp_path, case, mutate_receipt):
    root = write_bound_project(tmp_path / "stagelink")
    receipt = strict_receipt(root)
    mutate_receipt(receipt)
    spy = Spy([])

    with pytest.raises(ProvisioningError, match="receipt"):
        reconcile_scheduled_consumer(
            root,
            declaration(root, schedule="0 7 * * *", script_seed=b"v2"),
            jobs=[{"id": "job-123", "name": "stagelink-public-catalog-refresh"}],
            receipt=receipt,
            invoke=spy,
        )

    assert spy.calls == [], case
    print("FORGED_RECEIPT_TRACE=" + json.dumps({"case": case, "invocations": spy.calls}))


def test_create_update_and_noop_receipts_have_exact_normalized_shape(tmp_path):
    root = write_bound_project(tmp_path / "stagelink")
    initial_plan = validate_scheduled_consumer(root, declaration(root))
    created = reconcile_scheduled_consumer(
        root, declaration(root), jobs=[], receipt=None, invoke=Spy([{"job_id": "job-123"}])
    )
    assert created["receipt"] == {
        "schema": "harness.scheduled-readonly-consumer-receipt.v1",
        "action": "created",
        "provisioner": PROVISIONER_IDENTITY,
        "owner": {
            "project_id": "stagelink",
            "job_identity": "stagelink-public-catalog-refresh",
        },
        "job_id": "job-123",
        "declaration_digest": initial_plan["declaration_digest"],
        "source": {
            "class": "injected_fixture",
            "ref": "stagelink:test-fixture:readonly",
            "availability": {
                "SUPABASE_SERVICE_ROLE_KEY": True,
                "SUPABASE_URL": True,
            },
        },
    }

    changed = declaration(root, schedule="0 7 * * *", script_seed=b"v2")
    changed_plan = validate_scheduled_consumer(root, changed)
    updated = reconcile_scheduled_consumer(
        root,
        changed,
        jobs=[{"id": "job-123", "name": "stagelink-public-catalog-refresh"}],
        receipt=created["receipt"],
        invoke=Spy([{"job_id": "job-123"}]),
    )
    expected = deepcopy(created["receipt"])
    expected["action"] = "updated"
    expected["declaration_digest"] = changed_plan["declaration_digest"]
    assert updated["receipt"] == expected

    caller_receipt = updated["receipt"]
    noop = reconcile_scheduled_consumer(
        root,
        changed,
        jobs=[{"id": "job-123", "name": "stagelink-public-catalog-refresh"}],
        receipt=caller_receipt,
        invoke=Spy([]),
    )
    expected["action"] = "noop"
    assert noop["receipt"] == expected
    assert noop["receipt"] is not caller_receipt
    assert set(noop["receipt"]) == RECEIPT_KEYS
    assert set(noop["receipt"]["owner"]) == {"project_id", "job_identity"}
    assert set(noop["receipt"]["source"]) == {"class", "ref", "availability"}
    assert set(noop["receipt"]["source"]["availability"]) == set(REQUIRED_NAMES)
    print("RECEIPT_KEYSETS=" + json.dumps({
        "top": sorted(noop["receipt"]),
        "owner": sorted(noop["receipt"]["owner"]),
        "source": sorted(noop["receipt"]["source"]),
        "availability": sorted(noop["receipt"]["source"]["availability"]),
        "noop_reused_caller_object": noop["receipt"] is caller_receipt,
    }, sort_keys=True))


@pytest.mark.parametrize(
    ("case", "jobs", "mutate_receipt", "message"),
    [
        (
            "foreign ownership",
            [{"id": "job-123", "name": "stagelink-public-catalog-refresh"}],
            lambda receipt: receipt["owner"].update(project_id="other-project"),
            "foreign ownership",
        ),
        (
            "duplicate match",
            [
                {"id": "job-a", "name": "stagelink-public-catalog-refresh"},
                {"id": "job-b", "name": "stagelink-public-catalog-refresh"},
            ],
            lambda receipt: None,
            "duplicate",
        ),
        (
            "receipt job missing",
            [{"id": "job-other", "name": "unrelated"}],
            lambda receipt: None,
            "receipt/job mismatch",
        ),
        (
            "receipt job renamed",
            [{"id": "job-123", "name": "foreign-name"}],
            lambda receipt: None,
            "receipt/job mismatch",
        ),
    ],
)
def test_conflicts_reject_without_mutation(tmp_path, case, jobs, mutate_receipt, message):
    root = write_bound_project(tmp_path / "stagelink")
    receipt = valid_receipt(root)
    mutate_receipt(receipt)
    spy = Spy([])

    with pytest.raises(ProvisioningError, match=message):
        reconcile_scheduled_consumer(
            root,
            declaration(root, schedule="0 7 * * *", script_seed=b"v2"),
            jobs=jobs,
            receipt=receipt,
            invoke=spy,
        )

    assert spy.calls == [], case
    print("FAKE_CONFLICT_TRACE=" + json.dumps({"case": case, "invocations": spy.calls}))


def test_existing_name_without_receipt_is_not_adopted_by_name(tmp_path):
    root = write_bound_project(tmp_path / "stagelink")
    spy = Spy([])

    with pytest.raises(ProvisioningError, match="ownership is absent"):
        reconcile_scheduled_consumer(
            root,
            declaration(root),
            jobs=[{"id": "foreign-job", "name": "stagelink-public-catalog-refresh"}],
            receipt=None,
            invoke=spy,
        )

    assert spy.calls == []


def test_receipt_and_argv_are_secret_free(tmp_path):
    root = write_bound_project(tmp_path / "stagelink")
    declared = declaration(root)
    sentinel = "secret-value-must-not-appear"
    spy = Spy([{"job_id": "job-123", "output": sentinel, "log": sentinel}])

    result = reconcile_scheduled_consumer(root, declared, jobs=[], receipt=None, invoke=spy)

    serialized_inputs_and_outputs = json.dumps(
        {"declaration": declared, "receipt": result["receipt"], "argv": spy.calls}, sort_keys=True
    )
    assert sentinel not in serialized_inputs_and_outputs
    assert set(result["receipt"]["source"]) == {"class", "ref", "availability"}


def test_project_instance_adapter_receipt_preserves_only_source_metadata(tmp_path):
    root = write_bound_project(tmp_path / "stagelink")
    declared = project_instance_declaration(root)
    result = reconcile_scheduled_consumer(
        root, declared, jobs=[], receipt=None, invoke=Spy([{"job_id": "job-123"}])
    )

    assert result["receipt"]["source"] == {
        "class": "project_instance_adapter",
        "ref": "stagelink:project-instance:supabase-readonly",
        "availability": {
            "SUPABASE_SERVICE_ROLE_KEY": True,
            "SUPABASE_URL": True,
        },
    }


class ChildSpy:
    def __init__(self, result=None, error=None):
        self.result = result if result is not None else {"exit_code": 0}
        self.error = error
        self.calls = []

    def __call__(self, script_identity, env):
        self.calls.append({"script_identity": script_identity, "env": env})
        if self.error is not None:
            raise self.error
        return self.result


def test_child_receives_only_the_two_declared_secret_names(tmp_path, monkeypatch):
    root = write_bound_project(tmp_path / "stagelink")
    plan = validate_scheduled_consumer(root, declaration(root))
    monkeypatch.setenv("HOME", "/sentinel/home")
    monkeypatch.setenv("PARENT_MARKER", "parent-sentinel")
    monkeypatch.setenv("UNRELATED_CREDENTIAL", "unrelated-sentinel")
    child = ChildSpy()

    result = run_scheduled_consumer_child(
        plan,
        source_values={
            "SUPABASE_URL": "https://fixture.supabase.invalid",
            "SUPABASE_SERVICE_ROLE_KEY": "fixture-service-role-sentinel",
        },
        child_runner=child,
    )

    assert result == {"exit_code": 0}
    assert child.calls == [{
        "script_identity": "stagelink/refresh_public_catalog.py",
        "env": {
            "SUPABASE_SERVICE_ROLE_KEY": "fixture-service-role-sentinel",
            "SUPABASE_URL": "https://fixture.supabase.invalid",
        },
    }]
    env_keys = sorted(child.calls[0]["env"])
    assert env_keys == REQUIRED_NAMES
    assert {"HOME", "PARENT_MARKER", "UNRELATED_CREDENTIAL"}.isdisjoint(env_keys)
    print("CHILD_ENV_KEYS=" + json.dumps(env_keys))


def test_project_instance_adapter_child_gets_exact_caller_values_without_fallback(tmp_path, monkeypatch):
    root = write_bound_project(tmp_path / "stagelink")
    plan = validate_scheduled_consumer(root, project_instance_declaration(root))
    monkeypatch.setenv("HOME", "/sentinel/home")
    monkeypatch.setenv("PARENT_MARKER", "parent-sentinel")
    monkeypatch.setenv("SUPABASE_URL", "forbidden-parent-fallback")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "forbidden-parent-fallback")
    child = ChildSpy()
    supplied = {
        "SUPABASE_URL": "https://caller-sentinel.invalid",
        "SUPABASE_SERVICE_ROLE_KEY": "caller-role-sentinel",
    }

    result = run_scheduled_consumer_child(plan, source_values=supplied, child_runner=child)

    assert result == {"exit_code": 0}
    assert child.calls == [{
        "script_identity": "stagelink/refresh_public_catalog.py",
        "env": {
            "SUPABASE_SERVICE_ROLE_KEY": "caller-role-sentinel",
            "SUPABASE_URL": "https://caller-sentinel.invalid",
        },
    }]
    assert set(child.calls[0]["env"]) == set(REQUIRED_NAMES)


@pytest.mark.parametrize(
    "source_values",
    [
        {"SUPABASE_URL": "url"},
        {
            "SUPABASE_URL": "url",
            "SUPABASE_SERVICE_ROLE_KEY": "key",
            "UNRELATED_TOKEN": "extra",
        },
        {"NEXT_PUBLIC_SUPABASE_URL": "url", "SUPABASE_SERVICE_ROLE_KEY": "key"},
    ],
)
def test_child_source_values_must_resolve_exact_declared_names(tmp_path, source_values):
    root = write_bound_project(tmp_path / "stagelink")
    plan = validate_scheduled_consumer(root, declaration(root))
    child = ChildSpy()

    with pytest.raises(ChildExecutionError, match="exact declared names"):
        run_scheduled_consumer_child(plan, source_values=source_values, child_runner=child)

    assert child.calls == []


def test_secret_sentinel_is_absent_from_all_non_child_surfaces(tmp_path):
    root = write_bound_project(tmp_path / "stagelink")
    declared = declaration(root)
    plan = validate_scheduled_consumer(root, declared)
    sentinel = "fixture-secret-sentinel"
    cron_spy = Spy([{"job_id": "job-123", "output": sentinel, "log": sentinel}])
    provisioned = reconcile_scheduled_consumer(root, declared, jobs=[], receipt=None, invoke=cron_spy)
    child = ChildSpy(result={"exit_code": 0, "output": sentinel, "log": sentinel})

    output = run_scheduled_consumer_child(
        plan,
        source_values={"SUPABASE_URL": sentinel, "SUPABASE_SERVICE_ROLE_KEY": sentinel},
        child_runner=child,
    )

    surfaces = {
        "declaration": declared,
        "normalized_plan": plan,
        "receipt": provisioned["receipt"],
        "argv": cron_spy.calls,
        "output": output,
    }
    assert sentinel not in json.dumps(surfaces, sort_keys=True)

    failing_child = ChildSpy(error=RuntimeError(sentinel))
    with pytest.raises(ChildExecutionError) as raised:
        run_scheduled_consumer_child(
            plan,
            source_values={"SUPABASE_URL": sentinel, "SUPABASE_SERVICE_ROLE_KEY": sentinel},
            child_runner=failing_child,
        )
    assert sentinel not in str(raised.value)
    print("SECRET_SENTINEL_LEAK=false")
