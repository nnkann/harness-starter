# Harness-starter Hermes adapter baseline context

This repository's active Harness/Hermes SSOT branch is `hermes/harness-starter-baseline`.

## Canonical operating rule

- `hermes/harness-starter-baseline` is the canonical branch for Harness/Hermes adapter contracts, reference packs, and baseline docs.
- `main` is a default/upstream anchor, not the active mutation target unless the owner explicitly says so.
- Retired experimental branches such as `codex/hermes-adapter` must not be treated as merge targets.
- Branch, commit, push, auth-sensitive, and write-capable operations must pass the runtime context guard before action.

## Prompt canaries for optional context verification

- MAAT judges first.
- THOTH compiles the contract before fan-out.
- Failure is a CPS event.
- Truthful reporting rules.
- Hermes context-loading reality.

## Baseline contract vocabulary

- Root user outcome is `root_goal`.
- Child/node completion criteria are `task_AC`.
- C split produces a `cps_flow_graph`; children inherit root identity by reference.
- P/S expression steps are ordered; order, occurrence, consumes/emits, and dependencies can change the workflow meaning.
- Review checks artifacts; CPS audit checks graph/transition/actor-binding/learning correctness.
- Actor choice is `actor_binding` and must be justified by CPS/profile routing evidence.
- Actor binding is adaptive: templates suggest candidate pools, but actual agent invocation is late-bound by expression step, evidence obligation, risk, context, and outcome trace.
- Final completion requires graph closure evidence and LangSmith-style trace keys, not a role checklist.


## hermes-kann default runtime obligations

`hermes-kann` replaces the generic default for user-facing Harness work. It is not an optional wrapper.

```yaml
hermes-kann:
  role: default_user_facing_harness_runtime
  replaces: generic_default
  obligations:
    - digest_first_tool_use
    - cps_before_execution
    - owner_approval_boundary
    - project_context_routing
    - honcho_context_merge
    - raw_output_hygiene
```

Maat-style handoff compliance must run before completion claims for Harness CPS doc_ops / Honcho wiki / Kanban promotion work.

## Evidence acquisition contract

Harness task packets should make evidence needs explicit before tool use. THOTH must compile this for fan-out when a task involves inspection, debugging, validation, review, or triage. This section is CPS-shaped: `C` defines the context/decision needing evidence, `P` defines the uncertainty or risk being resolved, and `S` defines the minimal evidence strategy and output shape. This is not another guardrail; it is an acquisition contract that prevents unnecessary stdout requests from being made.

Required packet section:

```yaml
evidence_acquisition:
  mode: digest-first
  C:
    decision_context: "What CPS/task_AC decision will this evidence support?"
    scope_refs: [root_goal, task_AC, cps_flow_graph_node]
  P:
    uncertainty: "What is unknown, risky, or disputed?"
    failure_mode_if_wrong: "What silent failure or wasted work happens if we collect the wrong evidence?"
  S:
    evidence_strategy: "How to answer with the smallest sufficient signal"
    expected_signal:
      - exit_code | count | changed_paths | top_errors | timestamp_window | line_refs | artifact_refs
    stdout_shape: "bounded digest; no raw corpus by default"
    raw_artifact_policy: "only when task_AC requires raw evidence; save artifact and report path + reason + index/readback plan"
    prohibited_stdout:
      - full git diff
      - unbounded grep/rg/search results
      - broad log tails
      - sqlite/session dumps
      - full test output
      - recursive file lists
```

Raw terminal stdout is not a default evidence source. Commands should emit the answer-shaped signal needed for the CPS decision: counts, paths, timestamps, failing examples, exit codes, and line references. If the raw corpus is genuinely necessary, it belongs in an artifact reference with a digest, not in worker-visible context.
