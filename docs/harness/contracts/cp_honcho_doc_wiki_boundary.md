---
title: Honcho Doc Wiki Boundary Contract
description: Source_ref-backed Honcho wiki/context plane boundary
domain: harness/contracts
status: active
c: honcho_doc_wiki_boundary
problem:
  - Honcho-only policy can drift from repo source
  - Raw transcript/log archival can become false durable policy
s:
  - Repo markdown remains authoritative SSOT
  - Honcho stores digests with source_path/source_commit/line_ref/artifact_ref
tags:
  - honcho
  - wiki
  - source-ref
owner_approval_boundary:
  - no implementation mutation before owner approval unless an executor packet explicitly authorizes the scope
  - no commit/push before explicit owner approval
prohibited_actions:
  - raw stdout/log archival as durable policy
  - Honcho-only policy creation without repo source_ref
---
# Contract

Repo / Harness starter is authoritative source. Honcho is an indexed wiki, digest archive, and context retrieval plane.

```yaml
honcho_doc_digest:
  project_id: string
  source_path: repo-relative-path
  source_commit: git-sha-or-working-tree-marker
  doc_type: string
  frontmatter_summary: object
  digest: string
  required_sections_present: [string]
  line_refs: [repo-relative-path#line-range]
  artifact_refs: [repo-relative-path]
  status: pending|ingested|skipped|failed
  updated_at: timestamp
```

Honcho context may tune continuity and routing; it must not override Harness policy, owner holds, or accepted source_ref evidence.
