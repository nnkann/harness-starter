---
title: reminder memory 계약 명확화
domain: harness
c: "review 기본 skip 재검토 항목을 signal로 등록하려다 reminder가 retention·management·exposure·CPS·memory·grouped recall과 결합된 계약임을 확인함"
problem: P8
s: [S8, S9]
tags: [memory, reminder, signal, kv-group]
relates-to:
  - path: decisions/hn_hermes_managed_downstream_memory.md
    rel: references
status: completed
created: 2026-05-20
updated: 2026-05-27
---

# reminder memory 계약 명확화

## CPS Rationale

- C -> P: reminder를 단순 rename으로 처리하면 보존·관리·출현·grouped recall 규칙이 흩어져 다음 세션에서 다시 누락된다.
- P -> S: S8은 reminder를 상태 파일과 recall route로 남기고, S9는 memory·group hit를 사실 증거가 아닌 재확인 후보로 제한한다.
- S -> AC: reminder를 project memory의 1급 하위 타입으로 정의하고 lifecycle·노출·CPS·kv_group 관계를 memory SSOT와 session-start 실행부에 모은다.

## 문제 재정의

2026-05-26 보강: Hermes-managed downstream에서는 reminder의 owner가 repo-local memory 자체가 아니다.
상위 정책은 `decisions--hn_hermes_managed_downstream_memory.md`이며, reminder는 Hermes가 읽을 수 있는
signal source이자 SSOT 확인 후보로 제한된다. reminder 본문을 Hermes built-in memory에 통째로 복사하지 않고,
반복 절차는 Hermes skill로, downstream 상태는 Hermes manifest/cron delta report로 이동한다.

처음에는 review 기본 skip 재검토 항목을 `.claude/memory/signal_*.md`로 남기려 했다.
하지만 사용자가 지적한 핵심은 파일명 문제가 아니었다. `reminder`는 다음 세션에
무엇을 다시 떠올릴지 결정하는 기능이므로 다음 계약과 함께 정의되어야 한다.

- 보존: 얼마나 오래 유지하고 언제 stale로 볼 것인가
- 관리: 생성·승격·만료·폐기·병합·억제를 누가 어떤 필드로 표현할 것인가
- 출현: session-start에서 언제 보여주고 언제 숨길 것인가
- CPS: reminder가 어떤 Problem/Solution의 누락 방어인지 어떻게 표시할 것인가
- memory: reminder가 사실 증거가 아니라 재확인 후보라는 제한을 어떻게 강제할 것인가

따라서 이번 작업의 본질은 `signal` -> `reminder` rename이 아니라,
project memory 안에 "다시 떠올릴 후보" 타입을 명시하고, SSOT를 한 곳에 고정하는 것이다.

## 검토 입력

- advisor: reminder는 독립 기능으로 승격하지 말고 project memory의 1급 하위 타입으로 둔다.
  독립 기능화는 이름은 선명하지만 `rules/memory.md`, `session-start.py`, CPS, WIP,
  decision/incident에 규칙이 퍼져 SSOT drift 위험이 커진다.
- Gemini: Letta/MemGPT의 core/archival 분리, OpenClaw의 gated active memory,
  Hermes의 session-start snapshot, LangGraph의 schema/scope/retrieval 축을 참고해
  lifecycle·노출 예산·stale 검증을 명시해야 한다.
- advisor/agy: `kv_group`은 hard filter가 아니라 routing hint일 때만 P8/P9 계약과
  양립한다. group이 맞지 않는 eligible reminder를 숨기면 P8 false negative가 되고,
  group hit가 stale 표시를 덮으면 P9 오염이 된다.
- 사용자 검토: reminder가 커질 때 grouped recall은 부가 최적화가 아니라 핵심
  전략이다. 문서만 남기지 말고 최소 실행부와 AC까지 같은 wave에서 닫아야 한다.
- 외부 레퍼런스 요지:
  - OpenClaw: active memory는 모든 추론 경로가 아니라 eligible persistent session에서만
    bounded recall을 수행한다. dreaming은 short-term signal을 score/frequency/diversity gate로
    long-term memory 승격 후보로 만든다.
  - Hermes: `MEMORY.md`/`USER.md` 같은 작은 snapshot은 세션 시작에 주입하고,
    episodic memory는 검색 기반으로 따로 둔다.
  - Letta/MemGPT: 항상 보여야 하는 core memory와 필요 시 검색하는 archival memory를 분리한다.
  - LangGraph/Deep Agents: memory는 duration/type/scope/update/retrieval/permission 축을
    분리해 설계한다.

## 선택지

리서치 입력을 단순히 "이름을 바꿀까?"로 축소하면 이 작업의 가치가 사라진다.
실제 선택지는 reminder를 어느 계층까지 끌어올릴지다.

| 선택지 | 모델 | 장점 | 문제 | 판정 |
|--------|------|------|------|------|
| A. `signal` 유지 | 기존 반복 신호 파일 유지 | 구현 변경 없음 | 사용자 관점에서 기능명이 불명확하고 P8 누락 방어가 약함 | 기각 |
| B. 단순 rename | `signal_*` -> `reminder_*` | 즉시 명확해짐 | retention·lifecycle·exposure·CPS 계약이 빠져 다시 drift 발생 | 기각 |
| C. memory 하위 타입 | `.claude/memory/reminders/reminder_*.md` + schema | SSOT 안정성, CPS 정합, 되돌림 용이 | 노출/만료/승격 자동화는 약함 | **Phase 0 채택** |
| D. 독립 reminder 기능 | `.claude/reminders/` + 전용 규칙/도구 | 제품 개념이 선명하고 관리 UI/CLI로 확장 쉬움 | memory와 중복되고 규칙이 여러 곳으로 퍼짐 | 보류 |
| E. gated active reminder | WIP domain·keywords·strength·stale 상태로 session-start 주입 제한 | OpenClaw active memory처럼 토큰 오염을 줄이며 필요한 것만 띄움 | 키워드 품질과 stale metadata 관리 필요 | **Phase 0 일부 채택, Phase 1 확장** |
| F. lifecycle manager | `reminder lint/list/archive/promote` 같은 관리 명령 | 생성·만료·폐기·병합이 기능이 되어 방치 방지 | 새 CLI/테스트/다운스트림 마이그레이션 필요 | Phase 1 후보 |
| G. grouped active reminder | `kv_group`으로 여러 query가 같은 reminder bucket을 공유 | semantic retrieval 없이 bounded recall과 group별 top-N을 구현 | group이 hard filter가 되면 P8 false negative 발생 | **Phase 1.5 채택** |
| H. retrieval memory | semantic/FTS 검색으로 관련 reminder만 검색 | Hermes/LangGraph식 episodic recall로 규모 확장 가능 | 현재 하네스에는 저장소·인덱스 비용이 과함 | Phase 2 후보 |
| I. rule promotion pipeline | 반복 reminder를 rules/decision/incident로 승격 | reminder가 영구 규칙으로 썩지 않고 SSOT로 이동 | 승격 기준과 review 비용 설계 필요 | Phase 1 후보 |

판단: 지금 해야 할 것은 C를 바닥 계약으로 깔고, E의 gated exposure를 최소 구현하는 것이다.
이렇게 해야 즉시 되돌릴 수 있으면서도 F/G/H/I로 확장할 길이 열린다. 즉 최종 목표는
"memory 하위 타입 하나"가 아니라 **project memory 위에 얹히는 active reminder layer**다.
다만 이번 wave에서 독립 기능·검색 저장소·전용 CLI까지 한 번에 넣으면 SSOT drift와
다운스트림 충돌이 커지므로 Phase 0으로 자른다.

2026-05-21 보강: G는 Phase 2 검색 저장소로 넘기면 핵심이 빠진다. reminder가
늘어날 때 "어떤 기억 bucket을 먼저 볼지"가 active reminder의 중심 전략이므로,
`kv_group`을 Phase 1.5로 포함한다. 단, 이 group은 필터가 아니라 routing hint다.

## 무거운 reminder 금지

여러 실패 사례에서 얻은 교훈은 "더 많이 기억시키면 해결된다"가 아니었다.
오히려 무거운 reminder는 P8을 줄이려다 P9를 키운다.

- reminder가 길면 세션 시작 출력이 규칙처럼 읽혀 현재 코드 확인을 건너뛴다.
- reminder가 많으면 중요한 것과 오래된 것이 같은 무게로 보인다.
- reminder가 직접 AC·테스트를 늘리면 과거 맥락이 현재 작업을 오염시킨다.
- reminder 생성·만료·폐기 기준이 없으면 memory가 또 하나의 SSOT drift 장소가 된다.

따라서 reminder는 **작고, 조건부로 노출되고, 반드시 SSOT 확인으로 이어지는 신호**여야 한다.
무거운 내용은 reminder에 넣지 않고 rules/decision/incident로 승격한다.

## 2단계 프로세스

이번 결정의 핵심 프로세스는 두 단계다.

### 1. Light reminder

session-start는 현재 WIP domain, strength, status, valid_until만 보고 짧은 후보를 띄운다.
이 단계의 출력은 "주의할 수 있음"이지 "사실"이나 "검증 결론"이 아니다.

출력 예:

```text
📌 리마인더 (memory):
  🔸 review 기본 skip 정책이 하네스 자체 rules/skills/scripts 변경의 누락을 통과시킬 수 있음
```

### 2. SSOT 확인

reminder가 떠오르면 바로 행동하지 않는다. 관련 owner를 확인한다.

- 행동 규칙이면 `.claude/rules/*.md`
- 절차면 `.claude/skills/**/SKILL.md` 또는 `.agents/skills/**/SKILL.md`
- 실행 판정이면 `.claude/scripts/*.py`
- 이유/결정이면 `docs/decisions/**`
- 사고 재발이면 `docs/incidents/**`
- CPS 관계면 `docs/guides/project_kickoff.md`

SSOT 확인 후에만 AC, 검증 범위, 구현 변경에 반영한다. 즉 reminder는 SSOT 확인의
대체물이 아니라 **SSOT 확인을 트리거하는 앞단 신호**다.

## Phase 1.5 — grouped active reminder

Gemma/GQA/MQA의 KV 공유 비유를 하네스에 그대로 옮기면, Query head는 현재
작업의 관점이고 K/V head는 공유되는 memory bucket이다. 하네스에서는 이를
`kv_group`으로 표현한다.

```text
Query = 현재 WIP domain + problem(P#) + tags + 변경 경로 + workflow phase
Key   = kv_group: <domain>/<candidate_p>/<workflow-or-risk-family>
Value = reminder 1줄 + source + owner + stale 여부
```

예:

```yaml
kv_group: harness/P8/review-commit
```

`kv_group`은 여러 reminder를 같은 회상 조건으로 묶고, session-start가 group별
top-N을 먼저 보여주게 하는 routing hint다. 하지만 이것이 hard filter가 되면
P8("떠올리지 못함")을 직접 깨뜨린다. 따라서 group이 맞지 않아도 기존
`status/domain/strength/valid_until` 기준으로 eligible한 reminder는 fallback
budget 안에서 계속 노출한다.

권장 group key:

```text
<domain>/<candidate_p>/<workflow-or-risk-family>
```

좋은 예:

- `harness/P8/review-commit`
- `harness/P9/stale-memory`
- `harness/P8/session-start`
- `harness/P9/ssot-validation`

피할 것:

- `harness/P8`: 너무 커서 노이즈가 는다.
- `harness/P8/review/commit/precheck/session-start`: 너무 잘게 쪼개져 recall 이점이 없다.
- 파일 경로 기반 group: 경로 변경에 취약해 SSOT drift가 는다.
- 결론형 group: `review-skip-is-dangerous`처럼 사실 판단처럼 굳는다.

## 하네스 레이어별 KV 적용

하네스의 레이어는 모델처럼 균질한 N-layer가 아니라 운영 흐름이다. 따라서
K는 여러 레이어가 공유해도 되지만, V의 의미는 레이어마다 새로 계산해야 한다.

| Layer | 하네스 레이어 | Query | 공유 가능한 K | V |
|---|---|---|---|---|
| L0 | 세션 진입 | 현재 세션, git 상태, WIP 목록 | repo 상태, WIP domain | session-start 출력 |
| L1 | CPS 판단 | 이 작업은 무슨 문제인가 | `P#`, `S#`, domain | 해결 기준, AC 기준 |
| L2 | 문서 그래프 | 관련 SSOT가 있나 | domain, tags, relates-to, path | owner 문서 경로 |
| L3 | WIP/AC | 이번 wave의 완료 기준은 무엇인가 | problem, s, status, AC | 실행·검증 약속 |
| L4 | Memory/Reminder | 무엇을 다시 떠올려야 하나 | `kv_group`, candidate_p, domain, keywords | reminder 1줄, source, owner |
| L5 | Skill/Agent routing | 누가 처리해야 하나 | trigger, risk type, changed path | skill/agent 계약 |
| L6 | Verification gate | 완료 증거가 맞나 | staged files, AC, P/S, secret risk | pass/block/stage |
| L7 | Commit/Downstream | 무엇을 영속화하나 | changed component, version impact | commit log, MIGRATIONS |
| L8 | Eval/Promotion | 반복 패턴인가 | incidents, audit, stale signals | promote/archive/lint 후보 |

공유 가능한 것은 structural/routing K다.

- structural KV: `domain`, `P#`, `S#`, `tags`, owner path
- routing KV: `kv_group`, workflow, risk-family
- evidence KV: tests 결과, pre-check 결과, review 결과, 실측

evidence KV는 reminder cache와 공유하지 않는다. reminder가 뜬 것은 "SSOT를
확인하라"는 후보 신호이지 "테스트를 반드시 늘려라"는 검증 결론이 아니다.

## 다른 시스템의 해법과 적용점

| 시스템 | 해결 방식 | 우리가 가져올 장점 | 그대로 쓰지 않는 이유 |
|--------|-----------|-------------------|------------------------|
| OpenClaw active memory | persistent session에서만 bounded recall 수행 | 항상 전체 주입하지 않고 WIP/domain gate로 제한 | 하네스는 agent runtime이 아니라 repo template이라 복잡한 online recall은 과함 |
| OpenClaw dreaming | short-term signal을 score/frequency/diversity gate로 long-term 후보화 | Phase 1에서 stale/report/promote 후보 산출에 적용 가능 | 지금은 score 저장소와 배치 루프가 없음 |
| Hermes persistent memory | `MEMORY.md` 같은 작은 snapshot과 episodic 검색 분리 | 작은 session-start 출력과 나중의 검색 기반 회상을 분리 | Chroma/FTS 의존성은 starter 기본값으로 무거움 |
| Letta/MemGPT | core memory와 archival memory 분리 | reminder는 core가 아니라 core에 올릴 후보로 제한 | memory block을 항상 주입하면 토큰/오염 비용이 커짐 |
| LangGraph/Deep Agents | duration/type/scope/update/retrieval/permission 축 분리 | schema에 status/source/owner/valid_until을 둬 관리 축을 분리 | full memory store abstraction은 현 단계 과설계 |

## 적용 장점과 단점

장점:

- SSOT 확인 누락을 줄인다. reminder가 "이거 확인해"라는 트리거가 된다.
- memory 오염을 줄인다. reminder는 사실이 아니라 후보로 제한된다.
- 토큰 비용을 줄인다. active/domain/strong 조건으로 노출을 줄인다.
- 다운스트림 안정성이 높다. Phase 0은 파일명·frontmatter·session-start 출력만 바꿔 되돌리기 쉽다.
- 다음 확장이 열린다. Phase 1 lint/report/promote, Phase 2 retrieval, Phase 3 promotion pipeline으로 갈 수 있다.

단점:

- metadata 관리 비용이 생긴다. `status`, `valid_until`, `source`가 오래되면 또 stale해진다.
- weak reminder가 많으면 여전히 노이즈가 된다. 노출 예산과 archive 기준이 필요하다.
- legacy `signal_*` 호환 때문에 한동안 이름이 두 개 존재한다.
- SSOT 확인을 자동으로 강제하지 않으면 reminder를 보고도 사람이 건너뛸 수 있다.
- retrieval이나 promotion pipeline을 성급히 넣으면 하네스 starter가 무거워진다.
- `kv_group` 분류가 수동 taxonomy로 굳으면 새 SSOT drift 축이 된다.
- group hit를 근거처럼 읽으면 "이 reminder가 현재 작업에 맞다"는 결론이 캐시된다.
- query group 파생 규칙이 좁으면 P8 false negative, 넓으면 weak reminder 노이즈가 늘어난다.

따라서 구현 원칙은 "가볍게 띄우고, 반드시 확인하게 하고, 오래되면 숨기고,
관련 작업이 있으면 흡수하고, 독립 판단 단위가 되면 SSOT로 승격"이다.

**Acceptance Criteria**:
- [x] Goal: S8·S9 기준으로 reminder를 project memory의 1급 하위 타입으로 정의하고 review 기본 skip 재검토 항목을 reminder로 등록한다.
  검증:
    review: skip
    tests: `python .claude/scripts/session-start.py`
    실측: `python .claude/scripts/session-start.py`가 active reminder와 legacy `signal_*.md`를 읽고, memory 규칙과 MEMORY 인덱스가 reminder 용어를 노출한다.
- [x] Goal: S8·S9 기준으로 Phase 1.5 grouped active reminder를 계약과 실행부에 포함한다.
  검증:
    review: self
    tests: `python -m pytest .claude/scripts/tests/test_session_start.py -q`
    실측: `kv_group` hit reminder가 먼저 정렬되고, group mismatch fallback reminder는 숨지 않으며, stale 표시가 유지된다.
- [x] Goal: reminder frontmatter 보강 책임을 일괄 마이그레이션이 아니라 eval --harness memory/reminder lint로 둔다.
  검증:
    review: self
    tests: `python -m pytest .claude/scripts/tests/test_eval_harness.py -q`
    실측: eval --harness가 신규/strong/stale/legacy 보강 순서, `kv_group` 누락·오타·과대/과소 group, stale 후보를 warning/report로 출력하고 pre-check hard block은 하지 않는다.
- [x] Goal: starter 본체의 legacy `signal_*.md` 7건을 `reminders/reminder_*.md`로 승격하고 MEMORY index와 방어 기록 참조를 갱신한다.
  검증:
    review: self
    tests: `python -m pytest .claude/scripts/tests/test_eval_harness.py .claude/scripts/tests/test_session_start.py -q`
    실측: `python .claude/scripts/eval_harness.py`의 memory/reminder frontmatter lint가 legacy/frontmatter 누락 없이 실행되고, strong+user 항목은 관련 WIP 흡수/승격 후보로 별도 보고한다. `python .claude/scripts/session-start.py`가 reminder 섹션을 정상 출력하며, `bash -n .claude/scripts/bash-guard.sh`가 통과한다.
- [x] Goal: reminder가 backlog처럼 쌓이지 않도록 관련 WIP 흡수를 WIP 승격보다 우선하는 lifecycle 계약을 추가한다.
  검증:
    review: self
    tests: `python -m pytest .claude/scripts/tests/test_eval_harness.py -q`
    실측: `eval --harness` memory/reminder lint가 무거운/강한/과밀 reminder를 "관련 WIP 흡수/승격 후보"로 보고하고, 대응 문구가 "관련 WIP가 있으면 흡수"를 먼저 안내한다.
- [x] Goal: active reminder의 위치를 `docs/`가 아니라 `.claude/memory/reminders/`로 고정하고 루트 fallback으로 downstream 호환을 유지한다.
  검증:
    review: self
    tests: `python -m pytest .claude/scripts/tests/test_session_start.py .claude/scripts/tests/test_eval_harness.py -q`
    실측: starter 본체 `reminder_*.md`는 `.claude/memory/reminders/`로 이동했고, `session-start.py`와 `eval_harness.py`는 새 폴더를 우선 읽으면서 루트 `reminder_*.md`/`signal_*.md`도 legacy fallback으로 읽는다.
- [x] `rules/memory.md`가 reminder를 독립 기능이 아닌 project memory 하위 1급 타입으로 설명한다. ✅
- [x] schema에 `status`·`source`·`owner`·`last_validated`·`valid_until` 관리 필드를 반영한다.
- [x] schema에 `kv_group` optional field를 추가하되 기존 reminder/signal에는 일괄 강제하지 않는다.
- [x] lifecycle 생성·승격·만료·폐기·병합·억제 규칙을 SSOT에 둔다.
- [x] 리서치 입력을 반영해 immediate fix, active reminder layer, lifecycle manager, retrieval memory, promotion pipeline 선택지를 구분한다.
- [x] 무거운 reminder 금지 원칙과 light reminder -> SSOT 확인 2단계 프로세스를 문서화한다.
- [x] 하네스 레이어별 KV 전달 계약을 structural/routing/evidence KV로 나누고 evidence KV 공유 금지를 명시한다.
- [x] `session-start.py`가 `reminder:`와 legacy `signal:`을 모두 지원하고 `status`/`valid_until`을 노출 판단에 반영한다. ✅
- [x] `session-start.py`가 WIP domain·problem·tags·변경 경로에서 query group을 파생하고 `kv_group` hit를 boost/rank/cap hint로 사용한다. ✅
- [x] review 기본 skip 재검토 항목이 `reminder_review_default_skip_risk.md`로 등록된다. ✅
- [x] Phase 1.5 grouped active reminder 전략을 계약에 포함하고 `kv_group`을 optional routing hint로 구현한다.
- [x] S8·S9 기준으로 `kv_group`이 hard filter가 아니며 stale 표시를 덮어쓰지 않음을 회귀 테스트로 고정한다.

## 결정 사항

- reminder는 독립 기능으로 승격하지 않고 project memory의 1급 하위 타입으로 둔다. 단, 이는 최종 축소안이 아니라 active reminder layer의 Phase 0이다.
- active reminder의 신규 위치는 `.claude/memory/reminders/reminder_*.md`로 고정한다. `docs/`는 SSOT 자리이므로 routing signal인 reminder를 두지 않는다.
- 루트 `reminder_*.md`와 `signal_*.md`는 legacy alias로 읽되 신규 생성하지 않는다.
- `kv_group`은 Phase 1.5 grouped active reminder의 optional field로 둔다. group은 boost/rank/cap hint이며, non-matching eligible reminder를 숨기는 hard filter가 아니다.
- reminder가 관련 작업 중에 떠오르면 새 backlog/WIP를 먼저 만들지 않는다. 현재 WIP의 domain/problem/kv_group과 맞으면 AC, `## 메모`, `## 결정 사항`에 흡수하고, 관련 WIP가 없을 때만 새 WIP 승격 후보로 둔다.
- starter 본체의 기존 `signal_*.md` 7건은 2026-05-21 cleanup에서 `reminders/reminder_*.md`로 승격했다. 루트 `reminder_*.md`/`signal_*.md` 읽기는 downstream 호환용 legacy alias로 유지한다.
- CPS 갱신: 없음. 기존 S8 reminder 상태화와 S9 stale memory 제한을 memory 계약으로 보강한다.

## 단계화 로드맵

| Phase | 목표 | 포함 | 제외 |
|-------|------|------|------|
| 0 | 이름·schema·노출 계약 확정 | `reminder_*`, legacy alias, `status`, `valid_until`, WIP domain gate | 전체 rename, 전용 CLI |
| 1 | 관리 기능화 | schema lint, stale 보고, archive/promote 후보 출력, eval/pre-check 경고 | semantic retrieval |
| 1.5 | grouped active reminder | `kv_group`, query group 파생, group hit 우선 정렬, fallback budget | hard filter, 검증 결론 캐시 |
| 2 | 검색 기반 회상 | keywords/FTS/semantic recall, WIP·파일 경로 기반 reminder 선택 | 항상 전체 주입 |
| 3 | 승격 pipeline | 반복 reminder를 rules/decision/incident로 이동하는 기준과 도구 | reminder를 영구 규칙 저장소로 방치 |

## 계약

### 파일과 SSOT

- SSOT: `.claude/rules/memory.md`
- 실행부: `.claude/scripts/session-start.py`
- 인덱스: `.claude/memory/MEMORY.md`
- 신규 타입: `.claude/memory/reminders/reminder_*.md`
- legacy alias: `.claude/memory/reminder_*.md`, `.claude/memory/signal_*.md`

### 필수/권장 필드

```yaml
---
reminder: <1줄 요약>
domain: harness
keywords: [review, commit]
strength: weak | medium | strong
candidate_p: P#
kv_group: <domain>/<candidate_p>/<workflow-or-risk-family>
status: completed
source: docs/decisions/... | docs/incidents/... | user | audit
owner: human | codex | harness
last_validated: YYYY-MM-DD
valid_until: YYYY-MM-DD
---
```

`last_validated`와 `valid_until`은 기존 항목에 일괄 강제하지 않는다. 강제하면 legacy
마이그레이션 비용이 커지므로, 신규 reminder와 strong reminder부터 우선 적용한다.
`kv_group`도 기존 항목에 일괄 강제하지 않는다. 없는 항목은 기존 domain/status
기준 fallback reminder로 남는다.

### frontmatter 보강 운영

기본 운영은 기존 reminder/signal 전체 frontmatter를 일괄 강제하지 않는다.
`kv_group`, `status`, `valid_until`, `last_validated`는 다음 순서로 보강한다.

1. 신규 `reminders/reminder_*.md`
2. `strength: strong` 또는 자주 노출되는 active reminder
3. stale 후보로 반복 보고되는 reminder/signal
4. legacy `signal_*.md` 전체 rename/status 보강

starter 본체에서는 2026-05-21 memory cleanup으로 4번까지 완료했다. 이 원칙은
downstream과 향후 신규 legacy 항목에 대한 운영 순서로 남긴다.

누락·오타·과대 group·과소 group·stale 후보 보고는 `eval --harness`의 memory/reminder
lint가 담당한다. pre-check hard block은 아직 도입하지 않는다. 먼저 eval에서
추천/경고로 운용하고, 오탐이 낮아진 뒤 warning 또는 block 승격을 검토한다.

### lifecycle

| 단계 | 처리 |
|------|------|
| 생성 | 반복 위험·후속 판단 후보를 `reminders/reminder_*.md`, `status: active`로 남김 |
| 승격 | 반복 발생·incident 연결·강한 노출 필요 시 `strength`와 `source` 보강 |
| 만료 | `valid_until` 경과 시 stale 후보로 표시하고 사실 증거로 사용 금지 |
| 폐기 | 현재 코드/문서와 불일치하면 `status: archived` |
| 병합 | 같은 회상 조건이 중복되면 넓은 reminder 하나로 합치고 나머지 archived |
| 억제 | 맞지만 현재 작업에 노이즈면 `status: suppressed` 또는 keywords 축소 |

### 관련 WIP 흡수 / 승격

reminder는 backlog 저장소가 아니라 작업 중 개입하는 routing signal이다. 따라서
무거워진 reminder의 기본 처리는 새 WIP 생성이 아니라 관련 WIP 흡수다.

흡수 우선 조건:

- 현재 WIP의 `domain`, `problem`, `tags`, `kv_group`과 reminder가 맞다.
- reminder가 현재 AC, 검증 범위, 의사결정, 회고 중 하나에 직접 영향을 준다.
- 독립된 설계/구현/검증 단위라기보다 현재 작업의 누락 방지 신호다.

처리 순서:

1. 관련 WIP의 AC, `## 메모`, `## 결정 사항` 중 맞는 위치에 reminder 경로와
   재확인 결과를 기록한다.
2. 관련 WIP가 없거나 독립 판단 단위이면 `/implementation` 또는 `/write-doc`로
   새 WIP를 만든다.
3. 완료 후 owner SSOT가 생기면 reminder `source`를 갱신하고, 장문 reminder는
   pointer로 축소하거나 `status: archived`로 둔다.

### 노출 규칙

- 기본 노출은 `status: active`이고 현재 WIP `domain`과 일치하는 reminder.
- `strength: strong`은 domain 불일치여도 최대 2건까지 보조 노출 가능.
- `suppressed`와 `archived`는 session-start 기본 노출에서 제외한다.
- `valid_until`이 지난 항목은 stale 후보로 표시하고, 현재 코드/문서 재확인 전까지
  검증 범위 확대 근거로 쓰지 않는다.
- `kv_group`이 현재 WIP query와 일치하면 먼저 정렬한다. 다만 group 불일치가
  eligibility 탈락 사유가 되어서는 안 된다.
- count만 출력하지 않는다. reminder는 항상 본문 요약 또는 stale 상태와 함께 노출한다.

### query group 계산

session-start는 현재 WIP에서 다음 structural key를 수집한다.

- `domain`
- `problem`의 `P#`
- WIP `tags`
- WIP 파일명 slug token
- staged/unstaged 변경 경로 token

그 뒤 보수적인 workflow/risk-family token과 교차해 query group 후보를 만든다.
현재 최소 구현의 family는 `review-commit`, `stale-memory`, `session-start`,
`ssot-validation`이다. 이는 taxonomy SSOT가 아니라 starter 기본 routing set이며,
확장 시 `.claude/rules/memory.md`를 먼저 갱신한다.

정렬 순서:

1. `kv_group` hit
2. stale 아님
3. `strength`
4. group 이름과 출력 line

노출 후보가 많을 때만 group별 cap을 적용한다. cap은 토큰 예산 장치이지
eligibility 판정이 아니다.

### CPS 관계

reminder는 주로 P8과 P9의 방어 장치다. P8은 "떠올리지 못함"이고, P9는
"오래된 memory를 사실처럼 씀"이다. 따라서 reminder는 검증 결론이 아니라
`환기 -> 재확인 -> 검증 선택`의 첫 단계로만 사용한다.

## 구현 반영

- `.claude/rules/memory.md`: reminder를 project memory 하위 1급 타입으로 정의하고
  schema/lifecycle/session-start 노출 계약을 추가했다.
- `.claude/scripts/session-start.py`: `reminder:`와 legacy `signal:`을 모두 읽고,
  `status`, `valid_until`, legacy `archived: true`, optional `kv_group`을 처리한다.
  `.claude/memory/reminders/`를 우선 읽고 루트 `.claude/memory/reminder_*.md`와
  `signal_*.md`는 downstream fallback으로 읽는다.
- `.claude/memory/MEMORY.md`: 반복 패턴 회상 섹션을 reminder 중심으로 바꾸고
  기존 signal 링크를 reminder 링크로 갱신했다.
- `.claude/memory/reminders/reminder_ac_skip_on_commit.md` 등 7개: legacy `signal_*.md`를
  `reminders/reminder_*.md`로 승격하고 `status/source/owner/last_validated/kv_group`을 보강했다.
- `.claude/memory/reminders/reminder_review_default_skip_risk.md`: review 기본 skip 재검토 항목을
  신규 reminder 형식으로 등록하고 `kv_group: harness/P8/review-commit`을 부여했다.
- `.claude/memory/project_eval_last.md`: 방어 활성 기록 파일명을
  `reminders/reminder_defense_success.md`로 갱신했다.
- `.claude/scripts/tests/test_session_start.py`: `kv_group`이 hard filter가 아니며
  stale 표시를 덮어쓰지 않는 회귀 테스트를 추가했다.
- `.claude/scripts/eval_harness.py`: memory/reminder frontmatter lint를 추가해
  `kv_group` 누락·형식 오류·과대/과소 group·candidate 불일치·stale 후보·legacy
  signal·status 누락을 warning/report로 출력하고, 방어 활성 기록 참조를
  `reminders/reminder_defense_success.md`로 갱신했다. 무거운/강한/과밀 reminder는
  관련 WIP 흡수 또는 WIP 승격 후보로 별도 보고한다.
- `.claude/scripts/bash-guard.sh`: 새 차단 성공 기록을 `reminders/reminder_defense_success.md`
  형식으로 append하게 갱신했다.
- `.claude/skills/eval/SKILL.md`: `/eval --harness` 항목 6의 방어 활성 기록 파일명을
  `reminders/reminder_defense_success.md`로 갱신했다.
- `.claude/scripts/tests/test_eval_harness.py`: reminder lint와 WIP `c:` 감지 회귀
  테스트를 추가했다.

## 미해결 / 다음 wave

- downstream에 남아 있을 수 있는 legacy `signal_*.md`는 계속 alias로 읽는다. starter
  본체에는 남기지 않았다.
- pre-check schema lint는 아직 추가하지 않았다. 이번 wave는 eval --harness
  warning/report까지로 제한하고, hard block은 별도 wave에서 검토한다.
- `kv_group` taxonomy list/archive/promote CLI는 아직 없다. group명 오타와 과대/과소
  분할은 eval report로 먼저 관측하고, Phase 1 lifecycle manager에서 관리 명령으로
  확장한다.
- query family 확장은 아직 코드 상수다. 반복 사례가 쌓이면 memory.md에 family 목록을
  먼저 추가하고 실행부를 맞춘다.
- review 기본 skip 정책 자체는 바꾸지 않았다. 이번 reminder는 다음 관련 wave에서 정책을
  재검토하라는 상태 파일이다.
- 관련 WIP 자동 매칭/흡수는 아직 보고 계약만 있다. 실제 흡수 위치 선택은 현재
  implementation/write-doc 흐름에서 사람이 AC·메모·결정 사항 중 선택한다.

## 검증

- `python -m py_compile .claude/scripts/session-start.py`
- `python -m pytest .claude/scripts/tests/test_eval_harness.py .claude/scripts/tests/test_session_start.py -q`
- `bash -n .claude/scripts/bash-guard.sh`
- `python .claude/scripts/session-start.py`
- `python .claude/scripts/eval_harness.py`

실측 결과: `python -m pytest .claude/scripts/tests/test_eval_harness.py .claude/scripts/tests/test_session_start.py -q`는
41개 테스트를 통과했다. `📌 리마인더 (memory):` 섹션에 신규
`review 기본 skip 정책...` reminder와 승격된 `reminders/reminder_*.md` 항목이 함께 노출됐다.
추가 회귀 테스트에서 `kv_group` hit reminder가 먼저 정렬되면서 fallback reminder는
숨지 않았고, stale reminder에는 재확인 필요 표시가 유지됐다. 루트 `reminder_*.md`도
downstream fallback으로 계속 읽는 테스트를 추가했다.
`eval_harness.py`는 memory/reminder frontmatter lint를 출력했고, 현재 repo에서는
pre-check hard block 없이 `reminder_commit_skill_bypass.md`를 관련 WIP 흡수/승격 후보로
warning/report했다.
