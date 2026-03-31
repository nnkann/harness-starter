#!/bin/bash
# 하네스 셋업 — 이 repo의 하네스 파일을 타겟 프로젝트에 복사한다.
# 사용법: bash setup.sh [타겟_디렉토리]
# 멱등성 보장: 기존 파일을 덮어쓰지 않음.

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:-.}"

if [ ! -d "$TARGET" ]; then
  echo -e "${RED}❌ 타겟 디렉토리가 없음: $TARGET${NC}"
  exit 1
fi

# 자기 자신에게 설치하는 것 방지
TARGET="$(cd "$TARGET" && pwd)"
if [ "$TARGET" = "$SCRIPT_DIR" ]; then
  echo -e "${RED}❌ 이 repo 안에는 설치할 수 없음. 타겟 프로젝트 경로를 지정하라.${NC}"
  exit 1
fi

echo "═══ 하네스 셋업 ═══"
echo "타겟: $TARGET"
echo ""

CREATED=0
SKIPPED=0

copy_if_new() {
  local src="$1"
  local dst="$2"
  mkdir -p "$(dirname "$dst")"
  if [ -f "$dst" ]; then
    echo -e "  ${YELLOW}⏭ 스킵${NC}: $(echo "$dst" | sed "s|$TARGET/||")"
    SKIPPED=$((SKIPPED + 1))
  else
    cp "$src" "$dst"
    echo -e "  ${GREEN}✓ 생성${NC}: $(echo "$dst" | sed "s|$TARGET/||")"
    CREATED=$((CREATED + 1))
  fi
}

# CLAUDE.md
echo "📄 CLAUDE.md"
copy_if_new "$SCRIPT_DIR/CLAUDE.md" "$TARGET/CLAUDE.md"

# .claude/rules/
echo ""
echo "📁 .claude/rules/"
for f in "$SCRIPT_DIR/.claude/rules/"*; do
  [ -f "$f" ] || continue
  copy_if_new "$f" "$TARGET/.claude/rules/$(basename "$f")"
done

# .claude/skills/
echo ""
echo "📁 .claude/skills/"
for skill_dir in "$SCRIPT_DIR/.claude/skills/"*/; do
  [ -d "$skill_dir" ] || continue
  copy_if_new "$skill_dir/SKILL.md" "$TARGET/.claude/skills/$(basename "$skill_dir")/SKILL.md"
done

# .claude/scripts/
echo ""
echo "📁 .claude/scripts/"
for f in "$SCRIPT_DIR/.claude/scripts/"*; do
  [ -f "$f" ] || continue
  copy_if_new "$f" "$TARGET/.claude/scripts/$(basename "$f")"
done

# settings.json
echo ""
echo "⚙️  .claude/settings.json"
copy_if_new "$SCRIPT_DIR/.claude/settings.json" "$TARGET/.claude/settings.json"

# docs/
echo ""
echo "📁 docs/"
for dir in wip setup history development harness archived; do
  if [ ! -d "$TARGET/docs/$dir" ]; then
    mkdir -p "$TARGET/docs/$dir"
    echo -e "  ${GREEN}✓ 생성${NC}: docs/$dir/"
    CREATED=$((CREATED + 1))
  else
    echo -e "  ${YELLOW}⏭ 스킵${NC}: docs/$dir/"
    SKIPPED=$((SKIPPED + 1))
  fi
done
copy_if_new "$SCRIPT_DIR/docs/harness/promotion-log.md" "$TARGET/docs/harness/promotion-log.md"

# .gitkeep
for dir in wip setup history development archived; do
  if [ -z "$(ls -A "$TARGET/docs/$dir" 2>/dev/null)" ]; then
    touch "$TARGET/docs/$dir/.gitkeep"
  fi
done

# 실행 권한
chmod +x "$TARGET/.claude/scripts/"*.sh 2>/dev/null

echo ""
echo "═══ 완료 ═══"
echo -e "  ${GREEN}생성: ${CREATED}개${NC}"
echo -e "  ${YELLOW}스킵: ${SKIPPED}개${NC}"
echo ""
echo "다음: claude code에서 프로젝트 열고 harness-init 실행"
