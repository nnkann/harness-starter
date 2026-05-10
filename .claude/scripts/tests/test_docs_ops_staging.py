"""docs_ops.py wip-sync 흐름의 자기 결과 staging 회귀 가드 (v0.42.5 — P6 보강).

검증 범위:
- cmd_cluster_update가 cluster 갱신 후 git add 호출 (이전 누락분)
- cmd_move가 frontmatter 갱신 후 dest 재staging (rename만 staging되던 결함)
- cmd_reopen이 frontmatter 갱신 후 dest 재staging (cmd_move와 동일 패턴)

배경: v0.42.1~42.4 모두 commit 직후 cluster + decisions 2건이 unstaged 잔여로
남던 결함. P6(검증망 스킵 — 메커니즘이 자기 결과를 검증·반영 안 함) 변종.
"""

import importlib.util
import os
import subprocess
from pathlib import Path

import pytest


SCRIPTS_DIR = Path(__file__).resolve().parents[1]


def _load_docs_ops():
    spec = importlib.util.spec_from_file_location(
        "docs_ops", SCRIPTS_DIR / "docs_ops.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _init_repo(tmp_path: Path) -> None:
    """tmp_path에 최소 git repo + docs/ 구조 초기화."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=tmp_path, check=True)

    # 최소 디렉토리 구조
    (tmp_path / "docs" / "WIP").mkdir(parents=True)
    (tmp_path / "docs" / "decisions").mkdir(parents=True)
    (tmp_path / "docs" / "clusters").mkdir(parents=True)
    (tmp_path / ".claude" / "rules").mkdir(parents=True)
    (tmp_path / ".claude" / "memory").mkdir(parents=True)

    # naming.md 약어 표 (cmd_cluster_update가 읽음)
    (tmp_path / ".claude" / "rules" / "naming.md").write_text(
        "# 네이밍\n\n"
        "## 도메인 약어 (abbr)\n\n"
        "| 도메인 (full) | 약어 (abbr) | cluster 파일 |\n"
        "|---------------|-------------|--------------|\n"
        "| harness | hn | docs/clusters/harness.md |\n",
        encoding="utf-8",
    )

    # 초기 commit (git add/rm 동작 검증을 위해 인덱스 baseline 필요)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, check=True)


def _write_wip(tmp_path: Path, slug: str = "hn_test_wave") -> Path:
    """AC 모두 [x] 상태인 WIP 파일 작성 (cmd_move 통과용)."""
    wip = tmp_path / "docs" / "WIP" / f"decisions--{slug}.md"
    wip.write_text(
        "---\n"
        "title: 테스트 WIP\n"
        "domain: harness\n"
        "problem: P6\n"
        "solution-ref:\n"
        "  - S6 — \"테스트 (부분)\"\n"
        "tags: [test]\n"
        "status: in-progress\n"
        "created: 2026-05-11\n"
        "---\n\n"
        "# 테스트\n\n"
        "## 작업\n\n"
        "- [x] Goal: 테스트 ✅\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", str(wip)], cwd=tmp_path, check=True)
    return wip


def _staged_files(tmp_path: Path) -> set[str]:
    """현재 git index에 staged된 파일 집합 (POSIX 경로)."""
    r = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=tmp_path, capture_output=True, text=True, check=True,
    )
    return {l.strip() for l in r.stdout.splitlines() if l.strip()}


def _unstaged_files(tmp_path: Path) -> set[str]:
    """working tree와 index 사이 unstaged 변경 파일 (M·??)."""
    r = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=tmp_path, capture_output=True, text=True, check=True,
    )
    # porcelain 형식: XY <path>. X=index, Y=worktree. Y가 공백 아니면 unstaged
    out: set[str] = set()
    for line in r.stdout.splitlines():
        if len(line) < 3:
            continue
        if line[1] != " ":  # worktree 변경 있음
            out.add(line[3:].strip())
    return out


@pytest.mark.eval
def test_cluster_update_stages_changes(tmp_path, monkeypatch):
    """cmd_cluster_update 호출 후 cluster 파일이 git index에 staged 상태."""
    _init_repo(tmp_path)
    _write_wip(tmp_path, "hn_cluster_test")
    monkeypatch.chdir(tmp_path)
    mod = _load_docs_ops()

    # cluster 비어 있는 상태에서 시작
    assert "docs/clusters/harness.md" not in _staged_files(tmp_path)

    rc = mod.cmd_cluster_update()
    assert rc == 0

    cluster = tmp_path / "docs" / "clusters" / "harness.md"
    assert cluster.exists()
    # 핵심: cluster 파일이 staged 상태여야 함 (이전 결함은 unstaged로 남음)
    assert "docs/clusters/harness.md" in _staged_files(tmp_path)
    # 그리고 unstaged 잔여 없음
    assert "docs/clusters/harness.md" not in _unstaged_files(tmp_path)


@pytest.mark.eval
def test_move_stages_frontmatter_update(tmp_path, monkeypatch):
    """cmd_move 호출 후 dest 파일이 staged 상태 (rename + frontmatter 갱신 모두).

    이전 결함: git mv는 rename만 staging, write_frontmatter_field 결과는 unstaged.
    """
    _init_repo(tmp_path)
    wip = _write_wip(tmp_path, "hn_move_test")
    monkeypatch.chdir(tmp_path)
    mod = _load_docs_ops()

    # WIP를 미리 commit해 깨끗한 baseline 만들기
    subprocess.run(["git", "commit", "-q", "-m", "wip"], cwd=tmp_path, check=True)

    rc = mod.cmd_move(str(Path("docs/WIP") / wip.name))
    assert rc == 0

    dest = tmp_path / "docs" / "decisions" / "hn_move_test.md"
    assert dest.exists()
    staged = _staged_files(tmp_path)
    # rename + frontmatter 갱신 둘 다 staged
    assert "docs/decisions/hn_move_test.md" in staged
    # unstaged 잔여 없음 (frontmatter 갱신분이 묻혀 있지 않음)
    assert "docs/decisions/hn_move_test.md" not in _unstaged_files(tmp_path)


@pytest.mark.eval
def test_reopen_stages_frontmatter_update(tmp_path, monkeypatch):
    """cmd_reopen 호출 후 dest(WIP) 파일이 staged 상태.

    cmd_move와 동일 패턴 — rename만 staging되고 status: in-progress 갱신은
    unstaged였던 결함.
    """
    _init_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    mod = _load_docs_ops()

    # completed 파일 작성 + commit
    completed = tmp_path / "docs" / "decisions" / "hn_reopen_test.md"
    completed.write_text(
        "---\n"
        "title: reopen 테스트\n"
        "domain: harness\n"
        "problem: P6\n"
        "solution-ref:\n"
        "  - S6 — \"테스트 (부분)\"\n"
        "tags: [test]\n"
        "status: completed\n"
        "created: 2026-05-11\n"
        "---\n\n"
        "# 테스트\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", str(completed)], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "completed"], cwd=tmp_path, check=True)

    rc = mod.cmd_reopen(str(Path("docs/decisions") / completed.name))
    assert rc == 0

    dest = tmp_path / "docs" / "WIP" / "decisions--hn_reopen_test.md"
    assert dest.exists()
    staged = _staged_files(tmp_path)
    assert "docs/WIP/decisions--hn_reopen_test.md" in staged
    # unstaged 잔여 없음 (status: in-progress 갱신이 묻혀 있지 않음)
    assert "docs/WIP/decisions--hn_reopen_test.md" not in _unstaged_files(tmp_path)
