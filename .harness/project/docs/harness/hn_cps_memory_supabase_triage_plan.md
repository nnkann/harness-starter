---
title: Harness CPS memory Supabase repurpose triage plan
description: "Hermes core를 수정하지 않고 기존 ai-prompter Supabase shell project를 Harness-owned CPS semantic memory layer로 전환하기 위한 owner-approval gated triage와 다른 세션 handoff prompt."
domain: harness
c: "Harness CPS 수식·템플릿·downstream learning이 누적되면서 file-only memory를 넘어서는 semantic query/index가 필요해졌지만, Hermes core/state.db/adapter export를 수정하면 소유권과 업데이트 경계가 깨진다."
problem: [P7, P8, P9, P11]
s: [S7, S8, S9, S11]
tags: [cps, memory, supabase, pgvector, triage, handoff, hermes-boundary]
relates-to:
  - harness/hn_cps_semantic_memory_db.md
  - decisions/hn_hermes_managed_downstream_memory.md
status: proposed
created: 2026-06-15
updated: 2026-06-15
owner_approval_boundary: "이 문서는 계획과 handoff prompt만 제공한다. Supabase project rename/repurpose, secret 재사용 범위 확정, DB migration apply, cron 생성, commit/push는 owner 승인 전 금지한다."
prohibited_actions:
  - "Hermes core/state.db 수정"
  - ".harness/hermes/** adapter/reference export 수정"
  - "Kanban DB schema에 CPS semantic memory를 직접 끼워 넣기"
  - "Supabase service-role/DB password/API secret을 chat/docs/git/memory에 저장"
  - "owner 승인 전 ai-prompter Supabase project rename/repurpose, remote schema 변경, ingestion write, cron 생성"
---

# Harness CPS memory Supabase repurpose triage plan

## Owner decisions captured 2026-06-15

- 기존 `ai-prompter` Supabase project는 테이블이 없는 shell 상태이므로 삭제/재생성보다 **rename/repurpose**를 우선한다.
- Owner가 Supabase project display name을 `harness-learning`으로 변경 완료했다.
- Supabase project metadata:
  - project-name: `harness-learning`
  - project id/ref: `cwtwbdwbhtpudwhfqbac`
  - region: `ap-northeast-2`
- Secret/key를 새로 받는 비용을 줄이기 위해 현재 project의 저장 key를 재사용하는 방향을 검토한다. 단 key 값은 chat/docs/git/memory에 기록하지 않는다.
- 먼저 Supabase dashboard read-only inventory를 한다. CLI는 이후 지속 업데이트/마이그레이션 관리용으로 붙인다.
- Schema는 공용 Harness memory schema로 둔다. 적용 방식은 SQL editor 수동 적용 또는 CLI migration 둘 다 가능하나, 최종 schema는 repo migration으로 회수한다.
- 각 프로젝트가 직접 올리는 방식보다 Harness cron/guardian이 downstream을 수거해서 주입하는 중앙 ingestion이 우선이다.
- Embedding/model은 고급 reasoning 모델(GPT-5.5급)이 필수는 아니다. Agy medium 또는 낮은 등급으로 충분한지 먼저 dry-run/eval로 확인한다.
- Prompter 작업과 Harness memory 작업은 겹치므로 순서를 나눠 진행한다.

## 결정 후보 요약

Harness CPS memory는 별도 DB가 필요해졌다. 단, 이 DB는 Hermes DB가 아니라 **Harness-owned semantic memory/index**다.

권장 방향:

```text
SSOT:
  harness-starter repo docs
  downstream repo docs
  accepted decision/policy files
  CPS equations/templates

Semantic index/query:
  Supabase Postgres + pgvector

Hermes:
  수정하지 않음
  기존 file/terminal/skill/cron 방식으로 query/ingest script를 호출
```

Supabase는 truth source가 아니라 아래 역할을 가진다.

```text
- CPS memory 검색 엔진
- downstream feedback index
- semantic recall layer
- candidate memory staging table
- inventory/delta metric cache
```

## CPS rationale

- C -> P: CPS 수식·템플릿·downstream 사례가 늘면서 “얼마나 누적되었나 / 무엇이 반복되는가 / 비슷한 사례가 있었나”를 semantic query로 물어야 한다.
- P -> S:
  - P7/S7: Hermes memory, repo docs, downstream reminder, external DB의 소유권을 분리한다.
  - P8/S8: memory/reminder를 사실이 아니라 재확인 가능한 signal/source_refs로 다룬다.
  - P9/S9: Hermes core/adapter/Kanban DB에 project learning을 저장하는 오염을 막는다.
  - P11/S11: downstream에서 발견된 동형 패턴을 reusable memory item으로 승격한다.
- S -> AC: Supabase project 전환은 owner 승인 후 별도 triage로 진행하며, 먼저 삭제/생성/스키마/ingestion/validation prompt를 고정한다.

## Architecture boundary

### 하지 않는 것

```text
X Hermes core 수정
X Hermes state.db 확장
X .harness/hermes adapter export 수정
X Kanban DB에 CPS semantic memory를 억지로 추가
X Supabase row를 단독 truth로 취급
X secret/service-role key를 chat/docs/git/memory에 저장
```

### 하는 것

```text
O Harness-owned Supabase project 사용
O repo docs/source_refs를 truth pointer로 유지
O Supabase를 vector/search/index/cache로 사용
O Hermes skill/cron/tool은 operator/query client 역할만 수행
O RLS ON, server automation은 service role을 로컬 .env/runtime secret에서만 사용
O owner 승인 전에는 계획/스키마 초안/프롬프트까지만 작성
```

## C split / triage graph

### C0. Owner plan confirmation

Goal: 지금 문서와 handoff prompt의 범위 확인.

AC:

- [x] Owner가 `ai-prompter Supabase 회수 여부`를 명시했다: 삭제/재생성보다 rename/repurpose 우선.
- [x] Owner가 project display name을 `harness-learning`으로 변경 완료했다.
- [x] Project metadata가 확인되어 있다: project ref `cwtwbdwbhtpudwhfqbac`, region `ap-northeast-2`.
- [ ] Owner가 schema 적용 주체를 선택한다: SQL editor 수동 적용 또는 CLI migration apply.

Hold:

- 승인 전 Supabase dashboard/CLI에서 rename, schema 변경, key rotation, project 삭제·생성을 하지 않는다.

### C1. Existing ai-prompter Supabase inventory / repurpose readiness

Goal: 기존 `ai-prompter` Supabase project가 shell 상태인지 확인하고 Harness learning 용도로 rename/repurpose 가능성을 판단한다.

Read-only checks:

- Supabase dashboard에서 current project name/ref/org/region 확인.
- table/auth/storage/edge function/cron/webhook 존재 여부 확인.
- 연결된 repo/app/deployment secret에서 현재 project ref/key 사용 여부 확인.
- 기존 저장 key를 재사용해도 되는지, 또는 key rotation이 필요한지 판단한다. key 값은 출력하지 않는다.

AC:

- [ ] project ref/org/region이 확인되어 있다.
- [ ] table이 없거나 비어 있다는 owner 진술이 dashboard에서 재확인되어 있다.
- [ ] 사용 중인 앱/secret/deployment dependency가 없거나 repurpose 영향이 기록되어 있다.
- [ ] 삭제가 아니라 rename/repurpose가 우선 결정으로 기록되어 있다.
- [ ] key reuse vs key rotation 판단이 owner-action으로 남아 있다.

Hold:

- rename/repurpose도 project identity 변경이므로 owner confirmation 없이는 실행 금지.

### C2. Harness Supabase project repurpose

Goal: 기존 shell project를 Harness CPS memory 전용 Supabase project로 전환한다.

Inputs:

- target display name: `harness-learning` confirmed
- project ref/API URL: `cwtwbdwbhtpudwhfqbac`, `https://cwtwbdwbhtpudwhfqbac.supabase.co`
- org: existing project org, dashboard confirmation pending if needed
- region: `ap-northeast-2`
- keys: existing stored key reuse preferred; no key values in chat/docs/git

AC:

- [x] project display name이 owner-approved 값으로 정리되어 있다: `harness-learning`.
- [x] project ref와 API URL이 확인되어 있다: `cwtwbdwbhtpudwhfqbac`, `https://cwtwbdwbhtpudwhfqbac.supabase.co`.
- [ ] RLS 기본 ON 전략이 기록되어 있다.
- [ ] service-role/secret key는 chat/docs/git에 노출되지 않았다.
- [ ] repo-local `.env`에는 secret 값 없이 key 이름/blank placeholder 또는 local path 안내만 있다.

Hold:

- Secret/service-role/DB password를 assistant에게 chat으로 붙여넣지 않는다.

### C3. Schema/migration draft

Goal: 최소 semantic memory schema를 repo-backed migration으로 준비한다.

Initial tables:

```text
cps_memory_items
cps_inventory_snapshots
memory_source_refs
memory_ingest_runs
```

Optional later:

```text
cps_query_logs
memory_review_events
```

AC:

- [ ] `pgvector` enable migration이 있다.
- [ ] `cps_memory_items.content_for_embedding`가 primary embedding text로 정의되어 있다.
- [ ] source_refs가 repo path/line/commit pointer를 가진다.
- [ ] inventory snapshots는 metric cache일 뿐 semantic source가 아니라고 명시한다.
- [ ] RLS policy는 anon read/write를 열지 않는다.

Hold:

- owner 승인 전 remote DB에 migration apply 금지.

### C4. Ingestion/indexing script

Goal: Harness/downstream docs에서 candidate memory item을 생성하고 Supabase에 upsert한다.

Design:

```text
harness cron/guardian -> downstream repo read-only scan -> candidate memory JSONL/report -> owner/reviewer acceptance -> Supabase upsert
```

Project repos should not each invent their own direct uploader first. Central Harness ingestion keeps CPS taxonomy, source_refs, status, and dedupe policy consistent.

AC:

- [ ] dry-run mode가 default다.
- [ ] source_refs 없는 item은 reject한다.
- [ ] fingerprint/dedupe key가 있다.
- [ ] accepted/candidate/rejected status를 구분한다.
- [ ] service-role key는 env에서만 읽는다.

Hold:

- 첫 ingestion은 dry-run report만 만들고 DB write는 owner 승인 후 실행한다.

### C5. Hermes integration without Hermes modification

Goal: Hermes는 기존 기능만 사용해 Harness memory를 조회한다.

Allowed integration:

```text
- Hermes skill: query/triage 절차 저장
- Hermes cron: read-only daily/weekly report
- terminal/file tools: repo-local script 실행
- built-in memory: “Harness CPS memory 위치/사용 원칙” pointer만 저장
```

AC:

- [ ] Hermes core/state.db/plugin export 수정이 없다.
- [ ] `.harness/hermes/**` 수정이 없다.
- [ ] cron은 report/delta만 생성하고 destructive write를 하지 않는다.
- [ ] Supabase 결과는 source_refs로 재확인한다.

### C6. Validation/reporting

Goal: owner가 “올려도 되는지” 판단할 수 있는 preflight report를 만든다.

Report sections:

```text
- Supabase project inventory
- deletion impact
- proposed new project metadata
- schema/migration summary
- RLS/secret boundary
- dry-run memory item count
- first query examples
- owner-action list
```

AC:

- [ ] “바로 올리지 않음” 상태를 유지한다.
- [ ] destructive/mutating action 전 confirmation gate가 있다.
- [ ] repo validation command가 통과한다.

## 최소 schema 초안

```sql
-- Requires: create extension if not exists vector;

create table if not exists cps_memory_items (
  id uuid primary key default gen_random_uuid(),
  namespace text not null default 'harness',
  project text,
  domain text,
  kind text not null,
  title text not null,
  summary text,
  content_for_embedding text not null,
  embedding vector,
  metadata jsonb not null default '{}'::jsonb,
  status text not null default 'candidate',
  fingerprint text unique,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists memory_source_refs (
  id uuid primary key default gen_random_uuid(),
  memory_item_id uuid not null references cps_memory_items(id) on delete cascade,
  repo text not null,
  path text not null,
  line_start int,
  line_end int,
  commit_sha text,
  source_type text not null default 'doc',
  created_at timestamptz not null default now()
);

create table if not exists cps_inventory_snapshots (
  id uuid primary key default gen_random_uuid(),
  snapshot_at timestamptz not null default now(),
  source_repo text not null,
  branch text,
  counts jsonb not null default '{}'::jsonb,
  details jsonb not null default '{}'::jsonb,
  created_by text not null default 'harness-memory-ingest'
);

create table if not exists memory_ingest_runs (
  id uuid primary key default gen_random_uuid(),
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  source_repo text not null,
  mode text not null default 'dry-run',
  status text not null default 'running',
  counts jsonb not null default '{}'::jsonb,
  report jsonb not null default '{}'::jsonb
);
```

Note: embedding dimension/model은 실제 provider 선택 후 migration에서 고정한다. 그 전까지 `embedding vector` 또는 임시 nullable column으로 두고, remote apply 전 확정한다.

## Other-session handoff prompt

아래 프롬프트를 새 세션에 그대로 전달한다.

```text
너는 Harness-starter repo에서 기존 ai-prompter Supabase shell project를 Harness-owned CPS semantic memory로 repurpose하는 작업의 triage 담당이다.

중요 경계:
- Hermes core/state.db를 수정하지 마라.
- .harness/hermes/** adapter/reference export를 수정하지 마라.
- Kanban DB schema에 CPS memory를 끼워 넣지 마라.
- Supabase service-role key, DB password, API secret을 chat/docs/git/memory에 저장하지 마라.
- owner 승인 전 ai-prompter Supabase project rename/repurpose, remote schema 변경, ingestion write, cron 생성, commit/push를 하지 마라.
- 삭제/재생성은 현재 우선안이 아니다. 기존 ai-prompter project가 테이블 없는 shell이면 rename/repurpose와 기존 저장 key 재사용을 우선 검토한다.
- 먼저 dashboard read-only inventory와 계획/리포트만 작성하고 owner confirmation을 받아라.

Repo:
- /Users/kann/projects/harness-starter
- active branch should be hermes/harness-starter-baseline

Supabase project:
- project name: harness-learning
- project ref: cwtwbdwbhtpudwhfqbac
- project API URL: https://cwtwbdwbhtpudwhfqbac.supabase.co
- region: ap-northeast-2
- key policy: reuse existing stored keys if available; never print or store key values in chat/docs/git/memory

반드시 먼저 읽을 문서:
- .harness/project/docs/harness/hn_cps_memory_supabase_triage_plan.md
- .harness/project/docs/harness/hn_cps_semantic_memory_db.md
- .harness/project/docs/decisions/hn_hermes_managed_downstream_memory.md
- AGENTS.md

목표:
1. ai-prompter용으로 만든 Supabase project가 shell 상태인지 dashboard read-only로 확인한다.
2. 삭제/재생성이 아니라 확정된 `harness-learning` project 기준의 repurpose/schema 계획을 제시한다.
3. 기존 저장 key를 재사용할 수 있는지 판단하되, key 값은 절대 출력/저장하지 않는다.
4. Supabase를 truth source가 아니라 semantic index/query/cache로 사용하는 schema/migration 초안을 제시한다.
5. 각 downstream project가 직접 올리는 방식보다 Harness cron/guardian이 read-only 수거 후 중앙 주입하는 방식을 우선 설계한다.
6. Hermes는 수정하지 않고 skill/cron/file/terminal 방식으로만 이 DB를 조회/운영하는 방식을 제시한다.
7. destructive/mutating action은 owner confirmation 이후 별도 단계로 넘긴다.

C split / triage:
- C0: owner plan confirmation and spelling confirmation
- C1: ai-prompter Supabase shell inventory and repurpose readiness, read-only only
- C2: Harness learning project rename/repurpose plan, no rename before approval
- C3: common schema/migration draft, no remote apply before approval
- C4: central Harness cron/guardian ingestion dry-run design
- C5: Hermes integration without Hermes modification
- C6: preflight report and owner-action list

이번 세션의 산출물:
- 한국어 preflight report
- 삭제/생성/마이그레이션/cron 각각에 대한 HOLD gate
- owner가 답해야 할 선택지 목록
- 다음 실행 세션에서 쓸 exact command 후보. 단 secret은 출력하지 말 것.

보고 형식:
1. 현재 이해
2. 금지선
3. C split triage
4. Supabase rename/repurpose 계획
5. schema/migration 초안 요약
6. Hermes 비수정 integration 계획
7. owner 확인 질문
8. 아직 실행하지 않은 것 목록

마지막 줄은 반드시:
상태: PLAN_ONLY_OWNER_CONFIRMATION_REQUIRED
```

## Owner confirmation checklist

Owner가 아래를 답하면 다음 세션이 실행 준비에 들어갈 수 있다.

```text
1. harness-learning project의 기존 저장 key를 재사용하되, key rotation은 하지 않는 방향으로 확정해도 되는가?
2. schema apply 1차는 SQL editor에서 owner가 직접 할까, 아니면 CLI migration으로 assistant가 진행할까?
3. 최종적으로 schema는 repo migration으로 회수/버전관리하는 데 동의하는가?
4. 첫 ingestion 범위는 harness-starter docs only로 시작하고, 이후 Harness cron/guardian이 StageLink 등 downstream을 수거하는 순서로 갈까?
5. embeddings/model은 Agy medium 또는 더 낮은 등급으로 dry-run/eval 후 결정하고, 초기 schema는 embedding nullable/text-first로 둘까?
6. Prompter 재작성 작업은 Harness memory Supabase schema 이후 별도 C로 분리할까?
```

## Acceptance Criteria

- [x] Supabase가 Harness-owned semantic memory/index이며 Hermes DB가 아님을 명시한다.
- [x] Hermes core/state.db/.harness/hermes 수정 금지선을 명시한다.
- [x] ai-prompter Supabase 삭제/회수가 아니라 기존 shell project rename/repurpose와 key 재사용 우선 흐름이 owner-approval gated C split으로 나뉘어 있다.
- [x] Supabase schema 초안이 source_refs, candidate/accepted status, inventory snapshot cache를 포함한다.
- [x] 다른 세션에서 바로 사용할 handoff prompt가 포함되어 있다.
- [x] destructive/mutating action 전 confirmation gate가 있다.

## 현재 상태

이 문서는 계획과 handoff prompt다. 아직 Supabase project rename/repurpose, schema apply, ingestion, cron 생성, commit/push는 수행하지 않았다.
