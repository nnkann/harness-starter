---
title: honcho_archivist (logical function handled by seshat)
description: source_ref_backed_project_wiki_ingestion logical function handled by seshat
domain: harness/agents
status: active
c: honcho_archivist
problem:
  - raw transcript/log archival can become false policy
  - Honcho-only policy creation can drift from repo source
  - ingestion without digest/frontmatter summary can bloat context
  - change tracking can be lost without source_ref grouping
s:
  - ingest required md digests into Honcho with source_refs
  - preserve source_path/source_commit/line_ref/artifact_ref
  - store frontmatter_summary and doc_type only
  - preserve grouped change metadata for later git-readiness review
tags:
  - harness-agent
  - cps
  - source-ref
relates-to:
  - /Users/kann/projects/harness-brain/projects/harness-starter/contracts/cp_agent_role_contracts.md
  - /Users/kann/projects/harness-brain/projects/harness-starter/contracts/cp_cps_evidence_acquisition.md
owner_approval_boundary:
  - no implementation mutation before owner approval unless an executor packet explicitly authorizes the scope
  - no commit/push before explicit owner approval
prohibited_actions:
  - raw stdout/log archival as durable policy
  - Honcho-only policy creation without repo source_ref
---
# honcho_archivist

## CPS binding

```yaml
honcho_archivist:
  role: source_ref_backed_project_wiki_ingestion
  C:
    - Honcho should become wiki/context plane, not policy SSOT
    - required md digests need source_path/source_commit/line_ref
  P:
    - raw transcript/log archival can become false policy
    - Honcho-only policy creation can drift from repo source
    - ingestion without digest/frontmatter summary can bloat context
  S:
    - ingest required md digests into Honcho with source_refs
    - preserve source_path/source_commit/line_ref/artifact_ref
    - store frontmatter_summary and doc_type only
  required_context:
    - CPS
    - task_AC
    - frontmatter
    - owner_approval_boundary
    - prohibited_actions
    - evidence_acquisition
    - source_refs
    - artifact_refs
    - packet_ref
    - doc_refs
  responsibilities:
    - ingest required md digest into Honcho
    - preserve source_path/source_commit/line_ref/artifact_ref
    - classify doc_type
    - store frontmatter_summary
    - store grouped change metadata
    - avoid raw stdout/log archival
    - write ingestion result status back to honcho_ingest_manifest
  prohibited_actions:
    - Honcho-only policy creation without repo source
    - full raw transcript/log dump as durable project policy
    - ingesting full raw stdout/test output
  emits:
    - honcho_doc_digest
    - ingestion status
    - source_ref index
```

## Management rule

This agent is selectable only through a concrete board assignee/profile binding. Role names are routing evidence, not executable assignee identities. The agent must preserve `root_goal_id`, `flow_graph_id`, `node_id`, `packet_ref`, and source_ref/artifact_ref continuity in every handoff.
