---
title: WIP-to-Kanban integration policy
domain: harness
c: "Hermes Kanban scheduling and legacy Harness WIP/domain-folder completion now both claim work ownership and can double-process or falsely complete the same item"
problem: [P3, P6, P7, P11]
s: [S3, S6, S7, S11]
tags: [kanban, wip, workflow]
relates-to:
  - path: .claude/rules/docs.md
    rel: references
  - path: docs/harness/hn_frontmatter_parser_drift.md
    rel: references
status: completed
created: 2026-06-05
updated: 2026-06-05
---

# WIP-to-Kanban integration policy

## Goal

Unify the legacy Harness WIP/document completion workflow with Hermes Kanban
without creating two competing state machines. Kanban should schedule and audit
execution. WIP/docs should remain the project SSOT for CPS, domain ownership,
completion evidence, and durable knowledge.

## Before

Legacy Harness treated `docs/WIP/` as the active queue.

1. A worker created or reopened a WIP document.
2. The WIP frontmatter carried `domain`, CPS `c`/`problem`/`s`, tags, status,
   and dates.
3. The body carried Goal, AC, implementation notes, decisions, and verification.
4. Completion changed the WIP to `status: completed`.
5. Commit-time tooling moved the WIP into the final domain-aware docs folder with
   `docs_ops.py move`, updated clusters, and sealed the completed doc.

Hermes Kanban adds task rows, decomposition, dependencies, worker claims, run
logs, comments, and board completion. Those are useful execution primitives, but
they can mark work done before the WIP/doc contract is complete.

## Unified Policy

1. **Scheduling owner:** Hermes Kanban owns queue state, dependency graph,
   assignment, claim/run records, workspace path, retries, and operational logs.
2. **Governance owner:** Harness docs own CPS, domain taxonomy, acceptance
   criteria, durable decisions, incidents, guides, and completed knowledge.
3. **Source of truth rule:** If a task changes project policy, code behavior, or
   downstream-visible knowledge, the Kanban task must carry or create a WIP/doc
   contract before it is considered complete.
4. **Small operational exception:** Pure operational board work that has no
   durable project knowledge may complete with a Kanban result only. The result
   must explicitly say no docs/WIP artifact was required.
5. **No bidirectional auto-ownership:** `wip_sync.py` is an inventory and bridge
   signal, not a second executable owner. It may create held mirror cards and
   invalid-WIP reports, but it should not race live Kanban decomposition.

## Flow After Integration

### Intake

- Rough dashboard/triage text may enter Kanban first.
- Before executable child cards become `ready`, harness-governed work must have a
  `doc_contract` in task metadata or body:
  - `wip_path` or `doc_required: false` with reason
  - CPS `c`, `problem`, `s`
  - target folder or domain when a final doc is expected
  - acceptance criteria and verification expectation
- Invalid or incomplete doc contracts stay held as `todo`/`todo-hold` or blocked
  with a reason naming the missing fields.

### Execution

- Workers use Kanban for assignment and dependency ordering.
- Workers use the WIP/doc contract for completion criteria.
- Scratch workspaces may be used for investigation notes, but durable policy,
  rollout, or downstream evidence must be written into repo docs or task
  metadata before completion.

### Completion

A Kanban task may be marked complete only when one of these is true:

- The WIP/doc contract is satisfied, relevant AC is checked or explicitly
  measured, and the final doc movement/cluster update is either complete or
  recorded as a required follow-up.
- The task is operational-only and records `doc_required: false` plus the reason.
- The task is a blocked/invalid intake item and records the exact missing
  frontmatter, CPS, AC, status, or environment prerequisite instead of creating a
  normal todo.

Completion metadata should include:

```json
{
  "doc_contract": {
    "doc_required": true,
    "wip_path": "docs/WIP/harness--hn_example.md",
    "target_folder": "docs/harness",
    "domain": "harness",
    "validation_status": "passed",
    "completion_evidence": "docs-validate 0 errors; AC checked"
  }
}
```

### Migration

- Existing WIP files remain authoritative for project governance.
- Existing Kanban tasks that came from WIP sync should keep stable
  `idempotency_key` links to their source WIP.
- Existing Kanban tasks without WIP contracts should be classified before work:
  operational-only, needs WIP/doc contract, invalid intake, or already covered by
  a completed child result.
- `completed` legacy task status must be normalized or treated as terminal by
  dependency gates; otherwise children can stay in `todo` despite completed
  prerequisite work.

## Responsibilities

| Surface | Responsibility |
| --- | --- |
| Hermes Kanban | scheduling, dependency graph, claims, retries, run metadata, dirty workspace reporting |
| `hermes_cli/wip_sync.py` | conservative WIP inventory, invalid-WIP blocking, held mirror cards |
| Harness docs rules | frontmatter, CPS, AC, domain/folder contract, completed-doc sealing |
| Harness skills/templates | when to create/update WIP docs and what completion evidence to write |
| Commit/docs tooling | `docs_ops.py move`, reverse-link updates, cluster refresh, pre-check gates |

## Required Follow-Up Tasks

- Hermes runtime should attach and preserve `doc_contract` metadata for
  harness-governed Kanban tasks.
- Hermes dependency logic should treat legacy `completed` status consistently or
  migrate it to `done`.
- Harness templates should teach workers the split: Kanban status is not enough
  for project-governed completion.
- Rollout guidance should tell downstreams how to classify existing WIPs and
  board tasks during migration.

**Acceptance Criteria**:
- [x] Goal: one integrated policy defines how rough ideas/WIPs move through
  Kanban, docs, domain ownership, and completion.
  검증:
    review: self
    tests: 없음
    실측: policy describes before/after flow, source-of-truth split,
      completion metadata, and migration handling.
- [x] Problem AC (P3/P6): completion cannot be claimed solely from board status
  when project docs evidence is required.
- [x] Solution AC (S7/S11): owner surfaces are separated and duplicate state
  machines are assigned explicit roles.
- [x] Guardrail AC (P11): Hermes runtime implementation and harness template
  updates are left as separate dependent tasks because they depend on this
  policy, not because the policy is incomplete.
