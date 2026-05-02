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
status: completed
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
- [x] Goal: 후보 3~4개에 대해 trade-off 명시 후 권장안 1개
  검증:
    review: skip
    tests: 없음 (의사결정)
    실측: 본 WIP `## 결정 사항` 첨부
- [x] 각 후보의 cluster 설계 의도 위반 여부 평가
- [x] cluster scan skip vs WIP 임시 등록 vs cluster 본문에 in-progress 섹션 등 trade-off

**후보 (초안, advisor 또는 단독 판단으로 확장)**:
- B1: WIP 시나리오 감지 시 cluster scan skip (fast path) — keyword grep만
- B2: cluster 본문에 `## in-progress` 섹션 추가, WIP 파일 경로 자동 등록
- B3: WIP는 그대로, doc-finder fast scan을 1단계로 격상해 cluster scan 보완
- B4: 폐기 (현 설계 유지) — 비용은 작아서 (b) 자체 우선순위 4로 강등

### 2. 권장안 구현

**Acceptance Criteria** (좁힌 Goal — 결정 사항 참조):
- [x] Goal: starter cluster 본문에 진행 중 WIP 섹션이 자동 추가되고, WIP 파일 변경 시 영향 cluster만 mtime 갱신
  검증:
    review: review
    tests: pytest -m docs_ops
    실측: starter 2 도메인 환경에서 cluster 본문에 `## 진행 중 (WIP)` 섹션 + WIP 4개 등록 확인
- [x] cluster-update에 WIP 수집 로직 추가 (B2 변형)
- [x] 회귀 테스트 1개 이상

**구현 결과** (2026-05-02):
- `docs_ops.py:cmd_cluster_update`이 `WIP in parts_set`이면 `wip_list`에 별도 수집 (`detect_abbr` 라우팅 태그 통과 재사용)
- cluster 본문에 `## 문서` 섹션 뒤 `## 진행 중 (WIP)` 섹션 추가, 비어 있으면 섹션 자체 생략
- C4 결정적 비교 로직 그대로 작동 — WIP 변경 시 영향 도메인 cluster만 mtime 갱신
- 회귀 테스트 1개 추가 — `TestClusterUpdateGating::test_wip_appears_in_cluster`
- 실측: starter 호출 후 `docs/clusters/harness.md`에 4 WIP 모두 등록, dead-link 검사 `pre_check_passed: true`
- pytest `-m docs_ops` 25/25 통과 (24 + 1)

### 3. 다운스트림 영향 명시

**Acceptance Criteria**:
- [x] Goal: MIGRATIONS.md에 다운스트림 영향 + 적용 방법 명시 ✅
  검증:
    review: self
    tests: 없음
    실측: harness-upgrade 시뮬
- [x] cluster 파일 양식 변경 여부 분류

**다운스트림 영향 분류** (2026-05-02):
- **양식 변경**: 추가만 — `## 진행 중 (WIP)` 섹션 신규. 기존 `## 문서` 섹션·frontmatter 무변경
- **이행**: 자동. 다운스트림은 `cluster-update` 다음 호출 시 WIP 있는 도메인 cluster만 1회 갱신 후 안정. WIP 없는 도메인은 본문 동일 → C4 skip 작동, 갱신 0
- **하위 호환**: 다운스트림이 cluster를 grep으로 읽는 도구가 있으면 `## 진행 중 (WIP)` 섹션이 추가로 hit됨. 기존 hit 행동에 영향 없음 (추가만)
- **MIGRATIONS.md 신규 섹션**: commit Step 4 version bump가 자동 처리

## 결정 사항

### 2026-05-02 — 후보 평가 (단독 판단)

**Trade-off**:

| 후보 | cluster 설계 의도 | C4(직전 wave)와 정합 | 가시성 효과 | 다운스트림 영향 | 채택 |
|------|------------------|--------------------|----------|---------------|-----|
| B1 cluster scan skip + WIP 별도 ls | 의도 유지 | 정합 | 사용자·에이전트가 두 진입점 알아야 함 | 가이드 추가만 | ❌ |
| **B2 변형** cluster에 `## 진행 중 (WIP)` 섹션 추가 | 의도 확장 (cluster = 도메인 진입점) | 정합 — `cluster-update` 결정적 출력 유지 | 단일 진입점에 WIP 노출 | 양식 추가, 기존 `## 문서` 무변경 | ✅ |
| B3 doc-finder fast scan 격상 | 별 메커니즘 도입 | 무관 | doc-finder 호출 늘어남 (역효과) | doc-finder 동작 변경 | ❌ |
| B4 폐기 | 의도 유지 | — | 0 | 0 | ❌ |

**채택: B2 변형**

**근거**:
1. **단일 진입점 유지** — 사용자·에이전트가 `clusters/{domain}.md` 한 곳에서 도메인의 completed + in-progress 모두 발견. B1처럼 `docs/WIP/` 별도 ls 가이드를 학습할 필요 없음
2. **C4와 정합** — `cluster-update`가 결정적 출력 + WIP도 수집 대상에 추가만 하면 됨. 새 WIP 생성 시 영향 도메인 cluster만 mtime 갱신, 기존 `## 문서` 섹션 무변경 → 다른 도메인 noise 0
3. **cluster 설계 의도 확장** — 원래 docs.md "WIP는 cluster 미포함" 규칙은 "completed가 아닌 것을 정식 목록에 끼우면 noise"라는 우려. 별 섹션(`## 진행 중 (WIP)`)으로 분리하면 이 우려 해소
4. **다운스트림 자동 이행** — cluster 첫 갱신 시 WIP 섹션 자동 추가. 기존 `## 문서` 본문 동일 → C4 skip 로직 작동, 본문이 진짜 바뀐 경우만 1회 갱신 후 안정

**구현 방안**:
1. `cmd_cluster_update`에서 abbr별로 WIP 파일도 수집 (현재는 `WIP in parts_set` 시 continue)
2. WIP 수집 시 라우팅 태그(`{대상폴더}--`) 통과 + abbr 매칭 (직교 파싱은 기존 `detect_abbr` 재사용)
3. cluster 본문에 `## 문서` 섹션 뒤 `## 진행 중 (WIP)` 섹션 추가, 비어 있으면 섹션 자체 생략
4. C4 결정적 비교 로직은 그대로 — 본문이 동일하면 skip

**반영 위치**: `.claude/scripts/docs_ops.py` `cmd_cluster_update`

**AC Goal 측정 가능 형태로 좁힘**:
- 원 Goal "cluster scan 비용 ≥80% 감소"는 baseline이 다운스트림 N=18 환경(5.6s) — starter cluster 2개로는 재현 불가
- 좁힌 Goal: "starter cluster 본문에 진행 중 WIP 섹션이 자동 추가되고, WIP 파일 변경 시 영향 cluster만 mtime 갱신". 자동 검증 가능

**CPS 갱신**: 없음 — Solution 메커니즘의 가시성 개선, 충족 기준 무변경

## 메모

### baseline 출처
`docs/decisions/hn_downstream_amplification.md` `## 메모` 참조 — 3환경
(starter / 다운스트림 N=1 / 다운스트림 N=2) 중 2개에서 (b) 명시 확인.

WIP 비중 큰 환경일수록 손해 — 활동량 많은 다운스트림에서 더 큰 비용.
