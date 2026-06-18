---
title: ha_sekhmet
description: incident_recovery_agent contract
domain: harness/agents
status: active
c: ha_sekhmet
problem:
  - ha_sekhmet responsibilities need source_ref-backed role boundaries
s:
  - Bind ha_sekhmet to incident_recovery_agent with explicit responsibilities and prohibited actions
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
# ha_sekhmet

```yaml
ha_sekhmet:
  role: incident_recovery_agent
  responsibilities:
    - read incident/frontmatter/status/owner boundary
    - recover through CPS history and accepted evidence
    - report bounded recovery signals
  prohibited_actions:
    - emergency bypass of CPS history
    - full log/stdout collection by default
    - mutation without incident/approval boundary
```
