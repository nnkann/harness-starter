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
status: pending
created: 2026-05-02
---

# commit 5.3 자동 실행

## 사전 준비
- 읽을 문서: `.claude/skills/commit/SKILL.md` Step 5.3 (SSOT 정의됨), `.claude/scripts/pre_commit_check.py` (ac_tests·ac_actual 출력)
- 이전 산출물: hn_harness_efficiency_overhaul.md Phase 2-A v0.29.1

## 목표
commit 스킬이 pre-check 출력 `ac_tests`·`ac_actual` 값을 화이트리스트 기반
자동 실행. 작성자 자가 보고 → 자동 실행으로 회귀 가드 강제.

## 작업 목록

### 1. commit/SKILL.md Step 5.3 코드 — 화이트리스트 자동 실행

**Acceptance Criteria**:
- [ ] Goal: pre-check 출력 ac_tests가 화이트리스트(pytest·bash -n·python -m·grep) 명령이면 자동 실행, 그 외는 가이드만
  검증:
    review: review
    tests: pytest -m stage
    실측: ac_tests=pytest -m secret 더미 WIP commit → pre-check 후 자동 실행 확인
- [ ] commit/SKILL.md Step 5.3 코드 블록 구체화 (현재는 SSOT만)
- [ ] 화이트리스트 패턴 정규식 정의 — `^(pytest|bash -n|python -m|grep)\b`
- [ ] 실패 시 commit 차단 + stderr 보고
- [ ] 화이트리스트 외 명령은 stderr 가이드만 + 사용자 승인 후 수동 실행

### 2. ac_actual 처리 (실측 명령)

**Acceptance Criteria**:
- [ ] Goal: ac_actual 값도 화이트리스트 자동 실행, 그 외 가이드
  검증:
    review: self
    tests: 없음
    실측: ac_actual=AKIA 실측 시나리오 → 가이드 출력 확인
- [ ] tests와 동일 화이트리스트 + 동일 실패 처리
- [ ] 자동 실행 명령 + 결과를 commit log에 한 줄 추가

## 결정 사항
(작업하면서 채움)

## 메모
- 본 wave는 v0.29.1 hn_harness_efficiency_overhaul.md에서 분리됨
- pre-check 출력 (ac_tests·ac_actual)은 이미 v0.29.1에서 구현됨 — commit 스킬은 그것 받기만
- 화이트리스트 외 명령 자동 실행 금지 — 보안 (rm -rf 등 임의 실행 차단)
