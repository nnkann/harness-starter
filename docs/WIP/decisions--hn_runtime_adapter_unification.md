---
title: 다중 runtime adapter 통합 관리
domain: harness
c: "Claude 구독/OAuth가 기본 전제가 아니게 되었고, 실제 운영 기본 조합이 Hermes + Codex + Agy로 이동했다. 기존 .claude 중심 본체와 .agents/.codex bridge를 방치하면 runtime drift와 downstream silent fail이 커진다."
problem: [P3, P5, P7]
s: [S3, S5, S7]
tags: [runtime, adapter, hermes, codex, agy, claude, downstream]
status: in-progress
created: 2026-05-26
relates-to:
  - path: WIP/guides--hn_hermes_integration.md
    rel: extends
  - path: WIP/decisions--hn_hermes_managed_downstream_memory.md
    rel: references
  - path: WIP/decisions--hn_git_subtree_policy.md
    rel: references
  - path: ../decisions/hn_runtime_ssot_generation.md
    rel: supersedes
  - path: ../harness/hn_codex_port.md
    rel: references
---

# 다중 runtime adapter 통합 관리

## 결정

하네스는 특정 agent runtime의 파일 묶음을 병렬로 방치하지 않는다.
공통 하네스 계약과 runtime adapter를 분리하고, downstream마다 runtime 조합을 manifest로 표현한다.

현재 기본 pilot stack은 다음과 같다.

```yaml
runtime_stack: hermes-codex-agy
runtime_adapters:
  hermes: orchestrator
  codex: executor
  agy: advisor
  claude: optional-adapter
```

Claude Code는 더 이상 기본 운영 전제가 아니다. 다만 기존 구현과 downstream 호환성 때문에 `.claude/`를 즉시 폐기하지 않는다.
이번 wave의 정책은 **`.claude`를 현재 구현 본체로 보존하되, 설계상으로는 runtime adapter 후보로 강등**하는 것이다.

## 책임 분리

| 계층 | 책임 | 현재 위치 | 방향 |
|---|---|---|---|
| Harness core | 정책, 문서 계약, safety guard, upgrade 계약, project lifecycle | `.claude/rules`, `.claude/scripts`, `docs/harness`, `docs/WIP` | 장기적으로 runtime-neutral contract로 추출 |
| Runtime adapter | 각 agent가 읽는 진입 파일·스킬·agent 정의·hook 표현 | `.claude`, `.agents`, `.codex`, `.antigravitycli`, Hermes skills/cron | generated/validated output 또는 manual overlay로 분류 |
| Hermes orchestration | downstream registry, cron, memory/session_search, cross-runtime review routing | Hermes profile/skills/cron | first-class 운영 계층 |
| Downstream manifest | project path, branch, cadence, runtime_stack, subtree 후보, owner action | `.claude/HARNESS.json` + Hermes manifest | 둘 중 하나가 아니라 상호 참조 |

## 표면 분류 초안

| 표면 | 분류 | 현재 판단 |
|---|---|---|
| `CLAUDE.md` | runtime adapter / manual overlay | Claude adapter. downstream 사용자 커스터마이징을 존중한다. |
| `AGENTS.md` | runtime adapter / manual overlay | Codex 진입점. Hermes + Codex 기본 stack에서 중요하다. |
| `.claude/HARNESS.json` | manifest | version/profile뿐 아니라 `runtime_stack`, `runtime_adapters`를 가진다. |
| `.claude/scripts/**` | core + adapter 혼합 | guard/pre-check/docs tooling은 core. Claude hook wrapper는 adapter. |
| `.claude/rules/**` | core 후보 | 현재는 Claude 형식이지만 정책 내용은 runtime-neutral로 추출 가능하다. |
| `.claude/skills/**` | adapter + source legacy | 현재 source 역할. 장기적으로 common contract에서 생성/검증. |
| `.claude/agents/**` | adapter + role source legacy | Hermes delegation preset과 Codex agent bridge의 입력 후보. |
| `.agents/skills/**` | generated/validated Codex adapter | 수동 mirror로 방치하지 않는다. `.claude/skills`와 drift audit 대상. |
| `.codex/agents/*.toml` | generated/validated Codex adapter | 얇은 bridge로 유지. `.claude/agents`와 1:1 검증. |
| `.codex/hooks.json` | opt-in adapter | schema 안정 전 기본 비활성 유지. |
| `.antigravitycli/**` | optional Agy/Antigravity adapter 후보 | repo-local 기본 배포 surface가 아니라 Hermes/Agy adapter에서 시작. |
| Hermes skills/cron/profile | runtime/orchestration adapter | repo-local 파일 복사가 아니라 loader/wrapper/guardian 역할. |

## 통합 원칙

1. **기본 조합은 Hermes + Codex + Agy다.** Hermes가 조율하고, Codex가 실행/검토하고, Agy가 advisory/adversarial reviewer로 보완한다.
2. **Claude는 optional adapter다.** 구독/OAuth availability를 전제하지 않는다.
3. **삭제보다 통합 관리가 우선이다.** `.agents`나 `.codex`가 존재해도 되지만, source 없이 수동 복제물로 방치하면 안 된다.
4. **runtime-specific 출력은 검증 가능해야 한다.** 같은 역할 계약이 런타임별 표현에서 의미 drift를 만들면 pre-check 또는 dedicated test가 실패해야 한다.
5. **downstream마다 stack을 manifest로 드러낸다.** StageLink pilot은 `hermes-codex-agy`로 시작하고, 다른 downstream은 `codex-only`, `claude-codex`, `hermes-only-guardian` 같은 profile로 확장한다.
6. **subtree/worktree 정책과 분리한다.** runtime adapter 통합은 agent surface 문제이고, subtree는 외부 component sync 정책이다. 두 정책 모두 manifest에 실을 수 있지만 같은 결정이 아니다.

## Phase plan

### Phase 0 — manifest와 문서 계약

- `.claude/HARNESS.json`에 `runtime_stack`과 `runtime_adapters`를 추가한다.
- `downstream-readiness.sh`가 runtime stack/adapters를 관측 출력한다.
- README에서 Claude-only 본체 표현을 제거하고 다중 adapter 관점으로 바꾼다.
- Hermes 통합 WIP가 `.claude/.agents`를 SSOT로 단정하지 않게 보정한다.

### Phase 1 — drift audit

- `.claude/skills/**` vs `.agents/skills/**` diff를 runtime wording과 행동 계약 차이로 분류한다.
- `.claude/agents/**` vs `.codex/agents/*.toml` 1:1 계약을 기존 `test_codex_agents.py`에서 유지한다.
- `runtime_stack`별 필수 adapter presence matrix를 만든다.

### Phase 2 — generated/overlay 후보 결정

- 가벼운 overlay 방식과 generator 방식을 비교한다.
- Codex adapter부터 generated output으로 전환할지 결정한다.
- Claude adapter는 기존 동작 보존을 최우선으로 두고 마지막에 전환한다.

### Phase 3 — Hermes first-class 운영

- Hermes skill은 project-local skill 복사가 아니라 loader/wrapper로 둔다.
- Hermes cron guardian은 runtime stack을 읽고 사용 가능한 reviewer(Codex/Agy/Claude)를 선택한다.
- StageLink pilot에서 `hermes-codex-agy` profile을 검증한다.

## Validation

- `python3 -m pytest .claude/scripts/tests/test_downstream_readiness.py -q`
- `python3 -m pytest .claude/scripts/tests/test_codex_agents.py -q`
- `python3 .claude/scripts/docs_ops.py validate`
- `python3 .claude/scripts/docs_ops.py verify-relates`
- `bash .claude/scripts/downstream-readiness.sh`

**Acceptance Criteria**:

- [x] Goal: Claude 중심 표면을 방치하지 않고 다중 runtime adapter 통합 관리 방향으로 재정의한다.
  검증:
    review: self + Codex/Agy advisory 가능
    tests: `python3 -m pytest .claude/scripts/tests/test_downstream_readiness.py -q`; `python3 .claude/scripts/docs_ops.py validate`; `python3 .claude/scripts/docs_ops.py verify-relates`
    실측: HARNESS.json과 downstream-readiness 출력에서 `hermes-codex-agy` stack이 드러난다.
- [x] S3: downstream silent fail을 줄이도록 runtime stack/adapters를 manifest와 readiness report에 노출한다.
- [x] S5: runtime별 skill/agent 복제를 source로 방치하지 않고 generated/validated adapter 후보로 분류한다.
- [x] S7: Hermes orchestration, harness core, runtime adapter, downstream manifest의 책임 경계를 표로 분리한다.
- [ ] `.claude/skills`와 `.agents/skills` drift audit을 별도 산출물로 만든다.
- [ ] StageLink의 Hermes manifest가 `runtime_stack: hermes-codex-agy`를 읽어 guardian/report에 반영한다.
