---
title: PreToolUse Bash -n 오탐으로 정당한 명령 차단
domain: harness
tags: [hook, pre-tool-use, false-positive, bash]
symptom-keywords:
  - "-n 금지"
  - "bash -n"
  - "head -n"
  - "PreToolUse 차단"
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

## 3차 — 공식 문서 확인 (2026-04-19, v1.9.0)

사용자 지적 ("이전에 수정한 내역이 있는데 어느 것도 참조하지 않고
지가 또 혼자 추측해서 수정하고 있는데 하네스가 제대로 작동하고 있는
거 맞아?") 후 공식 문서 https://code.claude.com/docs/en/permissions
조사로 추측 종료.

**확정 사실:**
- `if` 필드의 `Bash(...)`는 **권한 규칙 문법(permission rule syntax)**
- 단일 `*`는 **공백 포함 모든 문자**에 매칭. 와일드카드 위치 자유
  (시작·중간·끝)
- 공식 문서 직접 경고: "Bash permission patterns that try to constrain
  command arguments are **fragile**"
- 공식 권장 대안: **PreToolUse hook 스크립트로 jq 파싱 후 검증**.
  매처 패턴으로 정밀 제어 시도 X.

**1·2차 수정의 잘못:**
- 1차(1a50efd): substring 추정 후 `git commit* -n *` 사용. *가 공백
  포함이라 의도 외 매칭.
- 2차(88f1ff2): "anchor 강화"로 추측 수정 또. 실제 동작 확인 안 함.
- 3차(3468fb5): 또 추측 정밀화.
- 모두 공식 문서 한 번도 안 보고 진행. no-speculation·internal-first
  규칙 직접 위반.

**3차 해결 (v1.9.0):**
- settings.json의 모든 `Bash(... -X ...)` 매처 제거
- 단일 `bash-guard.sh` PreToolUse hook으로 통합 — jq로 명령 파싱 후
  토큰 단위 검사 (`git commit -n` 정확 매칭, `git commit -m "fix -n"`
  같은 메시지 안 -n은 통과 — 공식 권장 동작)
- 회귀 테스트(`test-bash-guard.sh`) 13/13 통과. 이전 광역 매처가 잘못
  차단했던 7가지 정당 명령 모두 통과 검증.
- `test-hooks.sh` 폐기 — bash glob로 매처 모사가 공식 동작과 다름,
  거짓 안전감 제공.

**미해결 수수께끼:**
이번 세션 중 `IS=$(grep -oE 'true|false' .claude/HARNESS.json) ; echo "$IS"`
같은 명령이 `git commit -n 금지` 메시지로 차단된 케이스가 있었음.
이 명령에 `git commit`도 `-n`도 없는데 매칭. 매처 광역성과 별개의
미스터리. v1.9.0의 단일 bash-guard.sh로 매처 자체를 단순화해서 우회됨.
원인 규명은 추가 시간 가치 낮음 (공식 권장 패턴 적용으로 해결됨).

## 메모

이번 단순화 작업 세션 중 자체 발견. hook_flow_efficiency 감사의
첫 산출물.
