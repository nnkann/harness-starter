from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any

SCHEMA = "harness.l3-adaptation-candidate.v1"
BENEFIT = "direct_target_runtime_evidence_reduces_declared_ac_failure"
NON_INFERIORITY = "all_declared_preserved_ac_and_control_surfaces_remain_non_regressed"
REGRESSION_STOP = "any_material_semantic_regression_requires_revert"
UNCERTAINTY_DISPOSITION = (
    "missing_direct_evidence_or_unresolved_uncertainty_requires_owner_hold"
)
SECRECY_BOUNDARY = "held_out_opaque_no_content_access"
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_HEX_ID = re.compile(r"^[0-9a-f]{40,64}$")
_PROJECTION_NAME = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_GENERIC_TEXT = frozenset({"generic", "candidate", "proposal", "effect", "change"})


class AdmissionError(ValueError):
    pass


def _exact_fields(value: object, required: set[str], context: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != required:
        raise AdmissionError(f"{context} fields are not exact")
    return value


def _text(value: object, context: str, *, specific: bool = False) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 1024:
        raise AdmissionError(f"{context} text is invalid")
    if specific and (len(value.strip()) < 8 or value.strip().lower() in _GENERIC_TEXT):
        raise AdmissionError(f"{context} text is generic")
    return value


def _digest(value: object, context: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise AdmissionError(f"{context} digest is invalid")
    return value


def _hex_identity(value: object, context: str) -> str:
    if not isinstance(value, str) or _HEX_ID.fullmatch(value) is None:
        raise AdmissionError(f"{context} identity is invalid")
    return value


def _unique_texts(value: object, context: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise AdmissionError(f"{context} must be a bounded list")
    items = [_text(item, context) for item in value]
    if len(items) != len(set(items)):
        raise AdmissionError(f"{context} contains duplicates")
    return items


def _parse_frozen_cohort(payload: object) -> dict[str, Any]:
    if not isinstance(payload, bytes):
        raise AdmissionError("cohort artifact bytes are required")

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise AdmissionError("cohort artifact contains duplicate fields")
            result[key] = value
        return result

    try:
        value = json.loads(payload.decode("utf-8"), object_pairs_hook=unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AdmissionError("cohort artifact is malformed") from exc
    if not isinstance(value, dict):
        raise AdmissionError("cohort artifact is malformed")
    return value


def _member_projection(member: object) -> dict[str, Any]:
    if not isinstance(member, dict):
        raise AdmissionError("cohort member is malformed")
    classification = member.get("classification")
    if classification == "HOLD_GAP":
        raise AdmissionError("cohort contains a HOLD_GAP member")
    if classification not in {"baseline_ready", "non_applicable-approved"}:
        raise AdmissionError("cohort member classification is unsupported")
    if classification == "baseline_ready" and any(
        field in member
        for field in ("approval_reference", "candidate_non_regression_condition")
    ):
        raise AdmissionError("baseline-ready cohort member contains forbidden fields")
    fields = [
        "project_id",
        "native_slug",
        "evaluation_slug",
        "primary_root",
        "classification",
        "reason",
        "gaps",
    ]
    if classification == "non_applicable-approved":
        fields.extend(["approval_reference", "candidate_non_regression_condition"])
    if any(field not in member for field in fields):
        raise AdmissionError("cohort member identity is incomplete")
    projection = {field: copy.deepcopy(member[field]) for field in fields}
    expected = set(fields)
    _exact_fields(projection, expected, "cohort member")
    for field in ("project_id", "native_slug", "evaluation_slug", "primary_root", "reason"):
        _text(projection[field], f"cohort member {field}")
    _unique_texts(projection["gaps"], "cohort member gaps", allow_empty=True)
    if classification == "non_applicable-approved":
        _text(projection["approval_reference"], "cohort member approval reference")
        if (
            projection["candidate_non_regression_condition"]
            != "candidate_does_not_reduce_required_membership"
        ):
            raise AdmissionError("cohort member non-regression condition is invalid")
    return projection


def _validate_cohort(
    binding: object,
    artifact_bytes: bytes,
    expected_artifact_sha256: str,
) -> None:
    cohort = _exact_fields(
        binding,
        {
            "artifact_ref",
            "artifact_sha256",
            "schema",
            "enrollment_policy_revision",
            "cutoff",
            "membership_digest",
            "members",
        },
        "cohort",
    )
    _text(cohort["artifact_ref"], "cohort artifact ref")
    if not isinstance(expected_artifact_sha256, str) or re.fullmatch(
        r"[0-9a-f]{64}", expected_artifact_sha256
    ) is None:
        raise AdmissionError("expected cohort artifact digest is invalid")
    frozen = _parse_frozen_cohort(artifact_bytes)
    actual_sha256 = hashlib.sha256(artifact_bytes).hexdigest()
    if actual_sha256 != expected_artifact_sha256:
        raise AdmissionError("cohort artifact digest does not match frozen identity")
    if cohort["artifact_sha256"] != "sha256:" + actual_sha256:
        raise AdmissionError("cohort artifact digest mismatch")
    enrollment_policy = frozen.get("enrollment_policy")
    if not isinstance(enrollment_policy, dict):
        raise AdmissionError("cohort enrollment policy is malformed")
    expected_identity = {
        "schema": frozen.get("schema"),
        "enrollment_policy_revision": enrollment_policy.get("revision"),
        "cutoff": frozen.get("cutoff"),
        "membership_digest": frozen.get("membership_digest"),
    }
    for key, expected in expected_identity.items():
        if cohort[key] != expected:
            raise AdmissionError(f"cohort {key} mismatch")
    if cohort["schema"] != "harness.l3-cohort-snapshot.v1":
        raise AdmissionError("cohort schema is unsupported")
    _digest(cohort["enrollment_policy_revision"], "cohort policy revision")
    _digest(cohort["membership_digest"], "cohort membership")
    _text(cohort["cutoff"], "cohort cutoff")
    frozen_members = frozen.get("cohort_members")
    if not isinstance(frozen_members, list):
        raise AdmissionError("cohort members are malformed")
    expected_members = [_member_projection(member) for member in frozen_members]
    supplied_members = cohort["members"]
    if not isinstance(supplied_members, list):
        raise AdmissionError("cohort members are malformed")
    for index, supplied in enumerate(supplied_members):
        expected_fields = (
            set(expected_members[index])
            if index < len(expected_members)
            else {
                "project_id",
                "native_slug",
                "evaluation_slug",
                "primary_root",
                "classification",
                "reason",
                "gaps",
            }
        )
        _exact_fields(supplied, expected_fields, "cohort member")
    identities = [
        (member["project_id"], member["native_slug"], member["primary_root"])
        for member in expected_members
    ]
    if len(identities) != len(set(identities)):
        raise AdmissionError("cohort members contain duplicate identities")
    if supplied_members != expected_members:
        raise AdmissionError("cohort members do not match the frozen cohort")


def _validate_baseline(
    baseline: object,
    expected_commit: str,
    expected_tree: str,
    expected_clean: bool,
    expected_status_digest: str,
) -> None:
    _hex_identity(expected_commit, "expected baseline commit")
    _hex_identity(expected_tree, "expected baseline tree")
    if not isinstance(expected_clean, bool):
        raise AdmissionError("expected baseline worktree clean state is invalid")
    _digest(expected_status_digest, "expected baseline worktree status")
    value = _exact_fields(baseline, {"commit", "tree", "worktree_state"}, "baseline")
    commit = _hex_identity(value["commit"], "baseline commit")
    tree = _hex_identity(value["tree"], "baseline tree")
    if commit != expected_commit or tree != expected_tree:
        raise AdmissionError("baseline identity mismatch")
    state = _exact_fields(
        value["worktree_state"], {"clean", "status_digest"}, "baseline worktree state"
    )
    if not isinstance(state["clean"], bool):
        raise AdmissionError("baseline worktree clean state is invalid")
    _digest(state["status_digest"], "baseline worktree status")
    if state["clean"] != expected_clean or state["status_digest"] != expected_status_digest:
        raise AdmissionError("baseline worktree state mismatch")


def _path_parts(ref: str, context: str) -> tuple[str, ...]:
    if ref.startswith("/") or "\\" in ref:
        raise AdmissionError(f"{context} write refs must be relative POSIX paths")
    parts = tuple(ref.split("/"))
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise AdmissionError(f"{context} write refs contain path aliases")
    return parts


def _related_path(left: str, right: str) -> bool:
    left_parts = tuple(left.split("/"))
    right_parts = tuple(right.split("/"))
    return left_parts == right_parts or left_parts == right_parts[: len(left_parts)] or right_parts == left_parts[: len(right_parts)]


def _validate_candidate(candidate: object, baseline_commit: str) -> list[str]:
    value = _exact_fields(
        candidate,
        {"identity", "baseline_commit", "allowed_write_refs", "causal_hypothesis", "target"},
        "candidate",
    )
    identity = _text(value["identity"], "candidate identity")
    if identity in {baseline_commit}:
        raise AdmissionError("candidate identity is not isolated")
    if value["baseline_commit"] != baseline_commit:
        raise AdmissionError("candidate baseline does not match")
    refs = _unique_texts(value["allowed_write_refs"], "candidate allowed write refs")
    parts = [_path_parts(ref, "candidate allowed") for ref in refs]
    for index, left in enumerate(parts):
        for right in parts[index + 1 :]:
            if left == right[: len(left)] or right == left[: len(right)]:
                raise AdmissionError("candidate allowed write refs are parent/child ambiguous")
    _text(value["causal_hypothesis"], "causal hypothesis", specific=True)
    target = _exact_fields(
        value["target"], {"c_ref", "ac_ref", "expected_ac_effect"}, "candidate target"
    )
    _text(target["c_ref"], "target C_ref")
    _text(target["ac_ref"], "target AC_ref")
    _text(target["expected_ac_effect"], "expected AC effect", specific=True)
    return refs


def _validate_evaluation(value: object) -> tuple[str, str]:
    evaluation = _exact_fields(value, {"model", "evaluator", "splits"}, "fixed evaluation")
    for name in ("model", "evaluator"):
        identity = _exact_fields(
            evaluation[name], {"identity", "configuration_digest"}, f"{name} identity"
        )
        _text(identity["identity"], f"{name} identity")
        _digest(identity["configuration_digest"], f"{name} configuration")
    splits = _exact_fields(
        evaluation["splits"],
        {
            "held_in_ref",
            "held_in_digest",
            "held_out_ref",
            "held_out_digest",
            "sampling_identity",
            "secrecy_boundary",
        },
        "evaluation splits",
    )
    for key in ("held_in_ref", "held_out_ref", "sampling_identity"):
        _text(splits[key], f"split {key}")
    for key in ("held_in_digest", "held_out_digest"):
        _digest(splits[key], f"split {key}")
    if splits["held_in_ref"] == splits["held_out_ref"] or splits["held_in_digest"] == splits["held_out_digest"]:
        raise AdmissionError("held-in and held-out identities must differ")
    if splits["secrecy_boundary"] != SECRECY_BOUNDARY:
        raise AdmissionError("held-out secrecy boundary is invalid")
    return evaluation["evaluator"]["identity"], splits["held_out_ref"]


def _validate_criteria(value: object) -> None:
    criteria = _exact_fields(
        value,
        {
            "benefit",
            "non_inferiority",
            "regression_stop",
            "uncertainty_disposition",
            "preserved_ac_refs",
        },
        "criteria",
    )
    expected = {
        "benefit": BENEFIT,
        "non_inferiority": NON_INFERIORITY,
        "regression_stop": REGRESSION_STOP,
        "uncertainty_disposition": UNCERTAINTY_DISPOSITION,
    }
    if any(criteria[key] != expected[key] for key in expected):
        raise AdmissionError("semantic criteria are not fixed")
    _unique_texts(criteria["preserved_ac_refs"], "preserved AC refs")


def _validate_controls(
    value: object,
    mutable_refs: list[str],
    evaluator_ref: str,
    held_out_ref: str,
    cohort_policy_ref: str,
) -> None:
    controls = _exact_fields(
        value,
        {
            "evaluator_ref",
            "held_out_ref",
            "permission_boundary_ref",
            "maat_disposition_ref",
            "sia_promotion_ref",
            "cohort_policy_ref",
            "execution_receipt_schema_ref",
            "additional_refs",
        },
        "immutable controls",
    )
    if controls["evaluator_ref"] != evaluator_ref:
        raise AdmissionError("immutable control evaluator mismatch")
    if controls["held_out_ref"] != held_out_ref:
        raise AdmissionError("immutable control held-out mismatch")
    if controls["cohort_policy_ref"] != cohort_policy_ref:
        raise AdmissionError("immutable control cohort policy mismatch")
    fixed_refs = []
    for key in (
        "evaluator_ref",
        "held_out_ref",
        "permission_boundary_ref",
        "maat_disposition_ref",
        "sia_promotion_ref",
        "cohort_policy_ref",
        "execution_receipt_schema_ref",
    ):
        fixed_refs.append(_text(controls[key], f"immutable control {key}"))
    fixed_refs.extend(_unique_texts(controls["additional_refs"], "additional immutable refs", allow_empty=True))
    if len(fixed_refs) != len(set(fixed_refs)):
        raise AdmissionError("immutable control refs contain duplicates")
    if any(_related_path(mutable, control) for mutable in mutable_refs for control in fixed_refs):
        raise AdmissionError("candidate mutable ref overlaps an immutable control")


def _validate_authority(value: object) -> None:
    authority = _exact_fields(
        value,
        {"confirm", "revert", "owner_hold", "learning_consideration", "learning_automatic"},
        "authority",
    )
    if authority != {
        "confirm": "Maat",
        "revert": "Maat",
        "owner_hold": "Maat",
        "learning_consideration": "SIA",
        "learning_automatic": False,
    }:
        raise AdmissionError("disposition authority is invalid")


def _validate_observability(value: object) -> None:
    budget = _exact_fields(
        value,
        {
            "allowed_projections",
            "correlation_key",
            "retention_seconds",
            "cardinality_ceiling",
            "max_dashboards",
            "max_alerts",
        },
        "observability",
    )
    projections = _unique_texts(budget["allowed_projections"], "observability projections")
    if any(_PROJECTION_NAME.fullmatch(name) is None for name in projections):
        raise AdmissionError("observability projection name is invalid")
    correlation = _exact_fields(
        budget["correlation_key"], {"name", "definition"}, "observability correlation key"
    )
    if correlation["name"] not in projections:
        raise AdmissionError("observability correlation key is not an allowed projection")
    _text(correlation["definition"], "observability correlation definition", specific=True)
    for key in ("retention_seconds", "cardinality_ceiling"):
        if isinstance(budget[key], bool) or not isinstance(budget[key], int) or budget[key] <= 0:
            raise AdmissionError(f"observability {key} must be positive and finite")
    for key in ("max_dashboards", "max_alerts"):
        if isinstance(budget[key], bool) or not isinstance(budget[key], int) or budget[key] < 0:
            raise AdmissionError(f"observability {key} must be finite and non-negative")


def serialize_admission(projection: dict) -> bytes:
    return json.dumps(
        projection, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8") + b"\n"


def compile_admission(
    admission: dict,
    *,
    cohort_artifact_bytes: bytes,
    expected_cohort_artifact_sha256: str,
    expected_baseline_commit: str,
    expected_baseline_tree: str,
    expected_baseline_clean: bool,
    expected_baseline_status_digest: str,
) -> tuple[dict, str]:
    top_fields = {
        "schema", "candidate_ref", "status", "cohort", "baseline", "candidate",
        "fixed_evaluation", "criteria", "immutable_controls", "authority", "observability",
    }
    value = _exact_fields(
        admission,
        top_fields,
        "admission",
    )
    if value["schema"] != SCHEMA:
        raise AdmissionError("admission schema is invalid")
    _text(value["candidate_ref"], "candidate ref")
    if value["status"] != "candidate-only":
        raise AdmissionError("candidate status is invalid")
    _validate_cohort(
        value["cohort"], cohort_artifact_bytes, expected_cohort_artifact_sha256
    )
    _validate_baseline(
        value["baseline"],
        expected_baseline_commit,
        expected_baseline_tree,
        expected_baseline_clean,
        expected_baseline_status_digest,
    )
    mutable_refs = _validate_candidate(value["candidate"], value["baseline"]["commit"])
    evaluator_ref, held_out_ref = _validate_evaluation(value["fixed_evaluation"])
    _validate_criteria(value["criteria"])
    _validate_controls(
        value["immutable_controls"],
        mutable_refs,
        evaluator_ref,
        held_out_ref,
        value["cohort"]["enrollment_policy_revision"],
    )
    _validate_authority(value["authority"])
    _validate_observability(value["observability"])
    projection = copy.deepcopy(value)
    canonical = serialize_admission(projection)
    return projection, "sha256:" + hashlib.sha256(canonical).hexdigest()
