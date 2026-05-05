#!/usr/bin/env python3
"""
pre-commit 검사.

출력 채널:
  stdout: commit 스킬이 파싱하는 key:value 요약 (스키마 변경 금지)
  stderr: 사용자 노출용 에러/경고

종료 코드:
  0: 통과
  2: 차단 (ERRORS > 0)
"""

import io
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# docs_ops.py 유틸 재사용 (naming.md 파싱 중복 방지)
_DOCS_OPS = Path(__file__).parent / "docs_ops.py"
if _DOCS_OPS.exists():
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("docs_ops", _DOCS_OPS)
    _docs_ops = _ilu.module_from_spec(_spec)   # type: ignore[arg-type]
    _spec.loader.exec_module(_docs_ops)         # type: ignore[union-attr]
    _extract_abbrs     = _docs_ops.extract_abbrs
    _detect_abbr       = _docs_ops.detect_abbr
    _extract_path_map  = _docs_ops.extract_path_domain_map
    _path_to_domain    = _docs_ops.path_to_domain
else:
    def _extract_abbrs():       return []
    def _detect_abbr(p, a):     return None
    def _extract_path_map():    return []
    def _path_to_domain(f, m):  return None

# ─────────────────────────────────────────────────────────
# 헬퍼
# ─────────────────────────────────────────────────────────

def run(cmd: list[str], *, check=False) -> str:
    """subprocess 실행 → stdout 문자열 반환. 실패 시 빈 문자열.

    Windows + 한글 staged diff에서 system locale(cp949)로 디코딩 실패해
    stdout=None이 되던 결함 방지 (incident hn_upstream_anomalies.md G 항목).
    """
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        return r.stdout or ""
    except Exception:
        return ""


def err(msg: str) -> None:
    print(msg, file=sys.stderr)


def lines(s: str) -> list[str]:
    return [l for l in s.splitlines() if l.strip()]


def parse_name_status(raw: str) -> list[tuple[str, str]]:
    """name-status 행 파싱 → (status, path) 리스트.
    git 실제 출력은 탭 구분, 테스트 픽스처는 공백 구분일 수 있어 둘 다 처리.
    rename(R100) 은 (status, old_path, new_path) → (status, new_path) 반환.
    """
    result = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        if "\t" in line:
            parts = line.split("\t")
        else:
            parts = line.split(None, 2)
        if len(parts) < 2:
            continue
        status = parts[0]
        # rename: parts[0]=R100, parts[1]=old, parts[2]=new
        path = parts[-1]
        result.append((status, path))
    return result


def resolve_path(base_dir: str, link: str) -> str:
    """상대 경로를 base_dir 기준으로 해석, 정규화."""
    if link.startswith("/") or link.startswith("http"):
        return ""
    p = Path(base_dir) / link
    try:
        # Path.resolve()는 실제 fs 접근하므로 수동 정규화
        parts = []
        for part in str(p).replace("\\", "/").split("/"):
            if part == "..":
                if parts:
                    parts.pop()
            elif part not in (".", ""):
                parts.append(part)
        return "/".join(parts)
    except Exception:
        return ""


# ─────────────────────────────────────────────────────────
# CPS·AC 메타데이터 파싱 (Phase 2-A 2단계 — v0.29.1)
# ─────────────────────────────────────────────────────────

CPS_DOC = "docs/guides/project_kickoff.md"
# CPS 면제 — frontmatter problem·solution-ref 강제 안 함
CPS_EXEMPT_PATHS = re.compile(r"^docs/guides/project_kickoff\.md$")


def normalize_quote(s: str) -> str:
    """CPS 인용 비교용 normalize. 공백 통일·줄바꿈 제거·backtick 제거."""
    s = s.replace("\n", " ").replace("`", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_frontmatter(text: str) -> tuple[dict, int]:
    """frontmatter 파싱 → (dict, body_start_line). frontmatter 없으면 ({}, 0)."""
    lines_ = text.splitlines()
    if not lines_ or lines_[0].strip() != "---":
        return {}, 0
    fm: dict = {}
    end = -1
    for i, line in enumerate(lines_[1:], start=1):
        if line.strip() == "---":
            end = i
            break
    if end < 0:
        return {}, 0

    cur_key = None
    list_buf: list = []
    for line in lines_[1:end]:
        m = re.match(r"^([a-zA-Z_-]+):\s*(.*)$", line)
        if m:
            if cur_key and list_buf:
                fm[cur_key] = list_buf
                list_buf = []
            cur_key = m.group(1)
            val = m.group(2).strip()
            if val:
                fm[cur_key] = val
                cur_key = None
            else:
                list_buf = []
        elif cur_key and re.match(r"^\s+-\s+(.+)$", line):
            item = re.match(r"^\s+-\s+(.+)$", line).group(1).strip()
            list_buf.append(item)
    if cur_key and list_buf:
        fm[cur_key] = list_buf
    return fm, end + 1


def parse_solution_ref(entry: str) -> tuple[str, str, bool]:
    """solution-ref 항목 파싱 → (solution_id, quote, is_partial).
    형식: 'S2 — "원문"' 또는 'S2 — "요약 (부분)"'.
    """
    # quote가 따옴표로 감싸짐. backtick·single quote도 허용
    m = re.match(r'^(S\d+)\s*[—\-]\s*[`"\']([^`"\'\n]+)[`"\']\s*$', entry.strip())
    if not m:
        return "", "", False
    sid, quote = m.group(1), m.group(2)
    is_partial = False
    if quote.endswith(" (부분)"):
        quote = quote[: -len(" (부분)")]
        is_partial = True
    return sid, quote, is_partial


_CPS_TEXT_CACHE: str | None = None


def get_cps_text() -> str:
    """CPS 본문 Read (캐싱). normalize 적용."""
    global _CPS_TEXT_CACHE
    if _CPS_TEXT_CACHE is None:
        try:
            _CPS_TEXT_CACHE = normalize_quote(Path(CPS_DOC).read_text(encoding="utf-8"))
        except Exception:
            _CPS_TEXT_CACHE = ""
    return _CPS_TEXT_CACHE


def parse_ac_block(body: str) -> dict:
    """AC 블록에서 Goal·검증 묶음 추출.
    형식:
        - [ ] Goal: <1줄>
          검증:
            review: skip|self|review|review-deep
            tests: <명령 또는 "없음">
            실측: <명령 또는 "없음">
    반환: {goal: str, ac_review: str, ac_tests: str, ac_actual: str}
    누락 항목은 빈 문자열.
    """
    result = {"goal": "", "ac_review": "", "ac_tests": "", "ac_actual": "", "ac_section_found": False}
    in_ac = False
    in_verify = False
    for line in body.splitlines():
        if "Acceptance Criteria" in line and "**" in line:
            in_ac = True
            result["ac_section_found"] = True
            continue
        if not in_ac:
            continue
        if line.startswith("## ") or line.startswith("### "):
            break
        # Goal 항목
        m = re.match(r"^\s*-\s*\[.\]\s*Goal:\s*(.+)$", line)
        if m and not result["goal"]:
            result["goal"] = m.group(1).strip()
            continue
        # 검증 블록 진입
        if re.match(r"^\s+검증:\s*$", line):
            in_verify = True
            continue
        if in_verify:
            mr = re.match(r"^\s+review:\s*(.+)$", line)
            mt = re.match(r"^\s+tests:\s*(.+)$", line)
            ma = re.match(r"^\s+실측:\s*(.+)$", line)
            if mr:
                result["ac_review"] = mr.group(1).strip()
            elif mt:
                result["ac_tests"] = mt.group(1).strip()
            elif ma:
                result["ac_actual"] = ma.group(1).strip()
            elif re.match(r"^\s*-\s*\[.\]", line):
                # 다음 AC 항목 → 검증 블록 종료
                in_verify = False
    return result


def verify_solution_ref(sol_refs: list, cps_text: str) -> list[str]:
    """solution-ref 인용을 CPS 본문과 비교. 박제 의심 경고 list 반환.
    형식 위반·CPS 미매칭 모두 경고.
    """
    warnings = []
    for entry in sol_refs:
        sid, quote, is_partial = parse_solution_ref(entry)
        if not sid:
            warnings.append(f"형식 위반: {entry}")
            continue
        if len(quote) > 50 and not is_partial:
            warnings.append(
                f"{sid} 인용 50자 초과인데 (부분) 마커 없음 — 원문 그대로 또는 요약+부분 마커"
            )
            continue
        nq = normalize_quote(quote)
        if nq and nq not in cps_text:
            warnings.append(f"{sid} 인용 박제 의심 (CPS 본문 미매칭): \"{quote[:60]}\"")
    return warnings


# ─────────────────────────────────────────────────────────
# 입력 수집
# ─────────────────────────────────────────────────────────

TEST_MODE = os.environ.get("TEST_MODE", "0") == "1"
HARNESS_EXPAND = os.environ.get("HARNESS_EXPAND", "0") == "1"
HARNESS_SPLIT_SUB = os.environ.get("HARNESS_SPLIT_SUB", "0") == "1"
HARNESS_SPLIT_OPT_IN = os.environ.get("HARNESS_SPLIT_OPT_IN", "0") == "1"
VERBOSE = os.environ.get("VERBOSE", "")

# ENOENT_PATTERNS는 test가 import하므로 module-level 유지
ENOENT_PATTERNS = re.compile(
    r"is not recognized as an internal or external command"
    r"|: command not found$"
    r"|command not found: [a-zA-Z0-9_./+-]+$"
    r"|^exec: [^:]+: not found$"
    r"|^sh: [0-9]+: [^:]+: not found$"
    r"|ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL",
    re.MULTILINE,
)

def main() -> int:
    """pre-commit 검사 메인. ERRORS > 0이면 2 반환.

    main 함수화 이유: import 시 module-level main 로직이 staged 변경에서
    sys.exit(2)를 호출해 import 자체가 막히던 결함 해소 (incident G Phase 2).
    """

    # git 입력 (TEST_MODE 시 환경변수 주입)
    if TEST_MODE and "_TEST_NAME_STATUS" in os.environ:
        name_status_raw = os.environ.get("_TEST_NAME_STATUS", "")
        numstat_raw     = os.environ.get("_TEST_NUMSTAT", "")
        diff_u0_raw     = os.environ.get("_TEST_DIFF_U0", "")
    else:
        name_status_raw = run(["git", "diff", "--cached", "--name-status"])
        numstat_raw     = run(["git", "diff", "--cached", "--numstat"])
        diff_u0_raw     = run(["git", "diff", "--cached", "-U0"])

    # 파생
    ns_parsed = parse_name_status(name_status_raw)
    staged_files: list[str] = [path for _, path in ns_parsed]

    # diff stats
    added_lines = deleted_lines = 0
    numstat_file_count = 0
    for line in numstat_raw.splitlines():
        parts = line.split()
        if len(parts) >= 3:
            try:
                added_lines   += int(parts[0])
                deleted_lines += int(parts[1])
                numstat_file_count += 1
            except ValueError:
                pass  # 바이너리 파일('-')
    # TEST_MODE에서 _TEST_NUMSTAT 미주입 시 name_status 기반으로 폴백
    total_files = numstat_file_count if numstat_file_count > 0 else len(staged_files)
    total_lines = added_lines + deleted_lines
    diff_stats  = f"files={total_files},+{added_lines},-{deleted_lines}"

    ERRORS = 0
    ALREADY_VERIFIED = "lint todo_fixme test_location wip_cleanup"

    # ─────────────────────────────────────────────────────────
    # 1. 린터
    # ─────────────────────────────────────────────────────────

    lint_cmd: list[str] = []
    pkg_mgr = ""

    if Path("CLAUDE.md").exists():
        for line in Path("CLAUDE.md").read_text(encoding="utf-8", errors="ignore").splitlines():
            m = re.match(r"패키지 매니저:\s*(\S+)", line)
            if m:
                pkg_mgr = m.group(1)
                break

    def _has_lint_script() -> bool:
        if not Path("package.json").exists():
            return False
        return '"lint"' in Path("package.json").read_text(encoding="utf-8", errors="ignore")

    def _resolve_cmd(name: str) -> str:
        """Windows에서 .cmd 확장자 없이 npm/pnpm/yarn/bun을 못 찾는 문제 해결."""
        resolved = shutil.which(name)
        return resolved if resolved else name

    if pkg_mgr == "npm"  and _has_lint_script(): lint_cmd = [_resolve_cmd("npm"), "run", "lint", "--silent"]
    elif pkg_mgr == "pnpm" and _has_lint_script(): lint_cmd = [_resolve_cmd("pnpm"), "lint"]
    elif pkg_mgr == "yarn" and _has_lint_script(): lint_cmd = [_resolve_cmd("yarn"), "lint"]
    elif pkg_mgr == "bun"  and _has_lint_script(): lint_cmd = [_resolve_cmd("bun"), "run", "lint"]
    elif pkg_mgr in ("pip", "poetry", "uv"):
        if subprocess.run(["ruff", "--version"], capture_output=True).returncode == 0:
            lint_cmd = ["ruff", "check", ".", "--quiet"]
    elif _has_lint_script():
        if Path("pnpm-lock.yaml").exists():   lint_cmd = [_resolve_cmd("pnpm"), "lint"]
        elif Path("yarn.lock").exists():      lint_cmd = [_resolve_cmd("yarn"), "lint"]
        elif Path("bun.lockb").exists():      lint_cmd = [_resolve_cmd("bun"), "run", "lint"]
        else:                                 lint_cmd = [_resolve_cmd("npm"), "run", "lint", "--silent"]
    elif Path("pyproject.toml").exists():
        if subprocess.run(["ruff", "--version"], capture_output=True).returncode == 0:
            lint_cmd = ["ruff", "check", ".", "--quiet"]

    if lint_cmd:
        r = subprocess.run(lint_cmd, capture_output=True, text=True)
        if r.returncode != 0:
            output = r.stdout + r.stderr
            if ENOENT_PATTERNS.search(output):
                err(f"⚠ 린터 도구 미설치 또는 PATH 누락. 린트 스킵 (커밋 계속).")
                err(f"   (실행: {' '.join(lint_cmd)} — node_modules 확인 또는 `npm install` 검토)")
                for l in output.splitlines()[-5:]:
                    err(f"   {l}")
            else:
                err(f"❌ 린터 에러. 에러 0에서만 커밋 가능. (실행: {' '.join(lint_cmd)})")
                for l in output.splitlines()[-20:]:
                    err(f"   {l}")
                ERRORS += 1

    # ─────────────────────────────────────────────────────────
    # 2. TODO/FIXME
    # ─────────────────────────────────────────────────────────

    SKIP_TODO = re.compile(r"^docs/|\.(?:md|mdx)$|README|CHANGELOG|^\.claude/scripts/")
    todo_candidates = [f for f in staged_files if not SKIP_TODO.search(f)]
    if todo_candidates:
        todo_files = []
        for f in todo_candidates:
            if Path(f).exists():
                try:
                    content = Path(f).read_text(encoding="utf-8", errors="ignore")
                    if re.search(r"TODO|FIXME|HACK", content):
                        todo_files.append(f)
                except Exception:
                    pass
        if todo_files:
            err("❌ TODO/FIXME/HACK 발견. 코드가 아니라 docs/WIP/에 기록하라.")
            for f in todo_files:
                err(f"   {f}")
            ERRORS += 1

    # ─────────────────────────────────────────────────────────
    # 3. 테스트 파일 위치
    # ─────────────────────────────────────────────────────────

    TEST_FILE_PAT = re.compile(r"\.(test|spec)\.|_test\.")
    TEST_DIR_PAT  = re.compile(r"^(?:tests/|__tests__/)")
    test_outside = [f for f in staged_files
                    if TEST_FILE_PAT.search(f) and not TEST_DIR_PAT.match(f)]
    if test_outside:
        err("❌ 테스트 파일이 tests/ 밖에 있음:")
        for f in test_outside:
            err(f"   {f}")
        ERRORS += 1

    # ─────────────────────────────────────────────────────────
    # 3.5. dead link 증분 검사
    # ─────────────────────────────────────────────────────────

    dead_links: list[str] = []

    # A. 삭제·rename된 md 파일을 참조하는 기존 링크
    deleted_or_moved: list[str] = []
    for line in name_status_raw.splitlines():
        if not line.strip():
            continue
        if "\t" in line:
            parts = line.split("\t")
        else:
            parts = line.split(None, 2)
        if not parts:
            continue
        status = parts[0]
        if status == "D" and len(parts) >= 2 and parts[-1].endswith(".md"):
            deleted_or_moved.append(parts[-1])
        elif status.startswith("R") and len(parts) >= 3 and parts[1].endswith(".md"):
            deleted_or_moved.append(parts[1])  # old path (탭 구분 시 parts[1]이 old)

    if deleted_or_moved:
        for removed in deleted_or_moved:
            removed_base = Path(removed).name
            # grep for links containing basename in docs/ and .claude/
            for search_root in ("docs", ".claude"):
                if not Path(search_root).exists():
                    continue
                result = run(["grep", "-rn", "--include=*.md",
                              "-E", rf"\]\([^)]*{re.escape(removed_base)}[^)]*\)",
                              search_root])
                if not result:
                    continue
                for hit in result.splitlines():
                    parts = hit.split(":", 2)
                    if len(parts) < 3:
                        continue
                    src, lineno, matched_line = parts[0], parts[1], parts[2]
                    if src in staged_files:
                        continue
                    # 링크 경로 추출 후 해석
                    for m in re.finditer(r"\]\(([^)]+)\)", matched_line):
                        link = m.group(1).split("#")[0].split(" ")[0]
                        if link.startswith(("http", "mailto:")):
                            continue
                        resolved = resolve_path(str(Path(src).parent), link)
                        if resolved == removed.replace("\\", "/"):
                            dead_links.append(f"   {src}:{lineno}: {matched_line.strip()}")
                            break

    # B. 추가된 md 라인의 링크 대상 존재 확인
    modified_md = [f for f in staged_files if f.endswith(".md")]
    if modified_md:
        current_path = None
        is_md = False
        for line in diff_u0_raw.splitlines():
            if line.startswith("diff --git "):
                p = line.split()[-1]
                current_path = p[2:] if p.startswith("b/") else p  # b/path → path
                is_md = current_path.endswith(".md")
                continue
            if line.startswith(("+++", "---")):
                continue
            if not (is_md and line.startswith("+")):
                continue
            # 백틱 제거 후 링크 추출
            clean = re.sub(r"`[^`]*`", "", line)
            for m in re.finditer(r"\]\(([^)]+\.md)(?:[)#][^)]*)?\)", clean):
                link = m.group(1)
                if link.startswith(("http", "mailto:")):
                    continue
                if link.startswith("docs/"):
                    resolved = link
                elif link.startswith("/"):
                    continue
                else:
                    resolved = resolve_path(str(Path(current_path).parent), link)
                resolved_path = resolved.split("#")[0]
                if resolved_path and not Path(resolved_path).exists():
                    dead_links.append(
                        f"   {current_path} → {link} (resolved: {resolved_path}, 파일 없음)"
                    )

    if dead_links:
        err("❌ dead link 감지 (이번 커밋이 유발):")
        for dl in dead_links:
            err(dl)
        err("   대응: 링크를 수정하거나, 이동된 파일의 새 경로로 갱신")
        ERRORS += 1

    # C. frontmatter relates-to 전수 검사 (docs/ 전체)
    # cmd_verify_relates stdout을 suppress해 pre-check key:value 출력 오염 방지
    _vr_buf = io.StringIO()
    _vr_old_stdout = sys.stdout
    sys.stdout = _vr_buf
    try:
        _vr_rc = _docs_ops.cmd_verify_relates()
    finally:
        sys.stdout = _vr_old_stdout
    if _vr_rc:
        err("❌ frontmatter relates-to 미연결 건 감지 (전수 검사):")
        for line in _vr_buf.getvalue().splitlines():
            if line.strip():
                err(f"   {line}")
        err("   대응: docs_ops.py verify-relates 로 상세 확인 후 경로 수정 또는 항목 제거")
        ERRORS += 1

    # ─────────────────────────────────────────────────────────
    # 3.5. completed 봉인 보호 — status: completed 문서 본문 무단 변경 차단
    # ─────────────────────────────────────────────────────────
    # 자기증명 (2026-05-02 v0.31.x): wave WIP가 completed로 이동된 후 같은
    # 세션에서 본문 무단 확장 → "최악 패턴" 사고. completed = 결정 봉인.
    # 변경하려면 docs_ops.py reopen으로 in-progress 전환이 의무.
    SEALED_FOLDERS = ("docs/decisions/", "docs/guides/", "docs/incidents/", "docs/harness/")
    # 운영 누적 파일 — 다운스트림 harness-upgrade 흐름이 정기적으로 덮어쓰는
    # starter 자기 운영 명세. completed 봉인 대상 아님.
    # (incident: 2026-05-02 다운스트림 v0.33.0 fetch 시 MIGRATIONS.md 차단 보고)
    SEALED_PATH_EXEMPT = (
        "docs/harness/MIGRATIONS.md",
        "docs/harness/MIGRATIONS-archive.md",
        "docs/harness/migration-log.md",
    )
    sealed_violations: list[str] = []
    for status_char, path in ns_parsed:
        if status_char not in ("M",):  # rename(R)·delete(D)·add(A) 면제 — 이동/archive/신설은 OK
            continue
        if not path.endswith(".md"):
            continue
        if not any(path.startswith(folder) for folder in SEALED_FOLDERS):
            continue
        if path in SEALED_PATH_EXEMPT:
            continue
        try:
            content = Path(path).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # frontmatter status 추출
        if not re.search(r"^status:\s*completed\s*$", content, re.MULTILINE):
            continue
        # 면제 판정 — 변경 이력 섹션 신규 항목 추가, frontmatter 수정은 허용
        # 1. `## 변경 이력` 헤더 이후 라인 추가
        # 2. frontmatter 블록 내 변경 (--- ~ --- 사이) — reopen 절차 후 solution-ref 등 정정 허용
        # 3. updated/status/빈 줄/변경 이력 헤더 자체
        has_history_section = bool(re.search(r"^##\s*변경\s*이력\s*$", content, re.MULTILINE))
        diff_for_file = run(["git", "diff", "--cached", "-U0", "--", path])

        # diff hunk 시작 라인 번호 추출 (post-image)
        history_section_line = None
        if has_history_section:
            for i, line in enumerate(content.splitlines(), start=1):
                if re.match(r"^##\s*변경\s*이력\s*$", line):
                    history_section_line = i
                    break

        # frontmatter 끝 라인 번호 (1-based) — 두 번째 "---" 위치
        frontmatter_end_line = 0
        lines_content = content.splitlines()
        if lines_content and lines_content[0].strip() == "---":
            for i, line in enumerate(lines_content[1:], start=2):
                if line.strip() == "---":
                    frontmatter_end_line = i
                    break

        body_changed = False
        current_post_line = 0
        in_post_block = False
        hunk_has_deletion = False
        for diff_line in diff_for_file.splitlines():
            # hunk header: @@ -A,B +C,D @@
            m = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", diff_line)
            if m:
                current_post_line = int(m.group(1))
                in_post_block = True
                hunk_has_deletion = False
                continue
            if not in_post_block:
                continue
            if diff_line.startswith("+++") or diff_line.startswith("---"):
                in_post_block = False
                continue
            if diff_line.startswith("+"):
                # 변경 이력 섹션 이후 라인이면 면제
                if history_section_line and current_post_line > history_section_line:
                    current_post_line += 1
                    continue
                # frontmatter 블록 내 변경 면제 — reopen 절차 후 메타데이터(solution-ref 등) 정정 허용
                if frontmatter_end_line and current_post_line <= frontmatter_end_line:
                    current_post_line += 1
                    continue
                stripped = diff_line[1:].strip()
                # updated·status 필드·빈 줄·변경 이력 헤더 자체 면제
                if re.match(r"^updated:\s*\d{4}-\d{2}-\d{2}\s*$", stripped):
                    current_post_line += 1
                    continue
                if re.match(r"^status:\s*\w+\s*$", stripped):
                    current_post_line += 1
                    continue
                if not stripped:
                    current_post_line += 1
                    continue
                if re.match(r"^##\s*변경\s*이력\s*$", stripped):
                    current_post_line += 1
                    continue
                # frontmatter relates-to.path 경로 수정 면제 — dead-link 복구에 필수
                # (WIP 이동 후 역참조 미갱신 케이스에서 completed 문서가 막히는 루프 방지)
                if re.match(r"^-\s+path:\s+\S+", stripped):
                    current_post_line += 1
                    continue
                # 본문 마크다운 링크 경로 교체 면제 — archived 이동 후 dead-link 복구
                # 같은 hunk에 삭제(-) 라인이 있으면 교체. 순수 추가(삭제 없음)는 차단.
                if hunk_has_deletion and re.search(r"\[.*?\]\(.*?\)", stripped):
                    current_post_line += 1
                    continue
                body_changed = True
                break
            elif diff_line.startswith("-"):
                # 삭제도 본문 변경 (변경 이력 섹션 위 본문 삭제는 차단)
                # post-image line은 증가 안 함
                hunk_has_deletion = True
                continue
            else:
                # context line (-U0이라 거의 없음)
                current_post_line += 1
        if body_changed:
            sealed_violations.append(path)

    if sealed_violations:
        err("❌ completed 문서 본문 무단 변경 감지:")
        for p in sealed_violations:
            err(f"   {p}")
        err("   completed = 결정 봉인. 변경하려면 다음 절차:")
        err("     1. python3 .claude/scripts/docs_ops.py reopen <파일>  (status → in-progress, WIP로 이동)")
        err("     2. 변경 작업")
        err("     3. /commit 으로 다시 completed 처리")
        err("   변경 이력 섹션 추가는 면제 — `## 변경 이력` 헤더 아래 누적은 허용")
        ERRORS += 1

    # ─────────────────────────────────────────────────────────
    # 4. WIP completed/abandoned 잔재
    # ─────────────────────────────────────────────────────────

    if Path("docs/WIP").exists():
        stale_pat = re.compile(
            r"^status:.*(?:completed|abandoned)|^> status:.*(?:completed|abandoned)",
            re.MULTILINE,
        )
        stale_files = []
        for f in Path("docs/WIP").glob("*.md"):
            try:
                if stale_pat.search(f.read_text(encoding="utf-8", errors="ignore")):
                    stale_files.append(f.name)
            except Exception:
                pass
        if stale_files:
            err("⚠️ docs/WIP/에 완료/중단 문서가 남아있음. 이동 필요:")
            for f in stale_files:
                err(f"   {f}")

    # ─────────────────────────────────────────────────────────
    # 5. 시크릿 스캔
    # ─────────────────────────────────────────────────────────

    S1_FILE_PAT = re.compile(
        r"auth|token|secret|key|credential|password|\.env", re.I
    )
    S1_EXEMPT   = re.compile(
        r"\.(test|spec)\.|/tests?/|/__tests__/|^docs/|\.md$|/example|-helper\.|-utils?\."
    )
    S1_LINE_PAT = re.compile(
        r"^\+.*(sb_secret_|service_role(?![A-Z_])|sk_live_|sk_test_|ghp_|AKIA[0-9A-Z]{16}|password\s*=)",
        re.I,
    )
    # 하네스 자체가 시크릿 패턴을 SSOT로 문서화하는 위치는 line 스캔 면제
    # (scripts: 정의/테스트 픽스처, agents/rules/skills/memory: 패턴 인용 문서)
    S1_LINE_EXEMPT = re.compile(
        r"^\.claude/(scripts|agents|rules|skills|memory)/"
        r"|^docs/(WIP|incidents|decisions|guides|harness)/"
        r"|^scripts/install-secret-scan-hook\.sh$"
        r"|^[^/]+\.md$"
        r"|^supabase/migrations/.*\.sql$"
    )

    s1_file_hit = any(
        S1_FILE_PAT.search(f) and not S1_EXEMPT.search(f)
        for f in staged_files
    )

    # 파일별로 현재 경로를 추적하며 line 스캔 (면제 파일 제외)
    s1_line_hit = False
    _cur_file = ""
    for _line in diff_u0_raw.splitlines():
        if _line.startswith("diff --git "):
            _p = _line.split()[-1]
            _cur_file = _p[2:] if _p.startswith("b/") else _p
            continue
        if S1_LINE_EXEMPT.match(_cur_file):
            continue
        if S1_LINE_PAT.match(_line):
            s1_line_hit = True
            break

    s1_level = ""
    if s1_line_hit:
        s1_level = "line-confirmed"
        err("❌ 시크릿 패턴 감지 (line-confirmed). 커밋 차단.")
        ERRORS += 1
    elif s1_file_hit:
        s1_level = "file-only"
        err("⚠️ 시크릿 관련 파일명 감지 (file-only). 내용 확인 권장.")

    # ─────────────────────────────────────────────────────────
    # 5.5. 버전 범프 누락 경고 (is_starter 전용, 차단 아님)
    # ─────────────────────────────────────────────────────────

    try:
        import json as _json
        _harness = _json.loads(Path(".claude/HARNESS.json").read_text(encoding="utf-8"))
        if _harness.get("is_starter"):
            _bump_out = run(["python3", ".claude/scripts/harness_version_bump.py"])
            _bump_type = next(
                (l.split(":", 1)[1].strip() for l in _bump_out.splitlines()
                 if l.startswith("version_bump:")), "none"
            )
            if _bump_type in ("patch", "minor"):
                _next_ver = next(
                    (l.split(":", 1)[1].strip() for l in _bump_out.splitlines()
                     if l.startswith("next_version:")), "?")
                err(f"⚠️  버전 범프 누락: {_bump_type} 필요 (→ {_next_ver})")
                err("   commit Step 4에서 HARNESS.json·MIGRATIONS.md·README.md 일괄 갱신.")
    except Exception:
        pass

    # ─────────────────────────────────────────────────────────
    # 6. AC + CPS 메타데이터 추출 (Phase 2-A — v0.29.1)
    # ─────────────────────────────────────────────────────────
    #
    # staged WIP·decisions·incidents·guides의 frontmatter problem·solution-ref +
    # AC Goal·검증 묶음 추출. 누락 시 차단. 외형 metric 폐기.

    wip_problem = ""
    wip_solution_ref = ""  # ";" 구분 list-style
    ac_review = ""
    ac_tests = ""
    ac_actual = ""
    cps_text = get_cps_text()
    if not cps_text:
        err("⚠ CPS 본문 없음 — solution-ref 박제 감지 불가 (harness-init 미완료 또는 project_kickoff.md 비어있음)")

    DOCS_REQUIRED_PAT = re.compile(r"^docs/(WIP|decisions|incidents|guides|harness)/.+\.md$")
    # CPS 자체는 면제. legacy 50개 문서 보강은 별 wave (frontmatter 강제 안 함)

    # staged WIP만 frontmatter 강제 (신규 문서 진입점이 WIP)
    staged_wip = [f for f in staged_files
                  if f.startswith("docs/WIP/") and f.endswith(".md")
                  and not CPS_EXEMPT_PATHS.match(f)]

    for wip in staged_wip:
        try:
            text = Path(wip).read_text(encoding="utf-8")
        except Exception:
            continue
        fm, body_start = parse_frontmatter(text)
        body = "\n".join(text.splitlines()[body_start:])

        # frontmatter problem 검증
        prob = fm.get("problem", "")
        if isinstance(prob, list):
            prob = prob[0] if prob else ""
        if not prob:
            err(f"❌ {wip}: frontmatter `problem` 누락. CPS Problem ID (P#) 명시 필수.")
            ERRORS += 1
            continue
        if not re.match(r"^P\d+$", prob.strip()):
            err(f"❌ {wip}: frontmatter `problem` 형식 위반 ('{prob}'). 'P1'·'P2' 형식.")
            ERRORS += 1
            continue
        wip_problem = prob.strip()

        # frontmatter solution-ref 검증
        sol_refs = fm.get("solution-ref", [])
        if isinstance(sol_refs, str):
            sol_refs = [sol_refs]
        if not sol_refs:
            err(f"❌ {wip}: frontmatter `solution-ref` 누락. Solution 충족 기준 인용 필수.")
            ERRORS += 1
            continue
        wip_solution_ref = "; ".join(sol_refs)

        # 박제 감지 (경고만, 차단 아님)
        if cps_text:
            warns = verify_solution_ref(sol_refs, cps_text)
            for w in warns:
                err(f"⚠ {wip}: solution-ref 박제 의심 — {w}")

        # AC Goal·검증 묶음 추출
        ac = parse_ac_block(body)
        if not ac["goal"]:
            if not ac["ac_section_found"]:
                err(f"❌ {wip}: AC 섹션 없음. `**Acceptance Criteria**:` (bold 형식) 헤더가 필요합니다. `### Acceptance Criteria` 헤더 형식은 인식하지 않습니다.")
            else:
                err(f"❌ {wip}: AC `Goal:` 항목 누락.")
            ERRORS += 1
            continue
        if not ac["ac_review"]:
            err(f"❌ {wip}: AC `검증.review` 누락. (skip|self|review|review-deep)")
            ERRORS += 1
            continue
        if ac["ac_review"] not in ("skip", "self", "review", "review-deep"):
            err(f"❌ {wip}: AC `검증.review` 값 위반 ('{ac['ac_review']}').")
            ERRORS += 1
            continue
        if not ac["ac_tests"]:
            err(f"❌ {wip}: AC `검증.tests` 누락. (pytest 명령 또는 \"없음\")")
            ERRORS += 1
            continue
        if not ac["ac_actual"]:
            err(f"❌ {wip}: AC `검증.실측` 누락. (구체 명령 또는 \"없음\")")
            ERRORS += 1
            continue
        ac_review = ac["ac_review"]
        ac_tests = ac["ac_tests"]
        ac_actual = ac["ac_actual"]

    # ─────────────────────────────────────────────────────────
    # Stage 결정 (AC + CPS 단일 룰)
    # ─────────────────────────────────────────────────────────
    #
    # 외형 룰 (UPSTREAM_PAT·META_M_PAT·docs 5줄·rename/meta 단독·WIP 단독) 폐기.
    # 단일 룰: 시크릿(보안 게이트) > CPS Problem 변경 > AC 검증.review 그대로.

    stage = ""

    # 룰 1: 시크릿 line-confirmed → deep (보안 게이트, 작성자 선언 무시)
    if s1_level == "line-confirmed":
        stage = "deep"

    # 룰 2: CPS Problem 정의 자체 staged → deep (cascade 영향)
    if not stage and any(CPS_EXEMPT_PATHS.match(f) for f in staged_files):
        # CPS 면제 파일이 staged면 그게 곧 CPS 본문 변경
        stage = "deep"

    # 룰 3: AC 검증.review 그대로 stage 결정
    if not stage:
        if ac_review:
            REVIEW_TO_STAGE = {
                "skip": "skip", "self": "micro",
                "review": "standard", "review-deep": "deep",
            }
            stage = REVIEW_TO_STAGE.get(ac_review, "")

    # 폴백: staged WIP 없는 경우 (코드만 staged 가능 — 정당 케이스)
    # 예: 본 commit (1단계 SSOT) 또는 hot fix
    # stage = "" 이면 wip_problem·wip_solution_ref도 ""
    # default standard로 폴백 (외형 metric 회피, 작성자 선언 부재 시 보수)
    if not stage and not staged_wip:
        stage = "standard"

    # ─────────────────────────────────────────────────────────
    # 커밋 분리 판정
    # ─────────────────────────────────────────────────────────

    split_plan   = 0
    split_action = "single"
    group_assign: dict[str, list[str]] = {}

    if HARNESS_SPLIT_SUB:
        split_plan   = 1
        split_action = "sub"
    elif not TEST_MODE and total_files > 0 and Path(".claude/scripts/task_groups.py").exists():
        tg = run([sys.executable, str(Path(__file__).parent / "task_groups.py")])
        if tg:
            for line in tg.splitlines():
                parts = line.split("\t")
                if len(parts) >= 2:
                    group_assign.setdefault(parts[0], []).append(parts[1])
            split_plan = len(group_assign)
            chars: set[str] = set()
            for g in group_assign:
                if g.startswith("char:"):
                    chars.add(g)
                elif g.startswith("wip:"):
                    parts_g = g.split(":")
                    if len(parts_g) >= 3:
                        chars.add(f"char:{parts_g[2]}")

            # split 옵트인 강등 (Phase 3 — 2026-05-02)
            # 기본: 단일 결정 = 단일 커밋 (atomic). 분할은 명시 옵트인.
            # 자동 분할 케이스: 거대 커밋 + char 다양성 (사용자 인지 부담 분산 가치 있을 때)
            #
            # 분할 트리거 조건 (모두 만족):
            #   1. char 다양성 >= 2
            #   2. HARNESS_SPLIT_OPT_IN=1 (사용자 명시) OR 거대 커밋 (files>30 OR +>1500 OR ->1500)
            #   3. stage가 skip 아님 (skip이면 review 분산 효과 0이므로 분할 무의미)
            is_huge = total_files > 30 or added_lines > 1500 or deleted_lines > 1500
            if len(chars) >= 2 and stage != "skip" and (HARNESS_SPLIT_OPT_IN or is_huge):
                split_action = "split"
            else:
                split_action = "single"

    # ─────────────────────────────────────────────────────────
    # prior_session_files
    # ─────────────────────────────────────────────────────────

    prior_files = "none"
    session_file = Path(".claude/memory/session-start-unstaged.txt")
    if session_file.exists():
        staged_list_raw = run(["git", "diff", "--cached", "--name-only"])
        staged_set = set(staged_list_raw.splitlines())
        try:
            session_set = set(session_file.read_text(encoding="utf-8").splitlines())
            overlap = sorted(session_set & staged_set)
            if overlap:
                prior_files = ",".join(overlap)
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────
    # 거대 변경 경고
    # ─────────────────────────────────────────────────────────

    if total_files > 30 or added_lines > 1500 or deleted_lines > 1500:
        err(f"⚠ 대규모 변경 감지 (files={total_files}, +{added_lines}, -{deleted_lines}).")
        err("  권장: 스코프를 나눠 작은 커밋 여러 개로 분리.")

    # ─────────────────────────────────────────────────────────
    # hook 미설치 경고 (Phase 1 — threat-analyst 권고)
    # 시크릿 line-confirmed 가드는 commit 스킬 경유 시에만 작동.
    # 터미널 직접 git commit 시 hook이 안전망. 미설치면 경고.
    # ─────────────────────────────────────────────────────────

    try:
        with open(".claude/HARNESS.json", encoding="utf-8") as f:
            hj = json.load(f)
        if hj.get("hook_installed") is not True:
            err("")
            err("⚠ pre-commit hook 미설치. 터미널 직접 git commit 시 시크릿 가드 부재.")
            if hj.get("is_starter"):
                err("  설치: bash .claude/scripts/install-starter-hooks.sh")
            else:
                err("  설치: bash scripts/install-secret-scan-hook.sh")
    except Exception:
        pass

    # ─────────────────────────────────────────────────────────
    # 출력
    # ─────────────────────────────────────────────────────────

    if ERRORS > 0:
        err("")
        err("🚫 커밋 차단. 위 문제를 해결하라.")

    print(f"pre_check_passed: {'false' if ERRORS > 0 else 'true'}")
    print(f"already_verified: {ALREADY_VERIFIED}")
    print(f"diff_stats: {diff_stats}")
    print(f"wip_problem: {wip_problem or 'none'}")
    print(f"wip_solution_ref: {wip_solution_ref or 'none'}")
    print(f"ac_review: {ac_review or 'none'}")
    print(f"ac_tests: {ac_tests or 'none'}")
    print(f"ac_actual: {ac_actual or 'none'}")
    print(f"recommended_stage: {stage}")
    print(f"s1_level: {s1_level}")
    print(f"split_plan: {split_plan}")
    print(f"split_action_recommended: {split_action}")
    print(f"prior_session_files: {prior_files}")

    if split_action == "split" and group_assign:
        CHAR_PRIO = {"exec": 1, "agent-rule": 2, "skill": 3, "misc": 4, "doc": 9}
        def sort_key(g: str) -> tuple:
            if g.startswith("char:"):
                c = g.split(":", 1)[1]
                return (CHAR_PRIO.get(c, 5), g)
            if g.startswith("wip:"):
                parts_g = g.split(":")
                c = parts_g[2] if len(parts_g) >= 3 else "misc"
                return (CHAR_PRIO.get(c, 5), g)
            return (10, g)
        for i, g in enumerate(sorted(group_assign, key=sort_key), 1):
            print(f"split_group_{i}_name: {g}")
            print(f"split_group_{i}_files: {','.join(group_assign[g])}")

    if ERRORS > 0:
        sys.exit(2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
