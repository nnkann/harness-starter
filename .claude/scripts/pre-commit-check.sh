#!/bin/bash
# 커밋 전 검사. 실패하면 exit 2로 커밋 차단.
ERRORS=0

# 1. TODO/FIXME/HACK 검사 (staged 파일만)
todo_files=$(git diff --cached --name-only | xargs grep -l "TODO\|FIXME\|HACK" 2>/dev/null)
if [ -n "$todo_files" ]; then
  echo "❌ TODO/FIXME/HACK 발견. 코드가 아니라 docs/WIP/에 기록하라."
  echo "$todo_files" | while read f; do
    echo "   $f"
  done
  ERRORS=$((ERRORS + 1))
fi

# 2. 린터 검사 (프로젝트에 린터가 있을 때만)
if [ -f "package.json" ] && grep -q '"lint"' package.json 2>/dev/null; then
  npm run lint --silent 2>/dev/null
  if [ $? -ne 0 ]; then
    echo "❌ 린터 에러. 에러 0에서만 커밋 가능."
    ERRORS=$((ERRORS + 1))
  fi
elif [ -f "pyproject.toml" ] && command -v ruff &>/dev/null; then
  ruff check . --quiet 2>/dev/null
  if [ $? -ne 0 ]; then
    echo "❌ 린터 에러. 에러 0에서만 커밋 가능."
    ERRORS=$((ERRORS + 1))
  fi
fi

# 3. tests/ 밖에 테스트 파일 있는지 검사
test_outside=$(git diff --cached --name-only | grep -E '\.test\.|\.spec\.|_test\.' | grep -v '^tests/' | grep -v '^__tests__/')
if [ -n "$test_outside" ]; then
  echo "❌ 테스트 파일이 tests/ 밖에 있음:"
  echo "$test_outside" | while read f; do
    echo "   $f"
  done
  ERRORS=$((ERRORS + 1))
fi

# 4. docs/WIP/에 completed/abandoned 파일이 남아있는지
if [ -d "docs/WIP" ]; then
  stale=$(grep -rl '> status: completed\|> status: abandoned' docs/WIP/ 2>/dev/null)
  if [ -n "$stale" ]; then
    echo "⚠️ docs/WIP/에 완료/중단 문서가 남아있음. 이동 필요:"
    echo "$stale" | while read f; do
      echo "   $(basename "$f")"
    done
  fi
fi

# 결과
if [ $ERRORS -gt 0 ]; then
  echo ""
  echo "🚫 커밋 차단. 위 문제를 해결하라."
  exit 2
fi
