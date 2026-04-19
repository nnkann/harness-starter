---
title: review·commit advisor 통합 — needs_advisor 자동 트리거
domain: harness
tags: [advisor, review, commit, integration]
relates-to:
  - path: ../harness/guardrails_followup_260419.md
    rel: extends
status: pending
created: 2026-04-19
---

# review·commit advisor 통합

`harness--guardrails_followup`에서 분리된 잔여. 단순화 작업 후속 검증
데이터(advisor 실제 호출 사례 1~2건) 누적 후 진행.

## 잔여 작업

### 1. review.md `needs_advisor: true` 필드

review가 diff 분석 후 "advisor 호출 필요" 판단.
출력 JSON에 `needs_advisor: true|false` 추가. 트리거 기준:
- 구조적 결정 (아키텍처·DB·API)
- 여러 선택지 중 하나 선택해야 하는 상황
- 규칙 신설·공개 API 변경
- 과거 incidents/와 유사 패턴

### 2. commit Step 7 advisor 병렬 호출

review의 `needs_advisor: true` hit 시 commit 스킬이 advisor를
review와 병렬로 호출. test-strategist와 같은 패턴 (2026-04-19 단순화
5단계).

응답 종합:
- review block + advisor recommendation → 차단·수정
- review ok + advisor recommendation → 권고만 표시
- 둘 다 ok → 그대로 진행

## 의존성

- staging 시스템(rules/staging.md) 안정 동작 확인
- advisor 자연 호출 사례 1~2건 누적 (single-source 사례 패턴)
- 단순화 작업 후속 검증 결과

## 우려

P0 단순화 후속이라 신호·트리거를 하나 더 추가하는 게 마찰 회수와
충돌. 실제 advisor 미호출이 문제가 됐던 케이스가 누적될 때 진행.
