---
title: CPS semantic memory DB 계층 정리
domain: harness
c: "CPS inventory와 downstream 학습을 DB화하려면 LangGraph 관점의 checkpoint/store 분리와 vector 검색 단위를 먼저 고정해야 한다."
problem: [P7, P8, P9, P11]
s: [S7, S8, S9, S11]
tags: [cps, memory, db, vector, langgraph, downstream]
status: in-progress
created: 2026-06-15
updated: 2026-06-15
---

# CPS semantic memory DB 계층 정리

## CPS Rationale

- C -> P: CPS 수식·템플릿·downstream 사례를 누적하려는 요구가 생겼지만, 실행 상태와 장기 학습을 같은 DB 스키마로 쪼개면 Hermes adapter export 오염, 중복 테이블, 벡터 검색 단위 파편화가 발생한다.
- P -> S: P7/S7은 소유권·출력 계약을 분리하고, P8/S8은 memory/reminder를 durable state로 상태화하며, P9/S9는 잘못된 레이어에 정책을 저장하는 오염을 막고, P11/S11은 downstream에서 발견된 동형 패턴을 재사용 가능한 단위로 승격한다.
- S -> AC: AC는 새 DB/마이그레이션을 즉시 만들지 않고, project-owned 문서에서 checkpoint layer와 semantic store layer를 분리한 뒤 관련 작업이 열릴 때 현재 템플릿으로 점진 보정하는 것이다.

## 결정 요약

1. 기존 downstream 문서를 일괄 migration하지 않는다.
2. 관련 문서나 작업이 열릴 때만 현재 frontmatter/CPS/AC/evidence 템플릿에 맞춰 점진 보정한다.
3. `.harness/hermes/**` adapter/reference export에는 CPS inventory, semantic memory DB, product/project 분석 산물을 넣지 않는다.
4. DB는 LangGraph 관점에 맞춰 `checkpoint layer`와 `semantic store layer`로 나눈다.
5. 벡터 검색 단위는 P/S edge 조각이 아니라 `C -> P -> S -> AC -> evidence -> reuse condition` 전체 narrative다.

## 레이어 경계

### 1. Checkpoint / execution state layer

역할:

- thread/run state
- task progress
- node state
- interrupt/resume
- human approval 대기
- tool-call result
- worker run outcome

저장 후보:

- 기존 Hermes Kanban `tasks`, `task_events`, `task_runs`, `comments`
- LangGraph checkpointer

규칙:

- 이 레이어는 실행 상태 저장소다.
- durable CPS ontology를 여기에 잘게 쪼개 저장하지 않는다.
- checkpoint row는 재시작·복구·time travel을 위한 state snapshot이지 장기 학습 memory item이 아니다.

### 2. Semantic store / long-term memory layer

역할:

- reusable CPS case
- workflow template
- AC decomposition pattern
- actor routing lesson
- negative evidence lesson
- downstream feedback
- rule/template 승격 후보

저장 후보:

- `cps_memory_items` 하나를 중심으로 둔 vector-addressable store
- 필요 시 metric cache인 `cps_inventory_snapshots`

규칙:

- 하나의 row는 하나의 재사용 가능한 의미 단위여야 한다.
- embedding 대상은 사람이 읽어도 의미가 닫히는 narrative여야 한다.
- P/S 번호, task id, graph id, label은 embedding 본문이 아니라 metadata/filter로 둔다.

## 최소 DB 모델

### `cps_memory_items`

목적: cross-thread long-term CPS memory item. 하나의 row가 하나의 semantic retrieval unit이다.

필드 후보:

```text
id
project_id
board_id
namespace
kind
title
summary
content_for_embedding
metadata_json
source_refs_json
evidence_refs_json
fingerprint
embedding
status
created_at
updated_at
```

`kind` 후보:

```text
case
workflow_template
ac_pattern
actor_routing_pattern
negative_evidence
rule_candidate
downstream_feedback
```

`content_for_embedding` 작성 규칙:

```text
Context: 어떤 상황/Concern인가.
Problem: 어떤 P 해석 또는 product-local problem인가.
Solution: 어떤 S/operator/template이 맞았는가.
AC: 어떤 완료 기준과 검증 범위가 필요했는가.
Evidence: 어떤 doc/task/run/source가 이를 뒷받침하는가.
Reusable when: 어떤 future task에서 재사용해야 하는가.
```

예시:

```text
Context: StageLink artist alias locale coverage가 검색·매칭 정확도에 영향을 준다.
Problem: locale alias data가 비어 있거나 분산되면 검색·추천·표시명이 흔들린다.
Solution: alias_locales, getArtistDisplayName, ontology label/alias 체계로 정규화한다.
AC: alias coverage, fallback policy, admin curation queue, remaining uncovered count를 evidence로 검증한다.
Evidence: .harness/project/docs/decisions/ar_multilang_coverage.md
Reusable when: product domain has multilingual entity naming, search matching, locale fallback, or curation queue.
```

metadata 예시:

```json
{
  "cps": {
    "c_ref": "multilingual artist identity affects search and display quality",
    "p_refs": ["P6"],
    "s_refs": ["S6"],
    "ordered_steps": ["P6/S6"],
    "flow_shape": "single_case_to_pattern"
  },
  "filters": {
    "domain": "artist",
    "project": "stagelink",
    "artifact_type": "decision",
    "promotion_target": "case",
    "labels": ["search", "i18n", "alias", "locale", "curation"],
    "status": "accepted",
    "confidence": 0.82,
    "legacy_shape": true
  },
  "reward": {
    "eligible": true,
    "trigger": "new_ac_decomposition_pattern",
    "message": "좋은 발견이야. 이 trace는 locale alias coverage를 reusable search/matching pattern으로 승격했다.",
    "awarded_at": "2026-06-15",
    "awarded_by": "reviewer"
  }
}
```

### `cps_inventory_snapshots`

목적: dashboard/metric cache. semantic memory source가 아니다.

필드 후보:

```text
id
project_id
board_id
snapshot_json
combo_count
edge_count
memory_item_count
reward_candidate_count
legacy_shape_ratio
created_at
```

규칙:

- trend, dashboard, weekly delta에만 사용한다.
- vector 검색 대상이 아니다.
- full CPS/AC 본문을 복제하지 않는다.

## 만들지 않을 테이블

아래 테이블은 현재 방향에서는 만들지 않는다.

```text
cps_expressions
cps_learning_events
cps_reward_events
```

이유:

- 하나의 학습 단위가 여러 row로 분산되어 retrieval 의미가 깨진다.
- embedding 대상 텍스트가 파편화된다.
- join이 늘고, vector search 결과가 edge/event 조각으로 튀어나온다.
- reward는 독립 entity가 아니라 memory item의 review/promotion metadata로 충분하다.

## Downstream 보정 정책

- project-local P/S 번호는 raw meaning으로 cross-project 비교하지 않는다.
- 비교 기준은 shape, evidence density, closure quality, reuse condition이다.
- `cps_flow_graph`, `root_goal`, `task_AC` 도입 전 문서는 legacy-shaped로 인정한다.
- `problem:` 직접 인용이 적어도 `solution-ref`, WIP, downstream feedback에서 살아 있으면 폐기 후보로 단정하지 않는다.
- StageLink 같은 product repo에서 발견된 실제 실패 패턴은 upstream policy보다 더 강한 실측 근거로 취급하되, 일반화 전에는 project-specific case로 둔다.

## 적용 순서

1. 이 문서는 정책/설계 decision으로 유지한다.
2. 기존 문서 전체 migration은 하지 않는다.
3. 새 CPS learning 작업이나 관련 downstream 문서 수정 시 현재 템플릿으로 점진 보정한다.
4. 실제 저장소는 Hermes core/state.db/Kanban DB가 아니라 Harness-owned semantic memory layer로 둔다. 현재 우선 후보는 Supabase Postgres + pgvector이며, repo-local JSONL/SQLite는 dry-run·fallback·export cache로만 취급한다.
5. 실제 Supabase project 삭제/생성, migration apply, ingestion write, cron 생성은 owner 승인 후 별도 triage에서 수행한다.
6. 구현 시 `.harness/hermes/**` adapter export는 수정 대상에서 제외한다.

## Acceptance Criteria

- [ ] `cps_memory_items` 중심의 semantic store 설계가 checkpoint/run state와 분리되어 있다.
- [ ] 벡터 대상이 P/S edge 조각이 아니라 C/P/S/AC/evidence/reuse narrative임을 명시한다.
- [ ] reward/칭찬 로직이 별도 테이블이 아니라 memory item metadata로 정의되어 있다.
- [ ] `cps_inventory_snapshots`가 metric cache일 뿐 semantic source가 아님을 명시한다.
- [ ] 기존 문서 일괄 보정 대신 관련 작업 시 점진 보정한다는 정책을 명시한다.
- [ ] `.harness/hermes/**` adapter/reference export를 수정하지 않는다는 금지선을 명시한다.

## 현재 상태

- 이 문서는 DB 테이블을 직접 생성하거나 migration하지 않는다.
- 이 문서는 이후 triage/implementation이 참조할 project-owned SSOT다.
- 실제 구현은 owner 승인 후 Supabase/Harness-owned project memory layer와 repo-local ingestion script 중 적절한 위치를 다시 판정한다.
