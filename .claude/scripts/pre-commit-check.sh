#!/bin/bash
# 커밋 전 검사. 실패하면 exit 2로 커밋 차단.
ERRORS=0

# 1. TODO/FIXME/HACK 검사 (staged 파일만)
todo_files=$(git diff --cached --name-only | xargs grep -l "TODO\|FIXME\|HACK" 2>/dev/null)
if [ -n "$todo_files" ]; then
  echo "❌ TODO/FIXME/HACK 발견. 코드가 아니라 docs/WIP/에 기록하라." >&2
  echo "$todo_files" | while read f; do
    echo "   $f" >&2
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
    echo "❌ 린터 에러. 에러 0에서만 커밋 가능. (실행: $LINT_CMD)" >&2
    ERRORS=$((ERRORS + 1))
  fi
fi

# 3. tests/ 밖에 테스트 파일 있는지 검사
test_outside=$(git diff --cached --name-only | grep -E '\.test\.|\.spec\.|_test\.' | grep -v '^tests/' | grep -v '^__tests__/')
if [ -n "$test_outside" ]; then
  echo "❌ 테스트 파일이 tests/ 밖에 있음:" >&2
  echo "$test_outside" | while read f; do
    echo "   $f" >&2
  done
  ERRORS=$((ERRORS + 1))
fi

# 4. docs/WIP/에 completed/abandoned 파일이 남아있는지
if [ -d "docs/WIP" ]; then
  # 프론트매터 또는 인라인 status에서 completed/abandoned 감지
  stale=$(grep -rl '^status:.*\(completed\|abandoned\)\|^> status:.*\(completed\|abandoned\)' docs/WIP/ 2>/dev/null)
  if [ -n "$stale" ]; then
    echo "⚠️ docs/WIP/에 완료/중단 문서가 남아있음. 이동 필요:" >&2
    echo "$stale" | while read f; do
      echo "   $(basename "$f")" >&2
    done
  fi
fi

# 5. 위험도 기반 리뷰 게이트 (light 모드일 때만)
HARNESS_LEVEL=""
if [ -f "CLAUDE.md" ]; then
  HARNESS_LEVEL=$(grep -m1 '하네스 강도:' CLAUDE.md 2>/dev/null | sed 's/.*하네스 강도:[[:space:]]*//' | tr -d ' ')
fi

if [ "$HARNESS_LEVEL" = "light" ]; then
  RISK_REASONS=""

  # 5a. 변경 파일 수 5개 이상
  CHANGED_COUNT=$(git diff --cached --name-only | wc -l | tr -d ' ')
  if [ "$CHANGED_COUNT" -ge 5 ]; then
    RISK_REASONS="${RISK_REASONS}\n   - 변경 파일 ${CHANGED_COUNT}개 (≥5)"
  fi

  # 5b. 삭제 라인 50줄 이상
  DELETED_LINES=$(git diff --cached --numstat | awk '{s+=$2} END {print s+0}')
  if [ "$DELETED_LINES" -ge 50 ]; then
    RISK_REASONS="${RISK_REASONS}\n   - 삭제 ${DELETED_LINES}줄 (≥50)"
  fi

  # 5c. 핵심 설정 파일 변경
  CORE_FILES=$(git diff --cached --name-only | grep -E '^(CLAUDE\.md|\.claude/settings\.json|\.claude/rules/|\.claude/scripts/)' 2>/dev/null)
  if [ -n "$CORE_FILES" ]; then
    RISK_REASONS="${RISK_REASONS}\n   - 핵심 설정 파일 변경"
  fi

  # 5d. 보안 관련 패턴
  SEC_MATCH=$(git diff --cached --name-only | grep -iE 'auth|token|secret|key|credential|password' 2>/dev/null)
  if [ -z "$SEC_MATCH" ]; then
    SEC_MATCH=$(git diff --cached -U0 | grep -iE '^\+.*(auth|token|secret|key|credential|password)' 2>/dev/null | head -1)
  fi
  if [ -n "$SEC_MATCH" ]; then
    RISK_REASONS="${RISK_REASONS}\n   - 보안 관련 패턴 감지"
  fi

  # 5e. 인프라/배포 파일
  INFRA_FILES=$(git diff --cached --name-only | grep -iE '(Dockerfile|docker-compose|\.github/workflows/|\.gitlab-ci|deploy)' 2>/dev/null)
  if [ -n "$INFRA_FILES" ]; then
    RISK_REASONS="${RISK_REASONS}\n   - 인프라/배포 파일 변경"
  fi

  # 5f. 단일 파일에서 추가+삭제 동시 30줄 이상
  COMPLEX=$(git diff --cached --numstat | awk '$1+0 >= 30 && $2+0 >= 30 {print $3}')
  if [ -n "$COMPLEX" ]; then
    RISK_REASONS="${RISK_REASONS}\n   - 구조적 수정 감지: $(echo "$COMPLEX" | head -1)"
  fi

  if [ -n "$RISK_REASONS" ]; then
    echo "" >&2
    echo "⚡ 위험도 감지 — 리뷰 에이전트가 자동 실행됩니다:" >&2
    echo -e "$RISK_REASONS" >&2
    echo "" >&2
  fi
fi

# 결과
if [ $ERRORS -gt 0 ]; then
  echo "" >&2
  echo "🚫 커밋 차단. 위 문제를 해결하라." >&2
  exit 2
fi
