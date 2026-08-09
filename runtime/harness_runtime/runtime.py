from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from copy import deepcopy
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path
from typing import Any, Sequence

SCHEMA_NAME = "harness.runtime.execution-receipt.v1"
_CASE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SHA256_IDENTITY_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_SOURCE_REVISION_RE = re.compile(r"^source-manifest:sha256:[0-9a-f]{64}$")
_EXECUTION_ENVIRONMENT = {"LANG": "C", "LC_ALL": "C", "PATH": os.defpath, "TZ": "UTC"}
_EXPERIENCE_BINDING_FIELDS = {
    "candidate_ref",
    "candidate_admission_digest",
    "executor_packet_digest",
    "correlation_key_name",
    "correlation_key_value",
    "evaluation_split",
    "held_in_ref",
    "held_in_digest",
    "phase",
    "source_revision_ref",
    "retention_seconds",
}
_PAIR_PLAN_FIELDS = {
    "pair_ref",
    "candidate_ref",
    "c_ref",
    "graph_ref",
    "candidate_admission_digest",
    "executor_packet_digest",
    "source_revision_projection",
    "baseline_revision_ref",
    "candidate_revision_ref",
    "model_identity",
    "model_configuration_digest",
    "evaluator_identity",
    "evaluator_configuration_digest",
    "result_contract_ref",
    "result_contract_digest",
    "held_in_ref",
    "held_in_digest",
    "held_out_ref",
    "held_out_digest",
    "sampling_identity",
    "target_ac_refs",
    "criteria",
    "preserved_ac_refs",
    "decision_observation",
    "retention_seconds",
}
_CRITERIA = {"benefit", "non_inferiority", "regression", "uncertainty"}
_L35_DECLARATION_REF = "C-L3.5-PE2/D-CURRENT-2026-08-09"
_L35_PRODUCER_CELL_FIELDS = {
    "cell",
    "cell_identity",
    "arm",
    "source_revision_ref",
    "evaluation_split",
    "split_ref",
    "split_digest",
    "model_identity",
    "model_configuration_digest",
    "sampling_identity",
}
_L35_IDENTITY_INPUT_FIELDS = {
    "arm",
    "source_revision_ref",
    "evaluation_split",
    "split_ref",
    "split_digest",
    "model_identity",
    "model_configuration_digest",
    "sampling_identity",
}
_L35_PRODUCER_FACT_FIELDS = {"source_native_preserved_ac"}
_L35_PHASE1_PRESERVED_AC_FIELDS = {
    "C-L3.4:AC1",
    "C-L3.4:AC3",
    "C-L3.4:AC4",
}
_L35_OWNER_HOLDS = {
    **{
        f"C-L3.4:AC{number}": {
            "owner_ref": "runtime/harness_runtime/runtime.py#_construct_l35_source_observation",
            "status": "no_value_and_owner_hold",
        }
        for number in (2, 6, 9)
    },
    **{
        f"C-L3.4:AC{number}": {
            "owner_ref": "runtime/harness_runtime/runtime.py#paired_readback",
            "status": "no_value_and_owner_hold",
        }
        for number in (5, 7, 8, 10, 11)
    },
    **{
        f"C-L3.4:AC{number}": {
            "owner_ref": "independent-verifier:anubis:C-L3.4",
            "status": "no_value_and_owner_hold",
        }
        for number in (12, 13)
    },
    "C-L3.4:AC14": {
        "owner_ref": "maat:C-L3.4:AC14-direct-runtime-evaluator",
        "status": "no_value_and_owner_hold",
    },
}
_L35_SOURCE_PRODUCER_ARGV = ["source-observation-producer", "--stdin-only"]
_L35_EVALUATOR_ARGV = [
    sys.executable,
    "/Users/kann/projects/harness-starter/runtime/harness_runtime/l3_ac14_evaluator.py",
]


class ReceiptValidationError(ValueError):
    """The isolated runtime input or persisted receipt is invalid."""


class _DuplicateKeyError(ValueError):
    pass


def schema_text() -> str:
    return resources.files("contracts").joinpath("execution-receipt.v1.schema.json").read_text(encoding="utf-8")


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _canonical_line(value: object, *, ensure_ascii: bool = False) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=ensure_ascii
    ).encode("utf-8") + b"\n"


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value = {}
    for key, item in pairs:
        if key in value:
            raise _DuplicateKeyError
        value[key] = item
    return value


def _reject_constant(value: str) -> None:
    raise ValueError(value)


def _parse_exact_line(value: object, context: str, *, ensure_ascii: bool = False) -> dict[str, Any]:
    if not isinstance(value, bytes):
        raise ReceiptValidationError(f"{context} must be bytes")
    try:
        text = value.decode("utf-8", errors="strict")
        parsed = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (TypeError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReceiptValidationError(f"{context} is not exact JSON") from exc
    try:
        canonical = _canonical_line(parsed, ensure_ascii=ensure_ascii)
    except (TypeError, ValueError) as exc:
        raise ReceiptValidationError(f"{context} is not canonicalizable") from exc
    if value != canonical or not isinstance(parsed, dict):
        raise ReceiptValidationError(f"{context} is not canonical JSON bytes")
    return parsed


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _projection_digest(value: object) -> str:
    try:
        canonical = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8") + b"\n"
    except (TypeError, ValueError) as exc:
        raise ReceiptValidationError("trusted projection is not canonicalizable") from exc
    return "sha256:" + _sha256(canonical)


def _exact_mapping(value: object, fields: set[str], context: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ReceiptValidationError(f"{context} fields are not exact")
    return value


def _bounded_text(value: object, context: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 1024:
        raise ReceiptValidationError(f"{context} is invalid")
    return value


def _identity_digest(value: object, context: str) -> str:
    if not isinstance(value, str) or _SHA256_IDENTITY_RE.fullmatch(value) is None:
        raise ReceiptValidationError(f"{context} is invalid")
    return value


def _decision_text(value: object, context: str) -> str:
    text = _bounded_text(value, context)
    if len(text.strip()) < 16:
        raise ReceiptValidationError(f"{context} is not falsifiable")
    return text


def _bounded_text_list(value: object, context: str) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or len(value) > 32
        or len(set(value)) != len(value)
    ):
        raise ReceiptValidationError(f"{context} is invalid")
    for item in value:
        _bounded_text(item, context)
    return value


def _source_path(value: object, context: str) -> str:
    path = _bounded_text(value, context)
    if path.startswith("/") or "\\" in path:
        raise ReceiptValidationError(f"{context} must be a relative POSIX path")
    if any(part in {"", ".", ".."} for part in path.split("/")):
        raise ReceiptValidationError(f"{context} contains path aliases")
    return path


def _validate_source_revision_projection(value: object) -> dict[str, Any]:
    projection = _exact_mapping(value, {"baseline", "candidate"}, "source revision projection")
    path_sets = []
    for arm in ("baseline", "candidate"):
        revision = _exact_mapping(
            projection[arm], {"revision_ref", "manifest"}, f"{arm} source revision"
        )
        revision_ref = revision["revision_ref"]
        if not isinstance(revision_ref, str) or _SOURCE_REVISION_RE.fullmatch(revision_ref) is None:
            raise ReceiptValidationError(f"{arm} source revision_ref is invalid")
        manifest = revision["manifest"]
        if not isinstance(manifest, dict) or not manifest:
            raise ReceiptValidationError(f"{arm} source manifest is invalid")
        for path, digest in manifest.items():
            _source_path(path, f"{arm} source manifest path")
            if not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None:
                raise ReceiptValidationError(f"{arm} source manifest digest is invalid")
        canonical_ref = "source-manifest:" + _projection_digest(manifest)
        if revision_ref != canonical_ref:
            raise ReceiptValidationError(f"{arm} source revision_ref does not match manifest")
        path_sets.append(set(manifest))
    if path_sets[0] != path_sets[1]:
        raise ReceiptValidationError("source revision arm path sets do not match")
    return projection


def _validate_decision_observation(value: object) -> dict[str, Any]:
    observation = _exact_mapping(
        value,
        {
            "failure_evidence",
            "causal_hypothesis",
            "targeted_change",
            "predicted_benefit",
            "at_risk_regression",
        },
        "decision observation",
    )
    for field in ("failure_evidence", "targeted_change"):
        evidence = _exact_mapping(observation[field], {"ref", "sha256"}, f"decision observation {field}")
        _bounded_text(evidence["ref"], f"decision observation {field} ref")
        _identity_digest(evidence["sha256"], f"decision observation {field} sha256")
    for field in ("causal_hypothesis", "predicted_benefit", "at_risk_regression"):
        _decision_text(observation[field], f"decision observation {field}")
    return observation


def _validate_pair_plan(value: object) -> dict[str, Any]:
    plan = _exact_mapping(value, _PAIR_PLAN_FIELDS, "pair plan")
    projection = _validate_source_revision_projection(plan["source_revision_projection"])
    for field in (
        "pair_ref",
        "candidate_ref",
        "c_ref",
        "graph_ref",
        "baseline_revision_ref",
        "candidate_revision_ref",
        "model_identity",
        "evaluator_identity",
        "result_contract_ref",
        "held_in_ref",
        "held_out_ref",
        "sampling_identity",
    ):
        _bounded_text(plan[field], f"pair plan {field}")
    if (
        plan["baseline_revision_ref"] != projection["baseline"]["revision_ref"]
        or plan["candidate_revision_ref"] != projection["candidate"]["revision_ref"]
    ):
        raise ReceiptValidationError("pair plan revision refs do not match source projection")
    for field in (
        "candidate_admission_digest",
        "executor_packet_digest",
        "model_configuration_digest",
        "evaluator_configuration_digest",
        "result_contract_digest",
        "held_in_digest",
        "held_out_digest",
    ):
        _identity_digest(plan[field], f"pair plan {field}")
    _bounded_text_list(plan["target_ac_refs"], "pair plan target_ac_refs")
    _bounded_text_list(plan["preserved_ac_refs"], "pair plan preserved_ac_refs")
    criteria = _exact_mapping(plan["criteria"], _CRITERIA, "pair plan criteria")
    for name, ref in criteria.items():
        _bounded_text(ref, f"pair plan {name} criterion")
    _validate_decision_observation(plan["decision_observation"])
    retention = plan["retention_seconds"]
    if isinstance(retention, bool) or not isinstance(retention, int) or retention <= 0:
        raise ReceiptValidationError("pair plan retention_seconds is invalid")
    return plan


def _validate_admitted_pair_plan(
    pair_plan: object,
    expected_pair_plan_digest: object,
    candidate_admission: object,
    expected_candidate_admission_digest: object,
    executor_packet: object,
    expected_executor_packet_digest: object,
) -> tuple[dict[str, Any], str]:
    plan = _validate_pair_plan(pair_plan)
    plan_digest = _identity_digest(expected_pair_plan_digest, "expected pair plan digest")
    if _projection_digest(plan) != plan_digest:
        raise ReceiptValidationError("pair plan identity mismatch")
    admission_digest = _identity_digest(
        expected_candidate_admission_digest, "expected candidate admission digest"
    )
    if _projection_digest(candidate_admission) != admission_digest:
        raise ReceiptValidationError("candidate admission identity mismatch")
    admission = _exact_mapping(
        candidate_admission,
        {
            "schema",
            "candidate_ref",
            "status",
            "cohort",
            "baseline",
            "candidate",
            "fixed_evaluation",
            "criteria",
            "immutable_controls",
            "authority",
            "observability",
        },
        "candidate admission",
    )
    if admission["schema"] != "harness.l3-adaptation-candidate.v1" or admission["status"] != "candidate-only":
        raise ReceiptValidationError("candidate admission is unsupported")
    _exact_mapping(
        admission["cohort"],
        {
            "artifact_ref",
            "artifact_sha256",
            "schema",
            "enrollment_policy_revision",
            "cutoff",
            "membership_digest",
            "members",
        },
        "candidate cohort",
    )
    baseline = _exact_mapping(admission["baseline"], {"commit", "tree", "worktree_state"}, "candidate baseline")
    if any(
        not isinstance(baseline[field], str)
        or re.fullmatch(r"[0-9a-f]{40,64}", baseline[field]) is None
        for field in ("commit", "tree")
    ):
        raise ReceiptValidationError("candidate baseline Git identity is invalid")
    baseline_state = _exact_mapping(
        baseline["worktree_state"], {"clean", "status_digest"}, "candidate baseline worktree state"
    )
    if not isinstance(baseline_state["clean"], bool):
        raise ReceiptValidationError("candidate baseline worktree state is invalid")
    _identity_digest(baseline_state["status_digest"], "candidate baseline worktree status digest")
    candidate = _exact_mapping(
        admission["candidate"],
        {"identity", "baseline_commit", "allowed_write_refs", "causal_hypothesis", "target"},
        "candidate revision",
    )
    target = _exact_mapping(candidate["target"], {"c_ref", "ac_ref", "expected_ac_effect"}, "candidate target")
    for field in ("identity", "baseline_commit", "causal_hypothesis"):
        _bounded_text(candidate[field], f"candidate {field}")
    for field in ("c_ref", "ac_ref", "expected_ac_effect"):
        _bounded_text(target[field], f"candidate target {field}")
    allowed_write_refs = _bounded_text_list(candidate["allowed_write_refs"], "candidate allowed_write_refs")
    for ref in allowed_write_refs:
        _source_path(ref, "candidate allowed_write_ref")
    if candidate["baseline_commit"] != baseline["commit"]:
        raise ReceiptValidationError("candidate baseline_commit does not match baseline commit")
    evaluation = _exact_mapping(
        admission["fixed_evaluation"], {"model", "evaluator", "splits"}, "candidate fixed evaluation"
    )
    model = _exact_mapping(evaluation["model"], {"identity", "configuration_digest"}, "candidate model")
    evaluator = _exact_mapping(
        evaluation["evaluator"],
        {"identity", "configuration_digest"},
        "candidate evaluator",
    )
    splits = _exact_mapping(
        evaluation["splits"],
        {
            "held_in_ref",
            "held_in_digest",
            "held_out_ref",
            "held_out_digest",
            "sampling_identity",
            "secrecy_boundary",
        },
        "candidate evaluation splits",
    )
    criteria = _exact_mapping(
        admission["criteria"],
        {"benefit", "non_inferiority", "regression_stop", "uncertainty_disposition", "preserved_ac_refs"},
        "candidate criteria",
    )
    preserved_ac_refs = _bounded_text_list(criteria["preserved_ac_refs"], "candidate preserved_ac_refs")
    controls = _exact_mapping(
        admission["immutable_controls"],
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
        "candidate controls",
    )
    _exact_mapping(
        admission["authority"],
        {"confirm", "revert", "owner_hold", "learning_consideration", "learning_automatic"},
        "candidate authority",
    )
    observability = _exact_mapping(
        admission["observability"],
        {
            "allowed_projections",
            "correlation_key",
            "retention_seconds",
            "cardinality_ceiling",
            "max_dashboards",
            "max_alerts",
        },
        "candidate observability",
    )
    if splits["secrecy_boundary"] != "held_out_opaque_no_content_access":
        raise ReceiptValidationError("candidate held-out secrecy boundary is unsupported")
    if controls["evaluator_ref"] != evaluator["identity"] or controls["held_out_ref"] != splits["held_out_ref"]:
        raise ReceiptValidationError("candidate immutable controls do not match fixed evaluation")
    packet = _exact_mapping(
        executor_packet,
        {
            "family",
            "work_id",
            "graph_ref",
            "local_nodes",
            "local_edges",
            "source_refs",
            "task_AC",
            "evidence_requirements",
            "allowed_write_refs",
            "must_preserve",
            "forbidden_effects",
        },
        "executor packet",
    )
    packet_digest = _identity_digest(expected_executor_packet_digest, "expected executor packet digest")
    if _projection_digest(packet) != packet_digest:
        raise ReceiptValidationError("executor packet identity mismatch")
    if (
        packet["family"] != "executor_local_packet"
        or packet["work_id"] != target["c_ref"]
        or packet["local_nodes"] != [target["c_ref"]]
        or packet["source_refs"] != [admission["candidate_ref"], admission_digest]
        or packet["task_AC"] != [target["ac_ref"]]
        or packet["allowed_write_refs"] != allowed_write_refs
        or packet["task_AC"] != plan["target_ac_refs"]
    ):
        raise ReceiptValidationError("executor packet does not match pair plan")
    projection = plan["source_revision_projection"]
    if (
        set(projection["baseline"]["manifest"]) != set(allowed_write_refs)
        or set(projection["candidate"]["manifest"]) != set(allowed_write_refs)
        or projection["candidate"]["revision_ref"] != candidate["identity"]
    ):
        raise ReceiptValidationError("source revision projection does not match candidate admission")
    decision = plan["decision_observation"]
    targeted_change = decision["targeted_change"]
    if (
        decision["causal_hypothesis"] != candidate["causal_hypothesis"]
        or decision["predicted_benefit"] != target["expected_ac_effect"]
        or decision["at_risk_regression"] != criteria["non_inferiority"]
        or targeted_change["ref"] != candidate["identity"]
        or targeted_change["sha256"] != "sha256:" + candidate["identity"].removeprefix("source-manifest:sha256:")
    ):
        raise ReceiptValidationError("candidate decision observation does not match pair plan")
    expected = {
        "candidate_ref": admission["candidate_ref"],
        "c_ref": target["c_ref"],
        "graph_ref": packet["graph_ref"],
        "candidate_admission_digest": admission_digest,
        "executor_packet_digest": packet_digest,
        "baseline_revision_ref": projection["baseline"]["revision_ref"],
        "candidate_revision_ref": projection["candidate"]["revision_ref"],
        "model_identity": model["identity"],
        "model_configuration_digest": model["configuration_digest"],
        "evaluator_identity": evaluator["identity"],
        "evaluator_configuration_digest": evaluator["configuration_digest"],
        "result_contract_ref": controls["execution_receipt_schema_ref"],
        "held_in_ref": splits["held_in_ref"],
        "held_in_digest": splits["held_in_digest"],
        "held_out_ref": splits["held_out_ref"],
        "held_out_digest": splits["held_out_digest"],
        "sampling_identity": splits["sampling_identity"],
        "target_ac_refs": [target["ac_ref"]],
        "criteria": {
            "benefit": criteria["benefit"],
            "non_inferiority": criteria["non_inferiority"],
            "regression": criteria["regression_stop"],
            "uncertainty": criteria["uncertainty_disposition"],
        },
        "preserved_ac_refs": preserved_ac_refs,
        "retention_seconds": observability["retention_seconds"],
    }
    if any(plan[field] != expected[field] for field in expected):
        raise ReceiptValidationError("candidate admission does not match pair plan")
    return deepcopy(plan), plan_digest


def _pair_binding(plan: dict[str, Any], plan_digest: str, cell: object) -> dict[str, Any]:
    cell = _exact_mapping(cell, {"arm", "evaluation_split"}, "paired cell")
    arm = cell["arm"]
    split = cell["evaluation_split"]
    if arm not in {"baseline", "candidate"} or split not in {"held_in", "held_out"}:
        raise ReceiptValidationError("paired cell is unsupported")
    return {
        "pair_plan": deepcopy(plan),
        "pair_plan_digest": plan_digest,
        "decision_observation_digest": _projection_digest(plan["decision_observation"]),
        "arm": arm,
        "evaluation_split": split,
        "source_revision_ref": plan[f"{arm}_revision_ref"],
        "split_ref": plan[f"{split}_ref"],
        "split_digest": plan[f"{split}_digest"],
    }


def _l35_producer_binding(plan: dict[str, Any], plan_digest: str, cell: object) -> dict[str, Any]:
    binding = _pair_binding(plan, plan_digest, cell)
    return {
        "pair_plan_digest": plan_digest,
        "arm": binding["arm"],
        "evaluation_split": binding["evaluation_split"],
        "source_revision_ref": binding["source_revision_ref"],
        "split_ref": binding["split_ref"],
        "split_digest": binding["split_digest"],
        "model_identity": plan["model_identity"],
        "model_configuration_digest": plan["model_configuration_digest"],
    }


def _derive_l35_cell_identity(value: object) -> str:
    inputs = _exact_mapping(value, _L35_IDENTITY_INPUT_FIELDS, "L3.5 cell identity inputs")
    return "sha256:" + _sha256(_canonical_line(inputs))


def _l35_producer_cell(plan: dict[str, Any], paired_cell: object) -> dict[str, Any]:
    binding = _pair_binding(plan, _projection_digest(plan), paired_cell)
    cell_name = f"{binding['arm']}/{binding['evaluation_split']}"
    cell = {
        "cell": cell_name,
        "arm": binding["arm"],
        "source_revision_ref": binding["source_revision_ref"],
        "evaluation_split": binding["evaluation_split"],
        "split_ref": binding["split_ref"],
        "split_digest": binding["split_digest"],
        "model_identity": plan["model_identity"],
        "model_configuration_digest": plan["model_configuration_digest"],
        "sampling_identity": plan["sampling_identity"],
    }
    cell["cell_identity"] = _derive_l35_cell_identity(
        {field: cell[field] for field in _L35_IDENTITY_INPUT_FIELDS}
    )
    return cell


def _validate_l35_source_producer_result(
    value: object, expected_cell: object
) -> dict[str, Any]:
    producer = _parse_exact_line(value, "source producer result")
    producer = _exact_mapping(
        producer,
        {"schema", "declaration_ref", "cell", "facts"},
        "source producer result",
    )
    if producer["schema"] != "harness.l3-ac14-source-producer-result.v1":
        raise ReceiptValidationError("source producer result schema is unsupported")
    if producer["declaration_ref"] != _L35_DECLARATION_REF:
        raise ReceiptValidationError("source producer declaration is not sealed")
    cell = _exact_mapping(
        producer["cell"], _L35_PRODUCER_CELL_FIELDS, "source producer cell"
    )
    expected = _exact_mapping(
        expected_cell, _L35_PRODUCER_CELL_FIELDS, "expected source producer cell"
    )
    for field in ("cell_identity", "split_digest", "model_configuration_digest"):
        _identity_digest(cell[field], f"source producer cell {field}")
    identity_inputs = {field: cell[field] for field in _L35_IDENTITY_INPUT_FIELDS}
    if (
        cell["arm"] not in {"baseline", "candidate"}
        or cell["evaluation_split"] not in {"held_in", "held_out"}
        or cell["cell"] != f"{cell['arm']}/{cell['evaluation_split']}"
        or cell["cell_identity"] != _derive_l35_cell_identity(identity_inputs)
        or not isinstance(cell["source_revision_ref"], str)
        or _SOURCE_REVISION_RE.fullmatch(cell["source_revision_ref"]) is None
    ):
        raise ReceiptValidationError("source producer cell is unsupported")
    for field in ("split_ref", "model_identity", "sampling_identity"):
        _bounded_text(cell[field], f"source producer cell {field}")
    if cell != expected:
        raise ReceiptValidationError("source producer cell does not match sealed paired cell")

    facts = _exact_mapping(producer["facts"], _L35_PRODUCER_FACT_FIELDS, "source producer facts")
    preserved = _exact_mapping(
        facts["source_native_preserved_ac"],
        _L35_PHASE1_PRESERVED_AC_FIELDS,
        "source producer source_native_preserved_ac",
    )
    if any(type(item) is not bool for item in preserved.values()):
        raise ReceiptValidationError("source producer facts must be booleans")
    return deepcopy(producer)


def _validate_l35_source_receipts(
    source_case_id: str,
    source_output: bytes,
    dispatch_bytes: object,
    terminal_bytes: object,
) -> tuple[dict[str, Any], dict[str, Any]]:
    dispatch = _parse_exact_line(
        dispatch_bytes, "source dispatch receipt", ensure_ascii=True
    )
    terminal = _parse_exact_line(
        terminal_bytes, "source terminal receipt", ensure_ascii=True
    )
    dispatch_fields = {
        "schema", "sequence", "event", "status", "case_id", "consumer",
        "recorded_at", "exit_code", "artifacts",
    }
    terminal_fields = {*dispatch_fields, "execution"}
    if (
        set(dispatch) != dispatch_fields
        or dispatch.get("schema") != SCHEMA_NAME
        or dispatch.get("sequence") != 1
        or dispatch.get("event") != "dispatch"
        or dispatch.get("status") != "observed"
        or dispatch.get("case_id") != source_case_id
        or dispatch.get("exit_code") is not None
    ):
        raise ReceiptValidationError("source dispatch receipt is invalid")
    if (
        set(terminal) != terminal_fields
        or terminal.get("schema") != SCHEMA_NAME
        or terminal.get("sequence") != 2
        or terminal.get("event") != "terminal"
        or terminal.get("status") != "pass"
        or terminal.get("exit_code") != 0
        or terminal.get("case_id") != source_case_id
        or terminal.get("consumer") != dispatch.get("consumer")
    ):
        raise ReceiptValidationError("source terminal receipt is invalid")
    _bounded_text(dispatch.get("consumer"), "source receipt consumer")
    dispatch_time = _recorded_time(dispatch.get("recorded_at"))
    terminal_time = _recorded_time(terminal.get("recorded_at"))
    if terminal_time <= dispatch_time:
        raise ReceiptValidationError("source terminal receipt does not follow dispatch")
    _validate_execution(terminal["execution"])
    if terminal["execution"]["argv"] != _L35_SOURCE_PRODUCER_ARGV:
        raise ReceiptValidationError("source producer command identity is invalid")
    dispatch_artifacts = _artifact_metadata(dispatch["artifacts"])
    terminal_artifacts = _artifact_metadata(terminal["artifacts"])
    empty_sha256 = _sha256(b"")
    if (
        dispatch_artifacts["body"] != terminal_artifacts["body"]
        or any(
            dispatch_artifacts[name]["sha256"] != empty_sha256
            or dispatch_artifacts[name]["bytes"] != 0
            for name in ("stdout", "stderr")
        )
        or terminal_artifacts["stdout"]["sha256"] != _sha256(source_output)
        or terminal_artifacts["stdout"]["bytes"] != len(source_output)
    ):
        raise ReceiptValidationError("source receipt artifacts do not match producer output")
    return dispatch, terminal


def _construct_l35_source_observation(
    *,
    source_case_id: str,
    evaluator_case_id: str,
    source_output: bytes,
    source_dispatch_receipt: bytes,
    source_terminal_receipt: bytes,
    source_readback_projection: bytes,
    pair_plan: dict[str, Any],
    expected_pair_plan_digest: str,
    paired_cell: dict[str, str],
    candidate_admission: dict[str, Any],
    expected_candidate_admission_digest: str,
    executor_packet: dict[str, Any],
    expected_executor_packet_digest: str,
) -> bytes:
    if (
        not isinstance(source_case_id, str)
        or _CASE_RE.fullmatch(source_case_id) is None
        or not isinstance(evaluator_case_id, str)
        or _CASE_RE.fullmatch(evaluator_case_id) is None
        or source_case_id == evaluator_case_id
    ):
        raise ReceiptValidationError("source and evaluator case ids must be valid and distinct")
    plan, plan_digest = _validate_admitted_pair_plan(
        pair_plan,
        expected_pair_plan_digest,
        candidate_admission,
        expected_candidate_admission_digest,
        executor_packet,
        expected_executor_packet_digest,
    )
    producer_binding = _l35_producer_binding(plan, plan_digest, paired_cell)
    expected_producer_cell = _l35_producer_cell(plan, paired_cell)
    producer = _validate_l35_source_producer_result(source_output, expected_producer_cell)
    _, terminal = _validate_l35_source_receipts(
        source_case_id,
        source_output,
        source_dispatch_receipt,
        source_terminal_receipt,
    )
    observation_binding = {
        "candidate_ref": plan["candidate_ref"],
        "candidate_admission_digest": expected_candidate_admission_digest,
        **producer_binding,
        "evaluator_identity": plan["evaluator_identity"],
        "evaluator_configuration_digest": plan["evaluator_configuration_digest"],
        "result_contract_ref": plan["result_contract_ref"],
        "result_contract_digest": plan["result_contract_digest"],
        "target_ac_ref": "AC14",
    }
    readback = _parse_exact_line(
        source_readback_projection, "source fresh readback projection"
    )
    readback = _exact_mapping(
        readback,
        {
            "schema",
            "source_case_id",
            "producer_state",
            "read_at",
            "binding",
            "dispatch_receipt_sha256",
            "terminal_receipt_sha256",
            "output_sha256",
            "artifacts",
        },
        "source fresh readback projection",
    )
    expected_readback = {
        "schema": "harness.l3-ac14-source-readback-projection.v1",
        "source_case_id": source_case_id,
        "producer_state": "stopped",
        "read_at": readback["read_at"],
        "binding": observation_binding,
        "dispatch_receipt_sha256": "sha256:" + _sha256(source_dispatch_receipt),
        "terminal_receipt_sha256": "sha256:" + _sha256(source_terminal_receipt),
        "output_sha256": "sha256:" + _sha256(source_output),
        "artifacts": terminal["artifacts"],
    }
    if (
        _recorded_time(readback["read_at"]) <= _recorded_time(terminal["recorded_at"])
        or readback != expected_readback
    ):
        raise ReceiptValidationError("source fresh readback projection is stale, mixed, or substituted")
    evidence_refs = sorted(
        {
            f"pair-plan:{plan_digest}",
            f"source-observation-case:{source_case_id}",
            "source-observation-dispatch-receipt:sha256:" + _sha256(source_dispatch_receipt),
            "source-observation-terminal-receipt:sha256:" + _sha256(source_terminal_receipt),
            "source-observation-readback:sha256:" + _sha256(source_readback_projection),
            "source-observation-output:sha256:" + _sha256(source_output),
        }
    )
    producer_facts = producer["facts"]
    return _canonical_line(
        {
            "schema": "harness.l3-ac14-source-observation.v1",
            "binding": observation_binding,
            "facts": {
                "preserved_ac": producer_facts["source_native_preserved_ac"],
            },
            "owner_holds": _L35_OWNER_HOLDS,
            "evidence_refs": evidence_refs,
        }
    )


def _validate_pair_binding(value: object) -> dict[str, Any]:
    binding = _exact_mapping(
        value,
        {
            "pair_plan",
            "pair_plan_digest",
            "decision_observation_digest",
            "arm",
            "evaluation_split",
            "source_revision_ref",
            "split_ref",
            "split_digest",
        },
        "paired evaluation binding",
    )
    plan = _validate_pair_plan(binding["pair_plan"])
    plan_digest = _identity_digest(binding["pair_plan_digest"], "paired evaluation pair plan digest")
    if _projection_digest(plan) != plan_digest:
        raise ReceiptValidationError("paired evaluation pair plan identity mismatch")
    decision_digest = _identity_digest(
        binding["decision_observation_digest"], "paired evaluation decision observation digest"
    )
    if _projection_digest(plan["decision_observation"]) != decision_digest:
        raise ReceiptValidationError("paired evaluation decision observation identity mismatch")
    expected = _pair_binding(
        plan,
        plan_digest,
        {"arm": binding["arm"], "evaluation_split": binding["evaluation_split"]},
    )
    if binding != expected:
        raise ReceiptValidationError("paired evaluation binding does not match pair plan")
    return binding


def _validate_evaluator_result(value: object, plan: dict[str, Any]) -> dict[str, Any]:
    result = _exact_mapping(
        value,
        {
            "evaluator_identity",
            "evaluator_configuration_digest",
            "result_contract_ref",
            "result_contract_digest",
            "evaluation_state",
            "evaluated_phase",
            "observed_ac_values",
            "unresolved_inputs",
        },
        "evaluator result",
    )
    for field in ("evaluator_identity", "result_contract_ref"):
        _bounded_text(result[field], f"evaluator result {field}")
    for field in ("evaluator_configuration_digest", "result_contract_digest"):
        _identity_digest(result[field], f"evaluator result {field}")
    for field in (
        "evaluator_identity",
        "evaluator_configuration_digest",
        "result_contract_ref",
        "result_contract_digest",
    ):
        if result[field] != plan[field]:
            raise ReceiptValidationError("evaluator result does not match fixed evaluator contract")
    if result["evaluation_state"] != "partial_unresolved":
        raise ReceiptValidationError("evaluator result evaluation_state is unsupported")
    if result["evaluated_phase"] != "phase_1_source_observation":
        raise ReceiptValidationError("evaluator result evaluated_phase is unsupported")
    observed = _exact_mapping(
        result["observed_ac_values"],
        _L35_PHASE1_PRESERVED_AC_FIELDS,
        "evaluator result observed_ac_values",
    )
    if any(type(item) is not bool for item in observed.values()):
        raise ReceiptValidationError("evaluator result observed_ac_values must be booleans")
    unresolved_inputs = _exact_mapping(
        result["unresolved_inputs"],
        set(_L35_OWNER_HOLDS),
        "evaluator result unresolved_inputs",
    )
    for ac_ref, expected in _L35_OWNER_HOLDS.items():
        hold = _exact_mapping(
            unresolved_inputs[ac_ref],
            {"owner_ref", "status"},
            f"evaluator result unresolved input {ac_ref}",
        )
        if hold != expected:
            raise ReceiptValidationError("evaluator result unresolved input does not match owner/status")
    if set(observed) & set(unresolved_inputs):
        raise ReceiptValidationError("evaluator result fact and unresolved input overlap")
    return deepcopy(result)


def _validate_experience_binding(value: object) -> dict[str, Any]:
    binding = _exact_mapping(value, _EXPERIENCE_BINDING_FIELDS, "experience binding")
    for field in (
        "candidate_ref",
        "correlation_key_name",
        "correlation_key_value",
        "held_in_ref",
        "source_revision_ref",
    ):
        _bounded_text(binding[field], f"experience binding {field}")
    for field in ("candidate_admission_digest", "executor_packet_digest", "held_in_digest"):
        _identity_digest(binding[field], f"experience binding {field}")
    if binding["evaluation_split"] != "held_in":
        raise ReceiptValidationError("experience binding evaluation_split is unsupported")
    if binding["phase"] not in {"baseline", "candidate", "revert"}:
        raise ReceiptValidationError("experience binding phase is unsupported")
    retention = binding["retention_seconds"]
    if isinstance(retention, bool) or not isinstance(retention, int) or retention <= 0:
        raise ReceiptValidationError("experience binding retention_seconds is invalid")
    return binding


def _trusted_experience_binding(
    experience_binding: object,
    candidate_admission: object,
    expected_candidate_admission_digest: object,
    executor_packet: object,
    expected_executor_packet_digest: object,
    expected_phase: object,
    expected_source_revision_ref: object,
) -> dict[str, Any]:
    binding = _validate_experience_binding(experience_binding)
    admission = _exact_mapping(
        candidate_admission,
        {
            "schema",
            "candidate_ref",
            "status",
            "cohort",
            "baseline",
            "candidate",
            "fixed_evaluation",
            "criteria",
            "immutable_controls",
            "authority",
            "observability",
        },
        "candidate admission",
    )
    expected_admission_digest = _identity_digest(
        expected_candidate_admission_digest, "expected candidate admission digest"
    )
    if _projection_digest(admission) != expected_admission_digest:
        raise ReceiptValidationError("candidate admission identity mismatch")
    if admission["schema"] != "harness.l3-adaptation-candidate.v1" or admission["status"] != "candidate-only":
        raise ReceiptValidationError("candidate admission is unsupported")
    candidate_ref = _bounded_text(admission["candidate_ref"], "candidate admission candidate_ref")
    evaluation = _exact_mapping(
        admission["fixed_evaluation"], {"model", "evaluator", "splits"}, "candidate fixed evaluation"
    )
    splits = _exact_mapping(
        evaluation["splits"],
        {
            "held_in_ref",
            "held_in_digest",
            "held_out_ref",
            "held_out_digest",
            "sampling_identity",
            "secrecy_boundary",
        },
        "candidate evaluation splits",
    )
    observability = _exact_mapping(
        admission["observability"],
        {
            "allowed_projections",
            "correlation_key",
            "retention_seconds",
            "cardinality_ceiling",
            "max_dashboards",
            "max_alerts",
        },
        "candidate observability",
    )
    correlation = _exact_mapping(
        observability["correlation_key"], {"name", "definition"}, "candidate correlation key"
    )
    correlation_name = _bounded_text(correlation["name"], "candidate correlation key name")
    if correlation_name not in observability["allowed_projections"] or correlation_name != "candidate_ref":
        raise ReceiptValidationError("candidate correlation key is unsupported")
    retention = observability["retention_seconds"]
    if isinstance(retention, bool) or not isinstance(retention, int) or retention <= 0:
        raise ReceiptValidationError("candidate retention_seconds is invalid")

    packet = _exact_mapping(
        executor_packet,
        {
            "family",
            "work_id",
            "graph_ref",
            "local_nodes",
            "local_edges",
            "source_refs",
            "task_AC",
            "evidence_requirements",
            "allowed_write_refs",
            "must_preserve",
            "forbidden_effects",
        },
        "executor packet",
    )
    expected_packet_digest = _identity_digest(
        expected_executor_packet_digest, "expected executor packet digest"
    )
    if _projection_digest(packet) != expected_packet_digest:
        raise ReceiptValidationError("executor packet identity mismatch")
    if packet["family"] != "executor_local_packet" or not isinstance(packet["source_refs"], list):
        raise ReceiptValidationError("executor packet is unsupported")
    if candidate_ref not in packet["source_refs"] or expected_admission_digest not in packet["source_refs"]:
        raise ReceiptValidationError("executor packet candidate correlation mismatch")
    if expected_phase not in {"baseline", "candidate", "revert"}:
        raise ReceiptValidationError("expected experience binding phase is unsupported")
    source_revision_ref = _bounded_text(
        expected_source_revision_ref, "expected experience binding source_revision_ref"
    )

    expected = {
        "candidate_ref": candidate_ref,
        "candidate_admission_digest": expected_admission_digest,
        "executor_packet_digest": expected_packet_digest,
        "correlation_key_name": correlation_name,
        "correlation_key_value": candidate_ref,
        "evaluation_split": "held_in",
        "held_in_ref": splits["held_in_ref"],
        "held_in_digest": splits["held_in_digest"],
        "phase": expected_phase,
        "source_revision_ref": source_revision_ref,
        "retention_seconds": retention,
    }
    if binding != expected:
        raise ReceiptValidationError("experience binding does not match trusted projections")
    return deepcopy(binding)


def _state_root() -> Path:
    override = os.environ.get("HARNESS_STATE_DIR")
    if not override:
        raise ReceiptValidationError("HARNESS_STATE_DIR is required; implicit or live state is forbidden")
    return Path(override).expanduser().resolve()


def _case_dir(case_id: str) -> Path:
    if not isinstance(case_id, str) or not _CASE_RE.fullmatch(case_id):
        raise ReceiptValidationError("case_id must be 1-128 safe filename characters")
    return _state_root() / "receipts" / _sha256(case_id.encode("utf-8"))


def _artifact(path: Path, case_dir: Path) -> dict[str, Any]:
    content = path.read_bytes()
    return {"ref": path.relative_to(case_dir).as_posix(), "sha256": _sha256(content), "bytes": len(content)}


def _write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def _append(case_dir: Path, receipt: dict[str, Any]) -> None:
    receipt_path = case_dir / "receipts.jsonl"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    with receipt_path.open("a", encoding="utf-8") as output:
        output.write(_canonical_bytes(receipt).decode("ascii") + "\n")
        output.flush()
        os.fsync(output.fileno())
    projection = case_dir / "current.json"
    temporary = projection.with_suffix(".tmp")
    temporary.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    temporary.replace(projection)


def _receipt(
    sequence: int,
    event: str,
    status: str,
    case_id: str,
    consumer: str,
    artifacts: dict[str, Any],
    exit_code: int | None,
    execution: dict[str, Any] | None = None,
    experience_binding: dict[str, Any] | None = None,
    paired_evaluation: dict[str, Any] | None = None,
    evaluator_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "schema": SCHEMA_NAME,
        "sequence": sequence,
        "event": event,
        "status": status,
        "case_id": case_id,
        "consumer": consumer,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "exit_code": exit_code,
        "artifacts": artifacts,
    }
    if execution is not None:
        receipt["execution"] = execution
    if experience_binding is not None:
        receipt["experience_binding"] = experience_binding
    if paired_evaluation is not None:
        receipt["paired_evaluation"] = paired_evaluation
    if evaluator_result is not None:
        receipt["evaluator_result"] = evaluator_result
    return receipt


def _git(worktree: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(worktree), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=_EXECUTION_ENVIRONMENT,
    )
    if completed.returncode != 0:
        raise ReceiptValidationError("worktree_cwd must be a Git worktree with a committed HEAD")
    return completed.stdout.decode("utf-8", errors="strict").strip()


def _worktree(path: str | Path) -> tuple[Path, str, str]:
    worktree = Path(path).expanduser().resolve()
    if not worktree.is_dir():
        raise ReceiptValidationError("worktree_cwd must be an existing directory")
    root = Path(_git(worktree, "rev-parse", "--show-toplevel")).resolve()
    if root != worktree:
        raise ReceiptValidationError("worktree_cwd must be the Git worktree root")
    commit = _git(worktree, "rev-parse", "HEAD")
    tree = _git(worktree, "rev-parse", "HEAD^{tree}")
    if _git(worktree, "status", "--porcelain", "--untracked-files=all"):
        raise ReceiptValidationError("worktree_cwd must be clean")
    return worktree, commit, tree


def _execution(argv: list[str], worktree: Path, commit: str, tree: str, environment: dict[str, str]) -> dict[str, Any]:
    return {
        "argv": argv,
        "argv_sha256": _sha256(_canonical_bytes(argv)),
        "environment": environment,
        "environment_sha256": _sha256(_canonical_bytes(environment)),
        "git_commit": commit,
        "git_tree": tree,
        "worktree_cwd": str(worktree),
        "worktree_cwd_sha256": _sha256(str(worktree).encode("utf-8")),
    }


def execute(
    case_id: str,
    consumer: str,
    body: bytes,
    command: Sequence[str],
    *,
    worktree_cwd: str | Path | None = None,
    experience_binding: dict[str, Any] | None = None,
    candidate_admission: dict[str, Any] | None = None,
    expected_candidate_admission_digest: str | None = None,
    executor_packet: dict[str, Any] | None = None,
    expected_executor_packet_digest: str | None = None,
    expected_phase: str | None = None,
    expected_source_revision_ref: str | None = None,
) -> dict[str, Any]:
    """Run one command in an explicit clean worktree and persist a verifiable receipt."""
    if not isinstance(consumer, str) or not consumer:
        raise ReceiptValidationError("consumer is required")
    if not isinstance(body, bytes):
        raise ReceiptValidationError("body must be bytes")
    argv = list(command)
    if not argv or any(not isinstance(item, str) or not item for item in argv):
        raise ReceiptValidationError("command must contain non-empty strings")
    if worktree_cwd is None:
        raise ReceiptValidationError("worktree_cwd is required; implicit caller cwd is forbidden")
    experience_inputs = (
        experience_binding,
        candidate_admission,
        expected_candidate_admission_digest,
        executor_packet,
        expected_executor_packet_digest,
        expected_phase,
        expected_source_revision_ref,
    )
    if all(value is None for value in experience_inputs):
        trusted_binding = None
    elif any(value is None for value in experience_inputs):
        raise ReceiptValidationError("experience binding inputs are partial")
    else:
        trusted_binding = _trusted_experience_binding(*experience_inputs)
    worktree, commit, tree = _worktree(worktree_cwd)
    state_root = _state_root()
    if state_root == worktree or worktree in state_root.parents:
        raise ReceiptValidationError("HARNESS_STATE_DIR must be outside worktree_cwd")
    case_dir = _case_dir(case_id)
    if (case_dir / "current.json").exists():
        raise ReceiptValidationError("case_id already has a receipt; choose a new isolated case")

    artifacts_dir = case_dir / "artifacts"
    artifact_paths = {name: artifacts_dir / f"{name}.bin" for name in ("body", "stdout", "stderr")}
    _write(artifact_paths["body"], body)
    _write(artifact_paths["stdout"], b"")
    _write(artifact_paths["stderr"], b"")
    artifacts = {name: _artifact(path, case_dir) for name, path in artifact_paths.items()}
    _append(
        case_dir,
        _receipt(
            1, "dispatch", "observed", case_id, consumer, artifacts, None,
            experience_binding=trusted_binding,
        ),
    )

    environment = {**_EXECUTION_ENVIRONMENT, "HARNESS_STATE_DIR": str(state_root)}
    execution = _execution(argv, worktree, commit, tree, environment)
    try:
        completed = subprocess.run(
            argv,
            input=body,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            cwd=worktree,
            env=environment,
        )
        exit_code, stdout, stderr = completed.returncode, completed.stdout, completed.stderr
    except OSError as exc:
        exit_code, stdout, stderr = 127, b"", f"runner error: {exc.__class__.__name__}\n".encode("ascii")
    _write(artifact_paths["stdout"], stdout)
    _write(artifact_paths["stderr"], stderr)
    artifacts = {name: _artifact(path, case_dir) for name, path in artifact_paths.items()}
    terminal = _receipt(
        2,
        "terminal",
        "pass" if exit_code == 0 else "fail",
        case_id,
        consumer,
        artifacts,
        exit_code,
        execution,
        trusted_binding,
    )
    _append(case_dir, terminal)
    verified, _ = _readback(case_id, consumer)
    return verified["receipt"]


def execute_paired_cell(
    case_id: str,
    consumer: str,
    source_output: bytes,
    command: Sequence[str],
    *,
    source_case_id: str,
    source_dispatch_receipt: bytes,
    source_terminal_receipt: bytes,
    source_readback_projection: bytes,
    worktree_cwd: str | Path,
    pair_plan: dict[str, Any],
    expected_pair_plan_digest: str,
    paired_cell: dict[str, str],
    candidate_admission: dict[str, Any],
    expected_candidate_admission_digest: str,
    executor_packet: dict[str, Any],
    expected_executor_packet_digest: str,
) -> dict[str, Any]:
    """Validate one prebound cell and launch its fixed evaluator."""
    if not isinstance(consumer, str) or not consumer:
        raise ReceiptValidationError("consumer is required")
    argv = list(command)
    if argv != _L35_EVALUATOR_ARGV:
        raise ReceiptValidationError("evaluator command identity is invalid")
    source_observation = _construct_l35_source_observation(
        source_case_id=source_case_id,
        evaluator_case_id=case_id,
        source_output=source_output,
        source_dispatch_receipt=source_dispatch_receipt,
        source_terminal_receipt=source_terminal_receipt,
        source_readback_projection=source_readback_projection,
        pair_plan=pair_plan,
        expected_pair_plan_digest=expected_pair_plan_digest,
        paired_cell=paired_cell,
        candidate_admission=candidate_admission,
        expected_candidate_admission_digest=expected_candidate_admission_digest,
        executor_packet=executor_packet,
        expected_executor_packet_digest=expected_executor_packet_digest,
    )
    plan, plan_digest = _validate_admitted_pair_plan(
        pair_plan,
        expected_pair_plan_digest,
        candidate_admission,
        expected_candidate_admission_digest,
        executor_packet,
        expected_executor_packet_digest,
    )
    binding = _pair_binding(plan, plan_digest, paired_cell)
    worktree, commit, tree = _worktree(worktree_cwd)
    state_root = _state_root()
    if state_root == worktree or worktree in state_root.parents:
        raise ReceiptValidationError("HARNESS_STATE_DIR must be outside worktree_cwd")
    case_dir = _case_dir(case_id)
    if (case_dir / "current.json").exists():
        raise ReceiptValidationError("case_id already has a receipt; choose a new isolated case")

    artifacts_dir = case_dir / "artifacts"
    artifact_paths = {name: artifacts_dir / f"{name}.bin" for name in ("body", "stdout", "stderr")}
    _write(artifact_paths["body"], source_observation)
    _write(artifact_paths["stdout"], b"")
    _write(artifact_paths["stderr"], b"")
    artifacts = {name: _artifact(path, case_dir) for name, path in artifact_paths.items()}
    _append(
        case_dir,
        _receipt(
            1,
            "dispatch",
            "observed",
            case_id,
            consumer,
            artifacts,
            None,
            paired_evaluation=binding,
        ),
    )

    environment = {**_EXECUTION_ENVIRONMENT, "HARNESS_STATE_DIR": str(state_root)}
    execution = _execution(argv, worktree, commit, tree, environment)
    try:
        completed = subprocess.run(
            argv,
            input=source_observation,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            cwd=worktree,
            env=environment,
        )
        exit_code, stdout, stderr = completed.returncode, completed.stdout, completed.stderr
    except OSError as exc:
        exit_code, stdout, stderr = 127, b"", f"runner error: {exc.__class__.__name__}\n".encode("ascii")
    _write(artifact_paths["stdout"], stdout)
    _write(artifact_paths["stderr"], stderr)
    artifacts = {name: _artifact(path, case_dir) for name, path in artifact_paths.items()}
    evaluator_result = None
    if exit_code == 0:
        if len(stdout) > 65536:
            raise ReceiptValidationError("evaluator result exceeds bounded output contract")
        evaluator_result = _validate_evaluator_result(
            _parse_exact_line(stdout, "evaluator result"), plan
        )
    terminal = _receipt(
        2,
        "terminal",
        "pass" if exit_code == 0 else "fail",
        case_id,
        consumer,
        artifacts,
        exit_code,
        execution,
        paired_evaluation=binding,
        evaluator_result=evaluator_result,
    )
    _append(case_dir, terminal)
    verified, _ = _readback(case_id, consumer)
    return verified["receipt"]


def _validate_execution(execution: object) -> None:
    if not isinstance(execution, dict):
        raise ReceiptValidationError("execution metadata is required for consumer readback")
    argv = execution.get("argv")
    environment = execution.get("environment")
    if not isinstance(argv, list) or not argv or any(not isinstance(item, str) or not item for item in argv):
        raise ReceiptValidationError("receipt argv is invalid")
    if execution.get("argv_sha256") != _sha256(_canonical_bytes(argv)):
        raise ReceiptValidationError("receipt argv digest does not match")
    if not isinstance(environment, dict) or environment != {**_EXECUTION_ENVIRONMENT, "HARNESS_STATE_DIR": environment.get("HARNESS_STATE_DIR")}:
        raise ReceiptValidationError("receipt environment is not constrained")
    if not isinstance(environment.get("HARNESS_STATE_DIR"), str):
        raise ReceiptValidationError("receipt environment is not constrained")
    if execution.get("environment_sha256") != _sha256(_canonical_bytes(environment)):
        raise ReceiptValidationError("receipt environment digest does not match")
    worktree_cwd = execution.get("worktree_cwd")
    if not isinstance(worktree_cwd, str) or execution.get("worktree_cwd_sha256") != _sha256(worktree_cwd.encode("utf-8")):
        raise ReceiptValidationError("receipt worktree cwd digest does not match")
    if not all(isinstance(execution.get(name), str) and re.fullmatch(r"[0-9a-f]{40,64}", execution[name]) for name in ("git_commit", "git_tree")):
        raise ReceiptValidationError("receipt Git identity is invalid")


def _artifact_metadata(artifacts: object) -> dict[str, dict[str, Any]]:
    if not isinstance(artifacts, dict) or set(artifacts) != {"body", "stdout", "stderr"}:
        raise ReceiptValidationError("receipt artifacts are invalid")
    for name in ("body", "stdout", "stderr"):
        item = artifacts[name]
        if (
            not isinstance(item, dict)
            or set(item) != {"ref", "sha256", "bytes"}
            or item.get("ref") != f"artifacts/{name}.bin"
            or not isinstance(item.get("sha256"), str)
            or _SHA256_RE.fullmatch(item["sha256"]) is None
            or isinstance(item.get("bytes"), bool)
            or not isinstance(item.get("bytes"), int)
            or item["bytes"] < 0
        ):
            raise ReceiptValidationError("receipt artifacts are invalid")
    return artifacts


def _verified_artifacts(case_dir: Path, artifacts: object) -> dict[str, bytes]:
    metadata = _artifact_metadata(artifacts)
    contents: dict[str, bytes] = {}
    for name in ("body", "stdout", "stderr"):
        item = metadata[name]
        artifact_path = (case_dir / item["ref"]).resolve()
        if case_dir not in artifact_path.parents:
            raise ReceiptValidationError("artifact escapes isolated state")
        try:
            content = artifact_path.read_bytes()
        except OSError as exc:
            raise ReceiptValidationError("artifact readback is unavailable") from exc
        if item.get("sha256") != _sha256(content) or item.get("bytes") != len(content):
            raise ReceiptValidationError("artifact readback does not match receipt")
        contents[name] = content
    return contents


def _read_time(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ReceiptValidationError("read_at must be a timezone-aware datetime")
    return value.astimezone(timezone.utc)


def _recorded_time(value: object) -> datetime:
    if not isinstance(value, str):
        raise ReceiptValidationError("receipt recorded_at is invalid")
    try:
        recorded = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ReceiptValidationError("receipt recorded_at is invalid") from exc
    if recorded.tzinfo is None or recorded.utcoffset() is None:
        raise ReceiptValidationError("receipt recorded_at is invalid")
    return recorded.astimezone(timezone.utc)


def _remove_raw_artifacts(case_dir: Path, artifacts: dict[str, dict[str, Any]]) -> None:
    for name in ("body", "stdout", "stderr"):
        path = (case_dir / artifacts[name]["ref"]).resolve()
        if case_dir not in path.parents:
            raise ReceiptValidationError("artifact escapes isolated state")
        for target in (path, path.with_suffix(path.suffix + ".tmp")):
            try:
                target.unlink()
            except FileNotFoundError:
                pass
    artifacts_dir = case_dir / "artifacts"
    try:
        artifacts_dir.rmdir()
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise ReceiptValidationError("expired artifact cleanup is incomplete") from exc


def _readback(
    case_id: str,
    expected_consumer: str | None,
    *,
    expected_experience_binding: dict[str, Any] | None = None,
    read_at: datetime | None = None,
    require_artifacts: bool = True,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    case_dir = _case_dir(case_id)
    path = case_dir / "current.json"
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        journal = [json.loads(line) for line in (case_dir / "receipts.jsonl").read_text(encoding="utf-8").splitlines()]
    except (OSError, json.JSONDecodeError) as exc:
        raise ReceiptValidationError("receipt readback is unavailable") from exc
    if len(journal) != 2 or journal[-1] != receipt:
        raise ReceiptValidationError("receipt journal does not match terminal projection")
    dispatch = journal[0]
    dispatch_fields = {
        "schema", "sequence", "event", "status", "case_id", "consumer",
        "recorded_at", "exit_code", "artifacts",
    }
    has_binding = "experience_binding" in dispatch or "experience_binding" in receipt
    has_pair = "paired_evaluation" in dispatch or "paired_evaluation" in receipt
    if has_binding and has_pair:
        raise ReceiptValidationError("receipt binding families cannot be combined")
    if has_binding:
        dispatch_fields.add("experience_binding")
    if has_pair:
        dispatch_fields.add("paired_evaluation")
    if (
        set(dispatch) != dispatch_fields
        or dispatch.get("schema") != SCHEMA_NAME
        or dispatch.get("sequence") != 1
        or dispatch.get("event") != "dispatch"
        or dispatch.get("status") != "observed"
        or dispatch.get("case_id") != case_id
        or dispatch.get("consumer") != receipt.get("consumer")
        or dispatch.get("exit_code") is not None
        or "execution" in dispatch
    ):
        raise ReceiptValidationError("dispatch receipt is invalid")
    required = {"schema", "sequence", "event", "status", "case_id", "consumer", "recorded_at", "exit_code", "artifacts", "execution"}
    if has_binding:
        required.add("experience_binding")
    if has_pair:
        required.add("paired_evaluation")
        if receipt.get("status") == "pass":
            required.add("evaluator_result")
    if set(receipt) != required or receipt.get("schema") != SCHEMA_NAME or receipt.get("sequence") != 2 or receipt.get("event") != "terminal":
        raise ReceiptValidationError("terminal receipt is invalid")
    if (
        receipt.get("case_id") != case_id
        or receipt.get("status") not in {"pass", "fail"}
        or not isinstance(receipt.get("exit_code"), int)
        or (receipt["status"] == "pass") != (receipt["exit_code"] == 0)
    ):
        raise ReceiptValidationError("terminal receipt is invalid")
    if expected_consumer is not None and receipt.get("consumer") != expected_consumer:
        raise ReceiptValidationError("consumer does not match receipt")
    _recorded_time(receipt.get("recorded_at"))
    _validate_execution(receipt["execution"])
    terminal_artifacts = _artifact_metadata(receipt["artifacts"])
    dispatch_artifacts = _artifact_metadata(dispatch["artifacts"])
    empty_sha256 = _sha256(b"")
    if (
        dispatch_artifacts["body"] != terminal_artifacts["body"]
        or any(
            dispatch_artifacts[name]["sha256"] != empty_sha256
            or dispatch_artifacts[name]["bytes"] != 0
            for name in ("stdout", "stderr")
        )
    ):
        raise ReceiptValidationError("dispatch artifact metadata is invalid")

    binding = None
    pair_binding = None
    expired = False
    if has_binding:
        if dispatch.get("experience_binding") != receipt.get("experience_binding"):
            raise ReceiptValidationError("experience binding changed between dispatch and terminal")
        binding = _validate_experience_binding(receipt["experience_binding"])
        if expected_experience_binding is not None:
            expected = _validate_experience_binding(expected_experience_binding)
            if binding != expected:
                raise ReceiptValidationError("experience binding does not match consumer expectation")
        expires_at = _recorded_time(dispatch.get("recorded_at")).timestamp() + binding["retention_seconds"]
        expired = _read_time(read_at).timestamp() >= expires_at
    elif expected_experience_binding is not None:
        raise ReceiptValidationError("expected experience binding is missing")
    if has_pair:
        if dispatch.get("paired_evaluation") != receipt.get("paired_evaluation"):
            raise ReceiptValidationError("paired evaluation changed between dispatch and terminal")
        pair_binding = _validate_pair_binding(receipt["paired_evaluation"])
        if receipt["status"] == "pass":
            _validate_evaluator_result(receipt["evaluator_result"], pair_binding["pair_plan"])
        expires_at = (
            _recorded_time(dispatch.get("recorded_at")).timestamp()
            + pair_binding["pair_plan"]["retention_seconds"]
        )
        expired = _read_time(read_at).timestamp() >= expires_at

    if expired:
        _remove_raw_artifacts(case_dir, terminal_artifacts)
        contents = {}
    else:
        contents = _verified_artifacts(case_dir, terminal_artifacts)
        if pair_binding is not None and receipt["status"] == "pass":
            direct_result = _parse_exact_line(
                contents["stdout"], "evaluator result artifact"
            )
            if direct_result != receipt["evaluator_result"]:
                raise ReceiptValidationError("evaluator result does not match direct target artifact")
    result = {
        "analysis_basis": SCHEMA_NAME,
        "consumer": receipt["consumer"],
        "receipt": receipt,
        "artifacts": receipt["artifacts"],
        "receipt_path": str(path),
    }
    if binding is not None or pair_binding is not None:
        result["raw_artifacts_available"] = not expired
    if expired and require_artifacts:
        raise ReceiptValidationError("raw artifact retention has expired")
    return result, contents


def readback(
    case_id: str,
    expected_consumer: str | None = None,
    *,
    expected_experience_binding: dict[str, Any] | None = None,
    read_at: datetime | None = None,
) -> dict[str, Any]:
    result, _ = _readback(
        case_id,
        expected_consumer,
        expected_experience_binding=expected_experience_binding,
        read_at=read_at,
        require_artifacts=False,
    )
    return result


def paired_readback(
    case_ids: Sequence[str],
    *,
    expected_consumer: str,
    pair_plan: dict[str, Any],
    expected_pair_plan_digest: str,
) -> dict[str, Any]:
    """Verify one complete fixed matrix and project factual candidate-minus-baseline deltas."""
    case_ids = list(case_ids)
    if len(case_ids) != 4:
        raise ReceiptValidationError("paired readback requires exactly four terminal receipts")
    if len(set(case_ids)) != 4:
        raise ReceiptValidationError("paired readback contains duplicate case ids")
    plan = _validate_pair_plan(pair_plan)
    plan_digest = _identity_digest(expected_pair_plan_digest, "expected pair plan digest")
    if _projection_digest(plan) != plan_digest:
        raise ReceiptValidationError("pair plan identity mismatch")

    cells: dict[tuple[str, str], dict[str, Any]] = {}
    for case_id in case_ids:
        verified, _ = _readback(case_id, expected_consumer, require_artifacts=False)
        receipt = verified["receipt"]
        if receipt["status"] != "pass" or receipt["exit_code"] != 0:
            raise ReceiptValidationError("paired readback requires successful terminal evaluator receipts")
        binding = _validate_pair_binding(receipt.get("paired_evaluation"))
        if binding["pair_plan"] != plan or binding["pair_plan_digest"] != plan_digest:
            raise ReceiptValidationError("paired readback contains mixed pair plans")
        result = _validate_evaluator_result(receipt.get("evaluator_result"), plan)
        key = (binding["arm"], binding["evaluation_split"])
        if key in cells:
            raise ReceiptValidationError("paired readback contains a duplicate matrix cell")
        cells[key] = {
            "case_id": case_id,
            "artifacts": deepcopy(receipt["artifacts"]),
            "evaluator_result": result,
            "terminal_receipt_sha256": "sha256:" + _sha256(_canonical_bytes(receipt)),
        }
    expected_cells = {
        ("baseline", "held_in"),
        ("candidate", "held_in"),
        ("baseline", "held_out"),
        ("candidate", "held_out"),
    }
    if set(cells) != expected_cells:
        raise ReceiptValidationError("paired readback matrix is incomplete or substituted")

    order = [
        ("baseline", "held_in"),
        ("candidate", "held_in"),
        ("baseline", "held_out"),
        ("candidate", "held_out"),
    ]
    labels = [f"{arm}-{split}" for arm, split in order]
    projected_cells = {label: cells[key] for label, key in zip(labels, order)}
    if any(
        cell["evaluator_result"]["evaluation_state"] == "partial_unresolved"
        for cell in cells.values()
    ):
        raise ReceiptValidationError(
            "final aggregation unavailable for partial_unresolved evaluator results"
        )
    observed_deltas: dict[str, Any] = {}
    for split in ("held_in", "held_out"):
        baseline = cells[("baseline", split)]["evaluator_result"]
        candidate = cells[("candidate", split)]["evaluator_result"]
        observed_deltas[split] = {
            field: {
                name: candidate[field][name] - baseline[field][name]
                for name in baseline[field]
            }
            for field in ("target_ac_values", "criteria_values")
        }
    return {
        "analysis_basis": SCHEMA_NAME,
        "pair_plan_digest": plan_digest,
        "decision_observation_digest": _projection_digest(plan["decision_observation"]),
        "cell_order": labels,
        "cells": projected_cells,
        "terminal_receipt_sha256": {
            label: projected_cells[label]["terminal_receipt_sha256"] for label in labels
        },
        "criteria": deepcopy(plan["criteria"]),
        "preserved_ac_refs": deepcopy(plan["preserved_ac_refs"]),
        "observed_deltas": observed_deltas,
    }


def analysis_input(
    case_id: str,
    expected_consumer: str | None = "anubis",
    output_limit: int = 16384,
    *,
    expected_experience_binding: dict[str, Any] | None = None,
    read_at: datetime | None = None,
) -> dict[str, Any]:
    """Return a verified receipt and bounded output for Anubis analysis."""
    if not isinstance(output_limit, int) or isinstance(output_limit, bool) or output_limit < 0:
        raise ReceiptValidationError("output_limit must be a non-negative integer")
    result, contents = _readback(
        case_id,
        expected_consumer,
        expected_experience_binding=expected_experience_binding,
        read_at=read_at,
    )
    outputs = {
        name: {
            "text": contents[name][:output_limit].decode("utf-8", errors="replace"),
            "truncated": len(contents[name]) > output_limit,
        }
        for name in ("stdout", "stderr")
    }
    return {**result, "outputs": outputs}
