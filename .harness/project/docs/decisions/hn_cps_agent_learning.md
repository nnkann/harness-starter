---
title: CPS agent learning loop 보강
domain: harness
c: "CPS+AC는 작동하지만 subagent 연계, 역방향·재개형 CPS 흐름, downstream cron 학습 반영이 약하다."
problem: [P5, P7, P8, P9]
s: [S5, S7, S8, S9]
tags: [cps, agent, cron, learning]
relates-to:
  - path: decisions/hn_gemini_delegation_pipeline.md
    rel: references
  - path: decisions/hn_hermes_managed_downstream_memory.md
    rel: references
status: completed
created: 2026-06-02
updated: 2026-06-02
---

# CPS agent learning loop 보강

## CPS Rationale

- C -> P: subagent와 cron 관찰이 CPS 판단으로 되돌아오지 않으면 P7 관계 불투명, P8 회상 누락, P9 오래된 신호 오염이 동시에 생긴다.
- P -> S: S5/S7은 agent handoff 계약을 작게 만들고, S8/S9는 cron·reminder를 사실이 아닌 재확인 신호로 제한한다.
- S -> AC: implementation 진입부와 memory/Hermes 계약에 flow type, CPS packet, downstream cron signal 처리 기준을 박아 둔다.

## 구현 계획

1. implementation 스킬에 CPS 흐름 분류와 specialist CPS packet 계약을 추가한다.
2. memory/Hermes 계약에 downstream cron 미반영 신호의 흡수·승격 기준을 추가한다.
3. active `.agents` mirror와 배포용 `.claude` 파일 역할 차이를 맞춘다.
4. codebase-analyst 최소 변경 제안 4개를 AC와 회귀 테스트로 닫는다.

**Acceptance Criteria**:
- [x] Goal: S5/S7/S8/S9 기준으로 subagent·역방향 CPS·downstream cron 학습 신호가 implementation 흐름에서 사라지지 않는다.
  검증:
    review: self
    tests: `python3 .claude/scripts/pre_commit_check.py`
    실측: implementation 스킬에 flow type, CPS packet, specialist 응답 계약, downstream cron signal 흡수 규칙이 존재한다.
- [x] Problem AC (P5/P7/P8/P9): subagent·cron 관찰이 CPS 판단으로 되돌아오지 않는 문제를 implementation 흐름에서 다룬다.
- [x] Solution AC (S5/S7): specialist handoff는 전체 문서 덤프가 아니라 C/P/S/AC/flow/open question packet으로 제한된다.
- [x] Solution AC (S8/S9): S/AC/테스트/cron에서 시작한 역방향 신호는 기존 P# 재확인 또는 P10 후보로 기록된다.
- [x] Behavior AC (S8/S9): downstream cron 미진행·delta report는 memory 사실이 아니라 WIP 흡수 또는 Hermes-managed downstream SSOT 재확인 후보로 처리된다.
- [x] Step AC (S7): active `.agents/skills/implementation`과 배포용 `.claude/skills/implementation`의 핵심 계약이 동기화된다.
- [x] Guardrail AC (S7/P11): Hermes-managed downstream 문서의 cascade boundary 위반 relates-to 3건이 정리되어 `verify-relates`가 통과한다.
- [x] Minimum AC 1: `.claude`/`.agents` implementation mirror drift 중 WIP 파일명·계획 문서 트리거·CPS flow 핵심 계약이 정리된다.
- [x] Minimum AC 2: `trigger:` metadata 스키마와 초기 agent 적용(codebase/debug/review/risk)이 존재한다.
- [x] Minimum AC 3: implementation Step 1에 재개·역방향 점검이 포함된다.
- [x] Minimum AC 4: cron 신규 구현 대신 `eval --harness`·harness-dev·harness-upgrade 운영 루틴에 downstream 학습 신호 확인이 포함된다.
- [x] Cron AC (S8/S9): Hermes daily cron이 registry의 harness-downstream을 순회하고 Feedback Reports를 수용 후보·반려·owner-action으로 분류한다.

## 결정 사항

- implementation Step 1에 `forward`, `reverse-solution`, `reverse-evidence`, `resume`, `interrupt` flow를 추가했다.
- specialist handoff를 CPS packet 기반으로 좁히고, 응답에 `CPS 영향`을 요구하도록 했다.
- `.claude/rules/docs.md`에 `trigger:` metadata 스키마를 추가하고, codebase/debug/review/risk 에이전트에 우선 적용했다.
- `.claude/rules/memory.md`와 `/eval --harness`에 downstream cron 학습 신호 처리 기준을 추가했다.
- `.agents` mirror drift 중 implementation/eval 핵심 계약을 `.claude`와 맞췄다.
- harness-dev/harness-upgrade 체크리스트에 downstream 보고·cron delta를 `/eval --harness` 관점으로 구분하고, report 부재는 "cron 미진행 신호"로 흡수하도록 추가했다.
- Hermes cron `cc8c81b8e83f`를 `harness-downstream-learning-check`로 전환했다. 매일 04:00 KST에 `harness_downstream_learning_check.py`가 registry의 harness-downstream을 순회하고 수용 후보·반려·owner-action을 분류한다.
- CPS 갱신: 없음. 기존 S5/S7/S8/S9 계약을 활성 절차와 metadata에 연결했다.

## 메모

- 사전 탐색: `hn_gemini_delegation_pipeline`, `hn_bit_cascade_objectification`, `hn_hermes_managed_downstream_memory`, `hn_reminder_memory_contract`가 기존 SSOT 후보다. 새 자동화보다 기존 계약을 implementation 진입부에 연결하는 것이 우선이다.
- codebase-analyst 결과: `.claude`/`.agents` implementation drift, `trigger:` metadata 미구현, 역방향/재개 흐름 부재, cron 구현 부재를 확인. 최소 변경으로 mirror drift 정리, `trigger:` 시범 적용, implementation Step 1 보강, cron 대신 eval/Hermes 학습 신호 명문화를 권고했다.
- 검증: `python3 -m pytest .claude/scripts/tests/test_skill_routing_contract.py -q` → 4 passed. `python3 .claude/scripts/docs_ops.py verify-relates` → 미연결 0건. `python3 .claude/scripts/pre_commit_check.py` → pass.
- cron 검증: `~/.hermes/scripts/harness_downstream_learning_check.py --force-report` → 3개 downstream 후보 순회. StageLink 수용 후보 2건, Ai-prompter 반려 1건, Issen owner-action 1건 분류. `hermes cron list` → `0 4 * * *`, next run `2026-06-03T04:00:00+09:00`.
