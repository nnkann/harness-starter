#!/bin/bash
# PreToolUse (Write) — 새 파일 생성 시 중복 확인 + naming 규칙 안내.
# stdin으로 JSON이 들어온다.

INPUT=$(cat)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)

# 파일이 없으면 종료
[ -z "$FILE" ] && exit 0

# 기존 파일 수정이면 통과 (새 파일 생성만 검사)
[ -f "$FILE" ] && exit 0

# src/ 하위 새 파일이면 중복 확인 안내
case "$FILE" in
  src/*|app/*|lib/*|packages/*)
    echo "📌 새 소스 파일 생성 감지: $FILE" >&2
    echo "   → LSP + Grep으로 중복 확인 했는가?" >&2
    echo "   → naming.md 규칙에 맞는 파일명인가?" >&2
    ;;
esac

# snake_case 파일명 검사 (docs, config 등 제외)
BASENAME=$(basename "$FILE")
BASENAME_NO_EXT="${BASENAME%.*}"

# 대문자가 포함된 소스 파일이면 경고
case "$FILE" in
  *.ts|*.tsx|*.js|*.jsx|*.py)
    if echo "$BASENAME_NO_EXT" | grep -q '[A-Z]'; then
      # 컴포넌트 파일 (PascalCase 허용 가능)은 제외
      case "$BASENAME_NO_EXT" in
        [A-Z]*)
          echo "⚠️ PascalCase 파일명: $BASENAME — 컴포넌트 파일이 맞는지 확인." >&2
          ;;
      esac
    fi
    ;;
esac

exit 0
