---
title: harness-starter core/overlay/local(Hermes) 경계 및 구조 개선안 설계 WIP
domain: harness
c: "Hermes가 하네스를 대체하지 않고 하네스 실행 계층으로 작동하도록, core/overlay/local binding과 worker routing을 시스템화해야 한다."
problem: [P2, P3, P5, P7, P8, P11]
s: [S2, S3, S5, S7, S8, S11]
tags: [harness, overlay, hermes, routing, feedback]
relates-to:
  - path: docs/WIP/guides--hn_hermes_integration.md
    rel: extends
  - path: docs/harness/hn_feedback_channel_format.md
    rel: extends
  - path: docs/guides/hn_upgrade_propagation.md
    rel: extends
status: in-progress
created: 2026-05-27
---

# 하네스 스타터 core/overlay/local binding 구조 개선안 WIP

**Acceptance Criteria**:

- [x] Goal: S2/S3/S5/S7/S8/S11 기준으로 Harness가 SSOT이고 Hermes가 orchestration/control-plane인 구조를 문서·스키마·업그레이드 흐름에 반영한다.
  검증:
    review: self
    tests: python3.11 .claude/scripts/pre_commit_check.py; python3.11 .claude/scripts/docs_ops.py validate; python3.11 .claude/scripts/docs_ops.py verify-relates; python3.11 .claude/scripts/docs_ops.py validate-harness-architecture; /Users/kann/.hermes/hermes-agent/venv/bin/python -m pytest .claude/scripts/tests/test_harness_architecture_contract.py -q
    실측: downstream 적용 시 Harness core·project overlay·local Hermes binding 경계가 분리되고, feedback intake와 worker routing이 role 중심으로 설명된다.
- [x] S7: Harness core / downstream project overlay / local Hermes execution binding 3계층 ownership이 표와 경로 예시로 명문화된다.
- [x] S5/S7: provider-independent worker taxonomy와 cost-routing tier가 모델명이 아니라 role/engine-class 중심으로 정의된다.
- [x] S3/S8: downstream → harness-starter typed feedback intake loop와 최소 report format이 정의된다.
- [x] S3/S7: git subtree와 vendored snapshot + `.harness/upstream.lock` + upgrade script의 장단점, 초기안, migration path가 기록된다.
- [x] S7/S8: Hermes memory/profile/session과 Harness docs/WIP/decision/intake의 책임 경계가 명문화된다.
- [x] S11: `.claude`, `.codex`, `.agents`, `.harness` 등 legacy/engine-specific 폴더의 장기 정리 방향과 직접 수정 금지 영역이 정리된다.
- [x] S2/S5: tiny LLM/script-only/docs-relay 작업과 specialist worker 작업의 분리 기준이 있어, 불필요한 비싼 worker 호출을 줄인다.

## CPS Rationale

- C → P: Hermes gateway·memory·profile이 편해서 Harness SSOT를 우회하면 P7(소유권 불투명), P8(memory 의존), P3(다운스트림 silent fail), P11(동형 구조 drift)이 동시에 발생한다.
- P → S: S7은 ownership/output contract를 드러내고, S8은 reminder/memory 의존을 상태화하며, S3은 downstream 전파 실패를 줄이고, S5/S2는 context/cost 폭증을 줄인다.
- S → AC: AC는 경계·routing·feedback·upgrade·legacy 정리를 실제 문서/스키마/검증 대상으로 남겨, Harness가 Hermes보다 상위 SSOT라는 사실을 검증 가능하게 만든다.

## 현재 판단

이 작업의 핵심 결정은 다음 한 문장이다.

> Hermes는 Harness를 대체하지 않는다. Hermes는 Harness를 실행하고 증폭하는 control-plane이며, Harness가 프로젝트별 workflow contract와 SSOT를 소유한다.

따라서 Codex, agy, Copilot, 향후 Gemma 4 2B 같은 tiny/local LLM은 “필수 에이전트”가 아니라 Harness role을 수행하는 교체 가능한 engine이다. 필수 단위는 모델명이 아니라 role contract다.

## 1. 3계층 ownership 모델

| 계층 | 소유자 | repo commit 여부 | 예시 경로 | 변경 원칙 |
|---|---|---:|---|---|
| Harness core | harness-starter upstream | 예 | `.claude/scripts/`, `.claude/skills/`, `.claude/rules/`, `docs/harness/`, 향후 `.harness/core/` | downstream에서 직접 영구 수정하지 않는다. 필요한 변경은 upstream-candidate로 보고 후 harness-starter에서 수정한다. |
| Downstream project overlay | 각 downstream repo | 예 | `docs/WIP/`, `docs/decisions/`, `.claude/rules/naming.md`의 도메인/경로 매핑, `.harness/project/`, `.harness/hermes/workers.yaml` | 프로젝트 고유 규칙·도메인·운영 제약을 담는다. core 파일을 patch하는 대신 overlay로 확장한다. |
| Local Hermes execution binding | 사용자 로컬 Hermes 환경 | 아니오 | `~/.hermes/profiles/*`, `~/.hermes/config.yaml`, `~/.local/bin/codexworker`, `~/.local/bin/agy`, cron job id, provider auth | 인증·모델·로컬 경로·worker runtime 상태. repo SSOT가 아니며, downstream으로 복사하지 않는다. |

### 경계 규칙

1. upstream-owned core 파일을 downstream agent가 직접 수정하려는 경우, 우선 `upstream-candidate` intake를 만든다.
2. downstream-only 규칙은 core에 섞지 않고 overlay에 둔다.
3. local Hermes binding은 repo 문서에 “필요한 role/engine class”만 남기고 token, profile id, cron id, local absolute secret path는 커밋하지 않는다.
4. Harness core는 “무엇을 해야 하는가”를 정의하고, Hermes는 “어떤 worker로 실행할 것인가”를 결정한다.
5. downstream upgrade는 core overwrite가 아니라 `detect → classify → review → apply → verify` 흐름으로 진행한다.

## 2. 권장 파일 구조 초안

```text
harness-starter/
  .claude/                         # 현재 core runtime. 단기 유지.
    skills/
    rules/
    scripts/
    agents/
  .codex/                          # engine-specific binding. 장기적으로 legacy/adapter화 후보.
  .agents/                         # provider-neutral agent contract 후보.
  docs/
    harness/                       # Harness core 결정·이력·업그레이드 SSOT
    guides/                        # 사용 절차
    decisions/                     # architecture/ownership 결정
    WIP/                           # 진행 중 작업
  .harness/                        # 신규 후보. 안정화 전까지 점진 도입.
    upstream.lock                  # downstream에서 현재 적용된 harness-starter ref 기록 후보
    core/                          # subtree 또는 vendored snapshot 후보
    schemas/
      workers.schema.yaml          # role/worker manifest schema 후보
      feedback.schema.yaml         # downstream intake schema 후보
    hermes/
      workers.yaml                 # project-local Hermes role binding 후보
      prompts/
    project/
      overlay.yaml                 # downstream-specific ownership/constraints 후보
```

단기적으로 `.claude`를 즉시 제거하지 않는다. 기존 downstream과 skill flow가 `.claude`를 기준으로 움직이기 때문이다. 대신 `.harness/*`를 새 canonical layer 후보로 도입하고, `.claude`는 “current core runtime path”로 명시한다.

## 3. Provider-independent worker taxonomy

| Role | 책임 | write permission | 기본 engine class | 현재 mapping 예시 | 호출 조건 | 호출 금지/주의 |
|---|---|---|---|---|---|---|
| orchestrator | 요청 triage, Harness rule 확인, worker dispatch, 결과 reconciliation | 제한적 | stable control-plane LLM | Hermes + Copilot gpt-4.1 | 모든 요청의 진입점 | 긴 구현/리서치를 직접 붙잡지 않음 |
| coder | 코드 수정, 테스트 작성, refactor, bounded patch | 허용, repo 정책 따름 | strong coding worker | codexworker / Codex gpt-5.5 | 구현·테스트·리팩터링 | repo lock 없이 병렬 write 금지 |
| reviewer | diff/AC/보안/회귀 검토 | read-only 기본 | independent reviewer | agy, Codex review, future model | 고위험 변경, Codex patch 후 | 검증 없이 사실로 채택 금지 |
| researcher | 외부 문서·대안·기술 조사 | read-only | research/advisory worker | agy async lane | 외부 지식·기술 선택 | project SSOT보다 우선하지 않음 |
| debug-finder | 로그·실패·재현·원인 후보 분석 | read-only 기본 | diagnostic worker | agy 또는 Hermes bounded | 1회 시도 후 원인 불명, 반복 실패 | 곧장 patch하지 않음 |
| internal-steward | repo history/docs/CPS/decisions 기반 내부 연속성 보호 | read-only 또는 scoped write | repo-context worker | Codex/Hermes | 기존 결정과 충돌하는 변경 | 새 best practice만으로 기존 의도 폐기 금지 |
| external-advisor | 외부 시각, 놓친 선택지, vendor/API shift 탐색 | read-only | external advisory worker | agy | architecture/product/stack 결정 | output은 advisory |
| efficiency-arbiter | 비용·시간·위험·검증 예산 기준 선택 | read-only | cheap/stable reasoning | agy+Hermes 또는 small model | full council이 과한지 판단 | 과잉 council 방지 |
| harness-maintainer | Harness docs/skills/scripts/schema 유지 | scoped write | Harness-aware worker | Hermes/Codex bounded | Harness core/overlay 변경 | downstream 특수 규칙 core 혼입 금지 |
| downstream-guardian | downstream 상태·WIP·upgrade·feedback 수집 | read-only 기본 | script-only + small synthesis | cron no_agent, Hermes | daily/weekly health | 자동 merge/commit 금지 |
| cron-lite | deterministic check | read-only | script-only/tiny LLM | no_agent script | green baseline 반복 체크 | 비싼 모델 사용 금지 |
| docs-relay / report-formatter / tiny-worker | 전달·요약·분류·changelog formatting | docs-only | tiny/local/cheap LLM | Copilot small, future Gemma 4 2B | 단순 문서 relay/report | architecture 판단/코딩 금지 |

Role은 stable contract이고 engine은 교체 가능한 binding이다. Manifest에는 `preferred_engine_class`와 `fallback_engine_class`를 우선 기록하고, 구체 provider/model은 local Hermes binding 또는 project override에 둔다.

## 4. Cost-routing tier 정책

| Tier | 이름 | 예시 | engine | 종료 조건 |
|---|---|---|---|---|
| 0 | script-only | git status, WIP count, hash, unchanged health check | shell/Python no_agent | stdout empty면 silent success 가능 |
| 1 | tiny/docs worker | 단순 요약, 전달, changelog, candidate 초안 분류, report formatting | tiny/local/cheap LLM | 판단 없는 정리 결과 |
| 2 | stable orchestrator | routing, 사용자 응답, worker 결과 종합, 중간 판단 | Hermes/Copilot 등 stable model | worker dispatch 또는 최종 synthesis |
| 3 | specialist worker | coding, deep debug, independent review, external research | Codex, agy 등 | bounded timeout + artifact |
| 4 | council path | Harness core 변경, architecture, migration, security/deploy/db 정책 | orchestrator + advisor/steward/arbiter | decision summary + verification |

Escalation rule:
- Tier 0/1에서 evidence가 충분하면 멈춘다.
- code write가 필요하면 Tier 3 coder로 보낸다.
- 불확실성/위험/반복 실패가 있으면 Tier 3 debug/review 또는 Tier 4 council로 올린다.
- 단순 문서 전달과 상태 relay를 specialist worker에게 보내지 않는다.

## 5. Downstream → harness-starter feedback intake

### 타입

| type | 의미 | 예시 next action |
|---|---|---|
| local-only | downstream 특수 규칙 | overlay에만 기록 |
| upstream-candidate | 여러 downstream에 일반화 가능한 core 개선 | harness-starter WIP/issue로 승격 |
| hermes-routing-candidate | Hermes dispatch/profile/cron 개선 | local Hermes config 또는 Harness Hermes manifest 개선 |
| worker-role-candidate | 새 role 또는 role contract 변경 | worker taxonomy 업데이트 |
| docs-schema-candidate | WIP/decision/intake schema 변경 | docs rule/schema 업데이트 |
| safety-policy-candidate | secret/deploy/db/permission 관련 안전 정책 | review-deep + owner approval |
| validation-gap | precheck/docs_ops/eval이 못 잡은 실패 | deterministic gate 추가 후보 |
| agent-failure-pattern | LLM/CLI가 반복 실수한 패턴 | skill/rule/prompt/guard 개선 |
| upgrade-friction | harness-upgrade 적용 중 충돌/불명확성 | MIGRATIONS/upgrade script 개선 |

### 최소 intake schema 초안

```yaml
version: 1
schema: harness-feedback-intake
source:
  project: stagelink
  repo: /path/to/downstream
  harness_ref: <current upstream ref or unknown>
  collected_by: downstream-guardian|harness-maintainer|manual
  collected_at: 2026-05-27T00:00:00+09:00
classification:
  type: upstream-candidate
  confidence: medium
  affected_layer: core|overlay|local-binding|unknown
summary: "반복되는 문제 1줄"
evidence:
  - kind: command|wip|incident|user-report|diff|log
    ref: "docs/WIP/... 또는 command 요약"
owner_action:
  required: true
  question: "core로 승격할지?"
proposed_next_step:
  target_repo: harness-starter
  action: create-wip|update-rule|update-skill|update-script|document-only
```

### 흐름

```text
downstream project
→ guardian / harness-maintainer
→ typed classification
→ harness-starter intake queue
→ dedup + priority + design
→ harness-starter core/skill/schema change
→ harness-upgrade report
→ downstream apply/verify
```

Daily guardian는 deterministic delta만 모으고, 의미 있는 변화가 있을 때만 Tier 1/2 synthesis를 호출한다.

## 6. Subtree vs snapshot tracking 판단

| 방식 | 장점 | 단점 | 적합 조건 |
|---|---|---|---|
| git subtree `.harness/core` | upstream ref 추적 명확, 실제 파일 포함, diff/merge 가능 | 사용법 복잡, conflict 관리 필요, core/overlay 경계 흐리면 위험 | core 파일이 downstream에서 거의 그대로 유지될 때 |
| vendored snapshot + `.harness/upstream.lock` | 단순, main-only downstream에 안전, upgrade script로 통제 쉬움 | git-native merge 이력 약함, drift 계산 로직 필요 | 초기 도입, downstream 변형이 아직 많은 단계 |
| package/core + overlay | 배포 경계 명확, runtime dependency화 가능 | package manager/버전 관리 부담, 로컬 offline성 저하 | core API가 안정되고 설치/업데이트 채널이 필요할 때 |

초기 결정 후보:
1. 지금은 vendored snapshot + `.harness/upstream.lock` + upgrade report를 먼저 설계한다.
2. `.harness/core` subtree는 core/overlay 경계가 안정된 뒤 migration path로 둔다.
3. StageLink처럼 main-only/no-worktree repo에서도 `detect → report → owner approval → apply → verify`가 가능해야 한다.
4. core 내부 직접 수정은 precheck/eval에서 warn/block 후보로 삼는다.

`.harness/upstream.lock` 후보:

```yaml
version: 1
schema: harness-upstream-lock
upstream:
  repo: https://github.com/nnkann/harness-starter.git
  ref: <commit-or-tag>
  applied_at: 2026-05-27T00:00:00+09:00
layout:
  core_path: .claude
  overlay_path: .harness/project
  hermes_binding_path: .harness/hermes
policy:
  core_direct_edit: report-upstream-candidate
  apply_mode: owner-approved
```

## 7. Hermes/Harness memory 및 책임 경계

| 항목 | Harness에 남길 것 | Hermes/local에 남길 것 |
|---|---|---|
| 프로젝트 규칙 | docs, rules, WIP, decisions, overlay manifest | 없음. 요약 참조만 가능 |
| 사용자 장기 선호 | 원칙이 project workflow로 승격된 경우 docs/rules | 일반 선호와 로컬 운영 방식 |
| provider/model | role contract에는 engine class만 | 실제 provider/model/profile/auth |
| cron/worker 상태 | 요구되는 check contract | cron id, PID, local path, auth |
| downstream feedback | intake/WIP/decision | session transcript 검색 보조 |

금지:
- Hermes memory를 Harness SSOT처럼 사용하기.
- `.claude/memory`나 reminders를 검증된 현재 사실처럼 보고하기.
- provider-specific prompt를 Harness core rule로 고정하기.
- Discord에 긴 지시문을 보낸 것만으로 durable work가 시작됐다고 간주하기.

## 8. Legacy/engine-specific 구조 정리 방향

현재 `.claude`는 사실상 Harness core runtime이고, `.codex`는 Codex binding이며, `.agents`는 provider-neutral agent contract 후보로 보인다. 즉시 rename/move하면 downstream upgrade가 깨질 수 있으므로 다음 순서가 안전하다.

1. 현행 경로 역할 문서화: `.claude = current core runtime`, `.codex = engine adapter`, `.agents = neutral contract candidate`.
2. 새 canonical 후보 `.harness/*`를 문서/스키마부터 도입한다.
3. `harness-upgrade`가 legacy 경로와 새 경로를 모두 인식하도록 한다.
4. downstream guardian가 engine-specific 파일 변경을 `local-binding` 또는 `engine-adapter`로 분류하도록 한다.
5. 충분한 migration window 후 `.harness/core` 또는 snapshot layout으로 이동한다.

Blocker:
- 기존 downstream들이 `.claude` 경로를 직접 참조한다.
- precheck/docs_ops/skills가 `.claude`를 전제로 한다.
- `.codex` 제거/이동은 Codex worker 운용과 충돌할 수 있다.
- 따라서 legacy 정리는 “삭제”가 아니라 “역할 축소 + adapter화 + migration guide”가 먼저다.

## 9. 다음 구현 후보

1. `docs/harness/hn_harness_first_architecture.md` 또는 decision 문서로 본 WIP의 stable portion 승격.
2. `.harness/upstream.lock` sample과 `.harness/schemas/feedback.schema.yaml`, `.harness/schemas/workers.schema.yaml` 초안 추가.
3. `docs/harness/MIGRATIONS.md`에 core/overlay/local binding upgrade note 추가.
4. `eval --harness` 또는 precheck에 core direct edit / missing upstream.lock / invalid workers.yaml warning 추가.
5. Hermes 쪽 skill/reference에는 “Discord prompt 전송 ≠ durable work 시작” pitfall을 유지한다.

## 진행 로그

- 2026-05-27: WIP 생성. implementation/harness-init/docs 규칙 확인.
- 2026-05-27: core/overlay/local ownership, role taxonomy, cost tier, feedback intake, subtree vs snapshot, memory boundary, legacy 정리 방향을 1차 WIP로 작성.
- 2026-05-27: `.harness/upstream.lock`, `.harness/hermes/workers.yaml`, `.harness/project/overlay.yaml`, `.harness/schemas/{workers,feedback}.schema.yaml`와 `docs_ops.py validate-harness-architecture` 검증 명령을 추가해 설계를 실행 가능한 contract로 승격.
