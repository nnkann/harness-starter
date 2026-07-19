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

Honcho의 shared workspace를 named profile 간의 **검색 가능한 continuity layer**로 사용한다. Hermes core, live gateway, Kanban, 새 task store는 변경하지 않는다.

Honcho는 실행 authority나 raw session 복제 수단이 아니다. 각 profile의 raw session summary는 분리되어 있으며, 필요한 과거 문맥은 explicit semantic retrieval로만 회복한다.

## Runtime configuration boundary

이 프로젝트는 pre-existing shared root `/Users/kann/.hermes/honcho.json`의 다음 contract를 요구한다. 이 파일은 project Git 밖의 runtime prerequisite이며, repository가 생성하거나 수정하는 산출물이 아니다.

| scope | field | required value |
|---|---|---|
| shared root | `peerName` | `kann` |
| shared root | `pinUserPeer` | `true` |
| role host | `workspace` | `hermes` |
| role host | `recallMode` | `tools` |
| role host | `sessionStrategy` | `per-repo` |
| role host | `aiPeer` | role-specific |

profile-local override는 금지한다. named role은 shared root contract를 상속해야 하며, profile-local Honcho config로 user peer, workspace, recall mode, session strategy, AI peer binding을 덮어쓰지 않는다.

Honcho tool 호출의 `peer="user"`는 Honcho tool alias이고, 이 contract에서 resolved physical shared user peer는 `kann`이다. alias 문자열을 물리 peer 이름으로 해석하거나 별도 `user` peer로 만들지 않는다. 이 shared user peer가 프로젝트 per-repo session의 공통 Honcho retrieval substrate이며, role host의 role-specific `aiPeer`는 서로 구분된 채 유지된다.

shared peer/session binding은 startup-read다. `peerName`, `pinUserPeer`, `sessionStrategy` 구성을 변경한 뒤 retrieval 결과를 해석하려면 fresh Hermes session 또는 fresh CLI process가 필요하다. 변경 전 session의 결과는 stale binding evidence이며, candidate absence나 HOLD 조건이 아니다.

```text
Maat   → peer=maat
Ptah   → peer=ptah
Anubis → peer=anubis
```

### Effective continuity guarantee

현재 continuity guarantee는 `/Users/kann/.hermes/honcho.json`에 host로 명시된 configured named profiles와 explicit `/Users/kann/projects/harness-starter` session override에 한정된다. generic plain-fresh-profile inheritance나 strict same-basename multi-repo isolation은 현재 보장하지 않는다.

새 profile 또는 repository는 사용 전에 fresh process에서 effective Honcho config와 resolved session binding을 read back하는 fresh-process config-resolution acceptance를 거쳐야 한다. 기존 named profile이나 explicit override의 결과를 새 대상의 acceptance evidence로 대신하지 않는다.

`recallMode: tools`이므로 다른 session의 문맥은 자동 주입되지 않는다. 각 역할은 먼저 제공된 `local_body_ref`와 `authority references`가 가리키는 원본 source/evidence를 읽는다. 둘만으로 locator와 active obligation이 충분하면 Honcho semantic retrieval을 생략한다. locator/obligation이 빠졌거나 continuity conflict를 해소해야 할 때만 Maat, Ptah, Anubis, SIA가 기존 Honcho tools로 `peer="user"`의 shared user-peer CPS layer에서 candidate를 검색한다. SIA는 retrieval proxy, broker, mandatory call path가 아니다. Maat의 indexed context는 role-specific candidate pivot이며 공통 retrieval substrate를 대체하지 않는다.

```text
# missing locator/obligation 또는 continuity conflict가 있는 경우에만
honcho_search(query=<message_id 또는 continuity anchor>, peer="user")
honcho_search(query=<message_id 또는 continuity anchor>, peer="maat")  # Maat role candidate pivot
```

## Continuity identity

새 ID registry나 임의의 `task_id`를 만들지 않는다. Discord에서 이미 제공하는 immutable identity를 그대로 쓴다.

```text
thread_id: 작업이 속한 Discord thread ID
message_id: 이 work unit을 시작한 최초 사용자 지시 message ID
```

`message_id`가 semantic candidate retrieval의 기본 query anchor다. `thread_id`는 같은 대화 안에서의 위치를 찾는 locator다. candidate를 얻은 뒤 두 identity와 authority reference가 가리키는 원본 source를 exact identity/source readback한다. 동일 thread의 후속 지시가 기존 work unit의 범위를 바꾸면 같은 `message_id`를 유지한다. 독립 work unit이면 그 지시의 message ID를 새 `message_id`로 사용한다.

profile-local Hermes session ID는 보조 관측값일 뿐, cross-profile continuity key가 아니다.

## Honcho에 남기는 handoff note

Honcho note의 목적은 줄이는 것이 아니라, **다음 holder가 무엇을 반드시 달성·구현·검증해야 하는지 추정 없이 정확히 전달하는 것**이다.

따라서 note에는 full task를 복제하지 않되, 다음 holder의 결과를 바꿀 active obligation은 빠뜨리지 않는다. Goal/AC를 기계적으로 전부 복사하지 않는다는 뜻이지, 필요한 Goal/AC clause를 생략한다는 뜻이 아니다.

### Required handoff note

다음 holder가 바뀌거나 새 session에서 재개해야 할 때, 아래 필드를 하나의 compact but complete note로 남긴다.

| 필드 | 반드시 적어야 하는 내용 |
|---|---|
| `message_id`, `thread_id` | semantic candidate retrieval과 exact identity/source readback의 기준 |
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

Honcho search result와 Maat-indexed Honcho context는 continuity를 찾기 위한 pivot/candidate reference다. Maat의 indexed context는 role-specific candidate pivot일 뿐이다. Ptah와 Anubis는 readable `local_body_ref`와 `authority references`가 충분하면 retrieval 없이 source/local authority를 읽는다. 필요한 경우에만 `peer="user"`의 공통 shared CPS layer에서 semantic candidate를 회복하고, exact identity/source readback으로 일치 여부를 확인하며, shared CPS work를 다시 증명하거나 재구성하지 않는다.

`message_id`와 `thread_id`는 work를 식별한다. 사실·범위·실행 권위는 원본 source/evidence와 현재 local body에 있다.

```text
1. local_body_ref와 authority references로 원본 source/evidence와 active obligation을 읽는다.
2. locator와 obligation이 충분하고 continuity conflict가 없으면 Honcho retrieval을 생략한다.
3. 누락이나 conflict가 있을 때만 semantic candidate를 검색하고, Maat role context가 필요하면 peer="maat" candidate를 pivot으로만 사용한다.
4. message_id, thread_id, authority references로 exact identity/source readback한다.
5. 각 holder는 자기 역할에 필요한 범위에서 source/evidence와 local body를 읽고 작업을 재개한다.
```

semantic search의 유사 결과는 다른 과거 work unit을 포함할 수 있다. `message_id` 또는 원본 reference가 일치하지 않으면 현재 작업 근거로 승격하지 않는다.

continuity bootstrap 중 prior Maat handoff note가 없다는 사실만으로 HOLD하지 않는다. local body가 없거나 모호한 경우, Honcho candidate와 source/evidence가 불일치하는 경우, 또는 authority가 충돌하는 경우에는 `need_local_body` 또는 HOLD를 유지한다.

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
readable local_body_ref + authority references 확인
→ 충분하면 retrieval 생략
→ locator/obligation 누락 또는 continuity conflict가 있으면 semantic candidate retrieval
→ exact identity/source readback
→ required handoff note와 현재 local body의 obligation 대조
→ 필요한 범위에서만 구현 또는 검증
```

이 절차는 current Discord thread를 바꾸거나, Hermes gateway session을 연결하거나, profile state를 공유하지 않는다.

## 장기 메모리 경계

종료된 task의 raw Honcho note는 단기 continuity 용도다. SIA의 exclusive role은 closure 이후 source-backed durable promotion/conflict scanning이며, 재사용 가치가 있는 안정된 정책·결정만 장기 promotion 후보로 정리한다.

### Durable promotion route boundary

SIA-only durable promotion은 named-profile selection과 source/evidence review로 enforce하는 route/role-contract boundary이며, per-tool Honcho ACL이 아니다. `honcho_conclude`는 existing general plugin capability로 남아 있으므로 비-SIA caller의 호출을 technical prevention한다고 주장하지 않는다.

이 경계를 bypass한 write는 out-of-contract incident다. 해당 candidate는 승격 근거로 사용하지 않고 HOLD한 뒤 Maat escalation으로 source, caller role, evidence를 재검토한다.

### SIA promotion용 compact CPS index

SIA promotion만을 위한 source-backed compact CPS index record는 아래 semantic candidate content만 담는다.

| 필드 | 내용 |
|---|---|
| `C/P/S` | promotion 후보가 보존하는 CPS 의미 |
| `message_id`, `thread_id` | 원본 work와 대화의 immutable locator |
| `current owner` / `next holder` / `phase` | 현재 책임과 전환 상태 |
| `required outcomes` | 남아 있는 필수 결과 |
| `active acceptance constraints` | 아직 유효한 acceptance criteria |
| `hard boundaries` / `hold conditions` | 금지 범위와 fail-closed 조건 |
| `authority references` | 원본 source/evidence 위치 |
| `required evidence` | promotion 또는 다음 판정에 필요한 증거 |
| `decision needed` | 남아 있는 판단 또는 escalation 질문 |
| `local_body_ref` | 현재 local execution authority 위치 |

이 index는 source로 되돌아가기 위한 semantic candidate content다. 실행 authority도 task registry도 아니다. 새 registry, adapter, schema를 만들거나 task 진행 상태를 소유하지 않는다.

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
shared root runtime config의 project Git 내 생성·수정 또는 profile-local override 추가
Kanban 도입
새 task database/schema/daemon
Honcho session 강제 공유
Goal/AC의 일괄 복사
```
