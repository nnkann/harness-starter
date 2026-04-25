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
    return subprocess.run(["git"] + args, capture_output=True, text=True)


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

# 단어 경계로 TODO/FIXME 매칭 (todo_fixme 같은 복합어 오탐 방지)
BLOCK_KEYWORDS = re.compile(r"\b(TODO|FIXME)\b", re.IGNORECASE)
BLOCK_HEADERS = re.compile(
    r"^\s*##\s*(후속|미결|미결정|추후|나중에|별도로)", re.MULTILINE
)
BLOCK_ITEMS = re.compile(
    r"^\s*[-*0-9.]+\s.*(후속|미결|미결정|추후|나중에|별도로).*$", re.MULTILINE
)
DONE_PAT = re.compile(r"✅|완료|처리됨|done", re.IGNORECASE)
RESULT_SECTION = re.compile(r"^## (처리 결과|원본|회고|처리|결과)", re.MULTILINE)


def _extract_body(text: str) -> str:
    """프론트매터 제거 + '처리 결과' 섹션 이후 skip."""
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
    body_lines, skip = [], False
    for line in lines[i:]:
        if RESULT_SECTION.match(line):
            skip = True
        if not skip:
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

    # 차단 검사
    hits = [l for l in BLOCK_KEYWORDS.findall(body) if not DONE_PAT.search(l)]
    header_hits = BLOCK_HEADERS.findall(body)
    item_hits   = [l for l in BLOCK_ITEMS.findall(body) if not DONE_PAT.search(l)]

    # 라인 단위로 재검사 (정확도)
    todo_lines = [l for l in body.splitlines()
                  if BLOCK_KEYWORDS.search(l) and not DONE_PAT.search(l)
                  and not re.search(r"todo_fixme|todo/fixme", l, re.I)]
    header_lines = [l for l in body.splitlines() if BLOCK_HEADERS.match(l)]
    item_lines   = [l for l in body.splitlines()
                    if re.match(r"^\s*[-*0-9.]+\s.*(후속|미결|미결정|추후|나중에|별도로)", l)
                    and not DONE_PAT.search(l)]

    if todo_lines or header_lines or item_lines:
        print(f"🚫 completed 전환 차단: {src} 본문에 미결 패턴 존재", file=sys.stderr)
        for l in todo_lines:   print(f"   TODO: {l}", file=sys.stderr)
        for l in header_lines: print(f"   HEADER: {l}", file=sys.stderr)
        for l in item_lines:   print(f"   ITEM: {l}", file=sys.stderr)
        print("   대응: (a) 잔여를 별도 WIP로 분리 (b) 본문에서 키워드 제거 후 재시도",
              file=sys.stderr)
        return 2

    dest = Path(f"docs/{prefix}/{rest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    git(["mv", str(src), str(dest)])

    today = date.today().isoformat()
    write_frontmatter_field(dest, "status", "completed")
    write_frontmatter_field(dest, "updated", today)

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

    for abbr in abbrs:
        domain = abbr_to_domain.get(abbr, abbr)
        cluster = Path(f"docs/clusters/{domain}.md")

        # 해당 abbr 문서 수집 (WIP·archived·clusters 제외)
        docs_list: list[Path] = []
        for md in sorted(DOCS_DIR.rglob("*.md")):
            parts_set = set(md.parts)
            if "WIP" in parts_set or "archived" in parts_set or "clusters" in parts_set:
                continue
            if detect_abbr(md, abbrs) == abbr:
                docs_list.append(md)

        lines = [
            "---",
            f"title: {domain} 클러스터",
            f"domain: {domain}",
            "tags: [cluster, index]",
            "status: completed",
            "created: 2026-04-16",
            f"updated: {today}",
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

        cluster.write_text("\n".join(lines) + "\n", encoding="utf-8")
        updated += 1

    print(f"clusters/ 갱신: {updated}개 파일")
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

    for wip in sorted(wip_dir.glob("*.md")):
        text = wip.read_text(encoding="utf-8")
        new_text = text
        file_matched = False

        for sf in staged_files:
            if not sf:
                continue
            sfbn = Path(sf).name

            def _mark_line(line: str) -> str:
                if "✅" in line:
                    return line
                if re.match(r"^\s*([-*]|\d+\.)\s", line):
                    if sf in line or sfbn in line:
                        return line.rstrip() + " ✅"
                return line

            marked = "\n".join(_mark_line(l) for l in new_text.splitlines())
            if marked != new_text:
                new_text = marked
                file_matched = True

        if not file_matched:
            continue

        wip.write_text(new_text, encoding="utf-8")
        write_frontmatter_field(wip, "updated", today)
        subprocess.run(["git", "add", str(wip)], capture_output=True)
        matched_wips += 1
        print(f"✅ 갱신: {wip}", file=sys.stderr)

        # 전부 완료 여부
        body_lines = []
        dash = 0
        for line in wip.read_text(encoding="utf-8").splitlines():
            if line.strip() == "---":
                dash += 1
                continue
            if dash >= 2:
                body_lines.append(line)

        pending = [l for l in body_lines
                   if re.match(r"^\s*([-*]|\d+\.)\s", l) and "✅" not in l
                   and l.strip()]
        if not pending:
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
