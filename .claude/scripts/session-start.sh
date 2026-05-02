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
  # prior-session 신호용 — pre-commit-check이 이전 세션 잔여물 식별에 사용.
  # 다음 SessionStart에서 덮어쓰기. gitignore: session-*.txt 커버.
  git diff --name-only > .claude/memory/session-start-unstaged.txt 2>/dev/null || true
fi

# 2. docs/WIP/ 진행 중 작업 확인
# awk 1회로 파일 내 frontmatter(status·title) + 인라인 fallback 모두 처리.
# 기존: 파일당 sed 2회 + grep 2회 (~40ms/파일). 변경: 파일당 awk 1회 (~10ms).
if [ -d "docs/WIP" ] && [ "$(ls -A docs/WIP 2>/dev/null)" ]; then
  echo ""
  echo "📋 진행 중인 작업:"
  for f in docs/WIP/*.md; do
    [ -f "$f" ] || continue
    # awk: frontmatter 안의 status/title 우선, 없으면 본문 `> status:`·`# `로 fallback
    line=$(awk '
      BEGIN { in_fm=0; fm_done=0 }
      /^---$/ { if (in_fm) { in_fm=0; fm_done=1 } else if (!fm_done) in_fm=1; next }
      in_fm && /^status:/ { sub(/^status:[[:space:]]*/, ""); status=$0; next }
      in_fm && /^title:/  { sub(/^title:[[:space:]]*/, "");  title=$0;  next }
      fm_done && !status && /^> status:/ { sub(/^> status:[[:space:]]*/, ""); status=$0 }
      fm_done && !title  && /^# / { sub(/^# /, ""); title=$0 }
      END { printf "%s\t%s", status, title }
    ' "$f")
    status="${line%%$'\t'*}"
    title="${line#*$'\t'}"
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

# 4. TODO/FIXME 잔존 확인 (src/ 있을 때만 — 없으면 grep 자체 스킵)
if [ -d "src" ]; then
  todo_count=$(grep -rn "TODO\|FIXME\|HACK" src/ --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" --include="*.py" 2>/dev/null | wc -l)
  if [ "$todo_count" -gt 0 ]; then
    echo ""
    echo "⚠️ 코드에 TODO/FIXME/HACK $todo_count개 발견. docs/WIP/에 옮겨야 함."
  fi
fi

# 5. 좀비 프로세스 확인 (node·python 테스트 서버) — pgrep 1회로 통합
zombie_total=$(pgrep -f "(node|python).*test" 2>/dev/null | wc -l)
if [ "$zombie_total" -gt 0 ]; then
  echo ""
  echo "⚠️ 테스트 관련 좀비 프로세스 ${zombie_total}개 발견."
fi

# 6. 하네스 업그레이드 필요 여부 확인
# harness-upstream remote가 있는 프로젝트에서만 체크
if git remote | grep -qx harness-upstream 2>/dev/null; then
  if [ -f ".claude/HARNESS.json" ]; then
    INSTALLED_VER=$(grep -o '"version"[[:space:]]*:[[:space:]]*"[^"]*"' .claude/HARNESS.json 2>/dev/null | sed 's/.*"\([^"]*\)"$/\1/')
    LATEST_VER=$(git show harness-upstream/main:.claude/HARNESS.json 2>/dev/null | grep -o '"version"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"\([^"]*\)"$/\1/')
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

# 7. 연속 동일 파일 수정 감지 — 동일 파일이 2 커밋 연속 수정되면 debug-specialist 강제 호출
#
# 정밀화 (2026-05-02 자기증명): prefix 의존 폐기. fix·feat·refactor 무관하게
# 같은 파일이 연속 2회 수정됐다는 사실 자체가 "동일 영역 반복 수정" 신호.
# v0.29.2(feat:) + v0.30.0(feat:) 케이스에서 fix prefix 미발화 인지 후 확장.
#
# 본 트리거가 wip-sync 부분 매칭 false positive 같은 시스템 동작 이슈도
# 잡도록 — 사용자 키워드 의존(debug-guard.sh)과 보완.
if git rev-parse --is-inside-work-tree &>/dev/null; then
  files1=$(git diff-tree --no-commit-id -r --name-only HEAD 2>/dev/null)
  files2=$(git diff-tree --no-commit-id -r --name-only HEAD~1 2>/dev/null)
  if [ -n "$files1" ] && [ -n "$files2" ]; then
    # 메타 파일(버전 범프 결과)은 자연 동반 변경 — 신호 노이즈로 제외
    repeated=$(comm -12 <(echo "$files1" | sort) <(echo "$files2" | sort) \
      | grep -vE '^(\.claude/HARNESS\.json|README\.md|docs/harness/MIGRATIONS\.md|docs/clusters/.*\.md)$')
    if [ -n "$repeated" ]; then
      msg1=$(git log -1 --format="%s" 2>/dev/null)
      msg2=$(git log -2 --format="%s" 2>/dev/null | tail -1)
      echo ""
      echo "⛔ 연속 동일 파일 수정 감지: 아래 파일이 최근 2 커밋 연속 수정됐습니다." >&2
      echo ""
      echo "⛔ 연속 동일 파일 수정 감지: 아래 파일이 최근 2 커밋 연속 수정됐습니다."
      echo "  HEAD:   $msg1"
      echo "  HEAD~1: $msg2"
      echo "$repeated" | while read f; do echo "  - $f"; done
      echo ""
      echo "<important>"
      echo "동일 영역 반복 수정 = no-speculation.md \"동일 수정 2회 이상\" 트리거."
      echo "직접 수정 전 debug-specialist 에이전트를 즉시 호출하라."
      echo "Agent 도구로 subagent_type: \"debug-specialist\" 호출 — 호출 전에 증상·재현 조건·직전 수정 내용을 명시하라."
      echo ""
      echo "예외: 메타 파일(HARNESS.json·README.md·MIGRATIONS.md·clusters)은 이미 제외됨."
      echo "그 외에도 단순 docs 갱신·버전 범프 동반 변경이 명확하면 사용자에게 알리고 진행 가능."
      echo "</important>"
    fi
  fi
fi

# 8. 핵심 규칙 리마인드
echo ""
echo "═══ RULES ═══"
echo "1. 린터 에러 0에서만 커밋."
echo "2. 새 파일 생성 전 naming.md 확인."
echo "3. 새 함수 전 check-existing으로 중복 확인."
echo "4. 검증 없이 '완료'라고 말하지 마."
echo "═════════════"
