---
title: Harness Agent Role Contracts
description: Role contracts for Hermes-kann transport, Maat fan-out, Thoth compile, Seshat doc-writing writer lane, Ptah apply, and audit roles
domain: harness/contracts
status: active
c: agent_role_contracts
problem:
  - Agent roles can collapse into generic execution
  - Execution agents can miss CPS/frontmatter/source_ref context
s:
  - Separate transport, fan-out, compile, doc-writing, change tracking, implementation, security, recovery, and wiki functions
  - Require CPS/task_AC/frontmatter/source_refs before execution
tags:
  - agents
  - roles
  - cps-routing
owner_approval_boundary:
  - no implementation mutation before owner approval unless an executor packet explicitly authorizes the scope
  - no commit/push before explicit owner approval
prohibited_actions:
  - raw stdout/log archival as durable policy
  - Honcho-only policy creation without repo source_ref
---
# Contract

## Required context for execution-class agents

```yaml
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
```

## Role separation

- hermes-kann transports raw intake only and never reselects agents.
- maat owns C-boundary, fan-out selection, and final route closure.
- thoth compiles Maat-approved CPS packets only.
- seshat owns doc-writing/doc_ops, source_ref-backed documentation lifecycle, and Honcho bookkeeping; doc-writing stays on the selected writer lane.
- the honcho_archivist / honcho_librarian / honcho_context functions are handled by seshat, not separate profiles.
- ptah implements only approved bounded task_AC.
- anubis checks boundary/security/cleanup risks.
- sekhmet handles incident recovery without bypassing CPS history.
