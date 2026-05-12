#!/bin/bash
# split-commit.sh — 커밋 분리 plan 출력/실행 (audit #18, 1 커밋 = 1 논리 단위).
#
# 동작 모드 (sub-task 3 — 2026-05-13 비파괴화):
#   기본 (인자 없음)  : plan 출력만. staged 변경 없음. exit 0
#   --apply           : 기존 destructive 동작. staged 비우고 첫 그룹 stage.
#   split-plan.txt 존재: 자동으로 --apply 의도 (다음 그룹 stage)
#
# 사용법:
#   bash .claude/scripts/split-commit.sh           # plan만
#   bash .claude/scripts/split-commit.sh --apply   # 실제 분리 실행
#
# SSOT: docs/WIP/harness--hn_commit_perf_optimization.md "C. split 정책 재정의".
# 호출 측은 commit/SKILL.md Step 5.5. 사용자 명시 동의 없으면 --apply 금지.
#
# 종료 코드:
#   0 정상 (plan 출력 또는 apply 완료)
#   1 오류
#   2 분리 불필요 (split_action_recommended != split)

set -e

SPLIT_PLAN=".claude/memory/split-plan.txt"
APPLY=0

# 인자 파싱
for arg in "$@"; do
  case "$arg" in
    --apply) APPLY=1 ;;
    --help|-h)
      echo "Usage: $0 [--apply]"
      echo "  기본은 plan 출력만 (비파괴). --apply 명시 시에만 staged 변경."
      exit 0
      ;;
  esac
done

# 0. split-plan.txt가 있으면 다음 그룹 자동 stage (재계산 없이, 자동 apply 의도)
if [ -f "$SPLIT_PLAN" ]; then
  NEXT_LINE=$(grep -v '^#' "$SPLIT_PLAN" | head -1)
  if [ -n "$NEXT_LINE" ]; then
    NEXT_NAME=$(echo "$NEXT_LINE" | cut -f1)
    NEXT_FILES=$(echo "$NEXT_LINE" | cut -f2)

    echo "split-plan.txt에서 다음 그룹 로드: $NEXT_NAME"
    git reset HEAD -- . > /dev/null 2>&1 || true
    echo "$NEXT_FILES" | tr ',' '\n' | while IFS= read -r f; do
      [ -z "$f" ] && continue
      if [ -e "$f" ]; then git add -- "$f"; else git rm -q -- "$f" 2>/dev/null || true; fi
    done

    REMAINING=$(grep -v '^#' "$SPLIT_PLAN" | tail -n +2)
    if [ -z "$REMAINING" ]; then
      rm -f "$SPLIT_PLAN"
      echo "✅ '$NEXT_NAME' staged 완료 (마지막 그룹)."
    else
      {
        head -2 "$SPLIT_PLAN"
        echo "$REMAINING"
      } > "${SPLIT_PLAN}.tmp" && mv "${SPLIT_PLAN}.tmp" "$SPLIT_PLAN"
      echo "✅ '$NEXT_NAME' staged 완료. 남은 그룹: $(echo "$REMAINING" | wc -l)개"
    fi
    exit 0
  fi
  rm -f "$SPLIT_PLAN"
fi

# 1. pre-check 실행
PRE_OUT=$(python3 "$(dirname "$0")/pre_commit_check.py" 2>/dev/null)
PRE_EXIT=$?
if [ "$PRE_EXIT" -ne 0 ]; then
  echo "❌ pre-check 실패. 먼저 해결하라." >&2
  exit 1
fi

ACTION=$(echo "$PRE_OUT" | awk -F': ' '/^split_action_recommended:/{print $2; exit}')
if [ "$ACTION" != "split" ]; then
  echo "분리 불필요 (split_action_recommended: $ACTION)" >&2
  exit 2
fi

# 2. 그룹 정보 추출
GROUP_DATA=$(echo "$PRE_OUT" | awk '
  /^split_group_[0-9]+_name: / {
    sub(/^split_group_/, "")
    idx=$0; sub(/_name: .*/, "", idx)
    name=$0; sub(/^[0-9]+_name: /, "", name)
    names[idx]=name
  }
  /^split_group_[0-9]+_files: / {
    sub(/^split_group_/, "")
    idx=$0; sub(/_files: .*/, "", idx)
    files=$0; sub(/^[0-9]+_files: /, "", files)
    filelists[idx]=files
  }
  END {
    for (i=1; i in names; i++) {
      printf "%s\t%s\n", names[i], filelists[i]
    }
  }
')

if [ -z "$GROUP_DATA" ]; then
  echo "❌ pre-check이 split_group_* 정보를 반환 안 함." >&2
  exit 1
fi

GROUP_COUNT=$(echo "$GROUP_DATA" | wc -l)

echo ""
echo "=== 커밋 분리 계획 (audit #18) ==="
echo "그룹 수: $GROUP_COUNT"
echo ""
idx=1
while IFS=$'\t' read -r name files; do
  [ -z "$name" ] && continue
  file_count=$(echo "$files" | tr ',' '\n' | wc -l)
  echo "  [$idx] $name ($file_count 파일)"
  echo "$files" | tr ',' '\n' | sed 's/^/       /'
  idx=$((idx + 1))
done <<< "$GROUP_DATA"

echo ""

# 3. APPLY 안 함 → plan만 출력하고 종료 (비파괴, sub-task 3)
if [ "$APPLY" -ne 1 ]; then
  echo "ℹ️  plan만 출력 (staged 변경 없음). 실제 분리는 --apply 옵션 필요."
  echo "   사용자 명시 동의 후: bash .claude/scripts/split-commit.sh --apply"
  exit 0
fi

# 4. --apply: destructive 흐름
echo "현재 전체 staged 상태를 초기화하고 첫 그룹만 다시 stage합니다."
echo "각 그룹별 커밋은 HARNESS_SPLIT_SUB=1 환경에서 Claude가 개별 수행."
echo ""

git reset HEAD -- . > /dev/null 2>&1 || true

FIRST_NAME=$(echo "$GROUP_DATA" | head -1 | cut -f1)
FIRST_FILES=$(echo "$GROUP_DATA" | head -1 | cut -f2)

echo "첫 그룹 stage 중: $FIRST_NAME"
echo "$FIRST_FILES" | tr ',' '\n' | while IFS= read -r f; do
  [ -z "$f" ] && continue
  if [ -e "$f" ]; then
    git add -- "$f"
  else
    git rm -q -- "$f" 2>/dev/null || true
  fi
done

echo ""
echo "✅ 첫 그룹 '$FIRST_NAME' staged 완료."
echo ""
echo "다음 단계:"
echo "  1. 이 그룹으로 커밋하라 (HARNESS_SPLIT_SUB=1 HARNESS_DEV=1):"
echo "     → Claude가 그룹 내용 보고 커밋 메시지 작성 + 커밋"
echo "  2. 커밋 후 다시 split-commit.sh 실행 → 다음 그룹 stage"
echo "  3. 전체 그룹 소진까지 반복"
echo ""
echo "전체 그룹 목록을 파일로 저장 중: .claude/memory/split-plan.txt"
mkdir -p .claude/memory
{
  echo "# split plan ($(date +%Y-%m-%dT%H:%M:%S))"
  echo "# 남은 그룹 (이 파일이 있으면 split 진행 중)"
  echo "$GROUP_DATA" | tail -n +2
} > .claude/memory/split-plan.txt

echo ""
exit 0
