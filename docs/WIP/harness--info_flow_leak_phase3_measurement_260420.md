---
title: 정보 흐름 누수 해소 Phase 3 — 실측 검증
domain: harness
tags: [audit, information-flow, measurement, phase3]
relates-to:
  - path: harness/info_flow_leak_audit_260420.md
    rel: caused-by
status: pending
created: 2026-04-20
---

# Phase 3 — 정보 흐름 누수 해소 실측 검증

Phase 1·2가 e0f33e4 커밋으로 적용됨. 효과를 실측 데이터로 검증한다.

## 측정 항목

### Phase 1 효과
- **eval --deep tool_uses 총합**: 현재 대비 70% 이하 목표
- **commit → test-strategist tool_uses**: 현재 대비 50% 이하 목표
- **review tool_uses 한도 위반 빈도**: 감소 확인

### Phase 2 효과
- **docs-manager 호출 시 tool_uses**: 5개 호출자(commit·upgrade·init·adopt·write-doc)
  하위 호출 비용 감소 확인

## 측정 방법

각 커밋마다 서브에이전트 응답의 `<usage>` 블록에서 `tool_uses` 추출.
세션 종료 시 누적해 효과 평가.

기준선 (해소 전):
- ec85c79 review: 6 tool_uses
- 다운스트림 c976255: micro인데 6 tool_uses
- 다운스트림 d1ef30d: deep인데 4 tool_uses (반대 방향 위반)

검증 (해소 후):
- e0f33e4 review: 5 tool_uses ✅ (한도 정확 준수, 첫 데이터)

## 데이터 수집

| 커밋 SHA | stage | tool_uses | 비고 |
|----------|-------|-----------|------|
| e0f33e4 | deep | 5 | Phase 1·2 적용 첫 측정 |
| | | | |

각 커밋마다 표에 추가. 5~10건 누적 후 통계 평가.

## 평가 기준

성공:
- 한도 위반 0건 또는 1건 이하
- 평균 tool_uses가 한도의 60~80% 범위 (한도 마진 적정)
- 동일 stage 내 tool_uses 분산 작음

실패 (Phase 1·2 재설계 필요):
- 한도 위반 반복 (3회 이상)
- 평균 tool_uses가 여전히 한도 100% 근처
- 메타 본문 박기·docs-manager 규약이 무시되는 패턴 발견

## 작업 흐름

이 WIP는 단발 작업이 아니라 **여러 세션에 걸친 누적 측정**. 매 세션
종료 시 또는 사용자가 평가 요청 시 데이터 행 추가.

5~10 데이터 누적 → 평가 → 본 문서 completed로 이동.
