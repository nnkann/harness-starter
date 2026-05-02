---
title: CPS Problem 인용 빈도 검토 — P1·P3·P4·P6 정체 의심 판정
domain: harness
problem: P5
solution-ref:
  - S5 — "원인이 특정되면 해당 항목 제거 + 실측 재측정 (부분)"
tags: [cps, problem, inflation, eval-integrity]
relates-to:
  - path: decisions/hn_eval_cps_integrity.md
    rel: caused-by
status: completed
created: 2026-05-02
---

# CPS Problem 인용 빈도 검토

`eval_cps_integrity.py`가 발견한 P1·P3·P4·P6 frontmatter 인용 0건
(v0.30.0 실측). 정의 자체 사용 안 됨 의심에 대한 사용자 판단 검토.

## 검토 방법

1. CPS 본문 Read — 6 Problem 정의 + 승격 상태 확인
2. frontmatter `problem:` 분포 grep
3. **본문 인용** grep (frontmatter는 인용 패턴 1개일 뿐 — 진정한 활용 측정엔 본문도 봐야)
4. 본문 P# 동음이의 disambiguation (자체 우선순위 라벨 vs CPS Problem)

## 결과

| Problem | fm 인용 | 본문 인용 (CPS 의미) | 판정 |
|---------|---------|---------|------|
| P1 LLM 추측 수정 반복 | 0 | 3건 (advisor·handoff·skill_audit) | **활용 중** — frontmatter 패턴만 누락 |
| P2 review 과잉 비용 | 3 | 다수 | 활용 중 |
| P3 다운스트림 사일런트 페일 | 0 | 0 (자체 우선순위 라벨 P3와 동음이의) | **정체 — 다운스트림 영향이라 starter엔 안 잡힘** |
| P4 광역 hook 매처 fragility | 0 | 0 (자체 라벨) | **정체 — 다운스트림 영향 동일** |
| P5 MCP·플러그인 컨텍스트 팽창 | 4 | 다수 | 활용 중 |
| P6 검증망 스킵 패턴 | 0 | 1건 (verification_pipeline S6 충족) | 희소하지만 **활용 중** |

## 결정 사항

- **P1·P6**: 폐기 안 함. 본문 인용으로 활용 확인. 향후 작업이 P1·P6 연관이면
  frontmatter `problem:` 명시 권고 (작성 패턴 표준화 — 본 결정의 부수 효과)
- **P3·P4 유지**: 인용 0건이지만 **다운스트림 사안**. starter 단독으론
  안 잡혀도 다운스트림에서 핵심. 폐기 시기상조
- **CPS 본문 변경 없음** — 6 Problem 모두 그대로 유지
- **eval_cps_integrity proxy 한계 발견 → 즉시 보강 (본 wave 동시 처리)**:
  frontmatter-only 카운트는 본문 인용을 못 잡음. 본 검토 직후 즉시
  `eval_cps_integrity.py`에 본문 grep + disambiguation 휴리스틱 추가.
  - `CPS_REF_PATTERNS`: "CPS 연결: P#", "P# (...)", "P# →", "P# 충족" 등 강한 신호
  - `SELF_LABEL_PATTERNS`: "**P#**:", "### P#." 자체 우선순위 라벨 제외
  - 검증 결과 (보강 후 실측): P1 0→4, P2 2→8, P5 4→9, P6 0→2.
    P3·P4만 진짜 정체로 남음 — 본 검토 수동 결론과 100% 일치
  - 자체 라벨 false positive 0건 (`**P3**:`·`### P3.` 비매칭 검증 통과)

## 메모

- 검토 작업 자체는 작음 — Read + grep + disambiguation 30분 이내
- v0.30.0 발견 시점 신선도 활용 — 데이터 사라지기 전 처리
- 동음이의 의심 케이스는 hn_contamination_followup·hn_generic_contamination_protection·
  hn_staging_remaining에서 P1~P4를 자체 우선순위 라벨로 사용. 향후 신규
  문서는 자체 라벨에 P# 형식 회피 권고 (혼동 방지) — 강제 안 함, 단지 가이드
- CPS 갱신: 없음
