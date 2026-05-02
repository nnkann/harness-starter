---
title: commit 스킬 5.3 — AC 검증 묶음 자동 실행 (tests·실측 화이트리스트)
domain: harness
problem: P2
solution-ref:
  - S2 — "review tool call 평균 ≤4회 (부분)"
tags: [commit, ac, automation, whitelist]
relates-to:
  - path: harness/hn_harness_efficiency_overhaul.md
    rel: caused-by
status: completed
created: 2026-05-02
updated: 2026-05-02
---

# commit 5.3 자동 실행

## 사전 준비
- 읽을 문서: `.claude/skills/commit/SKILL.md` Step 5.3 (SSOT 정의됨), `.claude/scripts/pre_commit_check.py` (ac_tests·ac_actual 출력) ✅
- 이전 산출물: hn_harness_efficiency_overhaul.md Phase 2-A v0.29.1

## 목표
commit 스킬이 pre-check 출력 `ac_tests`·`ac_actual` 값을 화이트리스트 기반
자동 실행. 작성자 자가 보고 → 자동 실행으로 회귀 가드 강제.

## 작업 목록

### 1. commit/SKILL.md Step 5.3 코드 — 화이트리스트 자동 실행

**Acceptance Criteria**:
- [x] Goal: pre-check 출력 ac_tests가 화이트리스트(pytest·bash -n·python -m·grep) 명령이면 자동 실행, 그 외는 가이드만
  검증:
    review: review
    tests: pytest -m stage
    실측: ac_tests=pytest -m secret 더미 WIP commit → pre-check 후 자동 실행 확인
- [x] commit/SKILL.md Step 5.3 코드 블록 구체화 (현재는 SSOT만) ✅
- [x] 화이트리스트 패턴 정규식 정의 — `^(pytest|bash -n|python -m|grep)\b`
- [x] 실패 시 commit 차단 + stderr 보고
- [x] 화이트리스트 외 명령은 stderr 가이드만 + 사용자 승인 후 수동 실행

### 2. ac_actual 처리 (실측 명령)

**Acceptance Criteria**:
- [x] Goal: ac_actual 값도 화이트리스트 자동 실행, 그 외 가이드
  검증:
    review: self
    tests: 없음
    실측: ac_actual=AKIA 실측 시나리오 → 가이드 출력 확인
- [x] tests와 동일 화이트리스트 + 동일 실패 처리
- [x] 자동 실행 명령 + 결과를 commit log에 한 줄 추가 — **범위 축소 결정**: `🔍 review: <stage> | problem | solution-ref` 라인이 이미 추적 담당(`staging.md` SSOT). ac_tests 결과 별도 라인은 자가 보고 시스템과 중복 — 도입 안 함. 실패 시 commit 차단 자체가 추적 신호.

## 결정 사항

- **변수 추출**: `PRE_CHECK_OUTPUT` 변수에서 `sed -n 's/^ac_tests: //p'`로 1줄 파싱. → 반영: `commit/SKILL.md` Step 5.3 "변수 추출" 블록 ✅
- **화이트리스트 정규식**: `^(pytest|bash -n|python -m|grep)\b` (case 패턴으로 동등 구현). → 반영: `commit/SKILL.md` Step 5.3 "화이트리스트" 블록 ✅
- **공유 함수 `run_ac_check`**: tests·실측 동일 분기 (코드 중복 제거). → 반영: `commit/SKILL.md` Step 5.3 분기 로직 ✅
- **sub-커밋 예외**: `HARNESS_SPLIT_SUB=1` 시 재실행 skip — 부모에서 이미 검증. → 반영: Step 5.3 진입 가드
- **`none` 처리**: pre-check이 빈 값을 `none`으로 출력. case 패턴에 `""|none|"없음"` 3개 포함
- **commit log 라인 추가 거부**: `🔍 review:` 한 줄이 이미 추적 SSOT. ac_tests 결과 라인 신설은 자가 보고와 중복 — 도입 안 함
- CPS 갱신: 없음 (Solution S2 메커니즘 변경 없음, 기존 SSOT 보강)

## 메모

- 본 wave는 v0.29.1 hn_harness_efficiency_overhaul.md에서 분리됨
- pre-check 출력 (ac_tests·ac_actual)은 v0.29.1에서 구현됨 — commit 스킬은 그것 받기만
- 화이트리스트 외 명령 자동 실행 금지 — 보안 (`rm -rf` 등 임의 실행 차단)
- 실측 검증: 6 케이스(pytest·grep·bash -n·python -m·rm -rf·none) 분기 로직 모두 의도대로 동작 확인 (bash 시뮬레이션)
- pytest -m stage: 2 passed (회귀 가드 통과)
