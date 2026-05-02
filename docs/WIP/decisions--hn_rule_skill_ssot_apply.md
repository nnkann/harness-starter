---
title: 룰-스킬 SSOT 적용 — Phase 1 commit/SKILL.md
domain: harness
problem: P5
solution-ref:
  - S5 — "원인이 특정되면 해당 항목 제거 + 실측 재측정 (부분)"
tags: [rules, skills, ssot, duplication, apply]
relates-to:
  - path: decisions/hn_rule_skill_ssot.md
    rel: caused-by
status: pending
created: 2026-05-02
---

# 룰-스킬 SSOT 적용 (Task 2 wave)

## 사전 준비
- 읽을 문서: `docs/decisions/hn_rule_skill_ssot.md` (Task 1 측정 결과)
- 핫스팟 1순위: commit × staging (Stage 결정 우선순위·Stage별 행동 본문 재진술)

## 목표
commit/SKILL.md Step 7의 staging.md 본문 재진술을 한 줄 link로 단순화.
staging.md 갱신 시 SKILL.md 동기화 누락 위험 제거.

## 작업

**Acceptance Criteria**:
- [x] Goal: commit/SKILL.md Step 7에서 staging.md 본문 재진술 제거 → SSOT link로 단순화
  검증:
    review: review
    tests: pytest -m stage
    실측: commit 흐름 회귀 없음 (자기증명 — 본 commit이 같은 흐름 사용)
- [x] Stage 결정 우선순위 박스 → staging.md 참조 한 줄
- [x] Stage별 행동 요약 → staging.md 참조 한 줄
- [x] staging.md 본 변경 결과 정합성 확인

## 결정 사항

### 적용 대상

commit/SKILL.md Step 7 두 영역:

1. **Stage 결정 우선순위** (529~541줄): 4단계 박스 + 충돌 처리 본문 → `staging.md` "## Stage 결정" 참조 한 줄
2. **Stage별 행동** (543~554줄): 4 stage 요약 + 거대 커밋 정책 → `staging.md` "## Stage" 참조 한 줄

### 비대상 (유지)

- 응답 처리 분기 (block/warn/pass) — staging.md에 없는 commit 스킬 고유 로직
- `extract_review_verdict.py` 호출 — commit 스킬 고유 흐름

### 효과 측정

- commit/SKILL.md 줄 수 감소 (~30줄 → ~5줄)
- staging.md 갱신 시 동기화 누락 위험 제거
- 다음 세션부터 6 commit 누적 후 review 분기 동작 정상 여부 추적

## 메모
- Phase 1만 본 wave. 핫스팟 2~5순위(implementation×docs, write-doc×docs/naming, harness-adopt×docs/naming)는 별 wave 후속
- 본 wave는 자기증명 — 본 commit이 commit 스킬을 사용하므로 흐름 회귀가 즉시 노출됨
