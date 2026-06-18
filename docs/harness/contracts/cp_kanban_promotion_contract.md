---
title: Kanban Promotion Compiler Contract
description: Harness CPS board triage-to-todo promotion contract
domain: harness/contracts
status: active
c: kanban_promotion
problem:
  - Native auto-decompose can bypass CPS/frontmatter/source_ref requirements
  - Triage items can become todo nodes without audit gate
s:
  - Retain Kanban but route Harness CPS boards through a promotion compiler
  - Create packet/manifests/gate node before ready materialization
tags:
  - kanban
  - promotion-compiler
  - cps
owner_approval_boundary:
  - no implementation mutation before owner approval unless an executor packet explicitly authorizes the scope
  - no commit/push before explicit owner approval
prohibited_actions:
  - raw stdout/log archival as durable policy
  - Honcho-only policy creation without repo source_ref
---
# Contract

Kanban remains the state and dependency surface. Harness CPS boards MUST NOT allow native direct auto-decompose to create todo/ready nodes.

```yaml
kanban_policy:
  keep_kanban: true
  keep_auto_decompose: true
  native_auto_decompose_for_harness_boards: false
  harness_promotion_compiler_required: true
```

## Promotion sequence

```text
triage root
  -> harness_compile_triage(task_id)
  -> write root cps_packet artifact
  -> write doc_ops_manifest
  -> write honcho_ingest_manifest
  -> create compile/audit gate node
  -> create compact implementation/review nodes
  -> link nodes behind compile/audit gate
  -> promote root as graph container, not completed work
```
