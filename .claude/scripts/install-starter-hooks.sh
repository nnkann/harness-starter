#!/bin/bash
# harness-starter 전용 git hook 설치.
# is_starter: true인 repo에서만 의미 있음.
# harness-sync Step 5 또는 수동으로 실행.

set -e

HOOK_FILE=".git/hooks/pre-commit"

# is_starter 확인
IS_STARTER=$(grep -o '"is_starter":[[:space:]]*true' .claude/HARNESS.json 2>/dev/null)
if [ -z "$IS_STARTER" ]; then
  echo "is_starter: false — starter hook 설치 스킵" >&2
  exit 0
fi

cat > "$HOOK_FILE" << 'HOOK'
#!/bin/bash
# 하네스 스타터 보호: HARNESS_DEV=1 없으면 커밋 차단
if [ "$HARNESS_DEV" != "1" ]; then
  echo ""
  echo "🚫 이 repo는 하네스 스타터(템플릿)입니다."
  echo "   직접 커밋할 수 없습니다."
  echo ""
  echo "   하네스 개발이 목적이라면:"
  echo "     HARNESS_DEV=1 git commit ..."
  echo ""
  exit 1
fi

# 버전 범프 체크 (sub-커밋은 스킵 — 부모 커밋에서 이미 판정)
if [ "$HARNESS_SPLIT_SUB" != "1" ]; then
  BUMP_OUTPUT=$(python3 .claude/scripts/harness_version_bump.py 2>/dev/null)
  BUMP_TYPE=$(echo "$BUMP_OUTPUT" | grep "^version_bump:" | cut -d' ' -f2)
  if [ "$BUMP_TYPE" = "patch" ] || [ "$BUMP_TYPE" = "minor" ]; then
    NEXT_VER=$(echo "$BUMP_OUTPUT" | grep "^next_version:" | cut -d' ' -f2)
    echo ""
    echo "⚠️  버전 범프 누락: $BUMP_TYPE 필요 (→ $NEXT_VER)"
    echo "   HARNESS.json version 갱신 후 git add .claude/HARNESS.json 하고 재커밋."
    echo ""
    exit 1
  fi
fi
HOOK

chmod +x "$HOOK_FILE"
echo "✅ starter pre-commit hook 설치됨: $HOOK_FILE"
