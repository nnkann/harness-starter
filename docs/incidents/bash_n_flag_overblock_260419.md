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

## 해결 (1차)

매처를 `git commit`·`git push`로 한정:
```json
{ "if": "Bash(git commit* -n *)", ... },
{ "if": "Bash(git push* -n *)", ... }
```

## 재발 (2차) — 단순화 검증 시나리오 C 중

위 매처도 여전히 광역. claude-code 매처가 명령 인자 전체에서 substring
매칭하는 듯. 스크립트 본문에 `commit`·`push`·`-n` 단어가 우연히 같이
등장하면 hit.

예: 다음 bash 스크립트 실행 차단됨
```bash
STAGED=$(git diff --cached --name-only)  # "commit"·"push" 무관, 그러나 ...
# 이후 awk에서 "-n" 옵션 사용
```

## 해결 (2차)

- `git commit -n*` (인자 직후) + `git commit* -n*` (옵션 사이) 두 패턴
- `git push -n` 차단 제거 (dry-run 정당함, `--dry-run`과 동일)
- 메시지를 짧게 (긴 설명은 발음에 묻힘)

## 재발 방지

- 새 PreToolUse 차단 패턴 추가 시: 광범위 와일드카드(`* -X *`) 절대 금지
- 매처 추가 후 **반드시** 격리 시나리오로 검증 (정당 명령이 막히는지)
- claude-code 매처 동작이 prefix·substring·regex 어느 쪽인지 공식 문서
  확인 후 사용 (현재는 substring 추정 — 추가 검증 필요)

## 메모

이번 단순화 작업 세션 중 자체 발견. hook_flow_efficiency 감사의
첫 산출물.
