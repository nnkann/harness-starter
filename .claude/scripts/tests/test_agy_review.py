"""agy-review.sh 계약 테스트."""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / ".claude" / "scripts" / "agy-review.sh"


def _fake_agy(tmp_path: Path) -> Path:
    fake = tmp_path / "agy"
    fake.write_text(
        "#!/bin/sh\n"
        "echo agy-called\n"
        "printf '%s\\n' \"$@\"\n",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    return fake


def test_agy_review_blocks_when_state_dir_is_not_writable(tmp_path: Path):
    """Codex sandbox처럼 Agy HOME 상태 디렉터리에 쓸 수 없으면 실행하지 않는다."""
    fake = _fake_agy(tmp_path)
    home = tmp_path / "home"
    state_dir = home / ".gemini" / "antigravity-cli"
    state_dir.mkdir(parents=True)
    state_dir.chmod(stat.S_IREAD | stat.S_IEXEC)

    env = {
        "AGY_BIN": str(fake),
        "HOME": str(home),
        "PATH": os.environ.get("PATH", ""),
    }
    try:
        result = subprocess.run(
            ["bash", str(SCRIPT), "검토 질문"],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    finally:
        state_dir.chmod(0o755)

    assert result.returncode == 73
    assert "Agy state dir is not writable" in result.stderr
    assert "로컬 터미널에서 직접 실행" in result.stderr
    assert ".claude/memory/session-agy-review.md" in result.stderr
    assert "agy-called" not in result.stdout


def test_agy_review_execs_fake_agy_with_project_root(tmp_path: Path):
    """상태 저장 가능 환경에서는 full permission Agy에 project root를 넘긴다."""
    fake = _fake_agy(tmp_path)
    home = tmp_path / "home"
    (home / ".gemini" / "antigravity-cli").mkdir(parents=True)
    handoff = tmp_path / ".claude" / "memory" / "session-agy-review.md"

    env = {
        "AGY_BIN": str(fake),
        "HOME": str(home),
        "AGY_HANDOFF_FILE": str(handoff),
        "PATH": os.environ.get("PATH", ""),
    }
    result = subprocess.run(
        ["bash", str(SCRIPT), "검토 질문"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "agy-called" in result.stdout
    assert f"handoff saved to {handoff}" in result.stderr
    assert "--dangerously-skip-permissions" in result.stdout
    assert "--add-dir" in result.stdout
    assert str(tmp_path) in result.stdout
    assert "--print-timeout" in result.stdout
    assert "--print" in result.stdout
    assert "검토 질문" in result.stdout
    saved = handoff.read_text(encoding="utf-8")
    assert "# Agy review handoff" in saved
    assert f"- root: {tmp_path}" in saved
    assert "- permission_mode: full" in saved
    assert "--dangerously-skip-permissions --add-dir <root>" in saved
    assert "## Prompt" in saved
    assert "검토 질문" in saved
    assert "## Response" in saved
    assert "agy-called" in saved


def test_agy_review_prompt_permission_mode_does_not_skip_permissions(tmp_path: Path):
    """필요하면 AGY_PERMISSION_MODE=prompt로 권한 프롬프트 모드에 둘 수 있다."""
    fake = _fake_agy(tmp_path)
    home = tmp_path / "home"
    (home / ".gemini" / "antigravity-cli").mkdir(parents=True)
    handoff = tmp_path / ".claude" / "memory" / "session-agy-review.md"

    env = {
        "AGY_BIN": str(fake),
        "HOME": str(home),
        "AGY_HANDOFF_FILE": str(handoff),
        "AGY_PERMISSION_MODE": "prompt",
        "PATH": os.environ.get("PATH", ""),
    }
    result = subprocess.run(
        ["bash", str(SCRIPT), "검토 질문"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "--dangerously-skip-permissions" not in result.stdout
    saved = handoff.read_text(encoding="utf-8")
    assert "- permission_mode: prompt" in saved
