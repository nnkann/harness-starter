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
  - sibling Discord threads can complete related work without future Harness workers seeing it
  - Hermes gateway routes can outlive archived/completed threads and misrepresent active work
s:
  - register ha_honcho_archivist, ha_honcho_librarian, and ha_honcho_context as managed roles
  - keep repo markdown as SSOT and Honcho as digest-first context/wiki plane
  - require manifest-driven ingestion, drift QA, and advisory context retrieval
  - route Honcho work through CPS/task_AC/owner boundary/source_ref contracts
  - require post-completion write-back and sibling-thread recall checks for project work
  - bind thread archive, route prune, DB session close, and compression health into one lifecycle check
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

## Cross-thread learning and route lifecycle

Harness uses Hermes as the execution substrate but acts as the project routing/process plane. Therefore every Harness preflight must include a bounded sibling-context lookup before work begins:

```yaml
cross_session_preflight:
  required_checks:
    - session_search for related sibling Discord thread work
    - Honcho context lookup for project/task/routing facts
    - repo source_ref/frontmatter check for canonical policy
  failure_mode: already-solved work is repeated or a corrected procedure is forgotten
  output_shape: bounded digest with session ids, source_refs, and decision impact
```

Every completion claim that changes project policy, routing, contracts, lifecycle, or agent procedure must create a write-back event. A conversation/task end should also emit a snapshot for asynchronous background analysis, so learning can propagate without forcing the foreground worker to carry the whole transcript:

```yaml
learning_writeback:
  triggers:
    - corrected agent procedure or missed preflight
    - new lifecycle invariant
    - completed handoff with future routing impact
    - thread/task closure with gateway route implications
    - conversation/session completed or intentionally archived
  snapshot_on_close:
    required: true
    shape:
      - session_id
      - thread_id
      - root_goal_id
      - task_AC_result
      - changed_policy_or_procedure
      - source_refs
      - artifact_refs
      - unresolved_holds
      - route_cleanup_state
    background_jobs:
      - summarize snapshot into digest-first project memory
      - extract durable policy/procedure deltas
      - update Honcho digest/wiki plane or manifest status
      - queue skill/Agent/SOUL patch when procedure failed
      - report drift or missing propagation as CPS learning events
  destinations:
    - repo markdown/source_ref update
    - honcho_ingest_manifest update or direct Honcho digest write
    - skill/Agent/SOUL patch when the failure was procedural
  prohibited:
    - relying only on the original Discord thread as durable memory
    - archiving a Discord thread without assigning Hermes route/session cleanup ownership
    - foreground agents re-reading full closed transcripts when a bounded snapshot/digest exists
```

Thread lifecycle is not complete until all relevant layers are reconciled: Discord thread archive/checkpoint, session-close snapshot, Hermes `sessions.json` route status, SQLite DB session end state, compression/quota health, and Honcho/background propagation result. A stale route pointing at an ended DB session is operational debt, not an active worker.

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
