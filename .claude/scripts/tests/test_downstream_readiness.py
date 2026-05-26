"""downstream-readiness.sh 계약 테스트."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / ".claude" / "scripts" / "downstream-readiness.sh"


def _copy_required_harness_surface(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()

    for rel in (
        ".claude/scripts/downstream-readiness.sh",
        ".claude/scripts/bash-guard.sh",
        ".claude/scripts/validate-settings.sh",
        ".claude/scripts/pre_commit_check.py",
        ".claude/scripts/test-bash-guard.sh",
        ".claude/scripts/tests/test_pre_commit.py",
        ".claude/settings.json",
        ".claude/rules/naming.md",
        ".claude/agents/review.md",
    ):
        src = REPO / rel
        dst = repo / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    return repo


def test_downstream_readiness_reports_runtime_stack_from_harness_json(tmp_path: Path):
    """Hermes-managed downstream은 HARNESS.json의 runtime_stack을 관측 신호로 출력한다."""
    repo = _copy_required_harness_surface(tmp_path)
    harness_json = repo / ".claude" / "HARNESS.json"
    harness_json.write_text(
        json.dumps(
            {
                "profile": "full",
                "version": "0.52.9",
                "is_starter": False,
                "runtime_stack": "hermes-codex-agy",
                "runtime_adapters": {
                    "hermes": "orchestrator",
                    "codex": "executor",
                    "agy": "advisor",
                    "claude": "optional-adapter",
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "runtime_stack: hermes-codex-agy" in result.stdout
    assert "runtime_adapters: hermes,codex,agy,claude" in result.stdout
