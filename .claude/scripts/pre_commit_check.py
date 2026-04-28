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

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# ─────────────────────────────────────────────────────────
# 헬퍼
# ─────────────────────────────────────────────────────────

def run(cmd: list[str], *, check=False) -> str:
    """subprocess 실행 → stdout 문자열 반환. 실패 시 빈 문자열."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
        return r.stdout
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
HARNESS_UPGRADE = os.environ.get("HARNESS_UPGRADE", "0") == "1"
VERBOSE = os.environ.get("VERBOSE", "")

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

ENOENT_PATTERNS = re.compile(
    r"is not recognized as an internal or external command"
    r"|: command not found$"
    r"|command not found: [a-zA-Z0-9_./+-]+$"
    r"|^exec: [^:]+: not found$"
    r"|^sh: [0-9]+: [^:]+: not found$"
    r"|ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL",
    re.MULTILINE,
)

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
# rename의 경우 old path가 사라지므로 별도로 추출 필요 (ns_parsed는 new path만 가짐)
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
# 5. 위험도 수집
# ─────────────────────────────────────────────────────────

risk_reasons: list[str] = []

if total_files >= 5:
    risk_reasons.append(f"변경 파일 {total_files}개 (≥5)")
if deleted_lines >= 50:
    risk_reasons.append(f"삭제 {deleted_lines}줄 (≥50)")

CORE_FILE_PAT = re.compile(
    r"^(?:CLAUDE\.md|\.claude/settings\.json|\.claude/rules/|\.claude/scripts/)"
)
if any(CORE_FILE_PAT.match(f) for f in staged_files):
    risk_reasons.append("핵심 설정 파일 변경")

SEC_FILE_PAT = re.compile(r"auth|token|secret|key|credential|password", re.I)
SEC_DIFF_PAT = re.compile(r"^\+.*(auth|token|secret|key|credential|password)", re.I | re.MULTILINE)
if any(SEC_FILE_PAT.search(f) for f in staged_files) or SEC_DIFF_PAT.search(diff_u0_raw):
    risk_reasons.append("보안 관련 패턴 감지")

INFRA_PAT = re.compile(r"Dockerfile|docker-compose|\.github/workflows/|\.gitlab-ci|deploy", re.I)
if any(INFRA_PAT.search(f) for f in staged_files):
    risk_reasons.append("인프라/배포 파일 변경")

# 단일 파일 추가+삭제 동시 30줄 이상
for line in numstat_raw.splitlines():
    parts = line.split()
    if len(parts) >= 3:
        try:
            if int(parts[0]) >= 30 and int(parts[1]) >= 30:
                risk_reasons.append(f"구조적 수정 감지: {parts[2]}")
                break
        except ValueError:
            pass

risk_factors_summary = ";".join(risk_reasons)

# ─────────────────────────────────────────────────────────
# 6. S10 연속 수정 카운트
# ─────────────────────────────────────────────────────────

REPEAT_RANGE = 5
EXEMPT_PAT   = re.compile(r"^\.claude/HARNESS\.json$|^docs/clusters/")
CORE_PAT     = re.compile(r"^CLAUDE\.md$|^\.claude/settings\.json$|^\.claude/rules/|^\.claude/scripts/")

if TEST_MODE:
    recent_files: list[str] = []
else:
    recent_raw = run(["git", "log", f"-{REPEAT_RANGE}", "--name-only", "--format="])
    recent_files = [l for l in recent_raw.splitlines() if l.strip()]

# 카운트 맵 구축
from collections import Counter
recent_count = Counter(recent_files)

repeat_warn_hit: list[str] = []
repeat_block_hit: list[str] = []
repeat_block_core: list[tuple[str, int]] = []

for f in staged_files:
    if EXEMPT_PAT.match(f):
        continue
    c = recent_count[f]
    if c >= 3:
        repeat_block_hit.append(f"   - {f} (최근 {REPEAT_RANGE}커밋 중 {c}회)")
        if CORE_PAT.match(f):
            repeat_block_core.append((f, c))
    elif c >= 2:
        repeat_warn_hit.append(f"   - {f} (최근 {REPEAT_RANGE}커밋 중 {c}회)")

if repeat_block_core:
    for f, c in repeat_block_core:
        err("")
        err(f"❌ 핵심 설정 파일 {c}회 연속 수정: {f}")
        err("   추측 수정 가능성. 다음을 먼저 확인:")
        err(f"   1. git log -5 -- {f} (이전 수정 사유)")
        err("   2. docs/incidents/ (관련 사례)")
        err("   3. 공식 문서 (rules/internal-first.md)")
        err("   정당한 점진 확장이면 HARNESS_EXPAND=1 prefix로 우회:")
        err("     HARNESS_EXPAND=1 git commit -m \"...\"")
        if HARNESS_EXPAND:
            if VERBOSE:
                err("   (HARNESS_EXPAND=1 감지 — 통과)")
        else:
            ERRORS += 1

repeat_max = 0
for f in staged_files:
    if EXEMPT_PAT.match(f):
        continue
    repeat_max = max(repeat_max, recent_count[f])

# ─────────────────────────────────────────────────────────
# 7. 신호 감지 (S1~S15)
# ─────────────────────────────────────────────────────────

signals: list[str] = []
sig_set: set[str] = set()

def add_signal(s: str) -> None:
    if s not in sig_set:
        signals.append(s)
        sig_set.add(s)

def has_sig(s: str) -> bool:
    return s in sig_set

# S1~S6, S11, S14, S15 통합 분류
S1_FILE_PAT = re.compile(
    r"auth|token|secret|key|credential|password|\.env", re.I
)
S1_EXEMPT   = re.compile(
    r"\.(test|spec)\.|/tests?/|/__tests__/|^docs/|\.md$|/example|-helper\.|-utils?\."
)
S2_PAT  = re.compile(
    r"^(?:CLAUDE\.md|\.claude/settings\.json|\.claude/rules/|\.claude/scripts/"
    r"|\.claude/hooks/|Dockerfile|docker-compose|\.github/workflows/)"
)
S11_PAT = re.compile(r"^(?:scripts/.*\.sh$|\.husky/|Makefile$)")
S14_PAT = re.compile(r"(?:^|/)migrations/|^alembic/versions/|^prisma/migrations/")
S15_PAT = re.compile(
    r"^(?:package\.json|pyproject\.toml|Cargo\.toml|go\.mod"
    r"|requirements.*\.txt|Gemfile|composer\.json)$"
)
LOCK_PAT = re.compile(
    r"^(?:package-lock\.json|pnpm-lock\.yaml|yarn\.lock|bun\.lockb"
    r"|uv\.lock|Cargo\.lock|go\.sum|composer\.lock|Gemfile\.lock)$"
)
META_PAT = re.compile(
    r"^(?:\.claude/HARNESS\.json|docs/clusters/.*\.md"
    r"|\.claude/memory/.*\.md|CHANGELOG\.md)$"
)
DOC_PAT  = re.compile(r"^docs/|\.md$")

s1_file_hit = False
s2_hit = s11_hit = s14_hit = s15_hit = False
lock_count = meta_count = doc_count = 0

for f in staged_files:
    if S1_FILE_PAT.search(f) and not S1_EXEMPT.search(f):
        s1_file_hit = True
    if S2_PAT.match(f):  s2_hit  = True
    if S11_PAT.match(f): s11_hit = True
    if S14_PAT.search(f):s14_hit = True
    if S15_PAT.match(f): s15_hit = True
    # 상호 배타 (lock > meta > doc)
    if LOCK_PAT.match(f):    lock_count += 1
    elif META_PAT.match(f):  meta_count += 1
    elif DOC_PAT.match(f):   doc_count  += 1

non_lock = total_files - lock_count
non_meta = total_files - meta_count
non_doc  = total_files - doc_count

# S1 라인 hit
S1_LINE_PAT = re.compile(
    r"^\+.*(sb_secret_|service_role|sk_live_|sk_test_|ghp_|AKIA[0-9A-Z]{16}|password\s*=)",
    re.I | re.MULTILINE,
)
s1_line_hit = bool(S1_LINE_PAT.search(diff_u0_raw))

s1_level = ""
if s1_line_hit:
    add_signal("S1"); s1_level = "line-confirmed"
elif s1_file_hit:
    add_signal("S1"); s1_level = "file-only"

if s2_hit:  add_signal("S2")

# S3: 모든 staged가 신규(A)
if total_files > 0:
    non_added = sum(1 for status, _ in ns_parsed if status != "A")
    if non_added == 0:
        add_signal("S3")

# S4/S5/S6 단독
if lock_count > 0 and non_lock == 0: add_signal("S4")
if meta_count > 0 and non_meta == 0: add_signal("S5")
if doc_count  > 0 and non_doc  == 0 and not has_sig("S5"): add_signal("S6")

# S8: 공유 모듈 시그니처 변경
S8_TEST_PAT = re.compile(r"\.(test|spec)\.|/tests?/|/__tests__/")
S8_JS_PAT   = re.compile(
    r"^[+-]export\s+(?:default\s+)?(?:async\s+)?(?:class|function|interface|type|enum|const|let|var)\s+"
)
S8_PY_PAT   = re.compile(r"^[+-](?:async\s+)?(?:def|class)\s+[a-zA-Z_]")
S8_GO_PAT   = re.compile(r"^[+-](?:func|type|var|const)\s+[A-Z][a-zA-Z0-9_]*")
S8_JAVA_PAT = re.compile(
    r"^[+-]\s*public\s+(?:static\s+)?(?:class|interface|enum|[a-zA-Z<>]+\s+[a-zA-Z_])"
)

current_file = ""
current_ext  = ""
s8_found = False
for line in diff_u0_raw.splitlines():
    if line.startswith("diff --git "):
        p = line.split()[-1]
        current_file = p[2:] if p.startswith("b/") else p
        if S8_TEST_PAT.search(current_file):
            current_ext = ""
        elif re.search(r"\.(ts|tsx|js|jsx)$", current_file): current_ext = "js"
        elif current_file.endswith(".py"):                    current_ext = "py"
        elif current_file.endswith(".go"):                    current_ext = "go"
        elif re.search(r"\.(java|cs)$", current_file):       current_ext = "java"
        else:                                                 current_ext = ""
        continue
    if line.startswith(("+++", "---")):
        continue
    if not s8_found:
        if current_ext == "js"   and S8_JS_PAT.match(line):   s8_found = True
        elif current_ext == "py" and S8_PY_PAT.match(line):   s8_found = True
        elif current_ext == "go" and S8_GO_PAT.match(line):   s8_found = True
        elif current_ext == "java" and S8_JAVA_PAT.match(line): s8_found = True

if s8_found:
    add_signal("S8")

# S9: 도메인 추출 + 등급 매핑
doc_domains: set[str] = set()
for f in staged_files:
    if f.startswith("docs/") and f.endswith(".md") and Path(f).exists():
        try:
            for l in Path(f).read_text(encoding="utf-8", errors="ignore").splitlines():
                if l.startswith("domain:"):
                    d = l[7:].strip()
                    if d:
                        doc_domains.add(d)
                    break
                if l.strip() == "---" and doc_domains:
                    break
        except Exception:
            pass

wip_domains: set[str] = set()
WIP_PREFIX = re.compile(r"^docs/WIP/([^-]+)--")
for f in staged_files:
    m = WIP_PREFIX.match(f)
    if m:
        wip_domains.add(m.group(1))

all_domains = sorted(doc_domains | wip_domains)
domains_str = ",".join(all_domains)

domain_grades: list[str] = []
grade_map: dict[str, str] = {}

naming_md = Path(".claude/rules/naming.md")
if all_domains and naming_md.exists():
    in_section = False
    for line in naming_md.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("## 도메인 등급"):
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section:
            if "**critical**" in line:
                after = re.sub(r".*:", "", line)
                for d in re.sub(r"[*()]", "", after).replace(",", " ").split():
                    if d:
                        grade_map[d] = "critical"
            elif "**meta**" in line:
                after = re.sub(r".*:", "", line)
                for d in re.sub(r"[*()]", "", after).replace(",", " ").split():
                    if d:
                        grade_map[d] = "meta"

    for d in all_domains:
        domain_grades.append(grade_map.get(d, "normal"))

domain_grades_str = ",".join(domain_grades)
if domain_grades:
    add_signal("S9")

domain_count = len(all_domains)
multi_domain = "true" if domain_count >= 2 else "false"

# S10
if repeat_max >= 2:
    add_signal("S10")

# S11/S14/S15
if s11_hit: add_signal("S11")
if s14_hit: add_signal("S14")
if s15_hit: add_signal("S15")

# S7: 위 신호 없으면 일반 코드
if total_files > 0 and not any(has_sig(s) for s in ("S3", "S4", "S5", "S6")):
    add_signal("S7")

# ─────────────────────────────────────────────────────────
# Stage 결정
# ─────────────────────────────────────────────────────────

UPSTREAM_PAT = re.compile(
    r"^(?:\.claude/scripts/|\.claude/agents/|\.claude/hooks/|\.claude/settings\.json$|h-setup\.sh$)"
)

stage = ""

# 룰 0: harness-upgrade 커밋 — upstream 검증된 코드, review 불필요
if HARNESS_UPGRADE:
    stage = "skip"

# 룰 1: 업스트림 위험 경로
if not stage and any(UPSTREAM_PAT.match(f) for f in staged_files):
    stage = "deep"

# 룰 2: 치명 신호
if not stage:
    if s1_level == "line-confirmed" or has_sig("S14") or has_sig("S8"):
        stage = "deep"

# 룰 3: skip 조건
is_move_commit = False
if not stage:
    META_M_PAT = re.compile(
        r"^docs/clusters/|^\.claude/HARNESS\.json$|^\.claude/memory/|^CHANGELOG\.md$"
    )
    rename_count = non_move = m_non_meta = 0
    for status, path in ns_parsed:
        if status.startswith("R"):
            rename_count += 1
        elif status == "M":
            if not META_M_PAT.match(path):
                m_non_meta += 1
        else:
            non_move += 1
    if rename_count > 0 and non_move == 0 and m_non_meta == 0:
        stage = "skip"
        is_move_commit = True
    elif has_sig("S5") and not any(has_sig(s) for s in ("S7", "S2", "S8", "S14")):
        stage = "skip"
    elif has_sig("S4") and not has_sig("S7"):
        stage = "skip"
    elif (has_sig("S6")
          and not any(has_sig(s) for s in ("S7", "S2", "S8", "S14", "S11"))
          and not any(f.startswith(".claude/skills/") or f.startswith(".claude/agents/")
                      for f in staged_files)
          and any(f.startswith("docs/WIP/") for f in staged_files)
          and all(f.startswith("docs/WIP/") for f in staged_files)):
        stage = "skip"
    elif (has_sig("S6") and total_lines <= 5
          and not any(has_sig(s) for s in ("S7", "S2", "S8", "S14", "S11"))
          and not any(f.startswith(".claude/skills/") or f.startswith(".claude/agents/")
                      for f in staged_files)):
        stage = "skip"

# 룰 4: 나머지 → standard
if not stage:
    stage = "standard"

# 2단계: S10 격상
if not is_move_commit:
    if repeat_max >= 3:
        stage = "deep"
    elif repeat_max == 2:
        stage = {"skip": "standard", "micro": "standard", "standard": "deep"}.get(stage, stage)

# ─────────────────────────────────────────────────────────
# 거대 변경 경고
# ─────────────────────────────────────────────────────────

if total_files > 30 or added_lines > 1500 or deleted_lines > 1500:
    err(f"⚠ 대규모 변경 감지 (files={total_files}, +{added_lines}, -{deleted_lines}).")
    err("  review maxTurns 한계로 verdict 신뢰도 저하 + 검토 피로 누적 가능.")
    err("  권장: 스코프를 나눠 작은 커밋 여러 개로 분리. 논리 단위별로 staging.")

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
        # 성격(char) 기반 split 조건 — 서로 다른 char가 2종 이상이면 split
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
# 출력
# ─────────────────────────────────────────────────────────

signals_str = ",".join(signals)

if ERRORS > 0:
    err("")
    err("🚫 커밋 차단. 위 문제를 해결하라.")

print(f"pre_check_passed: {'false' if ERRORS > 0 else 'true'}")
print(f"already_verified: {ALREADY_VERIFIED}")
print(f"risk_factors: {risk_factors_summary}")
print(f"diff_stats: {diff_stats}")
print(f"signals: {signals_str}")
print(f"domains: {domains_str}")
print(f"domain_grades: {domain_grades_str}")
print(f"multi_domain: {multi_domain}")
print(f"repeat_count: max={repeat_max}")
print(f"recommended_stage: {stage}")
print(f"s1_level: {s1_level}")
print(f"split_plan: {split_plan}")
print(f"split_action_recommended: {split_action}")
print(f"prior_session_files: {prior_files}")

if split_action == "split" and group_assign:
    # char 기반 정렬 — 위험도 높은 순서 (exec 먼저, doc 마지막)
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
