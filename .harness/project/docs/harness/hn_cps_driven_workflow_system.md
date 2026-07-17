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
  - .harness/hermes/reference/ops/cps-flow-audit.yaml
  - .harness/hermes/reference/examples/cps_adaptive_actor_binding.example.json
  - .harness/hermes/tools/cps_expression_lint.py
  - .harness/hermes/reference/pipeline.yaml
  - .harness/hermes/agent-task.template.yaml
  - .harness/schemas/agent-task.schema.yaml
status: draft
created: 2026-06-12
updated: 2026-06-17
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

## Review vs audit

Review and audit are separate workflow operators.

```text
review = artifact/result quality inspection
        (diff, code, document, test result, security/performance/regression surface)

audit  = CPS flow judgment
        (root_goal, C split, ordered P/S expression, graph transition,
         actor_binding rationale, source_ref integrity, learning promotion)
```

Artifact review can show that a node's output is good. It does **not** prove that the root `cps_flow_graph` is closed. CPS audit can accept, reject, split, rebind, or block the next transition even after artifact review passes.

## Adaptive actor binding

Agents are not called because a remembered template says a role always appears. Templates may suggest common actor pools, but the actual invocation is late-bound by the current expression step.

```text
ordered C/P/S expression
  -> judgment_function
  -> review_or_audit type
  -> candidate actor pool
  -> selected actor + alternatives + rebind triggers
  -> actor_binding_trace
```

Required binding fields:

```text
mode
candidate_pool
selected
selection_basis
alternatives_considered
rebind_triggers
```

A binding may change when new evidence appears: missing evidence, new security signal, owner boundary, failed review/audit, external facts, stale context, source_ref conflict, or actor/tool unavailability.

Example: the same `P7/S9` step can bind to Maat for purpose closure, Sekhmet for owner/security boundary, Anubis for node-local artifact validation, or a researcher when external facts dominate. The CPS expression records why the chosen actor was right for this step, not that a role is always right for that P/S pair.

## Linter contract

`.harness/hermes/tools/cps_expression_lint.py` validates design packets against the first executable guardrails:

```text
- ordered expression exists
- P/S are non-empty lists, not 1:1 scalar tags
- review.* and audit.* are both represented
- review_or_audit.type matches judgment_function
- actor_binding has candidate pool, selected actor, selection basis, alternatives, and rebind triggers
- source_refs are present
```

The linter intentionally warns/fails on static-looking 1:1 mappings so CPS packets do not regress to role checklist decomposition.

## Legacy adapter branch disposition

The former `codex/hermes-adapter` branch contained useful design evidence, but its files predate the baseline Goal/AC flow contract. Its content should be treated as evidence input, not as a merge target.
