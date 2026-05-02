---
title: cluster 재생성 게이팅 — 본체 변경 시 전수 갱신 패턴 분리
domain: harness
problem: P5
solution-ref:
  - S5 — "서브에이전트 spawn 시 컨텍스트 < 500k 토큰 (부분)"
tags: [clusters, docs-ops, incremental-update, gating]
relates-to:
  - path: decisions/hn_downstream_amplification.md
    rel: extends
status: in-progress
created: 2026-05-02
updated: 2026-05-02
---

# cluster 재생성 게이팅

## 사전 준비
- 읽을 문서:
  - `docs/decisions/hn_downstream_amplification.md` `## 메모` (cluster 재생성 (c) 발견 근거)
  - `.claude/scripts/docs_ops.py` `cluster-update` 함수
  - `.claude/skills/commit/SKILL.md` Step 2.1 cluster-update 호출 시점
- 이전 산출물: amplification wave Phase 4-A — (c) v0.33.0 업그레이드 commit 1건에서 18/18 전 도메인 mtime 갱신 확인

## 목표
다운스트림이 `harness-upgrade`로 docs_ops.py 본체 변경을 fetch하면
**모든 cluster 파일이 mtime 갱신**되어 commit diff 노이즈 N비례로 증폭
되는 문제 해결. 신규 문서·이동·rename 시 영향 도메인만 갱신하는
incremental update + 본체 변경 트리거를 분리.

## 작업 목록

### 1. 후보 평가

**Acceptance Criteria**:
- [ ] Goal: incremental vs 본체 변경 구분 메커니즘 후보 평가 후 권장안 1개
  검증:
    review: skip
    tests: 없음
    실측: 본 WIP `## 결정 사항` 첨부
- [ ] 각 후보의 멱등성·정합성 평가

**후보 (초안)**:
- C1: cluster-update에 `--changed-only` 플래그 추가 — 변경된 도메인만 갱신
- C2: cluster 파일에 본체 hash 임베드. hash 일치 시 mtime 안 건드림
- C3: 본체 변경 시점에만 전수 트리거, 그 외엔 영향 도메인만 (일반 commit과 upgrade commit 분리)
- C4: cluster 파일 출력을 결정적(deterministic)으로 만들어 변경 없으면 mtime 갱신 안 됨 (현 동작이 비결정?)

### 2. 권장안 구현

**Acceptance Criteria**:
- [ ] Goal: 일반 commit 시 cluster mtime 갱신은 영향 도메인만 (도메인 N 환경에서 1~2건 ≤ 전수 N건)
  검증:
    review: review
    tests: pytest -m docs_ops
    실측: starter에서 단일 도메인 문서 신설 시 영향 cluster 1개만 갱신됨을 확인
- [ ] docs_ops.py cluster-update 게이팅 로직 추가
- [ ] 회귀 테스트 1개 이상

### 3. 다운스트림 영향 명시

**Acceptance Criteria**:
- [ ] Goal: MIGRATIONS.md에 다운스트림 영향 + 적용 방법 명시
  검증:
    review: self
    tests: 없음
    실측: harness-upgrade 시뮬
- [ ] 다운스트림 cluster 파일 양식 영향 분류

## 결정 사항
(후보 평가 후 채움)

## 메모

### baseline 출처
`docs/decisions/hn_downstream_amplification.md` `## 메모` 참조.

상시 N 비례 갱신 아님 — docs_ops.py 본체 변경 시(예: v0.33.0 업그레이드)에만
전수 mtime 갱신. 일반 commit에서는 0건. **결함은 본체 변경이 N비례 noise를
유발한다는 점**, 일반 시나리오는 이미 정상.
