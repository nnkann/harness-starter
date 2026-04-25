#!/usr/bin/env python3
"""
task-groups.sh Python 재작성.

staged 파일을 task × abbr × kind 3축으로 그룹화 (audit #18).

그룹 키 형식:
  wip:<slug>:<abbr>:<kind>
  path:기타:<abbr>:<kind>   — WIP 매칭 실패 폴백
  meta:config               — 메타 파일 (흡수 대상)

출력 (stdout, tab-separated):
  group_name<TAB>file_path
"""

import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

NAMING_MD = Path(".claude/rules/naming.md")

META_PATTERNS = re.compile(
    r"^(\.claude/HARNESS\.json"
    r"|docs/harness/MIGRATIONS\.md"
    r"|README\.md"
    r"|CHANGELOG\.md"
    r"|docs/clusters/.*\.md)$"
)


# ─────────────────────────────────────────────────────────
# 유틸
# ─────────────────────────────────────────────────────────

def run(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def extract_abbrs() -> list[str]:
    if not NAMING_MD.exists():
        return []
    text = NAMING_MD.read_text(encoding="utf-8")
    in_section = False
    abbrs: set[str] = set()
    for line in text.splitlines():
        if re.match(r"^## 도메인 약어", line):
            in_section = True; continue
        if in_section and line.startswith("## "):
            break
        if in_section and re.match(r"^\| [a-z_]+\s*\|\s*[a-z]{2,3}\s*\|", line):
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 2:
                abbrs.add(parts[1])
    return sorted(abbrs)


def detect_abbr(path: str, abbr_pat: re.Pattern | None) -> str:
    name = Path(path).stem
    if "--" in name:
        name = name.split("--", 1)[1]
    if abbr_pat:
        m = abbr_pat.search(name)
        if m:
            return m.group(1)
    return "no-abbr"


# ─────────────────────────────────────────────────────────
# WIP 본문 파싱 → {pattern → (slug, kind)}
# ─────────────────────────────────────────────────────────

def parse_wip_impact() -> list[tuple[str, str, str, str]]:
    """WIP 파일에서 (slug, task_id, kind, file_pattern) 튜플 목록 반환."""
    results: list[tuple[str, str, str, str]] = []
    wip_dir = Path("docs/WIP")
    if not wip_dir.exists():
        return results

    for wip_file in sorted(wip_dir.glob("*.md")):
        slug = wip_file.stem
        if "--" in slug:
            slug = slug.split("--", 1)[1]

        text = wip_file.read_text(encoding="utf-8", errors="ignore")
        in_block = False
        task_id = ""
        kind = "feature"
        explicit_kind = False
        in_impact = False
        scan_lines = 0

        for line in text.splitlines():
            # 태스크 블록 헤더
            m = re.match(r"^### #?(\d[\d·]*)\.", line)
            if m:
                in_block = True
                task_id = m.group(1).replace("·", "-")
                kind = "feature"
                explicit_kind = False
                in_impact = False
                scan_lines = 0
                # 헤더 텍스트에서 kind 힌트
                if re.search(r"근본 수정|버그|오탐|fix:|hotfix", line, re.I):
                    kind = "bug"
                continue

            # 다른 헤더 → 블록 종료
            if re.match(r"^### ", line) and in_block:
                in_block = False; in_impact = False; continue
            if line.strip() == "---" and in_block:
                in_block = False; in_impact = False; continue

            if not in_block:
                continue

            # kind 마커
            if not explicit_kind:
                km = re.match(r"^>\s*kind:\s*([a-z]+)", line)
                if km:
                    kind = km.group(1); explicit_kind = True; continue
                if kind == "feature" and scan_lines < 5 and line.strip():
                    if re.search(r"근본 수정|버그|오탐|fix:|hotfix|회귀", line, re.I):
                        kind = "bug"
                    scan_lines += 1

            # 영향 파일 섹션
            if "**영향 파일**" in line:
                in_impact = True
            if in_impact:
                for m in re.finditer(r"`([^`]+)`", line):
                    p = m.group(1)
                    if "/" in p or "." in p:
                        if not re.match(r"^(--|Step)", p):
                            results.append((slug, task_id, kind, p))
                if line.strip() == "" or (re.match(r"^\*\*[^영]", line)):
                    in_impact = False

    return results


# ─────────────────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────────────────

def main() -> int:
    # staged 파일 + rename 감지
    name_status_raw = run(["git", "diff", "--cached", "--name-status", "-M25"])
    if not name_status_raw.strip():
        return 0

    # (status, path) 파싱 + rename map 구축
    rename_map: dict[str, str] = {}   # old → new
    staged_paths: list[str] = []

    for line in name_status_raw.splitlines():
        parts = line.split("\t")
        if not parts:
            continue
        status = parts[0]
        if re.match(r"^R\d+$", status) and len(parts) >= 3:
            old, new = parts[1], parts[2]
            rename_map[old] = new
            staged_paths.extend([old, new])
        elif len(parts) >= 2:
            staged_paths.append(parts[1])

    # WIP 이동 휴리스틱 (git rename 미감지 보완)
    deleted_wip: dict[str, str] = {}  # "folder/base.md" → old_path
    added_docs: dict[str, str] = {}   # "folder/base.md" → new_path

    for line in name_status_raw.splitlines():
        parts = line.split("\t")
        if not parts or len(parts) < 2:
            continue
        status, path = parts[0], parts[1]
        if status == "D" and path.startswith("docs/WIP/"):
            bn = Path(path).name
            m = re.match(r"^([a-z]+)--(.+\.md)$", bn)
            if m:
                key = f"{m.group(1)}/{m.group(2)}"
                deleted_wip[key] = path
        elif status == "A" and path.startswith("docs/") and not path.startswith("docs/WIP/"):
            rel = path[len("docs/"):]
            if rel in deleted_wip:
                old = deleted_wip[rel]
                if old not in rename_map:
                    rename_map[old] = path

    # abbr 패턴
    abbrs = extract_abbrs()
    abbr_pat: re.Pattern | None = None
    if abbrs:
        pat = "|".join(re.escape(a) for a in abbrs)
        abbr_pat = re.compile(rf"(?:^|[_-])({pat})_")

    # WIP impact map
    impact = parse_wip_impact()  # [(slug, task_id, kind, pattern)]

    def match_wip(f: str) -> tuple[str, str] | None:
        """파일 f → (slug, kind) 매칭. 실패 시 None."""
        fbn = Path(f).name
        best: tuple[str, str] | None = None
        for slug, _, kind, pattern in impact:
            pbn = Path(pattern).name
            if f == pattern or f.endswith("/" + pattern):
                return (slug, kind)
            if fbn == pbn and best is None:
                best = (slug, kind)
        return best

    # 그룹 할당
    assignments: list[tuple[str, str]] = []  # (group_key, file_path)

    for f in staged_paths:
        judge = rename_map.get(f, f)
        abbr = detect_abbr(judge, abbr_pat)

        # 1. 메타 파일
        if META_PATTERNS.match(judge):
            assignments.append(("meta:config", f))
            continue

        # 2. WIP 파일 자체
        if judge.startswith("docs/WIP/") and judge.endswith(".md"):
            slug = Path(judge).stem
            if "--" in slug:
                slug = slug.split("--", 1)[1]
            assignments.append((f"wip:{slug}:{abbr}:feature", f))
            continue

        # 3. task 매칭
        match = match_wip(judge)
        if match:
            slug, kind = match
            assignments.append((f"wip:{slug}:{abbr}:{kind}", f))
            continue

        # 4. 폴백
        assignments.append((f"path:기타:{abbr}:feature", f))

    # 메타 흡수: meta:config → 가장 큰 non-meta 그룹
    group_sizes: dict[str, int] = defaultdict(int)
    for key, _ in assignments:
        if key != "meta:config":
            group_sizes[key] += 1

    largest = max(group_sizes, key=lambda k: group_sizes[k]) if group_sizes else ""

    for key, f in assignments:
        if key == "meta:config" and largest:
            print(f"{largest}\t{f}")
        else:
            print(f"{key}\t{f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
