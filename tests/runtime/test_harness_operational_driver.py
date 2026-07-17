import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).parents[2] / "scripts" / "harness_operational_driver.py"
SPEC = importlib.util.spec_from_file_location("harness_operational_driver", SCRIPT)
assert SPEC and SPEC.loader
DRIVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DRIVER)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    source.mkdir(parents=True)
    (source / "test_sample.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    config_path = source / DRIVER.TEST_ENVIRONMENT_PATH
    config_path.parent.mkdir(parents=True)
    config = {
        "schema": DRIVER.TEST_ENVIRONMENT_SCHEMA,
        "runner_path": ".venv/bin/pytest",
        "expected_identity": "pytest",
        "expected_version": "8.4.2",
    }
    config_path.write_bytes(DRIVER._canonical_json(config) + b"\n")
    runner = source / ".venv/bin/pytest"
    runner.parent.mkdir(parents=True)
    runner.write_text("#!/usr/bin/python3\nfrom pytest import console_main\n", encoding="utf-8")
    runner.chmod(0o755)
    metadata = source / ".venv/lib/python3.11/site-packages/pytest-8.4.2.dist-info"
    metadata.mkdir(parents=True)
    (metadata / "METADATA").write_text("Name: pytest\nVersion: 8.4.2\n", encoding="utf-8")
    (metadata / "entry_points.txt").write_text("[console_scripts]\npytest = pytest:console_main\n", encoding="utf-8")
    return source


def _receipt(tmp_path: Path, source: Path, **changes) -> Path:
    body = {
        "schema": DRIVER.RECEIPT_SCHEMA,
        "task_ref": "kanban://tasks/task-17?opaque=true",
        "revision": "rev/α:0007",
        "source_root": str(source),
        "files": [{"path": "test_sample.py", "sha256": _digest(source / "test_sample.py")}],
        "focused_test_command": {"args": ["-q", "test_sample.py"]},
    }
    body.update(changes)
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(body, sort_keys=True), encoding="utf-8")
    return path


def _result(returncode=0, stdout="ok\n", stderr=""):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def test_opaque_correlation_fields_pass_through_without_receipt_or_goal_ac_material(tmp_path, monkeypatch):
    source = _source(tmp_path)
    path = _receipt(tmp_path, source)
    raw = path.read_bytes()
    monkeypatch.setattr(DRIVER.subprocess, "run", lambda *args, **kwargs: _result())

    packet = DRIVER.run(path)

    assert packet["task_ref"] == "kanban://tasks/task-17?opaque=true"
    assert packet["revision"] == "rev/α:0007"
    assert "receipt" not in packet
    assert packet["evidence"]["scope_receipt_sha256"] == hashlib.sha256(raw).hexdigest()
    rendered = json.dumps(packet, sort_keys=True)
    assert "goal_ac_body" not in rendered
    assert "goal_ac_body_sha256" not in rendered
    assert "Goal:" not in rendered
    assert "AC:" not in rendered


def test_correlation_only_receipt_is_rejected(tmp_path):
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps({"task_ref": "task-17", "revision": "7"}), encoding="utf-8")
    packet = DRIVER.run(path)
    assert packet["status"] == "failure"
    assert packet["phase"] == "receipt"
    assert "full scope receipt" in packet["error"]["message"]


def test_receipt_files_and_command_are_each_consumed_once(tmp_path, monkeypatch):
    source = _source(tmp_path)
    path = _receipt(tmp_path, source)
    reads = []
    executions = []
    original = DRIVER._read_once

    def read_once(candidate):
        reads.append(Path(candidate))
        return original(candidate)

    def execute(argv, **kwargs):
        executions.append((argv, kwargs))
        return _result()

    monkeypatch.setattr(DRIVER, "_read_once", read_once)
    monkeypatch.setattr(DRIVER.subprocess, "run", execute)
    packet = DRIVER.run(path)

    assert packet["status"] == "success"
    assert reads == [
        path,
        source / DRIVER.TEST_ENVIRONMENT_PATH,
        source / ".venv/bin/pytest",
        source / ".venv/lib/python3.11/site-packages/pytest-8.4.2.dist-info/METADATA",
        source / ".venv/lib/python3.11/site-packages/pytest-8.4.2.dist-info/entry_points.txt",
        source / "test_sample.py",
    ]
    assert len(executions) == 1
    argv, kwargs = executions[0]
    assert argv == [str((source / ".venv/bin/pytest").resolve()), "-q", "test_sample.py"]
    assert argv == packet["evidence"]["final_argv"]
    assert kwargs["shell"] is False


@pytest.mark.parametrize("mutation", ["unknown", "missing", "noncanonical", "identity", "version"])
def test_noncanonical_test_environment_is_rejected_without_execution(tmp_path, monkeypatch, mutation):
    source = _source(tmp_path)
    config_path = source / DRIVER.TEST_ENVIRONMENT_PATH
    config = json.loads(config_path.read_bytes())
    if mutation == "unknown":
        config["extra"] = True
    elif mutation == "missing":
        del config["runner_path"]
    elif mutation == "identity":
        config["expected_identity"] = "py.test"
    elif mutation == "version":
        config["expected_version"] = "8.4.1"
    if mutation == "noncanonical":
        config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    else:
        config_path.write_bytes(DRIVER._canonical_json(config) + b"\n")
    called = []
    monkeypatch.setattr(DRIVER.subprocess, "run", lambda *args, **kwargs: called.append(args))

    packet = DRIVER.run(_receipt(tmp_path, source))

    assert packet["status"] == "failure"
    assert packet["phase"] == "test_environment"
    assert called == []


@pytest.mark.parametrize("condition", ["symlink", "outside", "nonexecutable"])
def test_runner_must_be_root_contained_non_symlink_and_executable(tmp_path, monkeypatch, condition):
    source = _source(tmp_path)
    config_path = source / DRIVER.TEST_ENVIRONMENT_PATH
    runner = source / ".venv/bin/pytest"
    if condition == "symlink":
        runner.unlink()
        runner.symlink_to("/usr/bin/true")
    elif condition == "outside":
        config = json.loads(config_path.read_bytes())
        config["runner_path"] = "../pytest"
        config_path.write_bytes(DRIVER._canonical_json(config) + b"\n")
    else:
        runner.chmod(0o644)
    called = []
    monkeypatch.setattr(DRIVER.subprocess, "run", lambda *args, **kwargs: called.append(args))

    packet = DRIVER.run(_receipt(tmp_path, source))

    assert packet["status"] == "failure"
    assert packet["phase"] == "test_environment"
    assert called == []


@pytest.mark.parametrize("command", [
    {"argv": ["/usr/bin/pytest", "test_sample.py"]},
    {"args": ["pytest", "test_sample.py"]},
    {"args": ["-m", "pytest", "test_sample.py"]},
    {"args": ["--pyargs", "sample"]},
])
def test_receipt_executables_and_wrappers_are_rejected(tmp_path, monkeypatch, command):
    called = []
    monkeypatch.setattr(DRIVER.subprocess, "run", lambda *args, **kwargs: called.append(args))
    packet = DRIVER.run(_receipt(tmp_path, _source(tmp_path), focused_test_command=command))
    assert packet["status"] == "failure"
    assert packet["phase"] == "receipt"
    assert called == []


def test_packet_contains_canonical_config_runner_verification_and_final_argv(tmp_path, monkeypatch):
    source = _source(tmp_path)
    config_path = source / DRIVER.TEST_ENVIRONMENT_PATH
    monkeypatch.setattr(DRIVER.subprocess, "run", lambda *args, **kwargs: _result())

    packet = DRIVER.run(_receipt(tmp_path, source))
    evidence = packet["evidence"]

    assert evidence["test_environment"]["bytes_utf8"].encode() == config_path.read_bytes()
    assert evidence["test_environment"]["sha256"] == _digest(config_path)
    assert evidence["runner"]["relative_path"] == ".venv/bin/pytest"
    assert evidence["runner"]["absolute_path"] == str((source / ".venv/bin/pytest").resolve())
    assert evidence["runner"]["verified_identity"] == "pytest"
    assert evidence["runner"]["verified_version"] == "8.4.2"
    assert evidence["final_argv"] == [str((source / ".venv/bin/pytest").resolve()), "-q", "test_sample.py"]


def test_no_packaging_subprocess_or_packaging_branch_exists(tmp_path, monkeypatch):
    path = _receipt(tmp_path, _source(tmp_path))
    commands = []

    def execute(argv, **kwargs):
        commands.append(argv)
        return _result()

    monkeypatch.setattr(DRIVER.subprocess, "run", execute)
    DRIVER.run(path)
    assert len(commands) == 1
    assert not {"build", "wheel", "venv", "pip", "install"}.intersection(commands[0])
    source = SCRIPT.read_text(encoding="utf-8")
    assert "artifact_mode" not in source
    assert "cache_root" not in source


@pytest.mark.parametrize("returncode,status", [(0, "success"), (2, "failure")])
def test_success_and_failure_packets(tmp_path, monkeypatch, returncode, status):
    path = _receipt(tmp_path, _source(tmp_path))
    monkeypatch.setattr(
        DRIVER.subprocess, "run",
        lambda *args, **kwargs: _result(returncode, "captured stdout", "captured stderr"),
    )
    packet = DRIVER.run(path)
    execution = packet["evidence"]["execution"]
    assert packet["status"] == status
    assert packet["phase"] == "focused_test"
    assert execution["exit_code"] == returncode
    assert execution["stdout"] == "captured stdout"
    assert execution["stderr"] == "captured stderr"
    assert execution["duration_ns"] >= 0
    assert packet["cleanup_status"] == "removed"
    assert packet["evidence_retention"] == {"location": "packet.evidence", "until": "maat_close"}


def test_timeout_packet_captures_partial_output_and_cleanup(tmp_path, monkeypatch):
    path = _receipt(tmp_path, _source(tmp_path))

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"], output=b"partial out", stderr=b"partial err")

    monkeypatch.setattr(DRIVER.subprocess, "run", timeout)
    packet = DRIVER.run(path)
    execution = packet["evidence"]["execution"]
    assert packet["status"] == "timeout"
    assert execution["stdout"] == "partial out"
    assert execution["stderr"] == "partial err"
    assert execution["timeout_seconds"] == DRIVER.FOCUSED_TEST_TIMEOUT_SECONDS
    assert packet["cleanup_status"] == "removed"


def test_snapshot_failure_packet_and_cleanup(tmp_path, monkeypatch):
    source = _source(tmp_path)
    path = _receipt(tmp_path, source)
    (source / "test_sample.py").write_text("changed", encoding="utf-8")
    roots = []
    original = DRIVER.tempfile.mkdtemp

    def tracked(*args, **kwargs):
        root = Path(original(*args, **kwargs))
        roots.append(root)
        return str(root)

    monkeypatch.setattr(DRIVER.tempfile, "mkdtemp", tracked)
    packet = DRIVER.run(path)
    assert packet["status"] == "failure"
    assert packet["phase"] == "snapshot"
    assert packet["cleanup_status"] == "removed"
    assert len(roots) == 1 and not roots[0].exists()


def test_cleanup_failure_packet_preserves_execution_evidence(tmp_path, monkeypatch):
    path = _receipt(tmp_path, _source(tmp_path))
    monkeypatch.setattr(DRIVER.subprocess, "run", lambda *args, **kwargs: _result())
    monkeypatch.setattr(DRIVER.shutil, "rmtree", lambda path: (_ for _ in ()).throw(OSError("private")))
    packet = DRIVER.run(path)
    assert packet["status"] == "failure"
    assert packet["phase"] == "cleanup"
    assert packet["evidence"]["execution"]["outcome"] == "success"
    assert packet["cleanup_status"] == "failed"
    assert packet["cleanup_error"] == {"type": "OSError", "message": "ephemeral work cleanup failed"}


def test_main_emits_one_packet_and_nonzero_for_failure(tmp_path, capsys):
    code = DRIVER.main(["--scope-receipt", str(tmp_path / "missing.json")])
    lines = capsys.readouterr().out.splitlines()
    assert code == 1
    assert len(lines) == 1
    assert json.loads(lines[0])["recipients"] == ["anubis", "maat"]
