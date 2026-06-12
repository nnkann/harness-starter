# Harness Hermes Agent Roles

This file is a template for profile-local role guidance. Project repositories
may keep their own `AGENTS.md`; this export only defines the Hermes-facing role
contract.

## Project-Bound Profiles

| Profile pattern | Role archetype | Gateway | Responsibility |
| --- | --- | --- | --- |
| `<abbr>_maat` / `<project>-maat` | `moderator` | local config | Intake, final gate, owner-action, permission boundary checks. |
| `<abbr>_thoth` / `<project>-thoth` | `orchestrator` | optional local config | Task packet shaping, assignee routing, profile coordination. |
| `<abbr>_ptah` / `<project>-ptah` | `coder` | false | Bounded implementation inside approved task scope. |
| `<abbr>_anubis` / `<project>-anubis` | `reviewer` | false | AC, diff, test, regression, and handoff evidence review. |
| `<abbr>_sekhmet` / `<project>-sekhmet` | `threat-guard` | false | Gateway injection, env authority confusion, sandbox escape, secret/auth/exposure risk. |

## Shared Profiles

| Profile | Role archetype | Responsibility |
| --- | --- | --- |
| `seshat` | `researcher` | Official/current external evidence with freshness limits. |
| `nefertum` | `advisor` | Decision frame, trade-offs, conflict synthesis, reversal conditions. |
| `hathor` | `designer` | UI, interaction, visual coherence, accessibility proposals. |
| `hu` | `marketer` | Copy, positioning, release notes, stakeholder/channel messaging, and advisory workflow-efficiency/lap-time/model-tier probes when CPS triggers them. |

## Routing Rules

- `task.assignee` must be a concrete Hermes profile name or a registered local
  lane id.
- Role archetypes classify intent; they are not assignee identities.
- Shared profiles are proposal-only unless a local Hermes profile config gives
  them explicit project authority.
- Direct specialists should be selected before `advisor` when there is a single
  evidence axis.
- `advisor` is used for conflict, one-way decisions, architecture trade-offs,
  CPS ambiguity, or blocked execution caused by missing judgment.
- `hu` is used for advisory efficiency-speed probes when CPS P#/S# or the owner
  raises lap time, quota, fan-out, duplicate probe, over-review, or model-tier
  concerns; Hu cannot approve completion or override CPS/final gate authority.
- `threat-guard` is selected for gateway, env, sandbox, workspace, auth, secret,
  cross-board, and public exposure concerns.
- Unresolved assignees must remain unresolved or blocked; no fallback profile
  may execute silently.
