import ast
import copy
import itertools
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from harness_runtime.l3_ac14_evaluator import _evaluate


MODULE_PATH = (
    Path(__file__).parents[2] / "runtime" / "harness_runtime" / "l3_ac14_evaluator.py"
)
EVALUATOR_IDENTITY = "maat:C-L3.4:AC14-direct-runtime-evaluator"
EVALUATOR_CONFIGURATION_DIGEST = (
    "sha256:5da3457d462cdfe75b792ed4b48dea7d872eae9ce66aba894b38442bfcb83994"
)
RESULT_CONTRACT_REF = "harness.runtime.execution-receipt.v1"
RESULT_CONTRACT_DIGEST = (
    "sha256:928954a0f4ac84768e14b752386a6a6de2ae03fe43ac8e34d56384b941f305cb"
)
OBSERVED_AC_REFS = {"C-L3.4:AC1", "C-L3.4:AC3", "C-L3.4:AC4"}
OWNER_HOLDS = {
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
        "owner_ref": EVALUATOR_IDENTITY,
        "status": "no_value_and_owner_hold",
    },
}


def _observation() -> dict:
    return {
        "schema": "harness.l3-ac14-source-observation.v1",
        "binding": {
            "candidate_ref": "candidate:C-L3.4-E1",
            "candidate_admission_digest": "sha256:" + "1" * 64,
            "pair_plan_digest": "sha256:" + "2" * 64,
            "arm": "candidate",
            "evaluation_split": "held_in",
            "source_revision_ref": "source-manifest:sha256:" + "3" * 64,
            "split_ref": "split:held-in-v1",
            "split_digest": "sha256:" + "4" * 64,
            "model_identity": "model:fixed-v1",
            "model_configuration_digest": "sha256:" + "5" * 64,
            "evaluator_identity": EVALUATOR_IDENTITY,
            "evaluator_configuration_digest": EVALUATOR_CONFIGURATION_DIGEST,
            "result_contract_ref": RESULT_CONTRACT_REF,
            "result_contract_digest": RESULT_CONTRACT_DIGEST,
            "target_ac_ref": "AC14",
        },
        "facts": {
            "preserved_ac": {ref: True for ref in sorted(OBSERVED_AC_REFS)},
        },
        "owner_holds": copy.deepcopy(OWNER_HOLDS),
        "evidence_refs": ["artifact:direct-readback", "source:terminal-receipt"],
    }


def _result(observation: dict) -> dict:
    return {
        "evaluator_identity": EVALUATOR_IDENTITY,
        "evaluator_configuration_digest": EVALUATOR_CONFIGURATION_DIGEST,
        "result_contract_ref": RESULT_CONTRACT_REF,
        "result_contract_digest": RESULT_CONTRACT_DIGEST,
        "evaluation_state": "partial_unresolved",
        "evaluated_phase": "phase_1_source_observation",
        "observed_ac_values": copy.deepcopy(observation["facts"]["preserved_ac"]),
        "unresolved_inputs": copy.deepcopy(OWNER_HOLDS),
    }


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8") + b"\n"


def _run(stdin: bytes, *argv: str, environment: dict[str, str] | None = None):
    return subprocess.run(
        [sys.executable, str(MODULE_PATH), *argv],
        input=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
        check=False,
    )


def _assert_rejected(stdin: bytes, *argv: str) -> None:
    completed = _run(stdin, *argv)
    assert completed.returncode == 2
    assert completed.stdout == b""
    assert completed.stderr == b""


def test_phase1_partial_unresolved_result_is_exact_and_boolean():
    observation = _observation()
    observation["evidence_refs"] = ["artifact:직접-관찰"]

    completed = _run(_canonical(observation))

    assert completed.returncode == 0
    assert completed.stderr == b""
    assert completed.stdout == _canonical(_result(observation))
    result = json.loads(completed.stdout)
    assert result["evaluation_state"] == "partial_unresolved"
    assert result["evaluated_phase"] == "phase_1_source_observation"
    assert set(result["observed_ac_values"]) == OBSERVED_AC_REFS
    assert all(type(value) is bool for value in result["observed_ac_values"].values())
    assert result["unresolved_inputs"] == OWNER_HOLDS
    assert "owner_holds" not in result
    serialized = completed.stdout.decode()
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


def test_each_phase1_boolean_combination_is_preserved_without_numeric_fill():
    observation = _observation()
    keys = tuple(sorted(OBSERVED_AC_REFS))
    for values in itertools.product((False, True), repeat=len(keys)):
        observation["facts"]["preserved_ac"] = dict(zip(keys, values, strict=True))
        result = _evaluate(observation)
        assert result["observed_ac_values"] == observation["facts"]["preserved_ac"]
        assert all(type(value) is bool for value in result["observed_ac_values"].values())
        assert result["unresolved_inputs"] == OWNER_HOLDS


@pytest.mark.parametrize(
    "mutation",
    ["owner", "status", "overlap", "numeric_fact", "numeric_hold"],
)
def test_owner_status_mismatch_fact_hold_overlap_and_numeric_fill_fail_closed(mutation):
    observation = _observation()
    if mutation == "owner":
        observation["owner_holds"]["C-L3.4:AC2"]["owner_ref"] = "owner:substituted"
    elif mutation == "status":
        observation["owner_holds"]["C-L3.4:AC2"]["status"] = "resolved"
    elif mutation == "overlap":
        observation["owner_holds"]["C-L3.4:AC1"] = {
            "owner_ref": "owner:invented",
            "status": "no_value_and_owner_hold",
        }
    elif mutation == "numeric_fact":
        observation["facts"]["preserved_ac"]["C-L3.4:AC1"] = 1
    else:
        observation["owner_holds"]["C-L3.4:AC2"]["value"] = 0
    _assert_rejected(_canonical(observation))


def test_invented_final_value_inputs_fail_closed():
    for field, value in (
        ("target_ac_values", {"AC14": 1}),
        ("criteria_values", {"benefit": 1}),
        ("score", 1),
        ("disposition", "PASS"),
        ("confirm", True),
        ("revert", False),
    ):
        observation = _observation()
        observation[field] = value
        _assert_rejected(_canonical(observation))


def test_duplicate_additional_missing_malformed_and_noncanonical_input_fail_closed():
    observation = _observation()
    canonical = _canonical(observation)
    duplicate = canonical.replace(
        b'"schema":"harness.l3-ac14-source-observation.v1"',
        b'"schema":"harness.l3-ac14-source-observation.v1","schema":"harness.l3-ac14-source-observation.v1"',
        1,
    )
    additional = copy.deepcopy(observation)
    additional["additional"] = False
    missing = copy.deepcopy(observation)
    del missing["facts"]
    for stdin in (
        duplicate,
        _canonical(additional),
        _canonical(missing),
        b"\xff\n",
        b"{malformed}\n",
        json.dumps(observation, ensure_ascii=False).encode("utf-8") + b"\n",
        canonical.removesuffix(b"\n"),
        canonical + b"\n",
        canonical + b"x",
        canonical.replace(b"true", b"NaN", 1),
    ):
        _assert_rejected(stdin)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("candidate_admission_digest", "1" * 64),
        ("pair_plan_digest", "sha256:" + "A" * 64),
        ("split_digest", "sha256:" + "1" * 63),
        ("model_configuration_digest", "sha256:" + "g" * 64),
        ("source_revision_ref", "sha256:" + "3" * 64),
        ("arm", "revert"),
        ("evaluation_split", "training"),
        ("evaluator_identity", "other-evaluator"),
        ("evaluator_configuration_digest", "sha256:" + "6" * 64),
        ("result_contract_ref", "other-contract"),
        ("result_contract_digest", "sha256:" + "7" * 64),
        ("target_ac_ref", "AC13"),
    ],
)
def test_wrong_binding_identity_constant_arm_or_split_fails_closed(field, value):
    observation = _observation()
    observation["binding"][field] = value
    _assert_rejected(_canonical(observation))


def test_evidence_refs_must_be_nonempty_bounded_sorted_and_unique():
    for evidence_refs in (
        [],
        [""],
        ["x" * 1025],
        ["source:z", "source:a"],
        ["source:a", "source:a"],
        "source:a",
    ):
        observation = _observation()
        observation["evidence_refs"] = evidence_refs
        _assert_rejected(_canonical(observation))


def test_additional_argv_and_environment_cannot_invent_results():
    stdin = _canonical(_observation())
    for argv in (("1",), ("--score=1",), ("--expected-result=revert",)):
        _assert_rejected(stdin, *argv)
    expected = _run(stdin)
    environment = os.environ.copy()
    environment.update(
        {
            "SCORE": "1",
            "EXPECTED_RESULT": "PASS",
            "OWNER_HOLD": "resolved",
            "HARNESS_STATE_DIR": "/nonexistent",
        }
    )
    injected = _run(stdin, environment=environment)
    assert expected.returncode == injected.returncode == 0
    assert expected.stdout == injected.stdout
    assert expected.stderr == injected.stderr == b""


def test_same_input_bytes_produce_byte_identical_output():
    stdin = _canonical(_observation())
    first = _run(stdin)
    second = _run(stdin)
    assert first.returncode == second.returncode == 0
    assert first.stdout == second.stdout
    assert first.stderr == second.stderr == b""


def test_source_has_no_forbidden_access_or_alternate_policy():
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots = set()
    called_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported_roots.add((node.module or "").split(".", 1)[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called_names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called_names.add(node.func.attr)

    assert imported_roots <= {"__future__", "json", "re", "sys"}
    assert called_names.isdisjoint(
        {
            "open",
            "getenv",
            "getcwd",
            "listdir",
            "read_text",
            "read_bytes",
            "run",
            "Popen",
            "socket",
            "time",
            "now",
            "urandom",
        }
    )
    lowered = source.lower()
    for forbidden in (
        "subprocess",
        "pathlib",
        "socket",
        "requests",
        "urllib",
        "datetime",
        "random",
        "secrets",
        "hermes",
        "profile",
        "memory",
        "session",
        "fixture",
        "threshold",
        "confidence",
        "probability",
        "weight",
        "target_ac_values",
        "criteria_values",
        "non_inferiority",
        "score",
        "disposition",
        "promotion",
        "replay",
    ):
        assert forbidden not in lowered
    assert source.count("sys.stdin.buffer.read()") == 1
