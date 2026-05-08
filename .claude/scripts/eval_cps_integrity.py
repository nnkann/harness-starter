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


def check_harness_map(claude_root: Path) -> list[str]:
    """HARNESS_MAP.md 존재 여부 + 실제 파일 대조 (관계 그래프 단절 감지).

    HARNESS_MAP.md의 각 섹션에서 등재된 파일명을 추출하고,
    실제 .claude/ 하위 파일과 대조해 누락·초과를 보고한다.

    Returns: warning 문자열 목록
    """
    warnings: list[str] = []
    map_path = claude_root / "HARNESS_MAP.md"

    if not map_path.exists():
        warnings.append("⚠ HARNESS_MAP.md 미생성 — .claude/HARNESS_MAP.md 없음")
        return warnings

    try:
        map_text = map_path.read_text(encoding="utf-8")
    except Exception as e:
        warnings.append(f"⚠ HARNESS_MAP.md Read 실패: {e}")
        return warnings

    # ── 1. Rules 섹션 대조 ──────────────────────────────────────────────
    # MAP에서 "rules/xxx.md" 패턴 추출
    map_rules = set(re.findall(r"rules/(\w[\w-]*\.md)", map_text))
    actual_rules = {p.name for p in (claude_root / "rules").glob("*.md")} if (claude_root / "rules").is_dir() else set()
    for r in sorted(actual_rules - map_rules):
        warnings.append(f"⚠ [Rules] 실제 파일이 HARNESS_MAP에 없음: rules/{r}")
    for r in sorted(map_rules - actual_rules):
        warnings.append(f"⚠ [Rules] MAP 등재됐으나 파일 없음: rules/{r}")

    # ── 2. Skills 섹션 대조 ─────────────────────────────────────────────
    # MAP에서 "skills/xxx/SKILL.md" 패턴 추출 → 스킬명 추출
    map_skills = set(re.findall(r"skills/(\w[\w-]*)/SKILL\.md", map_text))
    actual_skills = {p.name for p in (claude_root / "skills").iterdir() if p.is_dir()} if (claude_root / "skills").is_dir() else set()
    for s in sorted(actual_skills - map_skills):
        warnings.append(f"⚠ [Skills] 실제 스킬이 HARNESS_MAP에 없음: skills/{s}/")
    for s in sorted(map_skills - actual_skills):
        warnings.append(f"⚠ [Skills] MAP 등재됐으나 폴더 없음: skills/{s}/")

    # ── 3. Agents 섹션 대조 ─────────────────────────────────────────────
    # MAP에서 "agents/xxx.md" 패턴 추출
    map_agents = set(re.findall(r"agents/(\w[\w-]*\.md)", map_text))
    actual_agents = {p.name for p in (claude_root / "agents").glob("*.md")} if (claude_root / "agents").is_dir() else set()
    for a in sorted(actual_agents - map_agents):
        warnings.append(f"⚠ [Agents] 실제 파일이 HARNESS_MAP에 없음: agents/{a}")
    for a in sorted(map_agents - actual_agents):
        warnings.append(f"⚠ [Agents] MAP 등재됐으나 파일 없음: agents/{a}")

    # ── 4. Scripts 섹션 대조 ────────────────────────────────────────────
    # MAP에서 scripts 테이블의 파일명 추출 (| 파일명 | 패턴)
    map_scripts: set[str] = set()
    for m in re.finditer(r"\|\s*([\w.-]+\.(?:py|sh))\s*\|", map_text):
        name = m.group(1)
        # 헤더 행 제외
        if name not in ("스크립트", "Scripts"):
            map_scripts.add(name)
    scripts_dir = claude_root / "scripts"
    actual_scripts: set[str] = set()
    if scripts_dir.is_dir():
        for p in scripts_dir.iterdir():
            if p.is_file() and p.suffix in (".py", ".sh") and not p.parent.name == "tests":
                actual_scripts.add(p.name)
    # tests/ 하위는 MAP 대조 제외
    for s in sorted(actual_scripts - map_scripts):
        warnings.append(f"⚠ [Scripts] 실제 파일이 HARNESS_MAP에 없음: scripts/{s}")
    for s in sorted(map_scripts - actual_scripts):
        warnings.append(f"⚠ [Scripts] MAP 등재됐으나 파일 없음: scripts/{s}")

    # ── 5. enforced-by 없는 규칙 감지 ──────────────────────────────────
    # HARNESS_MAP.md Rules 테이블 구조:
    #   Layer 0/2/3: | 규칙 | 역할 | defends | enforced-by | 원본 |
    #   Layer 1:     | 규칙 | 역할 | defends | parent | children | enforced-by | 원본 |
    # enforced-by는 마지막에서 두 번째 컬럼 → 뒤에 "원본" 컬럼이 반드시 존재.
    # "—" 또는 "-"만 감지 (빈 문자열 제외 → always-match 오탐 방지).
    enforced_empty_pat = re.compile(
        r"^\|\s*([\w-]+)\s*\|(?:[^|\n]*\|)+\s*(?:—|-)\s*\|[^|\n]+\|\s*$",
        re.MULTILINE,
    )
    # Rules 섹션만 추출해서 검사 (## Rules ~ ## Skills 사이)
    rules_section_m = re.search(r"## Rules.*?(?=## Skills|## Agents|$)", map_text, re.DOTALL)
    if rules_section_m:
        rules_section = rules_section_m.group(0)
        for m in enforced_empty_pat.finditer(rules_section):
            rule_name = m.group(1).strip()
            # 헤더·구분자·원본경로 행 제외
            if rule_name not in ("규칙", "---", "") and not rule_name.startswith("rules/"):
                warnings.append(f"⚠ [enforced-by 없음] {rule_name} — P7 방어 공백 가능성")

    # ── 6. defends-by 없는 Problem 감지 ────────────────────────────────
    # CPS 섹션의 defends-by 컬럼이 "(규칙 없음"·"(조사 중" 이외의 빈 값
    cps_section_m = re.search(r"## CPS.*?(?=## Rules|$)", map_text, re.DOTALL)
    if cps_section_m:
        cps_section = cps_section_m.group(0)
        # | P# | ... | defends-by 값 | ... | 형태
        # 빈 문자열 대안 제거 → 명시적 "—" 또는 "-"만 감지 (always-match 방지)
        # 괄호 값 "(규칙 없음...)"·"(조사 중...)"은 의도적 선언 → 별도 처리
        no_rule_pat = re.compile(r"^\|\s*(P\d+)\s*\|[^|]+\|\s*([^|]*?)\s*\|", re.MULTILINE)
        for m in no_rule_pat.finditer(cps_section):
            pid = m.group(1)
            defends_by = m.group(2).strip()
            # "—" 또는 "-"만 미선언으로 판정
            # "(규칙 없음...)"·"(조사 중...)" 등 괄호 시작은 의도적 선언 — 제외
            if defends_by in ("—", "-") and pid:
                warnings.append(f"⚠ [defends-by 없음] {pid} — 방어 규칙 미선언")

    return warnings


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

    # 관계 그래프 점검 — HARNESS_MAP.md vs 실제 파일 단절 감지
    claude_root = Path(".claude")
    map_warnings = check_harness_map(claude_root)
    print(f"")
    print(f"## 관계 그래프 점검")
    if map_warnings:
        print(f"- 단절 감지: {len(map_warnings)}건 ⚠")
        for w in map_warnings:
            print(f"  {w}")
    else:
        print(f"- 단절 감지: 0건 ✅ (HARNESS_MAP.md와 실제 파일 정합)")

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

    # ## Feedback Reports 섹션 추출
    fb_section_m = re.search(r"## Feedback Reports(.*?)(?=^## |\Z)", text, re.DOTALL | re.MULTILINE)
    if not fb_section_m:
        return []  # 섹션 없음 = FR 항목 없음

    fb_section = fb_section_m.group(1)

    # FR-NNN 항목 추출
    fr_blocks = re.split(r"(?=### FR-\d+)", fb_section)
    warnings: list[str] = []
    required_fields = ["**관점**", "**약점**", "**실천**", "**심각도**"]

    for block in fr_blocks:
        fr_m = re.match(r"### (FR-\d+)", block)
        if not fr_m:
            continue
        fr_id = fr_m.group(1)
        missing = [f for f in required_fields if f not in block]
        if missing:
            warnings.append(f"⚠️ {fr_id}: {', '.join(missing)} 없음")
        else:
            warnings.append(f"{fr_id} ✅")

    return warnings


if __name__ == "__main__":
    sys.exit(main())
