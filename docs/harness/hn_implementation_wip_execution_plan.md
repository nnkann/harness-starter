---
title: implementation WIP 실행 계획 요건 보강
domain: harness
c: "implementation WIP가 AC는 갖췄지만 실제 작업 단위와 단계별 산출물이 빠질 수 있다는 사용자 제안"
problem: P6
s: [S6]
tags: [implementation, wip, ac]
status: completed
created: 2026-05-22
updated: 2026-05-22
---

# implementation WIP 실행 계획 요건 보강

## CPS Rationale

- C → P: AC 형식만 맞고 실행 단계·산출물이 빠지면 완료 증거가 약해져 P6에 해당한다.
- P → S: S6은 검증 책임 위치와 증거 구분을 고정하므로 WIP 단계에서 산출물 기준을 드러내야 한다.
- S → AC: AC가 S6 기준으로 스킬·룰 변경 위치와 실측 grep을 닫으면 완료 가능하다.

## Goal

implementation WIP가 최소한 작업 단위, 단계별 산출물, 다음 단계 진입 검증 기준을 갖추도록 soft warning 규칙을 추가한다.

## 구현 계획

1. implementation 스킬 Step 3에 WIP 실행 계획 soft warning을 추가한다.
   - 산출물: `.claude/skills/implementation/SKILL.md`, `.agents/skills/implementation/SKILL.md`에 `## 구현 계획` 또는 동등 섹션, 단계별 산출물, 예외, hard fail 유예 기준이 명시됨.
2. implementation 스킬 Step 5에 완료 전 점검 지점을 추가한다.
   - 산출물: AC 검증 단계에서 실행 단계/산출물 누락을 경고하고 보완하도록 하는 문구.
3. docs 규칙의 AC 포맷에 implementation WIP 한정 실행성 연결을 남긴다.
   - 산출물: `.claude/rules/docs.md`가 AC의 다음 단계 진입 조건과 implementation 스킬 soft warning 책임을 참조함.

**Acceptance Criteria**:
- [x] Goal: S6 기준으로 implementation WIP 실행 단계·산출물 soft warning이 스킬과 룰에 반영된다.
  검증:
    review: self
    tests: 없음
    실측: `rg -n "implementation WIP 실행 계획 경고|실행 계획 점검|implementation WIP 실행성" .claude/skills/implementation/SKILL.md .agents/skills/implementation/SKILL.md .claude/rules/docs.md`
- [x] `.claude/skills/implementation/SKILL.md` Step 3·5에 실행 단계/산출물 누락 경고와 예외가 있다.
- [x] `.agents/skills/implementation/SKILL.md` Step 3·5가 `.claude` 미러와 같은 행동 계약을 가진다.
- [x] `.claude/rules/docs.md` AC 포맷이 implementation WIP의 다음 단계 진입 조건을 언급하고, 판정 책임은 implementation 스킬 soft warning으로 둔다.

## 결정 사항

- implementation WIP 실행 계획 요건은 hard fail이 아니라 soft warning으로 시작한다.
- 순수 결정문·조사문·사고 기록·write-doc 산출물·1줄 타이포·settings 토글은 예외로 둔다.

## 메모

- 사용자 제안 원문 요지: AC만으로 최종 목표는 검증할 수 있지만, implementation 작업이 실제로 쪼개졌는지는 보장하지 못한다. implementation WIP는 "작업 단위 + 산출물 + 검증 기준"을 갖춰야 한다.
- 실측: `rg -n "implementation WIP 실행 계획 경고|실행 계획 점검|implementation WIP 실행성" ...` 결과 `.claude/skills/implementation/SKILL.md`, `.agents/skills/implementation/SKILL.md`, `.claude/rules/docs.md`에서 모두 hit.
