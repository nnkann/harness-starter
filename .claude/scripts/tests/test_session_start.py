"""session-start.py reminder 노출 회귀 가드."""

import shutil
import subprocess
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]


def _copy_session_start(tmp_path: Path) -> None:
    scripts = tmp_path / ".claude" / "scripts"
    scripts.mkdir(parents=True)
    shutil.copy2(SCRIPTS_DIR / "session-start.py", scripts / "session-start.py")
    shutil.copytree(SCRIPTS_DIR / "utils", scripts / "utils")


def _init_repo(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=tmp_path, check=True)
    (tmp_path / "docs" / "WIP").mkdir(parents=True)
    (tmp_path / ".claude" / "memory").mkdir(parents=True)
    (tmp_path / ".claude" / "memory" / "reminders").mkdir(parents=True)
    (tmp_path / ".claude" / "memory" / "MEMORY.md").write_text(
        "# MEMORY\n\n- [hit](reminders/reminder_hit.md)\n",
        encoding="utf-8",
    )


def _write_wip(tmp_path: Path) -> None:
    (tmp_path / "docs" / "WIP" / "decisions--hn_memory_wave.md").write_text(
        "---\n"
        "title: reminder KV 테스트\n"
        "domain: harness\n"
        "problem: P8\n"
        "s: [S8]\n"
        "tags: [memory, reminder]\n"
        "status: in-progress\n"
        "created: 2026-05-21\n"
        "---\n\n"
        "# reminder KV 테스트\n",
        encoding="utf-8",
    )


def _write_reminder(tmp_path: Path, name: str, body: str) -> None:
    (tmp_path / ".claude" / "memory" / "reminders" / name).write_text(
        body, encoding="utf-8"
    )


def _write_legacy_reminder(tmp_path: Path, name: str, body: str) -> None:
    (tmp_path / ".claude" / "memory" / name).write_text(body, encoding="utf-8")


def _run_session_start(tmp_path: Path) -> str:
    result = subprocess.run(
        [sys.executable, ".claude/scripts/session-start.py"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return result.stdout


def test_kv_group_boost_keeps_fallback_eligible_reminder(tmp_path):
    """kv_group은 hard filter가 아니라 정렬 hint라 fallback reminder도 남는다."""
    _copy_session_start(tmp_path)
    _init_repo(tmp_path)
    _write_wip(tmp_path)
    _write_reminder(
        tmp_path,
        "reminder_fallback.md",
        "---\n"
        "reminder: fallback reminder도 출력되어야 함\n"
        "domain: harness\n"
        "strength: weak\n"
        "candidate_p: P8\n"
        "status: active\n"
        "---\n",
    )
    _write_reminder(
        tmp_path,
        "reminder_hit.md",
        "---\n"
        "reminder: kv group hit reminder가 먼저 출력되어야 함\n"
        "domain: harness\n"
        "strength: weak\n"
        "candidate_p: P8\n"
        "kv_group: harness/P8/stale-memory\n"
        "status: active\n"
        "---\n",
    )

    out = _run_session_start(tmp_path)

    hit_pos = out.index("kv group hit reminder")
    fallback_pos = out.index("fallback reminder")
    assert hit_pos < fallback_pos


def test_kv_group_does_not_hide_stale_marker(tmp_path):
    """group hit이 stale 판정을 덮어쓰면 P9 오염 방지 계약이 깨진다."""
    _copy_session_start(tmp_path)
    _init_repo(tmp_path)
    _write_wip(tmp_path)
    _write_reminder(
        tmp_path,
        "reminder_stale.md",
        "---\n"
        "reminder: stale reminder는 재확인 필요 표시가 남아야 함\n"
        "domain: harness\n"
        "strength: strong\n"
        "candidate_p: P8\n"
        "kv_group: harness/P8/stale-memory\n"
        "status: active\n"
        "valid_until: 2000-01-01\n"
        "---\n",
    )

    out = _run_session_start(tmp_path)

    assert "stale reminder는 재확인 필요 표시가 남아야 함" in out
    assert "stale 후보" in out


def test_legacy_root_reminder_still_read(tmp_path):
    """루트 reminder_*는 downstream 호환용 fallback으로 계속 읽는다."""
    _copy_session_start(tmp_path)
    _init_repo(tmp_path)
    _write_wip(tmp_path)
    _write_legacy_reminder(
        tmp_path,
        "reminder_legacy_root.md",
        "---\n"
        "reminder: legacy root reminder도 출력되어야 함\n"
        "domain: harness\n"
        "strength: weak\n"
        "candidate_p: P8\n"
        "status: active\n"
        "---\n",
    )

    out = _run_session_start(tmp_path)

    assert "legacy root reminder도 출력되어야 함" in out
