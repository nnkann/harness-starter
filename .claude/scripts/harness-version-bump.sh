#!/bin/bash
# 하네스 스타터 전용 버전 체크·안내 (audit #4, 2026-04-22).
#
# 역할: 이번 커밋이 minor/patch 범프가 필요한지 판단하는 **안내만** 출력.
# 실제 HARNESS.json·promotion-log.md 수정은 Claude/사용자가 수동으로 수행.
#
# 설계 원칙:
# - 다운스트림(is_starter=false 또는 파일 없음)은 즉시 exit 0 + 메시지 없음
# - 업스트림에서만 staged 변경을 분석해 범프 타입 후보(minor/patch/none)
#   를 제안. 최종 결정은 사용자
# - 실행 결과를 파일 수정에 직접 쓰지 않음 (commit 스킬이 SSOT 수정 담당)

set -e

# 1. is_starter 판정 (commit 스킬 Step 3 진입 가드와 동일 로직)
if ! grep -q '"is_starter"[[:space:]]*:[[:space:]]*true' .claude/HARNESS.json 2>/dev/null; then
  exit 0  # 다운스트림: 조용히 skip
fi

# 2. staged 파일 수집
STAGED=$(git diff --cached --name-only 2>/dev/null)
if [ -z "$STAGED" ]; then
  echo "version_bump: none (staged 없음)"
  exit 0
fi

# 3. 범프 타입 후보 결정 (audit SKILL.md 표와 동형)
#    minor: 스킬·에이전트·규칙 신설, 폴더 구조 변경, 스크립트 신설
#    patch: 기존 파일 로직 수정, 버그 수정
#    none:  문서·주석만
BUMP_TYPE="none"
REASONS=""

# minor 신호: 새 파일 추가 (A status)
NEW_CRITICAL=$(echo "$STAGED" | while IFS= read -r f; do
  [ -z "$f" ] && continue
  status=$(git diff --cached --name-status -- "$f" 2>/dev/null | awk '{print $1}' | head -1)
  if [ "$status" = "A" ]; then
    case "$f" in
      .claude/skills/*/SKILL.md|.claude/agents/*.md|.claude/rules/*.md|.claude/scripts/*.sh)
        echo "$f"
        ;;
    esac
  fi
done)

if [ -n "$NEW_CRITICAL" ]; then
  BUMP_TYPE="minor"
  REASONS="${REASONS}\n   - 신규 핵심 파일: $(echo "$NEW_CRITICAL" | paste -sd',' -)"
fi

# patch 신호 (minor 아닐 때만): 기존 스크립트·스킬·규칙 수정
if [ "$BUMP_TYPE" = "none" ]; then
  MODIFIED_CRITICAL=$(echo "$STAGED" | grep -E '^(\.claude/scripts/.+\.sh|\.claude/skills/.+/SKILL\.md|\.claude/rules/.+\.md|\.claude/agents/.+\.md|CLAUDE\.md)$' || true)
  if [ -n "$MODIFIED_CRITICAL" ]; then
    BUMP_TYPE="patch"
    REASONS="${REASONS}\n   - 기존 핵심 파일 수정: $(echo "$MODIFIED_CRITICAL" | head -3 | paste -sd',' -)"
  fi
fi

# 4. 결과 출력 (commit 스킬이 사용자에게 중계)
CURRENT_VERSION=$(grep -oE '"version"[[:space:]]*:[[:space:]]*"[^"]+"' .claude/HARNESS.json 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
echo "version_bump: ${BUMP_TYPE}"
echo "current_version: ${CURRENT_VERSION:-unknown}"
[ -n "$REASONS" ] && echo -e "reasons:${REASONS}" >&2
exit 0
