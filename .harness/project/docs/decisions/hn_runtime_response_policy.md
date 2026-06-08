---
title: Codex/Agy runtime response policy 설계
domain: harness
c: "Hermes가 Codex와 Agy를 기본 조합으로 쓰지만, agent 선택 뒤 적합성 판단과 결과 예측을 남기는 정책이 약하다."
problem: [P3, P5, P7, P8, P9]
s: [S3, S5, S7, S8, S9]
tags: [runtime, codex, agy, routing, agent]
status: completed
created: 2026-06-02
updated: 2026-06-02
---

# Codex/Agy Runtime Response Policy 설계

## CPS Rationale

- C -> P: runtime stack은 드러나지만 선택 근거·예측·사후 판정이 없으면 P7 관계 불투명, P8 자가 발화 의존, P9 정보 오염이 남고 downstream P3 silent fail로 이어진다.
- P -> S: S3/S5/S7은 runtime adapter를 작게 관리하고, S8/S9는 선택 신호를 상태와 현재 evidence로 재확인하게 한다.
- S -> AC: implementation Step 4가 Codex/Agy 선택 trace를 요구하고, docs rule과 회귀 테스트가 새 매트릭스 확장을 막는다.

## 구현 계획

1. implementation Step 4의 CPS response policy를 runtime 선택 trace까지 확장한다.
2. `.agents` mirror에 동일 계약을 반영한다.
3. docs rule의 `trigger:` 설명에 runtime response policy 의미를 연결한다.
4. routing contract 테스트로 선택 trace·예측·사후 판정을 고정한다.
5. `cps-learn` 스킬을 추가해 복수 P#/S# 해석과 AC 재구성을 다음 작업에서 재사용한다.

**Acceptance Criteria**:
- [x] Goal: S3/S5/S7/S8/S9 기준으로 Hermes가 Codex/Agy를 선택할 때 선택 근거·적합성 판단·예측·결과 판정이 response policy에 남는다.
  검증:
    review: self
    tests: `python3 -m pytest .claude/scripts/tests/test_skill_routing_contract.py -q`
    실측: implementation Step 4에 Codex/Agy runtime 선택 trace, fit 판단, prediction, post-result 판정이 존재한다.
- [x] Problem AC (P3/P7/P8/P9): runtime 선택이 단순 trigger hit로 끝나지 않고 선택 근거와 사후 판정으로 downstream silent fail·자가 발화·정보 오염을 줄인다.
- [x] Solution AC (S3/S7): Codex는 실행·repo evidence, Agy는 advisory/adversarial 관점으로 역할이 분리된다.
- [x] Solution AC (S5): P#/S#별 전체 라우팅 매트릭스나 새 metadata field를 만들지 않는다.
- [x] Solution AC (S8/S9): Agy/Codex 응답은 사실이 아니라 advisory-signal이며 현재 repo evidence로 재확인한다.
- [x] Guardrail AC (P5/P11): response policy 예외가 누적되더라도 본 wave에서는 새 schema를 만들지 않고 뒤집힐 조건으로 남긴다.
- [x] Guardrail AC (P7/P8): 단일 관점 질문에서 advisor-only 반복이 생기면 `overcalled`로 기록하고 다음 호출은 직접 specialist를 먼저 선택한다.
- [x] Behavior AC (P7/S7): 복수 P#는 문제 차원 증가로, 복수 S#는 실행 구조 증가로 해석한다.
- [x] Step AC (S3/S5/S7/S8/S9): 복수 S#가 붙으면 단일 Goal 안에서도 단계화·반복·분리 검증을 AC에 반영한다.
- [x] Step AC (S6/S7): `cps-learn` 스킬이 복수 P#와 복수 S#를 분리 해석하고 AC 재구성·specialist 폭·학습 반영을 출력한다.
- [x] Verification AC (S6/S7): routing contract 테스트와 precheck로 스킬·룰 계약 반영을 확인한다.

## 결정 사항

- runtime 선택은 `trigger:` hit만으로 끝내지 않고 `selected`·`fit`·`prediction`·`post-result` trace를 남긴다.
- Codex는 실행·diff·repo evidence, Agy는 advisory/adversarial 판단을 기본 역할로 둔다.
- Agy/Codex 응답은 `advisory-signal`이며, 현재 repo 문서·코드·실행 결과로 재확인하기 전까지 fact가 아니다.
- 복수 P#는 중복이 아니라 문제 차원 증가다. 각 P#가 요구하는 관찰·증거 축을
  분해해 무엇을 더 봐야 하는지 정한다.
- 복수 S#는 중복이 아니라 실행 구조 증가다. 각 S#가 요구하는 해결 기준을
  분해해 단일 Goal 안에서도 단계화·반복·분리 검증을 AC에 반영한다.
- 호출 폭은 고정 매트릭스가 아니다. P#가 만든 독립 문제 차원 수가 specialist
  폭을 정하고, S#가 만든 해결 기준 수가 실행 단계·반복·검증 폭을 정한다.
- advisor는 종합·충돌 해소용이다. 단일 증거 축은 `direct specialist first`로
  해당 specialist를 직접 선택하고, 독립 축이 여럿이면 병렬 specialist를 선택한다.
- advisor-only 반복은 `overcalled`로 기록하고 다음 호출에서 직접 specialist를 먼저 선택한다.
- advisor skill 래퍼도 같은 계약으로 정렬한다. implementation 연동 지점은 존재하지
  않는 Step 0.5가 아니라 Step 4이며, 단일 specialist 작업은 SKIP이다.
- 새 metadata field와 P#/S#별 전체 라우팅 매트릭스는 만들지 않는다. 예외가 5개 이상 누적되면 별도 설계로 재검토한다.
- CPS 갱신: 없음. 기존 S3/S5/S7/S8/S9 실행 품질 보강이다.
- `cps-learn`은 다운스트림도 쓰는 일반 스킬이다. `.claude/skills`와 `.agents/skills`
  양쪽에 추가하고 HARNESS.json `skills` 및 h-setup 프로파일에 등록한다.

## 메모

- advisor 권고: Step 4가 SSOT. 새 문서·새 metadata·P#/S#별 agent matrix는 P5/P11 위험으로 제외.
- 사용자 정정: 매트릭스는 고정되어 학습 시스템과 맞지 않는다. 복수 P#는
  더 봐야 할 문제 차원, 복수 S#는 단계화·반복·분리 검증이 필요한 실행 구조다.
- 사용자 후속: CPS+AC 해석을 학습하는 스킬이 필요하다는 지적을 반영해
  `cps-learn`을 추가했다. `cps-check`는 정합 검사, `cps-learn`은 구조 해석과
  AC 재구성이다.
- 검증: `python3 -m pytest .claude/scripts/tests/test_skill_routing_contract.py -q` → 4 passed.
- 문서 검증: `python3 .claude/scripts/docs_ops.py validate` → 오류 0, 기존 archived 날짜 suffix 경고 2건.
- 관계 검증: `python3 .claude/scripts/docs_ops.py verify-relates` → 미연결 0건.
- codebase-analyst 결과: advisor 스킬 래퍼의 SKIP과 implementation 연동 표가 advisor 과중 신호. Step 4/direct specialist first로 정렬 권고.
- risk-analyst 결과: advisor 우회가 새 라우팅 매트릭스로 굳지 않게 agent description SSOT 유지, 사후 post-result 기록 필요.
