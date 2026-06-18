---
title: Owner Approval Boundary Contract
description: Owner-action and mutation boundary for Harness-governed work
domain: harness/contracts
status: active
c: owner_approval_boundary
problem:
  - Implementation mutation can occur before the owner accepts the contract
  - Commit/push can close over unapproved work
s:
  - Represent owner approval as explicit packet state
  - Block commit/push unless owner approval is explicit
tags:
  - owner-approval
  - safety
  - mutation-boundary
owner_approval_boundary:
  - no implementation mutation before owner approval unless an executor packet explicitly authorizes the scope
  - no commit/push before explicit owner approval
prohibited_actions:
  - raw stdout/log archival as durable policy
  - Honcho-only policy creation without repo source_ref
---
# Contract

Owner approval is explicit, scoped, and auditable. A request to implement authorizes the implementation scope described by the current thread or packet; broader workspace changes, destructive operations, auth changes, commits, and pushes require their own approval signal unless the task packet explicitly includes them.

## Required packet shape

```yaml
owner_approval_boundary:
  implementation_scope: approved|blocked|owner-action-required
  commit: approved|blocked|owner-action-required
  push: approved|blocked|owner-action-required
  destructive_actions: blocked
  notes: [string]
```
