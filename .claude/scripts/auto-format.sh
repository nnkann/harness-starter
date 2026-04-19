#!/bin/bash
# PostToolUse (Write|Edit|MultiEdit) — 파일 저장 후 자동 포맷
# stdin으로 JSON이 들어온다. file_path를 추출해서 포맷.

INPUT=$(cat)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.file // empty' 2>/dev/null)

# 파일이 없으면 종료
[ -z "$FILE" ] && exit 0
[ ! -f "$FILE" ] && exit 0

# 확장자별 포매터 실행
EXT="${FILE##*.}"

case "$EXT" in
  ts|tsx|js|jsx|json|css|scss|html|md)
    if command -v npx &>/dev/null && [ -f "node_modules/.bin/prettier" ]; then
      npx prettier --write "$FILE" 2>/dev/null
    fi
    ;;
  py)
    if command -v ruff &>/dev/null; then
      ruff format "$FILE" 2>/dev/null
    elif command -v black &>/dev/null; then
      black --quiet "$FILE" 2>/dev/null
    fi
    ;;
esac

# settings.json 수정 직후 사전 검증 — Claude Code 재로드 시 schema 에러로
# 20k 토큰 덤프 방지. 실측 사례: 본 세션에 에러 2회 발생해 40k 허비.
case "$FILE" in
  */.claude/settings.json|.claude/settings.json)
    if [ -f ".claude/scripts/validate-settings.sh" ]; then
      if ! bash .claude/scripts/validate-settings.sh "$FILE" >/dev/null 2>&1; then
        # 에러 상세는 stderr로 (사용자에게 노출)
        echo "⚠️ settings.json 검증 실패 — Claude Code 재로드 전 수정 필요:" >&2
        bash .claude/scripts/validate-settings.sh "$FILE" 2>&1 | sed 's/^/   /' >&2
      fi
    fi
    ;;
esac

exit 0
