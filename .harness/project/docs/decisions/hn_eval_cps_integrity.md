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
status: completed
created: 2026-05-02
updated: 2026-05-02
---

# eval CPS 무결성 감시

## 사전 준비
- 읽을 문서: `.claude/skills/eval/SKILL.md`, `.claude/scripts/pre_commit_check.py` (verify_solution_ref·get_cps_text) ✅
- 이전 산출물: hn_harness_efficiency_overhaul.md Phase 2-A v0.29.1 (pre-check 박제 감지 1차 적용)

## 목표
eval --harness가 모든 frontmatter `solution-ref` 인용을 CPS 본문과 대조해
박제·Problem 인플레이션 발견. CPS = 마스터의 무결성 감시.

## 작업 목록

### 1. eval --harness CPS 박제 grep

**Acceptance Criteria**:
- [x] Goal: eval --harness가 모든 docs/ 문서의 frontmatter solution-ref 인용을 CPS 본문과 대조해 박제 의심 문서 list 출력
  검증:
    review: review
    tests: 없음 (eval 도구 — pytest marker 없음)
    실측: 본 starter에서 eval --harness 실행 후 박제 의심 0건 확인
- [x] eval/SKILL.md에 "## CPS 무결성 감시" 섹션 신설 ✅
- [x] pre_commit_check.py의 verify_solution_ref 재사용 (코드 중복 X)
- [x] Problem 인플레이션 감지 — Problem 6개 초과 시 경고
- [x] 보고 형식: 박제 의심 문서 path:line + 인용 vs CPS 본문 diff

### 2. eval --deep CPS Problem 진전 측정

**Acceptance Criteria**:
- [x] Goal: eval --deep이 각 Problem별 진전 신호(완료된 Solution 충족 기준 비율) 보고
  검증:
    review: self
    tests: 없음
    실측: 본 starter에서 진전 보고 1회 확인
- [x] 충족 기준 텍스트 → 충족 여부 매핑 메커니즘 정의 — **결정**: 자연어 충족 기준 자동 판정 불가 → Problem별 frontmatter 인용 빈도 proxy 채택
- [x] 진전 측정 6개월 정체 시 Problem 정체 신호 출력 — 인용 0건 Problem 즉시 표시 + 6개월 가이드 SKILL.md 명시 (시계열 비교는 본 wave 범위 외, 운용 가이드) ✅

## 결정 사항

- **헬퍼 스크립트 신설**: `.claude/scripts/eval_cps_integrity.py`. SKILL.md 1-liner 작성 위험 회피. → 반영: 본 파일·`eval/SKILL.md` "## CPS 무결성" 섹션 ✅
- **재사용 패턴**: `pre_commit_check.py`를 `importlib.spec_from_file_location`로 동적 import — 모듈명 하이픈 회피 + 코드 중복 0. → 반영: `eval_cps_integrity.py` 상단 ✅
- **eval/SKILL.md 통합 위치**: `--harness` 점검 항목 5(모호성·모순·부패·강제력·**무결성**). 별도 모드 신설 X (Problem inflation은 하네스 품질 항목) ✅
- **진전 신호 proxy**: 자연어 충족 기준 자동 판정 불가 → frontmatter `problem` 인용 빈도로 proxy. 인용 0건 = 정체 의심
- **자동화 불가 영역 정직 고지**: 시계열 비교(이전 eval delta)는 본 wave 범위 외. SKILL.md `--deep 활용` 섹션에 운용 가이드만 명시 ✅
- CPS 갱신: 없음 (Solution S5 메커니즘 변경 없음, eval 도구 보강)

## 메모

- 본 wave는 v0.29.1 hn_harness_efficiency_overhaul.md에서 분리됨
- pre_commit_check.py의 verify_solution_ref 함수 이미 작성됨 — eval에서 재사용
- **실측 발견**: 본 starter에서 P1·P3·P4·P6 frontmatter 인용 0건 — Problem 정체 또는 정의 사용 안 됨 신호. 별도 사안으로 CPS 자체 검토 필요할 수 있음 (현재는 알림만, 자동 조치 X)
- 박제 감지 시뮬레이션: `S99 — "존재하지 않는 박제 문자열"` → 정상 경고 출력 확인
- Problem 인플레이션 시뮬레이션: 임계 5로 낮춰 6 > 5 경고 출력 확인
