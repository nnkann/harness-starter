---
title: Discord project gateway isolation SSOT
domain: harness
c: "Discord 채널로 프로젝트를 나눴지만 Hermes 실행 컨텍스트, cwd, memory, 권한이 분리되지 않아 하네스·Hermes upstream·downstream 작업이 혼용된다."
problem: [P3, P5, P7, P8, P11]
s: [S3, S5, S7, S8, S11]
tags: [hermes, discord, gateway, isolation, permissions]
relates-to:
  - path: harness/hn_harness_core_overlay_binding.md
    rel: references
  - path: archived/hn_hermes_integration.md
    rel: references
  - path: decisions/hn_runtime_adapter_unification.md
    rel: references
  - path: decisions/hn_hermes_managed_downstream_memory.md
    rel: references
  - path: decisions/hn_memory.md
    rel: references
  - path: decisions/hn_reminder_memory_contract.md
    rel: references
status: completed
created: 2026-05-29
updated: 2026-06-01
---

# Discord Project Gateway Isolation SSOT

**Acceptance Criteria**:

- [x] Goal: Discord channel/thread, Hermes gateway dispatcher, project registry, project-bound worker fleet, cwd, memory namespace, permission model을 하나의 SSOT로 묶는다.
  검증:
    review: self
    tests: `rg -n "Project Binding Contract|Memory Boundary|Permission Boundary|Implementation Gate" docs/harness/hn_discord_project_gateway_isolation_ssot.md`
    실측: 이 문서 하나만 읽어도 구현 전 경계 조건과 금지 조건을 재구성할 수 있다.
- [x] S7/S8: 공유 memory와 project-local working memory의 분리 규칙을 명시한다.
- [x] S3/S7: `channel_id -> project_id -> worker_id -> fixed repo_root -> memory_namespace -> permission_profile` dispatch 계약을 명시한다.
- [x] S3/S11: Hermes runtime repo, harness-starter, downstream repo의 권한 경계를 분리한다.
- [x] S5: 구현 전 Agy advisory review 질문과 반박 조건을 문서화한다.
- [x] Agy review: 본 SSOT가 구현 전제, 누락된 우회 경로, 과잉 설계 여부를 독립 검토한다.
- [x] Implementation gate: Agy 검토 결과를 반영해 MVP 범위와 필수 차단 테스트를 확정한다.

## Decision

Discord 채널 분리는 UI 구분일 뿐이다. Hermes/Harness 운영에서는 채널 또는
thread가 들어오는 순간 gateway dispatcher가 project-bound worker를 선택해야
한다. 하나의 worker가 메시지마다 프로젝트를 바꾸는 방식은 기본 운영 모델이
아니다.

```text
discord_server_id
discord_channel_id
discord_thread_id
discord_message_id
  -> project_id
  -> worker_id
  -> fixed repo_root
  -> memory_namespace
  -> permission_profile
  -> execution_profile
```

모델의 기억, 현재 shell cwd, 최근 대화 주제, 파일명 키워드로 프로젝트를
추정하지 않는다. dispatcher route가 결정되지 않으면 write, commit, push,
apply_patch, cron executor, memory write를 시작하지 않는다.

Harness는 프로젝트별 workflow contract와 SSOT를 소유한다. Hermes는 Discord,
Slack, CLI, cron, session search, memory, worker dispatch를 운영하는
control-plane이다. Hermes가 전체 capability를 알고 있어도 모든 gateway와
모든 프로젝트에 같은 권한을 부여하지 않는다.

핵심 결정:

- 프로젝트 전환은 worker 내부 동작이 아니라 dispatcher의 worker 선택으로
  처리한다.
- project worker는 고정 repo root, 고정 memory namespace, 고정 permission
  profile을 가진다.
- Hermes admin/control-plane은 project registry와 dispatcher를 관리하지만,
  일반 project 작업을 직접 수행하지 않는다.
- cross-project 작업은 admin이 계획하고 각 project worker에게 위임한다.
- source repo는 `/Users/kann/projects/*` 아래에 모으고, `~/.hermes/*`는 runtime
  state/config/auth/cache/memory 전용으로 둔다.

## Failure Being Fixed

현재 실패는 단일 버그가 아니라 경계 부재의 합성 장애다.

- Discord 채널은 프로젝트별로 나뉘었지만 Hermes gateway dispatcher와
  project-bound worker가 동기화되지 않았다.
- 모든 세션의 cwd가 `/Users/kann/.hermes/hermes-agent`로 잡혀 Harness나
  downstream 작업이 Hermes upstream repo 작업처럼 보였다.
- harness-starter 작업을 Hermes upstream에 push하려는 시도가 생겼다.
- StageLink 관련 수정 지시가 harness-starter WIP 수정으로 흘렀다.
- project memory, WIP, pending task, branch 상태가 cross-project memory처럼
  섞였다.
- Hermes runtime repo 권한으로 harness-starter를 수정하려고 하거나, 반대로
  권한 밖으로 판단하는 반복 실패가 발생했다.
- Discord 원문을 session_search/gateway 없이 링크만으로 회수하려 해서 과거
  논의가 실행 컨텍스트로 연결되지 않았다.

## Project Worker Contract

### Required Registry

Hermes/Harness는 최소한 다음 project registry와 worker registry를 가져야 한다.
Project registry는 "무엇이 프로젝트인가"를 정의하고, worker registry는 "어떤
고정 실행 환경이 이 프로젝트를 담당하는가"를 정의한다.

```yaml
projects:
  harness-starter:
    root: /Users/kann/projects/harness-starter
    type: harness-starter
    default_branch: main
    remotes:
      origin: https://github.com/nnkann/harness-starter.git
    protected: false
    allow_push: true
    memory_namespace: project:harness-starter
    permission_profile: harness-admin
    worker_id: worker:harness-starter

  hermes-agent:
    root: /Users/kann/projects/hermes-agent
    type: hermes-runtime
    default_branch: main
    remotes:
      origin: https://github.com/NousResearch/hermes-agent.git
    protected: true
    allow_push: false
    memory_namespace: project:hermes-agent
    permission_profile: protected-runtime
    worker_id: worker:hermes-admin

  stagelink:
    root: /Users/kann/projects/stagelink
    type: harness-downstream
    default_branch: main
    protected: false
    allow_push: project-policy
    memory_namespace: project:stagelink
    permission_profile: downstream
    worker_id: worker:stagelink

workers:
  worker:harness-starter:
    project_id: harness-starter
    cwd: /Users/kann/projects/harness-starter
    memory_namespace: project:harness-starter
    permission_profile: harness-admin
    allowed_write_roots:
      - /Users/kann/projects/harness-starter

  worker:stagelink:
    project_id: stagelink
    cwd: /Users/kann/projects/stagelink
    memory_namespace: project:stagelink
    permission_profile: downstream
    allowed_write_roots:
      - /Users/kann/projects/stagelink

  worker:hermes-admin:
    project_id: hermes-agent
    cwd: /Users/kann/projects/hermes-agent
    memory_namespace: project:hermes-agent
    permission_profile: protected-runtime
    protected: true
```

### Required Dispatcher Map

Discord routing은 project/worker registry와 별도 map으로 둔다.
server/channel/thread id는 gateway-local 식별자이므로 project config에 섞지
않는다. 이 map은 Discord 채널 구조와 Hermes worker fleet의 동기화 계약이다.

```yaml
gateway_dispatch:
  discord:
    "1229431008424624139":
      channel_name_projects:
        haness-starter: harness-starter
        harness-starter: harness-starter
        stagelink: stagelink
        hermes-agent: hermes-agent
      channels:
        "1229431216344793189":
          project_id: harness-starter
          worker_id: worker:harness-starter
          allowed_principals: [owner, harness-maintainers]
        "1508435114487709857":
          project_id: stagelink
          worker_id: worker:stagelink
          allowed_principals: [owner, stagelink-maintainers]
```

Discord private thread는 새 thread id로 유입될 수 있으므로 고정 channel id
매핑만 신뢰하지 않는다. gateway는 channel directory의 부모 채널명
(`#haness-starter`, `#stagelink`, `#hermes-agent`)도 route key로 사용한다.
`1509784117519323136`은 별도 "gateway-isolation channel"이 아니라
`#hermes-agent` 아래 thread/topic이다.

프로젝트 등록은 `~/.hermes/config.yaml`을 직접 편집하는 대신 Hermes CLI의
검증 명령으로 수행한다. 새 downstream 프로젝트의 표준 등록 절차:

```bash
hermes project register <project-id> \
  --root /Users/kann/projects/<repo> \
  --remote <origin-url> \
  --discord-guild 1229431008424624139 \
  --discord-channel <channel-id> \
  --channel-name <discord-parent-channel-name>

hermes gateway restart
```

`hermes project register ... --dry-run`은 config를 쓰지 않고 registry,
worker, dispatcher route를 검증한다. 반복 실행 시 기존 `allowed_principals`,
permission profile, protected flag 같은 운영 정책은 명시적으로 바꾸지 않는 한
보존되어야 한다.

Dispatch 결과는 session start와 tool execution 전 모두에서 확인한다. 다만 일반
운영에서는 worker가 project를 바꾸지 않는다. dispatcher가 처음부터 맞는 worker로
메시지를 보낸다.

### User/Principal Rule

유저별 session 분리는 project isolation을 대체하지 않는다. user/principal은
"어떤 worker에 접근할 수 있는가"와 "cross-project admin 권한이 있는가"를
결정한다.

```yaml
principals:
  discord:
    users:
      "<owner_user_id>":
        roles: [owner, cross-project-admin]
        allowed_workers:
          - worker:harness-starter
          - worker:stagelink
          - worker:hermes-admin
      "<project_user_id>":
        roles: [contributor]
        allowed_workers:
          - worker:stagelink
```

Channel route와 principal rule이 모두 통과해야 worker dispatch가 성립한다.
유저별 session 관리는 대화 히스토리 분리를 위해 사용하고, 프로젝트 실행 경계는
project-bound worker로 보장한다.

### No Project Switching By Default

`active_project`는 worker 내부에서 검증용으로 읽는 파생값이다. 사용자가 같은
worker 안에서 `/project use <id>`로 프로젝트를 바꿔가며 작업하는 방식을 기본
운영 모델로 삼지 않는다.

허용되는 전환은 admin/control-plane 전용이며, 실제 파일 수정은 대상 project
worker에게 위임한다.

```text
admin worker receives cross-project request
  -> validates owner/principal approval
  -> decomposes task per project
  -> dispatches project-local work to each project worker
  -> reconciles results without borrowing another worker's cwd
```

## Cwd And Filesystem Boundary

모든 repo 명령은 worker의 고정 cwd에서 실행한다. Hermes 전역
`terminal.cwd`나 gateway daemon launch directory를 신뢰하지 않는다.

`cwd == worker.cwd`만으로는 충분하지 않다. 실행 가드는 명령의 실제 대상
경로를 canonical path로 해석한 뒤 `worker.allowed_write_roots` 안에 있는지
검증해야 한다.

Hard fail 조건:

- `cwd != worker.cwd`인데 write, test, git, apply_patch가 실행된다.
- `git -C`, `--git-dir`, `--work-tree`처럼 git 실행 컨텍스트를 다른 repo로
  바꾸는 플래그가 project-bound worker에서 사용된다.
- `apply_patch`, file write, plugin/MCP filesystem call이 절대 경로 또는
  symlink resolve 결과로 다른 worker root를 가리킨다.
- worker가 `harness-starter`인데 `/Users/kann/.hermes/hermes-agent`
  아래에 patch를 적용한다.
- worker가 downstream인데 harness-starter WIP를 수정한다.
- Hermes runtime repo가 protected인데 commit/push/reset/write를 시도한다.
- `repo_root`, `remote URL`, `branch`, `allow_push`가 registry와 다르다.

예외는 owner가 명시한 cross-project admin task뿐이다. 예외도 gateway admin
profile과 runtime approval을 통과해야 하며, 수정은 각 project worker가 수행한다.

## Repository Layout Boundary

Project-bound worker fleet을 쓰려면 파일시스템 배치도 같은 원칙을 따라야 한다.
source repo와 runtime state가 같은 `~/.hermes` 아래에 섞이면 cwd 혼동과 권한
오판이 다시 발생한다.

Canonical local layout example:

```text
/Users/kann/projects/
  harness-starter/       # Harness core/workflow SSOT repo
  stagelink/             # downstream project repo
  hermes-agent/          # Hermes upstream/source repo, protected project

/Users/kann/.hermes/
  config.yaml            # local runtime config
  profiles/              # local worker profiles
  memories/              # Hermes runtime memory store
  sessions/              # Hermes runtime sessions
  cron/                  # cron state
  gateway/               # gateway runtime state
  auth.json, .env        # local secrets/auth
```

Rules:

- `harness-starter`에는 layout schema, validation rule, template만 커밋한다.
  실제 절대 경로, Discord id, principal id는 local Hermes binding에 둔다.
- Do not move `~/.hermes` wholesale into `/Users/kann/projects`.
- Do move/clone source repos into `/Users/kann/projects`.
- `~/.hermes/hermes-agent` is legacy/transition path only.
- During migration, keep a temporary compatibility symlink only if existing
  Hermes code or profiles still reference the old path.
- After migration, project registry and worker registry must use
  `/Users/kann/projects/hermes-agent`.
- Runtime state paths under `~/.hermes` are never project worker cwd.

Migration sequence:

1. Stop Hermes gateway/worker processes or confirm no worker is using the old
   source path.
2. Preserve uncommitted changes in the Hermes source repo.
3. Move or clone source repo to `/Users/kann/projects/hermes-agent`.
4. Add a temporary symlink from `~/.hermes/hermes-agent` to the new path if
   needed for compatibility.
5. Update project/worker registry paths to the new canonical root.
6. Run route/worker invariant tests and Hermes smoke tests.
7. Remove the symlink only after references to the legacy path are gone.

## Permission Boundary

권한은 다음 식으로 계산한다.

```text
effective_permission =
  core capability exists
  AND gateway policy allows it
  AND principal/session policy allows it
  AND dispatcher route allows this worker
  AND project policy allows it
  AND worker profile allows it
  AND approval passed if required
```

`approval_required`는 deny가 아니다. 실행 전 사람이 승인해야 하는 별도 상태다.

Tool schema filtering과 execution revalidation을 둘 다 적용한다.

- schema filtering: agent planning 단계에서 금지 tool을 보이지 않게 한다.
- execution revalidation: direct tool call, plugin path, replay path, raw exec
  우회를 막는다.

Raw `git commit`, `git push`, `git reset`, write/delete filesystem operation,
`apply_patch`, cron executor는 project guard 없이는 실행하지 않는다.

## Memory Boundary

Memory는 공유하되 같은 층으로 공유하지 않는다.

| Namespace | Owner | 넣을 수 있는 것 | 넣으면 안 되는 것 |
|---|---|---|---|
| `global` | Harness/Hermes shared policy | 안정적인 운영 원칙, 용어, project 관계 | 현재 WIP, branch 상태, pending patch |
| `project:<id>` | 해당 project | project policy, current WIP summary, repo-specific decisions | 다른 project task, 다른 repo branch state |
| `channel:<id>` | gateway route | Discord channel summary, active project binding evidence | durable SSOT가 필요한 결정 원본 |
| `session:<id>` | project-bound worker | pending patch, current plan, transient approval | 장기 정책 또는 다른 project task |
| repo docs | 각 repo | CPS, WIP, decisions, project SSOT | Hermes auth/profile/local secret |

Hermes built-in memory는 cross-project stable facts만 담는다. 과거 Discord/CLI
논의는 `session_search`로 검색하고, 현재 repo 문서·코드·명령 결과로 재확인한
뒤 사용한다. repo-local reminder는 사실 증거가 아니라 확인 후보로만 취급한다.

`global` namespace는 런타임에서 read-only stable facts로 제한한다. `channel:<id>`
namespace는 route evidence와 대화 요약만 담고, project WIP·branch·pending patch를
`project:<id>`로 직접 쓰지 않는다.

## Harness Starter vs Hermes Runtime

`harness-starter`는 상위 workflow contract와 policy/config/test template을
소유한다. 하지만 local token, profile id, cron id, provider/model binding은
Hermes local execution binding에 남는다.

Hermes upstream/runtime repo는 protected runtime이다. `harness-starter` 정책을
구현하기 위해 Hermes core에 hook이 필요할 수 있지만, 장기 fork를 기본 전략으로
삼지 않는다. 기본 전략은 다음 순서다.

1. harness-starter에 policy, config template, compatibility test를 둔다.
2. Hermes에는 permission context 전달, schema filtering hook, execution
   authorization hook, audit event hook 같은 최소 upstreamable surface만 둔다.
3. upstream merge 전 patch lifecycle과 compatibility CI로 유지한다.
4. downstream에는 최소 harness surface와 project overlay만 둔다.

## Dispatcher And Worker Fleet Policy

기본 stack은 `hermes-codex-agy`다.

- Hermes: gateway intake, routing, session binding, memory/session_search,
  worker dispatch, reconciliation.
- Codex: bounded code/document patch executor.
- Agy: advisory/adversarial review, design risk, missing boundary, overfit check.

Worker는 project binding을 상속하는 것이 아니라 project binding으로 생성된다.
Agy나 Codex를 호출할 때도 prompt와 실행 profile에 `worker_id`, `project_id`,
`worker.cwd`, 금지 repo, memory namespace, expected output을 명시한다.
Agy는 project repo가 아니라 local runtime state인
`~/.gemini/antigravity-cli`에도 쓴다. 따라서 project-bound Codex worker가
Agy를 실행할 때 sandbox writable roots는 최소한 다음을 포함해야 한다.

- worker repo root
- `/Users/kann/projects` clone/register workspace
- `~/.gemini/antigravity-cli` Agy runtime state

이 root 전달은 worker `allowed_write_roots`와 별도의 runtime state root로
취급한다. Agy state를 project repo에 복사하거나 downstream SSOT로 만들지 않는다.

권장 운영 구조:

```text
Hermes gateway dispatcher
  -> worker:harness-starter   (fixed cwd: /Users/kann/projects/harness-starter)
  -> worker:stagelink         (fixed cwd: /Users/kann/projects/stagelink)
  -> worker:hermes-admin      (protected runtime/admin only)
```

Dispatcher sync invariant:

- Discord channel/thread map과 worker registry는 같은 config snapshot에서
  읽는다.
- channel이 project worker를 가리키면 해당 worker의 `project_id`, `cwd`,
  `memory_namespace`가 project registry와 일치해야 한다.
- 일치하지 않으면 gateway startup 또는 route reload가 실패해야 한다.
- route 변경은 audit log에 남기고, 기존 session은 새 worker로 silent migration
  하지 않는다. owner 확인 후 새 session으로 시작한다.

## Implementation Gate

구현은 아래 순서로만 시작한다.

1. 이 SSOT에 Agy review를 붙인다.
2. Agy가 지적한 blocker를 owner decision 또는 문서 수정으로 처리한다.
3. 구현 범위를 1차 MVP로 제한한다.
4. regression test를 먼저 정의한다.
5. Hermes/Harness 중 어느 repo를 수정할지 active project를 확정한다.

### MVP Scope

MVP는 project-bound worker fleet과 Discord dispatcher sync를 먼저 고정한다.
다음 경로를 막는 데 집중한다.

- MVP에서 cross-project admin execution은 거부한다. admin worker가 여러 project
  worker에 쓰기 작업을 분해·위임·reconcile하는 흐름은 격리 경계가 안정된 뒤
  별도 phase로 둔다.
- worker 내부 dynamic project switching은 MVP에서 제공하지 않는다.
- principal model은 owner approval 중심으로 시작한다. 복잡한 RBAC는 후속 phase다.
- Discord channel/thread에서 worker_id가 결정되지 않으면 write 금지.
- dispatcher route의 project_id와 worker.project_id가 다르면 route load 실패.
- worker cwd와 command cwd가 다르면 write/git/apply_patch 금지.
- `git -C`, `--git-dir`, `--work-tree`로 다른 repo를 가리키는 실행은 금지.
- apply_patch/write 대상의 resolve path가 worker allowed root 밖이면 금지.
- cron job은 project_id와 worker_id를 명시하지 않으면 fail-closed.
- protected Hermes runtime repo에서 raw git/write 금지.
- project별 worker memory namespace를 분리하고 session summary에 표시.
- gateway route가 없는 channel/thread/DM은 read-only 또는 owner selection 요구.

### Regression Tests

필수 회귀 테스트:

- harness-starter channel에서 Hermes repo commit/push 시도는 실패한다.
- Hermes upstream channel이 아닌 곳에서 `/Users/kann/.hermes/hermes-agent`
  patch는 실패한다.
- Hermes source repo canonical path is `/Users/kann/projects/hermes-agent`; using
  `~/.hermes/hermes-agent` as worker cwd fails after migration unless in explicit
  compatibility mode.
- StageLink channel에서 harness-starter WIP 수정 시도는 실패한다.
- Discord channel route가 `worker:stagelink`를 가리키는데 worker registry의
  `project_id`가 다르면 gateway startup 또는 route reload가 실패한다.
- contributor principal이 허용되지 않은 worker로 dispatch되면 실패한다.
- route 없는 Discord channel에서 write/apply_patch는 owner selection 전 실패한다.
- schema filtering으로 forbidden tool이 planning surface에 노출되지 않는다.
- execution revalidation으로 direct raw git 우회가 실패한다.
- `global` memory write가 project WIP/branch state를 포함하면 실패한다.
- project-bound worker가 `git -C /other/repo`, `--git-dir`, `--work-tree`로
  context를 바꾸면 실패한다.
- apply_patch/write 대상이 절대 경로 또는 symlink resolve 후 allowed root 밖이면
  실패한다.
- project_id/worker_id 없는 cron executor는 default admin으로 fallback하지 않고
  실패한다.
- harness-starter template/config sample은 local absolute path나 real Discord id를
  canonical committed binding으로 포함하지 않는다.

## Agy Review Result

2026-06-01 Agy review 결과는 `go-with-changes`다. 구현 방향 자체는 유지하되,
아래 보정이 SSOT에 반영되어야 implementation gate를 통과한다.

- 도구 레벨 우회 차단: `git -C`, `--git-dir`, `--work-tree`, 절대 경로 patch,
  symlink resolve 우회를 execution revalidation에서 막는다.
- cron strict binding: cron executor는 `project_id`와 `worker_id` 없이는
  fail-closed 한다.
- local binding split: harness-starter는 schema/template/validation만 소유하고,
  실제 `/Users/kann/...` 경로와 Discord/principal id는 local Hermes config에 둔다.
- memory 축소: `global`은 read-only stable facts, `channel:<id>`는 route evidence
  중심으로 제한한다.
- MVP 축소: cross-project execution과 dynamic project switching은 MVP에서 제외한다.

## Agy Review Prompt

구현 전 Agy에는 아래 질문으로 검증을 요청한다.

```text
You are reviewing docs/WIP/harness--hn_discord_project_gateway_isolation_ssot.md
before implementation.

Context:
- The failure is cross-project contamination across Discord channels, Hermes cwd,
  project memory, permissions, and repo writes.
- Harness must remain the project workflow SSOT.
- Hermes is the gateway/control-plane.
- The first implementation must use a project-bound worker fleet. The gateway
  dispatcher selects workers; workers do not switch projects by default.
- The first implementation must prevent wrong-repo writes and memory/task mixing.

Review focus:
1. Identify missing bypass paths in dispatcher sync, project-bound worker
   creation, cwd, filesystem write, git, apply_patch, cron executor, plugin/MCP
   tool calls, and memory writes.
2. Identify places where the SSOT overreaches into Hermes local runtime details
   that should remain local binding.
3. Identify whether shared memory is still too broad and likely to recreate
   contamination.
4. Identify what must be MVP versus later phase, assuming dynamic project
   switching inside a worker is not the target architecture.
5. Produce a go/no-go recommendation for implementation.

Output:
- Blockers
- Non-blocking risks
- MVP boundary corrections
- Tests that must exist before implementation
- Final recommendation: go / go-with-changes / no-go
```

## Open Questions

- Gateway route config의 canonical owner는 `~/.hermes/config.yaml`인지,
  harness-starter template인지, 둘의 조합인지 확정해야 한다.
- project registry가 Hermes local config에만 있으면 downstream upgrade로
  검증하기 어렵다. 반대로 repo에 local absolute path를 커밋하면 portability가
  깨진다. template + local binding split이 필요하다.
- Discord message history retrieval은 Hermes gateway/session_search가 맡아야
  한다. LLM 세션이 Discord URL을 직접 열어 과거 논의를 회수하는 구조는
  구현 목표가 아니다.
- cross-project admin task의 UX를 admin worker 명령으로 둘지, owner approval
  flow와 project-worker delegation으로만 둘지 결정해야 한다.
- Hermes source repo migration에서 legacy `~/.hermes/hermes-agent` symlink를
  언제 제거할지 결정해야 한다.

## Source Notes

이 SSOT는 다음 기존 결정을 통합한다.

- `docs/harness/hn_harness_core_overlay_binding.md`: Harness core / downstream
  overlay / local Hermes binding 3계층.
- `docs/archived/hn_hermes_integration.md`: Hermes는 harness-managed repo를
  감지하고 workflow를 실행하는 orchestration adapter.
- `docs/decisions/hn_runtime_adapter_unification.md`: 기본 runtime stack은
  Hermes + Codex + Agy.
- `docs/decisions/hn_hermes_managed_downstream_memory.md`: Hermes-managed
  downstream에서 memory/reminder는 SSOT가 아니라 signal/manifest/session_search
  경계로 나뉜다.
- `~/.codex/memories/harness_first_workflow.md`: 특정 Discord thread/channel에서
  cwd와 무관하게 harness-starter를 active project로 취급해야 한다는 운영 기억.

## Progress Log

- 2026-05-29: Discord project contamination, Hermes cwd 고정, project memory
  혼용, gateway permission 논의를 하나의 구현 전 SSOT로 통합.
- 2026-05-30: 단일 worker의 active project switching 모델을 폐기하고,
  Discord channel/thread와 project-bound Hermes worker fleet을 동기화하는
  dispatcher 모델을 기본 결정으로 보정.
- 2026-05-30: source repo는 `/Users/kann/projects/*`, Hermes runtime state는
  `~/.hermes/*`에 두는 repository layout boundary를 추가.
- 2026-05-30: Hermes source repo를 `/Users/kann/projects/hermes-agent`로
  이동하고 `~/.hermes/hermes-agent`는 compatibility symlink로 전환. Hermes CLI
  wrapper, venv entrypoint shebang, launchd plist, global terminal cwd fallback,
  project-worker registry를 새 canonical path 기준으로 갱신. `hermes --version`,
  launchd plist lint, Harness docs validation은 통과했으며, gateway launchd
  start는 sandbox 밖 `launchctl bootstrap` 권한이 필요해 보류.
- 2026-05-30: Hermes gateway에 `_resolve_source_project_context`와
  `gateway_dispatch`/`workers` 기반 project-bound cwd resolution을 추가.
  `~/.hermes/config.yaml`에 `harness-starter`, `stagelink`, `hermes-agent`
  projects/workers와 Discord channel dispatch map을 추가. Agent turn에는
  Project-Bound Worker Context를 주입하고 route가 있는 메시지는
  `TERMINAL_CWD`/`HERMES_ACTIVE_PROJECT`를 route cwd로 고정한다.
  검증: `tests/gateway/test_channel_project_context.py`와
  `tests/hermes_cli/test_gateway.py` 38 passed.
- 2026-05-30: `hermes project register/list/show`를 추가해 project/worker/
  Discord route 등록을 CLI로 관리한다. `harness-starter`와 `stagelink`는
  dry-run 기준 `Changed: none`으로 현재 runtime config와 일치한다.
- 2026-05-30: Codex app-server adapter가 worker `allowed_write_roots`를
  sandbox `writable_roots`로 전달하지 않던 누락을 수정했다. Gateway는
  project route에서 writable roots를 계산하고, `/Users/kann/projects`를
  project clone/register workspace로 Codex sandbox에 전달한다.
- 2026-05-31: Agy 실행 시 `~/.gemini/antigravity-cli` 쓰기 권한이 별도 runtime
  state root로 필요하다는 점을 명시했다. Hermes gateway는 project-bound Codex
  worker sandbox에 repo root, `/Users/kann/projects`, Agy state root를 함께
  전달해야 한다.
- 2026-06-01: Agy review를 실행해 `go-with-changes`를 받았다. `git -C`/절대
  경로 patch 우회, cron binding 공백, local path/Discord id 오버리치,
  global/channel memory 오염, MVP 과확장을 SSOT 보정 항목으로 반영했다.
