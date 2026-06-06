"""h-setup.sh runtime adapter metadata regression tests."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "h-setup.sh"


def run(cmd: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if check:
        assert result.returncode == 0, result.stdout + result.stderr
    return result


def test_upgrade_backfills_runtime_metadata_for_existing_harness_json(tmp_path: Path):
    """기존 downstream HARNESS.json도 upgrade 진입 시 runtime_stack 기본값을 얻는다."""
    target = tmp_path / "downstream"
    target.mkdir()
    run(["git", "init", "-q"], target)
    harness = target / ".claude" / "HARNESS.json"
    harness.parent.mkdir(parents=True)
    harness.write_text(
        json.dumps(
            {
                "profile": "minimal",
                "skills": "commit implementation",
                "version": "0.0.1",
                "is_starter": False,
                "installed_from_ref": "unknown",
                "installed_at": "unknown",
                "upgraded_at": None,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    run(["bash", str(SCRIPT), "--upgrade", str(target)], REPO)

    data = json.loads(harness.read_text(encoding="utf-8"))
    assert data["runtime_stack"] == "hermes-codex-agy"
    assert data["runtime_adapters"] == {
        "hermes": "orchestrator",
        "codex": "executor",
        "agy": "advisor",
        "claude": "optional-adapter",
    }


def test_new_install_creates_downstream_harness_definition_first(tmp_path: Path):
    """신규 프로젝트는 도메인 분류 전 HARNESS.json 정의 파일부터 가진다."""
    target = tmp_path / "new-project"
    target.mkdir()
    run(["git", "init", "-q"], target)

    run(["bash", str(SCRIPT), "--profile", "minimal", str(target)], REPO)

    harness = target / ".claude" / "HARNESS.json"
    pending = target / "docs" / "WIP" / "harness_init_pending.md"
    agents = target / "AGENTS.md"
    data = json.loads(harness.read_text(encoding="utf-8"))
    pending_text = pending.read_text(encoding="utf-8")
    agents_text = agents.read_text(encoding="utf-8")

    assert data["is_starter"] is False
    assert data["runtime_stack"] == "hermes-codex-agy"
    assert data["runtime_adapters"]["hermes"] == "orchestrator"
    assert "cps-learn" in data["skills"]
    assert (target / ".claude" / "skills" / "cps-learn" / "SKILL.md").exists()
    assert (target / ".agents" / "skills" / "cps-learn" / "SKILL.md").exists()
    assert pending.exists()
    assert pending_text.startswith("---\n")
    assert "title: 하네스 초기화 대기 중" in pending_text
    assert "domain: harness" in pending_text
    assert 'c: "h-setup.sh가 하네스 파일을 설치했지만 harness-init이 아직 프로젝트 CPS와 환경 결정을 만들지 않았다"' in pending_text
    assert "problem: [P7, P9]" in pending_text
    assert "s: [S7, S9]" in pending_text
    assert "tags: [init, setup, downstream]" in pending_text
    assert "status: pending" in pending_text
    assert "> status: pending" not in pending_text
    assert ".claude/HARNESS.json" in pending_text
    assert "도메인 분류" in pending_text
    assert "Runtime Adapter 표면" in agents_text
    assert "제품 아키텍처가 아니라 agent runtime adapter" in agents_text
    assert "minimal` 프로파일은 기능 minimal" in agents_text
