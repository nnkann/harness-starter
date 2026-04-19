# Hooks 규칙

PreToolUse `matcher`·`if` 패턴의 취약성을 피한다.

## 금지

`.claude/settings.json`에 **argument-constraint 매처 추가 금지**:

```json
// ❌ 금지
{ "if": "Bash(* --no-verify*)" }
{ "if": "Bash(git commit* -n*)" }
{ "if": "Bash(* -n *)" }
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

- **review 에이전트**: settings.json diff에 argument-constraint 매처가
  추가됐으면 [차단].
- **사용자**: 즉시 bash-guard.sh 방식으로 통합.
