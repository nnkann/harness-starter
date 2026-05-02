---
title: 다운스트림 증폭 완화 — 도메인 수 비례 비용 제거
domain: harness
problem: P5
solution-ref:
  - S5 — "서브에이전트 spawn 시 컨텍스트 < 500k 토큰 (부분)"
tags: [downstream, amplification, scale-gating, doc-finder]
relates-to:
  - path: harness/hn_harness_efficiency_overhaul.md
    rel: caused-by
status: pending
created: 2026-05-02
---

# 다운스트림 증폭 완화

## 사전 준비
- 읽을 문서: `.claude/skills/implementation/SKILL.md` Step 0.3·0.8, `.claude/scripts/docs_ops.py` (clusters)
- 이전 산출물: hn_harness_efficiency_overhaul.md Phase 2-A v0.29.1 (외형 metric 폐기·AC + CPS 도입)

## 목표
다운스트림에서 도메인·CPS·문서 수 증가에 step 비용이 비선형 증가하는 문제 해결.
실측 baseline 확보 후 단계 적용.

## 작업 목록

### 1. Phase 4-A — baseline trace 수집 (선행, 코드 변경 0)

**Acceptance Criteria**:
- [ ] Goal: 다운스트림 1개 프로젝트(예: Issen)에서 동일 작업 1건의 tool call·시간 trace 수집해 baseline 확보
  검증:
    review: skip
    tests: 없음 (측정 작업)
    실측: trace 결과 본 WIP `## 메모` 첨부
- [ ] doc-finder fast scan tool call 수 측정
- [ ] SSOT 3단계 탐색 시간 측정
- [ ] clusters 갱신 빈도 측정
- [ ] 도메인 수에 실제로 비례하는지 확인 (다른 곳이 진짜 병목이면 방향 재설계)

### 2. Phase 4-B — 게이팅 코드 적용 (Phase 4-A 결과 후)

**Acceptance Criteria**:
- [ ] Goal: 다운스트림 도메인 5~10개 환경에서 implementation 진입 비용이 starter 환경 대비 1.5x 이내
  검증:
    review: review-deep
    tests: pytest -m stage
    실측: Phase 4-A baseline 대비 절감 측정
- [ ] meta 도메인 단독 변경 시 doc-finder·SSOT 탐색 skip
- [ ] clusters 갱신은 새 문서 생성·이동 시에만 (commit 매번 X)
- [ ] domain 등급 (critical/normal/meta) 활용 — staging.md 기존 구조 재사용

## 결정 사항
(작업하면서 채움)

## 메모
- 본 wave는 v0.29.1 hn_harness_efficiency_overhaul.md에서 분리됨
- 측정 게이트 필수 — 추측 기반 적용 금지
- starter 단독 측정으로는 효과 검증 어려움. 다운스트림 1개 이상 필수
