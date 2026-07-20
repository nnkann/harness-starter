import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

import harness_runtime.sandbox as sandbox_module
from harness_runtime.binding_cli import main as binding_cli
from harness_runtime.project_binding import (
    BindingError,
    BindingInputs,
    apply_binding,
    inspect_binding,
    plan_binding,
    reconcile_legacy,
)
from harness_runtime.sandbox import SandboxError, build_sandbox_argv, build_sandbox_profile, prepare_sandbox, run_sandbox

ROOT = Path(__file__).parents[2]


def git_repo(path: Path) -> Path:
    path.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True)
    (path / "README.md").write_text("project\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "README.md"], check=True)
    subprocess.run(
        [
            "git", "-C", str(path), "-c", "user.name=Harness Test",
            "-c", "user.email=harness@example.invalid", "commit", "-qm", "initial",
        ],
        check=True,
    )
    return path


def inputs(repo: Path, *, version: str = "1") -> BindingInputs:
    return BindingInputs(
        project_id="project-test",
        project_root=repo,
        protected_branch="main",
        railway_service="service-test",
        runtime_version=version,
    )


def test_first_bind_creates_minimal_managed_binding(tmp_path):
    repo = git_repo(tmp_path / "project")

    before = inspect_binding(repo)
    planned = plan_binding(inputs(repo))
    applied = apply_binding(inputs(repo))

    assert before["status"] == "unbound"
    assert [action["operation"] for action in planned["actions"]] == ["create", "create", "create", "create"]
    assert applied["changed"] is True
    manifest = json.loads((repo / ".harness/project-binding.json").read_text(encoding="utf-8"))
    assert manifest["project"] == {
        "id": "project-test",
        "root": str(repo.resolve()),
        "protected_branch": "main",
        "railway_service": "service-test",
    }
    assert manifest["runtime_lock"] == {
        "path": ".harness/runtime.lock.json",
        "version": "1",
        "digest": json.loads((repo / ".harness/runtime.lock.json").read_text(encoding="utf-8"))["digest"],
    }
    assert manifest["verification"] == {
        "clean_worktree_required": True,
        "external_state_dir_required": True,
        "sandbox_backend": "macos-sandbox-exec",
        "network_default": "deny",
    }
    managed = manifest["managed_files"]
    assert managed == [
        ".harness/bin/harness-binding",
        ".harness/bin/harness-sandbox-run",
        ".harness/project-binding.json",
        ".harness/runtime.lock.json",
    ]
    assert (repo / ".harness/bin/harness-binding").stat().st_mode & 0o111
    assert (repo / ".harness/bin/harness-sandbox-run").stat().st_mode & 0o111


def test_reapply_is_noop_and_runtime_version_upgrade_is_managed(tmp_path):
    repo = git_repo(tmp_path / "project")
    apply_binding(inputs(repo))

    noop = apply_binding(inputs(repo))
    upgrade = plan_binding(inputs(repo, version="2"))
    applied = apply_binding(inputs(repo, version="2"))

    assert noop["changed"] is False
    assert {action["operation"] for action in noop["actions"]} == {"noop"}
    assert [(action["path"], action["operation"]) for action in upgrade["actions"]] == [
        (".harness/bin/harness-binding", "noop"),
        (".harness/bin/harness-sandbox-run", "noop"),
        (".harness/project-binding.json", "update"),
        (".harness/runtime.lock.json", "update"),
    ]
    assert applied["changed"] is True
    assert inspect_binding(repo)["status"] == "bound"
    assert json.loads((repo / ".harness/runtime.lock.json").read_text(encoding="utf-8"))["version"] == "2"


def test_plan_does_not_mutate_unbound_target(tmp_path):
    repo = git_repo(tmp_path / "project")
    before = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=all"],
        check=True, text=True, capture_output=True,
    ).stdout

    result = plan_binding(inputs(repo))

    after = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=all"],
        check=True, text=True, capture_output=True,
    ).stdout
    assert result["changed"] is True
    assert before == after == ""
    assert not (repo / ".harness").exists()


def test_apply_refuses_to_overwrite_unmanaged_binding_path(tmp_path):
    repo = git_repo(tmp_path / "project")
    user_file = repo / ".harness/bin/harness-binding"
    user_file.parent.mkdir(parents=True)
    user_file.write_text("user launcher\n", encoding="utf-8")

    with pytest.raises(BindingError, match="refusing to overwrite unmanaged files"):
        apply_binding(inputs(repo))

    assert user_file.read_text(encoding="utf-8") == "user launcher\n"
    assert not (repo / ".harness/project-binding.json").exists()


def test_legacy_reconciliation_removes_only_manifest_owned_unchanged_files(tmp_path):
    repo = git_repo(tmp_path / "project")
    managed = repo / ".claude/skills/legacy/SKILL.md"
    modified = repo / ".agents/skills/legacy/SKILL.md"
    arbitrary = repo / "docs/user.md"
    for path, content in ((managed, b"managed\n"), (modified, b"changed\n"), (arbitrary, b"user\n")):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    legacy_manifest = repo / ".harness/legacy-files.json"
    legacy_manifest.parent.mkdir(parents=True)
    legacy_manifest.write_text(json.dumps({
        "managed_by": "harness-project-binding",
        "files": {
            ".claude/skills/legacy/SKILL.md": hashlib.sha256(b"managed\n").hexdigest(),
            ".agents/skills/legacy/SKILL.md": hashlib.sha256(b"original\n").hexdigest(),
        },
    }), encoding="utf-8")

    plan = reconcile_legacy(repo, apply=False)
    assert managed.exists()
    assert [action["operation"] for action in plan["actions"]] == ["remove", "retain-modified"]

    result = reconcile_legacy(repo, apply=True)
    assert result["changed"] is True
    assert not managed.exists()
    assert modified.read_bytes() == b"changed\n"
    assert arbitrary.read_bytes() == b"user\n"
    remaining = json.loads(legacy_manifest.read_text(encoding="utf-8"))
    assert list(remaining["files"]) == [".agents/skills/legacy/SKILL.md"]


def test_sandbox_profile_and_arguments_make_network_opt_in(tmp_path):
    worktree = tmp_path / 'project "quoted"'
    state_dir = tmp_path / "state"

    offline = build_sandbox_profile(worktree, state_dir, network=False)
    online = build_sandbox_profile(worktree, state_dir, network=True)
    argv = build_sandbox_argv("/usr/bin/sandbox-exec", offline, ["railway", "status"])

    assert '(subpath "' + str(worktree).replace('"', '\\"') + '")' in offline
    assert '(subpath "' + str(state_dir) + '")' in offline
    assert "(deny network*)" in offline
    assert "(allow network*)" not in offline
    assert "(allow network*)" in online
    assert "(deny network*)" not in online
    assert argv == ["/usr/bin/sandbox-exec", "-p", offline, "railway", "status"]


def test_sandbox_rejects_network_for_arbitrary_command_before_preparation(tmp_path):
    with pytest.raises(SandboxError, match="Railway CLI"):
        run_sandbox(tmp_path / "missing-worktree", tmp_path / "state", ["curl", "https://example.com"], network=True)


def test_cli_network_rejects_arbitrary_command_before_sandbox_execution(tmp_path, capsys):
    with pytest.raises(SystemExit) as raised:
        binding_cli([
            "sandbox",
            "--worktree", str(tmp_path / "missing-worktree"),
            "--state-dir", str(tmp_path / "state"),
            "--network",
            "--",
            "curl", "https://example.com",
        ])

    assert raised.value.code == 2
    assert "Railway CLI" in capsys.readouterr().err


def test_sandbox_rejects_network_for_nonapproved_railway_executable(tmp_path, monkeypatch):
    approved = tmp_path / "approved" / "railway"
    impostor = tmp_path / "impostor" / "railway"
    for executable in (approved, impostor):
        executable.parent.mkdir()
        executable.write_text("#!/bin/sh\n", encoding="utf-8")
        executable.chmod(0o755)
    monkeypatch.setattr(sandbox_module.shutil, "which", lambda name: str(approved) if name == "railway" else None)

    with pytest.raises(SandboxError, match="approved Railway CLI executable"):
        run_sandbox(tmp_path / "missing-worktree", tmp_path / "state", [str(impostor), "status"], network=True)


def test_sandbox_executes_resolved_railway_identity_when_network_is_explicit(tmp_path, monkeypatch):
    approved = tmp_path / "bin" / "railway"
    approved.parent.mkdir()
    approved.write_text("#!/bin/sh\n", encoding="utf-8")
    approved.chmod(0o755)
    root = tmp_path / "worktree"
    state = tmp_path / "state"
    root.mkdir()
    recorded = {}
    monkeypatch.setattr(sandbox_module.shutil, "which", lambda name: str(approved) if name == "railway" else None)
    monkeypatch.setattr(
        sandbox_module,
        "prepare_sandbox",
        lambda *args, **kwargs: (root, state, "/usr/bin/sandbox-exec", "profile"),
    )

    def fake_run(argv, **kwargs):
        recorded["argv"] = argv
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(sandbox_module.subprocess, "run", fake_run)

    assert run_sandbox(root, state, ["railway", "status"], network=True) == 0
    assert recorded["argv"] == ["/usr/bin/sandbox-exec", "-p", "profile", str(approved.resolve()), "status"]


def test_sandbox_requires_macos_clean_worktree_and_external_state(tmp_path):
    repo = git_repo(tmp_path / "project")
    state_dir = tmp_path / "state"

    with pytest.raises(SandboxError, match="macOS"):
        prepare_sandbox(repo, state_dir, platform_name="Linux", sandbox_executable="/usr/bin/sandbox-exec")
    with pytest.raises(SandboxError, match="outside"):
        prepare_sandbox(repo, repo / "state", platform_name="Darwin", sandbox_executable="/usr/bin/sandbox-exec")
    (repo / "dirty.txt").write_text("dirty", encoding="utf-8")
    with pytest.raises(SandboxError, match="clean"):
        prepare_sandbox(repo, state_dir, platform_name="Darwin", sandbox_executable="/usr/bin/sandbox-exec")


@pytest.mark.skipif(sys.platform != "darwin", reason="requires the macOS sandbox-exec backend")
def test_real_sandbox_allows_worktree_write_and_denies_outside_write(tmp_path):
    repo = git_repo(tmp_path / "project")
    state_dir = tmp_path / "state"
    inside = repo / "allowed.txt"
    outside = tmp_path / "denied.txt"
    script = """
import pathlib
import sys

inside, outside = map(pathlib.Path, sys.argv[1:])
inside.write_text("allowed\\n", encoding="utf-8")
try:
    outside.write_text("denied\\n", encoding="utf-8")
except OSError:
    pass
else:
    raise SystemExit("outside write unexpectedly succeeded")
"""

    result = run_sandbox(repo, state_dir, [sys.executable, "-c", script, str(inside), str(outside)])

    assert result == 0
    assert inside.read_text(encoding="utf-8") == "allowed\n"
    assert not outside.exists()


def test_cli_inspect_plan_apply_and_reconcile(tmp_path, capsys):
    repo = git_repo(tmp_path / "project")
    binding_args = [
        "--project-id", "project-test",
        "--protected-branch", "main",
        "--railway-service", "service-test",
        str(repo),
    ]

    assert binding_cli(["inspect", str(repo)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "unbound"
    assert binding_cli(["plan", *binding_args]) == 0
    assert json.loads(capsys.readouterr().out)["changed"] is True
    assert not (repo / ".harness").exists()
    assert binding_cli(["apply", *binding_args]) == 0
    assert json.loads(capsys.readouterr().out)["changed"] is True
    assert binding_cli(["reconcile", str(repo)]) == 0
    assert json.loads(capsys.readouterr().out)["actions"] == []


def test_h_setup_is_a_thin_python_launcher(tmp_path):
    repo = git_repo(tmp_path / "project")
    completed = subprocess.run(
        [str(ROOT / "h-setup.sh"), "inspect", str(repo)],
        check=True,
        text=True,
        capture_output=True,
        env={"PATH": "/usr/bin:/bin", "PYTHON": sys.executable},
    )

    assert json.loads(completed.stdout)["status"] == "unbound"
    assert not (repo / ".claude").exists()
    assert not (repo / ".agents").exists()
    assert not (repo / ".codex").exists()
    assert not (repo / "docs").exists()


def test_target_installed_launcher_locates_runtime_without_pythonpath(tmp_path):
    repo = git_repo(tmp_path / "project")
    apply_binding(inputs(repo))
    environment = {"PATH": "/usr/bin:/bin", "PYTHON": getattr(sys, "_base_executable", sys.executable)}

    completed = subprocess.run(
        [str(repo / ".harness/bin/harness-binding"), "inspect", str(repo)],
        cwd=repo,
        check=True,
        text=True,
        capture_output=True,
        env=environment,
    )
    sandbox_help = subprocess.run(
        [str(repo / ".harness/bin/harness-sandbox-run"), "--help"],
        cwd=repo,
        check=True,
        text=True,
        capture_output=True,
        env=environment,
    )

    assert json.loads(completed.stdout)["status"] == "bound"
    assert "--worktree" in sandbox_help.stdout
    assert set(path.relative_to(repo).as_posix() for path in (repo / ".harness").rglob("*") if path.is_file()) == {
        ".harness/bin/harness-binding",
        ".harness/bin/harness-sandbox-run",
        ".harness/project-binding.json",
        ".harness/runtime.lock.json",
    }