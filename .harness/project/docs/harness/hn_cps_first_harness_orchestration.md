---
title: CPS-first Harness orchestration contract
description: Defines the baseline-branch Harness workflow where CPS compiles root_goal/task_AC flow graphs before actor fan-out, execution, review, and learning capture.
domain: harness
c: "Harness orchestration must start from CPS-grounded root_goal and graph contracts so Kanban automation supports judgment and learning rather than role-based fan-out."
problem: [P7, P8, P9, P11]
s: [S7, S8, S9, S11]
tags: [harness, hermes-adapter, baseline, cps, orchestration, root-goal, task-ac, flow-graph, learning-capture]
relates-to:
  - harness/hn_cps_driven_workflow_system.md
related-files:
  - path: .harness/hermes/reference/ops/cps-ac.yaml
    rel: authoritative-goal-ac-flow-contract
  - path: .harness/hermes/reference/pipeline.yaml
    rel: pipeline-gates
  - path: .harness/hermes/agent-task.template.yaml
    rel: task-packet-template
  - path: .harness/hermes/cps-profile-routing.yaml
    rel: actor-binding-policy
  - path: .harness/schemas/agent-task.schema.yaml
    rel: packet-schema
status: draft
created: 2026-06-09
updated: 2026-06-14
owner-approval-boundary:
  required-before: [changing_hermes_runtime_config, changing_dashboard_or_gateway_settings, committing_or_pushing]
prohibited-actions:
  - route_raw_harness_requests_directly_to_execution_workers
  - treat_code_review_as_cps_judgment_review
  - store_full_cps_or_ac_bodies_in_hermes_memory
  - copy_root_goal_into_child_task_AC_as_if_it_were_local_AC
cps:
  C: CPS-first orchestration must distinguish one root_goal from node-local task_AC and compile C split decisions into a searchable cps_flow_graph.
  P: [P7, P8, P9, P11]
  S: [S7, S8, S9, S11]
acceptance-criteria:
  - type: Solution AC
    ref: S7
    statement: Runnable packets expose root_goal_id, flow_graph_id, node_id, task_AC, actor_binding, owner boundary, related files, and expected evidence before execution.
  - type: Solution AC
    ref: S8
    statement: Learning capture records durable graph transition, routing, and task_AC lessons as stateful artifacts rather than transient Kanban status.
  - type: Solution AC
    ref: S9
    statement: Final completion requires artifact review plus CPS graph closure review using LangSmith-style trace labels.
  - type: Solution AC
    ref: S11
    statement: The authoritative Goal/AC flow contract remains .harness/hermes/reference/ops/cps-ac.yaml; documents summarize and cite it instead of drifting.
---

# CPS-first Harness orchestration contract

## Goal

Harness work must be driven by CPS judgment, not by automatic role fan-out.

Current baseline branch SSOT:

```text
hermes/harness-starter-baseline
```

The root request produces one or more `root_goal_id` values. Each root goal is compiled with CPS into a `cps_flow_graph`. Materialized child tasks carry `node_id`, `local_goal`, `task_AC`, `actor_binding`, input refs, output refs, and expected evidence. Children inherit the root goal by reference; they do not copy it as their local AC.

## Required flow

```text
T0 raw request
  -> T1 C/P/S extraction
  -> T2 C split decision
  -> T3 cps_flow_graph compile
  -> T4 actor_binding from CPS/profile routing
  -> T5 bounded packet execution with node-local task_AC
  -> T6 artifact review
  -> T7 CPS graph closure review
  -> T8 durable learning/template candidate capture
```

## Fan-out rule

Fan-out is allowed only when C or the ordered P/S expression requires separate evidence obligations. A role name is not a fan-out reason.

If C separates independent end-to-end outcomes, create separate triage roots with separate `root_goal_id` values. If the concerns share one end-to-end outcome, keep one root and represent the work as graph nodes/edges.

## Completion rule

A child task can only satisfy its own `task_AC`. The root goal closes only when graph evidence satisfies the root closure condition.

## Evaluation rule

Every materialized node must preserve enough trace data for later evaluation:

```text
root_goal_id, flow_graph_id, node_id, task_id, actor_binding,
cps_ref, task_AC, evidence_ref, transition_reason, outcome
```

Reviewer labels:

```text
root_goal_passed, task_AC_passed, evidence_sufficient,
actor_binding_correct, transition_correct, needs_rework,
blocked_owner_action
```
