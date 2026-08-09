import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from harness_runtime.scheduled_consumer import ScheduledConsumerError, validate_scheduled_consumer


REQUIRED_NAMES = ["SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_URL"]


def write_bound_project(root: Path, project_id: str = "stagelink") -> Path:
    root.mkdir()
    managed = [".harness/project-binding.json", ".harness/runtime.lock.json"]
    for relative in managed:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.name == "runtime.lock.json":
            path.write_text("{}\n", encoding="utf-8")
    binding = {
        "schema": "harness.project-binding.v1",
        "managed_by": "harness-project-binding",
        "project": {"id": project_id, "root": str(root.resolve())},
        "managed_files": managed,
    }
    (root / ".harness/project-binding.json").write_text(
        json.dumps(binding, sort_keys=True) + "\n", encoding="utf-8"
    )
    return root


def stagelink_declaration(root: Path) -> dict:
    return {
        "schema": "harness.scheduled-readonly-consumer.v1",
        "project": {"id": "stagelink", "root": str(root.resolve())},
        "job": {
            "identity": "stagelink-public-catalog-refresh",
            "schedule": "0 6 * * *",
            "delivery": "local",
        },
        "script": {
            "identity": "stagelink/scripts/refresh_public_catalog.py",
            "digest": "sha256:" + hashlib.sha256(b"stage-link-readonly-v1").hexdigest(),
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


def test_stagelink_shaped_scheduled_readonly_consumer_is_allowed(tmp_path):
    root = write_bound_project(tmp_path / "stagelink")

    plan = validate_scheduled_consumer(root, stagelink_declaration(root))

    assert plan["project"] == {"id": "stagelink", "root": str(root.resolve())}
    assert plan["required_names"] == REQUIRED_NAMES
    assert plan["source"] == {
        "class": "injected_fixture",
        "ref": "stagelink:test-fixture:readonly",
        "availability": {name: True for name in REQUIRED_NAMES},
    }
    assert plan["declaration_digest"].startswith("sha256:")


def test_project_instance_adapter_is_allowed_by_runtime_and_schema(tmp_path):
    root = write_bound_project(tmp_path / "stagelink")
    declaration = stagelink_declaration(root)
    declaration["source"] = {
        "class": "project_instance_adapter",
        "ref": "stagelink:project-instance:supabase-readonly",
        "availability": {name: True for name in REQUIRED_NAMES},
    }

    plan = validate_scheduled_consumer(root, declaration)
    schema_path = Path(__file__).parents[2] / "contracts/scheduled-readonly-consumer.v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(declaration)

    assert plan["source"] == declaration["source"]


def test_project_instance_adapter_foreign_ref_is_rejected(tmp_path):
    root = write_bound_project(tmp_path / "stagelink")
    declaration = stagelink_declaration(root)
    declaration["source"] = {
        "class": "project_instance_adapter",
        "ref": "other-project:project-instance:supabase-readonly",
        "availability": {name: True for name in REQUIRED_NAMES},
    }

    rejected(root, declaration, "source ref")


def test_normalized_plan_digest_is_independent_of_declared_name_order(tmp_path):
    root = write_bound_project(tmp_path / "stagelink")
    first = stagelink_declaration(root)
    second = deepcopy(first)
    second["required_names"] = list(reversed(second["required_names"]))
    second["source"]["availability"] = dict(
        reversed(list(second["source"]["availability"].items()))
    )

    first_plan = validate_scheduled_consumer(root, first)
    second_plan = validate_scheduled_consumer(root, second)

    assert first_plan == second_plan


def rejected(root: Path, declaration: dict, message: str) -> None:
    with pytest.raises(ScheduledConsumerError, match=message):
        validate_scheduled_consumer(root, declaration)


def test_unbound_project_is_rejected(tmp_path):
    root = tmp_path / "stagelink"
    root.mkdir()
    rejected(root, stagelink_declaration(root), "bound and undrifted")


def test_drifted_binding_is_rejected(tmp_path):
    root = write_bound_project(tmp_path / "stagelink")
    (root / ".harness/runtime.lock.json").unlink()
    rejected(root, stagelink_declaration(root), "bound and undrifted")


def test_project_identity_mismatch_is_rejected(tmp_path):
    root = write_bound_project(tmp_path / "stagelink")
    declaration = stagelink_declaration(root)
    declaration["project"]["id"] = "other-project"
    rejected(root, declaration, "project identity")


@pytest.mark.parametrize(
    ("field", "value"),
    [("access", "write"), ("class", "scheduled_admin_consumer")],
)
def test_write_or_admin_capability_is_rejected(tmp_path, field, value):
    root = write_bound_project(tmp_path / "stagelink")
    declaration = stagelink_declaration(root)
    declaration["capability"][field] = value
    rejected(root, declaration, "read-only capability")


def test_cross_project_source_is_rejected(tmp_path):
    root = write_bound_project(tmp_path / "stagelink")
    declaration = stagelink_declaration(root)
    declaration["source"]["ref"] = "other-project:test-fixture:readonly"
    rejected(root, declaration, "source ref")


def test_unregistered_source_class_is_rejected(tmp_path):
    root = write_bound_project(tmp_path / "stagelink")
    declaration = stagelink_declaration(root)
    declaration["source"]["class"] = "dotenv"
    rejected(root, declaration, "source class")


def test_missing_source_availability_is_rejected(tmp_path):
    root = write_bound_project(tmp_path / "stagelink")
    declaration = stagelink_declaration(root)
    del declaration["source"]["availability"]["SUPABASE_URL"]
    rejected(root, declaration, "availability")


def test_false_source_availability_is_rejected(tmp_path):
    root = write_bound_project(tmp_path / "stagelink")
    declaration = stagelink_declaration(root)
    declaration["source"]["availability"]["SUPABASE_URL"] = False
    rejected(root, declaration, "availability")


def test_no_agent_must_be_true(tmp_path):
    root = write_bound_project(tmp_path / "stagelink")
    declaration = stagelink_declaration(root)
    declaration["no_agent"] = False
    rejected(root, declaration, "no_agent")


@pytest.mark.parametrize(
    "path",
    [("job", "identity"), ("script", "identity"), ("script", "digest")],
)
def test_stable_job_and_script_identity_and_digest_are_required(tmp_path, path):
    root = write_bound_project(tmp_path / "stagelink")
    declaration = stagelink_declaration(root)
    del declaration[path[0]][path[1]]
    rejected(root, declaration, "identity and digest")


@pytest.mark.parametrize(
    "names",
    [
        ["SUPABASE_URL"],
        [*REQUIRED_NAMES, "UNRELATED_TOKEN"],
        ["NEXT_PUBLIC_SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"],
    ],
)
def test_required_names_reject_missing_extra_and_aliases(tmp_path, names):
    root = write_bound_project(tmp_path / "stagelink")
    declaration = stagelink_declaration(root)
    declaration["required_names"] = names
    rejected(root, declaration, "exact required names")


def test_declaration_schema_accepts_only_the_secret_free_contract(tmp_path):
    root = write_bound_project(tmp_path / "stagelink")
    schema_path = Path(__file__).parents[2] / "contracts/scheduled-readonly-consumer.v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    declaration = stagelink_declaration(root)

    Draft202012Validator(schema).validate(declaration)
    invalid = deepcopy(declaration)
    invalid["source"]["secret_value"] = "sentinel-secret"
    errors = list(Draft202012Validator(schema).iter_errors(invalid))

    assert errors
    assert "sentinel-secret" not in json.dumps(declaration, sort_keys=True)
