#!/bin/bash
# PostCompact — 압축 후 실행. 규칙을 재주입하고 현재 상태를 보여준다.

# 컴팩션 횟수 카운팅
COMPACT_FILE=".claude/.compact_count"
if [ -f "$COMPACT_FILE" ]; then
  count=$(cat "$COMPACT_FILE")
  count=$((count + 1))
else
  count=1
fi
echo "$count" > "$COMPACT_FILE"

echo "⚠️ COMPACTION #${count} — 컨텍스트 재주입"

# 1. 현재 작업 상태 복원
if [ -d "docs/WIP" ] && [ "$(ls -A docs/WIP 2>/dev/null)" ]; then
  echo ""
  echo "📋 진행 중인 작업:"
  for f in docs/WIP/*.md; do
    [ -f "$f" ] || continue
    # 프론트매터에서 status 읽기 (fallback: 인라인 > status:)
    status=$(sed -n '/^---$/,/^---$/{ /^status:/{ s/status:[[:space:]]*//; p; q; } }' "$f" 2>/dev/null)
    [ -z "$status" ] && status=$(grep -m1 '^> status:' "$f" 2>/dev/null | sed 's/> status: //')
    # 프론트매터에서 title 읽기 (fallback: 첫 # 제목)
    title=$(sed -n '/^---$/,/^---$/{ /^title:/{ s/title:[[:space:]]*//; p; q; } }' "$f" 2>/dev/null)
    [ -z "$title" ] && title=$(grep -m1 '^# ' "$f" 2>/dev/null | sed 's/^# //')
    echo "  - [$status] $title"

    # in-progress 문서의 결정 사항 재주입
    clean_status=$(echo "$status" | tr -d '[:space:]')
    if [ "$clean_status" = "in-progress" ]; then
      decisions=$(sed -n '/^## 결정 사항/,/^## /{ /^## /d; /^$/d; p; }' "$f" 2>/dev/null)
      if [ -n "$decisions" ] && [ "$decisions" != "(작업 중 기록)" ] && [ "$decisions" != "(작업하면서 채움)" ]; then
        echo "    📌 결정 사항:"
        echo "$decisions" | head -5 | while read line; do
          echo "      $line"
        done
      fi
    fi
  done
else
  echo ""
  echo "📋 진행 중인 작업: 없음"
fi

# 2. staged 변경 상태 복원
staged=$(git diff --cached --stat 2>/dev/null)
if [ -n "$staged" ]; then
  echo ""
  echo "📦 Staged 변경:"
  echo "$staged" | tail -1 | sed 's/^/  /'
fi

# 3. TODO 진행률
todo_total=0
todo_done=0
if [ -d "docs/WIP" ]; then
  for f in docs/WIP/*.md; do
    [ -f "$f" ] || continue
    s=$(sed -n '/^---$/,/^---$/{ /^status:/{ s/status:[[:space:]]*//; p; q; } }' "$f" 2>/dev/null | tr -d '[:space:]')
    [ -z "$s" ] && s=$(grep -m1 '^> status:' "$f" 2>/dev/null | sed 's/> status: //' | tr -d ' ')
    todo_total=$((todo_total + 1))
    if [ "$s" = "completed" ] || [ "$s" = "abandoned" ]; then
      todo_done=$((todo_done + 1))
    fi
  done
  if [ "$todo_total" -gt 0 ]; then
    echo ""
    echo "📊 WIP 진행률: ${todo_done}/${todo_total} 완료"
  fi
fi

# 4. 컴팩션 경고 (3회 이상)
if [ "$count" -ge 3 ]; then
  echo ""
  echo "⚠️ 컴팩션 ${count}회. 작업이 너무 큼. 커밋 후 분할을 고려하라."
fi

# 5. 규칙 재주입
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
