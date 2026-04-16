---
name: implementation
description: >-
  작업 시작 전 CPS 대조 + docs/WIP/에 계획 문서 생성, 작업 중 상태 기록. 완료 후 정리는 commit 스킬이 처리.
  TRIGGER when: 사용자가 기능 구현, 버그 수정, 리팩토링 등 코드 작업을 요청했을 때,
  "~해줘", "~만들어", "~고쳐", "~추가해" 등 구현 의도가 있는 요청.
  SKIP: 단순 질문, 설명 요청, 문서만 수정, 설정 변경, 커밋 요청, 1줄 타이포 수정.
---

# Implementation

작업을 시작하기 전에 CPS와 대조하고, 계획 문서를 만들고, 작업 중 상태를 기록한다.
완료 처리와 이동은 commit 스킬이 담당한다.

## 흐름

### Step 0. CPS 대조 (작업 시작 전)

먼저 harness-init이 완료되었는지 확인한다.

**init 미완료 감지:**
CLAUDE.md `## 환경`의 `패키지 매니저:` 값이 비어있으면 init이 완료되지 않은 것이다.
**이 경우 작업을 시작하지 않고 차단한다:**

> ⛔ 하네스 초기화가 완료되지 않았습니다. CPS와 기술 스택 없이는 작업을 시작할 수 없습니다.
>
> - 신규 프로젝트: `/harness-init` 실행
> - 기존 프로젝트에 하네스 이식: `/harness-adopt` → `/harness-init` 순서로 실행

이 게이트는 건너뛸 수 없다. init/adopt를 완료해야 implementation이 동작한다.

**init 완료 상태:**
docs/guides/에 CPS 문서(`project_kickoff_*.md`)가 있으면 먼저 읽는다.
`status: sample`인 문서는 예제이므로 무시한다. 실제 CPS만 대조한다.

**docs-lookup 에이전트로 관련 문서 탐색:**
CPS를 읽은 뒤, 이번 작업과 관련된 기존 문서가 있는지 탐색한다.
- 같은 Problem을 다룬 이전 결정이 있는가? (`decisions/`)
- 관련 인시던트가 있는가? (`incidents/`)
- 참고할 가이드가 있는가? (`guides/`)

확인할 것:
- 이번 작업이 CPS의 어떤 Problem과 연결되는가?
- 연결이 불명확하면 사용자에게 질문하라.
- 기존 Solution 방향과 충돌하지 않는가?
- 이전 결정/인시던트에서 참고할 내용이 있는가?

### Step 0.5. 접근법 검증 (선택)

작업의 접근법이 정리되면 사용자에게 묻는다:

> "이 접근법을 검증할까요? [Y/n]"

**Y 선택 시**: advisor 스킬의 리서치 + 코드분석 에이전트 2개를 병렬 호출한다.
- 리서치: "이 접근법에 대한 공식 문서, 업계 사례, 알려진 문제점"
- 코드분석: "현재 코드베이스에서 이 접근법이 기존 패턴과 충돌하는지"
- 결과를 Step 1에서 만드는 WIP 문서의 `## 메모`에 자동 기록

**N 선택 시 또는 무응답**: 건너뛰고 Step 1로 진행한다.

이 단계는 **작업 규모가 클 때**만 의미 있다. 파일 1~2개 수정하는 작업에는 제안하지 않는다.

### Step 1. 문서 생성

docs/WIP/에 문서를 만든다.

파일명: `{대상폴더}--{작업내용}_{YYMMDD}.md`
- 대상폴더: 완료 시 이동할 docs/ 하위 폴더명 (decisions, guides, incidents, harness)
- `--`: 대상폴더와 작업내용을 구분하는 구분자 (언더스코어와 혼동 방지)
- 작업내용: snake_case, 간결하게
- YYMMDD: 생성 날짜

이동 시 `{대상폴더}--` 접두사는 제거된다. WIP에서만 쓰이는 라우팅 태그다.

예시 (WIP → 이동 후):
- `decisions--auth_stack_decision_260330.md` → `docs/decisions/auth_stack_decision_260330.md`
- `incidents--token_refresh_fix_260330.md` → `docs/incidents/token_refresh_fix_260330.md`
- `guides--payment_api_260330.md` → `docs/guides/payment_api_260330.md`

문서 구조:
```markdown
---
title: {작업 제목}
domain: {CPS 도메인 또는 harness/meta}
tags: []
relates-to: []
status: pending
created: {YYYY-MM-DD}
---

# {작업 제목}

## 목표
- 이 작업에서 결정하거나 만들 것
- CPS 연결: Problem #{번호} (있으면)

## 결정 사항
(작업하면서 채움)

## 메모
(작업 중 발견한 것, 변경 이유 등)
```

- domain은 naming.md "도메인 목록 > 확정"에서 선택. 없으면 사용자에게 확인.
- relates-to는 작업 중 관련 문서가 명확해지면 채운다.

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

### Step 4. 작업 완료 + CPS Context 업데이트

`status: in-progress` → `status: completed`로 변경한다.

**CPS Context 업데이트 (사이클 완성):**
작업 결과가 기존 CPS에 영향을 주는지 확인한다:

| 상황 | 행동 |
|------|------|
| 새 Problem을 발견했다 | CPS 문서의 Problem 섹션에 추가 |
| 기존 Solution이 바뀌었다 | CPS 문서의 Solution 섹션 갱신 |
| Context가 달라졌다 (전제 변경) | CPS 문서의 Context 섹션 갱신 |
| 새 도메인이 생겼다 | CPS 도메인 목록 + naming.md에 추가 |
| 변경 없음 | 건너뜀 |

CPS 문서를 갱신했으면 WIP 문서의 `## 메모`에 "CPS 갱신: [변경 내용]"을 기록한다.

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
