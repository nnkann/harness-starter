---
name: implementation
description: 작업 시작 전 CPS 대조 + docs/WIP/에 계획 문서 생성, 작업 중 상태 기록. 완료 후 정리는 commit 스킬이 처리.
---

# Implementation

작업을 시작하기 전에 CPS와 대조하고, 계획 문서를 만들고, 작업 중 상태를 기록한다.
완료 처리와 이동은 commit 스킬이 담당한다.

## 흐름

### Step 0. CPS 대조 (작업 시작 전)

docs/setup/에 CPS 문서가 있으면 먼저 읽는다.

확인할 것:
- 이번 작업이 CPS의 어떤 Problem과 연결되는가?
- 연결이 불명확하면 사용자에게 질문하라.
- 기존 Solution 방향과 충돌하지 않는가?

CPS 문서가 없으면 (아직 init 전이거나 가벼운 프로젝트면) 이 단계를 건너뛴다.

### Step 1. 문서 생성

docs/WIP/에 문서를 만든다.

파일명: `{대상폴더}_{작업내용}_{YYMMDD}.md`
- 대상폴더: 완료 시 이동할 docs/ 하위 폴더명 (setup, history, development, harness)
- 작업내용: snake_case, 간결하게
- YYMMDD: 생성 날짜

예시:
- `setup_auth_stack_decision_260330.md` → 완료 시 docs/setup/으로
- `history_token_refresh_fix_260330.md` → 완료 시 docs/history/로
- `development_payment_api_260330.md` → 완료 시 docs/development/으로

문서 구조:
```markdown
> status: pending

# {작업 제목}

## 목표
- 이 작업에서 결정하거나 만들 것
- CPS 연결: Problem #{번호} (있으면)

## 결정 사항
(작업하면서 채움)

## 메모
(작업 중 발견한 것, 변경 이유 등)
```

문서가 먼저 존재해야 작업을 시작한다.

### Step 2. 작업 시작: 상태 변경

`status: pending` → `status: in-progress`로 변경한다.

### Step 3. 작업 중: 기록

- `## 결정 사항`에 내려진 결정과 이유를 기록한다.
- `## 메모`에 작업 중 발견한 것, 변경한 이유를 남긴다.
- 결정이 다른 파일에 반영되면 어디에 반영했는지 기록한다.

예시:
```markdown
## 결정 사항
- 아키텍처: flat 선택. 도메인 2개(auth, content)로 소규모.
- 프레임워크: Next.js. SSR 필요 + 팀 경험.
  → 반영: CLAUDE.md ## 환경, naming.md ## 폴더명
```

### Step 4. 작업 완료

`status: in-progress` → `status: completed`로 변경한다.
이후는 commit 스킬이 처리한다 (커밋 시 자동으로 적절한 폴더로 이동).

## 상태 값

| 상태 | 의미 |
|------|------|
| pending | 계획만 잡음. 아직 시작 안 함. |
| in-progress | 작업 진행 중. |
| completed | 작업 완료. 커밋 시 이동 대상. |
| abandoned | 중단. 커밋 시 archived/로 이동. |

## docs/WIP/ 규칙

- 이 폴더에 파일이 있다 = 할 일이 있다.
- completed/abandoned 파일이 남아있으면 안 된다 (commit이 정리).
- 문서는 간결하게. 결정과 이유만 기록. 장문 금지.
