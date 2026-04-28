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
# --upgrade: harness-upstream remote가 있으면 /harness-upgrade 스킬 안내.
#   remote 없으면 파일 복사 fallback (스테이징 → harness-upgrade 스킬이 병합).
#   HARNESS.json이 없는 fork 프로젝트도 지원 (.claude/ 존재 시 자동 생성).

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# GNU/BSD(macOS) sed 호환 in-place 편집 헬퍼.
#   사용: sed_inplace 's/foo/bar/' file
# BSD sed는 `-i` 뒤에 백업 확장자 인자(빈 문자열도)를 요구하고, GNU는 선택적이다.
# tmp 파일 경유로 양쪽 모두 안전하게 처리.
sed_inplace() {
  local expr="$1"; local file="$2"
  local tmp
  tmp="$(mktemp)" || return 1
  sed "$expr" "$file" > "$tmp" && mv "$tmp" "$file"
}

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
    SKILLS="harness-init harness-adopt harness-sync harness-upgrade commit implementation write-doc" ;;
  standard)
    SKILLS="harness-init harness-adopt harness-sync harness-upgrade commit implementation write-doc check-existing naming-convention" ;;
  full)
    SKILLS="harness-init harness-adopt harness-sync harness-upgrade commit implementation write-doc check-existing naming-convention coding-convention eval advisor" ;;
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

# --upgrade 모드: remote 있으면 스킬 안내, 없으면 파일 복사 fallback
if [ -n "$UPGRADE_MODE" ]; then
  META="$TARGET/.claude/HARNESS.json"
  if [ ! -f "$META" ]; then
    # HARNESS.json 없지만 .claude/ 디렉토리가 있으면 fork 프로젝트로 판단
    if [ -d "$TARGET/.claude" ]; then
      echo -e "${YELLOW}⚠ HARNESS.json 없음 — fork 프로젝트로 판단. HARNESS.json을 자동 생성합니다.${NC}"
      DETECTED_PROFILE="minimal"
      if [ -f "$TARGET/.claude/skills/eval/SKILL.md" ] || [ -f "$TARGET/.claude/skills/advisor/SKILL.md" ]; then
        DETECTED_PROFILE="full"
      elif [ -f "$TARGET/.claude/skills/check-existing/SKILL.md" ] || [ -f "$TARGET/.claude/skills/naming-convention/SKILL.md" ]; then
        DETECTED_PROFILE="standard"
      fi
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
  "installed_from_ref": "unknown",
  "installed_at": "unknown",
  "upgraded_at": null
}
EOF
      echo -e "${GREEN}✓ HARNESS.json 생성 (프로파일: $DETECTED_PROFILE)${NC}"
      echo ""
    else
      echo -e "${RED}❌ 하네스가 설치되지 않은 프로젝트. h-setup.sh를 먼저 실행하라.${NC}"
      exit 1
    fi
  fi

  # ─── 구 메타데이터 파일 마이그레이션 ───
  # v1.0.0 이전: HARNESS_VERSION, .harness_adopted 가 별도 파일로 존재
  LEGACY_CLEANED=""
  if [ -f "$TARGET/.claude/HARNESS_VERSION" ]; then
    # 버전 정보를 HARNESS.json에 반영 (version이 unknown이면)
    OLD_VER=$(cat "$TARGET/.claude/HARNESS_VERSION" 2>/dev/null | tr -d '[:space:]')
    CUR_JSON_VER=$(grep -o '"version"[[:space:]]*:[[:space:]]*"[^"]*"' "$META" 2>/dev/null | sed 's/.*"\([^"]*\)"$/\1/')
    if [ "$CUR_JSON_VER" = "unknown" ] && [ -n "$OLD_VER" ]; then
      sed_inplace "s/\"version\"[[:space:]]*:[[:space:]]*\"unknown\"/\"version\": \"$OLD_VER\"/" "$META"
    fi
    rm -f "$TARGET/.claude/HARNESS_VERSION"
    echo -e "${GREEN}✓ 마이그레이션: HARNESS_VERSION → HARNESS.json (삭제됨)${NC}"
    LEGACY_CLEANED="1"
  fi
  if [ -f "$TARGET/.claude/.harness_adopted" ]; then
    # adopted_at 정보를 HARNESS.json에 추가
    ADOPTED_TIME=$(grep -o 'adopted_at:.*' "$TARGET/.claude/.harness_adopted" 2>/dev/null | sed 's/adopted_at:[[:space:]]*//')
    [ -z "$ADOPTED_TIME" ] && ADOPTED_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    if ! grep -q '"adopted_at"' "$META" 2>/dev/null; then
      # GNU sed의 '\n' 치환은 BSD sed(macOS)에서 리터럴로 삽입되어 JSON이 깨진다.
      # awk로 마지막 '}' 라인 직전에 adopted_at 항목을 삽입. 양쪽 호환.
      tmp="$(mktemp)"
      awk -v t="$ADOPTED_TIME" '
        /^\}$/ && !done { print ",";  print "  \"adopted_at\": \"" t "\""; print "}"; done=1; next }
        { print }
      ' "$META" > "$tmp" && mv "$tmp" "$META"
    fi
    rm -f "$TARGET/.claude/.harness_adopted"
    echo -e "${GREEN}✓ 마이그레이션: .harness_adopted → HARNESS.json (삭제됨)${NC}"
    LEGACY_CLEANED="1"
  fi
  # 런타임 찌꺼기 정리
  rm -f "$TARGET/.claude/scheduled_tasks.lock" "$TARGET/.claude/ts_errors.log" 2>/dev/null
  if [ -n "$LEGACY_CLEANED" ]; then
    echo ""
  fi

  # 프로파일에서 스킬 목록 읽기
  CUR_PROFILE=$(grep -o '"profile"[[:space:]]*:[[:space:]]*"[^"]*"' "$META" 2>/dev/null | sed 's/.*"profile"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
  CUR_VERSION=$(grep -o '"version"[[:space:]]*:[[:space:]]*"[^"]*"' "$META" 2>/dev/null | sed 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
  BASE_REF=$(grep -o '"installed_from_ref"[[:space:]]*:[[:space:]]*"[^"]*"' "$META" 2>/dev/null | sed 's/.*"installed_from_ref"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')

  case "${CUR_PROFILE:-minimal}" in
    minimal)  SKILLS="harness-init harness-adopt harness-sync harness-upgrade commit implementation write-doc" ;;
    standard) SKILLS="harness-init harness-adopt harness-sync harness-upgrade commit implementation write-doc check-existing naming-convention" ;;
    full)     SKILLS="harness-init harness-adopt harness-sync harness-upgrade commit implementation write-doc check-existing naming-convention coding-convention eval advisor" ;;
    *)        SKILLS="harness-init harness-adopt harness-sync harness-upgrade commit implementation write-doc" ;;
  esac

  # ─── remote 방식 vs 파일 복사 방식 분기 ───
  if git -C "$TARGET" remote get-url harness-upstream > /dev/null 2>&1; then
    # remote가 있으면 스킬이 직접 처리 — 스크립트는 안내만
    echo "═══ 하네스 업그레이드 ═══"
    echo ""
    echo "harness-upstream remote 감지."
    echo "Claude Code에서 /harness-upgrade를 실행하세요."
    echo "스킬이 fetch → 변경 분석 → 3-way merge를 한 번에 처리합니다."
    exit 0
  fi

  # ─── 파일 복사 방식 (remote 없을 때) ───
  SRC_VERSION=$(grep -o '"version"[[:space:]]*:[[:space:]]*"[^"]*"' "$SCRIPT_DIR/.claude/HARNESS.json" 2>/dev/null | sed 's/.*"\([^"]*\)"$/\1/')

  if [ -z "$SRC_VERSION" ]; then
    echo -e "${RED}❌ 업스트림 버전을 확인할 수 없음.${NC}"
    echo "    harness-starter 리포에서 실행하고 있는지 확인하라."
    echo "    사용법: cd /path/to/harness-starter && bash h-setup.sh --upgrade /path/to/project"
    exit 1
  fi

  echo "═══ 하네스 업그레이드 ═══"
  echo "타겟:    $TARGET"
  echo "현재:    ${CUR_VERSION:-unknown}"
  echo "최신:    ${SRC_VERSION}"
  echo "방식:    파일 복사"
  echo ""

  if [ "$CUR_VERSION" = "$SRC_VERSION" ]; then
    echo -e "${GREEN}✅ 이미 최신 버전 ($SRC_VERSION). 업그레이드 불필요.${NC}"
    exit 0
  fi

  UPGRADE_DIR="$TARGET/.claude/.upgrade"
  rm -rf "$UPGRADE_DIR"
  mkdir -p "$UPGRADE_DIR"

  # ─── 파일 복사 방식 (fallback) ───
  echo "📦 파일 복사 방식으로 업그레이드 (harness-upstream remote 없음)"
  echo ""

  NEW_COUNT=0
  STAGED_COUNT=0
  UNCHANGED_COUNT=0

  stage_or_copy() {
    local src="$1"
    local dst="$2"
    local rel=$(echo "$dst" | sed "s|$TARGET/||")
    local stage_path="$UPGRADE_DIR/$rel"

    if [ ! -f "$dst" ]; then
      mkdir -p "$(dirname "$dst")"
      cp "$src" "$dst"
      echo -e "  ${GREEN}✓ 새 파일${NC}: $rel"
      NEW_COUNT=$((NEW_COUNT + 1))
    elif diff -q "$src" "$dst" > /dev/null 2>&1; then
      UNCHANGED_COUNT=$((UNCHANGED_COUNT + 1))
    else
      mkdir -p "$(dirname "$stage_path")"
      cp "$src" "$stage_path"
      echo -e "  ${YELLOW}⚡ 변경됨${NC}: $rel"
      STAGED_COUNT=$((STAGED_COUNT + 1))
    fi
  }

  # 에이전트
  echo "📁 .claude/agents/"
  for f in "$SCRIPT_DIR/.claude/agents/"*; do
    [ -f "$f" ] || continue
    stage_or_copy "$f" "$TARGET/.claude/agents/$(basename "$f")"
  done

  # 스크립트
  echo ""
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
  # starter_skills는 업그레이드 복사 제외 (다운스트림 전달 안 함)
  STARTER_SKILLS=$(grep -o '"starter_skills"[[:space:]]*:[[:space:]]*"[^"]*"' "$SCRIPT_DIR/.claude/HARNESS.json" 2>/dev/null | sed 's/.*"\([^"]*\)"$/\1/' | tr ',' ' ')
  for src in "$SCRIPT_DIR/.claude/skills/"*/SKILL.md; do
    [ -f "$src" ] || continue
    skill=$(basename "$(dirname "$src")")
    dst="$TARGET/.claude/skills/$skill/SKILL.md"
    [ -f "$dst" ] || continue
    echo "$SKILLS" | grep -qw "$skill" && continue
    echo "$STARTER_SKILLS" | grep -qw "$skill" && continue  # starter 전용 스킬 제외
    stage_or_copy "$src" "$dst"
  done

  # rules
  USER_TEMPLATE_RULES="coding.md naming.md"
  echo ""
  echo "📁 .claude/rules/"
  for f in "$SCRIPT_DIR/.claude/rules/"*; do
    [ -f "$f" ] || continue
    fname=$(basename "$f")
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

  # CLAUDE.md
  echo ""
  echo "⏭  CLAUDE.md — 사용자 커스터마이징 파일, 업그레이드 제외"

  # settings.json — hook 누락 감지
  MISSING_HOOKS=""
  MISSING_HOOK_COUNT=0
  SRC_SETTINGS="$SCRIPT_DIR/.claude/settings.json"
  TGT_SETTINGS="$TARGET/.claude/settings.json"

  echo ""
  echo "📁 .claude/settings.json (hook 누락 검사)"
  if [ -f "$SRC_SETTINGS" ] && [ -f "$TGT_SETTINGS" ]; then
    src_matchers=$(grep '"matcher"' "$SRC_SETTINGS" | sed 's/.*"matcher"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
    while IFS= read -r matcher; do
      [ -z "$matcher" ] && continue
      if [ "$matcher" = "" ]; then continue; fi
      if ! grep -qF "\"$matcher\"" "$TGT_SETTINGS" 2>/dev/null; then
        category=$(awk -v m="$matcher" '
          /"(PreToolUse|PostToolUse|Stop|SessionStart|PostCompact)"/ { cat=$0; gsub(/.*"/, "", cat); gsub(/".*/, "", cat) }
          index($0, "\"" m "\"") { print cat; exit }
        ' "$SRC_SETTINGS")
        MISSING_HOOKS="${MISSING_HOOKS}\n   - [${category}] matcher: \"${matcher}\""
        MISSING_HOOK_COUNT=$((MISSING_HOOK_COUNT + 1))
      fi
    done <<< "$src_matchers"

    for cat in SessionStart Stop PostCompact; do
      if grep -q "\"$cat\"" "$SRC_SETTINGS" 2>/dev/null && ! grep -q "\"$cat\"" "$TGT_SETTINGS" 2>/dev/null; then
        MISSING_HOOKS="${MISSING_HOOKS}\n   - [${cat}] 카테고리 전체 누락"
        MISSING_HOOK_COUNT=$((MISSING_HOOK_COUNT + 1))
      fi
    done

    if [ "$MISSING_HOOK_COUNT" -gt 0 ]; then
      echo -e "  ${YELLOW}⚠ 누락된 hook ${MISSING_HOOK_COUNT}개 감지${NC}"
      echo -e "$MISSING_HOOKS"
      mkdir -p "$UPGRADE_DIR/.claude"
      cp "$SRC_SETTINGS" "$UPGRADE_DIR/.claude/settings.json"
      STAGED_COUNT=$((STAGED_COUNT + 1))
    else
      echo -e "  ${GREEN}✓ 모든 hook 존재${NC}"
    fi
  elif [ -f "$SRC_SETTINGS" ] && [ ! -f "$TGT_SETTINGS" ]; then
    echo -e "  ${RED}⚠ 타겟에 settings.json 없음 — 스타터 버전 복사${NC}"
    mkdir -p "$TARGET/.claude"
    cp "$SRC_SETTINGS" "$TGT_SETTINGS"
    NEW_COUNT=$((NEW_COUNT + 1))
  fi

  # 업그레이드 리포트 생성
  if [ "$STAGED_COUNT" -gt 0 ]; then
    REPORT="$UPGRADE_DIR/UPGRADE_REPORT.md"
    cat > "$REPORT" <<EOF
# 하네스 업그레이드 리포트

- 현재 버전: ${CUR_VERSION:-unknown}
- 소스 버전: ${SRC_VERSION}
- 프로파일: ${CUR_PROFILE:-minimal}
- 방식: 파일 복사 (fallback)
- 생성일: $(date -u +%Y-%m-%dT%H:%M:%SZ)

## 변경 파일 목록

EOF
    find "$UPGRADE_DIR" -type f ! -name "UPGRADE_REPORT.md" | sort | while read staged_file; do
      rel=$(echo "$staged_file" | sed "s|$UPGRADE_DIR/||")
      target_file="$TARGET/$rel"
      echo "### $rel" >> "$REPORT"
      echo '```diff' >> "$REPORT"
      diff -u "$target_file" "$staged_file" 2>/dev/null | head -50 >> "$REPORT"
      echo '```' >> "$REPORT"
      echo "" >> "$REPORT"
    done

    if [ "$MISSING_HOOK_COUNT" -gt 0 ]; then
      cat >> "$REPORT" <<EOF

## settings.json — 누락된 hook ${MISSING_HOOK_COUNT}개

$(echo -e "$MISSING_HOOKS")

**조치**: harness-upgrade 스킬이 누락된 hook을 추가합니다.
EOF
    fi

    cat >> "$REPORT" <<'EOF'

## 다음 단계

Claude Code에서 아래를 실행하세요:

> harness-upgrade 스킬을 실행해줘
EOF
  fi

  if [ "$MISSING_HOOK_COUNT" -gt 0 ]; then
    echo ""
    echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  ⚠️  settings.json에 누락된 hook ${MISSING_HOOK_COUNT}개 감지              ║${NC}"
    echo -e "${RED}║  반드시 harness-upgrade 스킬을 실행하세요.                ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
  fi

  chmod +x "$TARGET/.claude/scripts/"*.sh 2>/dev/null

  echo ""
  echo "═══ 업그레이드 준비 완료 ═══"
  echo -e "  ${GREEN}새 파일:   ${NEW_COUNT}개${NC}"
  echo -e "  ${YELLOW}병합 필요: ${STAGED_COUNT}개${NC} (.claude/.upgrade/에 스테이징됨)"
  if [ "$MISSING_HOOK_COUNT" -gt 0 ]; then
    echo -e "  ${RED}hook 누락: ${MISSING_HOOK_COUNT}개${NC}"
  fi
  echo -e "  변경 없음: ${UNCHANGED_COUNT}개"
  echo ""

  if [ "$STAGED_COUNT" -gt 0 ]; then
    echo "다음: Claude Code에서 'harness-upgrade 스킬을 실행해줘'"
  else
    if command -v jq > /dev/null 2>&1; then
      jq --arg v "$SRC_VERSION" --arg t "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        '.version = $v | .upgraded_at = $t' "$META" > "$META.tmp" && mv "$META.tmp" "$META"
    else
      sed_inplace "s/\"version\": \"[^\"]*\"/\"version\": \"$SRC_VERSION\"/" "$META"
      sed_inplace "s/\"upgraded_at\": [^,}]*/\"upgraded_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"/" "$META"
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

# .claude/agents/
echo ""
echo "📁 .claude/agents/"
for f in "$SCRIPT_DIR/.claude/agents/"*; do
  [ -f "$f" ] || continue
  copy_if_new "$f" "$TARGET/.claude/agents/$(basename "$f")"
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
for dir in WIP decisions guides incidents harness archived clusters; do
  if [ ! -d "$TARGET/docs/$dir" ]; then
    mkdir -p "$TARGET/docs/$dir"
    echo -e "  ${GREEN}✓ 생성${NC}: docs/$dir/"
    CREATED=$((CREATED + 1))
  else
    echo -e "  ${YELLOW}⏭ 스킵${NC}: docs/$dir/"
    SKIPPED=$((SKIPPED + 1))
  fi
done

# .gitkeep
for dir in WIP decisions guides incidents archived; do
  if [ -z "$(ls -A "$TARGET/docs/$dir" 2>/dev/null)" ]; then
    touch "$TARGET/docs/$dir/.gitkeep"
  fi
done

# 실행 권한
chmod +x "$TARGET/.claude/scripts/"*.sh 2>/dev/null

# starter 전용 git hook 설치 (is_starter: false면 스크립트가 즉시 exit)
bash "$TARGET/.claude/scripts/install-starter-hooks.sh" 2>/dev/null || true

# .gitignore — 하네스가 필요로 하는 머신별 파일 제외
GI="$TARGET/.gitignore"
if [ -f "$GI" ]; then
  grep -q '^\.claude/\.env_synced$' "$GI" || echo '.claude/.env_synced' >> "$GI"
  grep -q '^\.claude/\.compact_count$' "$GI" || echo '.claude/.compact_count' >> "$GI"
  grep -q '^\.claude/\.upgrade/$' "$GI" || echo '.claude/.upgrade/' >> "$GI"
  grep -q '^\.claude/scheduled_tasks\.lock$' "$GI" || echo '.claude/scheduled_tasks.lock' >> "$GI"
  grep -q '^\.claude/ts_errors\.log$' "$GI" || echo '.claude/ts_errors.log' >> "$GI"
  grep -q '^\.claude/memory/session-\*$' "$GI" || echo '.claude/memory/session-*' >> "$GI"
  grep -q '^\.claude/\.test-sandbox/$' "$GI" || echo '.claude/.test-sandbox/' >> "$GI"
else
  cat > "$GI" <<'EOF'
# 하네스 — 머신별/세션별 파일 제외
.claude/.env_synced
.claude/.compact_count
.claude/.upgrade/
.claude/scheduled_tasks.lock
.claude/ts_errors.log
.claude/memory/session-*
.claude/.test-sandbox/
EOF
  echo -e "  ${GREEN}✓ 생성${NC}: .gitignore"
  CREATED=$((CREATED + 1))
fi

# 하네스 메타데이터 기록 (프로파일 + 버전)
META="$TARGET/.claude/HARNESS.json"
if [ ! -f "$META" ]; then
  SRC_VER=$(grep -o '"version"[[:space:]]*:[[:space:]]*"[^"]*"' "$SCRIPT_DIR/.claude/HARNESS.json" 2>/dev/null | sed 's/.*"\([^"]*\)"$/\1/')
  INSTALLED_REF=$(git -C "$SCRIPT_DIR" rev-parse HEAD 2>/dev/null || echo "unknown")
  cat > "$META" <<EOF
{
  "profile": "$PROFILE",
  "skills": "$SKILLS",
  "version": "${SRC_VER:-unknown}",
  "installed_from_ref": "${INSTALLED_REF}",
  "installed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "upgraded_at": null
}
EOF
  echo -e "  ${GREEN}✓ 생성${NC}: .claude/HARNESS.json"
  CREATED=$((CREATED + 1))
fi

# 프로젝트 출범 문서 placeholder — harness-init이 아직 안 돌았을 때 "다음 할 일"을 보여줌
KICKOFF="$TARGET/docs/WIP/harness_init_pending.md"
if [ ! -f "$KICKOFF" ] && [ ! -f "$TARGET/docs/guides/project_kickoff.md" ]; then
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

# 스타터 remote 보호 — push 원천 차단
# 타겟이 git repo이고 origin이 스타터를 가리키면 pull-only로 전환
normalize_git_url() {
  echo "$1" | sed -e 's|^git@github.com:|https://github.com/|' \
                   -e 's|\.git$||' \
                   -e 's|/$||'
}

if git -C "$TARGET" rev-parse --is-inside-work-tree > /dev/null 2>&1; then
  STARTER_URL=$(normalize_git_url "$(git -C "$SCRIPT_DIR" remote get-url origin 2>/dev/null)")
  TARGET_ORIGIN=$(normalize_git_url "$(git -C "$TARGET" remote get-url origin 2>/dev/null)")

  if [ -n "$STARTER_URL" ] && [ "$TARGET_ORIGIN" = "$STARTER_URL" ]; then
    echo ""
    echo "🔒 스타터 remote 보호"
    if git -C "$TARGET" remote | grep -qx harness-upstream; then
      echo -e "  ${YELLOW}⏭${NC} harness-upstream이 이미 존재. 보호 스킵."
    else
      # origin → harness-upstream (pull 전용)으로 리네임
      git -C "$TARGET" remote rename origin harness-upstream
      # push URL을 DISABLED로 설정하여 push 원천 차단
      git -C "$TARGET" remote set-url --push harness-upstream DISABLED_PUSH_TO_STARTER
      echo -e "  ${GREEN}✓${NC} origin → harness-upstream (pull 전용)"
      echo -e "  ${YELLOW}ℹ${NC} 프로젝트 remote를 origin으로 등록하세요:"
      echo "    git remote add origin <프로젝트_repo_URL>"
    fi
  fi
fi

echo ""
echo "═══ 완료 ═══"
echo -e "  ${GREEN}생성: ${CREATED}개${NC}"
echo -e "  ${YELLOW}스킵: ${SKIPPED}개${NC}"
echo ""
echo "다음: claude code에서 프로젝트 열고 'harness-init 스킬을 실행해줘'"
