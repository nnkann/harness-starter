#!/usr/bin/env python3
"""
eval --harness CPS 무결성 감시.

docs/ 하위 모든 .md 파일의 frontmatter solution-ref 인용을 CPS 본문과
대조해 박제 의심 보고. Problem 인플레이션(6개 초과) 경고.

출력:
  stdout: 박제 의심 path:line + 인용 vs CPS 본문 미매칭 사유
  exit 0: 보고 완료 (박제 0건이어도 0)
  exit 2: 형식 위반·CPS 본문 Read 실패 (eval이 사용자에게 노출)

재사용: pre_commit_check.py의 verify_solution_ref·parse_frontmatter·
get_cps_text. 코드 중복 X.
"""

import importlib.util
import re
import sys
from pathlib import Path

# pre_commit_check.py 동적 import (모듈명 - 포함 → 직접 import 불가)
_PCC = Path(__file__).parent / "pre_commit_check.py"
_spec = importlib.util.spec_from_file_location("pre_commit_check", _PCC)
_pcc = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_pcc)                  # type: ignore[union-attr]

parse_frontmatter   = _pcc.parse_frontmatter
get_cps_text        = _pcc.get_cps_text
verify_solution_ref = _pcc.verify_solution_ref
CPS_DOC             = _pcc.CPS_DOC


def extract_cps_solution_ids(cps_text: str) -> list[str]:
    """CPS 본문에서 S# Solution ID 목록을 순서대로 추출.
    "### S1 ..." 헤더 패턴 및 "**S1**" 굵은 글씨 패턴 모두 지원.
    """
    ids = re.findall(r"(?:###\s+|\*\*)(S\d+)\b", cps_text)
    # 순서 유지 + 중복 제거
    seen: set[str] = set()
    result = []
    for sid in ids:
        if sid not in seen:
            seen.add(sid)
            result.append(sid)
    return result


def count_solution_refs(docs_root: Path) -> dict[str, int]:
    """docs/ 하위 모든 .md 파일의 frontmatter solution-ref에서 S# 카운트.
    parse_frontmatter는 YAML 리스트 항목의 `- ` 마크를 제거해 반환.
    따라서 각 항목은 "S2 — ..." 형식 (앞 하이픈 없음).
    Returns: {S1: 3, S2: 12, ...}
    """
    pat = re.compile(r"^S(\d+)\b")
    counts: dict[str, int] = {}
    for md in sorted(docs_root.rglob("*.md")):
        try:
            text = md.read_text(encoding="utf-8")
        except Exception:
            continue
        fm, _ = parse_frontmatter(text)
        sol_refs = fm.get("solution-ref", [])
        if not sol_refs:
            continue
        if isinstance(sol_refs, str):
            sol_refs = [sol_refs]
        for ref in sol_refs:
            m = pat.match(str(ref).strip())
            if m:
                sid = f"S{m.group(1)}"
                counts[sid] = counts.get(sid, 0) + 1
    return counts


def count_cps_problems(cps_text_normalized: str) -> int:
    """CPS 본문에서 P# 패턴 고유 개수 카운트.
    normalize_quote 후라 줄바꿈은 공백. P1·P2... 패턴 grep.
    """
    ids = set(re.findall(r"\bP(\d+)\b", cps_text_normalized))
    return len(ids)


# CPS 의미의 P# 인용 패턴 (본문 grep용 — 자체 우선순위 라벨과 disambiguation)
#
# 활용 사례 (2026-05-02 본문 grep 분석):
#   "CPS 연결: P1(LLM 추측 수정)·P2(review 과잉 비용)" — CPS 인용 (잡힘)
#   "P6 → S6 해결 기준 충족" — CPS 인용 (잡힘)
#   "**P3**: 3 (스킬 질의)" — 자체 우선순위 라벨 (자연스럽게 제외)
#   "### P3. write-doc 확장" — 자체 라벨 (자연스럽게 제외)
#
# 포지티브 매칭만 사용 — CPS 의미 신호가 있는 패턴만 잡고, 자체 라벨은
# 매칭 안 되므로 제외 패턴 불필요. 본 starter 실측에서 false positive 0건.
CPS_REF_PATTERNS = [
    re.compile(r"CPS\s*연결[:\s]*[^\n]*?\b(P\d)\b"),       # "CPS 연결: P1·P2"
    re.compile(r"\b(P\d)\s*\([^)]*?(?:추측|review|다운스트림|매처|컨텍스트|검증|LLM|hook|MCP)[^)]*?\)"),  # "P1(LLM 추측...)"
    re.compile(r"\b(P\d)\s*→\s*S\d"),                       # "P6 → S6"
    re.compile(r"\b(P\d)\s*(?:충족|재발|연관|해결)"),         # "P6 충족"
]


def detect_cps_problem_refs(body: str) -> set[str]:
    """본문에서 CPS 의미의 P# 인용을 추출 (포지티브 매칭만).
    문서당 한 Problem은 1번만 카운트 (set 반환).
    """
    refs: set[str] = set()
    for pat in CPS_REF_PATTERNS:
        for m in pat.finditer(body):
            refs.add(m.group(1))
    return refs


def scan_doc(path: Path, cps_text: str, problem_refs: dict) -> list[str]:
    """단일 문서 frontmatter + 본문 검사.
    - solution-ref 박제 grep
    - problem 카운트 누적 (frontmatter + 본문 인용, 문서당 Problem 1회)
    path:warning 형식 list 반환.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        return [f"{path}: read 실패 ({e})"]

    fm, body_start = parse_frontmatter(text)
    body = "\n".join(text.splitlines()[body_start:])

    # 문서별 hit set — frontmatter + 본문 합쳐 중복 제거
    doc_refs: set[str] = set()

    # 1. frontmatter problem 인용
    prob = fm.get("problem", "")
    if isinstance(prob, str) and re.match(r"^P\d+$", prob.strip()):
        doc_refs.add(prob.strip())

    # 2. 본문 CPS 인용 (자체 라벨 제외)
    doc_refs.update(detect_cps_problem_refs(body))

    # 누적
    for pid in doc_refs:
        problem_refs.setdefault(pid, 0)
        problem_refs[pid] += 1

    sol_refs = fm.get("solution-ref", [])
    if not sol_refs:
        return []
    if isinstance(sol_refs, str):
        sol_refs = [sol_refs]

    warnings = verify_solution_ref(sol_refs, cps_text)
    return [f"{path}: {w}" for w in warnings]


def main() -> int:
    cps_text = get_cps_text()
    if not cps_text:
        print(f"❌ CPS 본문 Read 실패: {CPS_DOC}", file=sys.stderr)
        return 2

    docs_root = Path("docs")
    if not docs_root.is_dir():
        print(f"❌ docs/ 디렉토리 없음", file=sys.stderr)
        return 2

    problem_count = count_cps_problems(cps_text)
    solution_ids = extract_cps_solution_ids(cps_text)
    # 인플레이션 임계값: CPS Problem 수 기반 동적 계산 (고정 6 폐기)
    # 기준: Problem 수 + 2 (소규모 추가 여유), 최소 8
    inflation_threshold = max(8, problem_count + 2)

    all_warnings: list[str] = []
    problem_refs: dict = {}  # P# → 인용 문서 수 (진전 신호 proxy)
    scanned = 0
    for md in sorted(docs_root.rglob("*.md")):
        md_posix = str(md).replace("\\", "/")
        if md_posix == CPS_DOC:
            continue
        # docs/harness/ 는 upstream CPS를 참조하는 하네스 자체 문서 — 다운스트림 CPS와 대조 시 항상 오탐
        if md_posix.startswith("docs/harness/") or "/docs/harness/" in md_posix:
            continue
        scanned += 1
        all_warnings.extend(scan_doc(md, cps_text, problem_refs))

    solution_counts = count_solution_refs(docs_root)

    # BIT NEW 플래그 미처리 집계
    # docs/WIP/ + docs/decisions/ 파일에서 "P#: NEW" 패턴 grep
    new_flag_pat = re.compile(r"P#:\s*NEW\b")
    new_flag_items: list[str] = []
    for search_dir in [docs_root / "WIP", docs_root / "decisions"]:
        if not search_dir.is_dir():
            continue
        for md in sorted(search_dir.glob("*.md")):
            try:
                text = md.read_text(encoding="utf-8")
            except Exception:
                continue
            for line in text.splitlines():
                if new_flag_pat.search(line):
                    new_flag_items.append(f"  - {md.name}: {line.strip()}")

    print(f"## CPS 무결성 감시")
    print(f"")
    print(f"- 스캔 문서: {scanned}개")
    print(f"- CPS Problem 수: {problem_count}개")
    if problem_count > inflation_threshold:
        print(f"  ⚠ Problem 인플레이션 의심 — {problem_count} > {inflation_threshold} (동적 임계값). "
              f"근접 Problem 병합 검토 권고")
    print(f"- 박제 의심: {len(all_warnings)}건")
    if new_flag_items:
        print(f"- NEW 플래그 미처리: {len(new_flag_items)}건 ⚠")
        for item in new_flag_items:
            print(item)
        print(f"  → implementation Step 0에서 CPS P# 매칭 필요")
    else:
        print(f"- NEW 플래그 미처리: 0건 ✅")

    if all_warnings:
        print(f"")
        print(f"### 박제 의심 상세")
        for w in all_warnings:
            print(f"- {w}")

    # Problem 진전 신호 — 인용 문서 수 (eval --deep 활용)
    if problem_refs:
        print(f"")
        print(f"### Problem 인용 빈도 (진전 신호 proxy)")
        for pid in sorted(problem_refs, key=lambda x: int(x[1:])):
            print(f"- {pid}: {problem_refs[pid]}건")
        unreferenced = []
        for i in range(1, problem_count + 1):
            pid = f"P{i}"
            if pid not in problem_refs:
                unreferenced.append(pid)
        if unreferenced:
            print(f"")
            print(f"⚠ 인용 0건 Problem (정체 의심): {', '.join(unreferenced)}")
            print(f"  6개월 이상 인용 0이면 Problem 폐기 또는 병합 검토 권고")

    # Solution 충족 인용 분포
    if solution_ids:
        print(f"")
        print(f"### Solution 충족 인용 분포")
        zero_solutions = []
        for sid in solution_ids:
            count = solution_counts.get(sid, 0)
            if count == 0:
                print(f"- {sid}: 0건 ⚠")
                zero_solutions.append(sid)
            else:
                print(f"- {sid}: {count}건")
        if zero_solutions:
            print(f"")
            print(f"  인용 0건 Solution: {', '.join(zero_solutions)}")
            print(f"  (미충족 의심 — 최근 등록·구현 전·문서화 지연 등 맥락 확인 필요. 사람 판단)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
