import hashlib
import json
import re
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from harness_runtime.l3_cohort_snapshot import (
    CohortCompilerError,
    collect_native_records,
    compile_live_snapshot,
    compile_snapshot,
    serialize_snapshot,
)


POLICY_PATH = (
    Path("/Users/kann/projects/harness-brain/projects/harness-starter/contracts")
    / "l3_enrollment_policy.v1.yaml"
)
SCHEMA_PATH = Path("contracts/l3-cohort-snapshot.v1.schema.json")


def test_native_member_with_matching_manifest_is_allowed():
    snapshot = compile_snapshot(
        policy_path=POLICY_PATH,
        cutoff="2026-08-07T05:23:18Z",
        native_records=[
            {
                "project_id": "p_one",
                "native_slug": "one",
                "primary_root": "/repo/one",
                "manifest_bytes": (
                    b"schema: harness.project-manifest.v2\n"
                    b"project_slug: one\n"
                    b"workspace:\n"
                    b"  canonical_cwd: /repo/one\n"
                ),
            }
        ],
    )

    assert snapshot["enrollment_policy"] == {
        "source": str(POLICY_PATH),
        "revision": "sha256:" + hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
    }
    assert snapshot["cohort_members"][0]["classification"] == "baseline_ready"
    assert snapshot["cohort_members"][0]["reason"] == "source_native_active_record"


def test_native_slug_is_locator_alias_when_manifest_slug_differs():
    snapshot = compile_snapshot(
        policy_path=POLICY_PATH,
        cutoff="2026-08-07T05:23:18Z",
        native_records=[
            {
                "project_id": "p_class",
                "native_slug": "class",
                "primary_root": "/repo/harness-brain",
                "manifest_bytes": (
                    b"schema: harness.project-manifest.v2\n"
                    b"project_slug: harness-brain\n"
                    b"workspace:\n"
                    b"  canonical_cwd: /repo/harness-brain\n"
                ),
            }
        ],
    )

    member = snapshot["cohort_members"][0]
    assert member["native_slug"] == "class"
    assert member["evaluation_slug"] == "harness-brain"
    assert member["gaps"] == ["registry_alias_mismatch"]
    assert member["classification"] == "baseline_ready"
    assert {item["source"] for item in member["evidence"]} == {
        "native_project_registry",
        "canonical_manifest",
    }


def test_root_mismatch_is_retained_as_member_local_hold_gap():
    snapshot = compile_snapshot(
        policy_path=POLICY_PATH,
        cutoff="2026-08-07T05:23:18Z",
        native_records=[
            {
                "project_id": "p_one",
                "native_slug": "one",
                "primary_root": "/repo/one",
                "manifest_bytes": (
                    b"schema: harness.project-manifest.v2\n"
                    b"project_slug: one\n"
                    b"workspace:\n"
                    b"  canonical_cwd: /repo/other\n"
                ),
            }
        ],
    )

    assert len(snapshot["cohort_members"]) == 1
    assert snapshot["cohort_members"][0]["classification"] == "HOLD_GAP"
    assert snapshot["cohort_members"][0]["gaps"] == ["canonical_root_mismatch"]


@pytest.mark.parametrize(
    ("manifest_bytes", "gap", "evaluation_slug"),
    [
        (b"workspace: [unterminated\n", "manifest_malformed", None),
        (
            b"schema: harness.project-manifest.v2\nworkspace:\n  canonical_cwd: /repo/one\n",
            "manifest_missing_required_fields",
            None,
        ),
        (
            b"schema: harness.project-manifest.v2\nproject_slug: one\nworkspace: {}\n",
            "manifest_missing_required_fields",
            "one",
        ),
    ],
)
def test_manifest_defects_are_retained_as_hold_gaps(
    manifest_bytes, gap, evaluation_slug
):
    snapshot = compile_snapshot(
        policy_path=POLICY_PATH,
        cutoff="2026-08-07T05:23:18Z",
        native_records=[
            {
                "project_id": "p_one",
                "native_slug": "one",
                "primary_root": "/repo/one",
                "manifest_bytes": manifest_bytes,
            }
        ],
    )

    member = snapshot["cohort_members"][0]
    assert member["project_id"] == "p_one"
    assert member["evaluation_slug"] == evaluation_slug
    assert member["classification"] == "HOLD_GAP"
    assert member["gaps"] == [gap]


def native_record(project_id, native_slug, root, evaluation_slug=None):
    evaluation_slug = evaluation_slug or native_slug
    return {
        "project_id": project_id,
        "native_slug": native_slug,
        "primary_root": root,
        "manifest_bytes": (
            "schema: harness.project-manifest.v2\n"
            f"project_slug: {evaluation_slug}\n"
            "workspace:\n"
            f"  canonical_cwd: {root}\n"
        ).encode(),
    }


@pytest.mark.parametrize(
    ("records", "gap"),
    [
        (
            [
                native_record("p_same", "one", "/repo/one"),
                native_record("p_same", "two", "/repo/two"),
            ],
            "duplicate_project_id",
        ),
        (
            [
                native_record("p_one", "one", "/repo/shared"),
                native_record("p_two", "two", "/repo/shared"),
            ],
            "duplicate_primary_root",
        ),
        (
            [
                native_record("p_one", "one", "/repo/one", "shared"),
                native_record("p_two", "two", "/repo/two", "shared"),
            ],
            "duplicate_manifest_identity",
        ),
    ],
)
def test_identity_conflicts_retain_every_native_record_as_hold_gap(records, gap):
    snapshot = compile_snapshot(
        policy_path=POLICY_PATH,
        cutoff="2026-08-07T05:23:18Z",
        native_records=records,
    )

    assert len(snapshot["cohort_members"]) == 2
    assert {member["classification"] for member in snapshot["cohort_members"]} == {
        "HOLD_GAP"
    }
    assert all(gap in member["gaps"] for member in snapshot["cohort_members"])


def test_duplicate_manifest_keys_are_retained_as_hold_gap():
    record = native_record("p_one", "one", "/repo/one")
    record["manifest_bytes"] += b"project_slug: duplicate\n"

    snapshot = compile_snapshot(
        policy_path=POLICY_PATH,
        cutoff="2026-08-07T05:23:18Z",
        native_records=[record],
    )

    member = snapshot["cohort_members"][0]
    assert member["classification"] == "HOLD_GAP"
    assert member["evaluation_slug"] is None
    assert member["gaps"] == ["manifest_duplicate_key"]


def test_same_inputs_serialize_byte_identically_in_any_native_record_order():
    records = [
        native_record("p_two", "two", "/repo/two"),
        native_record("p_one", "one", "/repo/one"),
    ]

    first = compile_snapshot(
        policy_path=POLICY_PATH,
        cutoff="2026-08-07T05:23:18Z",
        native_records=records,
    )
    second = compile_snapshot(
        policy_path=POLICY_PATH,
        cutoff="2026-08-07T05:23:18Z",
        native_records=list(reversed(records)),
    )

    assert first["membership_digest"].startswith("sha256:")
    assert serialize_snapshot(first) == serialize_snapshot(second)
    assert [member["project_id"] for member in first["cohort_members"]] == [
        "p_one",
        "p_two",
    ]


def test_policy_explicitly_defines_authority_and_serialization_rules():
    policy_bytes = POLICY_PATH.read_bytes()
    policy = yaml.safe_load(policy_bytes)

    assert policy["schema"] == "harness.l3-enrollment-policy.v1"
    assert policy["policy_id"] == "C-L3.0b-R2-dynamic-enrollment-policy-authority"
    assert policy["membership"]["universe"] == "all_active_native_records_at_cutoff"
    assert policy["membership"]["source_commands"] == [
        "env -u HERMES_HOME hermes project list",
        "env -u HERMES_HOME hermes project show <native_slug>",
    ]
    assert policy["identity"]["stable"] == ["project_id", "canonical_native_primary_root"]
    assert policy["alias"]["evaluation_slug"] == "manifest.project_slug"
    assert policy["alias"]["locator_alias"] == "native_slug"
    assert policy["conflicts"]["classification"] == "HOLD_GAP"
    assert policy["serialization"]["canonical_json"] == {
        "sort_keys": True,
        "separators": [",", ":"],
        "ensure_ascii": False,
        "newline_terminated": True,
    }
    snapshot = compile_snapshot(
        policy_path=POLICY_PATH,
        cutoff="2026-08-07T05:23:18Z",
        native_records=[native_record("p_one", "one", "/repo/one")],
    )
    assert snapshot["enrollment_policy"]["revision"] == "sha256:" + hashlib.sha256(
        policy_bytes
    ).hexdigest()


def test_compiled_snapshot_conforms_to_cohort_schema():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    snapshot = compile_snapshot(
        policy_path=POLICY_PATH,
        cutoff="2026-08-07T05:23:18Z",
        native_records=[native_record("p_one", "one", "/repo/one")],
    )

    Draft202012Validator(schema).validate(snapshot)
    classification = schema["$defs"]["member"]["properties"]["classification"]
    assert classification == {
        "enum": ["baseline_ready", "non_applicable-approved", "HOLD_GAP"]
    }


def test_schema_rejects_legacy_or_unapproved_evaluation_states():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    snapshot = compile_snapshot(
        policy_path=POLICY_PATH,
        cutoff="2026-08-07T05:23:18Z",
        native_records=[native_record("p_one", "one", "/repo/one")],
    )
    snapshot["cohort_members"][0]["classification"] = "ALLOWED"
    assert list(validator.iter_errors(snapshot))

    snapshot["cohort_members"][0]["classification"] = "non_applicable-approved"
    snapshot["cohort_members"][0]["reason"] = "explicit_non_applicable_approval"
    assert list(validator.iter_errors(snapshot))


@pytest.mark.parametrize("classification", ["baseline_ready", "HOLD_GAP"])
@pytest.mark.parametrize(
    ("metadata_key", "metadata_value"),
    [
        ("approval_reference", "maat:invalid"),
        (
            "candidate_non_regression_condition",
            "candidate_does_not_reduce_required_membership",
        ),
    ],
)
def test_schema_rejects_approval_metadata_on_non_approved_classifications(
    classification, metadata_key, metadata_value
):
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    snapshot = compile_snapshot(
        policy_path=POLICY_PATH,
        cutoff="2026-08-07T05:23:18Z",
        native_records=[native_record("p_one", "one", "/repo/one")],
    )
    member = snapshot["cohort_members"][0]
    member["classification"] = classification
    member["reason"] = (
        "source_native_active_record" if classification == "baseline_ready" else "manifest_missing"
    )
    member[metadata_key] = metadata_value

    assert list(validator.iter_errors(snapshot))


def test_native_collection_uses_list_show_and_primary_root_manifests_only():
    outputs = {
        ("project", "list"): (
            "* harness-starter          Harness Starter  [1 folder(s)]\n"
            "  class                    Class  [2 folder(s)]\n"
        ),
        ("project", "show", "harness-starter"): (
            "harness-starter  [p_starter]\n"
            "  name:    Harness Starter\n"
            "  primary: /repo/starter\n"
        ),
        ("project", "show", "class"): (
            "class  [p_class]\n"
            "  name:    Class\n"
            "  primary: /repo/brain\n"
        ),
    }
    commands = []
    manifest_reads = []

    def run(args):
        commands.append(tuple(args))
        return outputs[tuple(args)]

    def read_manifest(path):
        manifest_reads.append(path)
        slug = "harness-brain" if path == Path("/repo/brain/manifest.yml") else "harness-starter"
        return native_record("unused", slug, str(path.parent))["manifest_bytes"]

    records = collect_native_records(run=run, read_manifest=read_manifest)

    assert commands == [
        ("project", "list"),
        ("project", "show", "harness-starter"),
        ("project", "show", "class"),
    ]
    assert manifest_reads == [
        Path("/repo/starter/manifest.yml"),
        Path("/repo/brain/manifest.yml"),
    ]
    assert [(record["project_id"], record["native_slug"]) for record in records] == [
        ("p_starter", "harness-starter"),
        ("p_class", "class"),
    ]


def test_live_compilation_retains_every_record_collected_at_cutoff():
    def run(args):
        if args == ["project", "list"]:
            return "  one                      One  [1 folder(s)]\n"
        return "one  [p_one]\n  name:    One\n  primary: /repo/one\n"

    snapshot = compile_live_snapshot(
        policy_path=POLICY_PATH,
        cutoff="2026-08-07T05:23:18Z",
        run=run,
        read_manifest=lambda path: native_record(
            "unused", "one", str(path.parent)
        )["manifest_bytes"],
    )

    assert snapshot["cutoff"] == "2026-08-07T05:23:18Z"
    assert [member["project_id"] for member in snapshot["cohort_members"]] == ["p_one"]


def test_membership_digest_drifts_with_cutoff_or_member_identity():
    record = native_record("p_one", "one", "/repo/one")
    baseline = compile_snapshot(
        policy_path=POLICY_PATH,
        cutoff="2026-08-07T05:23:18Z",
        native_records=[record],
    )
    later_cutoff = compile_snapshot(
        policy_path=POLICY_PATH,
        cutoff="2026-08-07T05:23:19Z",
        native_records=[record],
    )
    changed_identity = compile_snapshot(
        policy_path=POLICY_PATH,
        cutoff="2026-08-07T05:23:18Z",
        native_records=[native_record("p_two", "one", "/repo/one")],
    )

    assert baseline["membership_digest"] != later_cutoff["membership_digest"]
    assert baseline["membership_digest"] != changed_identity["membership_digest"]


def test_malformed_policy_fails_closed(tmp_path):
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text("membership: [unterminated\n")

    with pytest.raises(CohortCompilerError, match="policy is malformed"):
        compile_snapshot(
            policy_path=policy_path,
            cutoff="2026-08-07T05:23:18Z",
            native_records=[],
        )


def test_policy_semantic_drift_fails_closed(tmp_path):
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_bytes(
        POLICY_PATH.read_bytes().replace(
            b"all_active_native_records_at_cutoff", b"selected_native_records"
        )
    )

    with pytest.raises(CohortCompilerError, match="policy semantics are incompatible"):
        compile_snapshot(
            policy_path=policy_path,
            cutoff="2026-08-07T05:23:18Z",
            native_records=[],
        )


@pytest.mark.parametrize(
    ("path", "drifted_value"),
    [
        (("schema",), "harness.l3-enrollment-policy.v2"),
        (("policy_id",), "C-L3.0b-drifted"),
        (("membership", "universe"), "selected_native_records"),
        (("membership", "source_commands"), ["hermes project list"]),
        (("membership", "fixed_roster_or_allowlist"), "allowed"),
        (("membership", "per_project_exceptions"), "allowed"),
        (("cutoff", "format"), "RFC3339"),
        (("cutoff", "rule"), "compiler_generated_time"),
        (("identity", "stable"), ["project_id"]),
        (("identity", "canonical_native_primary_root"), "manifest.workspace.canonical_cwd"),
        (("identity", "manifest_identity"), "native_slug"),
        (("identity", "deterministic_order"), ["project_id"]),
        (("alias", "evaluation_slug"), "native_slug"),
        (("alias", "locator_alias"), "manifest.project_slug"),
        (("alias", "root_agrees_name_differs_gap"), "HOLD_GAP"),
        (("alias", "behavior"), "rename_native_record"),
        (("manifest", "source"), "<repository>/manifest.yml"),
        (("manifest", "required"), ["schema"]),
        (("manifest", "schema"), "harness.project-manifest.v1"),
        (("manifest", "root_rule"), "root_is_optional"),
        (("manifest", "invalid_record_behavior"), "exclude"),
        (("conflicts", "keys"), ["project_id"]),
        (("conflicts", "classification"), "baseline_ready"),
        (("conflicts", "behavior"), "deduplicate"),
        (("classifications", "baseline_ready", "value"), "ALLOWED"),
        (("classifications", "baseline_ready", "reason"), "active"),
        (("classifications", "baseline_ready", "evidence_source"), "manifest"),
        (("classifications", "non_applicable_approved", "value"), "non_applicable"),
        (("classifications", "non_applicable_approved", "approval_reference"), "optional"),
        (("classifications", "non_applicable_approved", "candidate_non_regression_condition"), "optional"),
        (("classifications", "non_applicable_approved", "auto_generation"), "allowed"),
        (("classifications", "held", "value"), "BLOCKED"),
        (("serialization", "policy_revision"), "sha256_canonical_policy"),
        (("serialization", "canonical_json", "sort_keys"), False),
        (("serialization", "canonical_json", "separators"), [", ", ": "]),
        (("serialization", "canonical_json", "ensure_ascii"), True),
        (("serialization", "canonical_json", "newline_terminated"), False),
        (("serialization", "membership_digest", "algorithm"), "sha512"),
        (("serialization", "membership_digest", "input"), ["members"]),
        (("compiler", "access"), "read_write"),
        (("compiler", "allowed_sources"), ["native_registry"]),
        (("compiler", "mutation_prohibited"), ["repositories"]),
    ],
)
def test_each_required_policy_semantic_drift_fails_at_named_field(
    tmp_path, path, drifted_value
):
    policy = yaml.safe_load(POLICY_PATH.read_bytes())
    target = policy
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = drifted_value
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(yaml.safe_dump(policy, sort_keys=False))

    with pytest.raises(CohortCompilerError, match=r"policy field " + re.escape(".".join(path))):
        compile_snapshot(
            policy_path=policy_path,
            cutoff="2026-08-07T05:23:18Z",
            native_records=[],
        )


@pytest.mark.parametrize(
    "cutoff",
    ["2026-08-07", "2026-08-07T05:23:18", "2026-08-07T05:23:18+00:00", "not-a-time"],
)
def test_cutoff_must_be_rfc3339_utc(cutoff):
    with pytest.raises(CohortCompilerError, match="cutoff must be RFC3339 UTC"):
        compile_snapshot(policy_path=POLICY_PATH, cutoff=cutoff, native_records=[])


@pytest.mark.parametrize("schema", [None, "harness.project-manifest.v1"])
def test_missing_or_wrong_manifest_schema_is_retained_as_hold_gap(schema):
    record = native_record("p_one", "one", "/repo/one")
    manifest = yaml.safe_load(record["manifest_bytes"])
    if schema is None:
        manifest.pop("schema")
    else:
        manifest["schema"] = schema
    record["manifest_bytes"] = yaml.safe_dump(manifest).encode()

    member = compile_snapshot(
        policy_path=POLICY_PATH,
        cutoff="2026-08-07T05:23:18Z",
        native_records=[record],
    )["cohort_members"][0]

    assert member["classification"] == "HOLD_GAP"
    assert member["gaps"] == ["manifest_schema_invalid"]


def test_registry_list_malformed_record_with_identity_is_retained_as_hold_gap():
    outputs = {
        ("project", "list"): "  one malformed-record\n",
        ("project", "show", "one"): "one  [p_one]\n  primary: /repo/one\n",
    }
    records = collect_native_records(
        run=lambda args: outputs[tuple(args)],
        read_manifest=lambda path: native_record(
            "unused", "one", str(path.parent)
        )["manifest_bytes"],
    )

    member = compile_snapshot(
        policy_path=POLICY_PATH,
        cutoff="2026-08-07T05:23:18Z",
        native_records=records,
    )["cohort_members"][0]
    assert member["classification"] == "HOLD_GAP"
    assert "registry_list_malformed" in member["gaps"]


def test_registry_record_without_retainable_identity_fails_closed():
    def run(args):
        if args == ["project", "list"]:
            return "  one malformed-record\n"
        return "one\n"

    with pytest.raises(CohortCompilerError, match="identity is incomplete"):
        collect_native_records(run=run, read_manifest=lambda path: b"")


def test_duplicate_registry_show_fields_are_retained_as_hold_gap():
    def run(args):
        if args == ["project", "list"]:
            return "  one  One  [1 folder(s)]\n"
        return "one  [p_one]\none  [p_other]\n  primary: /repo/one\n"

    records = collect_native_records(
        run=run,
        read_manifest=lambda path: native_record(
            "unused", "one", str(path.parent)
        )["manifest_bytes"],
    )
    member = compile_snapshot(
        policy_path=POLICY_PATH,
        cutoff="2026-08-07T05:23:18Z",
        native_records=records,
    )["cohort_members"][0]

    assert member["classification"] == "HOLD_GAP"
    assert member["gaps"] == ["registry_show_duplicate_field"]


def test_duplicate_registry_list_records_are_retained_as_hold_gaps():
    def run(args):
        if args == ["project", "list"]:
            return "  one  One  [1 folder(s)]\n  one  One  [1 folder(s)]\n"
        return "one  [p_one]\n  primary: /repo/one\n"

    records = collect_native_records(
        run=run,
        read_manifest=lambda path: native_record(
            "unused", "one", str(path.parent)
        )["manifest_bytes"],
    )
    members = compile_snapshot(
        policy_path=POLICY_PATH,
        cutoff="2026-08-07T05:23:18Z",
        native_records=records,
    )["cohort_members"]

    assert len(members) == 2
    assert all(member["classification"] == "HOLD_GAP" for member in members)
    assert all("duplicate_registry_record" in member["gaps"] for member in members)


def test_non_applicable_requires_explicit_approval_and_non_regression():
    record = native_record("p_one", "one", "/repo/one")
    baseline = compile_snapshot(
        policy_path=POLICY_PATH,
        cutoff="2026-08-07T05:23:18Z",
        native_records=[record],
    )
    assert baseline["cohort_members"][0]["classification"] == "baseline_ready"

    with pytest.raises(CohortCompilerError, match="non-applicable approval"):
        compile_snapshot(
            policy_path=POLICY_PATH,
            cutoff="2026-08-07T05:23:18Z",
            native_records=[record],
            non_applicable_approvals={"p_one": {"approval_reference": "maat:123"}},
        )

    approved = compile_snapshot(
        policy_path=POLICY_PATH,
        cutoff="2026-08-07T05:23:18Z",
        native_records=[record],
        non_applicable_approvals={
            "p_one": {
                "approval_reference": "maat:123",
                "candidate_non_regression_condition": "candidate_does_not_reduce_required_membership",
            }
        },
    )["cohort_members"][0]
    assert approved["classification"] == "non_applicable-approved"
    assert approved["approval_reference"] == "maat:123"


def test_duplicate_induced_final_hold_rejects_non_applicable_approval():
    records = [
        native_record("p_one", "one", "/repo/shared"),
        native_record("p_two", "two", "/repo/shared"),
    ]

    with pytest.raises(
        CohortCompilerError,
        match="non-applicable approval cannot target final HOLD_GAP for p_one",
    ):
        compile_snapshot(
            policy_path=POLICY_PATH,
            cutoff="2026-08-07T05:23:18Z",
            native_records=records,
            non_applicable_approvals={
                "p_one": {
                    "approval_reference": "maat:duplicate",
                    "candidate_non_regression_condition": "candidate_does_not_reduce_required_membership",
                }
            },
        )


def test_policy_byte_drift_changes_policy_and_membership_digests(tmp_path):
    drifted = tmp_path / "policy.yaml"
    drifted.write_bytes(POLICY_PATH.read_bytes() + b"\n# immutable revision drift\n")
    record = native_record("p_one", "one", "/repo/one")
    baseline = compile_snapshot(
        policy_path=POLICY_PATH,
        cutoff="2026-08-07T05:23:18Z",
        native_records=[record],
    )
    changed = compile_snapshot(
        policy_path=drifted,
        cutoff="2026-08-07T05:23:18Z",
        native_records=[record],
    )

    assert baseline["enrollment_policy"]["revision"] != changed["enrollment_policy"]["revision"]
    assert baseline["membership_digest"] != changed["membership_digest"]
