---
title: LLM 실수 방지 가드레일 후속 — review needs_advisor·허위 후속 감지·commit advisor 통합
domain: harness
tags: [guardrails, advisor, review, commit]
relates-to:
  - path: ../harness/llm_mistake_guardrails_260418.md
    rel: extends
status: pending
created: 2026-04-19
---

# LLM 실수 방지 가드레일 후속

원본 WIP `harness--llm_mistake_guardrails_260418.md`의 잔여 항목.

## 완료된 것 (원본 WIP 참조)

- P0 internal-first.md 신설 (커밋 26b72c6)
- P0 no-speculation.md 신설 (26b72c6)
- P1 pre-commit-check.sh 연속수정 임계값 2/3 (26b72c6)
- P0 advisor 에이전트 신설 + specialist 풀 6개 (e52234f)
- P1 self-verify.md에 test-strategist 자동 트리거 (e52234f)

## 잔여 작업

### 1. review.md needs_advisor 기준 (P1)

원본 WIP §"advisor·review 동급 병렬 배치":
- review가 diff 분석 후 "advisor 호출 필요" 판단 기준
- 출력 JSON에 `needs_advisor: true` 필드 추가 검토
- commit 스킬이 이 필드 보고 advisor 추가 호출

### 2. review.md 허위 후속 감지 (P1)

원본 WIP §"허위 후속 감지":
- WIP/커밋 메시지에 "재검토 필요", "추후 확인", "검증 예정" 등 모호한
  후속 패턴 감지
- 구체 근거 없으면 차단·경고

### 3. commit Step 7 advisor 자동 호출 통합 (P0 미완)

원본 WIP §"commit 스킬 Step 6·7 흐름 재설계":
- 현재 Step 7은 review만 호출
- advisor 호출 트리거 (구조적 결정·선행 실패·여러 선택지·규칙 신설·공개 API)
  hit 시 review와 병렬 호출
- 응답 종합 규칙 (block/recommendation 결합)

## 우선순위

P0~P1. staging 시스템(v1.6.0) 도입으로 일부 자연 흡수됐으니 재평가 필요:
- needs_advisor와 staging의 신호 시스템이 어떻게 연동되는지
- staging의 deep stage가 advisor 자동 호출까지 트리거할지

## 의존성

- staging 시스템(rules/staging.md) 안정화 후 진행 권장
- advisor 에이전트 실제 호출 사례 1~2건 누적 후 패턴 확정

## 검증

- 큰 결정 케이스에서 review + advisor 병렬 호출되는지
- 허위 후속 패턴이 실제 차단되는지
