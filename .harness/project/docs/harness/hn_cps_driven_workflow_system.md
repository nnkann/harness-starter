---
title: CPS-driven Harness workflow system
description: Captures the desired CPS workflow engine where C drives root splitting and ordered P/S expressions produce cps_flow_graph nodes, actor bindings, task_AC, reviews, and learning templates.
domain: harness
c: "Harness must express realistic concern decomposition through CPS flow graphs instead of role-checklist decomposition."
problem: [P7, P8, P9, P11]
s: [S7, S8, S9, S11]
tags: [harness, cps, workflow-engine, c-split, task-ac, langsmith, learning, orchestration]
relates-to:
  - harness/hn_cps_first_harness_orchestration.md
related-files:
  - .harness/hermes/reference/ops/cps-ac.yaml
  - .harness/hermes/reference/pipeline.yaml
  - .harness/hermes/agent-task.template.yaml
  - .harness/schemas/agent-task.schema.yaml
status: draft
created: 2026-06-12
updated: 2026-06-14
cps:
  C: CPS-driven workflow generation must be compact enough to operate but expressive enough for repeated/many-to-many P#/S# combinations, actor calls, moderation, recursion, and learning.
  P: [P7, P8, P9, P11]
  S: [S7, S8, S9, S11]
acceptance-criteria:
  - type: Problem AC
    ref: P7
    statement: Fan-out is justified by C split and ordered P/S expression obligations, not by fixed role checklist expansion.
  - type: Solution AC
    ref: S7
    statement: Runnable task packets carry root_goal_id, flow_graph_id, node_id, task_AC, actor_binding, and expected evidence.
  - type: Solution AC
    ref: S8
    statement: Completed flows emit reusable learning candidates as case/template artifacts, not transient Kanban status memories.
  - type: Solution AC
    ref: S9
    statement: CPS judgment/audit is distinct from artifact quality review and may occur multiple times in one expression.
  - type: Solution AC
    ref: S11
    statement: Policy SSOT remains the reference contract; schemas/routing/profile files implement or reference it rather than duplicating divergent rules.
prohibited-actions:
  - Do not treat C/P/S as decorative tags.
  - Do not assume P# and S# are 1:1 pairs.
  - Do not auto-create Anubis/Sekhmet/Maat/Ptah tasks merely because those roles exist.
  - Do not archive or complete old blocked/todo tasks without a CPS disposition record.
  - Do not store transient Kanban progress as durable learning.
---

# CPS-driven Harness workflow system

## Core model

`C` is the first fan-out axis. If it separates independent end-to-end outcomes, create separate roots. Otherwise keep one root and materialize a `cps_flow_graph` under that root.

`P#` identifies problem dimensions. `S#` identifies solution/workflow operators. They are many-to-many and position-dependent.

Example:

```text
C_blocked_recovery
  1. P7/S7   compile root_goal + node task_AC contract
  2. P9/S9   preflight CPS judgment
  3. P7/S7   materialize bounded actor packet
  4. P11/S11 check SSOT drift
  5. P9/S9   final graph closure audit
  6. P8/S8   promote learning/template candidate
```

## Node materialization

A graph node becomes a todo/review/final gate only when it has:

```text
node_id
cps_ref
operator
actor_binding
local_goal
task_AC
input_refs
output_refs
expected_evidence
```

## Runtime flow trace

Each transition appends a compact trace delta:

```text
root_goal_id
flow_graph_id
node_id
task_id
actor_binding
transition_reason
evidence_ref
outcome
```

This trace is the basis for LangSmith-style evaluation of whether CPS improved routing, handoff, evidence closure, and actor selection.

## Legacy adapter branch disposition

The former `codex/hermes-adapter` branch contained useful design evidence, but its files predate the baseline Goal/AC flow contract. Its content should be treated as evidence input, not as a merge target.
