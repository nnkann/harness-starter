---
title: review·commit advisor 통합 — needs_advisor 자동 트리거
domain: harness
tags: [advisor, review, commit, integration]
relates-to:
  - path: ../harness/hn_guardrails_followup.md
    rel: extends
status: abandoned
created: 2026-04-19
updated: 2026-04-19
---

# review·commit advisor 통합

## abandoned 사유 (2026-04-19)

본 WIP는 진행하지 않기로 결정. 3가지 이유:

1. **staging 신호와 70% 이상 겹침 — staging.md 자체 규칙 위반**
   - staging.md "신호 추가 4질문" 1번: "기존 신호와 70% 이상 겹치면 추가
     금지 (sub-rule로 흡수)"
   - `needs_advisor` 트리거 기준(구조적 결정·규칙 신설·공개 API)은
     이미 S2(핵심설정)·S8(공유모듈)·S9(critical)·S14(마이그레이션)이
     자동 deep stage로 처리. 같은 영역.
   - 별도 신호 만들면 분기 폭증 게이트 위반.

2. **review와 advisor의 분담 모호 — 중복 호출 위험**
   - staging deep stage에서 review가 이미 "기존 결정과의 정합성"·
     "3관점 독립 검증"(회귀·계약·스코프) 수행.
   - advisor가 추가로 줄 가치가 명확하지 않음. 두 에이전트가 같은
     diff에 같은 카테고리를 보면 토큰·시간 낭비.

3. **사용자 직접 호출 가능 — 자동화 가치 약함**
   - `/advisor` 슬래시 명령 존재.
   - test-strategist는 사람이 부르기 어려워 자동화한 거지만, advisor는
     "큰 결정 검증해" 같은 의식적 트리거가 자연스러운 명령.
   - 자동 호출은 사용자의 결정 권한을 빼앗는 패턴.

## 회수된 부분

`guardrails_followup`의 3개 항목 중:
- "허위 후속 감지" → 처리됨 (커밋 7a63d53, review.md 카테고리 신설)
- "needs_advisor 필드" → abandoned (위 사유)
- "commit Step 7 advisor 병렬 호출" → abandoned (위 사유)

## 재검토 트리거

다음 중 하나가 발생하면 재평가:
- staging deep stage가 잡지 못한 큰 결정 사고 발생 (incidents/ 추가)
- 사용자가 "advisor를 자동으로 불러줬으면" 명시 요청
- Anthropic 공식에서 multi-agent orchestration 모범 패턴 변경

---

## 원본 (참고)

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
