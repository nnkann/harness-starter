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
# 버전 범프 체크는 pre_commit_check.py가 담당 (commit Step 4에서 Claude가 판단·갱신)
HOOK

chmod +x "$HOOK_FILE"
echo "✅ starter pre-commit hook 설치됨: $HOOK_FILE"
