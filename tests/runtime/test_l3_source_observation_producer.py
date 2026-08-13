import ast
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


MODULE_PATH = (
    Path(__file__).parents[2]
    / "runtime"
    / "harness_runtime"
    / "l3_source_observation_producer.py"
)
PROJECT_ROOT = MODULE_PATH.parents[2]
TARGET_PATHS = (
    "contracts/execution-receipt.v1.schema.json",
    "runtime/harness_runtime/runtime.py",
    "tests/runtime/test_runtime_contract.py",
)
DECLARATION_REF = "C-L3.5-PE2/D-CURRENT-2026-08-09"
BASELINE_REVISION_REF = (
    "source-manifest:sha256:06f214e8971bc934a3829dc7ac07f35ac2d522945b5aa2cbe4831a5493642d89"
)

MODEL_IDENTITY = "C-L3.4-receipt-backed-paired-runtime"
MODEL_CONFIGURATION_DIGEST = (
    "sha256:1a2e1302ee243aff4237597118377cc28b835690fccacc6587942dcb7d311008"
)
SAMPLING_IDENTITY = "canonical-exhaustive-four-cell-plus-declared-denial-boundaries"
IDENTITY_INPUT_FIELDS = (
    "arm",
    "source_revision_ref",
    "evaluation_split",
    "split_ref",
    "split_digest",
    "model_identity",
    "model_configuration_digest",
    "sampling_identity",
)


def _cell_identity(cell: dict) -> str:
    inputs = {field: cell[field] for field in IDENTITY_INPUT_FIELDS}
    canonical = json.dumps(
        inputs, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8") + b"\n"
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def _candidate_projection(root: Path = PROJECT_ROOT) -> tuple[dict[str, str], str]:
    manifest = {
        relative: hashlib.sha256((root / relative).read_bytes()).hexdigest()
        for relative in TARGET_PATHS
    }
    canonical = json.dumps(
        manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8") + b"\n"
    revision = "source-manifest:sha256:" + hashlib.sha256(canonical).hexdigest()
    return manifest, revision


CANDIDATE_MANIFEST, CANDIDATE_REVISION_REF = _candidate_projection()


CELLS = {
    "baseline/held_in": {
        "arm": "baseline",
        "source_revision_ref": BASELINE_REVISION_REF,
        "evaluation_split": "held_in",
        "split_ref": "packet:C-L3.4#AC14:fresh-valid-chain",
        "split_digest": "sha256:130457b452647ac9bd236c4cb407e7264c8fb952389767740a7070cb3c3c5fec",
    },
    "baseline/held_out": {
        "arm": "baseline",
        "source_revision_ref": BASELINE_REVISION_REF,
        "evaluation_split": "held_out",
        "split_ref": "packet:C-L3.4#fail-closed-boundaries",
        "split_digest": "sha256:bfbe5cc7c7ee3582808bff92418a239277ea5e70271476fb2d97fcc5ebc6543a",
    },
    "candidate/held_in": {
        "arm": "candidate",
        "source_revision_ref": CANDIDATE_REVISION_REF,
        "evaluation_split": "held_in",
        "split_ref": "packet:C-L3.4#AC14:fresh-valid-chain",
        "split_digest": "sha256:130457b452647ac9bd236c4cb407e7264c8fb952389767740a7070cb3c3c5fec",
    },
    "candidate/held_out": {
        "arm": "candidate",
        "source_revision_ref": CANDIDATE_REVISION_REF,
        "evaluation_split": "held_out",
        "split_ref": "packet:C-L3.4#fail-closed-boundaries",
        "split_digest": "sha256:bfbe5cc7c7ee3582808bff92418a239277ea5e70271476fb2d97fcc5ebc6543a",
    },
}
for _cell in CELLS.values():
    _cell.update(
        model_identity=MODEL_IDENTITY,
        model_configuration_digest=MODEL_CONFIGURATION_DIGEST,
        sampling_identity=SAMPLING_IDENTITY,
    )
    _cell["cell_identity"] = _cell_identity(_cell)
PHASE_1_REFS = {"C-L3.4:AC1", "C-L3.4:AC3", "C-L3.4:AC4"}


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8") + b"\n"


def _selector(cell_name: str = "candidate/held_in") -> dict:
    return {
        "schema": "harness.l3-source-native-cell-observation.v1",
        "declaration_ref": DECLARATION_REF,
        "cell": cell_name,
    }


def _run(stdin: bytes, *argv: str):
    return subprocess.run(
        [sys.executable, str(MODULE_PATH), *argv],
        input=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _load_producer_module():
    spec = importlib.util.spec_from_file_location(
        "direct_source_observation_producer_under_test", MODULE_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_runtime_test_module():
    path = PROJECT_ROOT / "tests/runtime/test_runtime_contract.py"
    spec = importlib.util.spec_from_file_location("runtime_contract_helpers", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _copy_producer_tree(tmp_path: Path) -> Path:
    for relative in (*TARGET_PATHS, "runtime/harness_runtime/l3_source_observation_producer.py"):
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PROJECT_ROOT / relative, destination)
    return tmp_path / "runtime/harness_runtime/l3_source_observation_producer.py"


def _run_copied(producer_path: Path, stdin: bytes):
    return subprocess.run(
        [sys.executable, str(producer_path), "--stdin-only"],
        input=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _assert_rejected(value: object) -> None:
    completed = _run(_canonical(value), "--stdin-only")
    assert completed.returncode == 2
    assert completed.stdout == b""


@pytest.mark.parametrize("cell_name", CELLS)
def test_phase1_selector_only_input_is_the_complete_factual_contract(cell_name):
    completed = _run(_canonical(_selector(cell_name)), "--stdin-only")

    assert completed.returncode == 0
    assert completed.stderr == b""
    result = json.loads(completed.stdout)
    assert completed.stdout == _canonical(result)
    assert set(result) == {
        "schema", "declaration_ref", "candidate_source_revision", "cell", "facts"
    }
    assert result["declaration_ref"] == DECLARATION_REF
    assert result["cell"] == {
        "cell": cell_name,
        **CELLS[cell_name],
        "model_identity": MODEL_IDENTITY,
        "model_configuration_digest": MODEL_CONFIGURATION_DIGEST,
        "sampling_identity": SAMPLING_IDENTITY,
    }
    assert result["facts"] == {
        "source_native_preserved_ac": {ref: True for ref in sorted(PHASE_1_REFS)}
    }


def test_revised_candidate_manifest_and_identity_are_directly_projected_from_current_target_bytes():
    observed = {
        relative: hashlib.sha256((PROJECT_ROOT / relative).read_bytes()).hexdigest()
        for relative in TARGET_PATHS
    }
    assert observed == CANDIDATE_MANIFEST
    assert (
        "source-manifest:sha256:" + hashlib.sha256(_canonical(observed)).hexdigest()
        == CANDIDATE_REVISION_REF
    )

    producer = _load_producer_module()
    assert producer._observe_candidate_manifest() == (CANDIDATE_MANIFEST, CANDIDATE_REVISION_REF)

    completed = _run(_canonical(_selector()), "--stdin-only")
    result = json.loads(completed.stdout)
    assert result["candidate_source_revision"] == {
        "manifest": CANDIDATE_MANIFEST,
        "revision_ref": CANDIDATE_REVISION_REF,
    }


def test_changed_target_bytes_project_a_new_manifest_revision_and_candidate_identity(tmp_path):
    producer_path = _copy_producer_tree(tmp_path)
    before = json.loads(
        _run_copied(producer_path, _canonical(_selector())).stdout
    )
    target = tmp_path / "runtime/harness_runtime/runtime.py"
    target.write_bytes(target.read_bytes() + b"\n# changed candidate byte\n")
    manifest, revision = _candidate_projection(tmp_path)

    completed = _run_copied(producer_path, _canonical(_selector()))
    assert completed.returncode == 0
    result = json.loads(completed.stdout)
    assert revision != before["candidate_source_revision"]["revision_ref"]
    assert result["candidate_source_revision"] == {
        "manifest": manifest,
        "revision_ref": revision,
    }
    assert result["cell"]["source_revision_ref"] == revision
    assert result["cell"]["cell_identity"] == _cell_identity(result["cell"])


@pytest.mark.parametrize("target_relative", TARGET_PATHS)
@pytest.mark.parametrize("failure", ["missing", "tampered"])
def test_missing_or_tampered_target_source_fails_closed(
    tmp_path, target_relative, failure
):
    producer_path = _copy_producer_tree(tmp_path)
    target = tmp_path / target_relative
    if failure == "missing":
        target.unlink()
    else:
        target.unlink()
        target.symlink_to(PROJECT_ROOT / target_relative)

    completed = _run_copied(producer_path, _canonical(_selector()))
    assert completed.returncode == 2
    assert completed.stdout == b""
    assert completed.stderr == b""


@pytest.mark.parametrize("cell_name", ("candidate/held_in", "candidate/held_out"))
def test_revised_candidate_identity_flows_from_real_producer_into_runtime_constructor(
    monkeypatch, cell_name
):
    runtime_test = _load_runtime_test_module()
    plan, trusted = runtime_test._l35_context_bound_to_real_source_producer()
    admission = trusted["candidate_admission"]
    admission["candidate"]["identity"] = CANDIDATE_REVISION_REF
    admission["candidate"]["allowed_write_refs"] = sorted(CANDIDATE_MANIFEST)
    admission_digest = runtime_test._canonical_digest(admission)
    packet = trusted["executor_packet"]
    packet["source_refs"] = [admission["candidate_ref"], admission_digest]
    packet["allowed_write_refs"] = sorted(CANDIDATE_MANIFEST)
    packet_digest = runtime_test._canonical_digest(packet)
    plan["source_revision_projection"]["candidate"] = {
        "revision_ref": CANDIDATE_REVISION_REF,
        "manifest": CANDIDATE_MANIFEST,
    }
    plan["candidate_revision_ref"] = CANDIDATE_REVISION_REF
    plan["candidate_admission_digest"] = admission_digest
    plan["executor_packet_digest"] = packet_digest
    plan["decision_observation"]["targeted_change"] = {
        "ref": CANDIDATE_REVISION_REF,
        "sha256": "sha256:" + CANDIDATE_REVISION_REF.removeprefix("source-manifest:sha256:"),
    }
    trusted["expected_candidate_admission_digest"] = admission_digest
    trusted["expected_executor_packet_digest"] = packet_digest
    trusted["expected_pair_plan_digest"] = runtime_test._canonical_digest(plan)

    completed = _run(_canonical(_selector(cell_name)), "--stdin-only")
    assert completed.returncode == 0 and completed.stderr == b""
    split = cell_name.removeprefix("candidate/")
    chain = runtime_test._l35_source_chain(
        plan=plan,
        trusted=trusted,
        cell={"arm": "candidate", "evaluation_split": split},
    )
    chain["source_output"] = completed.stdout
    output_digest = hashlib.sha256(completed.stdout).hexdigest()
    terminal = json.loads(chain["source_terminal_receipt"])
    terminal["artifacts"]["stdout"].update(
        sha256=output_digest, bytes=len(completed.stdout)
    )
    chain["source_terminal_receipt"] = runtime_test._persisted_receipt_line(terminal)
    chain["readback_projection"]["artifacts"] = terminal["artifacts"]
    chain["readback_projection"]["output_sha256"] = "sha256:" + output_digest
    chain["readback_projection"]["terminal_receipt_sha256"] = (
        "sha256:" + hashlib.sha256(chain["source_terminal_receipt"]).hexdigest()
    )
    chain["source_readback_projection"] = runtime_test._canonical_line(
        chain["readback_projection"]
    )

    def unexpected_launch(*args, **kwargs):
        raise AssertionError("evaluator or PE2 must not launch")

    monkeypatch.setattr(runtime_test.runtime_module.subprocess, "run", unexpected_launch)
    observation = json.loads(
        runtime_test.runtime_module._construct_l35_source_observation(
            source_case_id=chain["source_case_id"],
            evaluator_case_id=chain["evaluator_case_id"],
            source_output=chain["source_output"],
            source_dispatch_receipt=chain["source_dispatch_receipt"],
            source_terminal_receipt=chain["source_terminal_receipt"],
            source_readback_projection=chain["source_readback_projection"],
            pair_plan=plan,
            paired_cell=chain["cell"],
            **trusted,
        )
    )
    assert observation["binding"]["source_revision_ref"] == CANDIDATE_REVISION_REF
    assert observation["facts"] == {
        "preserved_ac": {ref: True for ref in sorted(PHASE_1_REFS)}
    }
    assert observation["owner_holds"] == runtime_test._L35_OWNER_HOLDS
    serialized = _canonical(observation).decode()
    for forbidden in (
        "false",
        "evaluator_result",
        "target_ac_values",
        "criteria_values",
        "score",
        "disposition",
    ):
        assert forbidden not in serialized


def test_runtime_rejects_recomputed_identity_after_any_identity_input_mutation():
    runtime_test = _load_runtime_test_module()
    runtime = runtime_test.runtime_module
    for cell_name in ("candidate/held_in", "candidate/held_out"):
        completed = _run(_canonical(_selector(cell_name)), "--stdin-only")
        assert completed.returncode == 0
        produced = json.loads(completed.stdout)
        expected = dict(produced["cell"])
        for field in IDENTITY_INPUT_FIELDS:
            substituted = json.loads(completed.stdout)
            substituted["cell"][field] += ":mutated"
            substituted["cell"]["cell_identity"] = _cell_identity(
                substituted["cell"]
            )
            with pytest.raises(runtime_test.ReceiptValidationError):
                runtime._validate_l35_source_producer_result(
                    _canonical(substituted), expected
                )


def test_exact_phase1_keys_only_and_no_later_ac_is_emitted():
    result = json.loads(_run(_canonical(_selector()), "--stdin-only").stdout)
    assert set(result["facts"]) == {"source_native_preserved_ac"}
    assert set(result["facts"]["source_native_preserved_ac"]) == PHASE_1_REFS
    serialized = _canonical(result).decode()
    for number in (2, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14):
        assert f'C-L3.4:AC{number}"' not in serialized


def test_phase1_rejects_caller_observations_booleans_controls_paths_refs_and_projection():
    forbidden_payloads = [
        {"observations": {"C-L3.4:AC1": True}},
        {"producer_observed": True},
        {"observed_controls": {}},
        {"changed_paths": []},
        {"evidence_refs": ["source:fabricated"]},
        {"fact_projection": {"C-L3.4:AC1": True}},
    ]
    for payload in forbidden_payloads:
        _assert_rejected({**_selector(), **payload})


def test_changing_rejected_caller_fact_payload_cannot_change_emitted_facts():
    expected = json.loads(_run(_canonical(_selector()), "--stdin-only").stdout)["facts"]
    for claimed in (False, True):
        completed = _run(
            _canonical({**_selector(), "observations": {"C-L3.4:AC1": claimed}}),
            "--stdin-only",
        )
        assert completed.returncode == 2
        assert completed.stdout == b""
    assert json.loads(_run(_canonical(_selector()), "--stdin-only").stdout)["facts"] == expected


def test_completed_candidate_bound_projections_are_the_only_fact_authority():
    producer = _load_producer_module()
    exact = producer._produce(_selector())
    assert exact["facts"] == {
        "source_native_preserved_ac": {ref: True for ref in PHASE_1_REFS}
    }
    assert "source_evidence_refs" not in exact
    with pytest.raises(ValueError):
        producer._produce(
            {**_selector(), "observations": {"C-L3.4:AC1": True}}
        )


def test_only_sealed_declaration_and_declared_string_cell_selectors_are_accepted():
    wrong_declaration = _selector()
    wrong_declaration["declaration_ref"] = "caller-declaration"
    full_cell = _selector()
    full_cell["cell"] = {"cell": "candidate/held_in", **CELLS["candidate/held_in"]}
    for value in (
        wrong_declaration,
        full_cell,
        {**_selector(), "cell": "candidate/unknown"},
        {**_selector(), "cell": 1},
        {**_selector(), "schema": "caller-schema"},
    ):
        _assert_rejected(value)


def test_producer_mints_no_evidence_ref_or_non_phase1_assertion():
    result = json.loads(_run(_canonical(_selector()), "--stdin-only").stdout)
    assert set(result["facts"]["source_native_preserved_ac"]) == PHASE_1_REFS
    serialized = _canonical(result).decode()
    for forbidden in (
        "source_evidence_refs",
        "direct_target_observation",
        "control_surfaces_non_regressed",
        "material_semantic_regression_observed",
        "unresolved_uncertainty_observed",
    ):
        assert forbidden not in serialized


def test_noncanonical_duplicate_malformed_or_wrong_argv_has_no_result():
    canonical = _canonical(_selector())
    duplicate = canonical.replace(
        b'"schema":"harness.l3-source-native-cell-observation.v1"',
        b'"schema":"harness.l3-source-native-cell-observation.v1","schema":"harness.l3-source-native-cell-observation.v1"',
        1,
    )
    for stdin, argv in (
        (canonical.removesuffix(b"\n"), ("--stdin-only",)),
        (canonical + b"\n", ("--stdin-only",)),
        (duplicate, ("--stdin-only",)),
        (b"{malformed}\n", ("--stdin-only",)),
        (canonical, ()),
        (canonical, ("--stdin-only", "--score=1")),
    ):
        completed = _run(stdin, *argv)
        assert completed.returncode != 0
        assert completed.stdout == b""


def test_default_runtime_test_sources_do_not_reference_historical_global_tmp_artifacts():
    historical_artifact_names = (
        "c-l3-0b-r3-live-cohort-candidate.json",
        "maat-c-l3-4-e1-admitted-candidate.json",
    )

    source_under_test = Path(__file__).resolve()
    for source_path in (PROJECT_ROOT / "tests/runtime").glob("test_*.py"):
        if source_path.resolve() == source_under_test:
            continue
        source = source_path.read_text(encoding="utf-8")
        assert all(name not in source for name in historical_artifact_names)


def test_project_entry_point_and_source_use_only_declaration_bound_reads_and_stdin():
    pyproject = (MODULE_PATH.parents[2] / "pyproject.toml").read_text(encoding="utf-8")
    assert (
        'source-observation-producer = "harness_runtime.l3_source_observation_producer:main"'
        in pyproject
    )
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    called_names = {
        node.func.id if isinstance(node.func, ast.Name) else node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, (ast.Name, ast.Attribute))
    }
    assert imported_roots <= {"__future__", "hashlib", "json", "os", "stat", "sys", "pathlib"}
    assert called_names.isdisjoint(
        {"getenv", "getcwd", "read_text", "Popen", "socket"}
    )
    assert {"read_text", "run", "Popen", "socket"}.isdisjoint(called_names)
    assert source.count("sys.stdin.buffer.read()") == 1
