# Hooks 규칙

PreToolUse `matcher`·`if` 패턴의 취약성을 피한다.

> **적용 범위**: 이 규칙은 `settings.json` **`hooks` 블록의 `matcher`** 패턴만
> 대상으로 한다. `permissions.allow`의 `Bash(...)` 항목은 **허용 목록**이므로
> 이 규칙과 무관하다 — 혼동 금지.

## 금지 (hooks.matcher 한정)

`hooks` 블록의 `matcher`·`if`에 **argument-constraint 패턴 추가 금지**:

```json
// ❌ 금지 — hooks.matcher argument-constraint
{ "if": "Bash(* --no-verify*)" }
{ "if": "Bash(git commit* -n*)" }
{ "if": "Bash(* -n *)" }

// ✅ 무관 — permissions.allow는 허용 목록, 이 규칙 적용 안 됨
{ "permissions": { "allow": ["Bash(HARNESS_DEV=1 git *)", "Bash(cd *&&*)"] } }
```

공식 문서(`code.claude.com/docs/en/permissions`) 명시 경고:
> "Bash permission patterns that try to constrain command arguments
>  are fragile."

단일 `*`가 공백 포함 모든 문자에 매칭되어 의도 외 명령을 우연 차단.
stderr가 비어 디버깅 불가. incident `bash_n_flag_overblock`,
`matcher_false_block_and_readme_overwrite` 참조.

## 대안

도구 이름만 matcher로 잡고, **단일 hook 스크립트 안에서 jq + 토큰 분리**로
검증:

```json
// ✅ 권장
{
  "matcher": "Bash",
  "hooks": [
    { "type": "command", "command": "bash .claude/scripts/bash-guard.sh" }
  ]
}
```

예시: `.claude/scripts/bash-guard.sh` — stdin JSON 파싱, 토큰 단위 검사.

## 위반 발견 시

- **review 에이전트**: settings.json diff의 **`hooks` 블록 내** `matcher`에
  argument-constraint 패턴이 추가됐으면 [차단].
  `permissions.allow`에 `Bash(...)` 패턴이 추가된 것은 위반 아님 — 혼동 금지.
- **사용자**: 즉시 bash-guard.sh 방식으로 통합.
 
