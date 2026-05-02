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


PROBLEM_INFLATION_THRESHOLD = 6


def count_cps_problems(cps_text_normalized: str) -> int:
    """CPS 본문에서 P# 패턴 고유 개수 카운트.
    normalize_quote 후라 줄바꿈은 공백. P1·P2... 패턴 grep.
    """
    ids = set(re.findall(r"\bP(\d+)\b", cps_text_normalized))
    return len(ids)


def scan_doc(path: Path, cps_text: str, problem_refs: dict) -> list[str]:
    """단일 문서 frontmatter 검사.
    - solution-ref 박제 grep
    - problem 카운트 누적 (problem_refs dict mutate)
    path:warning 형식 list 반환.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        return [f"{path}: read 실패 ({e})"]

    fm, _ = parse_frontmatter(text)

    # problem 카운트 (진전 측정 — Problem별 인용 빈도 proxy)
    prob = fm.get("problem", "")
    if isinstance(prob, str) and re.match(r"^P\d+$", prob.strip()):
        problem_refs.setdefault(prob.strip(), 0)
        problem_refs[prob.strip()] += 1

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

    all_warnings: list[str] = []
    problem_refs: dict = {}  # P# → 인용 문서 수 (진전 신호 proxy)
    scanned = 0
    for md in sorted(docs_root.rglob("*.md")):
        if str(md).replace("\\", "/") == CPS_DOC:
            continue
        scanned += 1
        all_warnings.extend(scan_doc(md, cps_text, problem_refs))

    print(f"## CPS 무결성 감시")
    print(f"")
    print(f"- 스캔 문서: {scanned}개")
    print(f"- CPS Problem 수: {problem_count}개")
    if problem_count > PROBLEM_INFLATION_THRESHOLD:
        print(f"  ⚠ Problem 인플레이션 의심 — {problem_count} > {PROBLEM_INFLATION_THRESHOLD}. "
              f"근접 Problem 병합 검토 권고")
    print(f"- 박제 의심: {len(all_warnings)}건")

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

    return 0


if __name__ == "__main__":
    sys.exit(main())
