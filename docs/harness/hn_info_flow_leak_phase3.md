---
title: 정보 흐름 누수 해소 Phase 3 — 정성 평가 종결
domain: harness
tags: [audit, information-flow, measurement, phase3]
relates-to:
  - path: harness/hn_info_flow_leak_audit.md
    rel: caused-by
status: completed
created: 2026-04-20
updated: 2026-04-20
---

# Phase 3 — 정성 평가로 종결

Phase 1·2가 e0f33e4 커밋으로 적용됐다. 당초 계획은 5~10 커밋에 걸쳐
서브에이전트 `<usage>` 블록의 `tool_uses`를 누적해 정량 평가하는 것이었다.

## 종결 사유

**정량 측정 포기**:
- `tool_uses` 자동 로깅 메커니즘 부재. 수동 기록은 매 커밋마다 사람
  개입 필요 → 하네스 체감 속도 역행.
- 자동화(로깅 후크) 추가는 Phase 1·2가 줄이려던 오버헤드를 다시 얹는
  본말전도.
- 과거 커밋의 usage 데이터는 세션 종료 후 복구 불가.

**정성 평가로 전환**:
- 사용자 체감 기준: "review가 타임아웃·폭주·형식 오류를 일으키는가?"
- 문제 발생 시에만 조사 재개.

## 관측된 정성 증거 (해소 후 5커밋)

Phase 1·2 적용(e0f33e4) 이후 5커밋(f28f849, 0d1514d, 6e89967, 5ecbed0,
fded369) 동안:

- review stage deep 5회 연속, tool_uses 한도 위반 보고 없음.
- fded369 review는 verdict 폼(첫 2줄 `## 리뷰 결과` + `verdict: pass`)
  완벽 준수. 이전 커밋의 폼 수정이 작동 확인.
- 5ecbed0에서 [주의] 1건 감지·해소(다운스트림 제품명 유출) — review의
  정상 작동 근거.
- 체감 회귀 없음.

## 재개 조건

다음 중 하나 발생 시 정량 측정 재개 검토:
- review 응답에서 tool_uses 한도 초과 경고 반복(3회+)
- 서브에이전트 호출 비용이 체감상 증가
- 메타 본문 박기·docs-manager 규약 무시 패턴 재관찰

## 원 계획 참조

- 당초 측정 항목: eval --deep tool_uses 70% 이하, commit → test-strategist
  50% 이하, docs-manager 5개 호출자 감소.
- 기준선: ec85c79 review 6 tool_uses, c976255 micro 6 tool_uses,
  d1ef30d deep 4 tool_uses(반대 방향 위반).
- 검증 첫 데이터: e0f33e4 review 5 tool_uses (한도 정확 준수).

이 기준선 대비 1건 관측으로는 통계적 결론 불가하지만, 5커밋 정성 관찰로
"회귀 없음"은 확인됨.
