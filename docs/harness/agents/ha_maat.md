---
title: ha_maat
description: cps_audit_and_project_digest_gate contract
domain: harness/agents
status: active
c: ha_maat
problem:
  - ha_maat responsibilities need source_ref-backed role boundaries
s:
  - Bind ha_maat to cps_audit_and_project_digest_gate with explicit responsibilities and prohibited actions
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
# ha_maat

```yaml
ha_maat:
  role: cps_audit_and_project_digest_gate
  responsibilities:
    - audit CPS/task_AC/evidence_acquisition contract
    - audit owner_approval_boundary
    - audit prohibited_actions
    - audit frontmatter/doc_refs/source_refs
    - create or approve project-specific skill digest
    - reject raw-output-first evidence plans
    - request missing evidence only as signal specs
  prohibited_actions:
    - full raw stdout requests
    - full git diff/log/sqlite/test output requests
    - full skill/document dump when digest suffices
```
