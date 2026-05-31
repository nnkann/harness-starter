#!/bin/bash
# agy-review.sh - downstream 공통 Agy advisory review runner
#
# 사용:
#   bash .claude/scripts/agy-review.sh "검토 질문"
#   printf '%s\n' "검토 질문" | bash .claude/scripts/agy-review.sh
#
# 정책:
# - repo-local 구현물이 아니라 local Agy execution binding을 호출한다.
# - Agy는 advisory reviewer지만 필요하면 프로젝트 파일까지 확인해야 하므로 기본 권한은 full이다.
#   AGY_PERMISSION_MODE=prompt 로 낮추면 --dangerously-skip-permissions를 빼고 실행한다.
# - stdout은 그대로 보여주면서 .claude/memory/session-agy-review.md fallback에도 저장한다.
#   Codex는 이 파일을 읽어 Agy 응답을 같은 작업 흐름에 반영한다.
# - Agy 장기 세션 상태는 현재 HOME 아래 ~/.gemini/antigravity-cli에 저장된다.
#   Codex tool sandbox처럼 HOME 상태 디렉터리에 쓸 수 없는 환경에서는 실행하지 않고
#   같은 프로젝트 root에서 로컬 터미널 직접 실행 명령을 안내한다.
# - 파일 수정 여부는 prompt와 Agy 권한 요청에 맡긴다. read-only 검토는 prompt에 명시한다.

set -u

ROOT="${HARNESS_PROJECT_ROOT:-$(pwd)}"
TIMEOUT="${AGY_PRINT_TIMEOUT:-5m}"
PERMISSION_MODE="${AGY_PERMISSION_MODE:-full}"
AGY_STATE_DIR="${HOME:-}/.gemini/antigravity-cli"
AGY_HANDOFF_FILE="${AGY_HANDOFF_FILE:-.claude/memory/session-agy-review.md}" # fallback runtime handoff path

print_local_handoff() {
  echo "agy-review: Agy state dir is not writable: $AGY_STATE_DIR" >&2
  echo "agy-review: Codex tool sandbox에서 실행하면 log/conversation/cache/brain 저장이 깨질 수 있습니다." >&2
  echo "agy-review: 같은 프로젝트에 대해 Agy를 쓰려면 로컬 터미널에서 직접 실행하세요:" >&2
  printf '  cd %q\n' "$ROOT" >&2
  if [[ "$PROMPT" == *$'\n'* ]]; then
    echo "  printf '%s\n' '<prompt>' | bash .claude/scripts/agy-review.sh" >&2
  else
    printf '  bash .claude/scripts/agy-review.sh %q\n' "$PROMPT" >&2
  fi
  echo "agy-review: 로컬 실행 결과는 $AGY_HANDOFF_FILE 에 저장됩니다." >&2
}

agy_state_writable() {
  if [ -z "${HOME:-}" ]; then
    return 1
  fi
  mkdir -p "$AGY_STATE_DIR" 2>/dev/null || return 1
  local probe
  probe="$AGY_STATE_DIR/.agy-review-write-test.$$"
  touch "$probe" 2>/dev/null || return 1
  rm -f "$probe" 2>/dev/null || true
}

if [ $# -gt 0 ]; then
  PROMPT="$*"
elif [ -t 0 ]; then
  echo "usage: bash .claude/scripts/agy-review.sh \"<prompt>\"" >&2
  echo "       printf '%s\n' \"<prompt>\" | bash .claude/scripts/agy-review.sh" >&2
  exit 2
else
  PROMPT="$(cat)"
fi

if [ -z "$PROMPT" ]; then
  echo "agy-review: prompt is empty" >&2
  exit 2
fi

case "$PERMISSION_MODE" in
  full)
    AGY_PERMISSION_ARGS=(--dangerously-skip-permissions)
    AGY_PERMISSION_DISPLAY="--dangerously-skip-permissions "
    ;;
  prompt)
    AGY_PERMISSION_ARGS=()
    AGY_PERMISSION_DISPLAY=""
    ;;
  *)
    echo "agy-review: unsupported AGY_PERMISSION_MODE: $PERMISSION_MODE (use full or prompt)" >&2
    exit 2
    ;;
esac

if [ -n "${AGY_BIN:-}" ]; then
  AGY="$AGY_BIN"
elif command -v agy >/dev/null 2>&1; then
  AGY="$(command -v agy)"
elif [ -x "/Users/kann/.local/bin/agy" ]; then
  AGY="/Users/kann/.local/bin/agy"
else
  echo "agy-review: agy executable not found. Set AGY_BIN or install agy." >&2
  exit 127
fi

if [ ! -x "$AGY" ]; then
  echo "agy-review: AGY_BIN is not executable: $AGY" >&2
  exit 127
fi

if [ "${AGY_SKIP_STATE_CHECK:-}" != "1" ] && ! agy_state_writable; then
  print_local_handoff
  exit 73
fi

mkdir -p "$(dirname "$AGY_HANDOFF_FILE")"
{
  echo "# Agy review handoff"
  echo
  echo "- generated: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "- root: $ROOT"
  echo "- permission_mode: $PERMISSION_MODE"
  echo "- command: agy ${AGY_PERMISSION_DISPLAY}--add-dir <root> --print-timeout $TIMEOUT --print <prompt>"
  echo
  echo "## Prompt"
  echo
  printf '%s\n' "$PROMPT"
  echo
  echo "## Response"
  echo
} >"$AGY_HANDOFF_FILE"

if [ "$PERMISSION_MODE" = "full" ]; then
  "$AGY" "${AGY_PERMISSION_ARGS[@]}" --add-dir "$ROOT" --print-timeout "$TIMEOUT" --print "$PROMPT" | tee -a "$AGY_HANDOFF_FILE"
  STATUS=${PIPESTATUS[0]}
else
  "$AGY" --add-dir "$ROOT" --print-timeout "$TIMEOUT" --print "$PROMPT" | tee -a "$AGY_HANDOFF_FILE"
  STATUS=${PIPESTATUS[0]}
fi
echo "" >>"$AGY_HANDOFF_FILE"
echo "agy-review: handoff saved to $AGY_HANDOFF_FILE" >&2
exit "$STATUS"
