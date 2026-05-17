---
name: implementation
description: >-
  작업 오케스트레이터(라우터). CPS 대조 → SSOT 판단 → WIP 관리 → 실행 흐름.
  분석·탐색·검증은 specialist에 위임. 이 스킬은 "언제 누구를 부를지"만 결정.
  TRIGGER when: (1) 사용자가 기능 구현·버그 수정·리팩토링 요청 ("~해줘", "~만들어", "~고쳐"),
  (2) 직전 턴에 구체 계획 제시된 상태에서 승인 표현 ("진행해줘", "OK", "고", "이대로"),
  (3) 직전 작업이 implementation이었어도 후속 작업 트리거는 재발화.
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
| Pass | 나→specialist: 작업 단위 · CPS 참조 · 이미 확인된 내부 자료 |
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

## Step 3. WIP 생성 (분리 필요할 때만)

**파일명** (`.claude/rules/naming.md` SSOT):
- `{abbr}_{slug}.md` (라우팅 태그 폐기 — wave에서 결정)
- abbr: naming.md "도메인 약어" 표
- slug: snake_case 의미명. 날짜 suffix 금지

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

자기완결성·1레이어·구체주의는 사후 review가 잡음.

## Step 4. 실행 (라우팅만)

코드 수정은 메인 Claude. 이 스킬은:

1. **TodoWrite로 단위 분해** — "한 번에 검증 가능한 최소 단위"
2. **specialist 트리거** — agent description SSOT (라우팅 매트릭스 폐기):
   - 에이전트 description에 trigger 명시됨. 해당 description이 시스템 프롬프트에 깔림
   - 막혔을 때 description의 TRIGGER 조건과 일치하면 호출
3. **중복 함수 확인**: LSP + `Grep "def {함수명}"` 1회. check-existing 스킬 폐기

## Step 5. AC 검증 + 기록

**Phase 완료 직후 AC 실행** — 필수:

- **자동화 가능**: Bash로 실행 후 결과 제시
- **자동화 불가** (Claude 행동·UI·운용 효과): "자동 검증 불가 — 운용에서 확인 필요" 명시
- **테스트**: AC `검증.tests`에 `pytest -m <marker>` 명시될 때만 실행 (`self-verify.md` 트리거 매트릭스 SSOT)
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

