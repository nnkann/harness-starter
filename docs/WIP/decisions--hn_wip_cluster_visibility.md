---
title: WIP cluster scan 가시성 — in-progress 도달 경로 추가
domain: harness
problem: P5
solution-ref:
  - S5 — "서브에이전트 spawn 시 컨텍스트 < 500k 토큰 (부분)"
tags: [clusters, wip, doc-finder, fast-path]
relates-to:
  - path: decisions/hn_downstream_amplification.md
    rel: extends
status: in-progress
created: 2026-05-02
updated: 2026-05-02
---

# WIP cluster scan 가시성

## 사전 준비
- 읽을 문서:
  - `docs/decisions/hn_downstream_amplification.md` `## 메모` (3환경 baseline, (b) 발견 근거)
  - `.claude/rules/docs.md` "## clusters/" + "WIP는 cluster 미포함" 설계 의도
  - `.claude/scripts/docs_ops.py` cluster-update 로직
  - `.claude/skills/implementation/SKILL.md` Step 0 SSOT 3단계 (cluster scan 호출 위치)
- 이전 산출물: amplification wave Phase 4-A — (b) "WIP cluster miss" 3환경 중 2개 발현 입증

## 목표
in-progress WIP가 cluster scan 단독으로 발견되지 않아 keyword grep 폴백
비용이 발생하는 문제 해결. 현 설계("WIP는 cluster 미포함" — completed 후
이동 시 추가)는 유지하되, 사용자·에이전트가 "현재 진행 중 작업"을 찾을
때 cluster scan 비용 0이거나 결과 hit 양산 방향으로 fast path 추가.

## 작업 목록

### 1. 후보 평가 (advisor 또는 단독 판단)

**Acceptance Criteria**:
- [ ] Goal: 후보 3~4개에 대해 trade-off 명시 후 권장안 1개
  검증:
    review: skip
    tests: 없음 (의사결정)
    실측: 본 WIP `## 결정 사항` 첨부
- [ ] 각 후보의 cluster 설계 의도 위반 여부 평가
- [ ] cluster scan skip vs WIP 임시 등록 vs cluster 본문에 in-progress 섹션 등 trade-off

**후보 (초안, advisor 또는 단독 판단으로 확장)**:
- B1: WIP 시나리오 감지 시 cluster scan skip (fast path) — keyword grep만
- B2: cluster 본문에 `## in-progress` 섹션 추가, WIP 파일 경로 자동 등록
- B3: WIP는 그대로, doc-finder fast scan을 1단계로 격상해 cluster scan 보완
- B4: 폐기 (현 설계 유지) — 비용은 작아서 (b) 자체 우선순위 4로 강등

### 2. 권장안 구현

**Acceptance Criteria**:
- [ ] Goal: WIP 시나리오에서 SSOT 3단계 cluster scan 비용 ≥80% 감소
  검증:
    review: review
    tests: pytest -m gate
    실측: amplification baseline의 cluster scan 5.6s가 ≤1s로 단축됨을 starter에서 재현 측정
- [ ] cluster scan skip 또는 WIP 등록 메커니즘 코드 변경
- [ ] 회귀 테스트 1개 이상

### 3. 다운스트림 영향 명시

**Acceptance Criteria**:
- [ ] Goal: MIGRATIONS.md에 다운스트림 영향 + 적용 방법 명시
  검증:
    review: self
    tests: 없음
    실측: harness-upgrade 시뮬
- [ ] cluster 파일 양식 변경 여부 분류

## 결정 사항
(advisor 또는 단독 판단 후 채움)

## 메모

### baseline 출처
`docs/decisions/hn_downstream_amplification.md` `## 메모` 참조 — 3환경
(starter / 다운스트림 N=1 / 다운스트림 N=2) 중 2개에서 (b) 명시 확인.

WIP 비중 큰 환경일수록 손해 — 활동량 많은 다운스트림에서 더 큰 비용.
