import copy
import hashlib
import json
import os
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from harness_runtime.l3_adaptation import (
    AdmissionError,
    compile_admission,
    serialize_admission,
)

COHORT_PATH = Path(os.environ["HARNESS_HISTORICAL_L3_COHORT_PATH"])
COHORT_BYTES = COHORT_PATH.read_bytes()
COHORT_SHA256 = "0caf2513e3870db4773a9097aa9ab8fbcd74323b80fb9664ad1b8f214d4258a1"
BASELINE_COMMIT = "4bd38ae20a27535166354ddcc5a77d55691fa296"
BASELINE_TREE = "c78f6a35bfb4a3aceca5fa5a7d90bdf4d42ac6ce"
BASELINE_CLEAN = False
BASELINE_STATUS_DIGEST = "sha256:e37d1592383b429ff526234ce20c5be0685e5fab653aefa325cb424dca5b4952"
SCHEMA_PATH = Path("contracts/l3-adaptation.v1.schema.json")
COHORT_SCHEMA_PATH = Path("contracts/l3-cohort-snapshot.v1.schema.json")


BENEFIT = "direct_target_runtime_evidence_reduces_declared_ac_failure"
NON_INFERIORITY = "all_declared_preserved_ac_and_control_surfaces_remain_non_regressed"
REGRESSION_STOP = "any_material_semantic_regression_requires_revert"
UNCERTAINTY = "missing_direct_evidence_or_unresolved_uncertainty_requires_owner_hold"


def cohort_binding(artifact_bytes=COHORT_BYTES):
    cohort = json.loads(artifact_bytes)
    return {
        "artifact_ref": str(COHORT_PATH),
        "artifact_sha256": "sha256:" + COHORT_SHA256,
        "schema": cohort["schema"],
        "enrollment_policy_revision": cohort["enrollment_policy"]["revision"],
        "cutoff": cohort["cutoff"],
        "membership_digest": cohort["membership_digest"],
        "members": [
            {
                key: member[key]
                for key in (
                    "project_id",
                    "native_slug",
                    "evaluation_slug",
                    "primary_root",
                    "classification",
                    "reason",
                    "gaps",
                    "approval_reference",
                    "candidate_non_regression_condition",
                )
                if key in member
            }
            for member in cohort["cohort_members"]
        ],
    }


def valid_admission():
    return {
        "schema": "harness.l3-adaptation-candidate.v1",
        "candidate_ref": "C-L3.1:manual-candidate-001",
        "status": "candidate-only",
        "cohort": cohort_binding(),
        "baseline": {
            "commit": BASELINE_COMMIT,
            "tree": BASELINE_TREE,
            "worktree_state": {
                "clean": BASELINE_CLEAN,
                "status_digest": BASELINE_STATUS_DIGEST,
            },
        },
        "candidate": {
            "identity": "isolated:manual-candidate-001",
            "baseline_commit": BASELINE_COMMIT,
            "allowed_write_refs": ["runtime/target.py"],
            "causal_hypothesis": "The bounded target change removes the declared runtime failure cause.",
            "target": {
                "c_ref": "C-L3.target",
                "ac_ref": "AC-runtime-1",
                "expected_ac_effect": "Reduce the declared target runtime failure without changing controls.",
            },
        },
        "fixed_evaluation": {
            "model": {
                "identity": "model:fixed-v1",
                "configuration_digest": "sha256:" + "2" * 64,
            },
            "evaluator": {
                "identity": "evaluator:fixed-v1",
                "configuration_digest": "sha256:" + "3" * 64,
            },
            "splits": {
                "held_in_ref": "split:held-in-v1",
                "held_in_digest": "sha256:" + "4" * 64,
                "held_out_ref": "split:held-out-v1",
                "held_out_digest": "sha256:" + "5" * 64,
                "sampling_identity": "sampling:fixed-v1",
                "secrecy_boundary": "held_out_opaque_no_content_access",
            },
        },
        "criteria": {
            "benefit": BENEFIT,
            "non_inferiority": NON_INFERIORITY,
            "regression_stop": REGRESSION_STOP,
            "uncertainty_disposition": UNCERTAINTY,
            "preserved_ac_refs": ["AC-control-1"],
        },
        "immutable_controls": {
            "evaluator_ref": "evaluator:fixed-v1",
            "held_out_ref": "split:held-out-v1",
            "permission_boundary_ref": "authority:permission-v1",
            "maat_disposition_ref": "authority:maat-v1",
            "sia_promotion_ref": "authority:sia-v1",
            "cohort_policy_ref": "sha256:4e7aa55f539fb1330adbf0fcd2a4e4d6255f5161a466d45212c1af6354cf1585",
            "execution_receipt_schema_ref": "harness.runtime.execution-receipt.v1",
            "additional_refs": ["contracts/control-surface.v1"],
        },
        "authority": {
            "confirm": "Maat",
            "revert": "Maat",
            "owner_hold": "Maat",
            "learning_consideration": "SIA",
            "learning_automatic": False,
        },
        "observability": {
            "allowed_projections": ["candidate_ref", "correlation_key", "semantic_outcome"],
            "correlation_key": {
                "name": "candidate_ref",
                "definition": "Exact candidate_ref joined only within this bounded evaluation.",
            },
            "retention_seconds": 86400,
            "cardinality_ceiling": 100,
            "max_dashboards": 0,
            "max_alerts": 0,
        },
    }


def compile_valid(admission=None, **overrides):
    admission = admission or valid_admission()
    return compile_admission(
        admission,
        cohort_artifact_bytes=overrides.pop("cohort_artifact_bytes", COHORT_BYTES),
        expected_cohort_artifact_sha256=overrides.pop(
            "expected_cohort_artifact_sha256", COHORT_SHA256
        ),
        expected_baseline_commit=overrides.pop("expected_baseline_commit", BASELINE_COMMIT),
        expected_baseline_tree=overrides.pop("expected_baseline_tree", BASELINE_TREE),
        expected_baseline_clean=overrides.pop("expected_baseline_clean", BASELINE_CLEAN),
        expected_baseline_status_digest=overrides.pop(
            "expected_baseline_status_digest", BASELINE_STATUS_DIGEST
        ),
        **overrides,
    )


def compile_with_trusted_baseline(admission=None, **overrides):
    return compile_valid(
        admission,
        expected_baseline_clean=overrides.pop("expected_baseline_clean", BASELINE_CLEAN),
        expected_baseline_status_digest=overrides.pop(
            "expected_baseline_status_digest", BASELINE_STATUS_DIGEST
        ),
        **overrides,
    )


def non_applicable_frozen_member(
    *,
    approval_reference="approval:C-L3.1",
    condition="candidate_does_not_reduce_required_membership",
):
    cohort = json.loads(COHORT_BYTES)
    member = cohort["cohort_members"][0]
    member["classification"] = "non_applicable-approved"
    if approval_reference is not None:
        member["approval_reference"] = approval_reference
    if condition is not None:
        member["candidate_non_regression_condition"] = condition
    artifact_bytes = json.dumps(
        cohort, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    digest = hashlib.sha256(artifact_bytes).hexdigest()
    admission = valid_admission()
    admission["cohort"] = cohort_binding(artifact_bytes)
    admission["cohort"]["artifact_sha256"] = "sha256:" + digest
    return admission, artifact_bytes, digest


def mutate(path, value):
    admission = valid_admission()
    target = admission
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return admission


@pytest.mark.parametrize(
    ("path", "spoofed_value"),
    [
        (("baseline", "worktree_state", "status_digest"), "sha256:" + "0" * 64),
        (("baseline", "worktree_state", "clean"), True),
    ],
)
def test_trusted_baseline_binding_rejects_spoofed_projection(path, spoofed_value):
    projection, _ = compile_with_trusted_baseline()
    assert projection["baseline"]["worktree_state"] == {
        "clean": BASELINE_CLEAN,
        "status_digest": BASELINE_STATUS_DIGEST,
    }
    with pytest.raises(AdmissionError, match="baseline worktree"):
        compile_with_trusted_baseline(mutate(path, spoofed_value))


@pytest.mark.parametrize(
    ("approval_reference", "condition"),
    [
        ("approval:C-L3.1", "wrong_condition"),
        ("", "candidate_does_not_reduce_required_membership"),
        (1, "candidate_does_not_reduce_required_membership"),
        (None, "candidate_does_not_reduce_required_membership"),
        ("approval:C-L3.1", None),
    ],
)
def test_non_applicable_approved_compiler_schema_denial_parity(
    approval_reference, condition
):
    admission, artifact_bytes, digest = non_applicable_frozen_member(
        approval_reference=approval_reference, condition=condition
    )
    try:
        compile_valid(
            admission,
            cohort_artifact_bytes=artifact_bytes,
            expected_cohort_artifact_sha256=digest,
        )
    except AdmissionError:
        compiler_rejected = True
    else:
        compiler_rejected = False
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    schema_rejected = bool(list(Draft202012Validator(schema).iter_errors(admission)))

    assert compiler_rejected == schema_rejected
    assert compiler_rejected


def test_non_applicable_approved_compiler_schema_acceptance_parity():
    admission, artifact_bytes, digest = non_applicable_frozen_member()
    projection, _ = compile_valid(
        admission,
        cohort_artifact_bytes=artifact_bytes,
        expected_cohort_artifact_sha256=digest,
    )
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    Draft202012Validator(schema).validate(projection)
    assert projection == admission


@pytest.mark.parametrize(
    "forbidden_field",
    ["approval_reference", "candidate_non_regression_condition"],
)
def test_baseline_ready_frozen_forbidden_field_compiler_schema_denial_parity(
    forbidden_field,
):
    cohort = json.loads(COHORT_BYTES)
    cohort["cohort_members"][0][forbidden_field] = None
    artifact_bytes = json.dumps(
        cohort, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    digest = hashlib.sha256(artifact_bytes).hexdigest()
    admission = valid_admission()
    admission["cohort"] = cohort_binding(artifact_bytes)
    admission["cohort"]["artifact_sha256"] = "sha256:" + digest
    admission["cohort"]["members"][0].pop(forbidden_field)

    cohort_schema = json.loads(COHORT_SCHEMA_PATH.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(cohort_schema).iter_errors(cohort))
    with pytest.raises(AdmissionError):
        compile_valid(
            admission,
            cohort_artifact_bytes=artifact_bytes,
            expected_cohort_artifact_sha256=digest,
        )


@pytest.mark.parametrize(
    ("projected_clean", "expected_clean"), [(True, False), (False, True)]
)
def test_trusted_baseline_clean_mismatch_fails_in_both_directions(
    projected_clean, expected_clean
):
    admission = mutate(("baseline", "worktree_state", "clean"), projected_clean)
    with pytest.raises(AdmissionError, match="baseline worktree state mismatch"):
        compile_valid(admission, expected_baseline_clean=expected_clean)


@pytest.mark.parametrize("expected_clean", [0, 1, "false"])
def test_trusted_baseline_clean_requires_actual_boolean(expected_clean):
    with pytest.raises(AdmissionError, match="expected baseline worktree clean"):
        compile_valid(expected_baseline_clean=expected_clean)


@pytest.mark.parametrize(
    "expected_digest",
    ["", "sha256:" + "A" * 64, "sha256:" + "0" * 63, 1],
)
def test_trusted_baseline_status_digest_rejects_malformed_values(expected_digest):
    with pytest.raises(AdmissionError, match="expected baseline worktree status"):
        compile_valid(expected_baseline_status_digest=expected_digest)


def test_trusted_baseline_inputs_are_mandatory_keyword_arguments():
    common = {
        "cohort_artifact_bytes": COHORT_BYTES,
        "expected_cohort_artifact_sha256": COHORT_SHA256,
        "expected_baseline_commit": BASELINE_COMMIT,
        "expected_baseline_tree": BASELINE_TREE,
    }
    with pytest.raises(TypeError, match="expected_baseline_clean"):
        compile_admission(
            valid_admission(),
            expected_baseline_status_digest=BASELINE_STATUS_DIGEST,
            **common,
        )
    with pytest.raises(TypeError, match="expected_baseline_status_digest"):
        compile_admission(
            valid_admission(), expected_baseline_clean=BASELINE_CLEAN, **common
        )


def test_complete_admission_compiles_to_canonical_candidate_projection_and_digest():
    projection, digest = compile_valid()
    canonical = json.dumps(
        projection, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8") + b"\n"

    assert projection == valid_admission()
    assert serialize_admission(projection) == canonical
    assert digest == "sha256:" + hashlib.sha256(canonical).hexdigest()
    assert serialize_admission(projection).endswith(b"\n")
    assert "candidate-only" in canonical.decode("utf-8")


def test_compiled_projection_conforms_to_draft_2020_12_schema():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(compile_valid()[0])


@pytest.mark.parametrize(
    "path",
    [
        (),
        ("cohort",),
        ("cohort", "members", 0),
        ("baseline",),
        ("baseline", "worktree_state"),
        ("candidate",),
        ("candidate", "target"),
        ("fixed_evaluation",),
        ("fixed_evaluation", "model"),
        ("fixed_evaluation", "evaluator"),
        ("fixed_evaluation", "splits"),
        ("criteria",),
        ("immutable_controls",),
        ("authority",),
        ("observability",),
        ("observability", "correlation_key"),
    ],
)
def test_unknown_fields_are_rejected_recursively_by_compiler_and_schema(path):
    admission = valid_admission()
    target = admission
    for part in path:
        target = target[part]
    target["smuggled"] = True

    with pytest.raises(AdmissionError, match="fields"):
        compile_valid(admission)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(admission))


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("cohort", "artifact_sha256"), "sha256:" + "0" * 64),
        (("cohort", "enrollment_policy_revision"), "sha256:" + "0" * 64),
        (("cohort", "cutoff"), "2026-08-07T06:19:32Z"),
        (("cohort", "membership_digest"), "sha256:" + "0" * 64),
        (("cohort", "schema"), "harness.l3-cohort-snapshot.v2"),
    ],
)
def test_cohort_identity_mismatch_fails_closed(path, value):
    with pytest.raises(AdmissionError, match="cohort"):
        compile_valid(mutate(path, value))


def test_changed_frozen_artifact_or_expected_digest_fails_closed():
    changed = COHORT_BYTES.replace(b"harness-brain", b"harness-drain", 1)
    with pytest.raises(AdmissionError, match="artifact digest"):
        compile_valid(cohort_artifact_bytes=changed)
    with pytest.raises(AdmissionError, match="artifact digest"):
        compile_valid(expected_cohort_artifact_sha256="0" * 64)


def test_selective_subset_duplicate_or_hold_gap_member_fails_closed():
    admission = valid_admission()
    admission["cohort"]["members"].pop()
    with pytest.raises(AdmissionError, match="cohort members"):
        compile_valid(admission)

    admission = valid_admission()
    admission["cohort"]["members"][1] = copy.deepcopy(admission["cohort"]["members"][0])
    with pytest.raises(AdmissionError, match="duplicate|cohort members"):
        compile_valid(admission)

    cohort = json.loads(COHORT_BYTES)
    cohort["cohort_members"][0]["classification"] = "HOLD_GAP"
    frozen = json.dumps(cohort, separators=(",", ":")).encode()
    digest = hashlib.sha256(frozen).hexdigest()
    admission = valid_admission()
    admission["cohort"]["artifact_sha256"] = "sha256:" + digest
    admission["cohort"]["members"][0]["classification"] = "HOLD_GAP"
    with pytest.raises(AdmissionError, match="HOLD_GAP"):
        compile_valid(
            admission,
            cohort_artifact_bytes=frozen,
            expected_cohort_artifact_sha256=digest,
        )


@pytest.mark.parametrize("classification", ["allowed", "PASS", "non_applicable"])
def test_unsupported_member_classification_fails_closed(classification):
    with pytest.raises(AdmissionError, match="classification|cohort members"):
        compile_valid(mutate(("cohort", "members", 0, "classification"), classification))


def test_baseline_identity_and_explicit_worktree_state_are_required_and_pinned():
    for key in ("commit", "tree", "worktree_state"):
        admission = valid_admission()
        admission["baseline"].pop(key)
        with pytest.raises(AdmissionError):
            compile_valid(admission)
    with pytest.raises(AdmissionError, match="baseline"):
        compile_valid(mutate(("baseline", "commit"), "a" * 40))
    with pytest.raises(AdmissionError, match="baseline"):
        compile_valid(expected_baseline_tree="a" * 40)
    assert compile_valid()[0]["baseline"]["worktree_state"]["clean"] is False


@pytest.mark.parametrize(
    "refs",
    [
        [],
        ["runtime/target.py", "runtime/target.py"],
        ["runtime/target", "runtime/target/child.py"],
        ["/runtime/target.py"],
        ["runtime/./target.py"],
        ["runtime/../target.py"],
        ["runtime//target.py"],
        ["."],
    ],
)
def test_mutable_refs_reject_empty_duplicate_ambiguous_or_aliasing_paths(refs):
    with pytest.raises(AdmissionError, match="write refs"):
        compile_valid(mutate(("candidate", "allowed_write_refs"), refs))


def test_candidate_identity_is_isolated_and_bound_to_baseline():
    with pytest.raises(AdmissionError, match="candidate identity"):
        compile_valid(mutate(("candidate", "identity"), BASELINE_COMMIT))
    with pytest.raises(AdmissionError, match="candidate baseline"):
        compile_valid(mutate(("candidate", "baseline_commit"), "a" * 40))


def test_mutable_refs_are_disjoint_from_every_immutable_control_ref():
    for key in (
        "evaluator_ref",
        "held_out_ref",
        "permission_boundary_ref",
        "maat_disposition_ref",
        "sia_promotion_ref",
        "cohort_policy_ref",
        "execution_receipt_schema_ref",
    ):
        admission = valid_admission()
        admission["immutable_controls"][key] = "runtime/target.py"
        with pytest.raises(AdmissionError, match="immutable control"):
            compile_valid(admission)
    admission = valid_admission()
    admission["immutable_controls"]["additional_refs"] = ["runtime/target.py"]
    with pytest.raises(AdmissionError, match="immutable control"):
        compile_valid(admission)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("candidate", "causal_hypothesis"), "generic"),
        (("candidate", "causal_hypothesis"), ["one", "two"]),
        (("candidate", "target", "c_ref"), ""),
        (("candidate", "target", "ac_ref"), ["AC1", "AC2"]),
        (("candidate", "target", "expected_ac_effect"), ["one", "two"]),
        (("candidate", "target", "expected_ac_effect"), "generic"),
    ],
)
def test_exactly_one_specific_hypothesis_target_and_effect_are_required(path, value):
    with pytest.raises(AdmissionError, match="text|target|hypothesis|effect"):
        compile_valid(mutate(path, value))


@pytest.mark.parametrize(
    "path",
    [
        ("fixed_evaluation", "model", "identity"),
        ("fixed_evaluation", "model", "configuration_digest"),
        ("fixed_evaluation", "evaluator", "identity"),
        ("fixed_evaluation", "evaluator", "configuration_digest"),
        ("fixed_evaluation", "splits", "held_in_ref"),
        ("fixed_evaluation", "splits", "held_in_digest"),
        ("fixed_evaluation", "splits", "held_out_ref"),
        ("fixed_evaluation", "splits", "held_out_digest"),
        ("fixed_evaluation", "splits", "sampling_identity"),
        ("fixed_evaluation", "splits", "secrecy_boundary"),
    ],
)
def test_fixed_evaluation_identities_are_mandatory(path):
    admission = valid_admission()
    target = admission
    for key in path[:-1]:
        target = target[key]
    target.pop(path[-1])
    with pytest.raises(AdmissionError):
        compile_valid(admission)


def test_held_in_and_held_out_identities_must_differ():
    admission = valid_admission()
    admission["fixed_evaluation"]["splits"]["held_out_ref"] = "split:held-in-v1"
    with pytest.raises(AdmissionError, match="held-in and held-out"):
        compile_valid(admission)
    admission = valid_admission()
    admission["fixed_evaluation"]["splits"]["held_out_digest"] = "sha256:" + "4" * 64
    with pytest.raises(AdmissionError, match="held-in and held-out"):
        compile_valid(admission)


def test_held_out_content_is_neither_accepted_nor_returned():
    admission = valid_admission()
    admission["fixed_evaluation"]["splits"]["held_out_content"] = ["secret"]
    with pytest.raises(AdmissionError, match="fields"):
        compile_valid(admission)
    projection, _ = compile_valid()
    assert "held_out_content" not in json.dumps(projection)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("criteria", "benefit"), "score improves"),
        (("criteria", "non_inferiority"), "mostly unchanged"),
        (("criteria", "regression_stop"), "continue"),
        (("criteria", "uncertainty_disposition"), "approve"),
        (("immutable_controls", "evaluator_ref"), "evaluator:other"),
        (("immutable_controls", "held_out_ref"), "split:other"),
        (("immutable_controls", "cohort_policy_ref"), "sha256:" + "0" * 64),
    ],
)
def test_semantic_criteria_and_linked_controls_are_fixed(path, value):
    with pytest.raises(AdmissionError):
        compile_valid(mutate(path, value))


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("observability", "allowed_projections"), []),
        (("observability", "allowed_projections"), ["candidate_ref", "candidate_ref"]),
        (("observability", "retention_seconds"), 0),
        (("observability", "retention_seconds"), -1),
        (("observability", "retention_seconds"), "unbounded"),
        (("observability", "cardinality_ceiling"), 0),
        (("observability", "max_dashboards"), -1),
        (("observability", "max_alerts"), -1),
        (("observability", "correlation_key"), "candidate_ref"),
    ],
)
def test_observability_budget_must_be_explicit_and_finite(path, value):
    with pytest.raises(AdmissionError, match="observability|fields"):
        compile_valid(mutate(path, value))


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("status",), "PASS"),
        (("authority", "confirm"), "Ptah"),
        (("authority", "revert"), "candidate"),
        (("authority", "owner_hold"), "owner"),
        (("authority", "learning_consideration"), "Maat"),
        (("authority", "learning_automatic"), True),
    ],
)
def test_status_and_disposition_authority_cannot_be_escalated(path, value):
    with pytest.raises(AdmissionError):
        compile_valid(mutate(path, value))


@pytest.mark.parametrize(
    "field",
    ["pass", "approval", "merge", "activation", "replacement", "promotion", "learning", "execution", "goal_closure", "receipt"],
)
def test_unauthorized_output_fields_are_rejected(field):
    admission = valid_admission()
    admission[field] = True
    with pytest.raises(AdmissionError, match="fields"):
        compile_valid(admission)


def test_digest_and_serialization_drift_with_any_admitted_identity_change():
    projection, digest = compile_valid()
    changed = valid_admission()
    changed["observability"]["retention_seconds"] += 1
    changed_projection, changed_digest = compile_valid(changed)

    assert digest != changed_digest
    assert serialize_admission(projection) != serialize_admission(changed_projection)
    assert "\\u" not in serialize_admission(projection).decode("utf-8")


def test_module_has_no_file_network_subprocess_or_live_state_operation():
    source = Path("runtime/harness_runtime/l3_adaptation.py").read_text(encoding="utf-8")
    for prohibited_import in ("pathlib", "os", "subprocess", "socket", "urllib", "http", "requests"):
        assert f"import {prohibited_import}" not in source
        assert f"from {prohibited_import}" not in source
