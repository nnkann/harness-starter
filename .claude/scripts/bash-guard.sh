#!/bin/bash
# PreToolUse Bash hook — jq로 명령 파싱 후 정밀 검증.
#
# 공식 문서 인용:
# > "Bash permission patterns that try to constrain command arguments are
# >  fragile. ... For more reliable URL filtering, consider: Use PreToolUse
# >  hooks: implement a hook that validates URLs in Bash commands ..."
#
# 단일 hook이 모든 검증을 담당. matcher 패턴은 Bash tool name만 매칭.
# 광역 와일드카드 매처(Bash(* X *))는 substring/glob 동작이 fragile해서
# 우연 매칭 + 우연 통과가 모두 발생. 본 스크립트로 통일.
#
# 종료 코드:
#   0 = 통과
#   2 = 차단 (stderr 메시지를 Claude에게 보냄)

# stdin: PreToolUse hook JSON
INPUT=$(cat)

# jq가 있으면 사용, 없으면 grep으로 fallback
if command -v jq >/dev/null 2>&1; then
  COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""')
else
  # fallback: 단순 grep (정확하지 않을 수 있음)
  COMMAND=$(echo "$INPUT" | grep -oE '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/^"command"[[:space:]]*:[[:space:]]*"//;s/"$//')
fi

# 빈 명령은 통과
[ -z "$COMMAND" ] && exit 0

# ─────────────────────────────────────────────
# 검증 1: --no-verify 플래그 (commit/push hook 우회)
# ─────────────────────────────────────────────
if echo "$COMMAND" | grep -qE '(^|[[:space:]])--no-verify([[:space:]]|$)'; then
  echo "❌ --no-verify 금지 (pre-commit/pre-push hook 우회)." >&2
  exit 2
fi

# ─────────────────────────────────────────────
# 검증 2: git commit -n (--no-verify의 short form)
# 공백 구분 토큰으로 검사 — 단순 substring 아님
# ─────────────────────────────────────────────
# git commit으로 시작하는 명령에서 -n 옵션이 인자로 등장하는지
if echo "$COMMAND" | grep -qE '^[[:space:]]*git[[:space:]]+commit([[:space:]]|$)'; then
  # 토큰 분리해서 -n 단독 인자 확인
  # -m "msg with -n" 안의 -n은 quoted라 이미 한 토큰. 단순 grep으로는 구분 어려움.
  # 셸 평가로 토큰화
  TOKENS=()
  eval "TOKENS=($COMMAND)" 2>/dev/null
  for tok in "${TOKENS[@]}"; do
    if [ "$tok" = "-n" ]; then
      echo "❌ git commit -n 금지 (verify 우회). bash -n 같은 다른 -n은 영향 없음." >&2
      exit 2
    fi
  done
fi

# ─────────────────────────────────────────────
# 검증 3: git commit 호출 시 pre-commit-check.sh 실행
# (이전 settings.json의 별도 매처 통합)
# ─────────────────────────────────────────────
if echo "$COMMAND" | grep -qE '^[[:space:]]*([^|;&]+[[:space:]]+)?git[[:space:]]+commit([[:space:]]|$)'; then
  if [ -f ".claude/scripts/pre-commit-check.sh" ]; then
    bash .claude/scripts/pre-commit-check.sh
    PRE_EXIT=$?
    if [ "$PRE_EXIT" -ne 0 ]; then
      exit "$PRE_EXIT"
    fi
  fi
fi

exit 0
