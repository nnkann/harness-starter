import hashlib
import inspect
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from harness_runtime import ReceiptValidationError, __version__, analysis_input, execute, readback, schema_text
import harness_runtime.runtime as runtime_module
from harness_runtime.cli import main as cli_main
from harness_runtime.l3_adaptation import compile_admission


def _clean_git_worktree(path: Path) -> Path:
    path.mkdir()
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    (path / ".gitignore").write_text(".harness-state\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", ".gitignore"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(path),
            "-c",
            "user.name=Harness Test",
            "-c",
            "user.email=harness@example.invalid",
            "commit",
            "-qm",
            "initial",
        ],
        check=True,
    )
    return path


def _canonical_digest(value: object) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode() + b"\n"
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def _l3_context(retention_seconds: int = 60):
    admission = {
        "schema": "harness.l3-adaptation-candidate.v1",
        "candidate_ref": "C-L3.1:manual-candidate-001",
        "status": "candidate-only",
        "cohort": {},
        "baseline": {},
        "candidate": {},
        "fixed_evaluation": {
            "model": {},
            "evaluator": {},
            "splits": {
                "held_in_ref": "split:held-in-v1",
                "held_in_digest": "sha256:" + "4" * 64,
                "held_out_ref": "split:held-out-v1",
                "held_out_digest": "sha256:" + "5" * 64,
                "sampling_identity": "sampling:fixed-v1",
                "secrecy_boundary": "held_out_opaque_no_content_access",
            },
        },
        "criteria": {},
        "immutable_controls": {},
        "authority": {},
        "observability": {
            "allowed_projections": ["candidate_ref"],
            "correlation_key": {
                "name": "candidate_ref",
                "definition": "Exact admitted candidate reference.",
            },
            "retention_seconds": retention_seconds,
            "cardinality_ceiling": 1,
            "max_dashboards": 0,
            "max_alerts": 0,
        },
    }
    admission_digest = _canonical_digest(admission)
    executor_packet = {
        "family": "executor_local_packet",
        "work_id": "C-L3.3",
        "graph_ref": "graph:C-L3",
        "local_nodes": ["C-L3.3"],
        "local_edges": [],
        "source_refs": [admission["candidate_ref"], admission_digest],
        "task_AC": ["AC1"],
        "evidence_requirements": ["execution-receipt"],
        "allowed_write_refs": ["runtime/target.py"],
        "must_preserve": ["held-out"],
        "forbidden_effects": ["held-out-access"],
    }
    executor_digest = _canonical_digest(executor_packet)
    binding = {
        "candidate_ref": admission["candidate_ref"],
        "candidate_admission_digest": admission_digest,
        "executor_packet_digest": executor_digest,
        "correlation_key_name": "candidate_ref",
        "correlation_key_value": admission["candidate_ref"],
        "evaluation_split": "held_in",
        "held_in_ref": "split:held-in-v1",
        "held_in_digest": "sha256:" + "4" * 64,
        "phase": "candidate",
        "source_revision_ref": "source:candidate-revision-001",
        "retention_seconds": retention_seconds,
    }
    trusted = {
        "candidate_admission": admission,
        "expected_candidate_admission_digest": admission_digest,
        "executor_packet": executor_packet,
        "expected_executor_packet_digest": executor_digest,
        "expected_phase": "candidate",
        "expected_source_revision_ref": "source:candidate-revision-001",
    }
    return binding, trusted


_L34_INPUTS = {
    "held_in": b"held-in-synthetic-input",
    "held_out": b"held-out-secret-body",
}
_L34_ADMISSION_PATH = Path("/tmp/maat-c-l3-4-e1-admitted-candidate.json")
_L34_ADMISSION_SHA256 = "b44db270a17b9fae156b441adeb23b14f627ac12cdcb7dcb12484870bda60a9b"
_L34_COHORT_PATH = Path("/tmp/c-l3-0b-r3-live-cohort-candidate.json")
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


_L35_PRESERVED_AC_REFS = [
    f"C-L3.4:AC{number}" for number in range(1, 14)
]
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
_L35_IDENTITY_INPUT_FIELDS = (
    "arm",
    "source_revision_ref",
    "evaluation_split",
    "split_ref",
    "split_digest",
    "model_identity",
    "model_configuration_digest",
    "sampling_identity",
)


def _l35_cell_identity(cell: dict) -> str:
    inputs = {field: cell[field] for field in _L35_IDENTITY_INPUT_FIELDS}
    return "sha256:" + hashlib.sha256(_canonical_line(inputs)).hexdigest()


def _l35_context():
    source_paths = {
        "runtime/harness_runtime/runtime.py": "1" * 64,
        "tests/runtime/test_runtime_contract.py": "2" * 64,
    }
    candidate_paths = {
        "runtime/harness_runtime/runtime.py": "3" * 64,
        "tests/runtime/test_runtime_contract.py": "4" * 64,
    }
    baseline_ref = "source-manifest:" + _canonical_digest(source_paths)
    candidate_ref = "source-manifest:" + _canonical_digest(candidate_paths)
    admission = {
        "schema": "harness.l3-adaptation-candidate.v1",
        "candidate_ref": "candidate:C-L3.5-runtime-constructor",
        "status": "candidate-only",
        "cohort": {
            "artifact_ref": "cohort:bounded-test",
            "artifact_sha256": "sha256:" + "5" * 64,
            "schema": "harness.l3-cohort-snapshot.v1",
            "enrollment_policy_revision": "policy:test",
            "cutoff": "2026-08-08T00:00:00+00:00",
            "membership_digest": "sha256:" + "6" * 64,
            "members": [],
        },
        "baseline": {
            "commit": "7" * 40,
            "tree": "8" * 40,
            "worktree_state": {"clean": True, "status_digest": "sha256:" + "9" * 64},
        },
        "candidate": {
            "identity": candidate_ref,
            "baseline_commit": "7" * 40,
            "allowed_write_refs": sorted(source_paths),
            "causal_hypothesis": "Verified antecedent evidence removes the temporal cycle.",
            "target": {
                "c_ref": "C-L3.4",
                "ac_ref": "AC14",
                "expected_ac_effect": "Construct direct runtime evidence before evaluator launch.",
            },
        },
        "fixed_evaluation": {
            "model": {
                "identity": "model:fixed-v1",
                "configuration_digest": "sha256:" + "a" * 64,
            },
            "evaluator": {
                "identity": "maat:C-L3.4:AC14-direct-runtime-evaluator",
                "configuration_digest": "sha256:5da3457d462cdfe75b792ed4b48dea7d872eae9ce66aba894b38442bfcb83994",
            },
            "splits": {
                "held_in_ref": "split:held-in-v1",
                "held_in_digest": "sha256:" + "b" * 64,
                "held_out_ref": "split:held-out-v1",
                "held_out_digest": "sha256:" + "c" * 64,
                "sampling_identity": "sampling:fixed-v1",
                "secrecy_boundary": "held_out_opaque_no_content_access",
            },
        },
        "criteria": {
            "benefit": "criterion:benefit",
            "non_inferiority": "criterion:non-inferiority",
            "regression_stop": "criterion:regression",
            "uncertainty_disposition": "criterion:uncertainty",
            "preserved_ac_refs": _L35_PRESERVED_AC_REFS,
        },
        "immutable_controls": {
            "evaluator_ref": "maat:C-L3.4:AC14-direct-runtime-evaluator",
            "held_out_ref": "split:held-out-v1",
            "permission_boundary_ref": "boundary:test",
            "maat_disposition_ref": "maat:test",
            "sia_promotion_ref": "sia:test",
            "cohort_policy_ref": "cohort:test",
            "execution_receipt_schema_ref": "harness.runtime.execution-receipt.v1",
            "additional_refs": [],
        },
        "authority": {
            "confirm": "maat",
            "revert": "maat",
            "owner_hold": "owner",
            "learning_consideration": "sia",
            "learning_automatic": False,
        },
        "observability": {
            "allowed_projections": ["candidate_ref"],
            "correlation_key": {
                "name": "candidate_ref",
                "definition": "Exact admitted candidate reference.",
            },
            "retention_seconds": 3600,
            "cardinality_ceiling": 4,
            "max_dashboards": 0,
            "max_alerts": 0,
        },
    }
    admission_digest = _canonical_digest(admission)
    executor_packet = {
        "family": "executor_local_packet",
        "work_id": "C-L3.4",
        "graph_ref": "graph:G-L3",
        "local_nodes": ["C-L3.4"],
        "local_edges": [],
        "source_refs": [admission["candidate_ref"], admission_digest],
        "task_AC": ["AC14"],
        "evidence_requirements": ["direct-target-evaluator-result"],
        "allowed_write_refs": sorted(source_paths),
        "must_preserve": ["held-out-secrecy"],
        "forbidden_effects": ["disposition"],
    }
    executor_digest = _canonical_digest(executor_packet)
    plan = {
        "pair_ref": "pair:C-L3.4:C-L3.4-E1",
        "candidate_ref": admission["candidate_ref"],
        "c_ref": "C-L3.4",
        "graph_ref": "graph:G-L3",
        "candidate_admission_digest": admission_digest,
        "executor_packet_digest": executor_digest,
        "source_revision_projection": {
            "baseline": {"revision_ref": baseline_ref, "manifest": source_paths},
            "candidate": {"revision_ref": candidate_ref, "manifest": candidate_paths},
        },
        "baseline_revision_ref": baseline_ref,
        "candidate_revision_ref": candidate_ref,
        "model_identity": "model:fixed-v1",
        "model_configuration_digest": "sha256:" + "a" * 64,
        "evaluator_identity": "maat:C-L3.4:AC14-direct-runtime-evaluator",
        "evaluator_configuration_digest": "sha256:5da3457d462cdfe75b792ed4b48dea7d872eae9ce66aba894b38442bfcb83994",
        "result_contract_ref": "harness.runtime.execution-receipt.v1",
        "result_contract_digest": "sha256:928954a0f4ac84768e14b752386a6a6de2ae03fe43ac8e34d56384b941f305cb",
        "held_in_ref": "split:held-in-v1",
        "held_in_digest": "sha256:" + "b" * 64,
        "held_out_ref": "split:held-out-v1",
        "held_out_digest": "sha256:" + "c" * 64,
        "sampling_identity": "sampling:fixed-v1",
        "target_ac_refs": ["AC14"],
        "criteria": {
            "benefit": "criterion:benefit",
            "non_inferiority": "criterion:non-inferiority",
            "regression": "criterion:regression",
            "uncertainty": "criterion:uncertainty",
        },
        "preserved_ac_refs": _L35_PRESERVED_AC_REFS,
        "decision_observation": {
            "failure_evidence": {"ref": "evidence:missing-runtime-chain", "sha256": "sha256:" + "d" * 64},
            "causal_hypothesis": "Verified antecedent evidence removes the temporal cycle.",
            "targeted_change": {"ref": candidate_ref, "sha256": "sha256:" + candidate_ref.rsplit(":", 1)[-1]},
            "predicted_benefit": "Construct direct runtime evidence before evaluator launch.",
            "at_risk_regression": "criterion:non-inferiority",
        },
        "retention_seconds": 3600,
    }
    return plan, {
        "expected_pair_plan_digest": _canonical_digest(plan),
        "candidate_admission": admission,
        "expected_candidate_admission_digest": admission_digest,
        "executor_packet": executor_packet,
        "expected_executor_packet_digest": executor_digest,
    }


def _canonical_line(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode() + b"\n"


def _persisted_receipt_line(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode() + b"\n"


def _l35_source_chain(
    *,
    false_facts=False,
    source_case_id="source-observation-1",
    evaluator_case_id="evaluator-1",
    plan=None,
    trusted=None,
    cell=None,
):
    if plan is None or trusted is None:
        plan, trusted = _l35_context()
    if cell is None:
        cell = {"arm": "candidate", "evaluation_split": "held_in"}
    arm = cell["arm"]
    split = cell["evaluation_split"]
    producer_binding = {
        "pair_plan_digest": trusted["expected_pair_plan_digest"],
        "arm": arm,
        "evaluation_split": split,
        "source_revision_ref": plan[f"{arm}_revision_ref"],
        "split_ref": plan[f"{split}_ref"],
        "split_digest": plan[f"{split}_digest"],
        "model_identity": plan["model_identity"],
        "model_configuration_digest": plan["model_configuration_digest"],
    }
    producer_cell = {
        "cell": f"{arm}/{split}",
        "arm": arm,
        "source_revision_ref": plan[f"{arm}_revision_ref"],
        "evaluation_split": split,
        "split_ref": plan[f"{split}_ref"],
        "split_digest": plan[f"{split}_digest"],
        "model_identity": plan["model_identity"],
        "model_configuration_digest": plan["model_configuration_digest"],
        "sampling_identity": plan["sampling_identity"],
    }
    producer_cell["cell_identity"] = _l35_cell_identity(producer_cell)
    producer = {
        "schema": "harness.l3-ac14-source-producer-result.v1",
        "declaration_ref": "C-L3.5-PE2/D-CURRENT-2026-08-09",
        "cell": producer_cell,
        "facts": {
            "source_native_preserved_ac": {
                ref: not false_facts or ref != "C-L3.4:AC3"
                for ref in ("C-L3.4:AC1", "C-L3.4:AC3", "C-L3.4:AC4")
            },
        },
    }
    source_output = _canonical_line(producer)
    empty = hashlib.sha256(b"").hexdigest()
    body = hashlib.sha256(b"bounded-source-input").hexdigest()
    output = hashlib.sha256(source_output).hexdigest()
    dispatch_artifacts = {
        "body": {"ref": "artifacts/body.bin", "sha256": body, "bytes": 20},
        "stdout": {"ref": "artifacts/stdout.bin", "sha256": empty, "bytes": 0},
        "stderr": {"ref": "artifacts/stderr.bin", "sha256": empty, "bytes": 0},
    }
    terminal_artifacts = json.loads(json.dumps(dispatch_artifacts))
    terminal_artifacts["stdout"] = {
        "ref": "artifacts/stdout.bin",
        "sha256": output,
        "bytes": len(source_output),
    }
    base = {
        "schema": "harness.runtime.execution-receipt.v1",
        "case_id": source_case_id,
        "consumer": "maat-source-observation",
        "recorded_at": "2026-08-08T00:00:00+00:00",
    }
    dispatch = {
        **base,
        "sequence": 1,
        "event": "dispatch",
        "status": "observed",
        "exit_code": None,
        "artifacts": dispatch_artifacts,
    }
    environment = {"LANG": "C", "LC_ALL": "C", "PATH": os.defpath, "TZ": "UTC", "HARNESS_STATE_DIR": "/isolated-state"}
    argv = ["source-observation-producer", "--stdin-only"]
    terminal = {
        **base,
        "recorded_at": "2026-08-08T00:00:01+00:00",
        "sequence": 2,
        "event": "terminal",
        "status": "pass",
        "exit_code": 0,
        "artifacts": terminal_artifacts,
        "execution": {
            "argv": argv,
            "argv_sha256": hashlib.sha256(json.dumps(argv, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "environment": environment,
            "environment_sha256": hashlib.sha256(json.dumps(environment, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "git_commit": "e" * 40,
            "git_tree": "f" * 40,
            "worktree_cwd": "/bounded-worktree",
            "worktree_cwd_sha256": hashlib.sha256(b"/bounded-worktree").hexdigest(),
        },
    }
    dispatch_bytes = _persisted_receipt_line(dispatch)
    terminal_bytes = _persisted_receipt_line(terminal)
    observation_binding = {
        "candidate_ref": plan["candidate_ref"],
        "candidate_admission_digest": trusted["expected_candidate_admission_digest"],
        **producer_binding,
        "evaluator_identity": plan["evaluator_identity"],
        "evaluator_configuration_digest": plan["evaluator_configuration_digest"],
        "result_contract_ref": plan["result_contract_ref"],
        "result_contract_digest": plan["result_contract_digest"],
        "target_ac_ref": "AC14",
    }
    readback_projection = {
        "schema": "harness.l3-ac14-source-readback-projection.v1",
        "source_case_id": source_case_id,
        "producer_state": "stopped",
        "read_at": "2026-08-08T00:00:02+00:00",
        "binding": observation_binding,
        "dispatch_receipt_sha256": "sha256:" + hashlib.sha256(dispatch_bytes).hexdigest(),
        "terminal_receipt_sha256": "sha256:" + hashlib.sha256(terminal_bytes).hexdigest(),
        "output_sha256": "sha256:" + output,
        "artifacts": terminal_artifacts,
    }
    return {
        "plan": plan,
        "trusted": trusted,
        "cell": cell,
        "source_case_id": source_case_id,
        "evaluator_case_id": evaluator_case_id,
        "source_output": source_output,
        "source_dispatch_receipt": dispatch_bytes,
        "source_terminal_receipt": terminal_bytes,
        "source_readback_projection": _canonical_line(readback_projection),
        "producer": producer,
        "readback_projection": readback_projection,
    }


_L35_EVALUATOR_PATH = Path(
    "/Users/kann/projects/harness-starter/runtime/harness_runtime/l3_ac14_evaluator.py"
)
_L35_EVALUATOR_COMMAND = [sys.executable, str(_L35_EVALUATOR_PATH)]
_L35_PRODUCER_PATH = Path(
    "/Users/kann/projects/harness-starter/runtime/harness_runtime/l3_source_observation_producer.py"
)


def _l35_context_bound_to_real_source_producer(project_root=None):
    plan, trusted = _l35_context()
    baseline_manifest = {
        "contracts/execution-receipt.v1.schema.json": "1b464b23cd5c08d33f1608b0bee7af92014d62484b63ef09fa1ab9e47390efda",
        "runtime/harness_runtime/runtime.py": "d695741374836b658a673f232eab8b20b9a0308fecec23c32f8ee05551b0a2c1",
        "tests/runtime/test_runtime_contract.py": "c3b2d69142fe3e9f63b19d204f133a353a2a4023d93c23de434f3635236db78c",
    }
    project_root = Path(__file__).parents[2] if project_root is None else Path(project_root)
    candidate_manifest = {
        relative_path: hashlib.sha256((project_root / relative_path).read_bytes()).hexdigest()
        for relative_path in (
            "contracts/execution-receipt.v1.schema.json",
            "runtime/harness_runtime/runtime.py",
            "tests/runtime/test_runtime_contract.py",
        )
    }
    baseline_ref = "source-manifest:" + _canonical_digest(baseline_manifest)
    candidate_ref = "source-manifest:" + _canonical_digest(candidate_manifest)
    admission = trusted["candidate_admission"]
    admission["candidate"]["identity"] = candidate_ref
    admission["candidate"]["allowed_write_refs"] = sorted(candidate_manifest)
    admission["fixed_evaluation"]["model"] = {
        "identity": "C-L3.4-receipt-backed-paired-runtime",
        "configuration_digest": "sha256:1a2e1302ee243aff4237597118377cc28b835690fccacc6587942dcb7d311008",
    }
    admission["fixed_evaluation"]["splits"] = {
        "held_in_ref": "packet:C-L3.4#AC14:fresh-valid-chain",
        "held_in_digest": "sha256:130457b452647ac9bd236c4cb407e7264c8fb952389767740a7070cb3c3c5fec",
        "held_out_ref": "packet:C-L3.4#fail-closed-boundaries",
        "held_out_digest": "sha256:bfbe5cc7c7ee3582808bff92418a239277ea5e70271476fb2d97fcc5ebc6543a",
        "sampling_identity": "canonical-exhaustive-four-cell-plus-declared-denial-boundaries",
        "secrecy_boundary": "held_out_opaque_no_content_access",
    }
    admission["immutable_controls"]["held_out_ref"] = admission["fixed_evaluation"]["splits"]["held_out_ref"]
    admission_digest = _canonical_digest(admission)
    packet = trusted["executor_packet"]
    packet["source_refs"] = [admission["candidate_ref"], admission_digest]
    packet["allowed_write_refs"] = sorted(candidate_manifest)
    packet_digest = _canonical_digest(packet)
    plan.update({
        "candidate_admission_digest": admission_digest,
        "executor_packet_digest": packet_digest,
        "source_revision_projection": {
            "baseline": {"revision_ref": baseline_ref, "manifest": baseline_manifest},
            "candidate": {"revision_ref": candidate_ref, "manifest": candidate_manifest},
        },
        "baseline_revision_ref": baseline_ref,
        "candidate_revision_ref": candidate_ref,
        "model_identity": admission["fixed_evaluation"]["model"]["identity"],
        "model_configuration_digest": admission["fixed_evaluation"]["model"]["configuration_digest"],
        "held_in_ref": admission["fixed_evaluation"]["splits"]["held_in_ref"],
        "held_in_digest": admission["fixed_evaluation"]["splits"]["held_in_digest"],
        "held_out_ref": admission["fixed_evaluation"]["splits"]["held_out_ref"],
        "held_out_digest": admission["fixed_evaluation"]["splits"]["held_out_digest"],
        "sampling_identity": admission["fixed_evaluation"]["splits"]["sampling_identity"],
    })
    plan["decision_observation"]["targeted_change"] = {
        "ref": candidate_ref,
        "sha256": "sha256:" + candidate_ref.removeprefix("source-manifest:sha256:"),
    }
    return plan, {
        **trusted,
        "expected_pair_plan_digest": _canonical_digest(plan),
        "expected_candidate_admission_digest": admission_digest,
        "expected_executor_packet_digest": packet_digest,
    }


def test_schema_is_versioned_and_describes_execution_identity():
    schema = json.loads(schema_text())
    assert schema["$id"].endswith("execution-receipt.v1.schema.json")
    assert schema["properties"]["schema"]["const"] == "harness.runtime.execution-receipt.v1"
    required = schema["properties"]["execution"]["required"]
    assert {"argv_sha256", "environment_sha256", "git_commit", "git_tree", "worktree_cwd"} <= set(required)
    assert __version__ == "0.1.1"
    terminal_rule = schema["allOf"][1]
    assert terminal_rule["then"]["required"] == ["execution"]


def test_explicit_isolated_state_and_safe_case_are_required(tmp_path, monkeypatch):
    worktree = _clean_git_worktree(tmp_path / "worktree")
    monkeypatch.delenv("HARNESS_STATE_DIR", raising=False)
    with pytest.raises(ReceiptValidationError, match="HARNESS_STATE_DIR is required"):
        execute("unit-case", "anubis", b"body", [sys.executable, "-c", "pass"], worktree_cwd=worktree)
    monkeypatch.setenv("HARNESS_STATE_DIR", str(tmp_path / "isolated-state"))
    with pytest.raises(ReceiptValidationError, match="case_id"):
        execute("../unit-case", "anubis", b"body", [sys.executable, "-c", "pass"], worktree_cwd=worktree)


def test_implicit_nested_or_dirty_worktree_is_forbidden(tmp_path, monkeypatch):
    monkeypatch.setenv("HARNESS_STATE_DIR", str(tmp_path / "isolated-state"))
    worktree = _clean_git_worktree(tmp_path / "worktree")
    with pytest.raises(ReceiptValidationError, match="worktree_cwd is required"):
        execute("implicit-cwd", "anubis", b"body", [sys.executable, "-c", "pass"])
    nested = worktree / "nested"
    nested.mkdir()
    subprocess.run(["git", "-C", str(worktree), "add", "nested"], check=True)
    with pytest.raises(ReceiptValidationError, match="worktree root"):
        execute("nested-cwd", "anubis", b"body", [sys.executable, "-c", "pass"], worktree_cwd=nested)
    (worktree / "untracked.txt").write_text("dirty", encoding="utf-8")
    with pytest.raises(ReceiptValidationError, match="worktree_cwd must be clean"):
        execute("dirty-cwd", "anubis", b"body", [sys.executable, "-c", "pass"], worktree_cwd=worktree)


def test_state_dir_inside_worktree_is_forbidden(tmp_path, monkeypatch):
    worktree = _clean_git_worktree(tmp_path / "worktree")
    monkeypatch.setenv("HARNESS_STATE_DIR", str(worktree / ".harness-state"))
    with pytest.raises(ReceiptValidationError, match="outside worktree_cwd"):
        execute("internal-state", "anubis", b"body", [sys.executable, "-c", "pass"], worktree_cwd=worktree)


def test_cli_run_accepts_worktree_cwd_and_analysis_input(tmp_path, monkeypatch, capsys):
    state_dir = tmp_path / "isolated-state"
    worktree = _clean_git_worktree(tmp_path / "worktree")
    body = tmp_path / "body.bin"
    body.write_bytes(b"cli-body")
    monkeypatch.setenv("HARNESS_STATE_DIR", str(state_dir))

    assert cli_main([
        "run",
        "--case", "cli-case",
        "--consumer", "anubis",
        "--body-file", str(body),
        "--worktree-cwd", str(worktree),
        "--",
        sys.executable, "-c", "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())",
    ]) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["execution"]["worktree_cwd"] == str(worktree)

    assert cli_main(["analysis-input", "--case", "cli-case"]) == 0
    verified = json.loads(capsys.readouterr().out)
    assert verified["outputs"]["stdout"] == {"text": "cli-body", "truncated": False}


def test_execution_receipt_and_anubis_input_are_verified(tmp_path, monkeypatch):
    state_dir = tmp_path / "isolated-state"
    worktree = _clean_git_worktree(tmp_path / "clean-worktree")
    monkeypatch.setenv("HARNESS_STATE_DIR", str(state_dir))
    monkeypatch.setenv("HERMES_HOME", "/forbidden/hermes")
    monkeypatch.setenv("AGY_RUNTIME", "forbidden")
    command = [
        sys.executable,
        "-c",
        (
            "import json, os, pathlib, sys; "
            "print(json.dumps({'cwd': str(pathlib.Path.cwd()), 'env': dict(os.environ)}, sort_keys=True)); "
            "sys.stderr.write('analysis-stderr')"
        ),
    ]
    result = execute("lifecycle-case", "anubis", b"producer-body", command, worktree_cwd=worktree)

    assert result["status"] == "pass"
    assert result["execution"]["git_commit"]
    assert result["execution"]["git_tree"]
    assert set(result["execution"]["environment"]) == {"HARNESS_STATE_DIR", "LANG", "LC_ALL", "PATH", "TZ"}
    receipt = readback("lifecycle-case", expected_consumer="anubis")
    assert receipt["analysis_basis"] == "harness.runtime.execution-receipt.v1"
    assert Path(receipt["receipt_path"]).is_relative_to(state_dir)
    analyst_input = analysis_input("lifecycle-case", output_limit=8)
    stdout = json.loads(analysis_input("lifecycle-case")["outputs"]["stdout"]["text"])
    assert stdout["cwd"] == str(worktree)
    assert "HERMES_HOME" not in stdout["env"]
    assert "AGY_RUNTIME" not in stdout["env"]
    assert analyst_input["outputs"]["stdout"]["truncated"] is True
    assert analyst_input["outputs"]["stderr"] == {"text": "analysis", "truncated": True}


def test_readback_rejects_receipt_or_artifact_tampering(tmp_path, monkeypatch):
    state_dir = tmp_path / "isolated-state"
    worktree = _clean_git_worktree(tmp_path / "worktree")
    monkeypatch.setenv("HARNESS_STATE_DIR", str(state_dir))
    execute("tamper-case", "anubis", b"body", [sys.executable, "-c", "print('ok')"], worktree_cwd=worktree)
    receipt_path = Path(readback("tamper-case")["receipt_path"])
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["execution"]["argv"].append("tampered")
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ReceiptValidationError, match="journal does not match"):
        readback("tamper-case")

    execute("artifact-case", "anubis", b"body", [sys.executable, "-c", "print('ok')"], worktree_cwd=worktree)
    artifact_receipt = readback("artifact-case")
    stdout_path = Path(artifact_receipt["receipt_path"]).parent / artifact_receipt["artifacts"]["stdout"]["ref"]
    stdout_path.write_bytes(b"changed")
    with pytest.raises(ReceiptValidationError, match="artifact readback does not match"):
        analysis_input("artifact-case")


def test_failed_spawn_still_produces_terminal_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv("HARNESS_STATE_DIR", str(tmp_path / "isolated-state"))
    worktree = _clean_git_worktree(tmp_path / "worktree")
    result = execute("missing-command", "anubis", b"", ["/definitely/missing/harness-command"], worktree_cwd=worktree)
    assert result["status"] == "fail"
    assert result["exit_code"] == 127
    verified = analysis_input("missing-command")
    assert verified["outputs"]["stderr"]["text"] == "runner error: FileNotFoundError\n"


@pytest.mark.parametrize(
    ("mutation", "value"),
    [
        ("candidate_admission_digest", "sha256:" + "0" * 64),
        ("candidate_admission_digest", "SHA256:" + "0" * 64),
        ("evaluation_split", "held_out"),
        ("phase", "baseline"),
        ("phase", "retry"),
        ("source_revision_ref", "source:substituted"),
        ("retention_seconds", 0),
        ("held_in_ref", None),
        ("held_out_ref", "split:held-out-v1"),
        ("benefit", "improved"),
    ],
)
def test_l3_experience_binding_rejects_mismatch_before_launch_and_write(
    tmp_path, monkeypatch, mutation, value
):
    state_dir = tmp_path / "isolated-state"
    monkeypatch.setenv("HARNESS_STATE_DIR", str(state_dir))
    binding, trusted = _l3_context()
    binding[mutation] = value
    calls = 0

    def unexpected_run(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("subprocess must not launch")

    monkeypatch.setattr(runtime_module.subprocess, "run", unexpected_run)
    with pytest.raises(ReceiptValidationError, match="experience binding"):
        execute(
            "l3-rejected",
            "anubis",
            b"body",
            [sys.executable, "-c", "pass"],
            worktree_cwd=tmp_path / "never-read",
            experience_binding=binding,
            **trusted,
        )

    assert calls == 0
    assert not state_dir.exists()


@pytest.mark.parametrize("mismatch", ["candidate", "executor", "partial"])
def test_l3_trusted_projection_mismatch_is_rejected_before_launch_and_write(
    tmp_path, monkeypatch, mismatch
):
    state_dir = tmp_path / "isolated-state"
    monkeypatch.setenv("HARNESS_STATE_DIR", str(state_dir))
    binding, trusted = _l3_context()
    if mismatch == "candidate":
        trusted["candidate_admission"]["candidate_ref"] = "C-L3.1:substituted"
    elif mismatch == "executor":
        trusted["executor_packet"]["work_id"] = "substituted"
    else:
        trusted["executor_packet"] = None
    calls = 0

    def unexpected_run(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("subprocess must not launch")

    monkeypatch.setattr(runtime_module.subprocess, "run", unexpected_run)
    with pytest.raises(ReceiptValidationError, match="identity mismatch|inputs are partial"):
        execute(
            f"l3-trusted-{mismatch}",
            "anubis",
            b"body",
            [sys.executable, "-c", "pass"],
            worktree_cwd=tmp_path / "never-read",
            experience_binding=binding,
            **trusted,
        )

    assert calls == 0
    assert not state_dir.exists()


def test_l3_experience_binding_is_identical_process_only_bounded_and_schema_valid(
    tmp_path, monkeypatch
):
    state_dir = tmp_path / "isolated-state"
    worktree = _clean_git_worktree(tmp_path / "worktree")
    monkeypatch.setenv("HARNESS_STATE_DIR", str(state_dir))
    binding, trusted = _l3_context()

    terminal = execute(
        "l3-success",
        "anubis",
        b"held-in-body",
        [sys.executable, "-c", "import sys; sys.stdout.write('abcdefghij')"],
        worktree_cwd=worktree,
        experience_binding=binding,
        **trusted,
    )
    verified = analysis_input(
        "l3-success",
        output_limit=4,
        expected_experience_binding=binding,
    )
    case_dir = Path(verified["receipt_path"]).parent
    journal = [json.loads(line) for line in (case_dir / "receipts.jsonl").read_text().splitlines()]
    schema = json.loads(schema_text())
    Draft202012Validator.check_schema(schema)
    for receipt in journal:
        Draft202012Validator(schema).validate(receipt)
    for field, value in (
        ("held_out_ref", "split:held-out-v1"),
        ("benefit", "improved"),
        ("retention_seconds", 0),
    ):
        denied = json.loads(json.dumps(journal[-1]))
        denied["experience_binding"][field] = value
        assert list(Draft202012Validator(schema).iter_errors(denied))

    assert [item["event"] for item in journal] == ["dispatch", "terminal"]
    assert [item["sequence"] for item in journal] == [1, 2]
    assert journal[0]["experience_binding"] == journal[1]["experience_binding"] == binding
    assert terminal["status"] == "pass" and terminal["exit_code"] == 0
    assert verified["outputs"]["stdout"] == {"text": "abcd", "truncated": True}
    serialized = json.dumps(journal)
    for forbidden in (
        "held_out_ref",
        "held_out_digest",
        "benefit",
        "verdict",
        "confirmation",
        "owner_hold",
        "learning_candidate",
        "promotion",
        "goal_closure",
    ):
        assert forbidden not in serialized


def test_l3_raw_artifacts_expire_at_exact_boundary_and_cleanup_is_case_local(
    tmp_path, monkeypatch
):
    state_dir = tmp_path / "isolated-state"
    worktree = _clean_git_worktree(tmp_path / "worktree")
    monkeypatch.setenv("HARNESS_STATE_DIR", str(state_dir))
    binding, trusted = _l3_context(retention_seconds=2)
    execute(
        "expiring-case",
        "anubis",
        b"body",
        [sys.executable, "-c", "print('raw-output')"],
        worktree_cwd=worktree,
        experience_binding=binding,
        **trusted,
    )
    execute(
        "other-case",
        "anubis",
        b"other",
        [sys.executable, "-c", "print('other-output')"],
        worktree_cwd=worktree,
    )
    receipt_path = Path(readback("expiring-case")["receipt_path"])
    dispatch = json.loads((receipt_path.parent / "receipts.jsonl").read_text().splitlines()[0])
    recorded_at = datetime.fromisoformat(dispatch["recorded_at"])

    before = recorded_at + timedelta(seconds=2, microseconds=-1)
    assert analysis_input(
        "expiring-case",
        read_at=before,
        expected_experience_binding=binding,
    )["outputs"]["stdout"]["text"] == "raw-output\n"

    with pytest.raises(ReceiptValidationError, match="expired"):
        analysis_input(
            "expiring-case",
            read_at=recorded_at + timedelta(seconds=2),
            expected_experience_binding=binding,
        )

    assert not (receipt_path.parent / "artifacts").exists()
    assert not list(receipt_path.parent.rglob("*.tmp"))
    other = Path(readback("other-case")["receipt_path"]).parent
    assert (other / "artifacts" / "stdout.bin").read_bytes() == b"other-output\n"
    compact = readback(
        "expiring-case",
        read_at=recorded_at + timedelta(seconds=2),
        expected_experience_binding=binding,
    )
    assert compact["raw_artifacts_available"] is False


def test_l3_readback_rejects_changed_binding_between_dispatch_and_terminal(
    tmp_path, monkeypatch
):
    state_dir = tmp_path / "isolated-state"
    worktree = _clean_git_worktree(tmp_path / "worktree")
    monkeypatch.setenv("HARNESS_STATE_DIR", str(state_dir))
    binding, trusted = _l3_context()
    execute(
        "binding-tamper",
        "anubis",
        b"body",
        [sys.executable, "-c", "pass"],
        worktree_cwd=worktree,
        experience_binding=binding,
        **trusted,
    )
    receipt_path = Path(readback("binding-tamper")["receipt_path"])
    journal_path = receipt_path.parent / "receipts.jsonl"
    journal = [json.loads(line) for line in journal_path.read_text().splitlines()]
    journal[-1]["experience_binding"]["source_revision_ref"] = "source:substituted"
    journal_path.write_text(
        "".join(json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n" for item in journal),
        encoding="utf-8",
    )
    receipt_path.write_text(json.dumps(journal[-1]), encoding="utf-8")

    with pytest.raises(ReceiptValidationError, match="changed between dispatch and terminal"):
        analysis_input("binding-tamper", expected_experience_binding=binding)


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


def test_l35_source_producer_result_requires_exact_canonical_bound_bytes():
    chain = _l35_source_chain()
    expected_cell = chain["producer"]["cell"]

    assert runtime_module._validate_l35_source_producer_result(
        chain["source_output"], expected_cell
    ) == chain["producer"]

    duplicate = chain["source_output"].replace(
        b'"schema":"harness.l3-ac14-source-producer-result.v1"',
        b'"schema":"harness.l3-ac14-source-producer-result.v1","schema":"harness.l3-ac14-source-producer-result.v1"',
        1,
    )
    additional = json.loads(chain["source_output"])
    additional["facts"]["terminal_receipt_observed"] = True
    unsorted_refs = json.loads(chain["source_output"])
    unsorted_refs["source_evidence_refs"] = ["source:minted"]
    wrong_boolean = json.loads(chain["source_output"])
    wrong_boolean["facts"]["source_native_preserved_ac"]["C-L3.4:AC1"] = 1
    for rejected in (
        duplicate,
        chain["source_output"].removesuffix(b"\n"),
        chain["source_output"] + b"\n",
        json.dumps(chain["producer"]).encode() + b"\n",
        b"\xff\n",
        _canonical_line(additional),
        _canonical_line(unsorted_refs),
        _canonical_line(wrong_boolean),
    ):
        with pytest.raises(ReceiptValidationError):
            runtime_module._validate_l35_source_producer_result(rejected, expected_cell)

    substitutions = {
        "cell_identity": "sha256:" + "0" * 64,
        "source_revision_ref": "source-manifest:sha256:" + "1" * 64,
        "split_ref": "split:substituted",
        "split_digest": "sha256:" + "2" * 64,
        "model_identity": "model:substituted",
        "model_configuration_digest": "sha256:" + "3" * 64,
        "sampling_identity": "sampling:substituted",
    }
    for field, value in substitutions.items():
        substituted = json.loads(chain["source_output"])
        substituted["cell"][field] = value
        with pytest.raises(ReceiptValidationError):
            runtime_module._validate_l35_source_producer_result(
                _canonical_line(substituted), expected_cell
            )
    later_ac = json.loads(chain["source_output"])
    later_ac["facts"]["source_native_preserved_ac"]["C-L3.4:AC2"] = True
    with pytest.raises(ReceiptValidationError):
        runtime_module._validate_l35_source_producer_result(
            _canonical_line(later_ac), expected_cell
        )


def test_l35_cell_identity_derives_from_exactly_eight_identity_inputs():
    chain = _l35_source_chain()
    cell = chain["producer"]["cell"]
    identity_inputs = {
        field: cell[field] for field in _L35_IDENTITY_INPUT_FIELDS
    }

    assert runtime_module._derive_l35_cell_identity(identity_inputs) == cell["cell_identity"]
    for field in _L35_IDENTITY_INPUT_FIELDS:
        mutated = dict(identity_inputs)
        mutated[field] = mutated[field] + ":mutated"
        assert runtime_module._derive_l35_cell_identity(mutated) != cell["cell_identity"]
    with pytest.raises(ReceiptValidationError):
        runtime_module._derive_l35_cell_identity(
            {**identity_inputs, "cell": cell["cell"]}
        )


def test_l35_constructor_preserves_exact_partial_facts_and_routes_later_owners():
    chain = _l35_source_chain()
    observation = json.loads(runtime_module._construct_l35_source_observation(
        source_case_id=chain["source_case_id"], evaluator_case_id=chain["evaluator_case_id"],
        source_output=chain["source_output"], source_dispatch_receipt=chain["source_dispatch_receipt"],
        source_terminal_receipt=chain["source_terminal_receipt"], source_readback_projection=chain["source_readback_projection"],
        pair_plan=chain["plan"], paired_cell=chain["cell"], **chain["trusted"],
    ))
    assert observation["facts"] == {
        "preserved_ac": {
            "C-L3.4:AC1": True,
            "C-L3.4:AC3": True,
            "C-L3.4:AC4": True,
        }
    }
    assert observation["owner_holds"] == _L35_OWNER_HOLDS
    serialized = _canonical_line(observation).decode()
    for forbidden in ("evaluator_result", "target_ac_values", "criteria_values", "score", "disposition"):
        assert forbidden not in serialized


def test_current_worktree_producer_to_evaluator_receipt_schema_readback_e2e(
    tmp_path, monkeypatch,
):
    project_root = Path(__file__).parents[2]
    plan, trusted = _l35_context_bound_to_real_source_producer(project_root)
    selector = {
        "schema": "harness.l3-source-native-cell-observation.v1",
        "declaration_ref": "C-L3.5-PE2/D-CURRENT-2026-08-09",
        "cell": "candidate/held_in",
    }
    completed = subprocess.run(
        [
            sys.executable,
            str(project_root / "runtime/harness_runtime/l3_source_observation_producer.py"),
            "--stdin-only",
        ],
        input=_canonical_line(selector),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert completed.returncode == 0 and completed.stderr == b""

    chain = _l35_source_chain(plan=plan, trusted=trusted)
    chain["source_output"] = completed.stdout
    chain["producer"] = json.loads(completed.stdout)
    output_digest = hashlib.sha256(completed.stdout).hexdigest()
    terminal = json.loads(chain["source_terminal_receipt"])
    terminal["artifacts"]["stdout"].update(
        sha256=output_digest, bytes=len(completed.stdout)
    )
    chain["source_terminal_receipt"] = _persisted_receipt_line(terminal)
    chain["readback_projection"]["artifacts"] = terminal["artifacts"]
    chain["readback_projection"]["output_sha256"] = "sha256:" + output_digest
    chain["readback_projection"]["terminal_receipt_sha256"] = (
        "sha256:" + hashlib.sha256(chain["source_terminal_receipt"]).hexdigest()
    )
    chain["source_readback_projection"] = _canonical_line(chain["readback_projection"])
    assert all(
        isinstance(chain[name], bytes)
        for name in (
            "source_output",
            "source_dispatch_receipt",
            "source_terminal_receipt",
            "source_readback_projection",
        )
    )
    state_dir = tmp_path / "isolated-state"
    monkeypatch.setenv("HARNESS_STATE_DIR", str(state_dir))
    worktree = _clean_git_worktree(tmp_path / "worktree")
    terminal = runtime_module.execute_paired_cell(
        chain["evaluator_case_id"],
        "maat",
        chain["source_output"],
        _L35_EVALUATOR_COMMAND,
        source_case_id=chain["source_case_id"],
        source_dispatch_receipt=chain["source_dispatch_receipt"],
        source_terminal_receipt=chain["source_terminal_receipt"],
        source_readback_projection=chain["source_readback_projection"],
        worktree_cwd=worktree,
        pair_plan=plan,
        paired_cell=chain["cell"],
        **trusted,
    )
    assert terminal["evaluator_result"]["observed_ac_values"] == {
        "C-L3.4:AC1": True,
        "C-L3.4:AC3": True,
        "C-L3.4:AC4": True,
    }
    assert terminal["evaluator_result"]["evaluation_state"] == "partial_unresolved"
    assert terminal["evaluator_result"]["evaluated_phase"] == "phase_1_source_observation"
    assert terminal["evaluator_result"]["unresolved_inputs"] == _L35_OWNER_HOLDS
    assert "owner_holds" not in terminal["evaluator_result"]
    verified = runtime_module.readback(
        chain["evaluator_case_id"], expected_consumer="maat"
    )
    receipt_path = Path(verified["receipt_path"])
    journal = [
        json.loads(line)
        for line in (receipt_path.parent / "receipts.jsonl").read_text().splitlines()
    ]
    validator = Draft202012Validator(json.loads(schema_text()))
    assert all(not list(validator.iter_errors(receipt)) for receipt in journal)
    assert json.loads(
        (receipt_path.parent / terminal["artifacts"]["stdout"]["ref"]).read_bytes()
    ) == terminal["evaluator_result"]
    serialized = _canonical_line(terminal["evaluator_result"]).decode()
    for forbidden in (
        "target_ac_values",
        "criteria_values",
        "non_inferiority",
        "score",
        "disposition",
        "PASS",
        "confirm",
        "revert",
    ):
        assert forbidden not in serialized


def test_l35_source_terminal_receipt_rejects_nonliteral_or_additional_producer_argv_before_construction(
    tmp_path, monkeypatch
):
    state_dir = tmp_path / "isolated-state"
    monkeypatch.setenv("HARNESS_STATE_DIR", str(state_dir))
    counters = {"launch": 0, "write": 0, "append": 0}

    def counted(name):
        def unexpected(*args, **kwargs):
            counters[name] += 1
            raise AssertionError(f"{name} must not occur")

        return unexpected

    monkeypatch.setattr(runtime_module.subprocess, "run", counted("launch"))
    monkeypatch.setattr(runtime_module, "_write", counted("write"))
    monkeypatch.setattr(runtime_module, "_append", counted("append"))
    for argv in (
        ["source-observation-producer"],
        ["--stdin-only", "source-observation-producer"],
        ["source-observation-producer", "--stdout"],
        ["source-observation-producer", "--stdin-only", "extra"],
        ["/path/source-observation-producer", "--stdin-only"],
    ):
        chain = _l35_source_chain()
        terminal = json.loads(chain["source_terminal_receipt"])
        terminal["execution"]["argv"] = argv
        terminal["execution"]["argv_sha256"] = hashlib.sha256(
            json.dumps(argv, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        chain["source_terminal_receipt"] = _persisted_receipt_line(terminal)
        chain["readback_projection"]["terminal_receipt_sha256"] = (
            "sha256:" + hashlib.sha256(chain["source_terminal_receipt"]).hexdigest()
        )
        chain["source_readback_projection"] = _canonical_line(chain["readback_projection"])

        with pytest.raises(ReceiptValidationError, match="source producer command identity"):
            runtime_module._construct_l35_source_observation(
                source_case_id=chain["source_case_id"],
                evaluator_case_id=chain["evaluator_case_id"],
                source_output=chain["source_output"],
                source_dispatch_receipt=chain["source_dispatch_receipt"],
                source_terminal_receipt=chain["source_terminal_receipt"],
                source_readback_projection=chain["source_readback_projection"],
                pair_plan=chain["plan"],
                paired_cell=chain["cell"],
                **chain["trusted"],
            )

    assert counters == {"launch": 0, "write": 0, "append": 0}
    assert not state_dir.exists()


def test_l35_execute_paired_cell_rejects_substituted_or_additional_evaluator_argv_before_launch_or_write(
    tmp_path, monkeypatch
):
    state_dir = tmp_path / "isolated-state"
    monkeypatch.setenv("HARNESS_STATE_DIR", str(state_dir))
    original_construct = runtime_module._construct_l35_source_observation
    original_worktree = runtime_module._worktree
    counters = {"construct": 0, "worktree": 0, "launch": 0, "write": 0, "append": 0}

    def counted_construct(*args, **kwargs):
        counters["construct"] += 1
        return original_construct(*args, **kwargs)

    def counted_worktree(*args, **kwargs):
        counters["worktree"] += 1
        return original_worktree(*args, **kwargs)

    def counted(name):
        def unexpected(*args, **kwargs):
            counters[name] += 1
            raise AssertionError(f"{name} must not occur")

        return unexpected

    monkeypatch.setattr(runtime_module, "_construct_l35_source_observation", counted_construct)
    monkeypatch.setattr(runtime_module, "_worktree", counted_worktree)
    monkeypatch.setattr(runtime_module.subprocess, "run", counted("launch"))
    monkeypatch.setattr(runtime_module, "_write", counted("write"))
    monkeypatch.setattr(runtime_module, "_append", counted("append"))
    for command in (
        ["python3.11", str(_L35_EVALUATOR_PATH)],
        [sys.executable, "/tmp/substituted-evaluator.py"],
        [*_L35_EVALUATOR_COMMAND, "extra"],
        [sys.executable, "-c", "pass"],
    ):
        chain = _l35_source_chain()
        with pytest.raises(ReceiptValidationError):
            runtime_module.execute_paired_cell(
                chain["evaluator_case_id"],
                "maat",
                chain["source_output"],
                command,
                source_case_id=chain["source_case_id"],
                source_dispatch_receipt=chain["source_dispatch_receipt"],
                source_terminal_receipt=chain["source_terminal_receipt"],
                source_readback_projection=chain["source_readback_projection"],
                worktree_cwd=tmp_path / "never-read",
                pair_plan=chain["plan"],
                paired_cell=chain["cell"],
                **chain["trusted"],
            )
        assert counters == {
            "construct": 0,
            "worktree": 0,
            "launch": 0,
            "write": 0,
            "append": 0,
        }

    assert not state_dir.exists()


def test_l35_unresolved_inputs_do_not_block_evaluator_receipt_and_schema_readback(
    tmp_path, monkeypatch
):
    state_dir = tmp_path / "isolated-state"
    monkeypatch.setenv("HARNESS_STATE_DIR", str(state_dir))
    worktree = _clean_git_worktree(tmp_path / "worktree")
    chain = _l35_source_chain()
    terminal = runtime_module.execute_paired_cell(
        chain["evaluator_case_id"],
        "maat",
        chain["source_output"],
        _L35_EVALUATOR_COMMAND,
        source_case_id=chain["source_case_id"],
        source_dispatch_receipt=chain["source_dispatch_receipt"],
        source_terminal_receipt=chain["source_terminal_receipt"],
        source_readback_projection=chain["source_readback_projection"],
        worktree_cwd=worktree,
        pair_plan=chain["plan"],
        paired_cell=chain["cell"],
        **chain["trusted"],
    )

    assert terminal["status"] == "pass" and terminal["exit_code"] == 0
    assert terminal["evaluator_result"]["observed_ac_values"] == {
        "C-L3.4:AC1": True,
        "C-L3.4:AC3": True,
        "C-L3.4:AC4": True,
    }
    assert terminal["evaluator_result"]["evaluation_state"] == "partial_unresolved"
    assert terminal["evaluator_result"]["evaluated_phase"] == "phase_1_source_observation"
    assert terminal["evaluator_result"]["unresolved_inputs"] == _L35_OWNER_HOLDS
    assert "owner_holds" not in terminal["evaluator_result"]
    verified = runtime_module.readback(
        chain["evaluator_case_id"], expected_consumer="maat"
    )
    receipt_path = Path(verified["receipt_path"])
    journal = [json.loads(line) for line in (receipt_path.parent / "receipts.jsonl").read_text().splitlines()]
    validator = Draft202012Validator(json.loads(schema_text()))
    assert all(not list(validator.iter_errors(receipt)) for receipt in journal)
    assert json.loads((receipt_path.parent / terminal["artifacts"]["stdout"]["ref"]).read_bytes()) == terminal["evaluator_result"]


@pytest.mark.parametrize("mutation", ["owner", "status", "overlap", "numeric", "final"])
def test_l35_evaluator_result_validator_rejects_owner_status_overlap_numeric_and_final_values(
    mutation,
):
    plan, _ = _l35_context()
    result = {
        "evaluator_identity": plan["evaluator_identity"],
        "evaluator_configuration_digest": plan["evaluator_configuration_digest"],
        "result_contract_ref": plan["result_contract_ref"],
        "result_contract_digest": plan["result_contract_digest"],
        "evaluation_state": "partial_unresolved",
        "evaluated_phase": "phase_1_source_observation",
        "observed_ac_values": {
            "C-L3.4:AC1": True,
            "C-L3.4:AC3": True,
            "C-L3.4:AC4": True,
        },
        "unresolved_inputs": json.loads(json.dumps(_L35_OWNER_HOLDS)),
    }
    if mutation == "owner":
        result["unresolved_inputs"]["C-L3.4:AC2"]["owner_ref"] = "owner:substituted"
    elif mutation == "status":
        result["unresolved_inputs"]["C-L3.4:AC2"]["status"] = "resolved"
    elif mutation == "overlap":
        result["unresolved_inputs"]["C-L3.4:AC1"] = {
            "owner_ref": "owner:invented",
            "status": "no_value_and_owner_hold",
        }
    elif mutation == "numeric":
        result["observed_ac_values"]["C-L3.4:AC1"] = 1
    else:
        result["target_ac_values"] = {"AC14": 1}
    with pytest.raises(ReceiptValidationError):
        runtime_module._validate_evaluator_result(result, plan)


def test_l35_evaluator_result_schema_is_partial_unresolved_only():
    plan, _ = _l35_context()
    result = {
        "evaluator_identity": plan["evaluator_identity"],
        "evaluator_configuration_digest": plan["evaluator_configuration_digest"],
        "result_contract_ref": plan["result_contract_ref"],
        "result_contract_digest": plan["result_contract_digest"],
        "evaluation_state": "partial_unresolved",
        "evaluated_phase": "phase_1_source_observation",
        "observed_ac_values": {
            "C-L3.4:AC1": True,
            "C-L3.4:AC3": False,
            "C-L3.4:AC4": True,
        },
        "unresolved_inputs": _L35_OWNER_HOLDS,
    }
    schema = json.loads(schema_text())
    validator = Draft202012Validator(
        {"$ref": "#/$defs/evaluator_result", "$defs": schema["$defs"]}
    )
    assert not list(validator.iter_errors(result))
    for field, value in (
        ("owner_holds", _L35_OWNER_HOLDS),
        ("target_ac_values", {"AC14": 1}),
        ("criteria_values", {"benefit": 1}),
        ("non_inferiority", 1),
        ("score", 1),
        ("disposition", "PASS"),
    ):
        invented = json.loads(json.dumps(result))
        invented[field] = value
        assert list(validator.iter_errors(invented))


def test_paired_readback_rejects_partial_unresolved_before_final_numeric_aggregation(
    monkeypatch,
):
    plan, trusted = _l35_context()
    plan_digest = trusted["expected_pair_plan_digest"]
    result = {
        "evaluator_identity": plan["evaluator_identity"],
        "evaluator_configuration_digest": plan["evaluator_configuration_digest"],
        "result_contract_ref": plan["result_contract_ref"],
        "result_contract_digest": plan["result_contract_digest"],
        "evaluation_state": "partial_unresolved",
        "evaluated_phase": "phase_1_source_observation",
        "observed_ac_values": {
            "C-L3.4:AC1": True,
            "C-L3.4:AC3": False,
            "C-L3.4:AC4": True,
        },
        "unresolved_inputs": json.loads(json.dumps(_L35_OWNER_HOLDS)),
    }
    matrix = (
        ("baseline", "held_in"),
        ("candidate", "held_in"),
        ("baseline", "held_out"),
        ("candidate", "held_out"),
    )
    receipts = {}
    for index, (arm, split) in enumerate(matrix):
        case_id = f"partial-cell-{index}"
        receipts[case_id] = {
            "status": "pass",
            "exit_code": 0,
            "artifacts": {},
            "paired_evaluation": runtime_module._pair_binding(
                plan,
                plan_digest,
                {"arm": arm, "evaluation_split": split},
            ),
            "evaluator_result": json.loads(json.dumps(result)),
        }

    def read_partial(case_id, expected_consumer, require_artifacts):
        assert expected_consumer == "maat"
        assert require_artifacts is False
        return {"receipt": receipts[case_id]}, {}

    monkeypatch.setattr(runtime_module, "_readback", read_partial)
    with pytest.raises(
        ReceiptValidationError,
        match="final aggregation unavailable for partial_unresolved",
    ):
        runtime_module.paired_readback(
            list(receipts),
            expected_consumer="maat",
            pair_plan=plan,
            expected_pair_plan_digest=plan_digest,
        )


def test_l35_source_observation_constructor_preserves_false_facts_and_exact_evidence_refs():
    chain = _l35_source_chain(false_facts=True)
    observed = runtime_module._construct_l35_source_observation(
        source_case_id=chain["source_case_id"],
        evaluator_case_id=chain["evaluator_case_id"],
        source_output=chain["source_output"],
        source_dispatch_receipt=chain["source_dispatch_receipt"],
        source_terminal_receipt=chain["source_terminal_receipt"],
        source_readback_projection=chain["source_readback_projection"],
        pair_plan=chain["plan"],
        paired_cell=chain["cell"],
        **chain["trusted"],
    )
    observation = json.loads(observed)

    assert observed == _canonical_line(observation)
    assert observation["facts"]["preserved_ac"]["C-L3.4:AC3"] is False
    assert set(observation["facts"]["preserved_ac"]) == {
        "C-L3.4:AC1", "C-L3.4:AC3", "C-L3.4:AC4"
    }
    assert observation["owner_holds"] == _L35_OWNER_HOLDS
    expected_refs = sorted(
        {
            f"pair-plan:{chain['trusted']['expected_pair_plan_digest']}",
            f"source-observation-case:{chain['source_case_id']}",
            "source-observation-dispatch-receipt:sha256:"
            + hashlib.sha256(chain["source_dispatch_receipt"]).hexdigest(),
            "source-observation-terminal-receipt:sha256:"
            + hashlib.sha256(chain["source_terminal_receipt"]).hexdigest(),
            "source-observation-readback:sha256:"
            + hashlib.sha256(chain["source_readback_projection"]).hexdigest(),
            "source-observation-output:sha256:"
            + hashlib.sha256(chain["source_output"]).hexdigest(),
        }
    )
    assert observation["evidence_refs"] == expected_refs


def test_l35_source_observation_constructor_rejects_same_case_future_stale_mixed_and_substituted_evidence():
    mutations = []

    same_case = _l35_source_chain(evaluator_case_id="source-observation-1")
    mutations.append(same_case)

    future = _l35_source_chain()
    terminal = json.loads(future["source_terminal_receipt"])
    terminal["evaluator_result"] = {"target_ac_values": {"AC14": 1}}
    future["source_terminal_receipt"] = _persisted_receipt_line(terminal)
    mutations.append(future)

    stale = _l35_source_chain()
    stale["readback_projection"]["producer_state"] = "running"
    stale["source_readback_projection"] = _canonical_line(stale["readback_projection"])
    mutations.append(stale)

    mixed = _l35_source_chain()
    mixed["readback_projection"]["terminal_receipt_sha256"] = "sha256:" + "0" * 64
    mixed["source_readback_projection"] = _canonical_line(mixed["readback_projection"])
    mutations.append(mixed)

    substituted = _l35_source_chain()
    substituted["producer"]["cell"]["arm"] = "baseline"
    substituted["source_output"] = _canonical_line(substituted["producer"])
    mutations.append(substituted)

    for chain in mutations:
        with pytest.raises(ReceiptValidationError):
            runtime_module._construct_l35_source_observation(
                source_case_id=chain["source_case_id"],
                evaluator_case_id=chain["evaluator_case_id"],
                source_output=chain["source_output"],
                source_dispatch_receipt=chain["source_dispatch_receipt"],
                source_terminal_receipt=chain["source_terminal_receipt"],
                source_readback_projection=chain["source_readback_projection"],
                pair_plan=chain["plan"],
                paired_cell=chain["cell"],
                **chain["trusted"],
            )


def test_l35_execute_paired_cell_cannot_launch_or_write_before_verified_source_construction(
    tmp_path, monkeypatch
):
    chain = _l35_source_chain()
    state_dir = tmp_path / "isolated-state"
    monkeypatch.setenv("HARNESS_STATE_DIR", str(state_dir))
    launches = 0
    writes = 0

    def unexpected_run(*args, **kwargs):
        nonlocal launches
        launches += 1
        raise AssertionError("subprocess must not launch")

    def unexpected_write(*args, **kwargs):
        nonlocal writes
        writes += 1
        raise AssertionError("state or artifact write must not occur")

    monkeypatch.setattr(runtime_module.subprocess, "run", unexpected_run)
    monkeypatch.setattr(runtime_module, "_write", unexpected_write)
    with pytest.raises(ReceiptValidationError):
        runtime_module.execute_paired_cell(
            chain["evaluator_case_id"],
            "maat",
            b'{"schema":"caller-fact-vector"}\n',
            _L35_EVALUATOR_COMMAND,
            source_case_id=chain["source_case_id"],
            source_dispatch_receipt=chain["source_dispatch_receipt"],
            source_terminal_receipt=chain["source_terminal_receipt"],
            source_readback_projection=chain["source_readback_projection"],
            worktree_cwd=tmp_path / "never-read",
            pair_plan=chain["plan"],
            paired_cell=chain["cell"],
            **chain["trusted"],
        )

    assert launches == 0
    assert writes == 0
    assert not state_dir.exists()


def test_l35_temporal_contract_keeps_producer_constructor_and_consumer_evidence_distinct():
    chain = _l35_source_chain()
    signature = inspect.signature(runtime_module._construct_l35_source_observation)
    forbidden_overrides = {
        "producer_observed",
        "terminal_receipt_observed",
        "fresh_consumer_readback_observed",
        "identity_chain_exact",
        "preserved_ac",
        "control_surfaces_non_regressed",
        "material_semantic_regression_observed",
        "unresolved_uncertainty_observed",
        "target_ac_values",
        "criteria_values",
        "score",
        "verdict",
        "disposition",
    }
    assert set(signature.parameters).isdisjoint(forbidden_overrides)

    observation = json.loads(
        runtime_module._construct_l35_source_observation(
            source_case_id=chain["source_case_id"],
            evaluator_case_id=chain["evaluator_case_id"],
            source_output=chain["source_output"],
            source_dispatch_receipt=chain["source_dispatch_receipt"],
            source_terminal_receipt=chain["source_terminal_receipt"],
            source_readback_projection=chain["source_readback_projection"],
            pair_plan=chain["plan"],
            paired_cell=chain["cell"],
            **chain["trusted"],
        )
    )
    refs = observation["evidence_refs"]
    assert f"source-observation-case:{chain['source_case_id']}" in refs
    assert all(chain["evaluator_case_id"] not in ref for ref in refs)
    layer_refs = [
        ref
        for ref in refs
        if ref.startswith(
            (
                "source-observation-output:",
                "source-observation-dispatch-receipt:",
                "source-observation-terminal-receipt:",
                "source-observation-readback:",
            )
        )
    ]
    assert len(layer_refs) == 4
    assert len(set(layer_refs)) == 4
