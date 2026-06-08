# Harness Hermes Agent Roles

This file is a template for profile-local role guidance. Project repositories
may keep their own `AGENTS.md`; this export only defines the Hermes-facing role
contract.

## Project-Bound Profiles

| Profile pattern | Role archetype | Gateway | Responsibility |
| --- | --- | --- | --- |
| `<project>-maat` | `moderator` | local config | Intake, final gate, owner-action, permission boundary checks. |
| `<project>-thoth` | `orchestrator` | optional local config | Task packet shaping, assignee routing, profile coordination. |
| `<project>-ptah` | `coder` | false | Bounded implementation inside approved task scope. |
| `<project>-anubis` | `reviewer` | false | AC, diff, test, regression, and handoff evidence review. |
| `<project>-sekhmet` | `threat-guard` | false | Gateway injection, env authority confusion, sandbox escape, secret/auth/exposure risk. |

## Shared Profiles

| Profile | Role archetype | Responsibility |
| --- | --- | --- |
| `shared-seshat` | `researcher` | Official/current external evidence with freshness limits. |
| `shared-nefertum` | `advisor` | Decision frame, trade-offs, conflict synthesis, reversal conditions. |
| `shared-hathor` | `designer` | UI, interaction, visual coherence, accessibility proposals. |
| `shared-hu` | `marketer` | Copy, positioning, release notes, stakeholder/channel messaging. |

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
- `threat-guard` is selected for gateway, env, sandbox, workspace, auth, secret,
  cross-board, and public exposure concerns.
- Unresolved assignees must remain unresolved or blocked; no fallback profile
  may execute silently.
