#!/bin/bash
# PostCompact — 압축 후 실행. 규칙을 재주입하고 현재 상태를 보여준다.

echo "⚠️ COMPACTION COMPLETE — 컨텍스트 재주입"

# 1. 현재 작업 상태 복원
if [ -d "docs/wip" ] && [ "$(ls -A docs/wip 2>/dev/null)" ]; then
  echo ""
  echo "📋 진행 중인 작업:"
  for f in docs/wip/*.md; do
    [ -f "$f" ] || continue
    status=$(grep -m1 '^> status:' "$f" 2>/dev/null | sed 's/> status: //')
    title=$(grep -m1 '^# ' "$f" 2>/dev/null | sed 's/^# //')
    echo "  - [$status] $title"
  done
fi

# 2. 규칙 재주입
echo ""
echo "═══ RULES ═══"
echo "1. 린터 에러 0에서만 커밋."
echo "2. 새 파일 생성 전 naming.md 확인."
echo "3. 새 함수 전 check-existing으로 중복 확인."
echo "4. 테스트는 tests/ 폴더에만."
echo "5. 문서는 docs/ 하위에만."
echo "6. grep 대신 LSP 우선."
echo "7. 검증 없이 '완료'라고 말하지 마."
echo "═════════════"
