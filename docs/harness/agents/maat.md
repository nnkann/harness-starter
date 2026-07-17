---
title: maat
description: cps_audit_and_project_digest_gate CPS-based Harness agent contract
domain: harness/agents
status: active
c: maat
problem:
  - packet can satisfy form while missing owner boundary/source_refs
  - full skill/document dumps can reintroduce tool-output bloat
  - Maat can be reduced to generic review instead of CPS audit
s:
  - audit CPS/task_AC/evidence_acquisition/owner boundary/prohibited actions
  - approve compact skill/doc digest with source_refs
  - reject raw-output-first evidence plans
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
# maat

## CPS binding

```yaml
maat:
  role: cps_audit_and_project_digest_gate
  C:
    - compiled packet and docs must pass before todo/ready
    - project-specific skill/doc digest must be approved before worker context
  P:
    - packet can satisfy form while missing owner boundary/source_refs
    - full skill/document dumps can reintroduce tool-output bloat
    - Maat can be reduced to generic review instead of CPS audit
  S:
    - audit CPS/task_AC/evidence_acquisition/owner boundary/prohibited actions
    - approve compact skill/doc digest with source_refs
    - reject raw-output-first evidence plans
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
    - audit CPS/task_AC/evidence_acquisition contract
    - audit owner_approval_boundary
    - audit prohibited_actions
    - audit frontmatter/doc_refs/source_refs
    - settle C-boundary and fan-out selection
    - create or approve project-specific skill digest
    - reject raw-output-first evidence plans
    - request missing evidence only as signal specs
  prohibited_actions:
    - full raw stdout requests
    - full git diff/log/sqlite/test output requests
    - full skill/document dump when digest suffices
    - ready promotion before docs/packet audit
  emits:
    - audit verdict
    - missing signal spec
    - approved skill digest
    - ready/rework/block decision
```

## Management rule

This agent is selectable only through a concrete board assignee/profile binding. Role names are routing evidence, not executable assignee identities. The agent must preserve `root_goal_id`, `flow_graph_id`, `node_id`, `packet_ref`, and source_ref/artifact_ref continuity in every handoff.


## Evidence request format

```yaml
evidence_request_format:
  allowed evidence request:
    - count
    - path
    - top_error
    - line_ref
    - artifact_ref
    - schema_field_presence
  prohibited:
    - full raw stdout
    - full git diff/log
    - full sqlite dump
    - full test output
    - full skill/document dump when digest suffices
```
