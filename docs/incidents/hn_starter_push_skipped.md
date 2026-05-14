---
title: starter 12커밋 push 누락 — 다운스트림이 업스트림 변경 못 봄
domain: harness
tags: [push, starter, downstream, propagation, commit-skill]
problem: P3
s: [S3]
symptom-keywords:
  - "다운스트림에서 안 보여"
  - "업스트림에 안 보이지"
  - "harness-upgrade 변경 없음"
  - "fetch했는데 갱신 없음"
relates-to:
  - path: ../harness/MIGRATIONS.md
    rel: references
status: completed
created: 2026-04-19
updated: 2026-04-19
---

# starter 12커밋 push 누락

## 증상

다운스트림 프로젝트에서 `git fetch harness-upstream` 후
`/harness-upgrade`를 실행해도 v1.7.0/v1.8.0 변경이 안 보임.
"왜 다른 프로젝트에서 업스트림에 안 보이지?" 사용자 발견.

## 원인

starter 리포의 12커밋(70d3378..3468fb5) 전부 로컬에만 존재. GitHub
origin에 push 안 됨.

근본 원인:
1. starter는 `.git/hooks/pre-push`가 `HARNESS_DEV=1` 환경변수 없으면
   푸시 차단 (실수 push 방지). commit과 동일.
2. commit 스킬이 매 커밋마다 `HARNESS_DEV=1 git commit`은 호출했지만
   `git push`는 호출 안 함. 스킬 명세에 "푸시" 섹션이 있지만 starter
   보호 우회 명시 없어 LLM이 일반 커밋처럼 처리하고 끝냄.
3. push 차단 시 별도 알림 없으면 "안 했음"이 silent.

## 해결

### 즉시
- `HARNESS_DEV=1 git push origin main`으로 12커밋 한 번에 push.
- 다운스트림이 다음 fetch 시 정상 수신.

### 재발 방지
- commit 스킬 "푸시" 섹션에 starter 분기 추가:
  - `is_starter: true`면 `HARNESS_DEV=1 git push` 명시
  - push 결과를 사용자 보고에 반드시 포함
- test-hooks.sh에 push 차단 회귀 케이스 추가
  - `HARNESS_DEV=1 git push` 통과
  - 일반 `git push` 차단 (starter에서)
- harness-upgrade 스킬 Step 0에 안내:
  - 다운스트림 사용자가 업스트림 fetch 후 빈 결과 받으면 starter
    리포에 push가 안 된 가능성을 안내

## 메모

본 패턴은 "보호 hook + 자동화 스킬"의 일반적 함정. 보호 hook이 작동
하면 silent하게 해당 작업이 안 되는데, 자동화 스킬은 보호 우회 절차를
명시해야 한다. 다른 보호 hook(--no-verify 차단 등)도 같은 패턴 점검 필요.

## 관련 발견 — pre-check.sh lint stdout 오염

본 인시던트 처리 중 사용자 보고로 추가 발견:
- 다운스트림(monorepo·lint 보유)에서 `bash test-pre-commit.sh`가 12/21로
  떨어짐. starter(lint 없음)에선 21/21.
- 원인: `pre-commit-check.sh`의 `$LINT_CMD 2>/dev/null` — stderr만 버리고
  stdout은 흘림. lint 명령(npm/eslint 등)의 stdout이 pre-check stdout
  (key:value)에 섞여 commit 스킬·review·테스트의 grep 매칭 실패.
- 해결: `2>&1`로 묶어 변수 캡처, 종료 코드만 평가, 실패 시 stderr로
  마지막 20줄 출력 (사용자 디버깅 도움).
- 이번 v1.8.1 패치에 포함.
