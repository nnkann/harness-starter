---
title: Honcho Agent Management Contract
description: Management plane for source_ref-backed Honcho wiki agents in Harness CPS boards
domain: harness/contracts
status: active
c: honcho_agent_management
problem:
  - Honcho agents can be described in docs but not registered as managed board/profile lanes
  - Honcho ingestion, drift QA, and context retrieval can be confused with policy authority
  - wiki digests can drift from repo md source without a management loop
s:
  - register ha_honcho_archivist, ha_honcho_librarian, and ha_honcho_context as managed roles
  - keep repo markdown as SSOT and Honcho as digest-first context/wiki plane
  - require manifest-driven ingestion, drift QA, and advisory context retrieval
  - route Honcho work through CPS/task_AC/owner boundary/source_ref contracts
  - block raw transcript/log/stdout archival as policy
tags:
  - honcho
  - wiki
  - cps
  - management
relates-to:
  - docs/harness/contracts/cp_honcho_doc_wiki_boundary.md
  - docs/harness/agents/ha_honcho_archivist.md
  - docs/harness/agents/ha_honcho_librarian.md
  - docs/harness/agents/ha_honcho_context.md
owner_approval_boundary:
  - no Honcho policy write without repo md source_ref
  - no commit/push before explicit owner approval
prohibited_actions:
  - raw transcript/log/stdout archival as durable project policy
  - treating Honcho as authoritative policy SSOT
---

# Honcho Agent Management Contract

## Managed Honcho agents

```yaml
honcho_agent_management:
  managed_agents:
    - profile: ha_honcho_archivist
      role_archetype: honcho-archivist
      trigger: honcho_ingest_manifest docs with status pending
      responsibility: ingest source_ref-backed md digests into Honcho
    - profile: ha_honcho_librarian
      role_archetype: honcho-librarian
      trigger: scheduled drift QA or post-ingestion verification
      responsibility: compare repo source docs against Honcho digests and report drift
    - profile: ha_honcho_context
      role_archetype: honcho-context
      trigger: pre-compile context retrieval or CPS routing support
      responsibility: return advisory digest-first context with source_ref candidates
  authority_order:
    - owner approval boundary
    - repo Harness markdown/source_ref
    - cps_packet/task_AC/evidence_acquisition
    - Honcho digest/context
  prohibited:
    - Honcho-only policy creation
    - full raw transcript/log/stdout ingestion
    - using prior context to override source_ref evidence or owner holds
```

## Lifecycle

1. `ha_seshat` creates/updates `honcho_ingest_manifest.yaml` from repo docs.
2. `ha_maat` audits source_refs, frontmatter summaries, and raw-ingestion prohibitions.
3. `ha_honcho_archivist` ingests digests and records status.
4. `ha_honcho_librarian` verifies completeness/drift and emits a QA report.
5. `ha_honcho_context` retrieves digest-first context for future CPS compile; it is advisory only.

## Required digest shape

```yaml
honcho_doc_digest:
  project_id: string
  source_path: repo-relative-path
  source_commit: git-sha-or-working-tree-marker
  doc_type: string
  frontmatter_summary: object
  digest: string
  required_sections_present: [C, P, S, owner_approval_boundary, prohibited_actions]
  line_refs: [repo-relative-path#line-range]
  artifact_refs: [repo-relative-path]
  status: pending|ingested|skipped|failed
  updated_at: timestamp
```
