---
title: Harness Agent Role Contracts
description: Role contracts for Thoth, Maat, Seshat, Ptah, Anubis, Sekhmet, and Honcho wiki roles
domain: harness/contracts
status: active
c: agent_role_contracts
problem:
  - Agent roles can collapse into generic execution
  - Execution agents can miss CPS/frontmatter/source_ref context
s:
  - Separate compile, doc_ops, audit, implementation, security, recovery, and wiki roles
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

- ha_thoth compiles CPS and task packets; it does not implement.
- ha_seshat owns doc_ops and source_ref-backed documentation lifecycle.
- ha_maat audits packet/docs/skill digest before ready.
- ha_ptah implements only approved bounded task_AC.
- ha_anubis checks boundary/security/cleanup risks.
- ha_sekhmet handles incident recovery without bypassing CPS history.
- ha_honcho_archivist/librarian/context operate the digest-first wiki plane and never override repo policy.
