---
title: Honcho workspace 기반 cross-session continuity
status: proposed
created: 2026-07-18
updated: 2026-07-18
tags: [honcho, cps, continuity, session, handoff]
relates-to:
  - path: decisions/hn_harness_runtime_externalization.md
    rel: references
---

# Honcho workspace 기반 cross-session continuity

## 결정

Honcho의 shared workspace를 named profile 간의 **검색 가능한 continuity layer**로 사용한다. Hermes core, live gateway, profile config, Kanban, 새 task store는 변경하지 않는다.

Honcho는 실행 authority나 raw session 복제 수단이 아니다. 각 profile의 raw session summary는 분리되어 있으며, 필요한 과거 문맥은 explicit semantic retrieval로만 회복한다.

## 실제 전제

현재 named profile은 공용 `/Users/kann/.hermes/honcho.json`의 `workspace: hermes`를 사용한다. AI peer는 profile별로 분리되어 있다.

```text
Maat   → peer=maat
Ptah   → peer=ptah
Anubis → peer=anubis
```

`recallMode: tools`이므로 다른 session의 문맥은 자동 주입되지 않는다. 필요한 경우 `honcho_search`로 target peer를 명시해 검색한다.

```text
honcho_search(query=<message_id 또는 continuity anchor>, peer="maat")
```

## Continuity identity

새 ID registry나 임의의 `task_id`를 만들지 않는다. Discord에서 이미 제공하는 immutable identity를 그대로 쓴다.

```text
thread_id: 작업이 속한 Discord thread ID
message_id: 이 work unit을 시작한 최초 사용자 지시 message ID
```

`message_id`가 exact lookup과 pivot의 기본 key다. `thread_id`는 같은 대화 안에서의 위치를 찾는 locator다. 동일 thread의 후속 지시가 기존 work unit의 범위를 바꾸면 같은 `message_id`를 유지한다. 독립 work unit이면 그 지시의 message ID를 새 `message_id`로 사용한다.

profile-local Hermes session ID는 보조 관측값일 뿐, cross-profile continuity key가 아니다.

## Honcho에 남기는 handoff note

Honcho note의 목적은 줄이는 것이 아니라, **다음 holder가 무엇을 반드시 달성·구현·검증해야 하는지 추정 없이 정확히 전달하는 것**이다.

따라서 note에는 full task를 복제하지 않되, 다음 holder의 결과를 바꿀 active obligation은 빠뜨리지 않는다. Goal/AC를 기계적으로 전부 복사하지 않는다는 뜻이지, 필요한 Goal/AC clause를 생략한다는 뜻이 아니다.

### Required handoff note

다음 holder가 바뀌거나 새 session에서 재개해야 할 때, 아래 필드를 하나의 compact but complete note로 남긴다.

| 필드 | 반드시 적어야 하는 내용 |
|---|---|
| `message_id`, `thread_id` | exact lookup/pivot과 원본 대화 복귀 기준 |
| `current owner` / `next holder` / `phase` | 누가 어떤 단계에서 이어받는지 |
| `required outcomes` | 다음 holder가 반드시 구현·달성·판정해야 하는 결과 |
| `active acceptance constraints` | 아직 충족되지 않았거나, 다음 holder가 직접 확인해야 하는 AC clause. 필요한 경우 정확한 원문 또는 immutable source section reference를 사용 |
| `hard boundaries` / `hold conditions` | 하면 안 되는 변경, 중단해야 하는 조건, 확정되지 않은 가정 |
| `authority references` | 현재 실행 authority인 local body와 원본 Discord/source/evidence의 정확한 위치 |
| `required evidence` | 완료 주장 전에 어떤 receipt, readback, test, comparison이 필요한지 |
| `decision needed` | holder가 구현이 아니라 판단·escalation을 해야 하는 경우 그 질문 |

`stdout/stderr`, full prompt, raw receipt, diff, live state처럼 다음 holder의 판단을 바꾸지 않는 원문은 note에 복사하지 않는다. 그런 원문이 필요하면 `authority references`로 원본을 가리킨다.

Goal/AC의 처리 기준은 다음과 같다.

```text
다음 holder의 산출물·검증·중단 조건을 바꾸는 clause
→ handoff note에 정확히 포함

현재 holder에게만 필요한 배경, 이미 충족되어 다음 단계에 영향이 없는 clause,
원본을 보지 않아도 되는 장문 설명
→ note에 복사하지 않고 authority reference만 유지
```

## Retrieval과 authority

Honcho search result는 continuity candidate다. 실행·검증 권위는 아니다.

```text
1. exact message_id로 Maat peer를 우선 검색한다.
2. thread_id와 source/evidence reference를 원본에서 확인한다.
3. 현재 local body와 범위가 일치하면 작업을 재개한다.
4. local body가 없거나 search result가 모호하면 need_local_body 또는 hold한다.
```

semantic search의 유사 결과는 다른 과거 work unit을 포함할 수 있다. `message_id` 또는 원본 reference가 일치하지 않으면 현재 작업 근거로 승격하지 않는다.

## Role boundary

| 역할 | Honcho workspace에서 하는 일 | 하지 않는 일 |
|---|---|---|
| Maat | required handoff note를 남기고, 검색 결과와 원본 evidence를 대조 | memory만으로 accept/hold 확정 |
| Ptah | `message_id`로 필요한 context를 회복 | memory로 누락된 local body를 추정해 구현 |
| Anubis | required outcomes/AC candidate를 회복하고 receipt/evidence와 대조 | 모델 서술이나 memory만으로 검증 통과 |
| SIA | closed work unit에서 장기 promotion 후보의 continuity/conflict scan | raw task log를 장기 메모리에 복사 |

## 새 세션 재개 절차

새 session의 첫 입력에는 existing Discord identity와 local body의 위치를 포함한다.

```text
thread_id: <existing Discord thread ID>
message_id: <work unit을 시작한 existing Discord message ID>
local_body_ref: <현재 실행 authority의 위치>
```

그 뒤 다음 순서로 진행한다.

```text
message_id exact search
→ thread/source/evidence readback
→ required handoff note와 현재 local body의 obligation 대조
→ 필요한 범위에서만 구현 또는 검증
```

이 절차는 current Discord thread를 바꾸거나, Hermes gateway session을 연결하거나, profile state를 공유하지 않는다.

## 장기 메모리 경계

종료된 task의 raw Honcho note는 단기 continuity 용도다. SIA는 source-backed이고 재사용 가치가 있는 안정된 정책·결정만 장기 promotion 후보로 정리한다.

다음은 장기 메모리에 넣지 않는다.

```text
individual run ID
stdout/stderr
temporary path
one-off failure
raw receipt
task 진행 상황
```

## 비목표

```text
Hermes core 수정
live gateway 수정 또는 재시작
profile config 변경
Kanban 도입
새 task database/schema/daemon
Honcho session 강제 공유
Goal/AC의 일괄 복사
```
