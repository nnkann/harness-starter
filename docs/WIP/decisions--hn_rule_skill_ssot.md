---
title: 룰-스킬 중복 제거 — 룰 SSOT 강제 (Phase 5)
domain: harness
problem: P5
solution-ref:
  - S5 — "원인이 특정되면 해당 항목 제거 + 실측 재측정 (부분)"
tags: [rules, skills, ssot, duplication]
relates-to:
  - path: harness/hn_harness_efficiency_overhaul.md
    rel: caused-by
status: pending
created: 2026-05-02
---

# 룰-스킬 중복 제거

## 사전 준비
- 읽을 문서: `.claude/rules/*.md` (12개), `.claude/skills/*/SKILL.md` (13개)
- 이전 산출물: hn_harness_efficiency_overhaul.md (룰·에이전트 메타데이터 추가됨)
- 자기증명 사례: hn_upstream_anomalies.md Phase 1 — install-starter-hooks.sh와 pre_commit_check.py의 시크릿 면제 패턴이 별개 SSOT라 한쪽 갱신 시 다른 쪽 동기화 누락

## 목표
룰(`.claude/rules/*.md`)을 SSOT로 강제. 스킬 step에서 룰 본문 재진술 금지,
진입점·link만. 룰 갱신 시 스킬 동기화 누락 사고 방지.

## 작업 목록

### 1. 룰-스킬 중복 매핑 (선행 측정)

**Acceptance Criteria**:
- [ ] Goal: 어느 스킬이 어느 룰을 재진술하는지 전수 매핑
  검증:
    review: skip
    tests: 없음 (측정 작업)
    실측: 매핑 결과 본 WIP `## 메모` 첨부
- [ ] 12개 룰 × 13개 스킬 매트릭스
- [ ] 재진술 빈도 높은 top 10 추출

### 2. commit/SKILL.md 1단계 적용 (실측 후 점진 확대)

**Acceptance Criteria**:
- [ ] Goal: commit/SKILL.md에서 룰 본문 재진술 제거 → SSOT link만
  검증:
    review: review
    tests: pytest -m stage
    실측: commit 흐름 동작 회귀 없음 확인
- [ ] commit/SKILL.md 한정 1단계 적용
- [ ] 효과 측정 (스킬 분량 감소·동기화 누락 발생 빈도)

### 3. 점진 확대 (실측 사고율 < 5% 시)

**Acceptance Criteria**:
- [ ] Goal: implementation·harness-upgrade·eval·write-doc 순차 적용
  검증:
    review: review
    tests: 없음 (운용 검증)
    실측: 6개월 사고율 추적
- [ ] 1단계 완료 6개월 후 사고율 측정 → 통과 시 다음 스킬

## 결정 사항
(작업하면서 채움)

## 메모
- 본 wave는 v0.29.1 hn_harness_efficiency_overhaul.md에서 분리됨
- 폭주 위험 (advisor 사전 보강에서 지적): 1단계로 끝나지 않고 N단계 폭주 가능 — incremental 정리도 옵션
- 자기증명 사례 발생: install-starter-hooks.sh ↔ pre_commit_check.py S1_LINE_EXEMPT 동기화 누락 (이미 발현됨)
