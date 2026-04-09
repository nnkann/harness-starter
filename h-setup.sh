#!/bin/bash
# 하네스 셋업 — 이 repo의 하네스 파일을 타겟 프로젝트에 복사한다.
# 사용법: bash h-setup.sh [--profile minimal|standard|full] [타겟_디렉토리]
#         bash h-setup.sh --upgrade [타겟_디렉토리]
#         bash h-setup.sh --add <skill> [타겟_디렉토리]
# 멱등성 보장: 기존 파일을 덮어쓰지 않음.
#
# 프로파일:
#   minimal  (기본) — harness-init, commit, implementation + rules + CLAUDE.md
#   standard        — minimal + check-existing, naming-convention
#   full            — 전부 (coding-convention, eval, advisor 포함)
# 필요한 스킬은 나중에 `bash h-setup.sh --add <skill>`로 추가 가능.
#
# --upgrade: 기존 하네스를 최신 버전으로 업그레이드.
#   새 파일은 바로 복사, 수정된 파일은 .claude/.upgrade/에 스테이징 후 리포트 생성.
#   충돌 해결은 harness-upgrade 스킬이 대화형으로 처리.
#   harness.json이 없는 fork 프로젝트도 지원 (.claude/ 존재 시 자동 생성).

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 인자 파싱
PROFILE="minimal"
ADD_SKILL=""
UPGRADE_MODE=""
TARGET=""
while [ $# -gt 0 ]; do
  case "$1" in
    --profile)
      PROFILE="$2"; shift 2 ;;
    --add)
      ADD_SKILL="$2"; shift 2 ;;
    --upgrade)
      UPGRADE_MODE="1"; shift ;;
    *)
      TARGET="$1"; shift ;;
  esac
done
TARGET="${TARGET:-.}"

# 프로파일별 스킬 목록
case "$PROFILE" in
  minimal)
    SKILLS="harness-init commit implementation harness-upgrade" ;;
  standard)
    SKILLS="harness-init commit implementation harness-upgrade check-existing naming-convention" ;;
  full)
    SKILLS="harness-init commit implementation harness-upgrade check-existing naming-convention coding-convention eval advisor" ;;
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

# --upgrade 모드: 기존 하네스를 최신으로 업그레이드
if [ -n "$UPGRADE_MODE" ]; then
  META="$TARGET/.claude/harness.json"
  if [ ! -f "$META" ]; then
    # harness.json 없지만 .claude/ 디렉토리가 있으면 fork 프로젝트로 판단
    if [ -d "$TARGET/.claude" ]; then
      echo -e "${YELLOW}⚠ harness.json 없음 — fork 프로젝트로 판단. harness.json을 자동 생성합니다.${NC}"
      # 설치된 스킬 목록으로 프로파일 추정
      DETECTED_PROFILE="minimal"
      if [ -f "$TARGET/.claude/skills/eval/SKILL.md" ] || [ -f "$TARGET/.claude/skills/advisor/SKILL.md" ]; then
        DETECTED_PROFILE="full"
      elif [ -f "$TARGET/.claude/skills/check-existing/SKILL.md" ] || [ -f "$TARGET/.claude/skills/naming-convention/SKILL.md" ]; then
        DETECTED_PROFILE="standard"
      fi
      # 설치된 스킬 실제 목록 수집
      DETECTED_SKILLS=""
      for d in "$TARGET/.claude/skills/"*/; do
        [ -d "$d" ] || continue
        DETECTED_SKILLS="$DETECTED_SKILLS $(basename "$d")"
      done
      DETECTED_SKILLS=$(echo "$DETECTED_SKILLS" | xargs)
      cat > "$META" <<EOF
{
  "profile": "$DETECTED_PROFILE",
  "skills": "$DETECTED_SKILLS",
  "version": "unknown",
  "installed_at": "unknown",
  "upgraded_at": null
}
EOF
      echo -e "${GREEN}✓ harness.json 생성 (프로파일: $DETECTED_PROFILE)${NC}"
      echo ""
    else
      echo -e "${RED}❌ 하네스가 설치되지 않은 프로젝트. h-setup.sh를 먼저 실행하라.${NC}"
      exit 1
    fi
  fi

  # 버전 비교
  SRC_VERSION=$(cat "$SCRIPT_DIR/.claude/HARNESS_VERSION" 2>/dev/null | tr -d '[:space:]')
  CUR_VERSION=$(grep -o '"version"[[:space:]]*:[[:space:]]*"[^"]*"' "$META" 2>/dev/null | sed 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')

  # 소스 VERSION이 비어있으면 스타터 리포가 아닌 곳에서 실행한 것
  if [ -z "$SRC_VERSION" ]; then
    echo -e "${RED}❌ .claude/HARNESS_VERSION이 없거나 비어있음. harness-starter 리포에서 실행하고 있는지 확인하라.${NC}"
    echo "    사용법: cd /path/to/harness-starter && bash h-setup.sh --upgrade /path/to/project"
    exit 1
  fi

  echo "═══ 하네스 업그레이드 ═══"
  echo "타겟:    $TARGET"
  echo "현재:    ${CUR_VERSION:-unknown}"
  echo "최신:    ${SRC_VERSION}"
  echo ""

  if [ "$CUR_VERSION" = "$SRC_VERSION" ]; then
    echo -e "${GREEN}✅ 이미 최신 버전 ($SRC_VERSION). 업그레이드 불필요.${NC}"
    exit 0
  fi

  # 프로파일에서 스킬 목록 읽기
  CUR_PROFILE=$(grep -o '"profile"[[:space:]]*:[[:space:]]*"[^"]*"' "$META" 2>/dev/null | sed 's/.*"profile"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
  case "${CUR_PROFILE:-minimal}" in
    minimal)  SKILLS="harness-init commit implementation harness-upgrade" ;;
    standard) SKILLS="harness-init commit implementation harness-upgrade check-existing naming-convention" ;;
    full)     SKILLS="harness-init commit implementation harness-upgrade check-existing naming-convention coding-convention eval advisor" ;;
    *)        SKILLS="harness-init commit implementation harness-upgrade" ;;
  esac

  UPGRADE_DIR="$TARGET/.claude/.upgrade"
  rm -rf "$UPGRADE_DIR"
  mkdir -p "$UPGRADE_DIR"

  NEW_COUNT=0
  STAGED_COUNT=0
  UNCHANGED_COUNT=0

  # 업그레이드용 파일 비교 함수
  stage_or_copy() {
    local src="$1"
    local dst="$2"
    local rel=$(echo "$dst" | sed "s|$TARGET/||")
    local stage_path="$UPGRADE_DIR/$rel"

    if [ ! -f "$dst" ]; then
      # 새 파일 — 바로 복사
      mkdir -p "$(dirname "$dst")"
      cp "$src" "$dst"
      echo -e "  ${GREEN}✓ 새 파일${NC}: $rel"
      NEW_COUNT=$((NEW_COUNT + 1))
    elif diff -q "$src" "$dst" > /dev/null 2>&1; then
      # 변경 없음
      UNCHANGED_COUNT=$((UNCHANGED_COUNT + 1))
    else
      # 변경 있음 — .upgrade/에 스테이징
      mkdir -p "$(dirname "$stage_path")"
      cp "$src" "$stage_path"
      echo -e "  ${YELLOW}⚡ 변경됨${NC}: $rel"
      STAGED_COUNT=$((STAGED_COUNT + 1))
    fi
  }

  # 스크립트
  echo "📁 .claude/scripts/"
  for f in "$SCRIPT_DIR/.claude/scripts/"*; do
    [ -f "$f" ] || continue
    stage_or_copy "$f" "$TARGET/.claude/scripts/$(basename "$f")"
  done

  # 스킬 (프로파일 기준)
  echo ""
  echo "📁 .claude/skills/ ($CUR_PROFILE)"
  for skill in $SKILLS; do
    src="$SCRIPT_DIR/.claude/skills/$skill/SKILL.md"
    [ -f "$src" ] || continue
    stage_or_copy "$src" "$TARGET/.claude/skills/$skill/SKILL.md"
  done
  # 스타터에 있지만 프로파일에 없는 스킬도 타겟에 있으면 업그레이드 대상
  for src in "$SCRIPT_DIR/.claude/skills/"*/SKILL.md; do
    [ -f "$src" ] || continue
    skill=$(basename "$(dirname "$src")")
    dst="$TARGET/.claude/skills/$skill/SKILL.md"
    [ -f "$dst" ] || continue
    # 이미 위에서 처리한 스킬은 건너뛰기
    echo "$SKILLS" | grep -qw "$skill" && continue
    stage_or_copy "$src" "$dst"
  done

  # rules — 하네스 관리 rule은 비교, 사용자 템플릿 rule은 제외.
  # coding.md, naming.md: 빈 템플릿 → 사용자가 채움 → 비교하면 항상 "변경됨"
  # docs.md, self-verify.md, memory.md: 하네스 규칙 → 업그레이드 대상
  USER_TEMPLATE_RULES="coding.md naming.md"
  echo ""
  echo "📁 .claude/rules/"
  for f in "$SCRIPT_DIR/.claude/rules/"*; do
    [ -f "$f" ] || continue
    fname=$(basename "$f")
    # 사용자 템플릿 rule은 새 파일만 복사, 기존 파일은 건드리지 않음
    if echo " $USER_TEMPLATE_RULES " | grep -qF " $fname "; then
      dst="$TARGET/.claude/rules/$fname"
      if [ ! -f "$dst" ]; then
        mkdir -p "$(dirname "$dst")"
        cp "$f" "$dst"
        echo -e "  ${GREEN}✓ 새 파일${NC}: .claude/rules/$fname"
        NEW_COUNT=$((NEW_COUNT + 1))
      else
        echo -e "  ⏭ 제외 (사용자 템플릿): .claude/rules/$fname"
      fi
    else
      stage_or_copy "$f" "$TARGET/.claude/rules/$fname"
    fi
  done

  # settings.json, CLAUDE.md — 사용자가 프로젝트에 맞게 커스터마이징하는 파일. 업그레이드 제외.
  echo ""
  echo "⏭  settings.json, CLAUDE.md — 사용자 커스터마이징 파일, 업그레이드 제외"

  # VERSION 복사
  cp "$SCRIPT_DIR/.claude/HARNESS_VERSION" "$TARGET/.claude/HARNESS_VERSION" 2>/dev/null

  # 업그레이드 리포트 생성
  if [ "$STAGED_COUNT" -gt 0 ]; then
    REPORT="$UPGRADE_DIR/UPGRADE_REPORT.md"
    cat > "$REPORT" <<EOF
> status: pending

# 하네스 업그레이드 리포트

- 소스 버전: ${SRC_VERSION}
- 현재 버전: ${CUR_VERSION}
- 프로파일: ${CUR_PROFILE}
- 생성일: $(date -u +%Y-%m-%dT%H:%M:%SZ)

## 변경 파일 목록

EOF
    # 스테이징된 파일들의 diff 요약 추가
    find "$UPGRADE_DIR" -type f ! -name "UPGRADE_REPORT.md" | sort | while read staged_file; do
      rel=$(echo "$staged_file" | sed "s|$UPGRADE_DIR/||")
      target_file="$TARGET/$rel"
      echo "### $rel" >> "$REPORT"
      echo '```diff' >> "$REPORT"
      diff -u "$target_file" "$staged_file" 2>/dev/null | head -50 >> "$REPORT"
      echo '```' >> "$REPORT"
      echo "" >> "$REPORT"
    done

    cat >> "$REPORT" <<'EOF'

## 다음 단계

Claude Code에서 아래를 실행하세요:

> harness-upgrade 스킬을 실행해줘

harness-upgrade 스킬이 각 파일의 diff를 분석하고, 사용자 커스터마이징을 보존하면서 병합을 수행합니다.
EOF
  fi

  # 실행 권한
  chmod +x "$TARGET/.claude/scripts/"*.sh 2>/dev/null

  echo ""
  echo "═══ 업그레이드 준비 완료 ═══"
  echo -e "  ${GREEN}새 파일:   ${NEW_COUNT}개${NC}"
  echo -e "  ${YELLOW}병합 필요: ${STAGED_COUNT}개${NC} (.claude/.upgrade/에 스테이징됨)"
  echo -e "  변경 없음: ${UNCHANGED_COUNT}개"
  echo ""

  if [ "$STAGED_COUNT" -gt 0 ]; then
    echo "다음: Claude Code에서 'harness-upgrade 스킬을 실행해줘'"
    echo "      → 각 파일의 diff를 보고 승인하면서 병합합니다."
  else
    # 새 파일만 있고 충돌 없으면 바로 harness.json 업데이트
    if command -v jq > /dev/null 2>&1; then
      jq --arg v "$SRC_VERSION" --arg t "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        '.version = $v | .upgraded_at = $t' "$META" > "$META.tmp" && mv "$META.tmp" "$META"
    else
      sed -i "s/\"version\": \"[^\"]*\"/\"version\": \"$SRC_VERSION\"/" "$META"
      sed -i "s/\"upgraded_at\": [^,}]*/\"upgraded_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"/" "$META"
    fi
    echo -e "${GREEN}✅ 업그레이드 완료 (${CUR_VERSION} → ${SRC_VERSION})${NC}"
    rm -rf "$UPGRADE_DIR"
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
  grep -q '^\.claude/\.upgrade/$' "$GI" || echo '.claude/.upgrade/' >> "$GI"
else
  cat > "$GI" <<'EOF'
# 하네스 — 머신별/세션별 파일 제외
.claude/.env_synced
.claude/.compact_count
.claude/.upgrade/
EOF
  echo -e "  ${GREEN}✓ 생성${NC}: .gitignore"
  CREATED=$((CREATED + 1))
fi

# 하네스 메타데이터 기록 (프로파일 + 버전)
META="$TARGET/.claude/harness.json"
if [ ! -f "$META" ]; then
  HARNESS_VERSION=$(cat "$SCRIPT_DIR/.claude/HARNESS_VERSION" 2>/dev/null | tr -d '[:space:]')
  cat > "$META" <<EOF
{
  "profile": "$PROFILE",
  "skills": "$SKILLS",
  "version": "${HARNESS_VERSION:-unknown}",
  "installed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "upgraded_at": null
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

이 프로젝트는 `h-setup.sh`로 하네스 파일이 복사되었지만, **프로젝트 결정(CPS/스택/강도)** 이 아직 이뤄지지 않았습니다.

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
