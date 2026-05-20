"""harness_version_bump.py CLI 계약 테스트."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "harness_version_bump.py"


def run(cmd: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if check:
        assert result.returncode == 0, result.stderr
    return result


def run_with_env(
    cmd: list[str],
    cwd: Path,
    env: dict[str, str],
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    merged_env.update(env)
    result = subprocess.run(
        cmd,
        cwd=cwd,
        env=merged_env,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if check:
        assert result.returncode == 0, result.stderr
    return result


def init_starter_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    run(["git", "init", "-q"], repo)
    run(["git", "config", "user.email", "test@example.com"], repo)
    run(["git", "config", "user.name", "Test User"], repo)

    harness_path = repo / ".claude" / "HARNESS.json"
    harness_path.parent.mkdir(parents=True)
    harness_path.write_text(
        json.dumps({"is_starter": True, "version": "0.51.8"}, ensure_ascii=False),
        encoding="utf-8",
    )

    skill_path = repo / ".claude" / "skills" / "implementation" / "SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text("---\nname: implementation\n---\n\n# Implementation\n", encoding="utf-8")

    run(["git", "add", "."], repo)
    run(["git", "commit", "-q", "-m", "init"], repo)
    return repo


@pytest.mark.version
def test_unstaged_critical_change_reports_stage_required(tmp_path: Path):
    repo = init_starter_repo(tmp_path)
    skill_path = repo / ".claude" / "skills" / "implementation" / "SKILL.md"
    skill_path.write_text(skill_path.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")

    result = run([sys.executable, str(SCRIPT)], repo)

    assert "version_bump: none" in result.stdout
    assert "stage_required: true" in result.stdout
    assert "pending_bump: patch" in result.stdout
    assert "기존 핵심 파일 수정" in (result.stdout + result.stderr)


@pytest.mark.version
def test_staged_critical_change_reports_patch(tmp_path: Path):
    repo = init_starter_repo(tmp_path)
    skill_path = repo / ".claude" / "skills" / "implementation" / "SKILL.md"
    skill_path.write_text(skill_path.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")
    run(["git", "add", ".claude/skills/implementation/SKILL.md"], repo)

    result = run([sys.executable, str(SCRIPT)], repo)

    assert "version_bump: patch" in result.stdout
    assert "current_version: 0.51.8" in result.stdout
    assert "next_version: 0.51.9" in result.stdout
    assert "stage_required" not in result.stdout


@pytest.mark.version
def test_untracked_new_script_reports_pending_minor(tmp_path: Path):
    repo = init_starter_repo(tmp_path)
    script_path = repo / ".claude" / "scripts" / "new_tool.py"
    script_path.parent.mkdir(parents=True)
    script_path.write_text("print('new')\n", encoding="utf-8")

    result = run([sys.executable, str(SCRIPT)], repo)

    assert "version_bump: none" in result.stdout
    assert "stage_required: true" in result.stdout
    assert "pending_bump: minor" in result.stdout


@pytest.mark.version
def test_harness_bump_patch_opt_in_reports_patch_for_script_change(tmp_path: Path):
    repo = init_starter_repo(tmp_path)
    script_path = repo / ".claude" / "scripts" / "existing.py"
    script_path.parent.mkdir(parents=True)
    script_path.write_text("print('old')\n", encoding="utf-8")
    run(["git", "add", ".claude/scripts/existing.py"], repo)
    run(["git", "commit", "-q", "-m", "add script"], repo)

    script_path.write_text("print('new')\n", encoding="utf-8")
    run(["git", "add", ".claude/scripts/existing.py"], repo)

    result = run_with_env(
        [sys.executable, str(SCRIPT)],
        repo,
        {"HARNESS_BUMP": "patch"},
    )

    assert "version_bump: patch" in result.stdout
    assert "next_version: 0.51.9" in result.stdout
    assert "HARNESS_BUMP=patch 명시" in (result.stdout + result.stderr)


@pytest.mark.version
def test_unsupported_arg_fails_instead_of_running_default_check(tmp_path: Path):
    repo = init_starter_repo(tmp_path)

    result = run([sys.executable, str(SCRIPT), "--apply", "patch"], repo, check=False)

    assert result.returncode == 2
    output = result.stdout + result.stderr
    assert "unsupported_arg: --apply" in output
    assert "usage: harness_version_bump.py" in output
    assert "version_bump:" not in result.stdout
