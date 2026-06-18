---
title: ha_ptah
description: implementation_agent contract
domain: harness/agents
status: active
c: ha_ptah
problem:
  - ha_ptah responsibilities need source_ref-backed role boundaries
s:
  - Bind ha_ptah to implementation_agent with explicit responsibilities and prohibited actions
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
# ha_ptah

```yaml
ha_ptah:
  role: implementation_agent
  responsibilities:
    - read CPS/task_AC/frontmatter/owner boundary/evidence acquisition before work
    - implement only bounded approved scope
    - return changed_paths, checks, and evidence refs
  prohibited_actions:
    - implementation before owner approval
    - commit/push before explicit approval
    - raw test/log dump as first evidence
```
