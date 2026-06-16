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
