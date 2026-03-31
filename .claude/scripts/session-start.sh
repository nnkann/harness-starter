#!/bin/bash
# 세션 시작 시 프로젝트 상태를 실제로 확인한다.

echo "═══ SESSION START ═══"

# 1. docs/wip/ 진행 중 작업 확인
if [ -d "docs/wip" ] && [ "$(ls -A docs/wip 2>/dev/null)" ]; then
  echo ""
  echo "📋 진행 중인 작업:"
  for f in docs/wip/*.md; do
    [ -f "$f" ] || continue
    status=$(grep -m1 '^> status:' "$f" 2>/dev/null | sed 's/> status: //')
    title=$(grep -m1 '^# ' "$f" 2>/dev/null | sed 's/^# //')
    echo "  - [$status] $title ($(basename "$f"))"
  done
else
  echo ""
  echo "📋 진행 중인 작업: 없음"
fi

# 2. TODO/FIXME 잔존 확인
todo_count=$(grep -rn "TODO\|FIXME\|HACK" src/ --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" --include="*.py" 2>/dev/null | wc -l)
if [ "$todo_count" -gt 0 ]; then
  echo ""
  echo "⚠️ 코드에 TODO/FIXME/HACK $todo_count개 발견. docs/wip/에 옮겨야 함."
fi

# 3. 좀비 프로세스 확인 (node, python 테스트 서버 등)
zombie_node=$(pgrep -f "node.*test" 2>/dev/null | wc -l)
zombie_python=$(pgrep -f "python.*test" 2>/dev/null | wc -l)
zombie_total=$((zombie_node + zombie_python))
if [ "$zombie_total" -gt 0 ]; then
  echo ""
  echo "⚠️ 테스트 관련 좀비 프로세스 ${zombie_total}개 발견."
fi

# 4. 핵심 규칙 리마인드
echo ""
echo "═══ RULES ═══"
echo "1. 린터 에러 0에서만 커밋."
echo "2. 새 파일 생성 전 naming.md 확인."
echo "3. 새 함수 전 check-existing으로 중복 확인."
echo "4. 검증 없이 '완료'라고 말하지 마."
echo "═════════════"
