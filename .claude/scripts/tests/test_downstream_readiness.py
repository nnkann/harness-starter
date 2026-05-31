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
        ".claude/scripts/agy-review.sh",
        ".claude/scripts/bash-guard.sh",
        ".claude/scripts/validate-settings.sh",
        ".claude/scripts/pre_commit_check.py",
        ".claude/scripts/test-bash-guard.sh",
        ".claude/scripts/tests/test_pre_commit.py",
        ".claude/settings.json",
        ".claude/rules/naming.md",
        ".claude/agents/review.md",
        ".claude/skills/commit/SKILL.md",
        ".claude/skills/implementation/SKILL.md",
        ".claude/skills/harness-upgrade/SKILL.md",
        ".agents/skills/commit/SKILL.md",
        ".agents/skills/implementation/SKILL.md",
        ".agents/skills/harness-upgrade/SKILL.md",
        "AGENTS.md",
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
                "skills": "harness-sync,harness-upgrade,implementation,commit,advisor,write-doc,naming-convention,coding-convention,eval",
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
    assert "agy runner: .claude/scripts/agy-review.sh" in result.stdout
    assert "agy handoff: .claude/memory/session-agy-review.md" in result.stdout
    assert "agy permission_mode: full" in result.stdout


def test_downstream_readiness_reports_agy_callable_from_env(tmp_path: Path):
    """Agy adapter가 있으면 downstream 공통 runner와 local binding을 관측한다."""
    repo = _copy_required_harness_surface(tmp_path)
    fake_bin = tmp_path / "agy"
    fake_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    fake_bin.chmod(0o755)

    harness_json = repo / ".claude" / "HARNESS.json"
    harness_json.write_text(
        json.dumps(
            {
                "profile": "full",
                "skills": "harness-sync,harness-upgrade,implementation,commit,advisor,write-doc,naming-convention,coding-convention,eval",
                "version": "0.54.0",
                "is_starter": False,
                "runtime_stack": "hermes-codex-agy",
                "runtime_adapters": {
                    "hermes": "orchestrator",
                    "codex": "executor",
                    "agy": "advisor",
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
        env={"AGY_BIN": str(fake_bin)},
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "agy runner: .claude/scripts/agy-review.sh" in result.stdout
    assert "agy handoff: .claude/memory/session-agy-review.md" in result.stdout
    assert "agy permission_mode: full" in result.stdout
    assert f"agy callable: {fake_bin}" in result.stdout


def test_downstream_readiness_blocks_missing_codex_commit_skill(tmp_path: Path):
    """Codex adapter가 있는데 .agents commit skill이 없으면 silent fail로 차단한다."""
    repo = _copy_required_harness_surface(tmp_path)
    (repo / ".agents" / "skills" / "commit" / "SKILL.md").unlink()
    harness_json = repo / ".claude" / "HARNESS.json"
    harness_json.write_text(
        json.dumps(
            {
                "profile": "full",
                "skills": "harness-sync,harness-upgrade,implementation,commit,advisor,write-doc,naming-convention,coding-convention,eval",
                "version": "0.54.0",
                "is_starter": False,
                "runtime_stack": "hermes-codex-agy",
                "runtime_adapters": {
                    "hermes": "orchestrator",
                    "codex": "executor",
                    "agy": "advisor",
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

    assert result.returncode == 1
    assert ".agents/skills/commit/SKILL.md 없음" in result.stdout
    assert "누락: 1" in result.stdout


def test_downstream_readiness_blocks_legacy_codex_surface_gap(tmp_path: Path):
    """runtime_adapters 없는 구 HARNESS.json은 claude,codex 기본값으로 검사한다."""
    repo = _copy_required_harness_surface(tmp_path)
    shutil.rmtree(repo / ".agents")
    (repo / "AGENTS.md").unlink()
    harness_json = repo / ".claude" / "HARNESS.json"
    harness_json.write_text(
        json.dumps(
            {
                "profile": "full",
                "skills": "harness-sync,harness-upgrade,implementation,commit,advisor,write-doc,naming-convention,coding-convention,eval",
                "version": "0.52.6",
                "is_starter": False,
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

    assert result.returncode == 1
    assert "runtime_adapters: claude,codex" in result.stdout
    assert "AGENTS.md 없음" in result.stdout
    assert ".agents/skills/commit/SKILL.md 없음" in result.stdout
