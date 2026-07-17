---
title: CPS-driven blocked todo disposition evidence
description: Evidence note retained from the retired adapter branch; records how blocked or newly discovered tasks should be classified as inline, merge, prerequisite, split, escalate, or block through CPS graph transitions.
domain: harness
c: "When work discovers additional tasks, the deciding agent must classify the transition and record why the flow continued, split, merged, blocked, or escalated."
problem: [P7, P8, P9, P11]
s: [S7, S8, S9, S11]
tags: [harness, cps, blocked, disposition, evidence, retired-adapter]
relates-to:
  - harness/hn_cps_driven_workflow_system.md
status: evidence
created: 2026-06-12
updated: 2026-06-14
---

# CPS-driven blocked todo disposition evidence

Additional work discovered during execution is not automatically a stop, a merge, or a new root. It must be classified as a graph transition.

Disposition options:

```text
inline        same node can satisfy task_AC without changing root closure
merge         duplicate/overlapping node evidence should be consolidated
prerequisite  a new node must complete before current node can close
split         C reveals a separate root_goal or independent evidence obligation
escalate      owner/moderator decision is required
block         required evidence or permission is unavailable
```

Required trace fields:

```text
root_goal_id
flow_graph_id
current_node_id
observed_signal
disposition
transition_reason
responsible_decision_node_owner
next_payload_ref
evidence_ref
```

Purpose: reduce recurrence by locating failure at the graph point where it happened, not by assigning blame after the fact.
