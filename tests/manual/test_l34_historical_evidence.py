"""Explicit-input historical L3.4 candidate-evaluation evidence.

This module is intentionally outside the default ``tests/runtime`` suite. It never
creates, restores, copies, or refreshes historical evidence: both original paths
must be provided by the explicit manual-evidence runner.
"""

import importlib.util
import json
import os
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from harness_runtime import ReceiptValidationError, schema_text
from harness_runtime.l3_adaptation import compile_admission

_CONTRACT_PATH = Path(__file__).parents[1] / "runtime" / "test_runtime_contract.py"
_spec = importlib.util.spec_from_file_location("runtime_contract_manual_evidence_support", _CONTRACT_PATH)
assert _spec is not None and _spec.loader is not None
_contract = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_contract)

_canonical_digest = _contract._canonical_digest
_l35_source_chain = _contract._l35_source_chain
_L35_EVALUATOR_COMMAND = _contract._L35_EVALUATOR_COMMAND
_L35_OWNER_HOLDS = _contract._L35_OWNER_HOLDS
runtime_module = _contract.runtime_module

_L34_INPUTS = {
    "held_in": b"held-in-synthetic-input",
    "held_out": b"held-out-secret-body",
}
_L34_ADMISSION_PATH = Path(os.environ["HARNESS_HISTORICAL_L3_ADMISSION_PATH"])
_L34_ADMISSION_SHA256 = "b44db270a17b9fae156b441adeb23b14f627ac12cdcb7dcb12484870bda60a9b"
_L34_COHORT_PATH = Path(os.environ["HARNESS_HISTORICAL_L3_COHORT_PATH"])
_L34_COHORT_SHA256 = "0caf2513e3870db4773a9097aa9ab8fbcd74323b80fb9664ad1b8f214d4258a1"
_L34_SOURCE_REVISION_PROJECTION = {
    "baseline": {
        "revision_ref": "source-manifest:sha256:b93576cae512b43440b0a69931053f1e952bd741d019e2f4e1d18d51f14ff4db",
        "manifest": {
            "contracts/execution-receipt.v1.schema.json": "328416e427c5faa773c1f68385235b40527a65f6666cb5ee06a1410a50d9beaf",
            "runtime/harness_runtime/runtime.py": "1ee10918172770b3e5a1d22e2ef1999610f9b9ec6cb12f531b2ee1c7886a53f8",
            "tests/runtime/test_runtime_contract.py": "a0759a201354ef3628f8dd10ec83cfd89191263822abef89e2d566dcef4587d9",
        },
    },
    "candidate": {
        "revision_ref": "source-manifest:sha256:412130faed9f850cc5b6eea38c4521e30461ac38038e003af3a2a863cdd67152",
        "manifest": {
            "contracts/execution-receipt.v1.schema.json": "df4c8cc9f0e174e921b5b149b20feaf41f4ea2a3abfd4c58c0a7a512a3a44666",
            "runtime/harness_runtime/runtime.py": "81c0c2e4cf84185b7921b3d3f86e2084460d631549a5338df2849336a9a5ae4f",
            "tests/runtime/test_runtime_contract.py": "5cc8c00841249b6a85906911961c7be4400f04694bd84b32284521c171610607",
        },
    },
}


def _l34_context():
    artifact_bytes = _L34_ADMISSION_PATH.read_bytes()
    admission_source = json.loads(artifact_bytes)
    admission, admission_digest = compile_admission(
        admission_source,
        cohort_artifact_bytes=_L34_COHORT_PATH.read_bytes(),
        expected_cohort_artifact_sha256=_L34_COHORT_SHA256,
        expected_baseline_commit=admission_source["baseline"]["commit"],
        expected_baseline_tree=admission_source["baseline"]["tree"],
        expected_baseline_clean=admission_source["baseline"]["worktree_state"]["clean"],
        expected_baseline_status_digest=admission_source["baseline"]["worktree_state"]["status_digest"],
    )
    assert artifact_bytes == json.dumps(
        admission, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8") + b"\n"
    assert admission_digest == "sha256:" + _L34_ADMISSION_SHA256
    target = admission["candidate"]["target"]
    controls = admission["immutable_controls"]
    criteria = admission["criteria"]
    executor_packet = {
        "family": "executor_local_packet",
        "work_id": target["c_ref"],
        "graph_ref": "graph:G-L3",
        "local_nodes": [target["c_ref"]],
        "local_edges": [],
        "source_refs": [admission["candidate_ref"], admission_digest],
        "task_AC": [target["ac_ref"]],
        "evidence_requirements": ["direct-target-evaluator-result"],
        "allowed_write_refs": admission["candidate"]["allowed_write_refs"],
        "must_preserve": ["held-out-secrecy", "evidence-only-authority"],
        "forbidden_effects": ["activation", "disposition", "learning"],
    }
    executor_digest = _canonical_digest(executor_packet)
    projection = json.loads(json.dumps(_L34_SOURCE_REVISION_PROJECTION))
    plan = {
        "pair_ref": "pair:C-L3.4:C-L3.4-E1",
        "candidate_ref": admission["candidate_ref"],
        "c_ref": target["c_ref"],
        "graph_ref": executor_packet["graph_ref"],
        "candidate_admission_digest": admission_digest,
        "executor_packet_digest": executor_digest,
        "source_revision_projection": projection,
        "baseline_revision_ref": projection["baseline"]["revision_ref"],
        "candidate_revision_ref": projection["candidate"]["revision_ref"],
        "model_identity": admission["fixed_evaluation"]["model"]["identity"],
        "model_configuration_digest": admission["fixed_evaluation"]["model"]["configuration_digest"],
        "evaluator_identity": admission["fixed_evaluation"]["evaluator"]["identity"],
        "evaluator_configuration_digest": admission["fixed_evaluation"]["evaluator"]["configuration_digest"],
        "result_contract_ref": controls["execution_receipt_schema_ref"],
        "result_contract_digest": "sha256:928954a0f4ac84768e14b752386a6a6de2ae03fe43ac8e34d56384b941f305cb",
        "held_in_ref": admission["fixed_evaluation"]["splits"]["held_in_ref"],
        "held_in_digest": admission["fixed_evaluation"]["splits"]["held_in_digest"],
        "held_out_ref": admission["fixed_evaluation"]["splits"]["held_out_ref"],
        "held_out_digest": admission["fixed_evaluation"]["splits"]["held_out_digest"],
        "sampling_identity": admission["fixed_evaluation"]["splits"]["sampling_identity"],
        "target_ac_refs": executor_packet["task_AC"],
        "criteria": {
            "benefit": criteria["benefit"],
            "non_inferiority": criteria["non_inferiority"],
            "regression": criteria["regression_stop"],
            "uncertainty": criteria["uncertainty_disposition"],
        },
        "preserved_ac_refs": criteria["preserved_ac_refs"],
        "decision_observation": {
            "failure_evidence": {
                "ref": "pre-E1:absence-of-operational-AC14-evidence",
                "sha256": admission["fixed_evaluation"]["splits"]["held_in_digest"],
            },
            "causal_hypothesis": admission["candidate"]["causal_hypothesis"],
            "targeted_change": {
                "ref": admission["candidate"]["identity"],
                "sha256": "sha256:" + projection["candidate"]["revision_ref"].removeprefix("source-manifest:sha256:"),
            },
            "predicted_benefit": target["expected_ac_effect"],
            "at_risk_regression": criteria["non_inferiority"],
        },
        "retention_seconds": admission["observability"]["retention_seconds"],
    }
    return plan, {
        "expected_pair_plan_digest": _canonical_digest(plan),
        "candidate_admission": admission,
        "expected_candidate_admission_digest": admission_digest,
        "executor_packet": executor_packet,
        "expected_executor_packet_digest": executor_digest,
    }




def test_l34_compiled_admission_four_cell_source_observations_remain_partial_and_bound():
    plan, trusted = _l34_context()
    observations = []
    for arm, split in (
        ("baseline", "held_in"),
        ("candidate", "held_in"),
        ("baseline", "held_out"),
        ("candidate", "held_out"),
    ):
        case_id = f"l34-{arm}-{split}"
        cell = {"arm": arm, "evaluation_split": split}
        source = _l35_source_chain(
            source_case_id=f"source-{case_id}", evaluator_case_id=case_id,
            plan=plan, trusted=trusted, cell=cell,
        )
        observation = json.loads(runtime_module._construct_l35_source_observation(
            source_case_id=source["source_case_id"],
            evaluator_case_id=case_id,
            source_output=source["source_output"],
            source_dispatch_receipt=source["source_dispatch_receipt"],
            source_terminal_receipt=source["source_terminal_receipt"],
            source_readback_projection=source["source_readback_projection"],
            pair_plan=plan,
            paired_cell=cell,
            **trusted,
        ))
        assert observation["facts"] == {
            "preserved_ac": {
                "C-L3.4:AC1": True,
                "C-L3.4:AC3": True,
                "C-L3.4:AC4": True,
            }
        }
        assert observation["owner_holds"] == _L35_OWNER_HOLDS
        observations.append(observation)

    assert [item["binding"]["arm"] for item in observations] == [
        "baseline", "candidate", "baseline", "candidate"
    ]
    assert [item["binding"]["evaluation_split"] for item in observations] == [
        "held_in", "held_in", "held_out", "held_out"
    ]


@pytest.mark.parametrize(
    "mismatch",
    [
        "baseline_manifest_drift",
        "candidate_manifest_drift",
        "candidate_identity",
        "path_set",
        "criteria_mapping",
        "control_mapping",
        "projection_tampering",
        "translated_admission",
    ],
)
def test_l34_source_projection_and_source_mapping_mismatches_fail_before_launch_and_write(
    tmp_path, monkeypatch, mismatch
):
    state_dir = tmp_path / "isolated-state"
    monkeypatch.setenv("HARNESS_STATE_DIR", str(state_dir))
    plan, trusted = _l34_context()
    source_plan = json.loads(json.dumps(plan))
    source_trusted = json.loads(json.dumps(trusted))
    if mismatch == "baseline_manifest_drift":
        plan["source_revision_projection"]["baseline"]["manifest"]["runtime/harness_runtime/runtime.py"] = "0" * 64
    elif mismatch == "candidate_manifest_drift":
        plan["source_revision_projection"]["candidate"]["manifest"]["runtime/harness_runtime/runtime.py"] = "0" * 64
    elif mismatch == "candidate_identity":
        plan["source_revision_projection"]["candidate"]["revision_ref"] = (
            "source-manifest:sha256:" + "0" * 64
        )
        plan["candidate_revision_ref"] = plan["source_revision_projection"]["candidate"]["revision_ref"]
    elif mismatch == "path_set":
        plan["source_revision_projection"]["candidate"]["manifest"].pop(
            "tests/runtime/test_runtime_contract.py"
        )
    elif mismatch == "criteria_mapping":
        plan["criteria"]["regression"] = plan["criteria"]["benefit"]
    elif mismatch == "control_mapping":
        plan["result_contract_ref"] = "harness.runtime.execution-receipt.v2"
    elif mismatch == "projection_tampering":
        plan["source_revision_projection"]["baseline"]["unexpected"] = True
    else:
        translated = json.loads(json.dumps(trusted["candidate_admission"]))
        translated["baseline"] = {"revision_ref": plan["baseline_revision_ref"]}
        translated["candidate"] = {"revision_ref": plan["candidate_revision_ref"]}
        translated["fixed_evaluation"]["evaluator"].update(
            result_contract_ref=plan["result_contract_ref"],
            result_contract_digest=plan["result_contract_digest"],
        )
        translated["immutable_controls"] = {"c_ref": plan["c_ref"], "graph_ref": plan["graph_ref"]}
        translated["criteria"] = plan["criteria"]
        trusted["candidate_admission"] = translated
        trusted["expected_candidate_admission_digest"] = _canonical_digest(translated)
    trusted["expected_pair_plan_digest"] = _canonical_digest(plan)
    cell = {"arm": "baseline", "evaluation_split": "held_in"}
    source = _l35_source_chain(
        source_case_id=f"source-denial-{mismatch}",
        evaluator_case_id=f"l34-source-denial-{mismatch}",
        plan=source_plan, trusted=source_trusted, cell=cell,
    )
    calls = 0

    def unexpected_run(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("subprocess must not launch")

    monkeypatch.setattr(runtime_module.subprocess, "run", unexpected_run)
    with pytest.raises(ReceiptValidationError):
        runtime_module.execute_paired_cell(
            f"l34-source-denial-{mismatch}",
            "maat",
            source["source_output"],
            _L35_EVALUATOR_COMMAND,
            source_case_id=source["source_case_id"],
            source_dispatch_receipt=source["source_dispatch_receipt"],
            source_terminal_receipt=source["source_terminal_receipt"],
            source_readback_projection=source["source_readback_projection"],
            worktree_cwd=tmp_path / "never-read",
            pair_plan=plan,
            paired_cell=cell,
            **trusted,
        )

    assert calls == 0
    assert not state_dir.exists()


@pytest.mark.parametrize(
    "malformation",
    ["missing", "unknown", "absolute_path", "aliased_path", "uppercase_hash", "short_hash", "noncanonical_ref"],
)
def test_l34_source_projection_runtime_and_schema_shape_denial_parity(
    tmp_path, monkeypatch, malformation
):
    state_dir = tmp_path / "isolated-state"
    monkeypatch.setenv("HARNESS_STATE_DIR", str(state_dir))
    plan, trusted = _l34_context()
    source_plan = json.loads(json.dumps(plan))
    source_trusted = json.loads(json.dumps(trusted))
    projection = plan["source_revision_projection"]
    if malformation == "missing":
        projection["baseline"].pop("manifest")
    elif malformation == "unknown":
        projection["candidate"]["extra"] = True
    elif malformation == "absolute_path":
        projection["baseline"]["manifest"]["/runtime.py"] = projection["baseline"]["manifest"].pop(
            "runtime/harness_runtime/runtime.py"
        )
    elif malformation == "aliased_path":
        projection["baseline"]["manifest"]["runtime/../runtime.py"] = projection["baseline"]["manifest"].pop(
            "runtime/harness_runtime/runtime.py"
        )
    elif malformation == "uppercase_hash":
        projection["baseline"]["manifest"]["runtime/harness_runtime/runtime.py"] = "A" * 64
    elif malformation == "short_hash":
        projection["baseline"]["manifest"]["runtime/harness_runtime/runtime.py"] = "0" * 63
    else:
        projection["baseline"]["revision_ref"] = "sha256:" + "0" * 64
        plan["baseline_revision_ref"] = projection["baseline"]["revision_ref"]
    trusted["expected_pair_plan_digest"] = _canonical_digest(plan)
    cell = {"arm": "baseline", "evaluation_split": "held_in"}
    source = _l35_source_chain(
        source_case_id=f"source-shape-{malformation}",
        evaluator_case_id=f"l34-projection-shape-{malformation}",
        plan=source_plan, trusted=source_trusted, cell=cell,
    )
    schema = json.loads(schema_text())
    pair_plan_validator = Draft202012Validator({"$ref": "#/$defs/pair_plan", "$defs": schema["$defs"]})
    assert list(pair_plan_validator.iter_errors(plan))
    calls = 0

    def unexpected_run(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("subprocess must not launch")

    monkeypatch.setattr(runtime_module.subprocess, "run", unexpected_run)
    with pytest.raises(ReceiptValidationError):
        runtime_module.execute_paired_cell(
            f"l34-projection-shape-{malformation}",
            "maat",
            source["source_output"],
            _L35_EVALUATOR_COMMAND,
            source_case_id=source["source_case_id"],
            source_dispatch_receipt=source["source_dispatch_receipt"],
            source_terminal_receipt=source["source_terminal_receipt"],
            source_readback_projection=source["source_readback_projection"],
            worktree_cwd=tmp_path / "never-read",
            pair_plan=plan,
            paired_cell=cell,
            **trusted,
        )

    assert calls == 0
    assert not state_dir.exists()


@pytest.mark.parametrize(
    "field", ["causal_hypothesis", "predicted_benefit", "at_risk_regression"]
)
def test_l34_whitespace_decision_text_is_rejected_by_schema_and_runtime(
    tmp_path, monkeypatch, field
):
    state_dir = tmp_path / "isolated-state"
    monkeypatch.setenv("HARNESS_STATE_DIR", str(state_dir))
    plan, trusted = _l34_context()
    source_plan = json.loads(json.dumps(plan))
    source_trusted = json.loads(json.dumps(trusted))
    schema = json.loads(schema_text())
    pair_plan_validator = Draft202012Validator({"$ref": "#/$defs/pair_plan", "$defs": schema["$defs"]})
    assert not list(pair_plan_validator.iter_errors(plan))
    plan["decision_observation"][field] = " " * 16
    cell = {"arm": "baseline", "evaluation_split": "held_in"}
    source = _l35_source_chain(
        source_case_id=f"source-whitespace-{field}",
        evaluator_case_id=f"l34-whitespace-{field}",
        plan=source_plan, trusted=source_trusted, cell=cell,
    )
    calls = 0

    def unexpected_run(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("subprocess must not launch")

    monkeypatch.setattr(runtime_module.subprocess, "run", unexpected_run)
    with pytest.raises(
        ReceiptValidationError,
        match=rf"decision observation {field} is not falsifiable",
    ):
        runtime_module.execute_paired_cell(
            f"l34-whitespace-{field}",
            "maat",
            source["source_output"],
            _L35_EVALUATOR_COMMAND,
            source_case_id=source["source_case_id"],
            source_dispatch_receipt=source["source_dispatch_receipt"],
            source_terminal_receipt=source["source_terminal_receipt"],
            source_readback_projection=source["source_readback_projection"],
            worktree_cwd=tmp_path / "never-read",
            pair_plan=plan,
            paired_cell=cell,
            **trusted,
        )

    assert calls == 0
    assert not state_dir.exists()
    assert list(pair_plan_validator.iter_errors(plan))


@pytest.mark.parametrize(
    ("target", "mutation"),
    [
        ("plan", ("model_identity", "model:substituted")),
        ("plan", ("held_out_ref", "split:post-selected")),
        ("decision", ("predicted_benefit", "Rewritten after observation.")),
        ("cell", ("evaluation_split", "post_selected")),
        ("cell", ("extra", "forbidden")),
    ],
)
def test_l34_partial_or_mutated_trusted_inputs_fail_before_launch_and_write(
    tmp_path, monkeypatch, target, mutation
):
    state_dir = tmp_path / "isolated-state"
    monkeypatch.setenv("HARNESS_STATE_DIR", str(state_dir))
    plan, trusted = _l34_context()
    cell = {"arm": "baseline", "evaluation_split": "held_in"}
    source = _l35_source_chain(
        source_case_id="source-l34-rejected", evaluator_case_id="l34-rejected",
        plan=json.loads(json.dumps(plan)),
        trusted=json.loads(json.dumps(trusted)),
        cell=json.loads(json.dumps(cell)),
    )
    key, value = mutation
    if target == "decision":
        plan["decision_observation"][key] = value
    elif target == "plan":
        plan[key] = value
    elif target == "cell":
        cell[key] = value
    calls = 0

    def unexpected_run(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("subprocess must not launch")

    monkeypatch.setattr(runtime_module.subprocess, "run", unexpected_run)
    with pytest.raises(ReceiptValidationError, match="pair|decision|cell"):
        runtime_module.execute_paired_cell(
            "l34-rejected",
            "maat",
            source["source_output"],
            _L35_EVALUATOR_COMMAND,
            source_case_id=source["source_case_id"],
            source_dispatch_receipt=source["source_dispatch_receipt"],
            source_terminal_receipt=source["source_terminal_receipt"],
            source_readback_projection=source["source_readback_projection"],
            worktree_cwd=tmp_path / "never-read",
            pair_plan=plan,
            paired_cell=cell,
            **trusted,
        )
    assert calls == 0
    assert not state_dir.exists()


def test_l34_consumer_has_no_result_set_before_owner_holds_are_resolved(
    tmp_path, monkeypatch
):
    state_dir = tmp_path / "isolated-state"
    monkeypatch.setenv("HARNESS_STATE_DIR", str(state_dir))
    plan, trusted = _l34_context()
    readback_args = {
        "expected_consumer": "maat",
        "pair_plan": plan,
        "expected_pair_plan_digest": trusted["expected_pair_plan_digest"],
    }
    with pytest.raises(ReceiptValidationError, match="exactly four"):
        runtime_module.paired_readback([], **readback_args)
    with pytest.raises(ReceiptValidationError, match="duplicate|matrix"):
        runtime_module.paired_readback(["same"] * 4, **readback_args)
    assert not state_dir.exists()
