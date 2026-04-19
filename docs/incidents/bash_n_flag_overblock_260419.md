---
title: PreToolUse Bash -n 오탐으로 정당한 명령 차단
domain: harness
tags: [hook, pre-tool-use, false-positive, bash]
symptom-keywords:
  - "-n 금지"
  - "bash -n"
  - "head -n"
  - "PreToolUse 차단"
relates-to:
  - path: ../WIP/harness--hook_flow_efficiency_260418.md
    rel: caused-by
status: completed
created: 2026-04-19
updated: 2026-04-19
---

# PreToolUse Bash -n 오탐

## 증상

`Bash` 도구 호출이 다음 메시지로 차단:
```
❌ --no-verify / -n 금지.
```

차단된 명령 예시 (모두 정당):
- `bash -n script.sh` — 셸 구문 체크 (검증 자체)
- `head -n 5 file` — 파일 미리보기
- `awk -n ...` 같은 옵션 사용

## 원인

`.claude/settings.json`의 PreToolUse 매처 `Bash(* -n *)`가 너무 광범위.
원래 의도는 `git commit -n` (verify hook 우회) 차단인데, 모든 `-n`
플래그를 잡음.

## 해결

매처를 `git commit`·`git push`로 한정:
```json
{ "if": "Bash(git commit* -n *)", ... },
{ "if": "Bash(git push* -n *)", ... }
```

`bash -n` 같은 구문 체크는 `bash -o noexec`로 우회 가능 (메시지에 명시).

## 재발 방지

- 새 PreToolUse 차단 패턴 추가 시: 광범위 와일드카드(`* -X *`) 대신
  대상 명령을 명시 (`git commit* -X *`)
- 차단 메시지에 정당한 사용 시 대안 제공 (위 `bash -o noexec` 예시)

## 메모

이번 단순화 작업 세션 중 자체 발견. hook_flow_efficiency 감사의
첫 산출물.
