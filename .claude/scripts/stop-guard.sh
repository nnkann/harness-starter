#!/bin/bash
# Stop — 에이전트 응답 완료 시 실행. 미커밋 변경/WIP 상태를 경고.

# 1. 미커밋 변경 확인
uncommitted=$(git status --porcelain 2>/dev/null | wc -l)
if [ "$uncommitted" -gt 0 ]; then
  echo "⚠️ 미커밋 변경 ${uncommitted}개. 커밋 잊지 마." >&2
fi

# 2. in-progress WIP 문서 확인
if [ -d "docs/WIP" ]; then
  in_progress=0
  for f in docs/WIP/*.md; do
    [ -f "$f" ] || continue
    # 프론트매터에서 status 읽기 (fallback: 인라인 > status:)
    s=$(sed -n '/^---$/,/^---$/{ /^status:/{ s/status:[[:space:]]*//; p; q; } }' "$f" 2>/dev/null | tr -d '[:space:]')
    [ -z "$s" ] && s=$(grep -m1 '^> status:' "$f" 2>/dev/null | sed 's/> status: //' | tr -d ' ')
    if [ "$s" = "in-progress" ]; then
      in_progress=$((in_progress + 1))
    fi
  done
  if [ "$in_progress" -gt 0 ]; then
    echo "📋 in-progress 작업 ${in_progress}개 남아있음." >&2
  fi
fi

# 3. 컴팩션 카운터 리셋
rm -f .claude/.compact_count

exit 0
