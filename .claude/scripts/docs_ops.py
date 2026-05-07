#!/usr/bin/env python3
"""
서브커맨드:
  validate                     프론트매터·약어 검증
  move <wip-file>              WIP 접두사로 대상 폴더 이동 + status=completed
  reopen <completed-file>      완료 문서를 WIP로 되돌림 + status=in-progress
  cluster-update               모든 clusters/*.md 재생성
  verify-relates               relates-to.path 정합성 전수 검사
  wip-sync <file> [...]        commit Step 7.5 — staged 파일 체크리스트 ✅ 갱신

종료 코드:
  0 성공
  1 일반 오류
  2 차단 (completed 전환 차단 등)
"""

import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

NAMING_MD = Path(".claude/rules/naming.md")
DOCS_DIR  = Path("docs")

# ─────────────────────────────────────────────────────────
# 유틸
# ─────────────────────────────────────────────────────────

def extract_abbrs() -> list[str]:
    """naming.md '## 도메인 약어' 섹션에서 abbr 목록 추출."""
    if not NAMING_MD.exists():
        return []
    text = NAMING_MD.read_text(encoding="utf-8")
    in_section = False
    abbrs: set[str] = set()
    for line in text.splitlines():
        if re.match(r"^## 도메인 약어", line):
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section and re.match(r"^\| [a-z_]+\s*\|\s*[a-z]{2,3}\s*\|", line):
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 2:
                abbrs.add(parts[1])
    return sorted(abbrs)


def extract_path_domain_map() -> list[tuple[str, str]]:
    """naming.md '## 경로 → 도메인 매핑' 섹션에서 [(glob_pattern, domain), ...] 추출.
    '실제 매핑' 레이블 이후 코드블록만 파싱. 섹션이 없거나 비어있으면 빈 리스트."""
    if not NAMING_MD.exists():
        return []
    text = NAMING_MD.read_text(encoding="utf-8")
    in_section = in_block = in_real = False
    pairs: list[tuple[str, str]] = []
    for line in text.splitlines():
        if re.match(r"^## 경로 → 도메인 매핑", line):
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section:
            if re.match(r"^실제 매핑", line.strip()):
                in_real = True
                continue
            if line.strip() == "```":
                in_block = not in_block
                if not in_block:
                    in_real = False  # 블록 종료 시 리셋
                continue
            if in_block and in_real:
                m = re.match(r"^(\S+)\s*→\s*(\S+)", line.strip())
                if m:
                    pairs.append((m.group(1), m.group(2)))
    return pairs


def path_to_domain(filepath: str, path_domain_map: list[tuple[str, str]]) -> str | None:
    """staged 파일 경로를 경로→도메인 매핑으로 도메인 추출. 없으면 None."""
    from fnmatch import fnmatch
    fp = filepath.replace("\\", "/")
    for pattern, domain in path_domain_map:
        # 패턴 정규화: src/payment/** → fnmatch로 처리
        pat = pattern.rstrip("/")
        if fnmatch(fp, pat) or fnmatch(fp, pat + "/*") or fp.startswith(pat.rstrip("*").rstrip("/") + "/"):
            return domain
    return None


def detect_abbr(filepath: Path, abbrs: list[str]) -> str | None:
    """파일명에서 abbr 추출 (첫 매치 정책, 라우팅/불투명 prefix 통과)."""
    name = filepath.stem  # .md 제거
    # 라우팅 접두사 (`decisions--` 등) 제거
    if "--" in name:
        name = name.split("--", 1)[1]
    pat = "|".join(re.escape(a) for a in abbrs)
    if not pat:
        return None
    m = re.search(rf"(?:^|[_-])({pat})_", name)
    return m.group(1) if m else None


def extract_frontmatter(path: Path) -> dict[str, str]:
    """YAML frontmatter를 간단 파싱 → {field: value} 딕셔너리."""
    fm: dict[str, str] = {}
    if not path.exists():
        return fm
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    dash_count = 0
    for line in lines:
        if line.strip() == "---":
            dash_count += 1
            if dash_count == 2:
                break
            continue
        if dash_count == 1 and ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip("'\"")
    return fm


def write_frontmatter_field(path: Path, field: str, value: str) -> None:
    """파일의 frontmatter 특정 필드 값을 교체 (없으면 created: 뒤에 추가)."""
    text = path.read_text(encoding="utf-8")
    pat = re.compile(rf"^{re.escape(field)}:\s*.*$", re.MULTILINE)
    if pat.search(text):
        text = pat.sub(f"{field}: {value}", text)
    else:
        # created: 뒤에 삽입
        text = re.sub(
            r"^(created:\s*.*)$", rf"\1\n{field}: {value}", text, flags=re.MULTILINE
        )
    path.write_text(text, encoding="utf-8")


def resolve_path(base_dir: str, link: str) -> str:
    """상대경로 link를 base_dir 기준으로 정규화."""
    parts = []
    for part in (base_dir + "/" + link).replace("\\", "/").split("/"):
        if part == "..":
            if parts:
                parts.pop()
        elif part not in (".", ""):
            parts.append(part)
    return "/".join(parts)


def git(args: list[str]) -> subprocess.CompletedProcess:
    # Windows + 한글 환경 cp949 디코딩 결함 방지 (incident hn_upstream_anomalies G)
    return subprocess.run(["git"] + args, capture_output=True, text=True, encoding="utf-8")


# ─────────────────────────────────────────────────────────
# validate
# ─────────────────────────────────────────────────────────

def cmd_validate() -> int:
    errors = warnings = 0
    print("## docs 정합성 검증\n")

    # 확정 도메인 목록
    domains: set[str] = set()
    if NAMING_MD.exists():
        for line in NAMING_MD.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^확정:\s*(.+)", line)
            if m:
                domains = {d.strip() for d in m.group(1).split(",") if d.strip()}

    abbrs = extract_abbrs()
    # 중복 검사
    seen: set[str] = set()
    for a in abbrs:
        if a in seen:
            print(f"❌ 약어 중복: {a}")
            errors += 1
        seen.add(a)

    valid_statuses = {"pending", "in-progress", "completed", "abandoned", "sample"}

    for md in sorted(DOCS_DIR.rglob("*.md")):
        fm = extract_frontmatter(md)
        f = str(md)

        if not fm.get("title"):
            print(f"❌ {f}: title 누락"); errors += 1
        domain = fm.get("domain", "")
        if not domain:
            print(f"❌ {f}: domain 누락"); errors += 1
        elif domains and domain not in domains:
            print(f"⚠️  {f}: domain '{domain}' 이(가) naming.md 확정 목록에 없음")
            warnings += 1
        status = fm.get("status", "")
        if not status:
            print(f"❌ {f}: status 누락"); errors += 1
        elif status not in valid_statuses:
            print(f"⚠️  {f}: status '{status}' 비정상"); warnings += 1
        created = fm.get("created", "")
        if not created:
            print(f"❌ {f}: created 누락"); errors += 1
        elif not re.match(r"^\d{4}-\d{2}-\d{2}$", created):
            print(f"⚠️  {f}: created 형식 비정상 ({created})"); warnings += 1
        if re.search(r"_\d{6}\.md$", md.name):
            print(f"⚠️  {f}: 파일명 날짜 suffix 금지 (naming.md)"); warnings += 1

    print(f"\n결과: 오류 {errors}, 경고 {warnings}")
    return 1 if errors else 0


# ─────────────────────────────────────────────────────────
# move <wip-file>
# ─────────────────────────────────────────────────────────

# 명령형 패턴만 차단. 키워드 단독 매칭은 회고적 서술까지 잡아 오탐.
# TODO:/FIXME: (콜론 표기 — 코드 주석·이슈 트래커 관습)
BLOCK_KEYWORDS = re.compile(r"\b(TODO|FIXME)\s*:", re.IGNORECASE)
# 빈 체크박스 — 진짜 미완료 신호
BLOCK_EMPTY_CHECKBOX = re.compile(r"^\s*[-*]\s*\[\s\]\s", re.MULTILINE)
# 섹션 헤더의 미결 키워드 — 명백히 미결 항목 그룹
BLOCK_HEADERS = re.compile(
    r"^\s*#{1,6}\s*(후속|미결|미결정|추후|나중에|별도로)\b", re.MULTILINE
)
DONE_PAT = re.compile(r"✅|완료|처리됨|done", re.IGNORECASE)
RESULT_SECTION = re.compile(r"^## (처리 결과|원본|회고|처리|결과)", re.MULTILINE)


def _extract_body(text: str) -> str:
    """프론트매터 제거 + '처리 결과' 섹션 이후 skip + 코드블록 안 제외.

    코드블록(``` 또는 ~~~) 안의 라인은 차단 검사 대상 아님 — 예시 포맷이지
    진짜 미결 항목이 아니므로 면제.
    """
    lines = text.splitlines()
    i, dash = 0, 0
    while i < len(lines):
        if lines[i].strip() == "---":
            dash += 1
            i += 1
            if dash == 2:
                break
        else:
            i += 1
    body_lines, skip, in_code = [], False, False
    for line in lines[i:]:
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_code = not in_code
            continue
        if RESULT_SECTION.match(line):
            skip = True
        if not skip and not in_code:
            body_lines.append(line)
    return "\n".join(body_lines)


def _rewrite_relates_to(old_rel: str, new_rel: str, skip: Path) -> list[Path]:
    """docs/**/*.md 전체에서 relates-to.path == old_rel 인 항목을 new_rel 로 갱신.
    skip 파일(이동된 파일 자신)은 제외. 갱신된 파일 경로 목록 반환."""
    pat = re.compile(
        r"(^[ \t]*-[ \t]+path:[ \t]+)" + re.escape(old_rel) + r"([ \t]*$)",
        re.MULTILINE,
    )
    rewritten: list[Path] = []
    for md in DOCS_DIR.rglob("*.md"):
        if md.resolve() == skip.resolve():
            continue
        text = md.read_text(encoding="utf-8", errors="ignore")
        new_text, n = pat.subn(rf"\g<1>{new_rel}\2", text)
        if n:
            md.write_text(new_text, encoding="utf-8")
            subprocess.run(["git", "add", str(md)], capture_output=True)
            rewritten.append(md)
    return rewritten


def cmd_move(src_str: str) -> int:
    if not src_str:
        print("사용법: docs-ops.py move <wip-file>", file=sys.stderr); return 1
    src = Path(src_str)
    if not src.exists():
        print(f"❌ 파일 없음: {src}", file=sys.stderr); return 1
    if not str(src).startswith("docs/WIP/") and not str(src).replace("\\", "/").startswith("docs/WIP/"):
        print(f"❌ WIP 파일만 이동 가능: {src}", file=sys.stderr); return 1

    bn = src.name
    if "--" not in bn:
        print(f"❌ 접두사 없음 (decisions--/guides--/... 필요): {bn}", file=sys.stderr)
        return 1
    prefix, rest = bn.split("--", 1)

    folders = {"decisions", "guides", "incidents", "harness"}
    if prefix not in folders:
        print(f"❌ 접두사 '{prefix}--' 인식 불가. {folders} 중 하나여야 함", file=sys.stderr)
        return 1
    if re.search(r"_\d{6}\.md$", rest):
        print(f"❌ 파일명 날짜 suffix 금지 (naming.md): {rest}", file=sys.stderr)
        return 1

    text = src.read_text(encoding="utf-8")
    body = _extract_body(text)

    # 차단 검사 — 명령형 패턴만
    todo_lines = [l for l in body.splitlines()
                  if BLOCK_KEYWORDS.search(l) and not DONE_PAT.search(l)
                  and not re.search(r"todo_fixme|todo/fixme", l, re.I)]
    checkbox_lines = [l for l in body.splitlines() if BLOCK_EMPTY_CHECKBOX.match(l)]
    header_lines = [l for l in body.splitlines() if BLOCK_HEADERS.match(l)]

    if todo_lines or checkbox_lines or header_lines:
        print(f"🚫 completed 전환 차단: {src} 본문에 미결 패턴 존재", file=sys.stderr)
        for l in todo_lines:     print(f"   TODO/FIXME: {l}", file=sys.stderr)
        for l in checkbox_lines: print(f"   빈 체크박스: {l}", file=sys.stderr)
        for l in header_lines:   print(f"   미결 헤더: {l}", file=sys.stderr)
        print("   대응: (a) 잔여를 별도 WIP로 분리 (b) 미완료 항목 처리 후 재시도",
              file=sys.stderr)
        return 2

    dest = Path(f"docs/{prefix}/{rest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = git(["mv", str(src), str(dest)])
    if r.returncode != 0:
        # 미추적 파일(untracked)은 git mv 불가 — shutil로 이동 후 인덱스 수동 갱신
        shutil.move(str(src), str(dest))
        ra = git(["add", str(dest)])
        # src가 인덱스에 있을 때만 rm --cached 시도 (untracked 파일은 skip)
        src_in_index = git(["ls-files", "--error-unmatch", str(src)]).returncode == 0
        if src_in_index:
            rb = git(["rm", "--cached", str(src)])
            if rb.returncode != 0:
                print(f"❌ 인덱스 rm 실패: src={src} rc={rb.returncode}",
                      file=sys.stderr)
                return 1
        if ra.returncode != 0:
            print(f"❌ 인덱스 add 실패: dest={dest} rc={ra.returncode}",
                  file=sys.stderr)
            return 1

    today = date.today().isoformat()
    write_frontmatter_field(dest, "status", "completed")
    write_frontmatter_field(dest, "updated", today)

    # reopen→move 절차 추적: pre_commit_check.py가 M 파일 봉인 면제에 사용
    session_file = Path(".claude/memory/session-moved-docs.txt")
    try:
        existing = session_file.read_text(encoding="utf-8") if session_file.exists() else ""
        dest_unix = str(dest).replace("\\", "/")
        if dest_unix not in existing.splitlines():
            session_file.write_text(existing + dest_unix + "\n", encoding="utf-8")
    except OSError:
        pass

    # 역참조 갱신: 다른 문서의 relates-to.path가 이동 전 경로를 가리키면 새 경로로 갱신
    old_rel = str(src).replace("\\", "/").removeprefix("docs/")   # e.g. WIP/harness--hn_foo.md
    new_rel = str(dest).replace("\\", "/").removeprefix("docs/")  # e.g. harness/hn_foo.md
    rewritten = _rewrite_relates_to(old_rel, new_rel, skip=dest)

    print("## 문서 이동 완료\n")
    print(f"이동됨: {src} → {dest}")
    print(f"갱신됨: status=completed, updated={today}")
    if rewritten:
        print(f"relates_to_rewritten: {len(rewritten)}개 파일 ({', '.join(str(p) for p in rewritten)})")
    else:
        print("relates_to_rewritten: 0")
    return 0


# ─────────────────────────────────────────────────────────
# reopen <completed-file>
# ─────────────────────────────────────────────────────────

def cmd_reopen(src_str: str) -> int:
    if not src_str:
        print("사용법: docs-ops.py reopen <completed-file>", file=sys.stderr); return 1
    src = Path(src_str)
    if not src.exists():
        print(f"❌ 파일 없음: {src}", file=sys.stderr); return 1
    src_unix = str(src).replace("\\", "/")
    if src_unix.startswith("docs/WIP/"):
        print(f"❌ 이미 WIP: {src}", file=sys.stderr); return 1

    folder = src.parent.name
    if folder not in {"decisions", "guides", "incidents", "harness"}:
        print(f"❌ 지원되지 않는 폴더: {folder}", file=sys.stderr); return 1

    dest = Path(f"docs/WIP/{folder}--{src.name}")
    git(["mv", str(src), str(dest)])
    write_frontmatter_field(dest, "status", "in-progress")

    print("## 완료 문서 재개\n")
    print(f"되돌림: {src} → {dest}")
    print("갱신됨: status=in-progress")
    return 0


# ─────────────────────────────────────────────────────────
# cluster-update
# ─────────────────────────────────────────────────────────

def cmd_cluster_update() -> int:
    Path("docs/clusters").mkdir(parents=True, exist_ok=True)
    abbrs = extract_abbrs()
    if not abbrs:
        print("❌ naming.md 약어 표 비어있음", file=sys.stderr); return 1

    # abbr → domain 역매핑
    abbr_to_domain: dict[str, str] = {}
    if NAMING_MD.exists():
        for line in NAMING_MD.read_text(encoding="utf-8").splitlines():
            if re.match(r"^\| [a-z_]+\s*\|\s*[a-z]{2,3}\s*\|", line):
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 2:
                    abbr_to_domain[parts[1]] = parts[0]

    today = date.today().isoformat()
    updated = 0
    skipped = 0

    for abbr in abbrs:
        domain = abbr_to_domain.get(abbr, abbr)
        cluster = Path(f"docs/clusters/{domain}.md")

        # 해당 abbr 문서 수집 (archived·clusters 제외, WIP는 별도 수집)
        docs_list: list[Path] = []
        wip_list: list[Path] = []
        for md in sorted(DOCS_DIR.rglob("*.md")):
            parts_set = set(md.parts)
            if "archived" in parts_set or "clusters" in parts_set:
                continue
            if detect_abbr(md, abbrs) != abbr:
                continue
            if "WIP" in parts_set:
                wip_list.append(md)
            else:
                docs_list.append(md)

        def build_body(updated_value: str) -> str:
            lines = [
                "---",
                f"title: {domain} 클러스터",
                f"domain: {domain}",
                "tags: [cluster, index]",
                "status: completed",
                "created: 2026-04-16",
                f"updated: {updated_value}",
                "---",
                "",
                f"# {domain} 클러스터",
                "",
                f"도메인 {domain}({abbr}) 소속 문서 목록. docs-ops.py cluster-update 자동 생성.",
                "",
            ]
            if docs_list:
                lines.append("## 문서")
                lines.append("")
                for f in docs_list:
                    fm = extract_frontmatter(f)
                    title = fm.get("title") or f.name
                    rel = str(f).replace("\\", "/")
                    rel = rel.removeprefix("docs/")
                    lines.append(f"- [{title}](../{rel})")
            else:
                lines.append("_(문서 없음)_")
            if wip_list:
                lines.append("")
                lines.append("## 진행 중 (WIP)")
                lines.append("")
                for f in wip_list:
                    fm = extract_frontmatter(f)
                    title = fm.get("title") or f.name
                    rel = str(f).replace("\\", "/")
                    rel = rel.removeprefix("docs/")
                    lines.append(f"- [{title}](../{rel})")
            return "\n".join(lines) + "\n"

        # 결정적 비교: 기존 파일의 updated 값을 재사용해 본문 생성 → 동일하면 skip
        prev_updated = ""
        prev_text = ""
        if cluster.exists():
            prev_text = cluster.read_text(encoding="utf-8")
            m = re.search(r"^updated: (\S+)$", prev_text, re.MULTILINE)
            if m:
                prev_updated = m.group(1)

        candidate_with_prev = build_body(prev_updated) if prev_updated else ""
        if prev_text and candidate_with_prev == prev_text:
            skipped += 1
            continue

        cluster.write_text(build_body(today), encoding="utf-8")
        updated += 1

    print(f"clusters/ 갱신: {updated}개 파일 (skip {skipped}개)")
    return 0


# ─────────────────────────────────────────────────────────
# verify-relates
# ─────────────────────────────────────────────────────────

def _parse_relates_paths(path: Path) -> list[str]:
    """frontmatter의 relates-to.path 값 목록 추출."""
    fm_text = []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    dash = 0
    for line in lines:
        if line.strip() == "---":
            dash += 1
            if dash == 2:
                break
            continue
        if dash == 1:
            fm_text.append(line)

    paths: list[str] = []
    in_rt = False
    for line in fm_text:
        if re.match(r"^relates-to:\s*$", line):
            in_rt = True
            continue
        if in_rt and line and not line[0].isspace():
            in_rt = False
        if in_rt:
            m = re.match(r"^\s+-\s+path:\s*(.+)", line)
            if m:
                p = m.group(1).strip().strip("'\"")
                p = re.sub(r"\s*#.*$", "", p)
                if p:
                    paths.append(p)
    return paths


def cmd_verify_relates() -> int:
    errors = 0
    for md in sorted(DOCS_DIR.rglob("*.md")):
        rt_paths = _parse_relates_paths(md)
        for rp in rt_paths:
            if rp.startswith("/"):
                continue
            if rp.startswith(("../", "./")):
                resolved = resolve_path(str(md.parent).replace("\\", "/"), rp)
            else:
                resolved = f"docs/{rp}"
            rpath = resolved.split("#")[0]
            if not Path(rpath).exists():
                print(f"⚠️  {md}: relates-to '{rp}' (resolved: {rpath}) 존재하지 않음")
                errors += 1

    print(f"\n결과: 미연결 relates-to {errors} 건")
    return 1 if errors else 0


# ─────────────────────────────────────────────────────────
# wip-sync
# ─────────────────────────────────────────────────────────

def cmd_wip_sync(staged_files: list[str]) -> int:
    if not staged_files:
        print("사용법: docs-ops.py wip-sync <staged-file> [...]", file=sys.stderr)
        return 1

    wip_dir = Path("docs/WIP")
    if not wip_dir.exists():
        print("매칭 없음 (docs/WIP 없음)", file=sys.stderr)
        return 0

    today = date.today().isoformat()
    matched_wips = moved_wips = 0

    # abbr 기반 보조 매칭 준비
    abbrs = extract_abbrs()
    path_domain_map = extract_path_domain_map()
    # domain → abbr 역매핑 (naming.md 약어 표에서)
    domain_to_abbr: dict[str, str] = {}
    if NAMING_MD.exists():
        for line in NAMING_MD.read_text(encoding="utf-8").splitlines():
            if re.match(r"^\| [a-z_]+\s*\|\s*[a-z]{2,3}\s*\|", line):
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 2:
                    domain_to_abbr[parts[0]] = parts[1]

    # staged 파일들의 abbr 집합 (경로→도메인→abbr 변환)
    staged_abbrs: set[str] = set()
    if path_domain_map:
        for sf in staged_files:
            if not sf:
                continue
            domain = path_to_domain(sf, path_domain_map)
            if domain and domain in domain_to_abbr:
                staged_abbrs.add(domain_to_abbr[domain])

    # abbr → 해당 abbr을 가진 WIP 파일 목록 (복수 오탐 방지용)
    abbr_to_wips: dict[str, list[Path]] = {}
    if staged_abbrs:
        for wip in sorted(wip_dir.glob("*.md")):
            wip_abbr = detect_abbr(wip, abbrs)
            if wip_abbr and wip_abbr in staged_abbrs:
                abbr_to_wips.setdefault(wip_abbr, []).append(wip)

    # 의미 매칭 게이트 (2026-05-02 v0.30.7) — staged WIP의 problem 집합
    # 간접 매칭(body_referenced·abbr)에 적용. 어휘 일치를 의미 일치로 오인하는
    # false positive 차단 (`hn_session_test_results.md` 우선순위 2 사례).
    # 직접 체크박스 매칭(파일명 명시)은 작성자 의도 신호 강해 게이트 면제.
    staged_problems: set[str] = set()
    for sf in staged_files:
        if not sf:
            continue
        sf_path = Path(sf)
        if sf_path.exists() and sf.endswith(".md") and "WIP" in sf.replace("\\", "/"):
            fm = extract_frontmatter(sf_path)
            p = fm.get("problem", "").strip()
            if p:
                staged_problems.add(p)

    for wip in sorted(wip_dir.glob("*.md")):
        text = wip.read_text(encoding="utf-8")
        new_text = text
        file_matched = False
        body_referenced = False  # 본문에 staged 파일 언급 (Phase 3 — AC 전부 [x] 자동 이동 트리거)

        # frontmatter 구간 인덱스 계산 — 마킹 대상에서 제외
        # 자기증명 사례(2026-05-02): frontmatter `relates-to:` YAML 리스트가
        # `^\s*-\s` 정규식에 매칭돼 잘못된 ✅ 추가됨. 본문만 마킹 대상.
        _all_lines = text.splitlines()
        _fm_end = 0
        if _all_lines and _all_lines[0].strip() == "---":
            for _i, _l in enumerate(_all_lines[1:], start=1):
                if _l.strip() == "---":
                    _fm_end = _i + 1  # 닫는 --- 다음 줄부터 본문
                    break

        # 1차: 체크박스 라인 매칭 (정밀화 — 2026-05-02)
        # 이전 정규식 `^\s*([-*]|\d+\.)\s`는 모든 리스트 라인에 매칭돼
        # `## 사전 준비`의 "읽을 문서:" 줄에 false positive 다수 발생.
        # `^\s*[-*]\s+\[[ xX]\]\s` 로 좁혀 AC 체크박스만 대상.
        # splitlines()로 비교해 trailing newline 차이에 의한 오탐 방지
        for sf in staged_files:
            if not sf:
                continue
            sfbn = Path(sf).name
            _sf, _sfbn = sf, sfbn  # 루프 변수 클로저 캡처용 지역 변수

            # 본문 어딘가 언급되면 body_referenced=True (체크박스 추가 X 케이스 자동이동용)
            # 정밀화 (2026-05-02): frontmatter + 자연어 줄 false positive 방지를
            # 위해 **이미 [x] 마킹된 체크박스** 라인의 staged 파일 언급만 인정.
            # 자연어 설명(`## 사전 준비`의 "읽을 문서:")이나 `relates-to`는 자동
            # 이동 트리거로 부적절 — 의도된 시나리오는 "사용자가 미리 [x] 마킹한
            # 케이스"이므로 체크박스 라인 한정이 의미 정합.
            for _bl in _all_lines[_fm_end:]:
                if re.match(r"^\s*[-*]\s+\[[xX]\]\s", _bl) and (sf in _bl or sfbn in _bl):
                    body_referenced = True
                    break

            def _mark_line(line: str, _sf: str = _sf, _sfbn: str = _sfbn) -> str:
                if "✅" in line:
                    return line
                # 체크박스 라인 한정 — `- [ ]` 또는 `- [x]`/`- [X]`
                if re.match(r"^\s*[-*]\s+\[[ xX]\]\s", line):
                    if _sf in line or _sfbn in line:
                        return line.rstrip() + " ✅"
                return line

            orig_lines = new_text.splitlines()
            # frontmatter 구간은 _mark_line 적용 제외 — 그대로 보존
            marked_lines = orig_lines[:_fm_end] + [_mark_line(l) for l in orig_lines[_fm_end:]]
            if marked_lines != orig_lines:
                # trailing newline 보존
                new_text = "\n".join(marked_lines) + ("\n" if new_text.endswith("\n") else "")
                file_matched = True

        # 의미 게이트 — staged WIP의 problem과 일치할 때만 매칭 인정
        # 어휘 일치 ≠ 의미 일치 false positive 차단 (v0.30.6 자기증명 사례:
        # `hn_rule_skill_ssot.md` AC 본문 "commit/SKILL.md" 어휘 hit).
        wip_fm = extract_frontmatter(wip)
        wip_problem = wip_fm.get("problem", "").strip()

        def _passes_problem_gate() -> bool:
            # staged WIP에 problem이 하나도 없으면 게이트 skip (비-WIP 커밋)
            if not staged_problems:
                return True
            # 본 WIP가 직접 staged면 자기 자신이라 게이트 skip (작성자 직접 의도)
            try:
                if wip.resolve() in {Path(sf).resolve() for sf in staged_files if sf}:
                    return True
            except (OSError, ValueError):
                pass
            # 본 WIP의 problem이 staged 집합에 있으면 인정
            return wip_problem in staged_problems

        # 1차 직접 매칭 결과(file_matched)도 게이트 통과 의무
        if file_matched and not _passes_problem_gate():
            print(
                f"🛑 의미 게이트 차단 (직접 매칭): {wip} "
                f"(wip problem={wip_problem!r}, staged problems={sorted(staged_problems)})",
                file=sys.stderr,
            )
            file_matched = False
            new_text = text  # ✅ 추가 롤백

        # Phase 3 (2026-05-02): file_matched 안 됐어도 본문 언급 + AC 전부 [x]면 자동 이동
        # 사용자가 미리 [x] 마킹한 케이스 (이전 wip-sync는 ✅ 추가만 트리거)
        if not file_matched and body_referenced:
            if _passes_problem_gate():
                file_matched = True
            else:
                print(
                    f"🛑 의미 게이트 차단 (body_referenced): {wip} "
                    f"(wip problem={wip_problem!r}, staged problems={sorted(staged_problems)})",
                    file=sys.stderr,
                )

        # 2차: abbr 기반 보조 매칭 (체크리스트 없는 incidents 등)
        abbr_matched = False
        if not file_matched and staged_abbrs:
            wip_abbr = detect_abbr(wip, abbrs)
            if wip_abbr and wip_abbr in staged_abbrs:
                candidates = abbr_to_wips.get(wip_abbr, [])
                if len(candidates) > 1:
                    # 복수 WIP → 오탐 위험, skip
                    print(
                        f"⚠️  abbr '{wip_abbr}' WIP {len(candidates)}개 — 자동 매칭 skip"
                        f" (수동 확인 필요: {', '.join(str(c) for c in candidates)})",
                        file=sys.stderr,
                    )
                elif not _passes_problem_gate():
                    print(
                        f"🛑 의미 게이트 차단 (abbr): {wip} "
                        f"(wip problem={wip_problem!r}, staged problems={sorted(staged_problems)})",
                        file=sys.stderr,
                    )
                else:
                    abbr_matched = True
                    file_matched = True
                    print(f"🔗 abbr 매칭: {wip} ← staged abbr '{wip_abbr}'", file=sys.stderr)

        if not file_matched:
            continue

        if not abbr_matched:
            # 체크리스트 매칭 OR 본문 참조: 변경 있으면 갱신 후 미완료 항목 검사
            if new_text != text:
                wip.write_text(new_text, encoding="utf-8")
                write_frontmatter_field(wip, "updated", today)
                subprocess.run(["git", "add", str(wip)], capture_output=True)
                print(f"✅ 갱신: {wip}", file=sys.stderr)
            matched_wips += 1

            body_lines = []
            dash = 0
            for line in wip.read_text(encoding="utf-8").splitlines():
                if line.strip() == "---":
                    dash += 1
                    continue
                if dash >= 2:
                    body_lines.append(line)

            # 미완료 항목 = `- [ ]` 또는 `* [ ]` (빈 체크박스). ✅ 마킹된 리스트는 완료
            # Phase 3: 체크박스 패턴만 검사 — 일반 리스트 항목은 미완료 신호 아님
            pending = [l for l in body_lines
                       if re.match(r"^\s*([-*])\s+\[\s\]", l)
                       and "✅" not in l]
            if pending:
                continue
        else:
            # abbr 매칭: 체크리스트 없는 문서 → 직접 이동 시도
            matched_wips += 1

        print(f"🎉 모든 항목 완료 — 자동 이동 시도: {wip}", file=sys.stderr)
        r = subprocess.run(
            [sys.executable, __file__, "move", str(wip)],
            capture_output=True, text=True,
        )
        if r.returncode == 0:
            moved_wips += 1
            subprocess.run([sys.executable, __file__, "cluster-update"],
                           capture_output=True)
        else:
            print(f"⚠️  자동 이동 실패 — 수동 처리 필요: {wip}", file=sys.stderr)
            print(r.stderr, file=sys.stderr, end="")

    print(f"wip_sync_matched: {matched_wips}")
    print(f"wip_sync_moved: {moved_wips}")
    return 0


# ─────────────────────────────────────────────────────────
# 라우팅
# ─────────────────────────────────────────────────────────

USAGE = """\
사용법: docs-ops.py {validate|move|reopen|cluster-update|verify-relates|wip-sync} [args]

서브커맨드:
  validate                     프론트매터·약어 검증
  move <wip-file>              WIP 접두사로 대상 폴더 이동 + status=completed
  reopen <completed-file>      완료 문서를 WIP로 되돌림 + status=in-progress
  cluster-update               모든 clusters/*.md 재생성
  verify-relates               relates-to.path 정합성 전수 검사
  wip-sync <file> [...]        commit Step 7.5 — staged 파일 체크리스트 ✅ 갱신
"""

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(USAGE, file=sys.stderr)
        sys.exit(1)

    cmd = args[0]
    rest = args[1:]

    dispatch = {
        "validate":       lambda: cmd_validate(),
        "move":           lambda: cmd_move(rest[0] if rest else ""),
        "reopen":         lambda: cmd_reopen(rest[0] if rest else ""),
        "cluster-update": lambda: cmd_cluster_update(),
        "verify-relates": lambda: cmd_verify_relates(),
        "wip-sync":       lambda: cmd_wip_sync(rest),
    }

    if cmd not in dispatch:
        print(USAGE, file=sys.stderr)
        sys.exit(1)

    sys.exit(dispatch[cmd]())
