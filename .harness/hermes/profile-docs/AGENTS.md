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
- Unresolved assignees must remain unresolved or blocked; no fallback profile may execute silently.

## The Lazy Dev's Ladder (Ponytail) operating rule

이 프로젝트는 '게으른 개발자의 사다리(The Lazy Dev's Ladder)' 철학을 Harness CPS(Context, Problem, Solution) 아키텍처에 적용하여 에이전트의 코드 변경 및 패키지 추가를 엄격히 통제합니다.

1. **C (Context - 1~4단계)**: YAGNI 검증, 기존 코드 재사용, Stdlib & Native API 우선 검토를 통해 신규 개발의 실제 필요 맥락을 분석합니다.
2. **P (Problem - 5단계)**: 신규 의존성 추가나 외부 라이브러리 도입 유혹을 해결해야 할 문제(Problem) 요인으로 정의하여 억제합니다.
3. **S (Solution - 6~7단계)**: 코드를 단일 함수나 단일 라인 수준으로 극한 단순화하고, 추가 LOC를 100라인 이내로 통제하여 최소 작동 구현체를 도출합니다.

에이전트는 태스크 패킷의 `lazy_dev_justification` 필드에 위 사다리 검증 결과를 입증해야 하며, `audit_ponytail_compliance.py` 감사를 통과해야 최종 프로모션이 승인됩니다.
