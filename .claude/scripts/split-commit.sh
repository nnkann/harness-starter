#!/bin/bash
# split-commit.sh — 커밋 분리 실행 (audit #18, 글로벌 원칙 1 커밋 = 1 논리 단위).
#
# 역할:
# - pre-check stdout의 split_group_N_* 키를 읽어 그룹별 순차 커밋 수행
# - 각 sub-커밋은 HARNESS_SPLIT_SUB=1 환경변수로 pre-check 분리 판정 스킵
# - commit 스킬이 호출하거나 사용자가 직접 실행
#
# 사용법:
#   bash .claude/scripts/split-commit.sh
#
# 선행 조건:
#   - 현재 index(staged)에 커밋할 파일들이 올라가 있음
#   - pre-check이 split_action_recommended: split 을 출력한 상태
#
# 흐름:
#   1. pre-check 실행 → stdout 파싱
#   2. split_action_recommended == split 이면 계속, 아니면 즉시 종료
#   3. 현재 staged 스냅샷 저장 (git stash 대신 수동 파일 목록 보존)
#   4. git reset HEAD -- <모든 파일>  → staged 비우기
#   5. 각 그룹별:
#      a. 그룹 파일만 git add
#      b. HARNESS_SPLIT_SUB=1 로 Claude(사용자)에게 커밋 요청
#         (본 스크립트는 커밋 메시지 작성 안 함 — Claude가 그룹별 내용 보고 작성)
#   6. 모든 그룹 처리 완료 보고
#
# 종료 코드:
#   0 분리 계획 출력 + 첫 그룹 stage 완료 (사용자/Claude가 커밋 필요)
#   1 오류
#   2 분리 불필요 (split_action_recommended != split)

set -e

SPLIT_PLAN=".claude/memory/split-plan.txt"

# 0. split-plan.txt가 있으면 다음 그룹 자동 stage (pre-check 재계산 없이)
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

    # split-plan.txt에서 첫 줄 제거
    REMAINING=$(grep -v '^#' "$SPLIT_PLAN" | tail -n +2)
    if [ -z "$REMAINING" ]; then
      rm -f "$SPLIT_PLAN"
      echo "✅ '$NEXT_NAME' staged 완료 (마지막 그룹)."
    else
      {
        head -2 "$SPLIT_PLAN"  # 주석 헤더 보존
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

# 2. 그룹 정보 추출 (stdout의 split_group_N_name / split_group_N_files)
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
echo "현재 전체 staged 상태를 초기화하고 첫 그룹만 다시 stage합니다."
echo "각 그룹별 커밋은 HARNESS_SPLIT_SUB=1 환경에서 Claude가 개별 수행."
echo ""

# 3. 전체 staged 비우기 (파일은 working tree에 그대로 유지)
git reset HEAD -- . > /dev/null 2>&1 || true

# 4. 첫 그룹만 stage
FIRST_NAME=$(echo "$GROUP_DATA" | head -1 | cut -f1)
FIRST_FILES=$(echo "$GROUP_DATA" | head -1 | cut -f2)

echo "첫 그룹 stage 중: $FIRST_NAME"
echo "$FIRST_FILES" | tr ',' '\n' | while IFS= read -r f; do
  [ -z "$f" ] && continue
  # 삭제된 파일도 처리
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
