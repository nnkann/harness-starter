# Hooks 규칙

defends: P4

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

## 출력 의미 계약

hook stdout/stderr는 LLM이 후속 판단 baseline으로 삼는 신호다. count·라벨만
노출하면 P9 정보 오염을 만들 수 있으므로 의미를 분리해 출력한다.

- 차단: 차단된 명령·이유·다음 행동을 stderr에 명시
- 통과: 불필요한 성공 라벨 출력 금지. 출력이 필요하면 무엇을 검증했는지 명시
- count: 단독 출력 금지. loaded/validated/stale/skipped 같은 상태와 함께 출력
- skip: "위험 없음"이 아니라 "검사하지 않음"으로 표기

## 위반 발견 시

- **review 에이전트**: settings.json diff의 **`hooks` 블록 내** `matcher`에
  argument-constraint 패턴이 추가됐으면 [차단].
  `permissions.allow`에 `Bash(...)` 패턴이 추가된 것은 위반 아님 — 혼동 금지.
- **사용자**: 즉시 bash-guard.sh 방식으로 통합.
 
