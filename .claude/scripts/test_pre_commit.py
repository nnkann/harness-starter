"""
pre_commit_check.py 회귀 테스트 (pytest)

단위 테스트: TEST_MODE=1 + 환경변수 주입 — git 호출 없음, ~80ms/케이스
통합 테스트: 실제 git sandbox — dead link·이동 커밋 검증

사용: pytest .claude/scripts/test_pre_commit.py -v
      pytest .claude/scripts/test_pre_commit.py -v -k "unit"   # 단위만
      pytest .claude/scripts/test_pre_commit.py -v -k "integ"  # 통합만
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# ─────────────────────────────────────────────────────────
# 헬퍼
# ─────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.parent.parent  # harness-starter/
PY_SCRIPT = REPO_ROOT / ".claude" / "scripts" / "pre_commit_check.py"


def run_check(
    name_status: str = "",
    numstat: str = "",
    diff_u0: str = "",
    extra_env: dict | None = None,
) -> dict[str, str]:
    """pre_commit_check.py를 TEST_MODE=1으로 실행, stdout을 key:value 딕셔너리로 반환."""
    env = {
        **os.environ,
        "TEST_MODE": "1",
        "_TEST_NAME_STATUS": name_status,
        "_TEST_NUMSTAT": numstat,
        "_TEST_DIFF_U0": diff_u0,
    }
    if extra_env:
        env.update(extra_env)
    r = subprocess.run(
        [sys.executable, str(PY_SCRIPT)],
        env=env,
        capture_output=True,
        text=True,
    )
    out: dict[str, str] = {}
    for line in r.stdout.splitlines():
        if ": " in line:
            k, v = line.split(": ", 1)
            out[k] = v
    return out


def stage(out: dict) -> str:
    return out.get("recommended_stage", "")


# ─────────────────────────────────────────────────────────
# T33·T34 — ENOENT 패턴 (Python로 직접 검증)
# ─────────────────────────────────────────────────────────

# SSOT: pre_commit_check.py의 ENOENT_PATTERNS를 직접 임포트
sys.path.insert(0, str(PY_SCRIPT.parent))
from pre_commit_check import ENOENT_PATTERNS as ENOENT_PAT  # noqa: E402


class TestEnoentPattern:
    @pytest.mark.parametrize("fixture", [
        "'eslint' is not recognized as an internal or external command",
        "bash: eslint: command not found",
        "zsh: command not found: eslint",
        "sh: eslint: command not found",
        "exec: eslint: not found",
        "sh: 5: eslint: not found",
        "ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL  Command failed",
    ])
    def test_match(self, fixture):
        """T33: 린터 도구 실종 warn 매칭"""
        assert ENOENT_PAT.search(fixture)

    @pytest.mark.parametrize("fixture", [
        "Error: ENOENT: no such file or directory, open '/path/import.ts'",
        "Error: Cannot find module 'eslint-plugin-react'",
        "  3:7  error  'x' is defined but never used  no-unused-vars",
        "    at Object.<anonymous> (/app/node_modules/eslint/lib/cli.js:123:5)",
        "SyntaxError: Unexpected token '<' (1:0)",
    ])
    def test_no_false_positive(self, fixture):
        """T34: ESLint crash·rule 위반 → warn 오탐 없음"""
        assert not ENOENT_PAT.search(fixture)


# ─────────────────────────────────────────────────────────
# T14·T15 — completed 게이트 (Python 직접 검증)
# ─────────────────────────────────────────────────────────

def _extract_body_skip_result(text: str) -> str:
    """프론트매터 제거 + '처리 결과' 섹션 이후 skip."""
    lines = text.splitlines()
    # 프론트매터 건너뜀
    i, dash = 0, 0
    while i < len(lines):
        if lines[i].strip() == "---":
            dash += 1
            i += 1
            if dash == 2:
                break
        else:
            i += 1
    body_lines, skip = [], False
    for line in lines[i:]:
        if re.match(r"^## (처리 결과|원본|회고|처리|결과)", line):
            skip = True
        if not skip:
            body_lines.append(line)
    return "\n".join(body_lines)


BLOCK_HEADER = re.compile(r"^\s*##\s*(후속|미결|미결정|추후|나중에|별도로)", re.MULTILINE)


class TestCompletedGate:
    def test_block_header(self):
        """T14: ## 후속 헤더 → 차단 감지"""
        doc = """---
title: 게이트 테스트
domain: harness
status: pending
created: 2026-04-19
---

# 본문

## 후속
- TODO 작업.
"""
        body = _extract_body_skip_result(doc)
        assert BLOCK_HEADER.search(body)

    def test_result_section_exempt(self):
        """T15: 처리 결과 섹션 내 키워드 → 면제"""
        doc = """---
title: 게이트 테스트 2
domain: harness
status: pending
created: 2026-04-19
---

# 본문

## 처리 결과
- 후속 작업 없음.
- TODO 다 처리됨 ✅
"""
        body = _extract_body_skip_result(doc)
        assert not BLOCK_HEADER.search(body)


# ─────────────────────────────────────────────────────────
# 시크릿 스캔 단위 테스트
# ─────────────────────────────────────────────────────────

class TestSecretScan:
    def test_line_confirmed_blocks(self):
        """시크릿 패턴 라인 → pre_check_passed=false, s1_level=line-confirmed"""
        r = subprocess.run(
            [sys.executable, str(PY_SCRIPT)],
            env={
                **os.environ,
                "TEST_MODE": "1",
                "_TEST_NAME_STATUS": "M src/config.ts",
                "_TEST_NUMSTAT": "1 0 src/config.ts",
                "_TEST_DIFF_U0": '+export const KEY = "sk_live_xxxxxxxxxxxxxxxx";\n',
            },
            capture_output=True, text=True,
        )
        out: dict[str, str] = {}
        for line in r.stdout.splitlines():
            if ": " in line:
                k, v = line.split(": ", 1)
                out[k] = v
        assert out.get("pre_check_passed") == "false"
        assert out.get("s1_level") == "line-confirmed"
        assert r.returncode == 2

    def test_file_only_warns(self):
        """시크릿 관련 파일명 → s1_level=file-only, 차단 아님"""
        out = run_check(
            name_status="M src/auth.ts",
            numstat="1 0 src/auth.ts",
            diff_u0="+export const validate = () => true;\n",
        )
        assert out.get("s1_level") == "file-only"
        assert out.get("pre_check_passed") == "true"

    def test_helper_exempt(self):
        """auth-helper.ts → 시크릿 면제"""
        out = run_check(
            name_status="M src/auth-helper.ts",
            numstat="1 0 src/auth-helper.ts",
            diff_u0="+export const x = 1;\n",
        )
        assert out.get("s1_level", "") == ""
        assert out.get("pre_check_passed") == "true"


# ─────────────────────────────────────────────────────────
# Stage 기본 단위 테스트 (AC kind 기반)
# ─────────────────────────────────────────────────────────

class TestStageBasic:
    def test_upstream_scripts_deep(self):
        """업스트림 위험 경로 → deep"""
        out = run_check(
            name_status="M .claude/scripts/foo.sh",
            numstat="1 0 .claude/scripts/foo.sh",
            diff_u0="+#!/bin/bash\n",
        )
        assert stage(out) == "deep"

    def test_wip_only_skip(self):
        """WIP 단독 → skip"""
        out = run_check(
            name_status="M docs/WIP/decisions--hn_foo.md",
            numstat="3 0 docs/WIP/decisions--hn_foo.md",
            diff_u0="+내용\n",
        )
        assert stage(out) == "skip"

    def test_docs_5lines_skip(self):
        """docs 5줄 이하 → skip"""
        out = run_check(
            name_status="M docs/guides/hn_foo.md",
            numstat="1 0 docs/guides/hn_foo.md",
            diff_u0="+한 줄\n",
        )
        assert stage(out) == "skip"

    def test_no_wip_standard(self):
        """WIP 없는 일반 파일 → standard"""
        out = run_check(
            name_status="M src/foo.ts",
            numstat="2 0 src/foo.ts",
            diff_u0="+const x = 1;\n",
        )
        assert stage(out) == "standard"


# ─────────────────────────────────────────────────────────
# 통합 테스트 — 실제 git sandbox 필요
# ─────────────────────────────────────────────────────────

def _git(args: list[str], cwd: Path, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args, cwd=cwd, capture_output=True, text=True, **kwargs
    )


def _run_precheck(repo: Path) -> dict[str, str]:
    r = subprocess.run(
        [sys.executable, ".claude/scripts/pre_commit_check.py"],
        cwd=repo, capture_output=True, text=True,
    )
    out: dict[str, str] = {}
    for line in r.stdout.splitlines():
        if ": " in line:
            k, v = line.split(": ", 1)
            out[k] = v
    return out


def _reset(repo: Path) -> None:
    _git(["reset", "HEAD", "."], repo)
    _git(["clean", "-fdq"], repo)


def _commit(repo: Path, msg: str) -> None:
    env = {**os.environ, "HARNESS_DEV": "1"}
    subprocess.run(
        ["git", "-c", "commit.gpgsign=false", "commit", "-q", "-m", msg],
        cwd=repo, env=env, capture_output=True,
    )


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture(scope="module")
def integ_repo(tmp_path_factory):
    """module 스코프 sandbox: git clone + 최신 스크립트 복사."""
    tmp = tmp_path_factory.mktemp("integ")
    repo = tmp / "repo"
    subprocess.run(["git", "clone", "-q", str(REPO_ROOT), str(repo)],
                   capture_output=True, check=True)
    # 미커밋 최신 파일 덮어쓰기
    for name in ("pre_commit_check.py",):
        src = REPO_ROOT / ".claude" / "scripts" / name
        dst = repo / ".claude" / "scripts" / name
        if src.exists():
            shutil.copy2(src, dst)
    for name in ("staging.md", "naming.md"):
        src = REPO_ROOT / ".claude" / "rules" / name
        dst = repo / ".claude" / "rules" / name
        if src.exists():
            shutil.copy2(src, dst)
    yield repo


class TestIntegDeadLink:
    def test_deleted_file_dead_link(self, integ_repo):
        """T35.1: md 삭제 + 기존 링크 → 차단"""
        repo = integ_repo
        _write(repo / "docs/test_target/hn_dummy.md",
               "---\ntitle: dummy\ndomain: harness\nstatus: completed\ncreated: 2026-04-22\n---\n")
        _write(repo / "docs/test_cluster/harness_t35.md",
               "---\ntitle: cluster\ndomain: harness\nstatus: completed\ncreated: 2026-04-22\n---\n"
               "- [dummy](../test_target/hn_dummy.md)\n")
        _git(["add", "docs/test_target/hn_dummy.md", "docs/test_cluster/harness_t35.md"], repo)
        _commit(repo, "prep T35.1")
        _git(["rm", "-q", "docs/test_target/hn_dummy.md"], repo)
        out = _run_precheck(repo)
        assert out.get("pre_check_passed") == "false"
        _reset(repo)

    def test_new_md_broken_link(self, integ_repo):
        """T35.2: 새 md + 없는 링크 → 차단"""
        repo = integ_repo
        _write(repo / "docs/test_cluster2/broken.md",
               "---\ntitle: broken\ndomain: harness\nstatus: in-progress\ncreated: 2026-04-22\n---\n"
               "- [없는 파일](../test_target/hn_nonexistent.md)\n")
        _git(["add", "docs/test_cluster2/broken.md"], repo)
        out = _run_precheck(repo)
        assert out.get("pre_check_passed") == "false"
        _reset(repo)

    def test_link_target_also_staged(self, integ_repo):
        """T35.3: 링크 대상도 같이 staged → 통과"""
        repo = integ_repo
        _write(repo / "docs/test_target3/hn_new.md",
               "---\ntitle: new\ndomain: harness\nstatus: in-progress\ncreated: 2026-04-22\n---\n")
        _write(repo / "docs/test_cluster3/linker.md",
               "---\ntitle: linker\ndomain: harness\nstatus: in-progress\ncreated: 2026-04-22\n---\n"
               "- [new](../test_target3/hn_new.md)\n")
        _git(["add", "docs/test_target3/hn_new.md", "docs/test_cluster3/linker.md"], repo)
        out = _run_precheck(repo)
        assert out.get("pre_check_passed") == "true"
        _reset(repo)

    def test_same_basename_no_false_positive(self, integ_repo):
        """T38: 같은 basename 다른 경로 → 오탐 없음"""
        repo = integ_repo
        _write(repo / "docs/t38a_a/hn_sibling.md",
               "---\ntitle: a\ndomain: harness\nstatus: completed\ncreated: 2026-04-22\n---\n")
        _write(repo / "docs/t38a_b/hn_sibling.md",
               "---\ntitle: b\ndomain: harness\nstatus: completed\ncreated: 2026-04-22\n---\n")
        _write(repo / "docs/t38a_a/hn_ref_to_a.md",
               "---\ntitle: ref\ndomain: harness\nstatus: completed\ncreated: 2026-04-22\n---\n"
               "- [A](./hn_sibling.md)\n")
        _git(["add", "docs/t38a_a/hn_sibling.md", "docs/t38a_b/hn_sibling.md",
               "docs/t38a_a/hn_ref_to_a.md"], repo)
        _commit(repo, "prep T38")
        _git(["rm", "-q", "docs/t38a_b/hn_sibling.md"], repo)
        out = _run_precheck(repo)
        assert out.get("pre_check_passed") == "true"
        _reset(repo)


class TestIntegRelatesTo:
    def test_exists(self, integ_repo):
        """T36.1: relates-to 존재 → 통과"""
        repo = integ_repo
        _write(repo / "docs/t36_target/hn_existing.md",
               "---\ntitle: existing\ndomain: harness\nstatus: completed\ncreated: 2026-04-22\n---\n")
        _write(repo / "docs/t36_src/hn_refer.md",
               "---\ntitle: refer\ndomain: harness\nrelates-to:\n"
               "  - path: ../t36_target/hn_existing.md\n    rel: extends\n"
               "status: in-progress\ncreated: 2026-04-22\n---\n")
        _git(["add", "docs/t36_target/hn_existing.md", "docs/t36_src/hn_refer.md"], repo)
        out = _run_precheck(repo)
        assert out.get("pre_check_passed") == "true"
        _reset(repo)

    def test_missing(self, integ_repo):
        """T36.2: relates-to 미존재 → 차단"""
        repo = integ_repo
        _write(repo / "docs/t36b/hn_broken_rt.md",
               "---\ntitle: broken\ndomain: harness\nrelates-to:\n"
               "  - path: ../nowhere/hn_ghost.md\n    rel: references\n"
               "status: in-progress\ncreated: 2026-04-22\n---\n")
        _git(["add", "docs/t36b/hn_broken_rt.md"], repo)
        out = _run_precheck(repo)
        assert out.get("pre_check_passed") == "false"
        _reset(repo)

    def test_anchor(self, integ_repo):
        """T36.3: 앵커 포함 → 통과"""
        repo = integ_repo
        _write(repo / "docs/t36c_target/hn_anchor_target.md",
               "---\ntitle: anchor target\ndomain: harness\nstatus: completed\ncreated: 2026-04-22\n---\n## section\n")
        _write(repo / "docs/t36c_src/hn_anchor_refer.md",
               "---\ntitle: anchor refer\ndomain: harness\nrelates-to:\n"
               "  - path: ../t36c_target/hn_anchor_target.md#section\n    rel: references\n"
               "status: in-progress\ncreated: 2026-04-22\n---\n")
        _git(["add", "docs/t36c_target/hn_anchor_target.md", "docs/t36c_src/hn_anchor_refer.md"], repo)
        out = _run_precheck(repo)
        assert out.get("pre_check_passed") == "true"
        _reset(repo)

    def test_target_also_staged(self, integ_repo):
        """T36.4: 대상도 같이 staged → 통과"""
        repo = integ_repo
        _write(repo / "docs/t36d_target/hn_staged.md",
               "---\ntitle: staged target\ndomain: harness\nstatus: in-progress\ncreated: 2026-04-22\n---\n")
        _write(repo / "docs/t36d_src/hn_staged_refer.md",
               "---\ntitle: staged refer\ndomain: harness\nrelates-to:\n"
               "  - path: ../t36d_target/hn_staged.md\n    rel: references\n"
               "status: in-progress\ncreated: 2026-04-22\n---\n")
        _git(["add", "docs/t36d_target/hn_staged.md", "docs/t36d_src/hn_staged_refer.md"], repo)
        out = _run_precheck(repo)
        assert out.get("pre_check_passed") == "true"
        _reset(repo)

    def test_multi_one_dead(self, integ_repo):
        """T36.5: 멀티 relates-to 중 1건 dead → 차단"""
        repo = integ_repo
        _write(repo / "docs/t36e_target/hn_ok.md",
               "---\ntitle: ok\ndomain: harness\nstatus: completed\ncreated: 2026-04-22\n---\n")
        _write(repo / "docs/t36e_src/hn_multi.md",
               "---\ntitle: multi\ndomain: harness\nrelates-to:\n"
               "  - path: ../t36e_target/hn_ok.md\n    rel: extends\n"
               "  - path: ../t36e_target/hn_missing.md\n    rel: references\n"
               "status: in-progress\ncreated: 2026-04-22\n---\n")
        _git(["add", "docs/t36e_target/hn_ok.md", "docs/t36e_src/hn_multi.md"], repo)
        out = _run_precheck(repo)
        assert out.get("pre_check_passed") == "false"
        _reset(repo)

    def test_no_path_field(self, integ_repo):
        """T36.6: path 없는 relates-to 항목 → 통과"""
        repo = integ_repo
        _write(repo / "docs/t36f/hn_norelatespath.md",
               "---\ntitle: no path\ndomain: harness\nrelates-to:\n"
               "  - rel: references\nstatus: in-progress\ncreated: 2026-04-22\n---\n")
        _git(["add", "docs/t36f/hn_norelatespath.md"], repo)
        out = _run_precheck(repo)
        assert out.get("pre_check_passed") == "true"
        _reset(repo)

    def test_docs_root_relative_exists(self, integ_repo):
        """T36.7: docs/ 루트 기준 경로 존재 → 통과"""
        repo = integ_repo
        _write(repo / "docs/t36g_target/hn_rootabs.md",
               "---\ntitle: root abs target\ndomain: harness\nstatus: completed\ncreated: 2026-04-22\n---\n")
        _write(repo / "docs/t36g_src/hn_rootabs_refer.md",
               "---\ntitle: root abs refer\ndomain: harness\nrelates-to:\n"
               "  - path: t36g_target/hn_rootabs.md\n    rel: extends\n"
               "status: in-progress\ncreated: 2026-04-22\n---\n")
        _git(["add", "docs/t36g_target/hn_rootabs.md", "docs/t36g_src/hn_rootabs_refer.md"], repo)
        out = _run_precheck(repo)
        assert out.get("pre_check_passed") == "true"
        _reset(repo)

    def test_docs_root_relative_missing(self, integ_repo):
        """T36.8: docs/ 루트 기준 미존재 → 차단"""
        repo = integ_repo
        _write(repo / "docs/t36h/hn_rootabs_broken.md",
               "---\ntitle: root abs broken\ndomain: harness\nrelates-to:\n"
               "  - path: nowhere/hn_ghost.md\n    rel: references\n"
               "status: in-progress\ncreated: 2026-04-22\n---\n")
        _git(["add", "docs/t36h/hn_rootabs_broken.md"], repo)
        out = _run_precheck(repo)
        assert out.get("pre_check_passed") == "false"
        _reset(repo)


class TestIntegMoveCommit:
    """T39: 각 테스트가 독립적인 파일명 사용 — module sandbox 상태 오염 방지."""

    def _prep(self, repo, name: str) -> None:
        """이름별 독립 WIP 파일 생성·커밋."""
        _write(repo / f"docs/WIP/incidents--hn_t39_{name}.md",
               f"---\ntitle: t39 {name}\ndomain: harness\nstatus: completed\ncreated: 2026-04-25\n---\n")
        _git(["add", f"docs/WIP/incidents--hn_t39_{name}.md"], repo)
        _commit(repo, f"prep T39 {name}")

    def test_rename_only(self, integ_repo):
        """T39.1: rename 단독 → skip"""
        repo = integ_repo
        self._prep(repo, "t1")
        _git(["mv", "docs/WIP/incidents--hn_t39_t1.md", "docs/incidents/hn_t39_t1.md"], repo)
        out = _run_precheck(repo)
        assert out.get("recommended_stage") == "skip"
        _reset(repo)

    def test_rename_plus_cluster(self, integ_repo):
        """T39.2: rename + cluster M → skip"""
        repo = integ_repo
        self._prep(repo, "t2")
        _git(["mv", "docs/WIP/incidents--hn_t39_t2.md", "docs/incidents/hn_t39_t2.md"], repo)
        cluster = repo / "docs/clusters/harness.md"
        cluster.write_text(cluster.read_text(encoding="utf-8") +
                           "\n- [t2](../incidents/hn_t39_t2.md)\n", encoding="utf-8")
        _git(["add", "docs/incidents/hn_t39_t2.md", "docs/clusters/harness.md"], repo)
        out = _run_precheck(repo)
        assert out.get("recommended_stage") == "skip"
        _reset(repo)

    def test_rename_plus_code(self, integ_repo):
        """T39.3: rename + 코드 M → skip 아님"""
        repo = integ_repo
        self._prep(repo, "t3")
        _git(["mv", "docs/WIP/incidents--hn_t39_t3.md", "docs/incidents/hn_t39_t3.md"], repo)
        extra = repo / "docs/t39_t3_extra.md"
        extra.write_text("---\ntitle: t3 extra\ndomain: harness\nstatus: in-progress\ncreated: 2026-04-25\n---\n",
                         encoding="utf-8")
        _git(["add", "docs/incidents/hn_t39_t3.md", str(extra)], repo)
        out = _run_precheck(repo)
        assert out.get("recommended_stage") != "skip"
        _reset(repo)
        extra.unlink(missing_ok=True)

    def test_rename_cluster_no_upgrade(self, integ_repo):
        """T39.4: rename + cluster → skip"""
        repo = integ_repo
        self._prep(repo, "t4")
        _git(["mv", "docs/WIP/incidents--hn_t39_t4.md", "docs/incidents/hn_t39_t4.md"], repo)
        cluster = repo / "docs/clusters/harness.md"
        cluster.write_text(cluster.read_text(encoding="utf-8") +
                           "\n- [t4](../incidents/hn_t39_t4.md)\n", encoding="utf-8")
        _git(["add", "docs/incidents/hn_t39_t4.md", "docs/clusters/harness.md"], repo)
        out = _run_precheck(repo)
        assert out.get("recommended_stage") == "skip"
        _reset(repo)


# ─────────────────────────────────────────────────────────
# T40: docs_ops.py wip-sync abbr 기반 보조 매칭
# ─────────────────────────────────────────────────────────

DOCS_OPS_PY = REPO_ROOT / ".claude" / "scripts" / "docs_ops.py"


@pytest.fixture(scope="function")
def wipsync_repo(tmp_path_factory):
    """T40 전용 sandbox: git clone + docs_ops.py + naming.md 최신 복사. function-scope로 격리."""
    tmp = tmp_path_factory.mktemp("wipsync")
    repo = tmp / "repo"
    subprocess.run(["git", "clone", "-q", str(REPO_ROOT), str(repo)],
                   capture_output=True, check=True)
    for name in ("docs_ops.py",):
        src = REPO_ROOT / ".claude" / "scripts" / name
        dst = repo / ".claude" / "scripts" / name
        if src.exists():
            shutil.copy2(src, dst)
    for name in ("naming.md",):
        src = REPO_ROOT / ".claude" / "rules" / name
        dst = repo / ".claude" / "rules" / name
        if src.exists():
            shutil.copy2(src, dst)
    yield repo


def _run_wip_sync(repo: Path, staged_files: list[str]) -> tuple[dict[str, str], str]:
    """docs_ops.py wip-sync 실행. (stdout key:value dict, stderr str) 반환."""
    r = subprocess.run(
        [sys.executable, ".claude/scripts/docs_ops.py", "wip-sync"] + staged_files,
        cwd=repo, capture_output=True, text=True,
    )
    out: dict[str, str] = {}
    for line in r.stdout.splitlines():
        if ": " in line:
            k, v = line.split(": ", 1)
            out[k] = v
    return out, r.stderr


def _add_path_domain_map(repo: Path, mapping_lines: str) -> None:
    """naming.md '## 경로 → 도메인 매핑' 섹션의 '실제 매핑' 코드블록에 매핑 라인 추가."""
    naming = repo / ".claude" / "rules" / "naming.md"
    text = naming.read_text(encoding="utf-8")
    section_start = text.find("## 경로 → 도메인 매핑")
    real_label = text.find("실제 매핑", section_start)
    if real_label == -1:
        return
    block_start = text.find("```", real_label)
    if block_start == -1:
        return
    insert_pos = text.find("\n", block_start) + 1
    text = text[:insert_pos] + mapping_lines + "\n" + text[insert_pos:]
    naming.write_text(text, encoding="utf-8")


def _remove_path_domain_map_lines(repo: Path, mapping_lines: str) -> None:
    """naming.md에서 추가한 매핑 라인 제거 (테스트 teardown용)."""
    naming = repo / ".claude" / "rules" / "naming.md"
    text = naming.read_text(encoding="utf-8")
    for line in mapping_lines.splitlines():
        text = text.replace(line + "\n", "")
    naming.write_text(text, encoding="utf-8")


class TestWipSyncAbbrMatch:
    """T40: wip-sync abbr 기반 보조 매칭."""

    WIP_CONTENT = (
        "---\ntitle: T40 incident\ndomain: harness\n"
        "status: in-progress\ncreated: 2026-04-27\n---\n\n"
        "# T40 incident\n\n## 증상\n서술형 내용. 체크리스트 없음.\n"
    )

    def test_abbr_match_no_checklist(self, wipsync_repo):
        """T40.1: 체크리스트 없는 incidents WIP + abbr 매칭 staged 파일 → 자동 이동."""
        repo = wipsync_repo
        mapping = "src/t40/**     → harness"
        _add_path_domain_map(repo, mapping)

        wip = repo / "docs/WIP/incidents--hn_t40_abbr_single.md"
        _write(wip, self.WIP_CONTENT)
        _git(["add", str(wip)], repo)
        _commit(repo, "T40.1 prep WIP")

        out, stderr = _run_wip_sync(repo, ["src/t40/serviceA.ts"])
        assert out.get("wip_sync_matched") == "1", f"stderr: {stderr}"
        assert out.get("wip_sync_moved") == "1", f"stderr: {stderr}"
        assert not wip.exists(), "WIP 파일이 이동되지 않음"

        _remove_path_domain_map_lines(repo, mapping)

    def test_abbr_multi_wip_skip(self, wipsync_repo):
        """T40.2: 같은 abbr WIP 2개 → 이동 skip, stderr 경고."""
        repo = wipsync_repo
        mapping = "src/t40b/**     → harness"
        _add_path_domain_map(repo, mapping)

        wip1 = repo / "docs/WIP/incidents--hn_t40b_first.md"
        wip2 = repo / "docs/WIP/incidents--hn_t40b_second.md"
        _write(wip1, self.WIP_CONTENT.replace("T40 incident", "T40b first"))
        _write(wip2, self.WIP_CONTENT.replace("T40 incident", "T40b second"))
        _git(["add", str(wip1), str(wip2)], repo)
        _commit(repo, "T40.2 prep WIP x2")

        out, stderr = _run_wip_sync(repo, ["src/t40b/serviceB.ts"])
        assert out.get("wip_sync_matched") == "0", f"stderr: {stderr}"
        assert "skip" in stderr.lower() or "2개" in stderr, f"stderr: {stderr}"
        assert wip1.exists() and wip2.exists()

        _git(["reset", "HEAD", "."], repo)
        _git(["clean", "-fdq"], repo)
        _remove_path_domain_map_lines(repo, mapping)

    def test_abbr_no_path_map_fallback(self, wipsync_repo):
        """T40.3: 경로→도메인 매핑 없으면 abbr 매칭 skip → 체크리스트 매칭만 동작."""
        repo = wipsync_repo
        wip = repo / "docs/WIP/incidents--hn_t40c_nomap.md"
        _write(wip, self.WIP_CONTENT.replace("T40 incident", "T40c nomap"))
        _git(["add", str(wip)], repo)
        _commit(repo, "T40.3 prep WIP nomap")

        out, stderr = _run_wip_sync(repo, ["src/t40c/serviceC.ts"])
        assert out.get("wip_sync_matched") == "0", f"stderr: {stderr}"
        assert wip.exists()

        _git(["reset", "HEAD", "."], repo)
        _git(["clean", "-fdq"], repo)
