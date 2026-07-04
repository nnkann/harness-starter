---
title: Harness Session Reuse/Reclaim Local Implementation
description: Project-local session registry and trigger-based reclaim notes for harness-starter.
domain: harness/lifecycle
status: active
source_refs:
  - /Users/kann/projects/harness-brain/projects/harness-starter/contracts/cp_harness_session_reuse_reclaim.md
artifact_refs:
  - /Users/kann/projects/harness-starter/.harness/hermes/tools/session_registry.py
  - /Users/kann/projects/harness-starter/.harness/hermes/tools/session_reclaim.py
  - /Users/kann/projects/harness-starter/.harness/hermes/tools/lifecycle_runner.py
  - /Users/kann/projects/harness-starter/.harness/hermes/tools/cps_preflight_route_gate.py
owner_approval_boundary:
  - no Hermes core mutation
  - no writes to ~/.hermes/sessions/sessions.json or ~/.hermes/state.db
  - no standing watcher or blind hourly prune
---

# Harness Session Reuse/Reclaim Local Implementation

Harness owns session reuse/reclaim through a project-local registry:

```text
.harness/project/runs/session_registry.json
```

Hermes evidence remains read-only:

```text
~/.hermes/sessions/sessions.json
~/.hermes/state.db
```

The lifecycle runner updates the registry only at existing trigger points, starting with:

```text
.harness/hermes/tools/lifecycle_runner.py delegate --packet <packet>
```

No daemon, hourly watcher, or hidden physical Hermes cleanup is introduced.

## Lane key

Session lanes are keyed by:

```text
profile + platform + chat_id + thread_id/chat-level-key + project_slug
```

Unscoped project packets can be recorded, but project-scoped representative reuse requires a project slug.

## States

The registry distinguishes:

- `representative_open`
- `reusable_open`
- `stale_open`
- `duplicate_open_present`
- `orphan_route_present`
- `closed`
- `blocked_reclaim`

## Reclaim boundary

Logical reclaim is always project-local: registry state, reuse denial, reclaim candidates, and a manifest.

Physical Hermes cleanup is not automatic. When candidates exist, Harness writes:

```text
.harness/project/runs/session_reclaim_manifest.json
```

The manifest recommends an owner-approved bounded follow-up. If Hermes only exposes coarse cleanup, the manifest says so instead of pretending exact close semantics exist.

## Session policy evidence

`lifecycle_runner.py` attaches `session_policy` to `delegation_decision.json` and `handoff_snapshot.json`.

`cps_preflight_route_gate.py` includes `route_gate.session_policy` so reuse/reclaim state is visible in CPS evidence.
