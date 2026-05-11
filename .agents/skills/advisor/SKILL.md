---
name: advisor
description: >-
  멀티 에이전트 판단 엔진 스킬. PM(orchestrator) 에이전트가 specialist 풀
  (researcher/codebase-analyst/risk-analyst/threat-analyst/performance-analyst)
  에서 필요한 것만 골라 병렬 호출하고, 의사결정 프레임 라이브러리
  (Weighted Matrix·Pre-mortem·Trade-off·Expected Value·ADR·Reversibility)로
  판단 경로·충돌 해소·뒤집힐 조건을 명시한다.
  TRIGGER when: 기술 스택 선택, 아키텍처 결정, 새 라이브러리 도입,
  리팩토링 방향 등 판단이 필요한 순간에 "검증할까요? [Y/n]"으로 개입
  여부를 확인.
  SKIP: 답이 명확한 단순 질문, 이미 결정된 사항, 컨벤션 문제
  (naming.md/coding.md 참조).
---

# /advisor 스킬

`.claude/agents/advisor.md` 에이전트를 호출하는 얇은 래퍼. 실제 로직
(Orchestration·프레임 라이브러리·충돌 해소·판단 경로)은 **전부 에이전트
본문이 SSOT**. 본문 중복 금지.

## 사용법

| 사용법 | 설명 |
|--------|------|
| `/advisor <질문>` | 질문을 에이전트에 위임 |
| `/advisor <계획 또는 접근법>` | 계획의 타당성 검증 |

## 흐름

1. 사용자 입력 수신. 모호하면 "무엇을 검증할까요?" 한 줄 질문
2. Agent tool로 advisor 에이전트 호출. prompt에 사용자 원문 + 맥락 +
   명시적 우선순위(있으면) 포함
3. 에이전트 응답을 그대로 사용자에게 전달. 추가 가공 없음

## 다른 스킬과의 연동

| 호출자 | 지점 | 동작 |
|--------|------|------|
| implementation | Step 0.5 | "접근법 검증할까요? [Y/n]" → Y 시 호출 |
| harness-init | Step 6 | 스택 결정 전 — 단일 researcher로 족한 경우 직접 호출 권장 |
| commit | Step 7 | 큰 결정 hit 시 review와 병렬 |
| eval --deep | 2차 검증 | 4 specialist 고정 병렬 (advisor.md "예외" 섹션 SSOT) |
