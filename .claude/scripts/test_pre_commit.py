"""
pre_commit_check.py 회귀 테스트 (pytest)

단위 테스트: TEST_MODE=1 + 환경변수 주입 — git 호출 없음, ~80ms/케이스
통합 테스트: 실제 git sandbox — dead link·S10·이동 커밋 검증

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


def signals(out: dict) -> list[str]:
    return [s for s in out.get("signals", "").split(",") if s]


def stage(out: dict) -> str:
    return out.get("recommended_stage", "")


# ─────────────────────────────────────────────────────────
# 단위 테스트 — git 불필요
# ─────────────────────────────────────────────────────────

class TestS1:
    def test_helper_exempt(self):
        """T1: auth-helper.ts → S1 면제"""
        out = run_check(
            name_status="M src/auth-helper.ts",
            numstat="1 0 src/auth-helper.ts",
            diff_u0="+export const x = 1;\n",
        )
        assert "S1" not in signals(out)
        assert out.get("s1_level", "") == ""

    def test_file_only(self):
        """T2: auth.ts → S1 file-only"""
        out = run_check(
            name_status="M src/auth.ts",
            numstat="1 0 src/auth.ts",
            diff_u0="+export const validate = () => true;\n",
        )
        assert "S1" in signals(out)
        assert out.get("s1_level") == "file-only"

    def test_line_confirmed(self):
        """T3: 시크릿 패턴 → S1 line-confirmed + deep"""
        out = run_check(
            name_status="M src/config.ts",
            numstat="1 0 src/config.ts",
            diff_u0='+export const KEY = "sk_live_xxxxxxxxxxxxxxxx";\n',
        )
        assert "S1" in signals(out)
        assert out.get("s1_level") == "line-confirmed"
        assert stage(out) == "deep"


class TestStageSkip:
    def test_s5_clusters_only(self):
        """T4: clusters 단독 → S5 → skip"""
        out = run_check(
            name_status="M docs/clusters/harness.md",
            numstat="1 0 docs/clusters/harness.md",
            diff_u0="+한 줄 변경\n",
        )
        assert stage(out) == "skip"

    def test_s5_harness_json(self):
        """T30: HARNESS.json 단독 → S5 → skip"""
        out = run_check(
            name_status="M .claude/HARNESS.json",
            numstat='1 1 .claude/HARNESS.json',
            diff_u0='+"version": "0.20.19"',
        )
        assert stage(out) == "skip"

    def test_s6_docs_1line(self):
        """T37.1: docs 1줄 수정 → S6 ≤5줄 → skip"""
        out = run_check(
            name_status="M docs/guides/hn_probe.md",
            numstat="1 0 docs/guides/hn_probe.md",
            diff_u0="+추가 한 줄.\n",
        )
        assert stage(out) == "skip"

    def test_s6_docs_over5lines(self):
        """T37.2: docs 10줄 → standard"""
        out = run_check(
            name_status="M docs/guides/hn_probe2.md",
            numstat="10 0 docs/guides/hn_probe2.md",
            diff_u0="+줄1\n+줄2\n+줄3\n+줄4\n+줄5\n+줄6\n+줄7\n+줄8\n+줄9\n+줄10\n",
        )
        assert stage(out) != "skip"

    def test_s6_docs_with_code(self):
        """T37.3: docs + 코드 동반 → skip 아님"""
        out = run_check(
            name_status="M docs/guides/hn_probe3.md\nM src/foo.ts",
            numstat="1 0 docs/guides/hn_probe3.md\n1 0 src/foo.ts",
            diff_u0="+한줄.\n+export const foo = 1\n",
        )
        assert stage(out) != "skip"


class TestS8:
    def test_negative_test_file(self):
        """T5: *.test.ts → S8 음성"""
        out = run_check(
            name_status="M tests/foo.test.ts\nM src/comment.ts\nM src/internal.go",
            numstat="1 0 tests/foo.test.ts\n1 0 src/comment.ts\n1 0 src/internal.go",
            diff_u0=(
                "diff --git a/tests/foo.test.ts b/tests/foo.test.ts\n"
                "+export function setup() { return 1; }\n"
                "diff --git a/src/comment.ts b/src/comment.ts\n"
                '+const msg = "see export const X";\n'
                "diff --git a/src/internal.go b/src/internal.go\n"
                '+func handler() string { return "ok" }\n'
            ),
        )
        assert "S8" not in signals(out)

    def test_positive_ts_export(self):
        """T6: TS export function → S8 hit"""
        out = run_check(
            name_status="M src/api.ts\nM src/util.py\nM src/api.go",
            numstat="3 0 src/api.ts\n2 0 src/util.py\n2 0 src/api.go",
            diff_u0=(
                "diff --git a/src/api.ts b/src/api.ts\n"
                "+export function getUser(id: string) { return { id }; }\n"
                "diff --git a/src/util.py b/src/util.py\n"
                "+def calculate(x):\n+    return x * 2\n"
                "diff --git a/src/api.go b/src/api.go\n"
                '+func Handler() string { return "ok" }\n'
            ),
        )
        assert "S8" in signals(out)

    def test_positive_python_def(self):
        """T8: Python def → S8 hit"""
        out = run_check(
            name_status="M src/util.py",
            numstat="2 0 src/util.py",
            diff_u0=(
                "diff --git a/src/util.py b/src/util.py\n"
                "+def calculate(x):\n+    return x * 2\n"
            ),
        )
        assert "S8" in signals(out)

    def test_positive_go_exported(self):
        """T9: Go 대문자 func → S8 hit"""
        out = run_check(
            name_status="M src/api.go",
            numstat="2 0 src/api.go",
            diff_u0=(
                "diff --git a/src/api.go b/src/api.go\n"
                '+func Handler() string { return "ok" }\n'
            ),
        )
        assert "S8" in signals(out)


class TestStageDeep:
    def test_upstream_scripts(self):
        """T21: .claude/scripts → deep"""
        out = run_check(
            name_status="M .claude/scripts/foo.sh\nM .claude/agents/foo.md\nM .claude/hooks/pre.sh\nM .claude/settings.json",
            numstat="1 0 .claude/scripts/foo.sh\n1 0 .claude/agents/foo.md\n1 0 .claude/hooks/pre.sh\n1 0 .claude/settings.json",
            diff_u0="+#!/bin/bash\n+# agent\n+#!/bin/bash\n+{}\n",
        )
        assert stage(out) == "deep"

    def test_src_plus_scripts(self):
        """T31: src + scripts → deep"""
        out = run_check(
            name_status="M src/foo.ts\nM .claude/scripts/bar.sh",
            numstat="1 0 src/foo.ts\n1 0 .claude/scripts/bar.sh",
            diff_u0="+export const x = 1\n+#!/bin/bash\n",
        )
        assert stage(out) == "deep"


class TestStageStandard:
    def test_rules_not_deep(self):
        """T25-T27: rules·skills·CLAUDE.md → standard (not deep)"""
        out = run_check(
            name_status="M .claude/rules/foo.md\nM .claude/skills/foo/SKILL.md\nM CLAUDE.md",
            numstat="1 0 .claude/rules/foo.md\n1 0 .claude/skills/foo/SKILL.md\n5 0 CLAUDE.md",
            diff_u0="+# rule\n+# skill\n+# CLAUDE\n",
        )
        assert stage(out) == "standard"

    def test_docs_general(self):
        """T28: docs 일반 → standard"""
        out = run_check(
            name_status="M docs/guides/note.md",
            numstat="8 0 docs/guides/note.md",
            diff_u0="+---\n+title: 노트\n+domain: harness\n+status: completed\n+created: 2026-04-21\n+---\n+본문.\n",
        )
        assert stage(out) == "standard"

    def test_mixed_rules_docs_src(self):
        """T32: rules+docs+src(비-export) → standard"""
        out = run_check(
            name_status="M .claude/rules/foo.md\nM docs/guides/note.md\nM src/foo.ts",
            numstat="1 0 .claude/rules/foo.md\n8 0 docs/guides/note.md\n2 1 src/foo.ts",
            diff_u0="+# rule\n+본문.\n+const x = 1;\n",
        )
        assert stage(out) == "standard"


class TestSignalMix:
    def test_lock_doc_mix(self):
        """T16: lock + doc 혼합 → S4/S6 미발화"""
        out = run_check(
            name_status="M package-lock.json\nM docs/note.md",
            numstat="1 0 package-lock.json\n1 0 docs/note.md",
            diff_u0="+{}\n+# note\n",
        )
        assert "S4" not in signals(out)
        assert "S6" not in signals(out)
        assert stage(out) in ("standard", "micro", "deep")

    def test_meta_code_mix(self):
        """T17: meta + 코드 → S5 미발화, S7 발화"""
        out = run_check(
            name_status="M docs/clusters/harness.md\nM src/foo.ts",
            numstat="1 0 docs/clusters/harness.md\n1 0 src/foo.ts",
            diff_u0="+# clusters\n+export const x = 1\n",
        )
        assert "S5" not in signals(out)
        assert "S7" in signals(out)

    def test_s15_s7(self):
        """T18: package.json + 코드 → S15 + S7"""
        out = run_check(
            name_status="M src/bar.ts\nM package.json",
            numstat="1 1 src/bar.ts\n1 1 package.json",
            diff_u0=(
                '-export const x = 1\n+export const x = 2\n'
                '-"version":"0.0.1"\n+"version":"0.0.2"\n'
            ),
        )
        assert "S15" in signals(out)
        assert "S7" in signals(out)
        assert stage(out) in ("standard", "deep")


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
# 통합 테스트 — 실제 git sandbox 필요
# ─────────────────────────────────────────────────────────

def _git(args: list[str], cwd: Path, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args, cwd=cwd, capture_output=True, text=True, **kwargs
    )


def _run_precheck(repo: Path) -> dict[str, str]:
    # 상대경로 사용 — Windows Git Bash는 절대경로(C:\...)를 인식 못 함
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


class TestIntegS10:
    def test_s10_repeat_count(self, integ_repo):
        """T13: 3회 연속 수정 → S10, repeat_count max=2, exit 0"""
        repo = integ_repo
        f = repo / "docs" / "WIP" / "test--s10_probe.md"
        _write(f, "---\ntitle: t\ndomain: harness\nstatus: pending\ncreated: 2026-04-25\n---\n첫줄\n")
        _git(["add", str(f)], repo)
        _commit(repo, "T13 prep1")
        f.write_text(f.read_text() + "둘째\n", encoding="utf-8")
        _git(["add", str(f)], repo)
        _commit(repo, "T13 prep2")
        f.write_text(f.read_text() + "셋째\n", encoding="utf-8")
        _git(["add", str(f)], repo)

        r = subprocess.run(
            [sys.executable, ".claude/scripts/pre_commit_check.py"],
            cwd=repo, capture_output=True, text=True,
        )
        assert r.returncode == 0, "T13.1: 3회 연속 수정 차단 안 됨 (exit 0)"
        out: dict[str, str] = {}
        for line in r.stdout.splitlines():
            if ": " in line:
                k, v = line.split(": ", 1)
                out[k] = v
        assert out.get("repeat_count") == "max=2", f"T13.2: {out.get('repeat_count')}"
        _reset(repo)


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
        """이름별 독립 WIP 파일 생성·커밋 + S10용 더미 커밋."""
        _write(repo / f"docs/WIP/incidents--hn_t39_{name}.md",
               f"---\ntitle: t39 {name}\ndomain: harness\nstatus: completed\ncreated: 2026-04-25\n---\n")
        _git(["add", f"docs/WIP/incidents--hn_t39_{name}.md"], repo)
        _commit(repo, f"prep T39 {name}")
        _git(["commit", "--allow-empty", "-m", f"prep T39 {name} s10 v2"], repo)
        _git(["commit", "--allow-empty", "-m", f"prep T39 {name} s10 v3"], repo)

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
        # pre-commit-check.sh 대신 일반 파일을 수정 (sh 손상 방지)
        extra = repo / "docs/t39_t3_extra.md"
        extra.write_text("---\ntitle: t3 extra\ndomain: harness\nstatus: in-progress\ncreated: 2026-04-25\n---\n",
                         encoding="utf-8")
        _git(["add", "docs/incidents/hn_t39_t3.md", str(extra)], repo)
        out = _run_precheck(repo)
        assert out.get("recommended_stage") != "skip"
        _reset(repo)
        extra.unlink(missing_ok=True)

    def test_rename_cluster_s10(self, integ_repo):
        """T39.4: rename + cluster + S10 → skip (이동 커밋 S10 격상 면제)"""
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
    """naming.md '## 경로 → 도메인 매핑' 섹션 코드블록에 매핑 라인 추가."""
    naming = repo / ".claude" / "rules" / "naming.md"
    text = naming.read_text(encoding="utf-8")
    # 섹션 내 코드블록 첫 번째 ``` 뒤에 삽입
    section_start = text.find("## 경로 → 도메인 매핑")
    block_start = text.find("```", section_start)
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
        # 이동 후 WIP 파일 사라짐
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
        # WIP 파일들 그대로 남아있어야 함
        assert wip1.exists() and wip2.exists()

        _git(["reset", "HEAD", "."], repo)
        _git(["clean", "-fdq"], repo)
        _remove_path_domain_map_lines(repo, mapping)

    def test_abbr_no_path_map_fallback(self, wipsync_repo):
        """T40.3: 경로→도메인 매핑 없으면 abbr 매칭 skip → 체크리스트 매칭만 동작."""
        repo = wipsync_repo
        # 매핑 추가 없이 wip 생성
        wip = repo / "docs/WIP/incidents--hn_t40c_nomap.md"
        _write(wip, self.WIP_CONTENT.replace("T40 incident", "T40c nomap"))
        _git(["add", str(wip)], repo)
        _commit(repo, "T40.3 prep WIP nomap")

        out, stderr = _run_wip_sync(repo, ["src/t40c/serviceC.ts"])
        # 매핑 없으므로 matched=0
        assert out.get("wip_sync_matched") == "0", f"stderr: {stderr}"
        assert wip.exists()

        _git(["reset", "HEAD", "."], repo)
        _git(["clean", "-fdq"], repo)
