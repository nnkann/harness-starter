---
id: hn-lc-rpe-orchestrator-policy
project_id: harness-starter
domain: harness.role_enforcement
abbr: HN-LC-RPE
kind: implementation_ssot
naming_convention: hn_<domain>_<topic>_<artifact>.md
ssot_role: repo_ssot
lifecycle: active
status: active
updated: 2026-06-26
title: LazyCodex Role/Permission Enforcement and Orchestrator Policy
summary: Default keeps admin/recovery capability; hermes-kann orchestrates via Maat C-boundary, Thoth CPS compile, packet-bound actors, and operation guards.
tags: [harness, lazycodex, role-enforcement, orchestrator, cps, doc_ops, maat]
validation_refs:
  - /Users/kann/projects/harness-starter/.harness/project/docs/harness/hn_lazycodex_role_permission_enforcement_plan.md
  - /Users/kann/projects/harness-brain/projects/harness-starter/decisions/lazycodex-role-permission-enforcement-index.md
source_refs:
  - /Users/kann/projects/harness-starter/AGENTS.md
  - /Users/kann/projects/harness-starter/.harness/hermes/wrappers.yaml
  - /Users/kann/projects/harness-starter/.harness/hermes/workers.yaml
  - /Users/kann/projects/harness-starter/.harness/hermes/profiles.yaml
  - /Users/kann/projects/harness-starter/.harness/hermes/board-assignees.yaml
  - /Users/kann/projects/harness-starter/.harness/hermes/sandbox.yaml
  - /Users/kann/projects/harness-starter/.harness/hermes/cps-profile-routing.yaml
goal:
  id: G1
  statement: Keep real default usable for admin/recovery while routing Harness project work through hermes-kann orchestrator, Maat C-boundary, Thoth CPS compile, and packet-bound actors.
  closure_rule: Default does not need toolset removal; mutation is blocked by task packet, allowed_scope, owner boundary, operation guard, and Maat PASS.
cps:
  expression: C1 -> [P1,P2,P3,P4,P5] -> [S1,S2,S3,S4,S5] -> [AC1,AC2,AC3,AC4,AC5] -> G1
  context:
    id: C1
    summary: Default toolset lockdown blocked read/delegate/recovery; LazyCodex/Harness already models orchestration plus operation guards instead of disabling the runtime.
  problems:
    - id: P1
      order: 1
      text: Toolset-level default lockdown disables readback, delegation, and recovery.
    - id: P2
      order: 2
      text: Default had been acting as implicit orchestrator, causing direct interpretation and execution drift.
    - id: P3
      order: 3
      text: C-boundary was being assigned before Maat judged one-C vs multi-C cardinality.
    - id: P4
      order: 4
      text: Static role routing confused document judgment, implementation, evidence, and audit responsibilities.
    - id: P5
      order: 5
      text: CPS/doc_ops learning must be searchable without embedding audit/session/log bloat in core docs.
  solutions:
    - id: S1
      solves: [P1]
      operator: default_admin_recovery_restore
      text: Keep real default with normal tools; block only mutation actions through packet/guard/owner approval.
    - id: S2
      solves: [P2]
      operator: hermes_kann_orchestrator_profile
      text: Create hermes-kann as user-facing orchestrator/control-plane lane; default remains admin/recovery runtime.
    - id: S3
      solves: [P3]
      operator: maat_c_boundary_gate
      text: Maat decides C cardinality and document/task count before Thoth compiles CPS.
    - id: S4
      solves: [P4]
      operator: cps_operator_late_binding
      text: Route by S#.operator, required skills/resources/evidence/risk/scope, not by static role labels.
    - id: S5
      solves: [P5]
      operator: searchable_cps_doc_ops_metadata
      text: Preserve Goal, ordered P#, mapped S#, AC, routing, lifecycle, and learning tags in metadata/frontmatter; keep body concise.
  acceptance_criteria:
    - id: AC1
      judges: [S1]
      text: default config keeps read/search/file/terminal/delegation available; no repo mutation occurs without packet/guard/owner approval.
    - id: AC2
      judges: [S2]
      text: hermes-kann profile exists with SOUL that forbids implementation and requires routing through Maat/Thoth/packet actors.
    - id: AC3
      judges: [S3]
      text: Maat owns C-boundary and fails work lacking C cardinality judgment.
    - id: AC4
      judges: [S4]
      text: Handoff packets record concrete actor, operator reason, allowed_scope, forbidden_scope, owner_approval_boundary, and prohibited_actions.
    - id: AC5
      judges: [S5]
      text: This SSOT keeps searchable CPS/doc_ops metadata while excluding audit history, session ids, raw logs, long literal graphs, and open issue dumps.
---

# LazyCodex Role/Permission Enforcement and Orchestrator Policy

## Decision
Do **not** protect Harness by turning the real `default` runtime into a zero-tool profile. That blocks readback, delegation, recovery, and admin repair.

Use this split instead:

| Lane | Purpose | May do | Must not do |
|---|---|---|---|
| `default` | admin/recovery runtime | normal read/search/terminal/file/delegation/config repair when owner asks | act as project implementation worker or silent final gate |
| `hermes-kann` | CPS orchestrator/control-plane | receive intake, retrieve context, delegate, produce handoff/report | decide C-boundary, implement, patch docs/code, mutate git/cron/config for project work |
| `maat` | C-boundary and final gate | decide one C vs multiple C, audit Goal/AC/CPS/doc_ops/scope | implement or patch |
| `thoth` | CPS compiler | compile Maat-approved C into ordered P# -> S# -> AC -> Goal and routing packet | implement or self-pass |
| `seshat` | evidence/doc_ops input | source/doc_ops digest, freshness/confidence | stuff every ref into core docs or issue PASS |
| `sia` | cognitive continuity | recall similar CPS outcomes and failed routing patterns | mutate files or replace packet/gate |
| `ptah` | bounded apply | edit only packet-approved `allowed_scope` | decide document architecture or delete Goal/AC/CPS semantics |

## Required flow
1. `default` remains available for admin/recovery and routes owner-facing Harness work to `hermes-kann`.
2. `hermes-kann` captures the raw intake envelope and asks `sia`/`seshat` for recall/evidence signals when needed.
3. `hermes-kann` sends the request to `maat` for C-boundary judgment.
4. `maat` decides whether the request is one C or multiple C values. Document/task count follows that cardinality.
5. `thoth` compiles each Maat-approved C into ordered P#, mapped S#, AC, Goal closure, and candidate actor requirements.
6. Actor selection is late-bound from CPS operator needs, skills/resources/evidence/risk/scope, not from role labels alone.
7. Mutation goes only to a concrete actor with packet fields: `allowed_scope`, `forbidden_scope`, `owner_approval_boundary`, `prohibited_actions`, validation/evidence plan.
8. `maat` audits S# results against AC and Goal closure. No Maat PASS means HOLD/FAIL, not done.
9. Accepted outcomes become compact CPS learning events for GBrain/Honcho/SIA recall.

## Operation guard policy
Toolsets are not the primary safety boundary. Operation guards are.

Mutation-sensitive actions include file writes/patches, code execution, git commit/push, cron mutation, profile/config mutation, auth-sensitive operations, dependency installs, and destructive cleanup.

Before any such action:
- a packet_ref must exist;
- selected actor must be concrete;
- target path/action must be inside `allowed_scope` and outside `forbidden_scope`;
- owner approval must cover the boundary when required;
- Maat gate requirements must be known.

## DocOps rule
Core policy/contract docs keep the searchable equation and decision. They do **not** carry audit history.

Keep:
- `domain`, `abbr`, `kind`, `naming_convention`, `ssot_role`, `lifecycle`;
- Goal;
- ordered P#;
- mapped S#;
- AC judging S#;
- actor/routing/learning tags;
- concise source/artifact refs.

Remove from core body:
- session ids;
- validation_refs as history dumps;
- raw logs/stdout;
- long literal cps_flow_graph blocks;
- Mermaid diagrams used as proof;
- open-ended issue/laundry lists.

## Failure codes
Maat must fail with these codes when applicable:
- `FAIL_MISSING_C_BOUNDARY`
- `FAIL_STATIC_ROLE_ROUTING`
- `FAIL_MISSING_CPS_EXPRESSION`
- `FAIL_STRUCTURE_LOSS`
- `FAIL_SPLIT_OR_SLIM`
- `FAIL_SCOPE_VIOLATION`
- `FAIL_UNVERIFIED_GOAL_CLOSURE`

## Maat Compliance Matrix

| task_AC | Evidence | Verdict |
|---|---|---|
| AC1 | Repo SSOT preserves `default` admin/recovery with mutation guarded by packet/owner/Maat flow (`hn_lazycodex_role_permission_enforcement_plan.md:90-125`). | PASS |
| AC2 | `hermes-kann` SOUL exists and forbids implementation while routing through Maat/Thoth/packet actors (`/Users/kann/.hermes/profiles/hermes-kann/SOUL.md:12-17`, `:28-30`). | PASS |
| AC3 | Repo SSOT assigns C-boundary judgment to Maat and fails missing judgment (`hn_lazycodex_role_permission_enforcement_plan.md:107-115`, `150-158`). | PASS |
| AC4 | Repo SSOT requires concrete actor plus `allowed_scope`, `forbidden_scope`, `owner_approval_boundary`, and `prohibited_actions` in handoff packets (`hn_lazycodex_role_permission_enforcement_plan.md:110-128`). | PASS |
| AC5 | Repo SSOT keeps searchable CPS/doc_ops metadata and excludes audit/log bloat; GBrain index stays summary-only and points back to SSOT (`hn_lazycodex_role_permission_enforcement_plan.md:130-148`; `cp-lazycodex-role-permission-enforcement.md:32-45`). | PASS |

Reversibility: PASS — only bounded edits to the two approved existing docs; no git/config/profile/cron/dependency changes.

## Enforcement experiment design
Role instructions are advisory, not an authority boundary. A valid E2E must prove enforcement outside the model prompt:

| Layer | Requirement |
|---|---|
| launcher/tool surface | Gate/compile/recall lanes must start without write/patch capability for that task; this is per-task capability limiting, not global default lockdown. |
| capability packet | Ptah receives a two-file write capability only after Maat C-boundary and Thoth packet compile. |
| workflow gate | No Ptah run before Maat+Thoth artifacts exist; no completion before a separate Maat audit reads changed paths and validation evidence. |
| report hygiene | Final reports use one compact shape: status, changed paths, validation evidence, failures/warnings, owner actions. Do not repeat branch/cwd/session data in multiple sections. |

Failed E2E lesson: prompt-only read-only requests allowed Maat to patch files, so the next test must fail closed when a non-Ptah lane obtains write capability.

## Current implementation start
- `default` toolsets restored: `agent.disabled_toolsets: []`.
- `hermes-kann` profile is the intended orchestrator/control-plane lane.
- `hermes-kann` SOUL must enforce intake-only orchestration, Maat C-boundary, Thoth CPS compile, packet-bound actor delegation, and no direct mutation.
