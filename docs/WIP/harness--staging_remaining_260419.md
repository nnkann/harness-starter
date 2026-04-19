---
title: review staging 잔여 — S8 정밀화 + 5커밋 측정 + 폭증 게이트
domain: harness
tags: [staging, review, measurement]
relates-to:
  - path: ../harness/staging_followup_260419.md
    rel: extends
status: pending
created: 2026-04-19
---

# review staging 잔여

`harness--staging_followup`의 P1(S1 오탐 보정)·S6 완화는 처리 완료
(커밋 예정). 본 WIP는 잔여 P3·P4 + P2(측정).

## 잔여 작업

### P3. S8 export 검출 정밀화

현재 휴리스틱 (`grep -E '^[+-].*export'`) — 문자열·주석에도 잡힘.
언어별 시그니처 분리:
- TypeScript/JavaScript: `^export\s+(async\s+)?(class|function|interface|type|const|let|var|default)`
- Python: `^def\s+|^class\s+|^async\s+def\s+`
- Go: `^func\s+[A-Z]` (대문자 = export)

### P2. 5커밋 측정

다음 5번 커밋 후 측정:
- review 시간 평균 (deep/standard/micro/skip 분포)
- tool_uses 평균
- 입력 토큰 평균
- Stage별 빈도

목표: 평균 시간 60% 절감.

### P4. 폭증 차단 게이트 코드 강제 (장기)

pre-check이 신호 수 13 초과 시 경고. 1인 운영이면 후순위.

## 우선순위

P3: 의외 deep 사유 추적 (S8이 가장 많이 hit하는 신호)
P2: 단순화 후속 검증과 자연 누적
P4: 신호 추가 빈도 낮으면 보류
