---
name: advisor
description: >-
  멀티 에이전트 검증 스킬. PM(orchestrator) 에이전트가 specialist 풀
  (researcher/codebase-analyst/risk-analyst/performance-analyst/test-strategist)
  에서 필요한 것만 골라 병렬 호출하고 권고를 종합한다.
  TRIGGER when: 기술 스택 선택, 아키텍처 결정, 새 라이브러리 도입,
  리팩토링 방향 등 판단이 필요한 순간에 "검증할까요? [Y/n]"으로 개입
  여부를 확인.
  SKIP: 답이 명확한 단순 질문, 이미 결정된 사항, 컨벤션 문제
  (naming.md/coding.md 참조).
---

# /advisor 스킬

판단이 어려울 때, advisor 에이전트(PM, opus)가 specialist 풀에서 필요한
것만 골라 병렬 호출하고 권고를 종합한다.

## 사용법

| 사용법 | 설명 |
|--------|------|
| `/advisor <질문>` | 질문에 대해 적정 specialist 조합으로 검증 |
| `/advisor <계획 또는 접근법>` | 계획의 타당성 검증 |

## 흐름

이 스킬은 advisor 에이전트(`.claude/agents/advisor.md`)를 호출하는
얇은 래퍼다. 실제 orchestration·specialist 선정·종합 로직은 에이전트가
가진다.

### Step 1. 사용자 입력 수신

질문 또는 계획을 받는다. 모호하면 한 줄로 "무엇을 검증할까요?" 질문.

### Step 2. advisor 에이전트 호출

Agent tool로 advisor 에이전트 호출. prompt에 다음 포함:
- 사용자 질문/계획 원문
- 맥락 (선행 작업, 관련 파일, 이미 알고 있는 것)
- 명시적 우선순위 (있으면)

advisor 에이전트가 내부에서:
- specialist 선정 (scaling rule: 단순 0~1개, 보통 2~3개, 복잡 4~5개)
- 병렬 호출 (단일 메시지)
- 결과 종합 → 권고 작성

### Step 3. 사용자 보고

advisor 에이전트의 응답을 그대로 사용자에게 전달. 추가 가공 없음.

## 핵심 원칙

- advisor는 **권고만** 한다. 코드를 수정하지 않는다.
- 결정은 **사용자가** 내린다.
- specialist는 **병렬로** 호출된다 (외부 표준).
- specialist 1개가 실패해도 나머지 결과로 진행한다.
- **max 1 round of specialist calls** — 같은 사안 재호출 금지.

## 언제 사용하는가

- 기술 스택 선택이 고민될 때
- 아키텍처 결정에 확신이 없을 때
- 새 라이브러리 도입을 고려할 때
- 리팩토링 방향이 여러 개일 때
- "이게 맞는 건가?" 싶을 때

## 언제 사용하지 않는가

- 답이 명확한 단순 질문 (advisor 호출 = 토큰 비용)
- 이미 결정된 사항의 재확인
- 코드 스타일·네이밍 (naming.md, coding.md 직접 참조)
- 단일 관점으로 끝나는 작업 (해당 specialist 직접 호출이 더 빠름)

## 다른 스킬과의 연동

| 스킬·에이전트 | 연동 지점 | 동작 |
|------|----------|------|
| implementation | Step 0.5 | "접근법 검증할까요? [Y/n]" → Y 시 advisor 호출 |
| harness-init | Step 6 | 스택 결정 전 — 직접 researcher 호출이 더 적합한 경우도 |
| commit | Step 7 | review와 병렬로 advisor 호출 (큰 결정 hit 시) |
| eval --deep | 2차 검증 | 4관점 병렬 (advisor와는 다른 관점) |

## 답변

답변은 한국어로.
