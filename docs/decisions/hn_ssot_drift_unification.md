---
title: SSOT drift 발견 시 통합 의무
domain: harness
c: "버전 범프 누락 후속에서 SSOT가 commit Step 4·harness-dev·스크립트 주석·MIGRATIONS 관행으로 나뉘어 판단이 흔들림"
problem: [P7, P11]
s: [S7, S9, S11]
tags: [ssot, drift, implementation]
status: completed
created: 2026-05-20
updated: 2026-05-20
---

# SSOT drift 발견 시 통합 의무

## CPS Rationale

- C -> P: 같은 행동 계약이 여러 위치에 나뉘면 관계·소유권이 흐려지고 동형 drift가 잠복한다.
- P -> S: S7은 소유권·출력 계약을 드러내고, S9·S11은 오염된 단일 신호와 동형 후보 방치를 막는다.
- S -> AC: rules와 implementation Step 2가 SSOT 분산 발견 시 통합·참조화·역할 분리를 완료 기준으로 삼게 한다.

**Acceptance Criteria**:
- [x] Goal: S7·S9·S11 기준으로 SSOT 분산 발견 시 통합·정리 의무를 규칙과 구현 흐름에 명시한다.
  검증:
    review: skip
    tests: 없음
    실측: `.claude/rules/docs.md`에 SSOT drift 통합 원칙, `.claude/rules/code-ssot.md`에 코드 심볼 SSOT 원칙, `.claude/skills/implementation/SKILL.md`와 `.agents/skills/implementation/SKILL.md` Step 2에 실행 절차가 존재한다.
- [x] `docs.md`가 SSOT 분산 발견 시 하나를 owner SSOT로 지정하고 나머지는 참조·mirror·다운스트림 안내로 역할을 축소하도록 명시한다. ✅
- [x] `code-ssot.md`가 함수·메서드·클래스·변수·상수·정규식·schema key·환경변수 이름을 코드 심볼 SSOT 대상으로 명시한다. ✅
- [x] `implementation` Step 2가 후보 SSOT가 2개 이상이면 통합/역할 분리 전 완료 선언을 금지한다.
- [x] `.agents` active mirror도 동일한 Step 2 계약을 가진다.

## 결정 사항

- CPS 갱신: 없음. P7·P11에 이미 있는 관계/동형 drift 문제를 규칙과 작업 흐름으로 보강한다.
