---
title: ha_honcho_archivist
description: source_ref_backed_project_wiki_ingestion contract
domain: harness/agents
status: active
c: ha_honcho_archivist
problem:
  - ha_honcho_archivist responsibilities need source_ref-backed role boundaries
s:
  - Bind ha_honcho_archivist to source_ref_backed_project_wiki_ingestion with explicit responsibilities and prohibited actions
tags:
  - agent-role
  - harness
relates-to:
  - docs/harness/contracts/cp_agent_role_contracts.md
owner_approval_boundary:
  - no implementation mutation before owner approval unless an executor packet explicitly authorizes the scope
  - no commit/push before explicit owner approval
prohibited_actions:
  - raw stdout/log archival as durable policy
  - Honcho-only policy creation without repo source_ref
---
# ha_honcho_archivist

```yaml
ha_honcho_archivist:
  role: source_ref_backed_project_wiki_ingestion
  responsibilities:
    - ingest required md digest into Honcho
    - preserve source_path/source_commit/line_ref/artifact_ref
    - classify doc_type
    - store frontmatter_summary
    - avoid raw stdout/log archival
  prohibited_actions:
    - Honcho-only policy creation without repo source
    - full raw transcript/log dump as durable project policy
```
