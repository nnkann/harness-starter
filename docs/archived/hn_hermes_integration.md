---
title: Hermes × harness-starter 통합 설계 메모
domain: harness
problem: [P3, P5, P7]
s: [S3, S5, S7]
tags: [hermes, integration, gateway, cron, delegation]
status: abandoned
created: 2026-05-25
updated: 2026-06-01
relates-to:
  - path: decisions/hn_gemini_delegation_pipeline.md
    rel: references
  - path: decisions/hn_reminder_memory_contract.md
    rel: references
  - path: decisions/hn_runtime_adapter_unification.md
    rel: references
  - path: harness/hn_discord_project_gateway_isolation_ssot.md
    rel: references
---

# Hermes × harness-starter 통합 설계 메모

## 판단

Hermes와 harness-starter는 역할이 겹치기보다 보완된다.

- **harness-starter**: 프로젝트 로컬 규율, 스킬, hook, pre-check, CPS/docs workflow, migration 계약.
- **Hermes**: 메시징 gateway, 세션 검색, 지속 memory, cron, tool orchestration, subagent delegation, profile/runtime 관리.

따라서 결합 방향은 “harness를 Hermes 안에 흡수”가 아니라, Hermes가 harness-managed repo를 감지하고 그 프로젝트의 규칙·검증·스킬을 실행하는 **orchestration adapter**가 적합하다. runtime adapter 전체 정책은 `docs/decisions/hn_runtime_adapter_unification.md`가 이어받으며, 현재 기본 pilot stack은 Hermes + Codex + Agy다.

## 통합 목표

1. Hermes가 현재 workdir의 harness 여부를 자동 감지한다.
2. Hermes가 harness의 project-local skills/rules를 요약·로드한다.
3. Discord/Slack/CLI에서 자연어로 harness workflow를 호출한다.
4. Hermes cron이 harness health check를 주기 실행한다.
5. harness specialist 정의를 Hermes subagent/delegation preset으로 변환한다.
6. Hermes memory와 harness project memory의 경계를 분리한다.

## 1차 adapter — harness detector

Hermes가 workdir에서 아래 신호를 보면 harness project로 판정한다.

```text
.claude/HARNESS.json
.claude/scripts/pre_commit_check.py
.claude/skills/
.agents/skills/
docs/WIP/
docs/guides/project_kickoff.md
```

예상 출력:

```json
{
  "is_harness_project": true,
  "version": "0.52.8",
  "profile": "full",
  "is_starter": true,
  "runtime_stack": "hermes-codex-agy",
  "runtime_adapters": {"hermes": "orchestrator", "codex": "executor", "agy": "advisor", "claude": "optional-adapter"},
  "skills": ["implementation", "commit", "eval", "harness-upgrade"],
  "commands": {
    "precheck": "python .claude/scripts/pre_commit_check.py",
    "docs_validate": "python .claude/scripts/docs_ops.py validate",
    "verify_relates": "python .claude/scripts/docs_ops.py verify-relates",
    "eval_harness": "python .claude/scripts/eval_harness.py"
  }
}
```

## Hermes skill wrapper 후보

Hermes 사용자 skill로 다음 4개를 두면 초기 효과가 크다.

| Hermes skill | 역할 | 내부 참조 |
|---|---|---|
| `harness-project` | repo 감지, 버전/profile/WIP/health 요약 | `.claude/HARNESS.json`, `docs/WIP/` |
| `harness-eval` | pre-check/docs/eval 결과 실행·요약 | `.claude/scripts/*` |
| `harness-commit-assist` | staged diff, WIP, AC, pre-check 근거 정리 | `/commit` skill 계약 |
| `harness-upgrade-assist` | upstream/fallback upgrade 분석과 MIGRATIONS 안내 | `/harness-upgrade` skill |

주의: Hermes skill은 project-local harness skill을 그대로 복사하기보다, **loader/wrapper** 역할을 한다. SSOT는 특정 runtime 디렉터리 하나가 아니라 harness core contract와 runtime adapter 정책에 둔다. 과도기에는 `.claude/skills/*`가 legacy source 역할을 하지만, `.agents/skills/*`는 generated/validated Codex adapter 후보로 분류한다.

## Gateway UX

Discord/Slack에서 자연어를 harness command로 라우팅한다.

```text
@hermes 하네스 상태 봐줘
@hermes WIP 남은 거 요약해줘
@hermes 이번 변경 commit 가능해?
@hermes harness-upgrade 영향 분석해줘
@hermes eval --harness 돌리고 결과만 알려줘
```

Hermes는 다음 순서로 응답한다.

1. workdir/harness project 확인
2. safety: dirty tree와 staged diff 구분
3. 필요한 harness script 실행
4. raw log 대신 decision-grade summary 반환
5. 실패 시 “무엇이 막았는지 / 다음 owner action”을 분리해 출력

## Cron guardian

Hermes cron으로 harness health check를 자동화한다.

예시 스케줄:

- 매일 오전: pre-check + docs validate + verify-relates + WIP count
- 주 1회: eval_harness + migration drift + silent exception 후보 요약
- push 후: latest commit에 대한 health report

보고 형식:

```text
harness-starter daily check
- precheck: pass
- docs validate: warning 2
- relates-to: 0 broken
- WIP: 1 active
- tests: pass
- owner action: archived filename warning 정리 여부 결정
```

## Subagent/delegation 연결

harness의 specialist 정의를 Hermes `delegate_task` preset으로 매핑한다.

| harness specialist | Hermes delegation 용도 |
|---|---|
| `doc-finder` | docs/clusters → 후보 본문 탐색 |
| `codebase-analyst` | 내부 코드·문서 구조 분석 |
| `risk-analyst` | 과잉 설계·운영 리스크 반론 |
| `threat-analyst` | public repo/secrets/supply-chain 관점 점검 |
| `performance-analyst` | hook/test/runtime 비용 점검 |
| `review` | staged diff 단위 pre-commit 검증 |

초기 구현은 `.codex/agents/*.toml`과 `.claude/agents/*.md`를 직접 실행하지 않고, Hermes가 역할 설명을 읽어 `delegate_task` context로 주입하는 방식이 안전하다.

## Memory 경계

상세 정책은 `decisions--hn_hermes_managed_downstream_memory.md` WIP가 SSOT 후보다.
본 통합 메모는 Hermes adapter 관점의 요약만 유지한다.

- harness memory: repo-local compatibility signal, reminder pointer, 단독 실행 fallback.
- Hermes memory: 사용자 선호, 안정적인 프로젝트 관계, cross-downstream 운영 방식의 짧은 포인터.
- Hermes session_search: 과거 Discord/CLI 판단을 찾아 현재 repo 작업에 연결.
- Hermes skills: 반복 절차와 downstream 운영 playbook.
- Hermes manifest/cron: downstream 목록, 점검 정책, delta report.

금지:

- 프로젝트 정책을 Hermes user memory에 영구 저장해서 다른 repo에 오염시키기.
- Hermes episodic memory를 harness docs SSOT처럼 취급하기.
- `.claude/memory` 내용을 항상 통째로 system prompt에 주입하기.
- repo-local reminder를 사실 증거로 단정하기.

## 구현 단계

### Phase 1 — 감지와 요약

- `detect_harness_project(workdir)` 설계.
- `.claude/HARNESS.json` 파싱.
- WIP count, version, profile, available skills 요약.
- Python 3.10+ runtime check 포함.

### Phase 2 — health command wrapper

- pre-check/docs validate/verify-relates/eval_harness 실행 wrapper.
- stdout contract를 Hermes summary schema로 정규화.
- 실패를 pass/warn/block/owner-action으로 분류.

### Phase 3 — gateway command routing

- 자연어 intent → harness action 매핑.
- Discord/Slack report format 확정.
- long output은 파일 artifact 또는 condensed summary로 전환.

### Phase 4 — cron guardian

- daily/weekly health report template.
- workdir pinned cron job.
- 결과를 origin Discord thread 또는 home channel로 전송.

### Phase 5 — delegation preset

- specialist role parser.
- `delegate_task` context template.
- review/risk/doc-finder 3종부터 연결.

## 열린 결정

- Hermes orchestration adapter를 Hermes core에 둘지, Hermes skill로 둘지.
- harness repo가 Hermes skill registry에 직접 publish될지.
- project-local legacy `.claude/skills`와 generated `.agents/skills`를 Hermes skill schema로 변환할 때 frontmatter 필드 매핑.
- gateway에서 workdir 선택을 어떻게 할지: channel default, explicit repo alias, 또는 command arg.
- cron report가 WIP를 자동 생성/갱신할지, 단순 알림에 머물지.

**Acceptance Criteria**:
- [x] Goal: Hermes가 harness-managed repo를 감지하고 S3/S5/S7 기준의 상태·실행·문서 계약을 요약할 수 있는 통합 방향을 정리한다.
  검증:
    review: self
    tests: python .claude/scripts/pre_commit_check.py; python .claude/scripts/docs_ops.py validate; python .claude/scripts/docs_ops.py verify-relates
    실측: Hermes adapter 구현 시 non-harness repo / harness-starter / downstream harness repo 3케이스에서 감지 결과가 구분된다.
- [x] S3: 다운스트림 silent fail을 줄이도록 Python 요구사항, health command, owner action 출력 계약이 드러난다.
- [x] S5: project-local skills/rules를 통째로 주입하지 않고 wrapper/summary 방식으로 컨텍스트 팽창을 제한한다.
- [x] S7: Hermes memory와 harness project memory의 소유권·경계·출력 의미가 문서에 분리된다.

## 검증 후보

- `python .claude/scripts/pre_commit_check.py`
- `python .claude/scripts/docs_ops.py validate`
- `python .claude/scripts/docs_ops.py verify-relates`
- Hermes 측 adapter unit test: non-harness repo / harness-starter / downstream harness repo 3케이스

## 정리 결과

이 문서는 Hermes 통합 방향의 초기 설계 메모로 보존하되, 활성 WIP로 남기지
않는다. 본문 판단은 다음 문서로 흡수되었다.

- runtime stack과 adapter 경계: `docs/decisions/hn_runtime_adapter_unification.md`
- Discord/project-bound gateway 격리: `docs/harness/hn_discord_project_gateway_isolation_ssot.md`
- downstream memory/guardian 경계: `docs/decisions/hn_hermes_managed_downstream_memory.md`

따라서 새 구현 기준으로는 이 문서가 SSOT가 아니다.
