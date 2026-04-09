#!/bin/bash
# 하네스 셋업 — 이 repo의 하네스 파일을 타겟 프로젝트에 복사한다.
# 사용법: bash setup.sh [--profile minimal|standard|full] [타겟_디렉토리]
# 멱등성 보장: 기존 파일을 덮어쓰지 않음.
#
# 프로파일:
#   minimal  (기본) — harness-init, commit, implementation + rules + CLAUDE.md
#   standard        — minimal + check-existing, naming-convention
#   full            — 전부 (coding-convention, eval, advisor 포함)
# 필요한 스킬은 나중에 `bash setup.sh --add <skill>`로 추가 가능.

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 인자 파싱
PROFILE="minimal"
ADD_SKILL=""
TARGET=""
while [ $# -gt 0 ]; do
  case "$1" in
    --profile)
      PROFILE="$2"; shift 2 ;;
    --add)
      ADD_SKILL="$2"; shift 2 ;;
    *)
      TARGET="$1"; shift ;;
  esac
done
TARGET="${TARGET:-.}"

# 프로파일별 스킬 목록
case "$PROFILE" in
  minimal)
    SKILLS="harness-init commit implementation" ;;
  standard)
    SKILLS="harness-init commit implementation check-existing naming-convention" ;;
  full)
    SKILLS="harness-init commit implementation check-existing naming-convention coding-convention eval advisor" ;;
  *)
    echo -e "${RED}❌ 알 수 없는 프로파일: $PROFILE${NC}"
    echo "사용 가능: minimal | standard | full"
    exit 1 ;;
esac

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

# --add 모드: 단일 스킬만 추가
if [ -n "$ADD_SKILL" ]; then
  SRC="$SCRIPT_DIR/.claude/skills/$ADD_SKILL/SKILL.md"
  if [ ! -f "$SRC" ]; then
    echo -e "${RED}❌ 스킬 없음: $ADD_SKILL${NC}"
    exit 1
  fi
  DST="$TARGET/.claude/skills/$ADD_SKILL/SKILL.md"
  if [ -f "$DST" ]; then
    echo -e "${YELLOW}⏭ 이미 존재: $ADD_SKILL${NC}"
  else
    mkdir -p "$(dirname "$DST")"
    cp "$SRC" "$DST"
    echo -e "${GREEN}✓ 스킬 추가: $ADD_SKILL${NC}"
  fi
  exit 0
fi

echo "═══ 하네스 셋업 ═══"
echo "타겟:   $TARGET"
echo "프로파일: $PROFILE"
echo "스킬:   $SKILLS"
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

# .claude/skills/ (프로파일 기준)
echo ""
echo "📁 .claude/skills/ ($PROFILE)"
for skill in $SKILLS; do
  src="$SCRIPT_DIR/.claude/skills/$skill/SKILL.md"
  [ -f "$src" ] || { echo -e "  ${RED}❌ 스킬 누락: $skill${NC}"; continue; }
  copy_if_new "$src" "$TARGET/.claude/skills/$skill/SKILL.md"
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

# .gitignore — 하네스가 필요로 하는 머신별 파일 제외
GI="$TARGET/.gitignore"
if [ -f "$GI" ]; then
  grep -q '^\.claude/\.env_synced$' "$GI" || echo '.claude/.env_synced' >> "$GI"
  grep -q '^\.claude/\.compact_count$' "$GI" || echo '.claude/.compact_count' >> "$GI"
else
  cat > "$GI" <<'EOF'
# 하네스 — 머신별/세션별 파일 제외
.claude/.env_synced
.claude/.compact_count
EOF
  echo -e "  ${GREEN}✓ 생성${NC}: .gitignore"
  CREATED=$((CREATED + 1))
fi

# 하네스 메타데이터 기록 (프로파일 + 버전)
META="$TARGET/.claude/harness.json"
if [ ! -f "$META" ]; then
  cat > "$META" <<EOF
{
  "profile": "$PROFILE",
  "skills": "$SKILLS",
  "installed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
  echo -e "  ${GREEN}✓ 생성${NC}: .claude/harness.json"
  CREATED=$((CREATED + 1))
fi

# 프로젝트 출범 문서 placeholder — harness-init이 아직 안 돌았을 때 "다음 할 일"을 보여줌
KICKOFF="$TARGET/docs/WIP/harness_init_pending.md"
if [ ! -f "$KICKOFF" ] && [ ! -f "$TARGET/docs/setup/project_kickoff.md" ]; then
  cat > "$KICKOFF" <<'EOF'
> status: pending

# 하네스 초기화 대기 중

이 프로젝트는 `setup.sh`로 하네스 파일이 복사되었지만, **프로젝트 결정(CPS/스택/강도)** 이 아직 이뤄지지 않았습니다.

## 다음 할 일

Claude Code에서 아래를 실행하세요:

> harness-init 스킬을 실행해줘

harness-init이 끝나면 이 파일은 삭제되고, 대신 실제 결정이 담긴 `docs/WIP/project_kickoff_YYMMDD.md`가 생성됩니다.

## 왜 이 문서가 있나요?

하네스 철학: `docs/WIP/`에 파일이 있으면 할 일이 있다는 뜻입니다. 이 placeholder는 "하네스는 깔렸지만 프로젝트 결정은 안 됐다"는 상태를 명시적으로 드러냅니다.
EOF
  echo -e "  ${GREEN}✓ 생성${NC}: docs/WIP/harness_init_pending.md"
  CREATED=$((CREATED + 1))
fi

echo ""
echo "═══ 완료 ═══"
echo -e "  ${GREEN}생성: ${CREATED}개${NC}"
echo -e "  ${YELLOW}스킵: ${SKIPPED}개${NC}"
echo ""
echo "다음: claude code에서 프로젝트 열고 'harness-init 스킬을 실행해줘'"
