---
title: CPS-driven agent flow dogfood log
description: Evidence note retained from the retired adapter branch; records that role-style decomposition was insufficient and must be replaced by root_goal/task_AC CPS flow traces.
domain: harness
c: "Dogfood showed that organic workflow judgment requires explicit CPS transition traces, actor_binding responsibility, and task_AC evidence instead of only final conclusions."
problem: [P7, P8, P9, P11]
s: [S7, S8, S9, S11]
tags: [harness, cps, dogfood, evidence, flow-trace, retired-adapter]
relates-to:
  - harness/hn_cps_driven_workflow_system.md
status: evidence
created: 2026-06-12
updated: 2026-06-14
---

# CPS-driven agent flow dogfood log

This evidence was preserved while retiring `codex/hermes-adapter`.

Observed failure pattern:

```text
raw request
  -> role-style auto_decompose
  -> multiple child tasks
  -> shape-only CPS/AC metadata
  -> unclear responsibility for wrong flow transition
  -> missing evidence of whether CPS improved the decision
```

Baseline disposition:

- Use `root_goal_id` and `flow_graph_id` to preserve the root objective.
- Use node-local `task_AC` to show what each materialized task must prove.
- Use `actor_binding` to show why a researcher/coder/planner/reviewer was selected.
- Use `transition_reason` and `evidence_ref` to diagnose whether a bad outcome came from compile, routing, worker execution, handoff, review, or runtime enforcement.
- Promote only labeled, evidence-backed traces to future learning/template candidates.
