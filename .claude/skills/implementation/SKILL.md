---
name: implementation
description: >-
  작업 오케스트레이터(라우터). CPS 대조 → SSOT 판단 → WIP 관리 → 실행 흐름.
  분석·탐색·검증은 specialist에 위임. 이 스킬은 "언제 누구를 부를지"만 결정.
  TRIGGER when: (1) 사용자가 기능 구현·버그 수정·리팩토링 요청 ("~해줘", "~만들어", "~고쳐"),
  (2) 직전 턴에 구체 계획 제시된 상태에서 승인 표현 ("진행해줘", "OK", "고", "이대로"),
  (3) 직전 작업이 implementation이었어도 후속 작업 트리거는 재발화,
  (4) 코드·테스트·스크립트·룰 감사/개선을 위한 계획 문서부터 만들라는 요청.
  SKIP: 단순 질문·설명, 문서만 수정(→ write-doc), settings.json 키-값 토글,
  커밋 요청(→ commit), 1줄 타이포.
serves: S1, S6
---

# Implementation

작업 오케스트레이터. 누구를 언제 부를지 결정한다. 완료 처리·이동은 commit
스킬이 담당.

## 핸드오프 계약

| 축 | 내용 |
|----|------|
| Pass | 사용자→나: 작업 요청 원문(고유명사) · 승인 표현 · 직전 턴 계획 |
| Pass | 나→specialist: 작업 단위 · CPS packet(C/P/S/AC/flow/open question) · 이미 확인된 내부 자료 |
| Pass | 나→commit: WIP 경로 · status · `## 결정 사항`·`## 메모` |
| Preserve | 사용자 원문 고유명사 · specialist 응답 원문(요약 금지) · 위험 신호 |
| Signal | ⛔ 차단(init 미완료·3회 실패) · ⚠️ 경고(위험 hit) · 🔍 추적(specialist 호출) |
| Record | WIP `## 결정 사항`·`## 메모` (commit이 영속화) |

## Step 1. 진입 게이트 + CPS 매칭

**init 게이트**: `docs/guides/project_kickoff.md` 부재 또는 `status: sample`이면
차단:
> ⛔ 하네스 초기화 미완료. `/harness-init` 또는 `/harness-adopt → /harness-init` 실행.

SSOT: `.claude/scripts/check_init_done.sh`.

**CPS 매칭** (`docs_ops.py cps list`로 P# 후보 확인):

| 매칭 결과 | 행동 |
|---------|------|
| hit | P# 확정. WIP frontmatter `problem: P#` |
| miss + 병합 | 기존 Problem 본문 확장 (write-doc 위임) |
| miss + 추가 | 신규 P# 등록 (`docs_ops.py cps add "1줄"`) |
| Solution 변경 | owner 승인 필수 |

**Solution 인용** (번호만):
```yaml
problem: P3
s: [S2, S6]
```

**CPS 정합 substep** (옵트인 — `/cps-check` 단독 호출 시만 실행).
자동 발화 안 함 (자가 발화 의존 회피).

**CPS flow type** — C → P → S 단방향만 가정하지 않는다. Step 1에서
작업 발화가 어디서 시작했는지 먼저 라벨링하고, WIP `## CPS Rationale`에
역추적 근거를 남긴다.

| flow | 신호 | 처리 |
|------|------|------|
| `forward` | 사용자 관찰·버그·개선 요청(C)에서 시작 | C → P → S → AC 순서로 진행 |
| `reverse-solution` | 사용자가 특정 S/도구/규칙부터 바꾸자고 함 | S가 줄이려는 P#를 역조회하고, C가 그 P에 실제로 맞는지 확인 |
| `reverse-evidence` | 테스트·AC·pre-check·cron report 같은 증거에서 시작 | 증거가 어떤 S 해결 기준을 건드리는지 찾고 P#를 재확인 |
| `resume` | 기존 WIP·이전 계획·중단된 작업을 다시 이어감 | 기존 WIP `c/problem/s/AC`를 우선 읽고, 현재 C와 달라졌으면 재분류 |
| `interrupt` | 작업 중 스코프 외 이슈·BIT·review 경고 발생 | 본 wave 영역이면 P11 규칙대로 통합, 아니면 WIP 메모에 P# 후보와 재호출 조건 기록 |

`reverse-*`와 `resume`에서 P#가 애매하면 P10으로 숨기지 말고 가까운 P# 후보
1개와 의심 근거 1줄을 같이 남긴다. S 정의 변경은 여전히 owner 승인 필요.

## Step 2. 기존 자산 확인 + SSOT 분리 판단

**3단계 탐색** (`.claude/rules/docs.md` SSOT):

1. cluster 스캔 — `docs/clusters/{domain}.md` Read. tag 분포로 후보 선별
2. 키워드 grep — `docs/**/*.md` 본문 grep
3. 후보 본문 Read

**두 질문**:

1. SSOT가 이미 있는가? → 있으면 갱신 (completed면 `docs_ops.py reopen`)
2. 분리가 정말 필요한가? → 별도 실행·검증 / ADR급 독립 참조 / 진행 상태
   보존 필요할 때만

기본값은 기존 SSOT 갱신. 새 파일은 분리 근거 있을 때만. **탐색 결과는
상류 SSOT `## 메모`에 기록 의무** (묵시적 소실 금지).

**SSOT drift 발견 시** (`.claude/rules/docs.md` "SSOT drift 발견 시 통합 의무"):
- 같은 행동 계약·판정 기준·절차 후보가 2곳 이상이면 본 작업 범위에 포함한다.
- owner SSOT 1곳을 지정하고, 나머지는 참조·mirror·다운스트림 안내 등 역할을
  축소한다.
- 유지해야 하는 중복은 코드=판정, skill=절차, MIGRATIONS=다운스트림 안내,
  decision=이유처럼 역할을 명시한다.
- WIP AC에 통합/역할 분리 확인을 넣고, 정리 전 완료 선언 금지.

**코드 심볼 SSOT** (`.claude/rules/code-ssot.md`):
- 함수·메서드·클래스·변수·상수·정규식·schema key·환경변수 이름도 SSOT 대상이다.
- 새 심볼 추가 전 이름/의미 키워드로 기존 심볼과 호출자를 1차 검색한다.
- 같은 의미의 심볼이 2곳 이상이면 owner 심볼 지정·참조화·mirror 역할 명시를
  본 작업 범위에 포함한다.

## Step 3. WIP 생성 (분리 필요할 때만)

사용자가 "먼저 계획 문서부터"라고 해도, 이후 코드·테스트·스크립트·룰 변경으로
이어지는 작업이면 본 Step이 WIP를 만든다. write-doc은 문서 자체가 최종 산출물일
때만 사용한다.

**파일명** (`.claude/rules/naming.md` SSOT):
- `{대상폴더}--{abbr}_{slug}.md`
- 대상폴더: completed 이동 대상 폴더 (`decisions`, `guides`, `incidents`, `harness`, `cps`)
- abbr: naming.md "도메인 약어" 표
- slug: snake_case 의미명. 날짜 suffix 금지
- 현재 `docs_ops.py move`가 `{대상폴더}--` 접두사로 이동 대상을 판정한다.

**frontmatter** (필수):
```yaml
---
title: ...
domain: harness  # naming.md 도메인 목록
problem: P3      # CPS 인용 번호만
s: [S2, S6]
tags: []         # 영문 소문자+하이픈+숫자만 (naming.md tag 정책)
status: in-progress
created: YYYY-MM-DD
---
```

**본문 2원칙**:
1. 무엇을 한다 (Goal 1줄)
2. 어떻게 검증할지 (AC `검증.tests`·`검증.실측`)
3. typed AC로 P#/S# 추적성을 드러낸다 (`Problem AC (P#)`,
   `Solution AC (S#)`, `Step AC (S#)`, `Behavior AC (P#/S#)`,
   `Guardrail AC (P#/S#)`, `Verification AC (S#)`)

typed AC는 `.claude/rules/docs.md` "## AC 포맷"이 SSOT다. 각 typed AC
항목은 제목 또는 본문에 `P#` 또는 `S#`를 직접 인용해야 하며, frontmatter의
`problem`·`s` 번호가 AC 섹션 안에 각각 1회 이상 등장해야 한다.

**implementation WIP 실행 계획 경고** (soft warning):
- WIP가 코드·테스트·스크립트·룰 변경으로 이어지면 `## 구현 계획` 또는 동등한
  실행 단계 섹션을 둔다.
- 각 단계는 산출물을 명시한다. 예: 로그, 계측값, 구조체/필드, UI 표시, 테스트,
  문서 갱신.
- AC에는 "무엇을 확인하면 다음 단계로 갈 수 있는지"가 들어가야 한다.
- 순수 결정문·조사문·사고 기록·write-doc 산출물·1줄 타이포·settings 토글은 예외.
- 누락 시 "실행 단계/산출물 누락"으로 경고하고, 완료 선언 전 보완을 유도한다.
  반복 효과가 확인되기 전까지 hard fail로 막지 않는다.

자기완결성·1레이어·구체주의는 사후 review가 잡음.

## Step 4. 실행 (라우팅만)

코드 수정은 메인 Claude. 이 스킬은:

1. **TodoWrite로 단위 분해** — "한 번에 검증 가능한 최소 단위"
2. **specialist 트리거** — agent description SSOT (라우팅 매트릭스 폐기):
   - 에이전트 description에 trigger 명시됨. 해당 description이 시스템 프롬프트에 깔림
   - 막혔을 때 description의 TRIGGER 조건과 일치하면 호출
   - 호출 prompt에는 전체 문서 덤프 대신 CPS packet을 포함한다:
     `C`, `problem`, `s`, `flow`, `AC`, `already-read`, `question`, `expected-output`
   - specialist 응답에는 `CPS 영향`을 요구한다: 유지 / P# 재분류 후보 /
     S 변경 후보(owner 승인 필요) / AC 보강 후보 중 하나
   - specialist가 cron·memory·reminder·과거 incident를 근거로 들면 현재 repo
     evidence로 재확인하기 전까지 `memory-signal`로만 기록한다.
3. **downstream cron 학습 신호**:
   - cron report·Hermes delta·downstream inventory가 "안 됨/미진행"을 말하면
     사실 확정이 아니라 `reverse-evidence` flow로 처리한다.
   - 관련 WIP가 있으면 흡수하고, 없으면 `docs/decisions/hn_hermes_managed_downstream_memory.md`
     계약에 따라 Hermes/downstream SSOT 재확인 후보로 기록한다.
   - 자동으로 downstream 파일을 수정하거나 commit/push하지 않는다.
4. **중복 함수 확인**: LSP + `Grep "def {함수명}"` 1회. check-existing 스킬 폐기

## Step 5. AC 검증 + 기록

**Phase 완료 직후 AC 실행** — 필수:

- **자동화 가능**: Bash로 실행 후 결과 제시
- **자동화 불가** (Claude 행동·UI·운용 효과): "자동 검증 불가 — 운용에서 확인 필요" 명시
- **테스트**: AC `검증.tests`에 `pytest -m <marker>` 명시될 때만 실행 (`self-verify.md` 트리거 매트릭스 SSOT)
- **실행 계획 점검**: implementation WIP에 실행 단계 섹션 또는 단계별 산출물이 없으면
  "실행 단계/산출물 누락" 경고를 남기고, 완료 선언 전 보완한다. 예외는 Step 3
  "implementation WIP 실행 계획 경고" 기준을 따른다.
- **검증 다이어트**: pytest는 무거운 작업이다. 기본값은 변경 파일에 직접 대응하는
  단일 테스트 파일·단일 test id·좁은 marker다. 전체 스위트는 사용자가 요청했거나,
  릴리즈/커밋 직전 고위험 공유 코어 변경에서 최종 1회만 실행한다. 문구·WIP 기록만
  바뀐 경우 pytest를 다시 돌리지 않는다.
- **문서 헬스체크**: docs/ 문서가 생성·수정됐으면 `.claude/rules/docs.md`
  "문서 헬스체크 레이어" 체크 항목을 완료 전 자기 검증한다.
- **AC 미통과 → "완료" 선언 금지**. 원인 파악 후 재수정

**WIP 갱신**:
- `## 결정 사항`: 결정 + 이유 + 반영 위치
- `## 메모`: specialist 응답 원문 (요약 금지)

**스코프 외 버그 발견 시**: 별 WIP 생성하거나 본 WIP `## 메모`에 1줄 기록.
"나중에 처리" 금지.

## Step 6. 완료 + status 전환

`status: in-progress` → `status: completed`.

**CPS 영향 확인**:
| 상황 | 행동 |
|------|------|
| 새 Problem 발견 | `docs_ops.py cps add "1줄"` |
| 기존 Solution 변경 | owner 승인 후 kickoff 갱신 |
| 변경 없음 | WIP `## 결정 사항`에 "CPS 갱신: 없음" 명시 |

이후 commit 스킬이 이동·cluster 갱신 처리.

## 실패·escalate

| 막힘 | 에이전트 | 조건 |
|------|---------|------|
| 에러·테스트 실패 원인 불명 | debug-specialist | 1회 실패 즉시 |
| 동일 수정 2회 이상 | debug-specialist | 즉시 |
| 접근법 막막 | advisor | 방향 안 보일 때 |
| 위임 사이클 3회 미해결 | 사용자 보고 | — |

**중단**: 복구 불가 판단 시 `status: abandoned`. commit이 archived/로 이동.

## docs/WIP/ 규칙

- 파일 있다 = 할 일 있다
- completed/abandoned 잔재 금지 (commit 정리)
- 본문 50줄 이내 권장. 장문 금지
