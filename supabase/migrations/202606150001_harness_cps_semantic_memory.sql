-- Harness CPS semantic memory schema
-- Purpose: Harness-owned semantic index/query/cache for CPS memory.
-- Boundary: Supabase is not the truth source; repo docs/source_refs remain SSOT.
-- Secrets are never stored in this schema.

create extension if not exists pgcrypto;
create extension if not exists vector;

create table if not exists public.cps_memory_items (
  id uuid primary key default gen_random_uuid(),
  namespace text not null default 'harness',
  project text,
  domain text,
  kind text not null check (kind in (
    'case',
    'workflow_template',
    'ac_pattern',
    'actor_routing_pattern',
    'negative_evidence',
    'rule_candidate',
    'downstream_feedback'
  )),
  title text not null,
  summary text,
  content_for_embedding text not null,
  -- Keep dimension unspecified until embedding provider is accepted.
  -- Follow-up migration should change this to vector(<dimension>) before vector indexing.
  embedding vector,
  metadata jsonb not null default '{}'::jsonb,
  status text not null default 'candidate' check (status in ('candidate', 'accepted', 'rejected', 'archived')),
  fingerprint text not null unique,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

comment on table public.cps_memory_items is
  'Harness CPS semantic memory items. Rows are query/index/cache units, not truth source.';
comment on column public.cps_memory_items.content_for_embedding is
  'Closed narrative: Context, Problem, Solution, AC, Evidence, Reusable when.';
comment on column public.cps_memory_items.metadata is
  'Filters and review metadata; repo source_refs remain the evidence pointer.';

create table if not exists public.memory_source_refs (
  id uuid primary key default gen_random_uuid(),
  memory_item_id uuid not null references public.cps_memory_items(id) on delete cascade,
  repo text not null,
  path text not null,
  line_start int,
  line_end int,
  commit_sha text,
  source_type text not null default 'doc' check (source_type in ('doc', 'decision', 'code', 'run_report', 'feedback', 'other')),
  created_at timestamptz not null default now(),
  constraint memory_source_refs_line_order check (
    line_start is null or line_end is null or line_end >= line_start
  )
);

comment on table public.memory_source_refs is
  'Evidence pointers back to repo/docs. Memory items without source refs should not be accepted.';

create table if not exists public.cps_inventory_snapshots (
  id uuid primary key default gen_random_uuid(),
  snapshot_at timestamptz not null default now(),
  source_repo text not null,
  branch text,
  counts jsonb not null default '{}'::jsonb,
  details jsonb not null default '{}'::jsonb,
  created_by text not null default 'harness-memory-ingest'
);

comment on table public.cps_inventory_snapshots is
  'Metric/dashboard cache only. Not a semantic source and not a truth source.';

create table if not exists public.memory_ingest_runs (
  id uuid primary key default gen_random_uuid(),
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  source_repo text not null,
  mode text not null default 'dry-run' check (mode in ('dry-run', 'write')),
  status text not null default 'running' check (status in ('running', 'ok', 'partial', 'failed', 'skipped')),
  counts jsonb not null default '{}'::jsonb,
  report jsonb not null default '{}'::jsonb
);

comment on table public.memory_ingest_runs is
  'Ingestion audit trail. First runs must be dry-run until owner approves writes.';

create index if not exists cps_memory_items_namespace_project_idx
  on public.cps_memory_items (namespace, project);
create index if not exists cps_memory_items_kind_status_idx
  on public.cps_memory_items (kind, status);
create index if not exists cps_memory_items_domain_idx
  on public.cps_memory_items (domain);
create index if not exists cps_memory_items_metadata_gin_idx
  on public.cps_memory_items using gin (metadata);
create index if not exists memory_source_refs_item_idx
  on public.memory_source_refs (memory_item_id);
create index if not exists memory_source_refs_repo_path_idx
  on public.memory_source_refs (repo, path);
create index if not exists cps_inventory_snapshots_repo_time_idx
  on public.cps_inventory_snapshots (source_repo, snapshot_at desc);
create index if not exists memory_ingest_runs_repo_time_idx
  on public.memory_ingest_runs (source_repo, started_at desc);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists cps_memory_items_set_updated_at on public.cps_memory_items;
create trigger cps_memory_items_set_updated_at
before update on public.cps_memory_items
for each row execute function public.set_updated_at();

-- RLS boundary: do not open anon/authenticated access by default.
alter table public.cps_memory_items enable row level security;
alter table public.memory_source_refs enable row level security;
alter table public.cps_inventory_snapshots enable row level security;
alter table public.memory_ingest_runs enable row level security;

-- No anon/authenticated policies are created here.
-- Server automation should use the privileged server key from runtime env only.
