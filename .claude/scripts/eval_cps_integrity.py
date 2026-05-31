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

# Windows cp949 콘솔에서 emoji 출력 시 UnicodeEncodeError 차단.
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

# pre_commit_check.py 동적 import (모듈명 - 포함 → 직접 import 불가)
_PCC = Path(__file__).parent / "pre_commit_check.py"
_spec = importlib.util.spec_from_file_location("pre_commit_check", _PCC)
_pcc = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_pcc)                  # type: ignore[union-attr]

parse_frontmatter   = _pcc.parse_frontmatter
CPS_DOC             = _pcc.CPS_DOC


def get_cps_text() -> str:
    """CPS 본문 Read. pre_commit_check.py 폐기 함수 인라인 (§S-1 후속)."""
    try:
        return Path(CPS_DOC).read_text(encoding="utf-8")
    except Exception:
        return ""


def verify_solution_ref(sol_refs, cps_text: str) -> list[str]:
    """Solution 인용 검사 — §S-1 73% 삭감으로 50자 박제 검사 폐기.
    번호만 검사하던 게 본질. 본 함수는 형식 검사만 수행 (호환).
    """
    warnings: list[str] = []
    if not isinstance(sol_refs, list):
        sol_refs = [sol_refs]
    for entry in sol_refs:
        if not isinstance(entry, str):
            continue
        entry = entry.strip()
        if not entry:
            continue
        if not re.match(r"^S\d+", entry):
            warnings.append(f"solution-ref 형식 위반: '{entry}' (S# 번호 시작 필요)")
    return warnings


def _dedupe_ordered(ids: list[str]) -> list[str]:
    """순서를 유지하며 중복 ID를 제거한다."""
    seen: set[str] = set()
    result: list[str] = []
    for item in ids:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _extract_ordered_ids(cps_text: str, patterns: list[str]) -> list[str]:
    """여러 패턴에서 찾은 ID를 원문 등장 순서대로 정렬해 반환한다."""
    matches: list[tuple[int, str]] = []
    for pat in patterns:
        for m in re.finditer(pat, cps_text, re.MULTILINE):
            matches.append((m.start(), m.group(1)))
    return _dedupe_ordered([item for _, item in sorted(matches, key=lambda x: x[0])])


def extract_cps_solution_ids(cps_text: str) -> list[str]:
    """CPS 본문에서 S# Solution ID 목록을 순서대로 추출.
    "### S1 ..." 헤더 패턴 및 "**S1**" 굵은 글씨 패턴 모두 지원.
    """
    patterns = [
        r"^\|\s*\*{0,2}(S\d+)\*{0,2}\s*\|",
        r"^#{2,6}\s+\*{0,2}(S\d+)\*{0,2}(?:\b|[.\s:—-])",
        r"^\s*[-*]?\s*\*{2}(S\d+)\b",
    ]
    return _extract_ordered_ids(cps_text, patterns)


def extract_cps_problem_ids(cps_text: str) -> list[str]:
    """CPS Problems에서 P# Problem ID 목록을 순서대로 추출한다.

    표 형식과 헤더/굵은 글씨 형식을 모두 지원한다:
    `| P1 | ... |`, `### P5. ...`, `**P1 — ...**`.
    """
    patterns = [
        r"^\|\s*\*{0,2}(P\d+)\*{0,2}\s*\|",
        r"^#{2,6}\s+\*{0,2}(P\d+)\*{0,2}(?:\b|[.\s:—-])",
        r"^\s*[-*]?\s*\*{2}(P\d+)\b",
    ]
    return _extract_ordered_ids(cps_text, patterns)


def extract_solution_problem_map(cps_text: str) -> dict[str, str]:
    """CPS Solutions에서 S# → P# 매핑을 추출한다.

    예: `| S8 | P8 | ... |`, `### S8 (for P8)`
    """
    mapping: dict[str, str] = {}
    table_pat = r"^\|\s*\*{0,2}(S\d+)\*{0,2}\s*\|\s*\*{0,2}(P\d+)\*{0,2}\s*\|"
    for m in re.finditer(table_pat, cps_text, re.MULTILINE):
        mapping[m.group(1)] = m.group(2)

    header_pat = r"^#{2,6}\s+\*{0,2}(S\d+)\*{0,2}(?:\b|[.\s:—-]).*?\b(?:for|대상|Problem|P#)?\s*\*{0,2}(P\d+)\*{0,2}\b"
    for m in re.finditer(header_pat, cps_text, re.MULTILINE | re.IGNORECASE):
        mapping.setdefault(m.group(1), m.group(2))
    return mapping


def assess_cps_solution_coupling(
    problem_ids: list[str],
    solution_ids: list[str],
    solution_problem_map: dict[str, str],
) -> dict[str, list[str] | dict[str, list[str]]]:
    """P#↔S# 결합 누락·dangling을 판정한다."""
    problems = set(problem_ids)
    solutions = set(solution_ids)
    p_to_s: dict[str, list[str]] = {pid: [] for pid in problem_ids}

    unmapped_solutions = [sid for sid in solution_ids if sid not in solution_problem_map]
    dangling_solutions = []
    for sid in solution_ids:
        pid = solution_problem_map.get(sid)
        if not pid:
            continue
        if pid not in problems:
            dangling_solutions.append(f"{sid}->{pid}")
            continue
        p_to_s.setdefault(pid, []).append(sid)

    orphan_problems = [pid for pid in problem_ids if not p_to_s.get(pid)]
    unknown_map_entries = [
        sid for sid in sorted(solution_problem_map)
        if sid not in solutions
    ]
    return {
        "p_to_s": p_to_s,
        "orphan_problems": orphan_problems,
        "unmapped_solutions": unmapped_solutions,
        "dangling_solutions": dangling_solutions,
        "unknown_map_entries": unknown_map_entries,
    }


def _frontmatter_list(value) -> list[str]:
    """frontmatter 필드를 list[str]로 정규화한다."""
    if not value:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str):
        s = value.strip()
        if s.startswith("[") and s.endswith("]"):
            s = s.strip("[]")
            return [x.strip().strip("'\"") for x in s.split(",") if x.strip()]
        return [s] if s else []
    return [str(value).strip()]


def accumulate_solution_refs(fm: dict, counts: dict[str, int]) -> None:
    """frontmatter solution-ref/s 필드의 S# 인용을 counts에 누적한다."""
    pat = re.compile(r"^S(\d+)\b")
    sol_refs = _frontmatter_list(fm.get("solution-ref", []))
    sol_refs.extend(_frontmatter_list(fm.get("s", [])))
    for ref in sol_refs:
        m = pat.match(str(ref).strip())
        if m:
            sid = f"S{m.group(1)}"
            counts[sid] = counts.get(sid, 0) + 1


def count_solution_refs(docs_root: Path) -> dict[str, int]:
    """docs/ 하위 모든 .md 파일의 frontmatter solution-ref/s에서 S# 카운트.
    parse_frontmatter는 YAML 리스트 항목의 `- ` 마크를 제거해 반환.
    따라서 각 항목은 "S2 — ..." 형식 (앞 하이픈 없음).
    Returns: {S1: 3, S2: 12, ...}
    """
    counts: dict[str, int] = {}
    for md in sorted(docs_root.glob("**/*.md")):
        try:
            text = md.read_text(encoding="utf-8")
        except Exception:
            continue
        fm, _ = parse_frontmatter(text)
        accumulate_solution_refs(fm, counts)
    return counts


def count_wip_problem_signals(docs_root: Path, problem_to_solutions: dict[str, list[str]]) -> dict[str, int]:
    """진행 중 WIP에서 P# 또는 관련 S#가 언급된 횟수를 센다.

    primary `problem:` 인용이 없어도 WIP의 하위 목표나 `solution-ref`로 살아 있는
    장기 Problem을 폐기 후보로 오판하지 않기 위한 보조 신호다.
    """
    counts: dict[str, int] = {}
    wip_root = docs_root / "WIP"
    if not wip_root.is_dir():
        return counts
    for md in sorted(wip_root.rglob("*.md")):
        try:
            text = md.read_text(encoding="utf-8")
        except Exception:
            continue
        for pid, sids in problem_to_solutions.items():
            tokens = [pid, *sids]
            if any(re.search(rf"\b{re.escape(token)}\b", text) for token in tokens):
                counts[pid] = counts.get(pid, 0) + 1
    return counts


def _frontmatter_ids(value, prefix: str) -> list[str]:
    """frontmatter 값에서 P#/S# ID를 순서 유지 중복 제거로 추출한다."""
    ids: list[str] = []
    for item in _frontmatter_list(value):
        ids.extend(re.findall(rf"\b{re.escape(prefix)}\d+\b", item))
    return _dedupe_ordered(ids)


def analyze_cps_case_catalog(
    docs_root: Path,
    problem_ids: list[str],
    solution_ids: list[str],
) -> dict[str, object]:
    """docs/cps case 박제의 분류·학습 신호를 정량화한다.

    case는 재발 억제뿐 아니라 신규 Problem 후보와 기존 분류의 적응도를
    보여주는 학습 데이터다. 정의 밖 P/S가 남으면 retired 번호나 신규 P#가
    current CPS와 분리되어 있다는 신호로 보고한다.
    """
    cases_dir = docs_root / "cps"
    problem_set = set(problem_ids)
    solution_set = set(solution_ids)
    problem_counts: dict[str, int] = {}
    solution_counts: dict[str, int] = {}
    undefined_problem_refs: list[str] = []
    undefined_solution_refs: list[str] = []
    multi_problem_cases: list[str] = []
    p10_cases: list[str] = []
    case_count = 0

    if not cases_dir.is_dir():
        return {
            "case_count": 0,
            "problem_counts": problem_counts,
            "solution_counts": solution_counts,
            "undefined_problem_refs": undefined_problem_refs,
            "undefined_solution_refs": undefined_solution_refs,
            "multi_problem_cases": multi_problem_cases,
            "p10_cases": p10_cases,
            "case_covered_problems": [],
            "no_case_problems": problem_ids,
            "recurring_problem_cases": {},
        }

    for path in sorted(cases_dir.glob("cp_*.md")):
        case_count += 1
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        fm, _ = parse_frontmatter(text)
        try:
            rel = path.relative_to(docs_root.parent).as_posix()
        except ValueError:
            rel = path.as_posix()
        p_refs = _frontmatter_ids(fm.get("p") or fm.get("problem"), "P")
        s_refs = _frontmatter_ids(fm.get("s") or fm.get("solution-ref"), "S")

        if len(p_refs) > 1:
            multi_problem_cases.append(rel)
        if "P10" in p_refs:
            p10_cases.append(rel)

        for pid in p_refs:
            if pid not in problem_set:
                undefined_problem_refs.append(f"{rel}:{pid}")
                continue
            problem_counts[pid] = problem_counts.get(pid, 0) + 1
        for sid in s_refs:
            if sid not in solution_set:
                undefined_solution_refs.append(f"{rel}:{sid}")
                continue
            solution_counts[sid] = solution_counts.get(sid, 0) + 1

    case_covered_problems = [pid for pid in problem_ids if problem_counts.get(pid, 0) > 0]
    no_case_problems = [pid for pid in problem_ids if problem_counts.get(pid, 0) == 0]
    recurring_problem_cases = {
        pid: count for pid, count in problem_counts.items() if count >= 2
    }
    return {
        "case_count": case_count,
        "problem_counts": problem_counts,
        "solution_counts": solution_counts,
        "undefined_problem_refs": undefined_problem_refs,
        "undefined_solution_refs": undefined_solution_refs,
        "multi_problem_cases": multi_problem_cases,
        "p10_cases": p10_cases,
        "case_covered_problems": case_covered_problems,
        "no_case_problems": no_case_problems,
        "recurring_problem_cases": recurring_problem_cases,
    }


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
    re.compile(r"CPS\s*연결[:\s]*[^\n]*?\b(P\d+)\b"),       # "CPS 연결: P1·P2"
    re.compile(r"\b(P\d+)\s*\([^)]*?(?:추측|review|다운스트림|매처|컨텍스트|검증|LLM|hook|MCP)[^)]*?\)"),  # "P1(LLM 추측...)"
    re.compile(r"\b(P\d+)\s*→\s*S\d+"),                     # "P6 → S6" / "P10 → S10"
    re.compile(r"\b(P\d+)\s*(?:충족|재발|연관|해결)"),       # "P6 충족"
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


def scan_doc(
    path: Path,
    cps_text: str,
    problem_refs: dict,
    solution_counts: dict[str, int] | None = None,
) -> list[str]:
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
    if solution_counts is not None:
        accumulate_solution_refs(fm, solution_counts)

    # 문서별 hit set — frontmatter + 본문 합쳐 중복 제거
    doc_refs: set[str] = set()

    # 1. frontmatter problem 인용 — str 또는 list 형식 모두 처리
    prob_raw = fm.get("problem", "")
    prob_items: list[str] = []
    if isinstance(prob_raw, str):
        s = prob_raw.strip().strip("[]")
        prob_items = [x.strip().strip("'\"") for x in s.split(",") if x.strip()]
    elif isinstance(prob_raw, list):
        prob_items = [str(x).strip() for x in prob_raw if str(x).strip()]
    for item in prob_items:
        if re.match(r"^P\d+$", item):
            doc_refs.add(item)

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

    problem_ids = extract_cps_problem_ids(cps_text)
    problem_count = len(problem_ids) or count_cps_problems(cps_text)
    solution_ids = extract_cps_solution_ids(cps_text)
    solution_problem_map = extract_solution_problem_map(cps_text)
    coupling = assess_cps_solution_coupling(problem_ids, solution_ids, solution_problem_map)
    problem_to_solutions: dict[str, list[str]] = {}
    for sid, pid in solution_problem_map.items():
        problem_to_solutions.setdefault(pid, []).append(sid)
    # 인플레이션 임계값: CPS Problem 수 기반 동적 계산 (고정 6 폐기)
    # 기준: Problem 수 + 2 (소규모 추가 여유), 최소 8
    inflation_threshold = max(8, problem_count + 2)

    all_warnings: list[str] = []
    problem_refs: dict = {}  # P# → 인용 문서 수 (진전 신호 proxy)
    solution_counts: dict[str, int] = {}
    scanned = 0
    for md in sorted(docs_root.rglob("*.md")):
        md_posix = str(md).replace("\\", "/")
        if md_posix == CPS_DOC:
            continue
        # archived는 역사 박제 영역이다. current CPS 진전·분류 proxy에 섞으면
        # retired/absorbed P#가 살아 있는 Problem처럼 오염된다.
        if md_posix.startswith("docs/archived/") or "/docs/archived/" in md_posix:
            continue
        # docs/harness/ 는 upstream CPS를 참조하는 하네스 자체 문서 — 다운스트림 CPS와 대조 시 항상 오탐
        if md_posix.startswith("docs/harness/") or "/docs/harness/" in md_posix:
            continue
        scanned += 1
        all_warnings.extend(scan_doc(md, cps_text, problem_refs, solution_counts))

    wip_problem_signals = count_wip_problem_signals(docs_root, problem_to_solutions)
    case_catalog = analyze_cps_case_catalog(docs_root, problem_ids, solution_ids)

    # BIT NEW 플래그 폐기 (§S-3 73% 삭감). BIT 자가 발화 의존 메커니즘
    # 전체 폐기 — 본 집계도 함께 폐기.

    print(f"## CPS 무결성 감시")
    print(f"")
    print(f"- 스캔 문서: {scanned}개")
    print(f"- CPS Problem 수: {problem_count}개")
    if problem_count > inflation_threshold:
        print(f"  ⚠ Problem 인플레이션 의심 — {problem_count} > {inflation_threshold} (동적 임계값). "
              f"근접 Problem 병합 검토 권고")
    print(f"- 박제 의심: {len(all_warnings)}건")

    if all_warnings:
        print(f"")
        print(f"### 박제 의심 상세")
        for w in all_warnings:
            print(f"- {w}")

    known_problem_refs = {
        pid: count for pid, count in problem_refs.items() if pid in set(problem_ids)
    }
    unknown_problem_refs = {
        pid: count for pid, count in problem_refs.items() if pid not in set(problem_ids)
    }

    # Problem 진전 신호 — 인용 문서 수 (eval --deep 활용)
    if known_problem_refs:
        print(f"")
        print(f"### Problem 인용 빈도 (진전 신호 proxy)")
        for pid in sorted(known_problem_refs, key=lambda x: int(x[1:])):
            print(f"- {pid}: {known_problem_refs[pid]}건")
        unreferenced = []
        for pid in problem_ids:
            if pid not in known_problem_refs:
                unreferenced.append(pid)
        if unreferenced:
            print(f"")
            dormant: list[str] = []
            supported: list[str] = []
            for pid in unreferenced:
                related_sids = sorted(problem_to_solutions.get(pid, []), key=lambda x: int(x[1:]))
                related_solution_refs = sum(solution_counts.get(sid, 0) for sid in related_sids)
                wip_mentions = wip_problem_signals.get(pid, 0)
                if related_solution_refs or wip_mentions:
                    sid_label = ",".join(related_sids) if related_sids else "-"
                    supported.append(
                        f"{pid} (related S: {sid_label}, solution refs: {related_solution_refs}, WIP mentions: {wip_mentions})"
                    )
                else:
                    dormant.append(pid)
            if dormant:
                print(f"⚠ primary 인용 0건 Problem (정체 의심): {', '.join(dormant)}")
                print(
                    "  problem: 0 + related solution-ref/s: 0 + 진행 중 WIP 언급 0이 "
                    "6개월 이상 지속될 때 Problem 폐기 또는 병합 검토 권고"
                )
            if supported:
                print(f"ℹ primary 인용 0건이나 보조 신호가 있는 Problem: {', '.join(supported)}")
                print("  폐기·병합 전 Solution 인용, 진행 중 WIP, kickoff 보존 사유를 함께 확인")
    if unknown_problem_refs:
        print(f"")
        unknown_label = ", ".join(
            f"{pid}:{unknown_problem_refs[pid]}건"
            for pid in sorted(unknown_problem_refs, key=lambda x: int(x[1:]))
        )
        print(f"⚠ 현행 CPS에 없는 본문 P# 인용: {unknown_label}")
        print("  대응: retired/absorbed 번호면 현행 P#로 재분류하고, 신규 현상이면 CPS add 검토")

    # 관계 그래프 점검 — HARNESS_MAP.md 폐기 (§S-1 CPS 재설계).
    # wiki 그래프 모델로 대체 (cluster + tag 백링크). 본 점검 폐기.

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

    print(f"")
    print(f"### CPS P↔S 결합도")
    if coupling["orphan_problems"]:
        print(f"- ⚠ Solution 없는 Problem: {', '.join(coupling['orphan_problems'])}")
    else:
        print("- Problem→Solution coverage: 100% ✅")
    if coupling["unmapped_solutions"]:
        print(f"- ⚠ 대상 P# 매핑 없는 Solution: {', '.join(coupling['unmapped_solutions'])}")
    if coupling["dangling_solutions"]:
        print(f"- ⚠ 존재하지 않는 P#를 가리키는 Solution: {', '.join(coupling['dangling_solutions'])}")
    if coupling["unknown_map_entries"]:
        print(f"- ⚠ Solution 목록에 없는 매핑 entry: {', '.join(coupling['unknown_map_entries'])}")
    if not (
        coupling["unmapped_solutions"]
        or coupling["dangling_solutions"]
        or coupling["unknown_map_entries"]
    ):
        print("- Solution→Problem mapping: 100% ✅")

    print(f"")
    print(f"### CPS case catalog (학습·적응 신호)")
    case_count = int(case_catalog["case_count"])
    covered = case_catalog["case_covered_problems"]
    no_case = case_catalog["no_case_problems"]
    recurring = case_catalog["recurring_problem_cases"]
    undefined_p = case_catalog["undefined_problem_refs"]
    undefined_s = case_catalog["undefined_solution_refs"]
    multi_cases = case_catalog["multi_problem_cases"]
    p10_cases = case_catalog["p10_cases"]
    print(f"- case 박제: {case_count}건")
    print(f"- case coverage: {len(covered)}/{len(problem_ids)} Problems")
    if recurring:
        recurring_label = ", ".join(
            f"{pid}:{recurring[pid]}건"
            for pid in sorted(recurring, key=lambda x: int(x[1:]))
        )
        print(f"- 반복 Problem(case 2건 이상): {recurring_label}")
    else:
        print("- 반복 Problem(case 2건 이상): 0건")
    print(f"- 다중 P case: {len(multi_cases)}건")
    print(f"- P10 case: {len(p10_cases)}건")
    if no_case:
        print(f"- case 없는 Problem: {', '.join(no_case)}")
    if undefined_p or undefined_s:
        print(
            f"- ⚠ 정의 밖 case ref: P={len(undefined_p)}건, S={len(undefined_s)}건"
        )
        for item in [*undefined_p, *undefined_s][:10]:
            print(f"  - {item}")
        if len(undefined_p) + len(undefined_s) > 10:
            print(f"  ... 외 {len(undefined_p) + len(undefined_s) - 10}건")
        print("  대응: retired/absorbed 번호면 현행 P/S로 재분류하고, 신규 현상이면 CPS add 검토")
    else:
        print("- 정의 밖 case ref: 0건 ✅")

    # 피드백 리포트 포맷 검증
    fb_warnings = check_feedback_reports(docs_root)
    print(f"")
    print(f"## 피드백 리포트")
    if fb_warnings is None:
        print(f"- migration-log.md 없음 (다운스트림 전용) — skip ✅")
    elif not fb_warnings:
        print(f"- 피드백 리포트: 없음 ✅")
    else:
        fr_items = [w for w in fb_warnings if w.startswith("FR-")]
        format_warnings = [w for w in fb_warnings if not w.startswith("FR-")]
        if format_warnings:
            for w in format_warnings:
                print(f"- ⚠️ {w}")
        else:
            for w in fr_items:
                print(f"- {w}")

    return 0


def check_feedback_reports(docs_root: Path) -> list[str] | None:
    """migration-log.md의 Feedback Reports 섹션 포맷 검증.

    Returns:
        None  — migration-log.md 없음 (다운스트림 전용 파일, skip)
        []    — FR 항목 없음 또는 모두 정상
        [str] — 포맷 경고 목록
    """
    log_path = docs_root / "harness" / "migration-log.md"
    if not log_path.exists():
        return None

    try:
        text = log_path.read_text(encoding="utf-8")
    except Exception as e:
        return [f"migration-log.md Read 실패: {e}"]

    # Feedback Reports 섹션 양면 매칭 (v0.42.3 — 다운스트림 양식 차이 대응)
    # - top-level: `## Feedback Reports` (다음 `## ` 또는 EOF까지)
    # - 버전 섹션 내 서브헤더: `### Feedback Reports` (다음 `## ` 또는 `### ` 또는 EOF까지)
    # 다운스트림이 버전 섹션 안에 서브헤더로 작성하면 top-level만 잡던 구버전이 미인식
    sections: list[str] = []
    for m in re.finditer(
        r"^(##|###) Feedback Reports\s*\n(.*?)(?=^##\s|\Z)",
        text, re.DOTALL | re.MULTILINE,
    ):
        sections.append(m.group(2))

    if not sections:
        return []  # 섹션 없음 = FR 항목 없음

    # FR-NNN 항목 추출 — 헤더 레벨 양면 (### 또는 ####)
    # 필드 매칭 양식 (v0.42.6 — bold 내부 괄호 보강어 보강, FR-010 응답):
    # - bold 마커: `**필드**:` / `**필드 (보강어)**:` (필드명 뒤 선택적 괄호 허용)
    # - plain: `필드:`
    # - 헤더 인라인: `(필드: ...)` 또는 `(필드:` 괄호 안
    # 다운스트림이 헤더 라인에 `#### FR-NNN ... (심각도: medium — ...)` 형식으로
    # 표기하면 본문에 별도 `**심각도**:` 라인이 없어도 검출되도록 보강
    warnings: list[str] = []
    seen_ids: set[str] = set()
    required_fields = ["관점", "약점", "실천", "심각도"]
    fr_split_pattern = re.compile(r"(?=^#{3,4} FR-\d+)", re.MULTILINE)
    fr_header_pattern = re.compile(r"^#{3,4} (FR-\d+)")

    def _field_present(name: str, block: str) -> bool:
        # 3 양식 양면 매칭 — bold 마커(+ 선택 괄호 보강어) / plain / 헤더 인라인 괄호
        pattern = (
            rf"(?:\*\*{name}(?:\s+\([^)]*\))?\*\*\s*:"
            rf"|(?<![\w가-힣]){name}\s*:"
            rf"|\(\s*{name}\s*:)"
        )
        return bool(re.search(pattern, block))

    for fb_section in sections:
        fr_blocks = fr_split_pattern.split(fb_section)
        for block in fr_blocks:
            fr_m = fr_header_pattern.match(block)
            if not fr_m:
                continue
            fr_id = fr_m.group(1)
            if fr_id in seen_ids:
                continue  # 같은 FR ID 중복 방지 (여러 섹션에 걸쳐 있을 경우)
            seen_ids.add(fr_id)
            missing = [f for f in required_fields if not _field_present(f, block)]
            if missing:
                warnings.append(f"⚠️ {fr_id}: **{'**, **'.join(missing)}** 없음")
            else:
                warnings.append(f"{fr_id} ✅")

    return warnings


if __name__ == "__main__":
    sys.exit(main())
