#!/bin/bash
# Stop — 에이전트 응답 완료 시 실행. 미커밋 변경/WIP 상태를 경고.

# 1. 미커밋 변경 확인
uncommitted=$(git status --porcelain 2>/dev/null | wc -l)
if [ "$uncommitted" -gt 0 ]; then
  echo "⚠️ 미커밋 변경 ${uncommitted}개. 커밋 잊지 마." >&2
fi

# 2. in-progress WIP 문서 확인
# awk 1회로 모든 WIP 파일의 in-progress 카운트 (파일당 sed+grep → awk)
if [ -d "docs/WIP" ]; then
  in_progress=$(awk '
    FNR==1 { in_fm=0; fm_done=0; found=0 }
    /^---$/ { if (in_fm) { in_fm=0; fm_done=1 } else if (!fm_done) in_fm=1; next }
    in_fm && /^status:[[:space:]]*in-progress/ { count++; found=1; nextfile }
    fm_done && !found && /^> status:[[:space:]]*in-progress/ { count++; nextfile }
    END { print count+0 }
  ' docs/WIP/*.md 2>/dev/null)
  if [ "${in_progress:-0}" -gt 0 ]; then
    echo "📋 in-progress 작업 ${in_progress}개 남아있음." >&2
  fi
fi

# 3. 컴팩션 카운터 리셋
rm -f .claude/.compact_count

exit 0
