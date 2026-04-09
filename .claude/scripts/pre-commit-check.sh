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

# 2. 린터 검사 (CLAUDE.md의 패키지 매니저 설정을 읽어서 동적 결정)
LINT_CMD=""
PKG_MGR=""

# CLAUDE.md에서 패키지 매니저 읽기
if [ -f "CLAUDE.md" ]; then
  PKG_MGR=$(grep -m1 '패키지 매니저:' CLAUDE.md 2>/dev/null | sed 's/.*패키지 매니저:[[:space:]]*//' | tr -d ' ')
fi

# 패키지 매니저 기반 lint 명령 결정
case "$PKG_MGR" in
  npm)  [ -f "package.json" ] && grep -q '"lint"' package.json 2>/dev/null && LINT_CMD="npm run lint --silent" ;;
  pnpm) [ -f "package.json" ] && grep -q '"lint"' package.json 2>/dev/null && LINT_CMD="pnpm lint" ;;
  yarn) [ -f "package.json" ] && grep -q '"lint"' package.json 2>/dev/null && LINT_CMD="yarn lint" ;;
  bun)  [ -f "package.json" ] && grep -q '"lint"' package.json 2>/dev/null && LINT_CMD="bun run lint" ;;
  pip|poetry|uv)
    if command -v ruff &>/dev/null; then
      LINT_CMD="ruff check . --quiet"
    fi
    ;;
  *)
    # 패키지 매니저 미설정 시 자동 감지 (기존 방식)
    if [ -f "package.json" ] && grep -q '"lint"' package.json 2>/dev/null; then
      if [ -f "pnpm-lock.yaml" ]; then LINT_CMD="pnpm lint"
      elif [ -f "yarn.lock" ]; then LINT_CMD="yarn lint"
      elif [ -f "bun.lockb" ]; then LINT_CMD="bun run lint"
      else LINT_CMD="npm run lint --silent"
      fi
    elif [ -f "pyproject.toml" ] && command -v ruff &>/dev/null; then
      LINT_CMD="ruff check . --quiet"
    fi
    ;;
esac

if [ -n "$LINT_CMD" ]; then
  $LINT_CMD 2>/dev/null
  if [ $? -ne 0 ]; then
    echo "❌ 린터 에러. 에러 0에서만 커밋 가능. (실행: $LINT_CMD)"
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
