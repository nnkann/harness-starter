---
title: ha_honcho_context
description: digest_first_context_builder contract
domain: harness/agents
status: active
c: ha_honcho_context
problem:
  - ha_honcho_context responsibilities need source_ref-backed role boundaries
s:
  - Bind ha_honcho_context to digest_first_context_builder with explicit responsibilities and prohibited actions
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
# ha_honcho_context

```yaml
ha_honcho_context:
  role: digest_first_context_builder
  responsibilities:
    - retrieve project-relevant docs
    - provide source_ref candidates
    - suggest prior CPS patterns
    - provide context without overriding Harness policy
  prohibited_actions:
    - overriding owner holds
    - passing full raw archives when digest suffices
```
