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

exit 0
