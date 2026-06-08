---
title: eval에 Solution 충족 인용 분포 집계 추가
domain: harness
problem: P6
solution-ref:
  - S6 — "eval --deep이 사후 audit"
tags: [eval, cps, solution-ref, aggregation]
status: completed
created: 2026-05-03
updated: 2026-05-03
---

# eval에 Solution 충족 인용 분포 집계 추가

## 사전 준비
- 읽을 문서: `.claude/scripts/eval_cps_integrity.py`, `.claude/skills/eval/SKILL.md`, `docs/guides/project_kickoff.md`
- 이전 산출물: 없음

## 목표
- `eval_cps_integrity.py`에 Solution별 충족 인용 카운트 기능 추가
- CPS에 Solution이 얼마나 문서화됐는지 eval --harness 실행 시 한눈에 파악 가능하게
- 0건 = 즉 실패 단정 금지 — 사람 판단 자리임을 출력에 명시

## 작업 목록
### 1. eval_cps_integrity.py 확장

**영향 파일**: `.claude/scripts/eval_cps_integrity.py`

**Acceptance Criteria**:
- [x] Goal: count_solution_refs() 함수가 docs/ 전체를 스캔해 Solution별 인용 카운트를 반환한다
  검증:
    review: self
    tests: python3 -m pytest .claude/scripts/tests/ -q -k "solution_ref"
    실측: python3 .claude/scripts/eval_cps_integrity.py 실행 후 "Solution 충족 인용 분포" 섹션 출력 확인
- [x] S1~S6 각각의 인용 카운트가 출력된다
- [x] 0건 Solution에 ⚠ 마커가 붙되 "미충족 의심" 설명과 함께 사람 판단을 유도한다
- [x] 기존 출력(박제 의심, Problem 인용 빈도)이 깨지지 않는다

### 2. eval/SKILL.md 해석 가이드 추가

**영향 파일**: `.claude/skills/eval/SKILL.md`

**Acceptance Criteria**:
- [x] Goal: Solution 충족 인용 분포 섹션 결과를 어떻게 해석하는지 가이드가 추가된다
  검증:
    review: self
    tests: 없음
    실측: 없음 (문서 추가)

## 결정 사항
- count_solution_refs()는 frontmatter `solution-ref: [S# — ...]` 패턴을 파싱해 S# 추출
- CPS에서 Solution ID 목록 추출은 기존 count_cps_problems()와 대칭 구조로 설계
- 출력 위치: Problem 인용 빈도 섹션 뒤에 추가 (논리 흐름: Problem 인용 → Solution 인용)

## 메모
- advisor 판단(2026-05-03): 결정 C 채택. eval_cps_integrity.py 확장이 Surgical Change
- 0건 단정 금지 근거: Solution이 최근 등록됐거나 아직 구현 전일 수 있음 — 사람이 맥락을 알아야 판단 가능
- CPS 갱신: 없음 (기존 S6 범위 내)
