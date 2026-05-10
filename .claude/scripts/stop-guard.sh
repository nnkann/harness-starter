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

# 2.5. P8 Phase 3 — Stop hook 조건 A·B·C AND 발화 (Soft + Dry-run)
# A: git status 수정 파일 있음 (uncommitted > 0)
# B: 변경된 WIP 중 status: in-progress 있음
# C: 그 WIP에 빈 체크박스 `- [ ]` 또는 BIT 판단 블록 부재
# 모두 hit 시 stderr 1줄 + .claude/memory/stop_hook_audit.log append.
# 차단 아님 — 측정용. Phase 4에서 Hard Stop 도입 결정 근거.
if [ "${uncommitted:-0}" -gt 0 ] && [ -d "docs/WIP" ]; then
  changed_wip=$(git status --porcelain 2>/dev/null | awk '{print $2}' | grep '^docs/WIP/.*\.md$' || true)
  if [ -n "$changed_wip" ]; then
    risk_files=""
    while IFS= read -r f; do
      [ -z "$f" ] && continue
      [ -f "$f" ] || continue
      # status: in-progress 확인
      is_inprog=$(awk '
        /^---$/ { if (in_fm) { exit } else { in_fm=1; next } }
        in_fm && /^status:[[:space:]]*in-progress/ { print "1"; exit }
      ' "$f")
      [ "$is_inprog" != "1" ] && continue
      # 빈 체크박스 또는 BIT 블록 부재 확인 (grep -c | head -1로 단일 정수 보장)
      empty_box=$(grep -c '^[[:space:]]*-[[:space:]]*\[[[:space:]]\]' "$f" 2>/dev/null | head -1)
      has_bit=$(grep -c '^\[BIT 판단\]' "$f" 2>/dev/null | head -1)
      empty_box=${empty_box:-0}
      has_bit=${has_bit:-0}
      if [ "$empty_box" -gt 0 ] 2>/dev/null || [ "$has_bit" -eq 0 ] 2>/dev/null; then
        risk_files="${risk_files}${f} "
      fi
    done <<< "$changed_wip"
    if [ -n "$risk_files" ]; then
      ts=$(date '+%Y-%m-%dT%H:%M:%S')
      echo "🛑 [stop-guard A·B·C] 미커밋 in-progress WIP에 미완료 신호 — ${risk_files}" >&2
      mkdir -p .claude/memory
      echo "${ts} | A·B·C hit | ${risk_files}" >> .claude/memory/stop_hook_audit.log
    fi
  fi
fi

# 3. memory 저장 환기 (강제 아님. /clear 전 사용자 눈으로 판단)
if [ -d ".claude/memory" ]; then
  echo "💭 이번 세션에서 memory에 저장할 feedback·project 있나? (/clear 전 확인)" >&2
fi

# 4. 컴팩션 카운터 리셋
rm -f .claude/.compact_count

exit 0
