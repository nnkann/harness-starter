---
title: Typed AC contract
domain: harness
c: "AC가 CPS 기반으로 만들어져도 단계별 기준과 개별 기준의 역할 분류, P#/S# 연결이 드러나지 않는다."
problem: [P6, P7, P9]
s: [S6, S7, S9]
tags: [ac, cps, traceability]
relates-to:
  - path: .claude/rules/docs.md
    rel: references
status: completed
created: 2026-06-02
updated: 2026-06-02
---

# Typed AC contract

## CPS Rationale

- C -> P: AC의 역할이 섞이면 P6 검증 책임이 흐려지고, P7 소유·출력 계약과 P9 번호 기반 검증이 약해진다.
- P -> S: S6은 검증 증거의 위치를 고정하고, S7/S9는 P#/S# 번호를 통한 추적성을 요구한다.
- S -> AC: typed AC가 Problem/Solution/Step/Behavior/Guardrail/Verification 기준을 분리하고 각 항목이 P#/S#를 직접 인용한다.

## 구현 계획

1. `.claude/rules/docs.md` AC 포맷에 typed AC 분류와 개별 P#/S# 추적성 규칙을 추가한다.
2. `pre_commit_check.py`가 staged WIP의 typed AC 존재와 개별 P#/S# 인용을 검사한다.
3. implementation 스킬 mirror가 새 AC 작성 기준을 사용하도록 동기화한다.
4. 좁은 gate 테스트와 pre-check로 검증한다.

**Acceptance Criteria**:
- [x] Goal: P6/S6, P7/S7, P9/S9 기준으로 AC가 대표 Goal과 typed 개별 AC로 분리된다.
  검증:
    review: self
    tests: `python3 -m pytest .claude/scripts/tests/test_pre_commit.py -q -k "ACTypedTraceability or ACSolutionRef or ACCheckbox"`
    실측: `python3 .claude/scripts/pre_commit_check.py`
- [x] Problem AC (P6): AC 항목이 검증 책임 우회와 거짓 완료를 줄이는 기준인지 분리되어 보인다.
- [x] Solution AC (S6/S7/S9): frontmatter의 각 S#가 AC 섹션에 직접 인용되고 substring 박제 없이 번호로만 연결된다.
- [x] Step AC (S7): implementation 스킬의 WIP 작성 절차가 typed AC 작성 기준을 참조한다.
- [x] Behavior AC (P7/S7): 문서 작성자가 개별 AC만 읽어도 어떤 계약과 출력 책임을 닫는지 알 수 있다.
- [x] Guardrail AC (P9/S9): typed AC 항목은 P# 또는 S# 인용 없이는 pre-check에서 차단된다.
- [x] Verification AC (S6): typed AC gate 테스트와 pre-check가 통과한다.

## 결정 사항

- `.claude/rules/docs.md` AC 포맷을 대표 Goal + typed AC 6종으로 확장했다.
- `pre_commit_check.py`가 staged WIP의 typed AC 존재, `Problem AC`, 개별 P#/S# 인용, frontmatter P#/S# AC 섹션 인용을 검사한다.
- `.agents/skills/implementation`과 `.claude/skills/implementation` WIP 생성 기준에 typed AC 작성 규칙을 추가했다.
- `.claude/rules/naming.md`의 AC 메타데이터 SSOT 참조명을 새 포맷에 맞췄다.
- 기존 open WIP `decisions--hn_cps_agent_learning.md`의 AC 라벨을 typed AC 형식으로 보강했다.
- CPS 갱신: 없음. 기존 P6/P7/P9와 S6/S7/S9 해결 기준을 AC 포맷에 연결했다.

## 메모

- 기존 SSOT는 S# 섹션 인용만 강제했다. 이번 변경은 개별 AC 단위의 역할과 P#/S# 연결을 추가한다.
- 검증: `python3 -m py_compile .claude/scripts/pre_commit_check.py` 통과.
- 검증: `python3 -m pytest .claude/scripts/tests/test_pre_commit.py -q -k "ACTypedTraceability or ACSolutionRef or ACCheckbox"` → 15 passed.
- 검증: `TEST_MODE=1 _TEST_NAME_STATUS='A\tdocs/WIP/decisions--hn_typed_ac_contract.md' python3 .claude/scripts/pre_commit_check.py` → pass.
- 검증: `python .claude/scripts/safe_command.py verify-relates` → 미연결 0건.
- 검증: `python .claude/scripts/safe_command.py precheck` → pass. 단 staged 파일 없음 상태의 전체 pre-check다.
