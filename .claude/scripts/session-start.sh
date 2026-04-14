#!/bin/bash
# 세션 시작 시 프로젝트 상태를 실제로 확인한다.

echo "═══ SESSION START ═══"

# 1. Git 상태 요약
if git rev-parse --is-inside-work-tree &>/dev/null; then
  echo ""
  echo "🔀 Git 상태:"
  # 최근 커밋 3개
  echo "  최근 커밋:"
  git log --oneline -3 2>/dev/null | while read line; do
    echo "    $line"
  done
  # 마지막 커밋 경과 시간
  last_commit=$(git log -1 --format="%ar" 2>/dev/null)
  if [ -n "$last_commit" ]; then
    echo "  마지막 커밋: $last_commit"
  fi
  # uncommitted 변경 요약
  changes=$(git diff --stat 2>/dev/null)
  staged=$(git diff --cached --stat 2>/dev/null)
  if [ -n "$changes" ] || [ -n "$staged" ]; then
    echo "  미커밋 변경:"
    [ -n "$staged" ] && echo "    [staged]" && echo "$staged" | tail -1 | sed 's/^/    /'
    [ -n "$changes" ] && echo "    [unstaged]" && echo "$changes" | tail -1 | sed 's/^/    /'
  fi
fi

# 2. docs/WIP/ 진행 중 작업 확인
if [ -d "docs/WIP" ] && [ "$(ls -A docs/WIP 2>/dev/null)" ]; then
  echo ""
  echo "📋 진행 중인 작업:"
  for f in docs/WIP/*.md; do
    [ -f "$f" ] || continue
    status=$(grep -m1 '^> status:' "$f" 2>/dev/null | sed 's/> status: //')
    title=$(grep -m1 '^# ' "$f" 2>/dev/null | sed 's/^# //')
    echo "  - [$status] $title ($(basename "$f"))"
  done
else
  echo ""
  echo "📋 진행 중인 작업: 없음"
fi

# 3. Memory 상태 확인
if [ -f ".claude/memory/MEMORY.md" ]; then
  mem_count=$(grep -c '^\- ' .claude/memory/MEMORY.md 2>/dev/null || echo 0)
  echo ""
  echo "🧠 메모리: ${mem_count}개 항목 로드됨"
fi

# 4. TODO/FIXME 잔존 확인
todo_count=$(grep -rn "TODO\|FIXME\|HACK" src/ --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" --include="*.py" 2>/dev/null | wc -l)
if [ "$todo_count" -gt 0 ]; then
  echo ""
  echo "⚠️ 코드에 TODO/FIXME/HACK $todo_count개 발견. docs/WIP/에 옮겨야 함."
fi

# 5. 좀비 프로세스 확인 (node, python 테스트 서버 등)
zombie_node=$(pgrep -f "node.*test" 2>/dev/null | wc -l)
zombie_python=$(pgrep -f "python.*test" 2>/dev/null | wc -l)
zombie_total=$((zombie_node + zombie_python))
if [ "$zombie_total" -gt 0 ]; then
  echo ""
  echo "⚠️ 테스트 관련 좀비 프로세스 ${zombie_total}개 발견."
fi

# 6. 하네스 업그레이드 필요 여부 확인
# harness-upstream remote가 있는 프로젝트에서만 체크
if git remote | grep -qx harness-upstream 2>/dev/null; then
  if [ -f ".claude/harness.json" ] && [ -f ".claude/HARNESS_VERSION" ]; then
    INSTALLED_VER=$(grep -o '"version"[[:space:]]*:[[:space:]]*"[^"]*"' .claude/harness.json 2>/dev/null | sed 's/.*"\([^"]*\)"$/\1/')
    LATEST_VER=$(cat .claude/HARNESS_VERSION 2>/dev/null | tr -d '[:space:]')
    if [ -n "$INSTALLED_VER" ] && [ -n "$LATEST_VER" ] && [ "$INSTALLED_VER" != "$LATEST_VER" ]; then
      echo ""
      echo "╔════════════════════════════════════════════════════════════╗"
      echo "║  🔄 하네스 업그레이드 가능: ${INSTALLED_VER} → ${LATEST_VER}  ║"
      echo "║                                                            ║"
      echo "║  harness-starter에서 실행:                                ║"
      echo "║    bash h-setup.sh --upgrade $(pwd)"
      echo "╚════════════════════════════════════════════════════════════╝"
    fi
  fi
  # .upgrade/ 디렉토리가 남아있으면 미완료 업그레이드 경고
  if [ -d ".claude/.upgrade" ] && [ -f ".claude/.upgrade/UPGRADE_REPORT.md" ]; then
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║  ⚠️  미완료 업그레이드 감지                               ║"
    echo "║                                                            ║"
    echo "║  .claude/.upgrade/에 스테이징된 파일이 있습니다.          ║"
    echo "║  'harness-upgrade 스킬을 실행해줘' 로 병합하세요.        ║"
    echo "╚════════════════════════════════════════════════════════════╝"
  fi
fi

# 7. 핵심 규칙 리마인드
echo ""
echo "═══ RULES ═══"
echo "1. 린터 에러 0에서만 커밋."
echo "2. 새 파일 생성 전 naming.md 확인."
echo "3. 새 함수 전 check-existing으로 중복 확인."
echo "4. 검증 없이 '완료'라고 말하지 마."
echo "═════════════"
