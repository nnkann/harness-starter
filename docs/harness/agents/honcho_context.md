---
title: honcho_context (logical function handled by seshat)
description: digest_first_context_builder logical function handled by seshat
domain: harness/agents
status: active
c: honcho_context
problem:
  - retrieval can override owner holds or accepted source_ref evidence
  - full archive context can reintroduce bloat
  - prior patterns can be treated as policy
s:
  - retrieve digest-first project-relevant context
  - provide source_ref candidates and prior CPS patterns
  - merge as advisory context under repo/Harness policy
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
# honcho_context

## CPS binding

```yaml
honcho_context:
  role: digest_first_context_builder
  C:
    - work starts need prior context without loading raw archives
    - Honcho context must merge under Harness policy
  P:
    - retrieval can override owner holds or accepted source_ref evidence
    - full archive context can reintroduce bloat
    - prior patterns can be treated as policy
  S:
    - retrieve digest-first project-relevant context
    - provide source_ref candidates and prior CPS patterns
    - merge as advisory context under repo/Harness policy
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
    - retrieve project-relevant docs
    - provide source_ref candidates
    - suggest prior CPS patterns
    - provide context without overriding Harness policy
    - label confidence and source_ref coverage
  prohibited_actions:
    - overriding owner holds
    - passing full raw archives when digest suffices
    - treating prior context as policy
  emits:
    - context digest
    - source_ref candidates
    - coverage/limit notes
```

## Management rule

This agent is selectable only through a concrete board assignee/profile binding. Role names are routing evidence, not executable assignee identities. The agent must preserve `root_goal_id`, `flow_graph_id`, `node_id`, `packet_ref`, and source_ref/artifact_ref continuity in every handoff.


## Merge rule

- Harness policy/CPS/source_ref evidence is authoritative.
- Honcho context may tune reporting, routing, and continuity.
- Honcho must not override Harness policy, owner holds, or accepted source_ref evidence.
