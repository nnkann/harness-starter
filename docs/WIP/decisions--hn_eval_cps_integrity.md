---
title: eval CPS 무결성 감시 — 박제 감지·Problem 인플레이션
domain: harness
problem: P5
solution-ref:
  - S5 — "원인이 특정되면 해당 항목 제거 + 실측 재측정 (부분)"
tags: [eval, cps, integrity, downstream]
relates-to:
  - path: harness/hn_harness_efficiency_overhaul.md
    rel: caused-by
status: pending
created: 2026-05-02
---

# eval CPS 무결성 감시

## 사전 준비
- 읽을 문서: `.claude/skills/eval/SKILL.md`, `.claude/scripts/pre_commit_check.py` (verify_solution_ref·get_cps_text)
- 이전 산출물: hn_harness_efficiency_overhaul.md Phase 2-A v0.29.1 (pre-check 박제 감지 1차 적용)

## 목표
eval --harness가 모든 frontmatter `solution-ref` 인용을 CPS 본문과 대조해
박제·Problem 인플레이션 발견. CPS = 마스터의 무결성 감시.

## 작업 목록

### 1. eval --harness CPS 박제 grep

**Acceptance Criteria**:
- [ ] Goal: eval --harness가 모든 docs/ 문서의 frontmatter solution-ref 인용을 CPS 본문과 대조해 박제 의심 문서 list 출력
  검증:
    review: review
    tests: 없음 (eval 도구 — pytest marker 없음)
    실측: 본 starter에서 eval --harness 실행 후 박제 의심 0건 확인
- [ ] eval/SKILL.md에 "## CPS 무결성 감시" 섹션 신설
- [ ] pre_commit_check.py의 verify_solution_ref 재사용 (코드 중복 X)
- [ ] Problem 인플레이션 감지 — Problem 6개 초과 시 경고
- [ ] 보고 형식: 박제 의심 문서 path:line + 인용 vs CPS 본문 diff

### 2. eval --deep CPS Problem 진전 측정

**Acceptance Criteria**:
- [ ] Goal: eval --deep이 각 Problem별 진전 신호(완료된 Solution 충족 기준 비율) 보고
  검증:
    review: self
    tests: 없음
    실측: 본 starter에서 진전 보고 1회 확인
- [ ] 충족 기준 텍스트 → 충족 여부 매핑 메커니즘 정의
- [ ] 진전 측정 6개월 정체 시 Problem 정체 신호 출력

## 결정 사항
(작업하면서 채움)

## 메모
- 본 wave는 v0.29.1 hn_harness_efficiency_overhaul.md에서 분리됨
- pre_commit_check.py의 verify_solution_ref 함수 이미 작성됨 — eval에서 재사용
