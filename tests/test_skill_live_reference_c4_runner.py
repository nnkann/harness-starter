import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / ".harness/hermes/tools/skill_live_reference_c4_runner.py"
spec = importlib.util.spec_from_file_location("skill_live_reference_c4_runner", TOOL)
assert spec is not None and spec.loader is not None
runner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runner
spec.loader.exec_module(runner)


def unavailable_c2():
    return {
        "schema": runner.C2_SCHEMA,
        "result_id": "c2:native:unavailable",
        "source_receipt": "honcho-native:unavailable:test",
        "availability": "unavailable",
        "pointer_digest": None,
        "pointer_integrity": "unknown",
        "source_backed_conflicts": [],
        "verified_outcome_eligible": None,
    }


def test_c2_is_strict_and_cannot_manufacture_available_native_evidence():
    assert runner._validate_c2(unavailable_c2())["availability"] == "unavailable"
    for mutate in (
        lambda value: value.update(availability="available", pointer_digest="a" * 64, pointer_integrity="valid"),
        lambda value: value.update(source_backed_conflicts=[{"conflict_id": "fake"}]),
        lambda value: value.update(contract_fixture=True),
    ):
        value = unavailable_c2()
        mutate(value)
        with pytest.raises(runner.RunnerError):
            runner._validate_c2(value)


def test_state_dir_is_required_and_rejects_repo_and_brain_descendants(tmp_path):
    brain = tmp_path / "brain"
    brain.mkdir()
    for candidate in (None, ROOT / ".c4-state", brain / ".c4-state"):
        with pytest.raises(runner.RunnerError, match="HARNESS_STATE_DIR"):
            runner._external_state_dir(candidate, brain)


@pytest.mark.contract_fixture
def test_contract_fixture_dispatch_terminal_pair_and_clean_lane(tmp_path):
    brain = tmp_path / "harness-brain"
    source = brain / "projects/demo/skill.md"
    source.parent.mkdir(parents=True)
    source.write_text("canonical skill reference\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(brain)], check=True)
    subprocess.run(["git", "-C", str(brain), "add", "."], check=True)
    subprocess.run([
        "git", "-C", str(brain), "-c", "user.name=test",
        "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture",
    ], check=True)
    revision = subprocess.run(
        ["git", "-C", str(brain), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()

    gbrain = tmp_path / "gbrain"
    gbrain.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        "if sys.argv[1] == 'search':\n"
        "    print('[1.0000] projects/demo/skill.md -- candidate')\n"
        "elif sys.argv[1:3] == ['call', 'sources_status']:\n"
        f"    print(json.dumps({{'id':'harness-brain','local_path':{str(brain)!r},"
        f"'last_commit':{revision!r},'clone_state':'healthy'}}))\n"
        "else:\n"
        "    raise SystemExit(3)\n",
        encoding="utf-8",
    )
    gbrain.chmod(0o755)
    c2_path = tmp_path / "c2.json"
    c2_path.write_text(json.dumps(unavailable_c2()), encoding="utf-8")
    state = tmp_path / "external-state"

    summary, code = runner.execute(
        query="canonical skill reference",
        c2_artifact=c2_path,
        brain_root=brain,
        gbrain_executable=gbrain,
        state_dir=state,
        timeout=5,
    )

    assert code == 0
    dispatch = json.loads(Path(summary["dispatch_path"]).read_text())
    terminal = json.loads(Path(summary["terminal_path"]).read_text())
    assert dispatch["run_id"] == terminal["run_id"] == summary["run_id"]
    assert dispatch["linked_terminal_path"] == summary["terminal_path"]
    assert terminal["linked_dispatch_path"] == summary["dispatch_path"]
    assert terminal["source_trees_unchanged"] is True
    assert terminal["exit_code"] == 0
    assert terminal["lane"]["c1"]["canonical_revision"] == revision
    assert terminal["lane"]["c1"]["canonical_digest"]
    assert terminal["lane"]["c2"]["evidence_mode"] == "native"
    assert terminal["lane"]["c2"]["availability"] == "unavailable"
    assert terminal["lane"]["c2"]["provider_capability_boundary"]["invocation_scope_parameters"] == []
    assert terminal["lane"]["c3"]["clean"] is True
    assert terminal["lane"]["c3"]["delta"] is False
    assert terminal["lane"]["c3"]["sia_invoked"] is False
    assert terminal["conclusion"]["status"] == "partial"
    assert terminal["artifacts"]["body"]["readback_verified"] is True
    assert terminal["artifacts"]["stdout"]["readback_verified"] is True
    assert terminal["artifacts"]["stderr"]["readback_verified"] is True
