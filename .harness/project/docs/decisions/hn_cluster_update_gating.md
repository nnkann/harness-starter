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
status: completed
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
- [x] Goal: incremental vs 본체 변경 구분 메커니즘 후보 평가 후 권장안 1개
  검증:
    review: skip
    tests: 없음
    실측: 본 WIP `## 결정 사항` 첨부
- [x] 각 후보의 멱등성·정합성 평가

**후보 (초안)**:
- C1: cluster-update에 `--changed-only` 플래그 추가 — 변경된 도메인만 갱신
- C2: cluster 파일에 본체 hash 임베드. hash 일치 시 mtime 안 건드림
- C3: 본체 변경 시점에만 전수 트리거, 그 외엔 영향 도메인만 (일반 commit과 upgrade commit 분리)
- C4: cluster 파일 출력을 결정적(deterministic)으로 만들어 변경 없으면 mtime 갱신 안 됨 (현 동작이 비결정?)

### 2. 권장안 구현

**Acceptance Criteria**:
- [x] Goal: 일반 commit 시 cluster mtime 갱신은 영향 도메인만 (도메인 N 환경에서 1~2건 ≤ 전수 N건)
  검증:
    review: review
    tests: pytest -m docs_ops
    실측: starter에서 단일 도메인 문서 신설 시 영향 cluster 1개만 갱신됨을 확인
- [x] docs_ops.py cluster-update 게이팅 로직 추가 ✅
- [x] 회귀 테스트 1개 이상

**구현 결과** (2026-05-02):
- `docs_ops.py:cmd_cluster_update` C4 채택 — 기존 파일의 `updated:` 값 추출·재사용해 본문 비교, 동일하면 `write_text` skip
- 회귀 테스트 2개 추가 — `TestClusterUpdateGating::test_idempotent_skip`, `test_only_affected_domain_updates`
- 실측: starter 2 cluster 환경에서 2회 호출 → skip 2/2, mtime 무변경 확인
- 단일 cluster stale 시 영향 cluster만 mtime 갱신, 비영향 cluster mtime 무변경 확인
- pytest `-m docs_ops` 24/24 통과 (기존 22 + 신규 2)

### 3. 다운스트림 영향 명시

**Acceptance Criteria**:
- [x] Goal: MIGRATIONS.md에 다운스트림 영향 + 적용 방법 명시 ✅
  검증:
    review: self
    tests: 없음
    실측: harness-upgrade 시뮬
- [x] 다운스트림 cluster 파일 양식 영향 분류

**다운스트림 영향 분류** (2026-05-02):
- **양식 변경**: 없음. cluster 본문 구조 동일 (frontmatter + `## 문서` 목록)
- **인터페이스 변경**: 없음. `cluster-update` CLI 동일, 출력 메시지에 `(skip N개)` 추가만
- **호출 방식 변경**: 없음. commit Step 2.1 변경 불필요
- **이행**: 자동. 다운스트림은 v0.34.x 다음 commit 1회 후부터 mtime 갱신이 영향 도메인만 발생
- **기존 cluster 파일 처리**: 첫 호출 시 `updated:` 라인 본문이 동일하면 그대로 skip, 다르면 새 today로 1회 갱신 후 안정. 추가 이행 작업 없음
- **MIGRATIONS.md 신규 섹션**: commit 스킬의 version bump가 자동 처리 — 본 WIP 종료 후 commit 시 v0.34.1 (또는 v0.35.0 PATCH/MINOR 판단) 섹션에 위 분류 그대로 박힘

## 결정 사항

### 2026-05-02 — 후보 평가

**현 동작 분석** (`docs_ops.py:391-453` Read):
- `cmd_cluster_update`이 매 호출마다 모든 abbr × cluster를 전수 재생성
- 출력 본문에 `updated: {today}` 라인 포함 → **출력 비결정적**, 내용 동일해도 매일 diff 발생
- `cluster.write_text(...)`를 무조건 호출 → 내용 동일해도 mtime 갱신
- 결함의 진짜 원인: **C4 — 출력 비결정 + 무조건 write**. C1·C2·C3는 이 위에 쌓는 추가 메커니즘

**Trade-off**:

| 후보 | 변경 범위 | 멱등성 | 정합성 | 채택 |
|------|----------|-------|-------|-----|
| C1 `--changed-only` | cluster-update + 호출자(commit Step 2.1) 모두 변경 | 호출자가 어떤 도메인이 영향받는지 정확히 알아야 함 | git mv·rename 케이스 누락 위험 | ❌ |
| C2 본체 hash 임베드 | cluster 본문에 hash 라인 추가 + 비교 | 멱등 OK | cluster 양식 변경 → 다운스트림 마이그레이션 필요 | ❌ |
| C3 본체 변경 시점만 전수 | cluster-update 외부 트리거 분리 (commit/upgrade 구분) | 호출 분기 필요 | upgrade 외 본체 변경 케이스(개발자 수동 수정) 누락 | ❌ |
| **C4 결정적 출력 + diff 비교** | cluster-update 내부만, 한 함수 변경 | 내용 동일 → 무조건 skip | cluster 양식 무변경, 다운스트림 영향 0 | ✅ |

**채택: C4**

**근거**:
1. **결함의 본질에 정합** — "본체 변경 시 N 비례 mtime 갱신"의 진짜 원인은 비결정적 출력 + 무조건 write. 내용이 정말 같으면 mtime을 건드릴 이유가 없음
2. **변경 최소** — 함수 1개 내부 수정. cluster 양식·호출자·다운스트림 영향 모두 0
3. **자연 부산물**:
   - 일반 commit: 영향 도메인만 mtime 갱신 (목표 달성)
   - 본체 변경(docs_ops.py upgrade): 출력 형식이 진짜 바뀐 도메인만 갱신 (N 비례 noise 사라짐)
   - 양 케이스 통합 처리

**구현 방안**:
1. `updated: {today}` 라인을 **기존 파일에서 추출해 재사용** (내용 비교 시 noise 제거)
2. 새 본문(updated 제외)과 기존 본문(updated 제외) 비교
3. 동일 → skip (write 안 함, mtime 무변경)
4. 다름 → `updated: {today}`로 갱신해 write

**반영 위치**: `.claude/scripts/docs_ops.py` `cmd_cluster_update`

**CPS 갱신**: 없음 — 기존 Solution 메커니즘의 효율 개선, Problem·Solution 충족 기준 무변경

## 메모

### baseline 출처
`docs/decisions/hn_downstream_amplification.md` `## 메모` 참조.

상시 N 비례 갱신 아님 — docs_ops.py 본체 변경 시(예: v0.33.0 업그레이드)에만
전수 mtime 갱신. 일반 commit에서는 0건. **결함은 본체 변경이 N비례 noise를
유발한다는 점**, 일반 시나리오는 이미 정상.
