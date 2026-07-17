---
title: Harness runtime 외부화와 Hermes core 비수정 경계
domain: harness
c: "Harness는 buildable runtime·contract·adapter를 소유하고, Hermes는 공식 확장점으로만 연결되는 교체 가능한 execution host여야 한다."
problem: [P2, P3, P5, P7, P8, P11]
s: [S2, S3, S5, S7, S8, S11]
tags: [harness, hermes, runtime, boundary, build, state, git]
relates-to:
  - path: harness/hn_harness_core_overlay_binding.md
    rel: supersedes
  - path: decisions/hn_worktree_policy.md
    rel: references
status: in-progress
created: 2026-07-17
updated: 2026-07-17
---

# Harness runtime 외부화와 Hermes core 비수정 경계

## 결정

Harness의 정책·프로젝트 binding·CPS state·receipt·durable artifact는 Harness가 소유한다. Hermes는 Harness를 실행하는 host/adapter이며, Harness 기능을 Hermes core의 gateway, session, prompt, state 코드에 직접 구현하지 않는다.

다음 규칙은 예외 없이 적용한다.

1. Hermes repo에는 commit하거나 push하지 않는다.
2. Hermes core에는 추가 수정하지 않는다. `AGENTS.md`, `SOUL.md`, 그리고 두 파일이 명시적으로 참조하는 정책 파일만 local instruction surface로 취급한다.
3. 이미 존재하는 Hermes core 변경은 production change나 Git closure 대상으로 만들지 않는다. 대체 Harness 경로가 검증될 때까지 forensic/experimental evidence로만 보존한다.
4. generic upstream extension이 꼭 필요하면 Harness 전용 patch가 아니라 upstream이 소유하는 일반 계약 후보로 보고한다. owner가 명시 승인하기 전에는 적용하지 않는다.
5. Git closure와 push는 Harness-starter repo에만 적용한다.

## 문제와 경계

Hermes gateway/session 내부에 project cwd, session binding, compression 보존을 넣으면 Harness의 policy change가 live gateway restart와 같은 failure domain을 공유한다. 이 결합은 프로젝트 workflow 변경을 transport/session failure로 확대한다.

Hermes generic gateway hook은 현재 observer 성격이며, source identity를 받아 session/workdir를 동기적으로 결정하는 pre-session resolver contract는 확인이 필요하다. 따라서 자동 cwd binding을 core patch로 계속 확장하지 않는다. 공식 resolver가 확인되기 전까지는 이 전환을 미완료 dependency로 유지한다.

Hermes의 built-in compression persistence는 별도 기능이다. Harness는 이를 재구현하거나 임의 context engine으로 교체하지 않는다. persistence 공백이 실제로 입증된 경우에만 공식 plugin/provider 경계를 검토한다.

## 소유권

| 대상 | 소유자 | Git 대상 | 원칙 |
|---|---|---|---|
| 장기 정책·architecture rationale·도메인 문서 | Harness Brain | Harness-starter 복사본 아님 | canonical authority |
| 실행 가능한 schema·contract·runtime source·adapter·test | Harness-starter | commit/push 대상 | buildable runtime |
| Hermes profile instruction | Hermes local binding | core repo 대상 아님 | AGENTS/SOUL 및 참조 파일만 |
| Hermes gateway/session/prompt/state 구현 | Hermes upstream | Harness가 commit/push하지 않음 | 공식 extension만 사용 |
| receipt·SQLite·registry·checkpoint·lock·stdout/stderr | external runtime state | commit하지 않음 | source와 물리 분리 |
| review/merge가 필요한 durable deliverable | 명시적 export artifact 또는 Harness Brain | 목적에 따라 별도 | transient state와 구분 |

## 목표 구조

```text
Harness Brain
  └─ canonical policy / decision / domain authority

harness-starter
  ├─ contracts/       versioned machine-readable contracts
  ├─ runtime/         buildable Harness runtime
  ├─ adapters/        Hermes/Codex/Claude/AGY thin adapters
  ├─ templates/       source-controlled seed data
  ├─ tests/fixtures/  reproducible test data
  ├─ tests/           isolated verification
  └─ .harness/project/manifest.yaml

external state root
  └─ <profile>/<project-slug>/<canonical-cwd-hash>/
       sessions/ receipts/ checkpoints/ locks/ sqlite/ logs/
```

`HARNESS_STATE_DIR`는 state root를 명시하는 runtime input이다. test는 temporary state root를 사용한다. source repository 아래의 live `runs/`는 source, fixture, template과 섞지 않는다.

## Build/test 재구성 계약

Harness-starter는 문서·복사 스크립트 묶음이 아니라 독립적으로 build·test·install 가능한 runtime source repository가 된다. 이 전환은 Hermes runtime venv, live gateway, Hermes core checkout을 build input이나 test fixture로 사용하지 않는다.

### Build source와 artifact

1. repository root에 `pyproject.toml`을 둔다. runtime dependency와 test dependency를 분리해 선언한다.
2. lockfile은 해당 manifest에서만 생성한다. 시스템 Python이나 Hermes service venv의 설치 상태는 build 재현성의 근거가 아니다.
3. runtime source는 import 가능한 단일 package/API와 명시적 CLI entrypoint를 제공한다. `h-setup.sh`는 source tree 복사기가 아니라 versioned artifact를 bootstrap하는 thin installer가 된다.
4. build artifact에는 runtime source, versioned contract/schema, thin adapter entrypoint만 포함한다. Harness Brain의 canonical prose, live receipt, runtime database, logs는 포함하지 않는다.

### Test topology

| 층 | 입력 | 격리 조건 | 닫힘 증거 |
|---|---|---|---|
| contract/unit | versioned schema와 fixture | temporary directory, network 없음 | validation result + fixture readback |
| lifecycle/integration | clean temporary git worktree + temporary `HARNESS_STATE_DIR` | live `runs/`, dirty worktree, gateway 미사용 | producer receipt → consumer readback |
| adapter | built artifact + fake/isolated host fixture | Hermes core checkout과 live `HERMES_HOME` 미사용 | adapter request/response contract replay |
| canary | 단일 신규 case + 별도 state root | 기존 state는 read-only, write scope 제한 | runtime receipt + state readback + rollback path |

negative-path test는 의도한 validation error를 assertion으로 소비해야 하며, stderr 출력만으로 실패로 판정하지 않는다. test는 현재 worktree의 `git status` 전체 hash에 의존하지 않는다. 변경 범위 검증이 필요하면 test fixture의 명시적 source manifest와 allowlist를 사용한다.

### Build/test gate

각 source-only Git closure 전에 다음 증거가 필요하다.

1. lockfile 기반의 fresh environment에서 build artifact를 생성한다.
2. artifact만 설치한 환경에서 contract/unit 및 lifecycle/integration test를 실행한다.
3. temporary state root의 receipt를 consumer가 readback한다.
4. live gateway의 PID, Hermes core worktree, 기존 external state가 이 실행으로 변하지 않았음을 확인한다.

이 gate가 실패하면 artifact와 temporary fixture만 폐기한다. Hermes repo를 수정·commit·push하거나 live gateway를 재시작해서 test를 통과시키지 않는다.

## Hermes plugin admission 계약

Harness adapter가 Hermes에 연결되는 유일한 code path는 공식 plugin/config/hook surface다. plugin은 Hermes core tree에 복사하거나 vendor하지 않는다. third-party integration은 standalone plugin으로 배포한다는 Hermes 공식 plugin 정책을 따른다.

### 설치·발견·활성화 조건

1. plugin은 Harness-starter에서 build한 standalone artifact 또는 별도 plugin distribution으로 제공한다. 설치 위치는 `$HERMES_HOME/plugins/<plugin-name>/` 또는 Hermes가 지원하는 pip entry point다.
2. plugin directory에는 `plugin.yaml`과 `__init__.py`가 있어야 한다. manifest에는 최소 `name`, `version`, `description`을 선언하고, 등록하는 표면은 `provides_tools`, `provides_hooks` 등으로 명시한다.
3. `__init__.py`는 `register(ctx)` entrypoint를 제공한다. 등록하는 hook/middleware/tool/command는 Hermes가 공개한 유효 이름과 signature만 사용한다.
4. plugin은 opt-in이다. target profile의 `$HERMES_HOME/config.yaml`에서 `plugins.enabled` allowlist에 명시된 경우에만 활성화한다. `plugins.disabled` 또는 profile-level disable과 충돌하면 활성화하지 않는다.
5. 필요한 secret은 manifest나 source에 기록하지 않는다. `requires_env`는 presence gate로만 사용하고, 실제 값은 target profile의 secret source/environment가 제공한다.

### 기능 적합성 조건

- observer hook은 mandatory routing/session/workdir 결정을 소유하지 않는다. hook 예외가 발생하면 Hermes는 plugin만 비활성화하고 계속 실행할 수 있으므로, observer 결과를 CPS authorization이나 project binding의 유일한 truth로 삼으면 안 된다.
- pre-session resolver처럼 동기식 결정과 return contract가 필요한 기능은, 해당 공식 extension point가 존재하고 source-backed로 확인된 경우에만 plugin에 넣는다. 현재 generic hook 목록에 없는 기능은 plugin으로 가장하지 않는다.
- context engine 또는 memory provider는 single-select/provider replacement 특성이 있을 수 있다. 기존 compression·Honcho 등 active provider와 capability/ownership conflict scan 없이 설치하지 않는다.
- plugin은 Hermes session DB, gateway state, prompt source, core Python module을 직접 수정·import-time patch하지 않는다. Harness의 session/project truth는 외부 runtime contract와 `HARNESS_STATE_DIR`에 둔다.

### Admission packet과 검증

plugin을 target profile에 설치하기 전에 다음 packet을 만든다.

| 필드 | 요구 증거 |
|---|---|
| artifact identity | version, source digest, dependency lock digest |
| declared surface | manifest의 tools/hooks/middleware/commands와 실제 `register(ctx)` 대조 |
| compatibility | 지원 Hermes version/API와 plugin test 결과 |
| capability scope | tool dispatch, filesystem/network, state root, secret presence requirement |
| conflict scan | enabled/disabled plugin, single-select provider, 동일 tool/hook name, profile ownership |
| rollback | plugin directory 제거와 `plugins.enabled` entry 제거 후 core/state 무변경 readback |

검증은 temporary `HERMES_HOME`에서 artifact를 설치하고 `plugins.enabled`를 명시한 뒤 discovery·registration·대표 request-path를 replay하는 방식으로 수행한다. live `$HERMES_HOME`, live gateway, Hermes repo는 test fixture가 아니다.

실제 profile activation은 위 packet의 readback 뒤에만 수행한다. plugin load가 gateway process restart를 요구하면 active case/lock이 없는 단일 controlled restart로만 적용하며, restart를 plugin test나 source build의 정상 경로로 사용하지 않는다.

## 초기 cwd / session binding의 Harness 이관

### 현재 상태와 금지선

현재 자동 cwd 동작은 Hermes core의 gateway/session 실험 변경으로 구현되어 있다. 그 구현은 다음 runtime 의미를 이미 입증했다.

```text
Discord source identity
  → project_slug + canonical_cwd 결정
  → first ingress의 session anchor 영속
  → 이후 turn/restart 뒤 anchor 재사용
```

이 기능은 Harness 요구에 맞지만 Hermes core의 production ownership으로 승인된 것이 아니다. 해당 core diff는 commit하거나 push하지 않으며, 추가 보완 patch도 만들지 않는다. 이 문서의 migration 완료 전에는 current behavior를 사실 증거로만 보존한다.

### 목표 ownership과 contract

Harness runtime이 canonical binding registry를 소유한다. binding record의 최소 입력·출력은 다음과 같다.

```text
input:  platform, guild_id, parent_channel_id, thread_id, profile
output: project_slug, canonical_cwd, write_scope, binding_revision, source_ref
receipt: resolver_revision, binding_digest, session_key, consumer_readback
```

`canonical_cwd`는 Harness registry가 결정하는 project binding의 결과다. Hermes plugin은 공식 pre-session resolver가 제공하는 source identity를 Harness runtime에 전달하고, 검증된 결과만 session creation/agent execution에 적용한다. Hermes core DB는 host가 보관하는 session receipt일 수 있으나 canonical binding authority가 되지 않는다. Harness는 Hermes session SQLite를 직접 읽거나 쓰는 방식으로 이관하지 않는다.

### C → derived C → AC → original C

| 단계 | 계약 | 증거 |
|---|---|---|
| original C | first ingress가 올바른 canonical cwd에서 실행되고, follow-up/restart 뒤에도 같은 binding을 재사용한다 | source identity, binding receipt, agent cwd readback, follow-up session readback |
| derived C | temporary `HERMES_HOME`의 Harness plugin이 동일 source identity에서 외부 binding registry를 해석한다 | resolver request/response, binding digest, plugin registration receipt |
| derived AC | manifest/admission/compatibility/conflict scan과 isolated request-path replay가 통과한다 | artifact digest, enabled profile config, no-core-diff readback, isolated state receipt |
| return edge | 단일 controlled activation 뒤 live gateway가 original C를 만족하고, 기존 core experiment 없이 동일 binding을 재현한다 | gateway PID/service receipt, first-ingress cwd readback, restart 후 follow-up readback |

이 graph의 original C를 derived C로 바꾸어 완료 선언하지 않는다. isolated plugin replay는 activation 전제일 뿐이고, live first-ingress와 restart-reuse readback이 없으면 이관은 미완료다.

### 이관 순서와 rollback

1. current core behavior에서 source identity와 project/cwd 결과를 **read-only evidence**로 캡처한다. 이를 새 runtime authority나 dual-write source로 사용하지 않는다.
2. Harness registry에 canonical binding contract와 source-ref를 생성한다. fixture와 temporary state root에서 unknown/ambiguous binding은 fail-closed한다.
3. official pre-session resolver가 확인된 경우에만 Harness bridge artifact를 build하고 temporary `HERMES_HOME`에서 first-ingress/follow-up/restart replay를 수행한다.
4. admission packet과 derived AC가 닫힌 뒤, active case/lock이 없는 단일 controlled activation으로 one-case canary를 수행한다.
5. canary의 original C readback이 닫힌 경우에만 binding authority를 Harness registry로 전환한다. 이전 core experiment는 new core patch나 commit 없이 제거/비활성화할 수 있는 별도 cleanup work로 남긴다.

rollback은 Harness plugin activation과 Harness external state root만 되돌린다. core DB를 수동 복원하거나 direct session schema mutation으로 rollback하지 않는다. official resolver가 없거나 return edge가 실패하면, migration은 blocker로 기록하고 core 변경을 확대하지 않는다.

### Compression과의 분리

cwd/session binding 이관은 built-in compression persistence를 대체하지 않는다. Harness는 binding receipt와 durable semantic checkpoint를 제공하고, compression은 Hermes의 공식 built-in 경로가 담당한다. persistence gap이 source-backed로 확인되기 전에는 context engine/memory provider를 임의로 활성화하지 않는다.

## 순차 이관

1. **Freeze**: Hermes core에는 commit, push, 추가 수정을 하지 않는다. live gateway나 기존 state를 이동하지 않는다.
2. **Build/test ownership**: Harness-starter에 독립 dependency manifest와 lockfile, 재현 가능한 test entrypoint를 둔다. Hermes service venv와 시스템 Python을 Harness test environment로 사용하지 않는다.
3. **State split**: template/fixture를 source로 분리하고, 새 state root를 opt-in으로 추가한다. 기존 state는 read-only compatibility 대상으로만 둔다.
4. **Runtime API**: session registry, lifecycle, dispatcher를 Harness runtime API/CLI로 통합한다. adapter는 runtime을 호출할 뿐 policy/state truth를 복제하지 않는다.
5. **Canary**: temporary state root와 단일 신규 case에서 receipt/readback을 검증한다. 기존 state와 gateway는 rollback 대상이 되지 않아야 한다.
6. **Resolver decision**: 공식 pre-session resolver가 존재하거나 upstream이 수용한 경우에만 external Harness bridge로 cwd/session binding을 옮긴다. 그렇지 않으면 자동 cwd 전환은 보류한다.

## Git closure 규칙

Harness-starter의 source-only change만 독립 commit한다. generated state, lock, runtime database, logs, receipt, test output은 commit하지 않는다. source-only packet이 검증된 뒤 Git closure는 지정된 executor로 수행한다.

Hermes repo는 이 절차의 commit/push 대상이 아니다. Hermes core diff를 Harness-starter commit에 vendor하거나 숨겨서 closure하는 것도 금지한다.

## Acceptance Criteria

- [ ] Harness-starter가 자체 dependency manifest와 lockfile로 build/test를 재현한다.
- [ ] lifecycle test가 dirty live worktree가 아닌 temporary clean fixture/worktree에서 실행된다.
- [ ] source, template/fixture, external runtime state의 경로와 Git 추적 규칙이 분리된다.
- [ ] Harness runtime은 Hermes core import나 직접 SQLite/session schema mutation 없이 contract를 처리한다.
- [ ] Hermes adapter는 official plugin/hook/config surface만 사용하며, Hermes repo에는 commit/push가 발생하지 않는다.
- [ ] Harness registry가 source identity → project slug/canonical cwd/write scope binding의 canonical authority가 된다.
- [ ] temporary `HERMES_HOME`에서 Harness resolver plugin의 first-ingress, follow-up, restart-reuse replay가 receipt/readback으로 닫힌다.
- [ ] live canary에서 original C인 first-ingress cwd와 restart 뒤 binding reuse가 확인되기 전에는 core experiment 제거 또는 migration 완료를 선언하지 않는다.
- [ ] pre-session resolver의 공식 지원 여부와 적용 contract가 source-backed로 기록된다.

## 검증 규칙

각 단계는 producer → receipt → consumer readback으로 닫는다. build/test 분리의 PASS 개수만으로 완료를 선언하지 않는다. 기존 live gateway의 안정성, 기존 receipt의 readback, 새 runtime의 isolated replay가 동시에 충족되어야 다음 단계로 진행한다.
