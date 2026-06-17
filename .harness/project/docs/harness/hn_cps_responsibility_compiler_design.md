---
title: CPS responsibility compiler design
description: Defines the Harness compiler that translates triage C/P#/S# decisions into node-local todo responsibility contracts instead of copying CPS tags into child tasks.
domain: harness
c: "Harness triage must compile C/P#/S# decisions into responsibility-bearing graph nodes before todo materialization."
problem: [P7, P8, P9, P11]
s: [S7, S8, S9, S11]
tags: [harness, hermes, kanban, cps, compiler, triage, todo, responsibility, task-ac, actor-binding]
relates-to:
  - harness/hn_cps_driven_workflow_system.md
  - harness/hn_cps_first_harness_orchestration.md
related-files:
  - path: .harness/hermes/reference/ops/cps-ac.yaml
    rel: authoritative Goal/task_AC and CPS flow contract
  - path: .harness/hermes/reference/ops/cps-flow-audit.yaml
    rel: review/audit and adaptive actor-binding taxonomy
  - path: .harness/hermes/reference/examples/cps_adaptive_actor_binding.example.json
    rel: ordered CPS expression example
  - path: .harness/hermes/tools/cps_expression_lint.py
    rel: existing ordered-expression linter
  - path: .harness/hermes/agent-task.template.yaml
    rel: materialized task packet shape
  - path: .harness/schemas/agent-task.schema.yaml
    rel: task packet schema
status: design
created: 2026-06-17
updated: 2026-06-17
owner-approval-boundary:
  required-before:
    - mutating live Kanban tasks
    - enabling automatic promotion on a production board
    - changing Hermes gateway/dashboard runtime settings
    - committing or pushing implementation code beyond this design artifact
prohibited-actions:
  - Do not copy triage C/P#/S# blocks verbatim into every todo body.
  - Do not materialize todo children from role names alone.
  - Do not treat P# and S# as 1:1 scalar tags.
  - Do not let implementation children become ready before compile/audit responsibility is validated.
  - Do not rewrite or archive legacy tasks without a CPS disposition record.
cps:
  C: Triage C/P#/S# decisions are compiler input; executable todos must be responsibility nodes with local task_AC, actor_binding, and evidence obligations.
  P: [P7, P8, P9, P11]
  S: [S7, S8, S9, S11]
acceptance-criteria:
  - type: Solution AC
    ref: S7
    statement: The design defines a compiler packet that converts ordered C/P#/S# expression steps into node-local responsibility contracts with root_goal_id, flow_graph_id, node_id, task_AC, actor_binding, consumes, emits, and expected_evidence.
  - type: Solution AC
    ref: S8
    statement: The design records trace fields needed for later learning/template promotion without storing transient Kanban status as durable learning.
  - type: Solution AC
    ref: S9
    statement: The design separates artifact review from CPS audit and defines where compile, transition, actor-binding, and graph-closure audits occur.
  - type: Solution AC
    ref: S11
    statement: The design cites existing Harness SSOT files and avoids introducing divergent CPS/AC policy.
---

# CPS responsibility compiler design

## Goal

Build the missing Harness promotion layer between rough triage and executable todo work:

```text
triage C/P#/S# decision
  -> ordered CPS expression
  -> responsibility graph
  -> node-local todo packet
  -> evidence trace
  -> graph closure audit
```

The compiler does **not** copy `C`, `P#`, and `S#` into every child task as labels. It interprets them into the responsibility each child node owns.

## Current gap

Existing Hermes native decomposition accepts child tasks shaped like:

```json
{"title": "...", "body": "...", "assignee": "...", "parents": []}
```

That shape cannot preserve the Harness contract by itself because it has no first-class fields for:

```text
ordered expression step
role_in_expression
judgment_function
review_or_audit type
actor_binding rationale
consumes / emits
node-local task_AC
expected_evidence
transition trace
root graph closure
```

The current `cps-auto-decompose-guard` blocks the bad path on `harness_cps_v1` boards. This design defines the good path.

## Core rule

```text
C/P#/S# is compiler input.
Todo is compiler output.
```

A triage card may contain rough or final CPS judgment. The executable todo must contain the result of compiling that judgment into a node responsibility.

## Responsibility compiler responsibilities

### 1. Read triage decision

Input sources:

```text
- Kanban triage task title/body
- existing root_goal candidate
- C/P#/S# candidate or final selection
- owner boundary hints
- source_refs
- board metadata contract_kind=harness_cps_v1
```

The compiler must fail closed when the board is not a Harness CPS board unless explicitly run in `--dry-run --allow-non-harness-board` diagnostic mode.

### 2. Resolve C split

`C` is the first fan-out axis.

```text
If C implies distinct end-to-end outcomes:
  create/suggest separate root goals.

If C shares one end-to-end outcome:
  keep one root and create a cps_flow_graph under it.
```

Output:

```yaml
c_split_decision:
  mode: single_root | split_roots | blocked_owner_action
  reason: ...
  root_goal_id: rg_...
  split_root_candidates: []
```

### 3. Compile ordered P/S expression

`P#` are problem dimensions. `S#` are solution/workflow operators. They are many-to-many and order-sensitive.

The compiler produces expression steps:

```yaml
ordered_expression:
  - order: 10
    p: [P7]
    s: [S7]
    occurrence: 1
    role_in_expression: contract_compile
    judgment_function: audit.cps_compile
    review_or_audit:
      type: audit.cps_compile
      scope: [root_goal, task_AC, packet_shape]
    consumes: [triage_decision, source_refs]
    emits: [compiled_expression, task_packet_contract]
```

### 4. Bind actor responsibility

Actor selection is late-bound by the expression step, not static role checklist decomposition.

```yaml
actor_binding:
  mode: late_bound
  candidate_pool: [thoth, maat]
  selected:
    actor: thoth
    profile: ha_thoth
  selection_basis:
    - cps_expression_step
    - judgment_function
    - source_ref_authority
  alternatives_considered:
    - actor: maat
      reason_not_selected: final graph closure judgment not required at compile step
  rebind_triggers:
    - source_ref_conflict
    - missing_evidence
    - failed_audit
```

### 5. Generate node-local responsibility

Each expression step becomes one or more graph nodes only when it owns a distinct evidence obligation.

```yaml
nodes:
  - node_id: n_010
    expression_order: 10
    cps_ref:
      c: C_runtime_contract_repair
      p: [P7]
      s: [S7]
      occurrence: 1
    role_in_expression: contract_compile
    responsibility:
      owns:
        - compile the root Goal and ordered CPS expression into a valid task packet shape
        - emit missing contract fields if compilation is incomplete
      does_not_own:
        - implementation artifact changes
        - final root graph closure
        - owner approval override
    local_goal: Produce a valid responsibility graph packet for this triage root.
    task_AC:
      - root_goal_id and flow_graph_id are present.
      - every materialized node has node_id, cps_ref, actor_binding, task_AC, consumes, emits, and expected_evidence.
      - packet passes cps_expression_lint.py or reports explicit owner-action blockers.
    expected_evidence:
      - packet_ref
      - linter output
      - transition trace delta
```

### 6. Create graph edges

Edges represent responsibility dependencies and Kanban readiness gates.

```yaml
edges:
  - from_node: n_010
    to_node: n_020
    relation_type: unlocks
    condition: compile_verdict == pass
    handoff_payload_ref: packets/<run_id>/handoff_n010_n020.yaml
    unlock_policy: promote_child_when_parent_done
```

### 7. Materialize compact todo children

Kanban child bodies stay compact. Full graph data lives in `packet_ref`.

```markdown
## Harness task node

packet_ref: .harness/project/runs/<run_id>/cps_packet.yaml
root_goal_id: rg_...
flow_graph_id: fg_...
node_id: n_020
actor_binding: ha_ptah
cps_ref: C_runtime_contract_repair/P7/S7#2
responsibility: implement node-local packet materialization only

task_AC:
- Create only the output required by node n_020.
- Emit expected evidence refs listed in the packet.
- Do not close the root goal.

expected_evidence:
- ...
```

## Packet schema draft

The compiler writes:

```text
.harness/project/runs/<run_id>/cps_packet.yaml
```

Shape:

```yaml
version: 1
schema: harness-cps-responsibility-packet
source_task_id: t_...
board: harness-starter-project-hermes
contract_kind: harness_cps_v1
root_goal_id: rg_...
flow_graph_id: fg_...
root_goal: ...
source_refs: []
owner_boundary: []
global_constraints: []
closure_condition: ...

c_split_decision:
  mode: single_root
  reason: ...

ordered_expression:
  - order: 10
    p: [P7]
    s: [S7]
    occurrence: 1
    role_in_expression: contract_compile
    judgment_function: audit.cps_compile
    review_or_audit:
      type: audit.cps_compile
      scope: []
    actor_binding: {}
    consumes: []
    emits: []

nodes:
  - node_id: n_010
    expression_order: 10
    cps_ref: {}
    responsibility:
      owns: []
      does_not_own: []
    local_goal: ...
    task_AC: []
    actor_binding: {}
    input_refs: []
    output_refs: []
    expected_evidence: []

edges:
  - from_node: n_010
    to_node: n_020
    relation_type: unlocks
    condition: compile_verdict == pass
    handoff_payload_ref: ...
    unlock_policy: promote_child_when_parent_done

trace:
  trace_keys:
    - root_goal_id
    - flow_graph_id
    - node_id
    - task_id
    - actor_binding
    - cps_ref
    - task_AC
    - evidence_ref
    - transition_reason
    - outcome
```

## CLI design

Path:

```text
.harness/hermes/tools/harness_compile_triage.py
```

Commands:

```bash
python .harness/hermes/tools/harness_compile_triage.py dry-run --board harness-starter-project-hermes --task t_...
python .harness/hermes/tools/harness_compile_triage.py materialize --board harness-starter-project-hermes --task t_... --confirm
python .harness/hermes/tools/harness_compile_triage.py validate --packet .harness/project/runs/<run_id>/cps_packet.yaml
python .harness/hermes/tools/harness_compile_triage.py audit-board --board harness-starter-project-hermes --status active
```

### `dry-run`

Read-only. Emits the packet to stdout or `--out` without changing Kanban.

Required checks:

```text
- board exists
- board.contract_kind == harness_cps_v1
- task exists and is triage
- C/P#/S# candidates are parseable or owner-action is emitted
- ordered expression has at least one audit step and one review step unless blocked before execution
- actor_binding includes candidate_pool, selected, selection_basis, alternatives_considered, rebind_triggers
```

### `materialize`

Mutating. Requires `--confirm` and should be owner-approved before production use.

Actions:

```text
1. write cps_packet.yaml
2. create compile/audit gate child
3. create implementation/review child tasks as todo
4. add task_links according to graph edges
5. promote root triage to todo only after packet write succeeds
6. keep implementation children blocked behind compile/audit dependency
```

### `validate`

Read-only packet validation.

Should reuse/extend:

```text
.harness/hermes/tools/cps_expression_lint.py
```

Validation layers:

```text
- expression lint: existing cps_expression_lint.py rules
- responsibility lint: every materialized node owns exactly one local responsibility set
- packet lint: root_goal_id / flow_graph_id / node_id / task_AC / actor_binding / expected_evidence present
- edge lint: no cycles, every implementation node has a compile/audit predecessor unless explicitly owner-forced
```

### `audit-board`

Read-only board conformance report.

Find active Harness tasks missing responsibility contract fields:

```text
statuses: triage, todo, ready, running, review, blocked
flags:
  - missing_packet_ref
  - missing_node_id
  - missing_task_AC
  - missing_actor_binding
  - copied_CPS_without_responsibility
  - ready_without_compile_gate
```

## Kanban materialization strategy

Preferred graph:

```text
root triage task
  -> root todo task after compile

n_000 compile/audit gate
  -> ready first

n_010 implementation child
  -> todo, parent=n_000

n_020 review child
  -> todo, parent=n_010

n_900 graph closure audit
  -> todo, parent=n_020

root waits on terminal graph nodes
```

This uses native Kanban dependency semantics instead of a standing watcher.

## Review vs audit placement

```text
review.* nodes
  check artifact quality and node-local task_AC.

audit.* nodes
  check C split, ordered P/S expression, transition correctness, actor_binding, source_ref integrity, and graph closure.
```

A review pass must not close the root goal. Root closure requires graph closure audit.

## Implementation plan

### Phase 0 — lock scope

- Keep this implementation project-local under `.harness/hermes/tools/` and `.harness/project/docs/`.
- Do not modify Hermes core.
- Do not add a standing watcher.
- Do not enable production materialization until dry-run and validation pass on fixtures.

### Phase 1 — fixtures and tests

Create:

```text
.harness/hermes/tests/fixtures/cps_responsibility_triage_body.md
.harness/hermes/tests/fixtures/cps_responsibility_packet.valid.yaml
.harness/hermes/tests/fixtures/cps_responsibility_packet.invalid_copied_tags.yaml
.harness/hermes/tests/test_harness_compile_triage.py
```

Test cases:

```text
- dry-run parses C/P#/S# and emits ordered_expression
- P/S repeated occurrences remain distinct by order and occurrence
- copied C/P/S without responsibility fails validation
- static role checklist fails validation
- implementation node without compile/audit predecessor fails validation
- review-only graph without audit fails validation
- packet validates with existing cps_expression_lint.py
```

### Phase 2 — packet compiler library

Create:

```text
.harness/hermes/tools/harness_compile_triage.py
```

Internal functions:

```python
parse_triage_body(text) -> TriageDecision
compile_c_split(decision) -> CSplitDecision
compile_ordered_expression(decision) -> list[ExpressionStep]
bind_actors(steps, routing_policy) -> list[ExpressionStep]
materialize_nodes(steps) -> list[ResponsibilityNode]
materialize_edges(nodes) -> list[GraphEdge]
validate_packet(packet) -> list[str]
```

### Phase 3 — dry-run CLI

Implement read-only dry-run first.

Verification:

```bash
python .harness/hermes/tools/harness_compile_triage.py dry-run --fixture .harness/hermes/tests/fixtures/cps_responsibility_triage_body.md --json
python .harness/hermes/tools/cps_expression_lint.py .harness/hermes/tests/fixtures/cps_responsibility_packet.valid.yaml --json
python .harness/hermes/tests/test_harness_compile_triage.py
python .harness/hermes/loader.py validate-reference
```

### Phase 4 — board read adapter

Add read-only Kanban access behind an adapter so tests can use fixtures and production can read board tasks.

Rules:

```text
- production board access is read-only in dry-run
- do not import Hermes internals at module import time
- fail closed when board contract_kind is not harness_cps_v1
```

### Phase 5 — materialization mode behind explicit confirmation

Only after dry-run tests pass.

Required flags:

```text
materialize --confirm --board <board> --task <task_id>
```

Mutation sequence must be atomic where possible:

```text
write packet artifact first
create children with compact body
link dependencies
promote root
recompute ready only after compile gate dependency exists
```

### Phase 6 — board audit report

Add read-only conformance audit to identify legacy/contaminated active tasks.

Output JSON:

```json
{
  "board": "harness-starter-project-hermes",
  "contract_kind": "harness_cps_v1",
  "active_total": 0,
  "missing_packet_ref": [],
  "copied_cps_without_responsibility": [],
  "ready_without_compile_gate": []
}
```

## Validation commands

Before any commit/push of implementation:

```bash
python .harness/hermes/tests/test_harness_compile_triage.py
python .harness/hermes/tools/cps_expression_lint.py .harness/hermes/tests/fixtures/cps_responsibility_packet.valid.yaml --json
python .harness/hermes/loader.py validate-reference
python .harness/hermes/tools/verify_agents_context.py
git diff --check
```

## Success criteria

This design is implemented when:

```text
- dry-run converts triage C/P#/S# to responsibility graph packet
- copied-tag pseudo-packets fail validation
- child todos contain packet_ref and node-local task_AC, not full copied CPS blocks
- implementation nodes are dependency-gated behind compile/audit
- board audit can report legacy gaps without mutating tasks
- all validation commands pass
```

## Open questions

1. Whether first production materialization should create only a compile/audit gate node first, or create the full graph in `todo` with implementation children gated behind it.
2. Whether the compiler should require explicit `C:` / `P:` / `S:` fields in triage or allow heuristic extraction from prose.
3. Whether materialization should write packet artifacts under `.harness/project/runs/<run_id>/` or a board-local artifact directory when the work is not repo-mutating.
4. Whether actor profile resolution should read `.harness/hermes/cps-profile-routing.yaml` directly or receive a normalized profile roster from board metadata.

## Recommended next step

Implement Phase 1 and Phase 2 as TDD, keeping `materialize` disabled until fixture validation proves the compiler rejects copied CPS tags and static role checklist fan-out.
