---
title: 커밋 속도 최적화 — 단계 조건부 실행 + pre-check→리뷰 데이터 전달 + 모델 스위치
domain: harness
tags: [commit, performance, review-agent]
status: pending
created: 2026-04-18
---

# 커밋 속도 최적화

## 배경

v1.3.2에서 pre-check을 Step 5로 조기 실행하면서 "LLM 호출 전 정적 차단" 경로를
확보. 그러나 다음 경로에서 여전히 불필요한 비용/중복이 발생한다:

1. **불필요한 단계 진입**: WIP이 없는 커밋도 Step 2(계획 문서 처리)가 전수 검사
2. **중복 검증**: pre-check이 이미 잡은 항목(린터, TODO 등)을 리뷰 agent가 재확인할 위험.
   현재는 review.md 문서 지시로만 막음 — 데이터로 강제되지 않음
3. **리뷰의 포커스 부재**: 위험 요인을 pre-check이 감지해도 리뷰 agent는 그 힌트 없이
   전체 diff를 일반 검증 — 집중 지점이 불명확
4. **모델 오버스펙**: 작은 문서 수정에도 `model: sonnet` 고정

## 제안

### 1. 단계 조건부 실행 (gate)

각 단계 진입 전 필요성 검사. 미해당 시 스킵.

| 단계 | 실행 조건 |
|------|-----------|
| 2. 계획 문서 완료 처리 | `git diff --cached --name-only`에 `docs/WIP/` 포함 |
| 3. 하네스 버전 체크 | `.claude/*`, `scripts/*` 변경이 있을 때 (harness-starter 한정) |
| 7. 리뷰 Agent | strict 모드 또는 pre-check 위험 감지 hit 시 |

### 2. pre-check → 리뷰 데이터 전달 (인메모리 전달)

**방식**: 파일/환경변수 저장 없이, commit 스킬이 pre-check을 Bash로 실행한 후
**그 stdout/stderr 출력을 메모리(스킬 컨텍스트)에 담고 바로 리뷰 agent prompt에 포함**.

근거: 리뷰 호출은 같은 커밋 시퀀스 내에서 이어지는 단일 흐름. 파일 경유는
I/O 낭비 + 크로스플랫폼 경로 고민 + 잔여 파일 정리 부담.

**pre-check이 stdout으로 출력할 요약 포맷** (stderr는 사용자 노출용, stdout은
스킬 전달용으로 분리):

```
pre_check_passed: true
already_verified: lint, todo_fixme, test_location, wip_cleanup
risk_factors: 핵심 설정 파일 변경 (.claude/settings.json), 보안 패턴 감지 (token), 삭제 67줄
diff_stats: files=3, +42 -67
```

단순 key-value 라인 형식. JSON도 가능하지만 셸에서 더 간단한 문자열이 빠름.
Agent tool prompt에 그대로 붙여넣기만 하면 agent가 읽어낼 수 있음.

**commit 스킬 Step 7에서**: Agent tool 호출 prompt에 다음 블록 삽입:
```
## pre-check 결과
<pre-check stdout 내용 그대로 붙여넣기>

## 지시
위 risk_factors에 우선순위를 두고 3관점(회귀/계약/스코프) 검증하라.
already_verified 항목은 재검사 마라.
```

### 3. 리뷰 모델 스위치

리뷰 agent의 모델을 diff 규모 + 위험 요인 기반으로 동적 지정.

| 조건 | 모델 |
|------|------|
| 문서만 변경 (*.md, docs/) 또는 ≤ 50줄 | haiku |
| 일반 코드 변경 ≤ 200줄, 위험 요인 없음 | haiku |
| > 200줄, 또는 risk_factors 비어있지 않음 | sonnet |

**구현**: review.md frontmatter의 `model: sonnet` 제거. 커밋 스킬이 Agent tool 호출 시
`model` 파라미터 동적 지정. Agent tool이 이 파라미터를 받는지 먼저 확인 필요.

## 의존성

- pre-commit-check.sh에 **요약 라인을 stdout으로 추가 출력**. 기존 stderr(사용자
  대상 에러 메시지)는 그대로 두고 stdout 채널을 요약 전달용으로 분리.
- SKILL.md Step 5: pre-check을 Bash로 실행할 때 stdout을 변수에 캡처하도록 명시
- SKILL.md Step 7: 캡처한 stdout을 Agent tool prompt에 삽입하도록 명시
- review.md: "prompt에 pre-check 결과 블록이 있으면 already_verified 재검사 금지"
  명시

### 4. 전체 소요 시간 리포팅

커밋 완료 후 스킬이 전체/단계별 소요 시간을 간결히 표시:

```
⏱  전체 1m 2s (pre-check 0.3s / review 58s / commit 3.7s)
```

**구현**:
- commit 스킬의 각 Step 진입 시 `date +%s` 또는 SECONDS 변수로 타임스탬프
- Step 종료 시 차이 계산 누적
- 최종 요약에 포맷 `Nm Ns` (분이 0이면 `Ns`만)

**측정 대상 단계**:
- pre-check (Step 5)
- review (Step 7 병렬, advisor 포함 시 advisor도 분리 표기)
- git commit (Step 8, hook 재실행 포함)
- 기타 긴 단계가 생기면 추가

**효과**:
- 사용자가 어디서 시간 많이 쓰는지 바로 파악
- 최적화 효과를 수치로 확인 가능
- 숨은 병목 드러남

## 검증 방법

1. 문서만 수정하는 커밋 1건 → Step 2/3 스킵되는지 + haiku로 리뷰되는지
2. 일반 코드 수정 1건 → 정상 경로
3. 핵심 설정 변경 1건 → risk_factors 감지 → sonnet 리뷰
4. 각 경로에서 소요 시간 측정 (§4 시간 리포팅으로 자동 확보)

## 우선순위

P1. 체감 속도 개선에 직접적. 단 데이터 전달(2번)은 리뷰 품질 유지의 전제 조건이라
gate(1번)보다 먼저 구현하는 게 안전.

구현 순서 제안:
1. pre-commit-check.sh에 결과 JSON 출력 추가
2. SKILL.md Step 5·7 수정 (데이터 경로 + prompt 포함)
3. review.md에 "already_verified 재검사 금지" 명시
4. Step 2·3 gate 조건 명시
5. 모델 스위치 (Agent tool 파라미터 확인 후)
