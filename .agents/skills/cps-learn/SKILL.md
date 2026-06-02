---
name: cps-learn
description: >-
  CPS+AC 해석 스킬. 복수 P#는 문제 차원 증가로 보고 무엇을 더 봐야 하는지
  분석 축을 도출하고, 복수 S#는 실행 구조 증가로 보고 단계화·반복·분리
  검증 AC를 설계한다. TRIGGER when: implementation 중 P#/S#가 복수이거나,
  사용자가 "CPS 조합 해석", "AC 쪼개기", "호출 폭 판단", "cps-learn"을
  요청할 때. SKIP: 단일 P#/S#가 명확하고 AC 구조가 이미 충분한 경우,
  단순 번호 정합 검사(→ cps-check), 외부 자료 조사(→ researcher).
serves: S6, S7, S8, S9
---

# CPS Learn

CPS 번호를 맞히는 스킬이 아니다. 복수 C/P/S가 들어왔을 때 **왜 같이
붙었는지**를 해석하고, 그 해석을 AC·specialist 호출 폭·사후 학습으로
연결한다.

## 입력

호출자는 아래를 넘긴다:

- `C`: 사용자 발화·실측·WIP frontmatter `c`
- `problem`: 단일 또는 복수 P#
- `s`: 단일 또는 복수 S#
- `AC`: 기존 AC 초안 또는 비어 있음
- `post-result`: 이전 호출의 `fit|misfit|overcalled|undercalled`가 있으면 포함

## 해석 원칙

1. **복수 P# = 문제 차원 증가**
   - 중복 라벨이 아니다.
   - 각 P#가 요구하는 관찰·증거 축을 분해한다.
   - 출력은 "무엇을 더 봐야 하는가"다.

2. **복수 S# = 실행 구조 증가**
   - 해결책 나열이 아니다.
   - 각 S#가 요구하는 해결 기준을 분해한다.
   - 출력은 단계화·반복·분리 검증이 필요한 AC 구조다.

3. **호출 폭은 학습값**
   - 고정 라우팅 매트릭스 금지.
   - P#가 만든 독립 문제 차원 수가 specialist 폭을 정한다.
   - S#가 만든 해결 기준 수가 실행 단계·반복·검증 폭을 정한다.
   - 이전 `overcalled`·`undercalled`·`misfit`은 다음 호출 폭 조정 입력이다.

## 출력 형식

```
## cps-learn 결과

### P-axis: 더 봐야 할 문제 차원
- P#: <관찰·증거 축> → <확인할 것>

### S-axis: 실행·검증 구조
- S#: <해결 기준> → <Step/Guardrail/Verification AC 반영>

### AC 재구성
- Problem AC (P#): ...
- Solution AC (S#): ...
- Step AC (S#): ...
- Guardrail AC (P#/S#): ...
- Verification AC (S#): ...

### Specialist 폭
- narrow | parallel | advisor-synthesis
- 근거: <P-axis/S-axis 조합 해석>
- expected-output: <각 specialist에 넘길 좁은 질문>

### 학습 반영
- post-result 입력: <없음|fit|misfit|overcalled|undercalled>
- 다음 호출 조정: <좁힘|넓힘|유지|advisor 종합 필요>

### CPS 영향
- 유지 / P# 재분류 후보 / S 변경 후보(owner 승인 필요) / AC 보강 후보 중 하나
```

## 금지

- P#/S#별 고정 라우팅 매트릭스를 만들지 않는다.
- Solution 본문 substring을 AC에 박제하지 않는다. 번호만 쓴다.
- Agy/Codex·specialist 응답을 fact로 쓰지 않는다. repo 문서·코드·실행 결과로
  재확인하기 전까지 `advisory-signal`이다.
- "단일 Goal이니 단일 AC"로 축약하지 않는다. 복수 S#면 한 Goal 안에서도
  단계·반복·분리 검증이 필요할 수 있다.
