"""
pre_commit_check.py / docs_ops.py 회귀 테스트 (pytest)

**원칙: 매 커밋 무조건 실행 없음.** AC가 명시 요구할 때만 실행한다.
WIP AC `영향 범위:` 항목에 `pytest -m <marker> 회귀 체크`라 적혀 있으면
self-verify·review가 그 marker만 실행. 회귀 가드는 CI/eval --deep 트리거.

영역 marker:
- secret    : 시크릿 스캔 (3) — gitleaks 폴백 회귀 가드
- gate      : completed 전환 차단 룰 + completed 봉인 + init 게이트 (>10)
- stage     : pre_commit_check.py stage 결정 (4)
- enoent    : 린터 ENOENT 정규식 회귀 가드 (12)
- docs_ops  : dead link / relates-to / move commit / wip-sync (19)

사용:
  pytest -m gate            # 차단 룰만
  pytest -m "stage or gate" # stage + gate
  pytest                    # 전체 (CI/eval 전용)
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

REPO_ROOT = Path(__file__).parent.parent.parent.parent  # harness-starter/
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


def _clone_repo(dest: Path) -> None:
    """테스트 sandbox용 빠른 clone.

    반복 fixture setup이 전체 테스트 시간을 지배하므로 local object를 공유한다.
    sandbox는 테스트 종료 후 버려지며 push하지 않는다.
    """
    subprocess.run(
        ["git", "clone", "-q", "--shared", str(REPO_ROOT), str(dest)],
        capture_output=True,
        check=True,
    )


# ─────────────────────────────────────────────────────────
# T33·T34 — ENOENT 패턴 (Python로 직접 검증)
# ─────────────────────────────────────────────────────────

# SSOT: pre_commit_check.py의 ENOENT_PATTERNS를 직접 임포트
sys.path.insert(0, str(PY_SCRIPT.parent))
from pre_commit_check import ENOENT_PATTERNS as ENOENT_PAT  # noqa: E402


@pytest.mark.enoent
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


@pytest.mark.gate
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
# T43: commit_finalize.sh wrapper (v0.32.x 메커니즘 차단)
# ─────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def finalize_repo(tmp_path_factory):
    """commit_finalize.sh 테스트 sandbox: 본 repo clone + wrapper 복사."""
    tmp = tmp_path_factory.mktemp("finalize")
    repo = tmp / "repo"
    _clone_repo(repo)
    # wrapper + docs_ops가 working tree에만 있을 수 있어 복사
    for name in ("commit_finalize.sh", "docs_ops.py"):
        src = REPO_ROOT / ".claude" / "scripts" / name
        dst = repo / ".claude" / "scripts" / name
        if src.exists():
            shutil.copy2(src, dst)
            if name.endswith(".sh"):
                os.chmod(dst, 0o755)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@test"],
                   capture_output=True, check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "test"],
                   capture_output=True, check=True)
    yield repo


@pytest.mark.gate
class TestCommitFinalize:
    """T43: wrapper가 wip-sync + git commit 단일 흐름 처리."""

    def _run_wrapper(self, repo, env_extra: dict, *args) -> subprocess.CompletedProcess:
        # Windows subprocess env 전달 결함 회피 — 명시 env 합치고 inline 인자로
        prefix_parts = ["HARNESS_DEV=1"]
        for k, v in env_extra.items():
            prefix_parts.append(f"{k}={v}")
        prefix = " ".join(prefix_parts)
        # 인자 escape (테스트 메시지는 단순)
        arg_str = " ".join(f'"{a}"' for a in args)
        cmd = f"{prefix} bash .claude/scripts/commit_finalize.sh {arg_str}"
        return subprocess.run(
            ["bash", "-c", cmd],
            cwd=repo, capture_output=True, text=True,
        )

    def test_no_harness_dev_blocks(self, finalize_repo):
        """HARNESS_DEV 누락 → exit 2."""
        repo = finalize_repo
        env = {k: v for k, v in os.environ.items() if k != "HARNESS_DEV"}
        r = subprocess.run(
            ["bash", ".claude/scripts/commit_finalize.sh", "-m", "test"],
            cwd=repo, env=env, capture_output=True, text=True,
        )
        assert r.returncode == 2
        assert "HARNESS_DEV=1" in (r.stderr + r.stdout)

    def test_simple_commit_passes(self, finalize_repo):
        """staged 변경 + wrapper 호출 → 단일 commit 생성."""
        repo = finalize_repo
        target = repo / "test_file.txt"
        target.write_text("hello\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", str(target)], capture_output=True, check=True)
        before = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                                capture_output=True, text=True).stdout.strip()
        r = self._run_wrapper(repo, {"VERDICT": "pass"}, "-m", "test commit")
        assert r.returncode == 0, f"output: {r.stderr + r.stdout}"
        after = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                               capture_output=True, text=True).stdout.strip()
        assert before != after, "commit이 생성 안 됨"

    def test_block_skips_wip_sync(self, finalize_repo):
        """VERDICT=block이면 wip-sync skip하지만 git commit은 진행."""
        repo = finalize_repo
        target = repo / "test_block.txt"
        target.write_text("blocked\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", str(target)], capture_output=True, check=True)
        r = self._run_wrapper(repo, {"VERDICT": "block"}, "-m", "block test")
        assert r.returncode == 0, f"output: {r.stderr + r.stdout}"
        # wip_sync_matched 출력이 stdout에 없으면 wip-sync skip된 것
        assert "wip_sync_matched" not in (r.stderr + r.stdout), (
            f"VERDICT=block인데 wip-sync 실행됨:\n{r.stderr + r.stdout}"
        )


# ─────────────────────────────────────────────────────────
# T42: completed 봉인 게이트 (v0.31.x 자기증명 사고 대응)
# ─────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def sealed_repo(tmp_path_factory):
    """completed 봉인 테스트 sandbox: 본 repo clone + completed 문서 1개 commit."""
    tmp = tmp_path_factory.mktemp("sealed")
    repo = tmp / "repo"
    _clone_repo(repo)
    src = REPO_ROOT / ".claude" / "scripts" / "pre_commit_check.py"
    dst = repo / ".claude" / "scripts" / "pre_commit_check.py"
    if src.exists():
        shutil.copy2(src, dst)
    # completed 문서 신규 추가 (clean baseline)
    target = repo / "docs/decisions/hn_t42_seal.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "---\ntitle: T42 sealed\ndomain: harness\nproblem: P5\n"
        "solution-ref:\n  - S5 — \"테스트 픽스처 (부분)\"\n"
        "status: completed\ncreated: 2026-05-02\n---\n\n"
        "# T42\n\n## 결정\n원본 본문.\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "-C", str(repo), "add", str(target)], capture_output=True, check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "T42 prep sealed"],
                   capture_output=True, check=True)
    yield repo, target


@pytest.mark.gate
class TestCompletedSeal:
    """T42: completed 봉인 — status: completed 문서 본문 무단 변경 차단."""

    def test_body_change_blocks(self, sealed_repo):
        """본문 줄 추가 → exit 2 차단."""
        repo, target = sealed_repo
        text = target.read_text(encoding="utf-8")
        target.write_text(text + "\n무단 본문 추가.\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", str(target)], capture_output=True)
        r = subprocess.run(
            [sys.executable, ".claude/scripts/pre_commit_check.py"],
            cwd=repo, capture_output=True, text=True,
        )
        assert r.returncode == 2, f"exit={r.returncode} stderr={r.stderr}"
        assert "completed 문서 본문 무단 변경 감지" in (r.stderr + r.stdout)

    def test_change_history_section_exempt(self, sealed_repo):
        """## 변경 이력 섹션 신규 항목 추가 → 면제."""
        repo, target = sealed_repo
        text = target.read_text(encoding="utf-8")
        new_text = text + "\n## 변경 이력\n\n### v0.31.3 (2026-05-02)\n새 갱신 항목.\n"
        target.write_text(new_text, encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", str(target)], capture_output=True)
        r = subprocess.run(
            [sys.executable, ".claude/scripts/pre_commit_check.py"],
            cwd=repo, capture_output=True, text=True,
        )
        # 본 게이트는 통과해야 함 (다른 게이트 fail은 무관)
        assert "completed 문서 본문 무단 변경 감지" not in (r.stderr + r.stdout), f"output: {r.stderr + r.stdout}"

    def test_updated_field_only_exempt(self, sealed_repo):
        """frontmatter updated 필드만 변경 → 면제."""
        repo, target = sealed_repo
        text = target.read_text(encoding="utf-8")
        new_text = text.replace("created: 2026-05-02\n",
                                "created: 2026-05-02\nupdated: 2026-05-03\n")
        target.write_text(new_text, encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", str(target)], capture_output=True)
        r = subprocess.run(
            [sys.executable, ".claude/scripts/pre_commit_check.py"],
            cwd=repo, capture_output=True, text=True,
        )
        assert "completed 문서 본문 무단 변경 감지" not in (r.stderr + r.stdout), f"output: {r.stderr + r.stdout}"

    def test_rename_exempt(self, sealed_repo):
        """파일 rename (이동) → 면제 (M이 아닌 R)."""
        repo, target = sealed_repo
        new_path = target.parent.parent / "archived" / target.name
        new_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "-C", str(repo), "mv", str(target), str(new_path)],
                       capture_output=True)
        r = subprocess.run(
            [sys.executable, ".claude/scripts/pre_commit_check.py"],
            cwd=repo, capture_output=True, text=True,
        )
        assert "completed 문서 본문 무단 변경 감지" not in (r.stderr + r.stdout), f"output: {r.stderr + r.stdout}"

    def test_in_progress_not_blocked(self, sealed_repo):
        """status: in-progress 문서 본문 변경 → 통과 (게이트 미적용)."""
        repo, target = sealed_repo
        text = target.read_text(encoding="utf-8").replace(
            "status: completed", "status: in-progress"
        )
        target.write_text(text + "\n자유 변경.\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", str(target)], capture_output=True)
        r = subprocess.run(
            [sys.executable, ".claude/scripts/pre_commit_check.py"],
            cwd=repo, capture_output=True, text=True,
        )
        assert "completed 문서 본문 무단 변경 감지" not in (r.stderr + r.stdout), f"output: {r.stderr + r.stdout}"

    def test_relates_to_path_fix_exempt(self, sealed_repo):
        """T42.6: completed 문서의 relates-to path 경로 수정 → 봉인 통과 (dead-link 복구 허용).

        WIP 이동 후 역참조 미갱신으로 dead-link가 생긴 경우, completed 봉인이
        경로 수정을 막으면 영구 루프 발생 — path: 라인 변경은 면제.
        """
        repo, _ = sealed_repo
        # relates-to 있는 completed 문서 추가
        doc = repo / "docs/decisions/hn_t42_6_rt.md"
        target = repo / "docs/decisions/hn_t42_6_target.md"
        target.write_text(
            "---\ntitle: target\ndomain: harness\nstatus: completed\n"
            "created: 2026-05-03\n---\n# target\n",
            encoding="utf-8"
        )
        doc.write_text(
            "---\ntitle: T42.6 relates-to path fix\ndomain: harness\nproblem: P3\n"
            "solution-ref:\n  - S3 — \"test\"\n"
            "relates-to:\n  - path: WIP/decisions--hn_t42_6_old.md\n    rel: references\n"
            "status: completed\ncreated: 2026-05-03\n---\n\n# T42.6\n본문.\n",
            encoding="utf-8"
        )
        subprocess.run(["git", "-C", str(repo), "add", str(doc), str(target)], capture_output=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "T42.6 prep"],
                       capture_output=True)
        # dead-link 복구: WIP 경로 → decisions/ 경로로 수정
        doc.write_text(
            "---\ntitle: T42.6 relates-to path fix\ndomain: harness\nproblem: P3\n"
            "solution-ref:\n  - S3 — \"test\"\n"
            "relates-to:\n  - path: decisions/hn_t42_6_target.md\n    rel: references\n"
            "status: completed\ncreated: 2026-05-03\n---\n\n# T42.6\n본문.\n",
            encoding="utf-8"
        )
        subprocess.run(["git", "-C", str(repo), "add", str(doc)], capture_output=True)
        r = subprocess.run(
            [sys.executable, ".claude/scripts/pre_commit_check.py"],
            cwd=repo, capture_output=True, text=True,
        )
        assert "completed 문서 본문 무단 변경 감지" not in (r.stderr + r.stdout), \
            f"relates-to path 수정이 봉인에서 차단됨. output: {r.stderr + r.stdout}"

    def test_migrations_md_exempt(self, sealed_repo):
        """T42.5: docs/harness/MIGRATIONS.md status: completed + 본문 변경 → 통과.

        다운스트림 harness-upgrade가 MIGRATIONS.md를 정기적으로 덮어쓰는
        upstream 운영 누적 파일이라 SEALED 면제 (incident 2026-05-02 다운스트림 보고).
        """
        repo, _ = sealed_repo
        mig = repo / "docs" / "harness" / "MIGRATIONS.md"
        mig.parent.mkdir(parents=True, exist_ok=True)
        mig.write_text(
            "---\ntitle: MIGRATIONS\ndomain: harness\nstatus: completed\n"
            "created: 2026-04-16\n---\n\n## v0.33.0\n초기 본문.\n",
            encoding="utf-8"
        )
        subprocess.run(["git", "-C", str(repo), "add", str(mig)], capture_output=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-m", "init MIGRATIONS"],
                       capture_output=True, env={**os.environ, "HARNESS_DEV": "1"})
        # upstream 덮어쓰기 시뮬: 새 버전 섹션 추가
        mig.write_text(
            "---\ntitle: MIGRATIONS\ndomain: harness\nstatus: completed\n"
            "created: 2026-04-16\n---\n\n## v0.34.0\n신규 변경.\n\n## v0.33.0\n초기 본문.\n",
            encoding="utf-8"
        )
        subprocess.run(["git", "-C", str(repo), "add", str(mig)], capture_output=True)
        r = subprocess.run(
            [sys.executable, ".claude/scripts/pre_commit_check.py"],
            cwd=repo, capture_output=True, text=True,
        )
        assert "completed 문서 본문 무단 변경 감지" not in (r.stderr + r.stdout), \
            f"MIGRATIONS.md가 SEALED 면제되어야 함. output: {r.stderr + r.stdout}"

    def test_body_link_path_replace_exempt(self, sealed_repo):
        """T42.7: completed 문서 본문의 마크다운 링크 경로 교체 → 봉인 통과.

        archived 이동 후 dead-link 복구 케이스: 기존 링크 라인을 삭제하고
        같은 텍스트·다른 경로로 교체할 때 봉인에서 차단되지 않아야 한다.
        """
        repo, _ = sealed_repo
        doc = repo / "docs/decisions/hn_t42_7_link.md"
        doc.parent.mkdir(parents=True, exist_ok=True)
        doc.write_text(
            "---\ntitle: T42.7 link\ndomain: harness\nproblem: P5\n"
            "solution-ref:\n  - S5 — \"테스트 픽스처 (부분)\"\n"
            "status: completed\ncreated: 2026-05-04\n---\n\n"
            "자세한 내용은 [이전 결정](decisions/hn_old_decision.md)을 참고.\n",
            encoding="utf-8"
        )
        subprocess.run(["git", "-C", str(repo), "add", str(doc)], capture_output=True, check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-m", "T42.7 prep link"],
                       capture_output=True, env={**os.environ, "HARNESS_DEV": "1"}, check=True)
        # archived로 이동 후 링크 경로만 교체
        new_text = doc.read_text(encoding="utf-8").replace(
            "[이전 결정](decisions/hn_old_decision.md)",
            "[이전 결정](../archived/hn_old_decision.md)"
        )
        doc.write_text(new_text, encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", str(doc)], capture_output=True)
        r = subprocess.run(
            [sys.executable, ".claude/scripts/pre_commit_check.py"],
            cwd=repo, capture_output=True, text=True,
        )
        assert "completed 문서 본문 무단 변경 감지" not in (r.stderr + r.stdout), \
            f"링크 경로 교체가 봉인에서 차단됨. output: {r.stderr + r.stdout}"

    def test_body_link_new_addition_blocks(self, sealed_repo):
        """T42.8: completed 문서 본문에 새 링크 줄 추가(교체 아님) → 봉인 차단.

        삭제(-) 없이 순수 추가(+)인 경우는 링크라도 차단해야 한다.
        """
        repo, _ = sealed_repo
        doc = repo / "docs/decisions/hn_t42_8_newlink.md"
        doc.parent.mkdir(parents=True, exist_ok=True)
        doc.write_text(
            "---\ntitle: T42.8 newlink\ndomain: harness\nproblem: P5\n"
            "solution-ref:\n  - S5 — \"테스트 픽스처 (부분)\"\n"
            "status: completed\ncreated: 2026-05-04\n---\n\n"
            "기존 본문.\n",
            encoding="utf-8"
        )
        subprocess.run(["git", "-C", str(repo), "add", str(doc)], capture_output=True, check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-m", "T42.8 prep newlink"],
                       capture_output=True, env={**os.environ, "HARNESS_DEV": "1"}, check=True)
        # 순수 추가: 기존 본문 유지 + 새 링크 줄 추가
        doc.write_text(
            doc.read_text(encoding="utf-8") + "\n새로 추가된 [링크](decisions/hn_new.md).\n",
            encoding="utf-8"
        )
        subprocess.run(["git", "-C", str(repo), "add", str(doc)], capture_output=True)
        r = subprocess.run(
            [sys.executable, ".claude/scripts/pre_commit_check.py"],
            cwd=repo, capture_output=True, text=True,
        )
        assert "completed 문서 본문 무단 변경 감지" in (r.stderr + r.stdout), \
            f"새 링크 추가가 봉인에서 통과되면 안 됨. output: {r.stderr + r.stdout}"

    def test_reopen_move_cycle_exempt(self, sealed_repo):
        """T42.9: reopen→수정→move 정상 절차 경유 → 봉인 면제.

        rename 두 번 상쇄로 git이 M으로 분류하더라도,
        docs_ops.py move가 session-moved-docs.txt에 기록한 경로면 면제.
        incidents/hn_sealed_reopen_false_block.md
        """
        repo, _ = sealed_repo
        # completed 문서 생성
        doc = repo / "docs/decisions/hn_t42_9_reopen.md"
        doc.parent.mkdir(parents=True, exist_ok=True)
        original = (
            "---\ntitle: T42.9 reopen\ndomain: harness\nproblem: P6\n"
            "solution-ref:\n  - S6 — \"테스트 픽스처 (부분)\"\n"
            "status: completed\ncreated: 2026-05-08\n---\n\n"
            "원본 본문.\n"
        )
        doc.write_text(original, encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", str(doc)], capture_output=True, check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-m", "T42.9 prep"],
                       capture_output=True, env={**os.environ, "HARNESS_DEV": "1"}, check=True)

        # reopen: git mv → WIP + status: in-progress
        wip = repo / "docs/WIP/decisions--hn_t42_9_reopen.md"
        (repo / "docs/WIP").mkdir(exist_ok=True)
        subprocess.run(["git", "-C", str(repo), "mv",
                        str(doc.relative_to(repo)), str(wip.relative_to(repo))],
                       capture_output=True, check=True)
        wip.write_text(original.replace("status: completed", "status: in-progress"), encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", str(wip)], capture_output=True)

        # 사용자 본문 수정
        wip.write_text(wip.read_text(encoding="utf-8") + "\n새로운 본문 추가.\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", str(wip)], capture_output=True)

        # move: git mv → decisions/ + status: completed
        subprocess.run(["git", "-C", str(repo), "mv",
                        str(wip.relative_to(repo)), str(doc.relative_to(repo))],
                       capture_output=True, check=True)
        doc.write_text(
            doc.read_text(encoding="utf-8").replace("status: in-progress", "status: completed"),
            encoding="utf-8"
        )
        subprocess.run(["git", "-C", str(repo), "add", str(doc)], capture_output=True)

        # docs_ops.py move 효과 시뮬레이션: session-moved-docs.txt에 경로 기록
        session_file = repo / ".claude/memory/session-moved-docs.txt"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text("docs/decisions/hn_t42_9_reopen.md\n", encoding="utf-8")

        r = subprocess.run(
            [sys.executable, ".claude/scripts/pre_commit_check.py"],
            cwd=repo, capture_output=True, text=True,
        )
        assert "completed 문서 본문 무단 변경 감지" not in (r.stderr + r.stdout), \
            f"reopen→move 정상 절차가 봉인에서 차단됨. output: {r.stderr + r.stdout}"

    def test_status_change_without_reopen_blocks(self, sealed_repo):
        """T42.10: reopen 없이 completed 문서 본문 수정 → 세션 파일 없으면 여전히 차단.

        session-moved-docs.txt 없이 M 파일이 있으면 봉인 차단 유지.
        """
        repo, target = sealed_repo
        # session-moved-docs.txt가 없는 상태에서 본문만 추가
        original = target.read_text(encoding="utf-8")
        target.write_text(original + "\n무단 추가.\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", str(target)], capture_output=True)

        r = subprocess.run(
            [sys.executable, ".claude/scripts/pre_commit_check.py"],
            cwd=repo, capture_output=True, text=True,
        )
        assert "completed 문서 본문 무단 변경 감지" in (r.stderr + r.stdout), \
            f"무단 본문 변경이 봉인에서 통과되면 안 됨. output: {r.stderr + r.stdout}"


# ─────────────────────────────────────────────────────────
# implementation Step 0 init 게이트 (A4 의미 재정의, v0.34.0)
# ─────────────────────────────────────────────────────────

@pytest.mark.gate
class TestInitGate:
    """check_init_done.sh — A4 의미 재정의 회귀 가드.

    decisions/hn_init_gate_redesign.md ADR. drift 감지가 아닌
    "init 안 돈 신규 프로젝트만 차단".
    """

    SCRIPT_SRC = REPO_ROOT / ".claude" / "scripts" / "check_init_done.sh"

    @pytest.fixture
    def init_repo(self, tmp_path):
        """tmp 작업 디렉토리에 docs/guides/ + 스크립트 복사."""
        (tmp_path / "docs" / "guides").mkdir(parents=True)
        script_dir = tmp_path / ".claude" / "scripts"
        script_dir.mkdir(parents=True)
        shutil.copy(self.SCRIPT_SRC, script_dir / "check_init_done.sh")
        return tmp_path

    def test_kickoff_missing_blocks(self, init_repo):
        """project_kickoff.md 부재 → exit 2."""
        r = subprocess.run(
            ["bash", ".claude/scripts/check_init_done.sh"],
            cwd=init_repo, capture_output=True, text=True,
        )
        assert r.returncode == 2, f"부재 시 차단되어야 함. output: {r.stderr}"
        assert "부재" in r.stderr

    def test_kickoff_sample_only_blocks(self, init_repo):
        """project_kickoff.md status: sample 단독 → exit 2."""
        kickoff = init_repo / "docs" / "guides" / "project_kickoff.md"
        kickoff.write_text(
            "---\ntitle: kickoff sample\nstatus: sample\ncreated: 2026-04-16\n---\n\n# sample\n",
            encoding="utf-8"
        )
        r = subprocess.run(
            ["bash", ".claude/scripts/check_init_done.sh"],
            cwd=init_repo, capture_output=True, text=True,
        )
        assert r.returncode == 2, f"sample 단독 시 차단되어야 함. output: {r.stderr}"
        assert "sample" in r.stderr

    def test_kickoff_in_progress_passes(self, init_repo):
        """project_kickoff.md status: in-progress → exit 0."""
        kickoff = init_repo / "docs" / "guides" / "project_kickoff.md"
        kickoff.write_text(
            "---\ntitle: real kickoff\nstatus: in-progress\ncreated: 2026-04-16\n---\n",
            encoding="utf-8"
        )
        r = subprocess.run(
            ["bash", ".claude/scripts/check_init_done.sh"],
            cwd=init_repo, capture_output=True, text=True,
        )
        assert r.returncode == 0, f"in-progress 통과 실패: {r.stderr}"

    def test_kickoff_completed_passes(self, init_repo):
        """project_kickoff.md status: completed → exit 0."""
        kickoff = init_repo / "docs" / "guides" / "project_kickoff.md"
        kickoff.write_text(
            "---\ntitle: completed kickoff\nstatus: completed\ncreated: 2026-04-16\n---\n",
            encoding="utf-8"
        )
        r = subprocess.run(
            ["bash", ".claude/scripts/check_init_done.sh"],
            cwd=init_repo, capture_output=True, text=True,
        )
        assert r.returncode == 0, f"completed 통과 실패: {r.stderr}"

    def test_kickoff_sample_with_inline_comment_blocks(self, init_repo):
        """status: sample # comment (YAML 인라인 주석) → exit 2.

        review 지적사항 회귀 가드 (2026-05-02). YAML 스펙상 인라인 주석
        허용이라 status 값 뒤에 주석이 와도 차단 정상 작동해야.
        """
        kickoff = init_repo / "docs" / "guides" / "project_kickoff.md"
        kickoff.write_text(
            "---\ntitle: kickoff\nstatus: sample  # placeholder\ncreated: 2026-04-16\n---\n",
            encoding="utf-8"
        )
        r = subprocess.run(
            ["bash", ".claude/scripts/check_init_done.sh"],
            cwd=init_repo, capture_output=True, text=True,
        )
        assert r.returncode == 2, f"인라인 주석 sample도 차단되어야 함: {r.stderr}"

    def test_drift_does_not_block(self, init_repo, tmp_path):
        """CLAUDE.md `## 환경` 양식 drift는 차단 사유 아님.

        다운스트림이 자기 양식으로 채울 자유. 본 스크립트는 CLAUDE.md를
        검사하지 않는다 — kickoff만 본다.
        """
        kickoff = init_repo / "docs" / "guides" / "project_kickoff.md"
        kickoff.write_text(
            "---\ntitle: real kickoff\nstatus: in-progress\ncreated: 2026-04-16\n---\n",
            encoding="utf-8"
        )
        # CLAUDE.md를 비정상 양식(키 부재)으로 만들어도 영향 없어야
        (init_repo / "CLAUDE.md").write_text(
            "# CLAUDE\n## 환경\n- 언어: C++17\n- 빌드: CMake\n",
            encoding="utf-8"
        )
        r = subprocess.run(
            ["bash", ".claude/scripts/check_init_done.sh"],
            cwd=init_repo, capture_output=True, text=True,
        )
        assert r.returncode == 0, f"drift는 차단 사유 아님: {r.stderr}"


# ─────────────────────────────────────────────────────────
# 시크릿 스캔 단위 테스트
# ─────────────────────────────────────────────────────────

@pytest.mark.secret
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

    def test_harness_doc_line_exempt(self):
        """.claude/agents/*.md 같은 패턴 SSOT 문서는 line 스캔 면제 (incident hn_secret_line_exempt_gap)"""
        out = run_check(
            name_status="M .claude/agents/threat-analyst.md",
            numstat="1 0 .claude/agents/threat-analyst.md",
            diff_u0=(
                "diff --git a/.claude/agents/threat-analyst.md b/.claude/agents/threat-analyst.md\n"
                "+패턴: sb_secret_|service_role|sk_live_|sk_test_|ghp_|AKIA[0-9A-Z]{16}|password\\s*=\n"
            ),
        )
        assert out.get("s1_level", "") == ""
        assert out.get("pre_check_passed") == "true"

    def test_supabase_migration_sql_exempt(self):
        """supabase/migrations/*.sql의 PostgreSQL role 이름 service_role은 line 스캔 면제"""
        out = run_check(
            name_status="M supabase/migrations/20240101_rls.sql",
            numstat="3 0 supabase/migrations/20240101_rls.sql",
            diff_u0=(
                "diff --git a/supabase/migrations/20240101_rls.sql b/supabase/migrations/20240101_rls.sql\n"
                "+GRANT EXECUTE ON FUNCTION public.foo() TO service_role;\n"
                "+REVOKE ALL ON TABLE public.bar FROM service_role;\n"
                "+CREATE POLICY \"svc\" ON tbl FOR ALL USING ((auth.jwt() ->> 'role') = 'service_role');\n"
            ),
        )
        assert out.get("s1_level", "") == ""
        assert out.get("pre_check_passed") == "true"


# ─────────────────────────────────────────────────────────
# Stage 기본 단위 테스트 (AC kind 기반)
# ─────────────────────────────────────────────────────────

@pytest.mark.stage
class TestStageBasic:
    """Phase 2-A 외형 metric 폐기 후 (v0.29.1) — 모든 stage 결정은 AC + CPS.

    외형 metric 룰 (UPSTREAM_PAT·docs 5줄·WIP 단독·rename/meta 단독)은 통합 테스트
    (TestIntegMoveCommit·TestACBasedStage)로 이전. 단위 테스트는 시크릿 게이트만.
    """

    def test_secret_line_confirmed_deep(self):
        """시크릿 line-confirmed → deep (보안 게이트, AC 무관)"""
        out = run_check(
            name_status="M src/foo.ts",
            numstat="1 0 src/foo.ts",
            diff_u0="+const k = 'AKIAIOSFODNN7EXAMPLE';\n",
        )
        assert stage(out) == "deep"

    def test_no_wip_no_secret_standard(self):
        """staged WIP 없고 시크릿 없으면 standard 폴백 (보수)"""
        out = run_check(
            name_status="M src/foo.ts",
            numstat="2 0 src/foo.ts",
            diff_u0="+const x = 1;\n",
        )
        assert stage(out) == "standard"


@pytest.mark.stage
class TestAgentsBridgeSync:
    """§H-9 — .claude/skills/ ↔ .agents/skills/ SKILL.md 동기화 회귀 가드.

    Codex 브리지(.agents)는 Claude Code 본 SKILL(.claude)의 본문 복제.
    drift 방지 — 두 파일 내용이 LF 차이 외에는 동일해야 한다.
    """

    def test_commit_skill_synced(self):
        """`.claude/skills/commit/SKILL.md` ≡ `.agents/skills/commit/SKILL.md` (LF 차이 외)."""
        claude_src = (REPO_ROOT / ".claude/skills/commit/SKILL.md").read_bytes()
        agents_src = (REPO_ROOT / ".agents/skills/commit/SKILL.md").read_bytes()
        # CRLF → LF로 정규화 후 비교
        assert claude_src.replace(b"\r\n", b"\n") == agents_src, \
            ".claude/skills/commit/SKILL.md ↔ .agents/skills/commit/SKILL.md drift 감지 — .agents 동기화 필요"


@pytest.mark.stage
class TestSplitCommitNonDestructive:
    """§H-3 — split-commit.sh 비파괴 planner 회귀 가드.

    기본 실행은 staged 상태 무변경, `--apply` 시에만 destructive 동작.
    SKILL 자연어 호출부 변경(SKILL.md Step 5.5)은 본문 grep으로 정합 검증.
    """

    SCRIPT = REPO_ROOT / ".claude/scripts/split-commit.sh"

    # NOTE: bash -n syntax 검사는 본 wave에서 제거.
    # split-commit.sh 자체가 CRLF로 들어가 있어 pytest subprocess(bash -n) 환경에서
    # `do\r` 토큰 오류로 실패. SHELLOPTS=igncr 우회 가능하나, 근본 해결은 .sh 파일
    # LF 정규화 — followups §H-10 별 wave 후보 (.gitattributes + 변환).
    # 본 wave는 비파괴 로직의 grep 정합으로 회귀 가드 충분.

    def test_apply_flag_and_non_destructive_branch(self):
        """본문 grep 정합 — APPLY 변수·--apply 인자·비파괴 분기·CRLF 가드."""
        script = self.SCRIPT.read_text(encoding="utf-8")
        assert "APPLY=0" in script, "기본값 APPLY=0 누락"
        assert "--apply)" in script, "--apply 인자 case 누락"
        assert 'if [ "$APPLY" != 1 ]' in script, "비파괴 분기 (APPLY != 1) 누락"
        assert "check_crlf_sh" in script, "CRLF 가드 함수 누락"
        # destructive 블록은 비파괴 분기 안쪽에만 존재해야 함
        # (단순 검증: 'git reset HEAD' 등장 위치가 APPLY != 1 분기 이후여야)
        idx_non_destructive = script.find('if [ "$APPLY" != 1 ]')
        idx_reset = script.find("git reset HEAD --")
        assert idx_non_destructive > 0 and idx_reset > 0, "필수 패턴 누락"
        # 첫 번째 git reset HEAD --는 split-plan.txt 재진입(line 44)에 있음 (이미 --apply 흐름)
        # destructive 메인 블록의 git reset은 비파괴 분기 이후
        idx_reset_main = script.find("git reset HEAD --", idx_non_destructive)
        assert idx_reset_main > idx_non_destructive, "destructive 블록이 --apply 분기 안에 있어야 함"


@pytest.mark.stage
class TestRouteOutput:
    """§H-1 — route 신호 stdout 출력 회귀 가드.

    pre_commit_check.py에 commit_route/review_route/promotion/side_effects.*
    4축 6키가 추가됐는지, 기존 키와 공존하는지, 차단 케이스에서도 출력되는지
    검증. 소비는 후속 wave (§H-2 commit/SKILL.md) — 본 wave는 스키마 freeze만.
    """

    ROUTE_KEYS = (
        "commit_route",
        "review_route",
        "promotion",
        "side_effects.required",
        "side_effects.release",
        "side_effects.repair",
    )

    def test_route_keys_present_in_normal_case(self):
        """일반 코드 변경에서 4축 6키가 모두 출력된다."""
        out = run_check(
            name_status="M src/foo.ts",
            numstat="2 0 src/foo.ts",
            diff_u0="+const x = 1;\n",
        )
        for key in self.ROUTE_KEYS:
            assert key in out, f"missing route key: {key}"
        # 기본값: single / standard / none / none / none / none
        assert out["commit_route"] == "single"
        assert out["review_route"] == "standard"
        assert out["promotion"] == "none"
        assert out["side_effects.required"] == "none"
        assert out["side_effects.release"] == "none"
        assert out["side_effects.repair"] == "none"
        # 기존 키 회귀 가드 — route 추가가 기존 스키마를 깨지 않음
        assert "pre_check_passed" in out
        assert "recommended_stage" in out
        assert "split_action_recommended" in out

    def test_secret_block_still_emits_routes(self):
        """시크릿 line-confirmed 차단 (ERRORS>0) 시에도 route 4축이 stdout에 출력된다."""
        out = run_check(
            name_status="M src/foo.ts",
            numstat="1 0 src/foo.ts",
            diff_u0="+const k = 'AKIAIOSFODNN7EXAMPLE';\n",
        )
        # 시크릿 차단되어도 모든 route 키 출력
        for key in self.ROUTE_KEYS:
            assert key in out, f"route key {key} missing on secret block"
        # review_route는 deep (시크릿 게이트), 다른 키는 폴백 유지
        assert out["review_route"] == "deep"
        assert out["commit_route"] == "single"

    def test_release_promotion_on_starter_release_files(self):
        """is_starter + HARNESS.json staged → promotion=release, side_effects.release에 경로."""
        out = run_check(
            name_status="M .claude/HARNESS.json",
            numstat="1 1 .claude/HARNESS.json",
            diff_u0='+  "version": "0.44.1",\n-  "version": "0.44.0",\n',
        )
        # HARNESS_DEV 환경에서 본 repo HARNESS.json은 is_starter=true 시드
        # → release 신호 발화
        assert out["promotion"] == "release", out
        assert ".claude/HARNESS.json" in out["side_effects.release"]
        # repair는 본 wave 범위 외 — 항상 none
        assert out["side_effects.repair"] == "none"


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
    _clone_repo(repo)
    # 미커밋 최신 파일 덮어쓰기
    for name in ("pre_commit_check.py", "docs_ops.py"):
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


@pytest.mark.docs_ops
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


@pytest.mark.docs_ops
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


@pytest.mark.skip(reason="외형 metric 룰 (rename 단독·meta 단독·docs 5줄) 폐기 — v0.29.1 Phase 2-A. AC + CPS 의미 기반으로 전환됨. 신규 테스트는 TestACBasedStage (별 wave)")
@pytest.mark.stage
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
# T45: verify-relates 전수 검사 — pre-check 통합 회귀
# ─────────────────────────────────────────────────────────


@pytest.mark.docs_ops
class TestVerifyRelatesPrecheck:
    """T45: pre-check 3.5단계 C — relates-to 전수 검사."""

    def test_existing_ref_passes(self, integ_repo):
        """T45.1: staged 외 파일의 relates-to가 유효 → 통과"""
        repo = integ_repo
        # 대상 파일 커밋
        _write(repo / "docs/t45_target/hn_t45_dest.md",
               "---\ntitle: dest\ndomain: harness\nstatus: completed\ncreated: 2026-05-02\n---\n")
        _git(["add", "docs/t45_target/hn_t45_dest.md"], repo)
        _commit(repo, "prep T45.1 target")
        # 참조 파일 커밋 (관계 정상)
        _write(repo / "docs/t45_src/hn_t45_ref.md",
               "---\ntitle: ref\ndomain: harness\nrelates-to:\n"
               "  - path: ../t45_target/hn_t45_dest.md\n    rel: references\n"
               "status: completed\ncreated: 2026-05-02\n---\n")
        _git(["add", "docs/t45_src/hn_t45_ref.md"], repo)
        _commit(repo, "prep T45.1 ref")
        # 무관한 파일만 staged — 기존 relates-to는 유효해야 통과
        _write(repo / "docs/t45_other/hn_t45_other.md",
               "---\ntitle: other\ndomain: harness\nstatus: in-progress\ncreated: 2026-05-02\n---\n")
        _git(["add", "docs/t45_other/hn_t45_other.md"], repo)
        out = _run_precheck(repo)
        assert out.get("pre_check_passed") == "true"
        _reset(repo)

    def test_broken_ref_in_committed_file_blocks(self, integ_repo):
        """T45.2: 기커밋 파일의 relates-to가 깨져있으면 → 차단"""
        repo = integ_repo
        # 참조 파일 먼저 커밋 (대상 없는 broken ref)
        _write(repo / "docs/t45b_src/hn_t45b_broken.md",
               "---\ntitle: broken\ndomain: harness\nrelates-to:\n"
               "  - path: ../t45b_nowhere/hn_ghost.md\n    rel: references\n"
               "status: completed\ncreated: 2026-05-02\n---\n")
        _git(["add", "docs/t45b_src/hn_t45b_broken.md"], repo)
        _commit(repo, "prep T45.2 broken ref")
        # 무관한 파일 staged → pre-check이 전수 검사에서 기커밋 broken ref를 잡아야 함
        _write(repo / "docs/t45b_other/hn_t45b_unrelated.md",
               "---\ntitle: unrelated\ndomain: harness\nstatus: in-progress\ncreated: 2026-05-02\n---\n")
        _git(["add", "docs/t45b_other/hn_t45b_unrelated.md"], repo)
        out = _run_precheck(repo)
        assert out.get("pre_check_passed") == "false"
        _reset(repo)


# ─────────────────────────────────────────────────────────
# T40: docs_ops.py wip-sync abbr 기반 보조 매칭
# ─────────────────────────────────────────────────────────

DOCS_OPS_PY = REPO_ROOT / ".claude" / "scripts" / "docs_ops.py"


@pytest.fixture(scope="function")
def wipsync_repo(tmp_path_factory):
    """T40 전용 sandbox: git clone + docs_ops.py + naming.md 최신 복사. function-scope로 격리.

    starter repo의 docs/WIP/는 비움 — abbr 매칭 시 starter의 hn WIP 갯수에
    의존하면 "복수 → skip" 분기로 빠져 false negative. fixture가 자기 WIP만
    써야 의도 명확.
    """
    tmp = tmp_path_factory.mktemp("wipsync")
    repo = tmp / "repo"
    _clone_repo(repo)
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
    wip_dir = repo / "docs" / "WIP"
    if wip_dir.exists():
        for f in wip_dir.glob("*.md"):
            f.unlink()
        subprocess.run(["git", "-C", str(repo), "add", "-A"],
                       capture_output=True, check=True)
        status = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],
                                capture_output=True, check=True)
        if status.stdout.strip():
            subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "fixture: clear WIP"],
                           capture_output=True, check=True)
    yield repo


def _run_wip_sync(repo: Path, staged_files: list[str]) -> tuple[dict[str, str], str]:
    """docs_ops.py wip-sync 실행. (stdout key:value dict, stderr+stdout 원문) 반환.

    Windows subprocess가 stderr를 stdout에 흡수하는 케이스 대비 — 호출자가
    경고 메시지 검사하려면 양쪽 텍스트를 합쳐서 받아야 안전.
    """
    r = subprocess.run(
        [sys.executable, ".claude/scripts/docs_ops.py", "wip-sync"] + staged_files,
        cwd=repo, capture_output=True, text=True,
    )
    out: dict[str, str] = {}
    for line in r.stdout.splitlines():
        if re.match(r"^[a-z_]+: ", line):
            k, v = line.split(": ", 1)
            out[k] = v
    return out, r.stderr + "\n" + r.stdout


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


@pytest.mark.docs_ops
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

        out, combined = _run_wip_sync(repo, ["src/t40b/serviceB.ts"])
        assert out.get("wip_sync_matched") == "0", f"output: {combined}"
        assert "skip" in combined.lower() or "2개" in combined, f"output: {combined}"
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


# ─────────────────────────────────────────────────────────
# T40b: wip-sync 부분 매칭 false positive 방지 (2026-05-02 자기증명 사고)
# ─────────────────────────────────────────────────────────

@pytest.mark.docs_ops
class TestWipSyncMatchPrecision:
    """T40b: 매칭 정밀화 — 사전 준비·frontmatter false positive 차단."""

    def test_no_match_in_preparation_section(self, wipsync_repo):
        """staged 파일명이 `## 사전 준비` 자연어 줄에 있어도 ✅ 추가 안 됨."""
        repo = wipsync_repo
        wip = repo / "docs/WIP/decisions--hn_t40b_prep.md"
        content = (
            "---\ntitle: T40b prep\ndomain: harness\n"
            "status: pending\ncreated: 2026-05-02\n---\n\n"
            "# T40b\n\n## 사전 준비\n"
            "- 읽을 문서: `.claude/scripts/docs_ops.py` (wip-sync)\n\n"
            "**Acceptance Criteria**:\n"
            "- [ ] Goal: 다른 작업\n"
        )
        _write(wip, content)
        _git(["add", str(wip)], repo)
        _commit(repo, "T40b prep WIP")

        out, _ = _run_wip_sync(repo, [".claude/scripts/docs_ops.py"])
        after = wip.read_text(encoding="utf-8")
        # 본 WIP 자체에는 ✅ 추가되면 안 됨 (sandbox 다른 WIP는 무관)
        assert "✅" not in after, f"false positive ✅ 추가됨:\n{after}"

        _git(["reset", "HEAD", "."], repo)
        _git(["clean", "-fdq"], repo)

    def test_no_match_in_frontmatter_relates_to(self, wipsync_repo):
        """frontmatter `relates-to:` YAML 리스트에 staged 파일 경로 있어도 ✅ 안 됨."""
        repo = wipsync_repo
        wip = repo / "docs/WIP/decisions--hn_t40b_fm.md"
        content = (
            "---\ntitle: T40b fm\ndomain: harness\n"
            "relates-to:\n"
            "  - path: decisions/hn_t40b_other.md\n"
            "    rel: caused-by\n"
            "status: pending\ncreated: 2026-05-02\n---\n\n"
            "# T40b\n\n**Acceptance Criteria**:\n"
            "- [ ] Goal: 작업\n"
        )
        _write(wip, content)
        _git(["add", str(wip)], repo)
        _commit(repo, "T40b fm WIP")

        out, _ = _run_wip_sync(repo, ["decisions/hn_t40b_other.md"])
        after = wip.read_text(encoding="utf-8")
        # frontmatter `path:` 줄에 ✅ 추가되면 안 됨
        for line in after.splitlines():
            if "path:" in line and "decisions/hn_t40b_other" in line:
                assert "✅" not in line, f"frontmatter false positive: {line}"

        _git(["reset", "HEAD", "."], repo)
        _git(["clean", "-fdq"], repo)

    def test_marks_only_checkbox_lines(self, wipsync_repo):
        """체크박스 라인의 staged 파일 언급은 정상 매칭 (회귀 가드)."""
        repo = wipsync_repo
        wip = repo / "docs/WIP/decisions--hn_t40b_normal.md"
        content = (
            "---\ntitle: T40b normal\ndomain: harness\n"
            "status: pending\ncreated: 2026-05-02\n---\n\n"
            "# T40b\n\n**Acceptance Criteria**:\n"
            "- [ ] Goal: docs_ops.py 매칭 정밀화\n"
            "- [ ] 다른 항목\n"
        )
        _write(wip, content)
        _git(["add", str(wip)], repo)
        _commit(repo, "T40b normal WIP")

        out, _ = _run_wip_sync(repo, [".claude/scripts/docs_ops.py"])
        after = wip.read_text(encoding="utf-8")
        # Goal 줄에 ✅ 정확히 추가
        assert "Goal: docs_ops.py 매칭 정밀화 ✅" in after, f"정상 매칭 누락:\n{after}"
        # 다른 항목에는 추가 안 됨
        assert "다른 항목 ✅" not in after

        _git(["reset", "HEAD", "."], repo)
        _git(["clean", "-fdq"], repo)


# ─────────────────────────────────────────────────────────
# T40c: wip-sync 의미 게이트 — staged WIP problem 일치만 인정 (v0.30.7)
# ─────────────────────────────────────────────────────────

@pytest.mark.docs_ops
class TestWipSyncProblemGate:
    """v0.30.7 의미 게이트: 어휘 일치 ≠ 의미 일치 false positive 차단.

    배경: hn_session_test_results.md 우선순위 2 — `hn_rule_skill_ssot.md`
    AC 본문에 "commit/SKILL.md"가 등장. 본 commit이 commit/SKILL.md를
    수정하면 어휘 매칭 hit → 우연 ✅ 추가. problem 게이트로 차단.
    """

    def test_problem_mismatch_blocks_body_referenced(self, wipsync_repo):
        """staged WIP problem(P2)과 후보 WIP problem(P5) 불일치 → body_referenced 차단."""
        repo = wipsync_repo
        # 후보 WIP — P5, 본문에 staged 파일명 포함 ([x] 마킹된 줄)
        candidate = repo / "docs/WIP/decisions--hn_t40c_candidate.md"
        candidate.write_text(
            "---\ntitle: candidate\ndomain: harness\nproblem: P5\n"
            "status: in-progress\ncreated: 2026-05-02\n---\n\n"
            "# candidate\n\n**Acceptance Criteria**:\n"
            "- [x] Goal: foo.py 정밀화\n",
            encoding="utf-8",
        )
        # staged WIP — P2 (현 작업의 problem)
        staged_wip = repo / "docs/WIP/decisions--hn_t40c_current.md"
        staged_wip.write_text(
            "---\ntitle: current\ndomain: harness\nproblem: P2\n"
            "status: in-progress\ncreated: 2026-05-02\n---\n\n"
            "# current\n\n**Acceptance Criteria**:\n"
            "- [ ] Goal: 다른 작업\n",
            encoding="utf-8",
        )
        _git(["add", str(candidate), str(staged_wip)], repo)
        _commit(repo, "T40c prep")

        # foo.py + staged_wip 둘 다 staged
        out, combined = _run_wip_sync(
            repo, ["foo.py", "docs/WIP/decisions--hn_t40c_current.md"]
        )
        # candidate는 차단되어야 함 (problem 불일치)
        assert candidate.exists(), f"candidate가 자동 이동됨 — 게이트 미작동:\n{combined}"
        assert "의미 게이트 차단" in combined, f"게이트 메시지 누락:\n{combined}"

        _git(["reset", "HEAD", "."], repo)
        _git(["clean", "-fdq"], repo)

    def test_problem_match_passes_body_referenced(self, wipsync_repo):
        """staged WIP problem과 후보 WIP problem 일치 → body_referenced 인정."""
        repo = wipsync_repo
        candidate = repo / "docs/WIP/decisions--hn_t40c_match.md"
        candidate.write_text(
            "---\ntitle: candidate match\ndomain: harness\nproblem: P2\n"
            "status: in-progress\ncreated: 2026-05-02\n---\n\n"
            "# candidate\n\n**Acceptance Criteria**:\n"
            "- [x] Goal: foo.py 작업\n",
            encoding="utf-8",
        )
        staged_wip = repo / "docs/WIP/decisions--hn_t40c_current2.md"
        staged_wip.write_text(
            "---\ntitle: current\ndomain: harness\nproblem: P2\n"
            "status: in-progress\ncreated: 2026-05-02\n---\n\n"
            "# current\n\n**Acceptance Criteria**:\n"
            "- [ ] Goal: 작업\n",
            encoding="utf-8",
        )
        _git(["add", str(candidate), str(staged_wip)], repo)
        _commit(repo, "T40c match prep")

        out, combined = _run_wip_sync(
            repo, ["foo.py", "docs/WIP/decisions--hn_t40c_current2.md"]
        )
        # candidate가 자동 이동되어야 함 (problem 일치 + AC [x] 전부)
        assert not candidate.exists() or "의미 게이트" not in combined, (
            f"problem 일치인데 게이트 차단됨:\n{combined}"
        )

        _git(["reset", "HEAD", "."], repo)
        _git(["clean", "-fdq"], repo)

    def test_no_staged_wip_skips_gate(self, wipsync_repo):
        """staged에 WIP 없음 → 게이트 skip (코드만 staged인 케이스 — 회귀 가드)."""
        repo = wipsync_repo
        candidate = repo / "docs/WIP/decisions--hn_t40c_nogate.md"
        candidate.write_text(
            "---\ntitle: nogate\ndomain: harness\nproblem: P2\n"
            "status: in-progress\ncreated: 2026-05-02\n---\n\n"
            "# nogate\n\n**Acceptance Criteria**:\n"
            "- [x] Goal: foo.py 작업\n",
            encoding="utf-8",
        )
        _git(["add", str(candidate)], repo)
        _commit(repo, "T40c nogate prep")

        out, combined = _run_wip_sync(repo, ["foo.py"])
        # staged WIP 없으므로 게이트 skip → body_referenced로 매칭 통과
        assert "의미 게이트 차단" not in combined, (
            f"staged WIP 없는데 게이트 차단됨:\n{combined}"
        )

        _git(["reset", "HEAD", "."], repo)
        _git(["clean", "-fdq"], repo)


# ─────────────────────────────────────────────────────────
# T41: docs_ops.py move untracked WIP fallback (incident hn_secret_line_exempt_gap)
# ─────────────────────────────────────────────────────────

@pytest.mark.docs_ops
class TestMoveUntrackedWip:
    """untracked WIP 파일도 move가 성공해야 한다 (git rm --cached 회피)."""

    WIP_CONTENT = (
        "---\ntitle: T41 untracked move\ndomain: harness\n"
        "status: in-progress\ncreated: 2026-05-01\n---\n\n"
        "# T41 untracked move\n\n## 증상\n서술형. 체크리스트 없음.\n"
    )

    def test_untracked_move_succeeds(self, wipsync_repo):
        """T41.1: working tree에만 있는 WIP를 move → returncode 0, dest staged, status=completed."""
        repo = wipsync_repo
        wip = repo / "docs/WIP/incidents--hn_t41_untracked.md"
        _write(wip, self.WIP_CONTENT)
        # git add 하지 않음 — untracked 상태 유지

        r = subprocess.run(
            [sys.executable, ".claude/scripts/docs_ops.py", "move", str(wip.relative_to(repo))],
            cwd=repo, capture_output=True, text=True,
        )
        assert r.returncode == 0, f"stdout={r.stdout}\nstderr={r.stderr}"

        dest = repo / "docs/incidents/hn_t41_untracked.md"
        assert dest.exists(), "dest 파일이 생성되지 않음"
        assert not wip.exists(), "src WIP 파일이 남아있음"

        # dest가 git index에 staged됐는지 확인
        ls = subprocess.run(["git", "ls-files", "--cached", str(dest.relative_to(repo))],
                            cwd=repo, capture_output=True, text=True)
        assert ls.stdout.strip(), f"dest가 staged 안 됨: {ls.stdout}"

        # status: completed로 갱신됐는지
        text = dest.read_text(encoding="utf-8")
        assert "status: completed" in text, "status가 completed로 갱신 안 됨"

        _git(["reset", "HEAD", "."], repo)
        _git(["clean", "-fdq"], repo)


# ─────────────────────────────────────────────────────────
# T42: pre_commit_check.py main 함수화 — import 시 sys.exit 발생 안 함
# (incident hn_upstream_anomalies.md G Phase 2)
# ─────────────────────────────────────────────────────────

@pytest.mark.enoent
class TestModuleImportSafe:
    """module-level main 로직이 import 시 sys.exit하지 않아야 한다."""

    def test_import_does_not_exit(self):
        """T42.1: subprocess로 새 Python에서 import — staged 변경 유무 무관 통과."""
        # subprocess로 새 인터프리터에서 import 시도. main 로직이 module-level이면
        # sys.exit(2)로 종료되어 returncode 2. main 함수화 후엔 import만 통과 → returncode 0.
        r = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, r'" + str(PY_SCRIPT.parent) + "'); "
             "from pre_commit_check import ENOENT_PATTERNS; "
             "assert ENOENT_PATTERNS is not None; print('import_ok')"],
            cwd=REPO_ROOT, capture_output=True, text=True,
            env={**os.environ, "PYTHONUTF8": "1"},
        )
        assert r.returncode == 0, f"import 시 sys.exit 발생 (returncode={r.returncode}): stderr={r.stderr}"
        assert "import_ok" in r.stdout, f"import 후 print 도달 못 함: stdout={r.stdout}"


# ─────────────────────────────────────────────────────────
# T44: cluster-update 게이팅 (C4 결정적 출력)
# ─────────────────────────────────────────────────────────


@pytest.mark.docs_ops
class TestClusterUpdateGating:
    """T44: 본체·문서 변경 없으면 mtime 갱신 0건. 영향 도메인만 갱신."""

    def _run_cluster_update(self, repo: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, ".claude/scripts/docs_ops.py", "cluster-update"],
            cwd=repo, capture_output=True, text=True,
            env={**os.environ, "PYTHONUTF8": "1"},
        )

    def test_idempotent_skip(self, integ_repo):
        """T44.1: 두 번 호출해도 mtime 무변경 (skip)."""
        repo = integ_repo
        # 첫 호출 — 모든 cluster 정렬
        self._run_cluster_update(repo)
        clusters = sorted((repo / "docs/clusters").glob("*.md"))
        assert clusters, "clusters/ 비어 있음"
        before = {c: c.stat().st_mtime_ns for c in clusters}
        # 즉시 재호출
        r = self._run_cluster_update(repo)
        assert r.returncode == 0
        after = {c: c.stat().st_mtime_ns for c in clusters}
        assert before == after, f"멱등 깨짐: {[c.name for c in clusters if before[c] != after[c]]}"
        assert "skip" in r.stdout.lower()

    def test_only_affected_domain_updates(self, integ_repo):
        """T44.2: 단일 cluster를 의도적으로 stale 화 → 그것만 갱신."""
        repo = integ_repo
        self._run_cluster_update(repo)
        clusters = sorted((repo / "docs/clusters").glob("*.md"))
        assert len(clusters) >= 2, "다중 도메인 cluster 필요"
        target = clusters[0]
        others = clusters[1:]
        # target stale 화 (내용 변조)
        text = target.read_text(encoding="utf-8")
        target.write_text(text + "\n# stale_marker\n", encoding="utf-8")
        before_others = {c: c.stat().st_mtime_ns for c in others}
        before_target = target.stat().st_mtime_ns
        # 잠깐 대기 없이 재호출 — mtime 단위가 ns이므로 변경되면 즉시 반영
        r = self._run_cluster_update(repo)
        assert r.returncode == 0
        # target만 갱신됐어야 함
        after_others = {c: c.stat().st_mtime_ns for c in others}
        assert before_others == after_others, "비영향 cluster mtime 갱신됨"
        # target은 다시 결정적 본문으로 복원되어 mtime 갱신
        assert target.stat().st_mtime_ns != before_target or "stale_marker" not in target.read_text(encoding="utf-8")

    def test_wip_appears_in_cluster(self, integ_repo):
        """T44.3: WIP 파일이 cluster `## 진행 중 (WIP)` 섹션에 자동 등록."""
        repo = integ_repo
        # 임시 WIP 파일 신설 (harness 도메인)
        wip = repo / "docs/WIP/decisions--hn_t44_visibility.md"
        wip.parent.mkdir(parents=True, exist_ok=True)
        wip.write_text(
            "---\ntitle: T44 가시성 테스트\ndomain: harness\n"
            "problem: P5\nsolution-ref:\n  - S5 — \"테스트\"\n"
            "status: in-progress\ncreated: 2026-05-02\n---\n\n# 본문\n",
            encoding="utf-8",
        )
        try:
            r = self._run_cluster_update(repo)
            assert r.returncode == 0
            harness_cluster = repo / "docs/clusters/harness.md"
            text = harness_cluster.read_text(encoding="utf-8")
            assert "## 진행 중 (WIP)" in text, "WIP 섹션 헤더 누락"
            assert "decisions--hn_t44_visibility.md" in text, "신규 WIP 미등록"
            assert "T44 가시성 테스트" in text, "WIP title 누락"
        finally:
            if wip.exists():
                wip.unlink()
            self._run_cluster_update(repo)  # 정리
