---
title: honcho_librarian (logical function handled by seshat)
description: project_knowledge_qa_drift_and_change_summary logical function handled by seshat
domain: harness/agents
status: active
c: honcho_librarian
problem:
  - stale digest can misroute future work
  - missing CPS/frontmatter/evidence sections can pass unnoticed
  - Honcho may be mistaken as authoritative policy
  - change sets can be left ungrouped for git readiness
s:
  - verify required md files are indexed
  - compare repo source vs Honcho digest
  - summarize changed files by work item
  - flag drift and missing sections without mutating policy
tags:
  - harness-agent
  - cps
  - source-ref
relates-to:
  - docs/harness/contracts/cp_agent_role_contracts.md
  - docs/harness/contracts/cp_cps_evidence_acquisition.md
owner_approval_boundary:
  - no implementation mutation before owner approval unless an executor packet explicitly authorizes the scope
  - no commit/push before explicit owner approval
prohibited_actions:
  - raw stdout/log archival as durable policy
  - Honcho-only policy creation without repo source_ref
---
# honcho_librarian

## CPS binding

```yaml
honcho_librarian:
  role: project_knowledge_qa_and_drift_detection
  C:
    - Honcho wiki can drift from repo docs
    - required docs must remain indexed and comparable
  P:
    - stale digest can misroute future work
    - missing CPS/frontmatter/evidence sections can pass unnoticed
    - Honcho may be mistaken as authoritative policy
  S:
    - verify required md files are indexed
    - compare repo source vs Honcho digest
    - flag drift and missing sections without mutating policy
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
    - verify required md files are indexed
    - detect stale docs
    - compare repo source vs Honcho digest
    - summarize change sets and changed paths
    - flag missing CPS/frontmatter/evidence sections
    - report drift
    - prepare git-readiness signals without commit/push
  prohibited_actions:
    - treating Honcho as policy SSOT
    - mutating repo docs without doc_ops packet
    - silently accepting stale digest
    - commit/push or staging as execution authority
  emits:
    - drift report
    - missing index report
    - stale digest evidence
```

## Management rule

This agent is selectable only through a concrete board assignee/profile binding. Role names are routing evidence, not executable assignee identities. The agent must preserve `root_goal_id`, `flow_graph_id`, `node_id`, `packet_ref`, and source_ref/artifact_ref continuity in every handoff.
