---
title: Harness Frontmatter Schema Contract
description: Searchable frontmatter contract for Harness-governed source documents and task artifacts
domain: harness/contracts
status: active
c: frontmatter_schema
problem:
  - Required md files can drift or become undiscoverable without structured metadata
  - Workers need compact source_ref-backed context instead of full document dumps
s:
  - Require searchable frontmatter on canonical Harness md files
  - Use source_path, line_ref, artifact_ref, and owner boundary metadata as evidence anchors
tags:
  - frontmatter
  - source-ref
  - doc-ops
relates-to:
  - docs/harness/contracts/cp_cps_evidence_acquisition.md
owner_approval_boundary:
  - no implementation mutation before owner approval unless an executor packet explicitly authorizes the scope
  - no commit/push before explicit owner approval
prohibited_actions:
  - raw stdout/log archival as durable policy
  - Honcho-only policy creation without repo source_ref
---
# Contract

All required Harness markdown documents MUST start with YAML frontmatter. The frontmatter is the searchable digest header that lets Kanban packets, Maat audits, and Honcho wiki ingestion refer to source documents without copying entire files.

## Required fields

```yaml
title: string
description: string
domain: harness/contracts|harness/agents|harness/goals|harness/wiki
status: draft|active|stale|archived
c: string
problem: [string]
s: [string]
tags: [string]
relates-to: [repo-relative-path]
owner_approval_boundary: [string]
prohibited_actions: [string]
```

## Optional but preferred fields

```yaml
source_refs: [repo-relative-path#line-range]
artifact_refs: [repo-relative-path]
risk: low|medium|high
incident: false|true
owner: owner|ha_maat|ha_seshat
updated_by: profile-or-owner
```

## Digest rule

Workers receive frontmatter summaries plus source_ref candidates first. Full document text is loaded only when task_AC explicitly requires it.
