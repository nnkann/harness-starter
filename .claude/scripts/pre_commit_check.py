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
# 입력 수집
# ─────────────────────────────────────────────────────────

TEST_MODE = os.environ.get("TEST_MODE", "0") == "1"
HARNESS_EXPAND = os.environ.get("HARNESS_EXPAND", "0") == "1"
HARNESS_SPLIT_SUB = os.environ.get("HARNESS_SPLIT_SUB", "0") == "1"
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

    # C. frontmatter relates-to dead link
    if modified_md:
        for md_src in modified_md:
            if not Path(md_src).exists():
                continue
            try:
                content = Path(md_src).read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            # frontmatter 추출
            fm_lines: list[str] = []
            in_fm = False
            dash_count = 0
            for line in content.splitlines():
                if line.strip() == "---":
                    dash_count += 1
                    if dash_count == 2:
                        break
                    in_fm = True
                    continue
                if in_fm:
                    fm_lines.append(line)

            # relates-to 블록 파싱
            in_rt = False
            for fm_line in fm_lines:
                if re.match(r"^relates-to:\s*$", fm_line):
                    in_rt = True
                    continue
                if in_rt and fm_line and not fm_line[0].isspace():
                    in_rt = False
                if in_rt:
                    m = re.match(r"^\s+-\s+path:\s*(.+)", fm_line)
                    if not m:
                        continue
                    rt_path = m.group(1).strip().strip("'\"")
                    rt_path = re.sub(r"\s*#.*$", "", rt_path)
                    if not rt_path:
                        continue
                    if rt_path.startswith("/"):
                        continue
                    if rt_path.startswith(("../", "./")):
                        resolved = resolve_path(str(Path(md_src).parent), rt_path)
                    else:
                        resolved = f"docs/{rt_path}"
                    resolved_path = resolved.split("#")[0]
                    if resolved_path and not Path(resolved_path).exists():
                        dead_links.append(
                            f"   {md_src} frontmatter relates-to: {rt_path} "
                            f"(resolved: {resolved_path}, 파일 없음)"
                        )

    if dead_links:
        err("❌ dead link 감지 (이번 커밋이 유발):")
        for dl in dead_links:
            err(dl)
        err("   대응: 링크를 수정하거나, 이동된 파일의 새 경로로 갱신")
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
        r"^\+.*(sb_secret_|service_role|sk_live_|sk_test_|ghp_|AKIA[0-9A-Z]{16}|password\s*=)",
        re.I,
    )
    # 하네스 자체가 시크릿 패턴을 SSOT로 문서화하는 위치는 line 스캔 면제
    # (scripts: 정의/테스트 픽스처, agents/rules/skills/memory: 패턴 인용 문서)
    S1_LINE_EXEMPT = re.compile(
        r"^\.claude/(scripts|agents|rules|skills|memory)/"
        r"|^docs/(WIP|incidents|decisions|guides|harness)/"
        r"|^scripts/install-secret-scan-hook\.sh$"
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
    # 6. WIP에서 AC kind 읽기 (stage 판단용) — task 블록 단위
    # ─────────────────────────────────────────────────────────
    #
    # staged 파일이 영향을 주는 task만 골라서 그 task의 kind / has_impact_scope를 본다.
    # WIP 파일 전체 스캔 금지 — 다른 task의 `영향 범위:` 항목이 섞이면 오판.

    wip_kind = ""
    has_impact_scope = False

    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from task_groups import parse_wip_tasks  # type: ignore

        tasks = parse_wip_tasks()  # {(slug, task_id): {kind, impact_files, has_impact_scope}}

        matched_tasks: list[dict] = []

        for f in staged_files:
            # staged WIP 파일 자체 → 그 슬러그의 모든 task 영향 후보
            if f.startswith("docs/WIP/") and f.endswith(".md"):
                slug = Path(f).stem
                if "--" in slug:
                    slug = slug.split("--", 1)[1]
                for (s, _), info in tasks.items():
                    if s == slug:
                        matched_tasks.append(info)
                continue

            # 일반 staged 파일 → impact_files 매칭
            fbn = Path(f).name
            for (_, _), info in tasks.items():
                for pattern in info["impact_files"]:
                    pbn = Path(pattern).name
                    if f == pattern or f.endswith("/" + pattern) or fbn == pbn:
                        matched_tasks.append(info)
                        break

        # 매칭된 task들 중 kind 결정 (가장 강한 stage 유도하는 kind 우선: refactor/feature > bug > docs/chore)
        KIND_PRIO = {"refactor": 4, "feature": 3, "bug": 2, "docs": 1, "chore": 1}
        if matched_tasks:
            best = max(matched_tasks, key=lambda t: KIND_PRIO.get(t["kind"], 0))
            wip_kind = best["kind"]
            # has_impact_scope는 매칭된 task에서 OR
            has_impact_scope = any(t["has_impact_scope"] for t in matched_tasks)
    except Exception:
        pass

    # ─────────────────────────────────────────────────────────
    # Stage 결정 (AC kind 기반)
    # ─────────────────────────────────────────────────────────

    UPSTREAM_PAT = re.compile(
        r"^(?:\.claude/scripts/|\.claude/agents/|\.claude/hooks/|\.claude/settings\.json$|h-setup\.sh$)"
    )
    META_M_PAT = re.compile(
        r"^docs/clusters/|^\.claude/HARNESS\.json$|^\.claude/memory/|^CHANGELOG\.md$"
    )

    stage = ""

    # 룰 1: 업스트림 위험 경로 → deep
    if not stage and any(UPSTREAM_PAT.match(f) for f in staged_files):
        stage = "deep"

    # 룰 2: 시크릿 line-confirmed → deep
    if not stage and s1_level == "line-confirmed":
        stage = "deep"

    # 룰 3: skip 조건
    if not stage:
        rename_count = non_move = m_non_meta = 0
        for status, path in ns_parsed:
            if status.startswith("R"):
                rename_count += 1
            elif status == "M":
                if not META_M_PAT.match(path):
                    m_non_meta += 1
            else:
                non_move += 1

        is_meta_only = all(
            META_M_PAT.match(p) for st, p in ns_parsed if not st.startswith("R")
        ) if ns_parsed else False

        # 이동 커밋 (rename 단독)
        if rename_count > 0 and non_move == 0 and m_non_meta == 0:
            stage = "skip"
        # 메타 단독
        elif is_meta_only and rename_count == 0 and non_move == 0:
            stage = "skip"
        # WIP 단독
        elif (all(f.startswith("docs/WIP/") for f in staged_files)
              and staged_files
              and not any(f.startswith(".claude/skills/") or f.startswith(".claude/agents/")
                          for f in staged_files)):
            stage = "skip"
        # docs 5줄 이하
        elif (all(f.endswith(".md") for f in staged_files)
              and staged_files
              and total_lines <= 5):
            stage = "skip"

    # 룰 4: AC kind 기반 판단
    if not stage:
        if wip_kind in ("docs", "chore"):
            stage = "micro"
        elif wip_kind == "bug":
            stage = "standard" if has_impact_scope else "micro"
        elif wip_kind in ("feature", "refactor"):
            stage = "deep" if has_impact_scope else "standard"
        else:
            # WIP 없거나 kind 미지정 → standard
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
            split_action = "split" if len(chars) >= 2 else "single"

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
    print(f"wip_kind: {wip_kind or 'none'}")
    print(f"has_impact_scope: {'true' if has_impact_scope else 'false'}")
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
