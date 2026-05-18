---
title: kickoff Solutions 표 ↔ 실제 구현 dead link 점검
domain: harness
problem: P11
s: [S11]
tags: [cps-implementation-drift, kickoff-audit]
relates-to:
  - path: docs/decisions/hn_claude_dir_audit.md
    rel: caused-by
status: in-progress
created: 2026-05-18
---

# kickoff Solutions 표 ↔ 실제 구현 dead link 점검

## Goal

codebase-analyst 사각지대 — kickoff Solutions 표의 "해결 기준" 컬럼이
실제 구현(rules·skills·agents·scripts)에 매핑되는지 미확인. drift 잠복.

**Acceptance Criteria**:
- [ ] Goal: S11 충족 — Solutions 11개(S1~S9, S10, S11, S12)의 "해결 기준" 컬럼 텍스트가 실제 구현 위치(파일 경로·함수명)에 매핑되는지 grep·Read로 검증. dead reference 0건 확인
  검증:
    tests: 없음
    실측: 각 S#에 대해 (a) 해결 기준이 구체 검증 가능 명령·조건인가 (b) 그 기준이 어느 코드/rule에서 강제되는가 추적. 미연결 S# 발견 시 박제
- [ ] Solutions 11개 × 구현 매핑 표 작성
- [ ] dead reference 또는 모호한 기준 발견 시 별 wave 후보 분리

## 메모

- 본 wave가 P11 정의 직격 — Solutions 박제 위치 분산(kickoff 표 + 본문 + 실제 구현)에서 dead link 잠복 가능성
- codebase-analyst가 사각지대로 명시한 영역
