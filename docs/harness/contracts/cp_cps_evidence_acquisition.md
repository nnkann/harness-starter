---
title: CPS Evidence Acquisition Contract
description: Digest-first evidence acquisition contract for Harness-governed tasks
domain: harness/contracts
status: active
c: evidence_acquisition
problem:
  - Raw stdout/tool-output bloat
  - Premature git/log/sqlite/test dump collection
s:
  - Compile a CPS-shaped evidence acquisition contract before tool use
  - Prefer bounded signal output with source_ref-backed artifacts
tags:
  - cps
  - evidence
  - tool-output-hygiene
owner_approval_boundary:
  - no implementation mutation before owner approval unless an executor packet explicitly authorizes the scope
  - no commit/push before explicit owner approval
prohibited_actions:
  - raw stdout/log archival as durable policy
  - Honcho-only policy creation without repo source_ref
---
# Contract

Harness task packets MUST declare evidence_acquisition before fan-out or execution. Evidence is collected to support a CPS/task_AC decision, not to satisfy curiosity.

```yaml
evidence_acquisition:
  mode: digest-first
  C:
    decision_context: string
    scope_refs: [root_goal, task_AC, cps_flow_graph_node]
  P:
    uncertainty: string
    failure_mode_if_wrong: string
  S:
    evidence_strategy: string
    expected_signal: [exit_code, count, changed_paths, top_errors, timestamp_window, line_refs, artifact_refs, schema_field_presence]
    stdout_shape: bounded digest; no raw corpus by default
    raw_artifact_policy: save artifact and report path + reason when raw evidence is required
    prohibited_stdout: [full git diff, unbounded grep/search, broad log tails, sqlite/session dumps, full test output, recursive file lists]
```

Maat rejects packets whose first evidence step asks for raw terminal/git/sqlite/log/test output without a signal spec.
