import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from harness_runtime import ReceiptValidationError, __version__, analysis_input, execute, readback, schema_text
from harness_runtime.cli import main as cli_main


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
