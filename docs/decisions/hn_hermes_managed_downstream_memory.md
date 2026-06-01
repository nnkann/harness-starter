---
title: Hermes-managed downstream memory/reminder 운영 경계
domain: harness
c: "Hermes가 StageLink 같은 downstream을 주기적으로 살피는 운영 주체가 되면 repo-local memory/reminder와 Hermes memory/session_search/skills/cron의 책임이 겹친다."
problem: [P7, P8]
s: [S7, S8, S9]
tags: [hermes, memory, downstream, reminder, cron]
status: completed
created: 2026-05-26
updated: 2026-06-02
---

# Hermes-managed downstream memory/reminder 운영 경계

## 결정 요약

Hermes가 downstream 운영 루틴을 맡는 경우 `.claude/memory/`와 `.claude/memory/reminders/`는 장기 판단의 중심 저장소가 아니다.
repo-local memory/reminder는 **하네스 단독 실행 fallback**과 **SSOT 재확인 pointer**로 유지하고, 장기 운영 책임은 Hermes 계층으로 옮긴다.

| 정보 | Owner | 이유 |
|---|---|---|
| 사용자 선호, 프로젝트 관계처럼 downstream 밖에서도 유효한 짧은 사실 | Hermes built-in memory | 모든 세션에 작게 주입되어야 함 |
| 과거 Discord/CLI 논의, 일회성 판단, WIP 대화 | Hermes session_search | stale 가능성이 있으므로 검색 후 재확인 |
| 반복 절차: downstream health check, memory triage, cron report 해석 | Hermes skill | 절차는 memory가 아니라 skill |
| downstream 목록, repo path, branch, 점검 주기, 마지막 관찰 상태 | Hermes project registry/manifest | cron이 기계적으로 읽을 운영 데이터 |
| repo 내부 정책·CPS·완료 문서·현재 WIP | downstream repo docs | 프로젝트 SSOT |
| repo-local reminder | downstream repo memory/reminders | 사실 증거가 아니라 “확인해 볼 후보” |

## StageLink 1차 적용 방향

StageLink는 현재 첫 downstream pilot이다. Hermes routine은 한 번에 모든 자동화를 만들지 않고 다음 순서로 붙인다.

1. `stagelink` manifest entry를 만든다.
2. Hermes cron이 StageLink repo에서 `git status`, WIP 목록, harness 검증 명령, memory/reminder inventory를 읽는다.
3. cron report는 “새 사실”이 아니라 “확인이 필요한 delta”만 보고한다.
4. 반복되는 판단/절차는 Hermes skill로 승격하고, repo docs에는 프로젝트 고유 정책만 남긴다.
5. downstream이 늘어나면 manifest에 entry를 추가하고 동일 runner를 재사용한다.

## StageLink 2026-05-26 1차 inventory

- repo: `/Users/kann/projects/stagelink`
- branch/status: `main...origin/main`, dirty 없음.
- harness: `.claude/HARNESS.json` 기준 `profile=full`, `version=0.52.6`, `is_starter=false`.
- WIP: 2개
  - `docs/WIP/decisions--ar_multilang_coverage.md`
  - `docs/WIP/incidents--cr_multiplatform_crawl_integrity.md`
- health:
  - pre-check: pass. 단 `pre-commit hook 미설치` 경고가 owner-action 후보.
  - docs validate: pass, 경고 0.
  - verify-relates: pass, 미연결 0.
- memory/reminder inventory: 14개
  - `MEMORY.md`, `project_eval_last.md`: Downstream-local keep.
  - `feedback_*.md` 3개: Archive-drop 후보. 현 정책상 stale 여부를 재확인해야 한다.
  - `reminders/*.md` 9개: Downstream-local keep / Hermes signal.
  - `reminder_defense_success.md`: Harness SSOT promote 후보. guard 방어 성공 데이터라 upstream 정책·평가로 승격할 가치가 있다.

이 inventory는 사실 확정 문서가 아니라 Hermes cron이 읽을 baseline 후보이다. 다음 단계에서 cron report가 같은 분류를 자동으로 재생성해야 한다.

## Manifest schema 초안

```yaml
projects:
  stagelink:
    repo: /Users/kann/projects/stagelink
    type: harness-downstream
    default_branch: main
    language: ko
    no_worktree: true
    report_target: origin
    cadence:
      light: daily
      deep: weekly
    checks:
      - git_status
      - wip_inventory
      - harness_precheck
      - docs_validate
      - verify_relates
      - memory_reminder_inventory
    memory_policy:
      repo_memory_role: compatibility_signal
      hermes_memory_role: stable_cross_project_facts_only
      session_search_role: episodic_discussion_recall
      skills_role: repeatable_operations
```

## Cron/update 계약

운영 반영:

- daily cron은 `harness-downstream-learning-check`로 전환했다. Hermes project
  registry의 `type: harness-downstream` 프로젝트를 순회하며 **매일 04:00 KST**
  실행한다.
- daily job은 read-only다. 자동 실행이 downstream 파일을 임의 변경하지 않는다.
- 각 downstream의 health gate, readiness, eval, `migration-log.md` Feedback
  Reports를 확인하고 `accept-candidate` / `reject` / `owner-action`으로 분류한다.
- 별도 manual executor cron을 만들었다. 필요할 때 `cron run`으로 호출해 harness-upgrade 적용을 시도하되, dirty tree·충돌·owner 선택·Agy/Codex 안전성 이견이 있으면 멈추고 보고한다.
- executor도 commit/push는 하지 않는다. downstream 커밋은 각 repo의 `/commit` 흐름을 따른다.

보고서는 아래를 구분해야 한다.

- `fact`: 현재 repo에서 명령으로 확인한 사실.
- `memory-signal`: reminder/memory가 가리킨 재확인 후보.
- `delta`: 지난 실행 대비 변화.
- `owner-action`: 사용자가 결정해야 하는 항목.
- `candidate-upstream-change`: harness-starter로 되올릴 수 있는 정책/도구 개선 후보.
- `accept-candidate`: upstream에 수용 검토할 downstream Feedback Report.
- `reject`: 하네스 downstream이 아니거나 필수 필드·근거가 부족해 반려할 신호.
- `harness-upgrade`: current/upstream version/ref, 적용 가능성, manual executor 실행 여부.
- `agy_review` / `codex_review`: 서로 다른 관점의 advisory review. 둘이 이견이면 owner-action으로 격상.

`memory-signal`은 사실처럼 쓰지 않는다. 반드시 repo 문서·코드·실행 결과 중 하나로 재확인한다.
Agy/Codex 응답도 사실이 아니라 견제·보완용 검토 신호다. Hermes가 live repo evidence와 대조해 최종 보고한다.

**Acceptance Criteria**:

- [x] Goal: S7/S8/S9 기준으로 Hermes-managed downstream에서 하네스 memory/reminder의 owner와 출력 의미를 재정의한다.
  검증:
    review: self
    tests: `python3 .claude/scripts/docs_ops.py validate`; `python3 .claude/scripts/docs_ops.py verify-relates`
    실측: 이 WIP가 `.claude/memory/`를 repo-local compatibility signal로 낮추고, Hermes memory/session_search/skills/manifest/cron의 역할을 분리한다.
- [x] S7: `docs/WIP/decisions--hn_memory.md`가 이 정책을 참조하고, `.claude/memory/`의 지위를 repo-local compatibility signal로 낮춘다.
- [x] S8/S9: `docs/WIP/decisions--hn_reminder_memory_contract.md`가 Hermes-managed downstream에서 reminder를 확인 후보로 제한한다고 명시한다.
- [x] S7: downstream manifest schema 초안이 존재한다.
- [x] StageLink memory/reminder inventory가 작성되고, 각 항목이 `Hermes absorb / Harness SSOT promote / Downstream-local keep / Archive-drop` 중 하나로 분류된다.
- [x] daily cron runner가 Hermes project registry 기반 downstream 순회로 전환된다.
- [x] daily guardian cron이 매일 04:00 KST 실행되며 read-only로 health와 learning signal을 보고한다.
- [x] StageLink manual executor cron이 필요 시 직접 호출 가능한 형태로 존재하고, commit/push 없이 harness-upgrade 적용을 시도하도록 제한된다.
- [x] Agy/Codex 상호 견제 계약이 guardian skill과 cron prompt에 반영된다.
- [x] Hermes skill에 downstream health check와 memory/reminder triage 절차가 저장된다.
- [x] Cron report가 memory/reminder와 downstream Feedback Reports를 사실 증거가 아니라 재확인 signal로 표시하고, 수용 후보·반려·owner-action을 구분한다.
