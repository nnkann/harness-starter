#!/bin/bash
# docs-ops.sh — docs-manager 스킬 대체 스크립트 (audit #10, 2026-04-22).
#
# 이전의 docs-manager 스킬은 전부 규칙 기반 작업(프론트매터 검증·파일 이동·
# clusters 갱신·관계 맵 정합성)이라 LLM 판단이 불필요. 332줄 스킬을 폐기하고
# 본 스크립트로 이관.
#
# 서브커맨드:
#   validate                       프론트매터·약어 검증
#   move <wip-file>                WIP 파일을 `{대상폴더}--` 접두사에 따라 이동
#   reopen <completed-file>        완료 문서를 WIP로 되돌림
#   cluster-update                 모든 clusters/*.md 자동 갱신
#   verify-relates                 relates-to.path 정합성 검사
#
# 종료 코드:
#   0 성공
#   1 일반 오류
#   2 차단 (completed 전환 차단 등)
#
# SSOT 참조:
#   - 파일명 규칙: .claude/rules/naming.md
#   - 폴더 구조: .claude/rules/docs.md
#   - completed 전환 차단 키워드: .claude/rules/docs.md "## completed 전환 차단"

set -e

CMD="${1:-}"
shift || true

# ─────────────────────────────────────────────────
# 유틸
# ─────────────────────────────────────────────────

# naming.md에서 약어 목록 추출 — "## 도메인 약어 (abbr)" 섹션 한정.
# 과거에는 파일 전역 스캔이라 "후보 도메인" 같은 다른 표에 우연히 맞는
# `| word | 2-3자 |` 패턴도 약어로 오인식됐다. 섹션 스코프로 제한.
extract_abbrs() {
  awk '
    /^## 도메인 약어/ { in_section=1; next }
    /^## / && in_section { in_section=0 }
    in_section && /^\| [a-z_]+[[:space:]]*\|[[:space:]]*[a-z]{2,3}[[:space:]]*\|/ {
      gsub(/\|/, " ")
      print $2
    }
  ' .claude/rules/naming.md 2>/dev/null | sort -u
}

# 파일명에서 abbr 추출 (첫 매치 정책, 라우팅/불투명 prefix 통과)
# ABBR_PATTERN 환경변수가 설정돼 있으면 extract_abbrs() 재호출 없이 재사용.
# cmd_cluster_update() 같은 대량 호출 경로에서 I/O 반복 제거용.
detect_abbr() {
  local filename="$1"
  local basename="${filename##*/}"
  basename="${basename%.md}"
  # 라우팅 접두사 (`decisions--` 등) 제거
  basename="${basename#*--}"
  local abbrs="${ABBR_PATTERN:-$(extract_abbrs | tr '\n' '|' | sed 's/|$//')}"
  [ -z "$abbrs" ] && return 1
  echo "$basename" | grep -oE "(^|[_-])(${abbrs})_" | head -1 \
    | sed -E "s/^[_-]?(${abbrs})_\$/\1/"
}

# frontmatter 블록 추출 (첫 `---` ~ 두 번째 `---`)
extract_frontmatter() {
  awk 'BEGIN{n=0} /^---[[:space:]]*$/{n++; next} n==1{print} n>=2{exit}' "$1"
}

# frontmatter 필드 값 추출 (간단 파서)
fm_field() {
  local file="$1" field="$2"
  extract_frontmatter "$file" | awk -v f="$field" '
    $0 ~ "^"f":" {
      sub("^"f":[[:space:]]*", "")
      gsub(/^["'"'"']|["'"'"']$/, "")
      print
      exit
    }
  '
}

# ─────────────────────────────────────────────────
# validate
# ─────────────────────────────────────────────────
cmd_validate() {
  local errors=0
  local warnings=0
  echo "## docs 정합성 검증"
  echo ""

  # 도메인 목록 수집 (naming.md "도메인 목록 > 확정")
  local domains=$(awk '/^확정:/{sub(/^확정:[[:space:]]*/, ""); gsub(/,[[:space:]]*/, "\n"); print}' \
    .claude/rules/naming.md 2>/dev/null)

  # 약어 표 수집
  local abbrs=$(extract_abbrs)

  # 약어 중복 검사
  local dup=$(echo "$abbrs" | sort | uniq -d)
  if [ -n "$dup" ]; then
    echo "❌ 약어 중복: $dup"
    errors=$((errors + 1))
  fi

  # docs/ 하위 모든 md 순회
  while IFS= read -r file; do
    [ -z "$file" ] && continue
    [ ! -f "$file" ] && continue

    local title=$(fm_field "$file" "title")
    local domain=$(fm_field "$file" "domain")
    local status=$(fm_field "$file" "status")
    local created=$(fm_field "$file" "created")

    if [ -z "$title" ]; then
      echo "❌ $file: title 누락"
      errors=$((errors + 1))
    fi
    if [ -z "$domain" ]; then
      echo "❌ $file: domain 누락"
      errors=$((errors + 1))
    elif ! echo "$domains" | grep -qFx "$domain"; then
      echo "⚠️  $file: domain '$domain' 이(가) naming.md 확정 목록에 없음"
      warnings=$((warnings + 1))
    fi
    if [ -z "$status" ]; then
      echo "❌ $file: status 누락"
      errors=$((errors + 1))
    elif ! echo "pending in-progress completed abandoned sample" | grep -qw "$status"; then
      echo "⚠️  $file: status '$status' 비정상"
      warnings=$((warnings + 1))
    fi
    if [ -z "$created" ]; then
      echo "❌ $file: created 누락"
      errors=$((errors + 1))
    elif ! echo "$created" | grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'; then
      echo "⚠️  $file: created 형식 비정상 ($created)"
      warnings=$((warnings + 1))
    fi

    # 날짜 suffix 패턴 경고 (`_\d{6}\.md`)
    local bn="${file##*/}"
    if echo "$bn" | grep -qE '_[0-9]{6}\.md$'; then
      echo "⚠️  $file: 파일명 날짜 suffix 금지 (naming.md)"
      warnings=$((warnings + 1))
    fi
  done < <(find docs -name '*.md' -type f 2>/dev/null)

  echo ""
  echo "결과: 오류 $errors, 경고 $warnings"
  [ "$errors" -gt 0 ] && return 1
  return 0
}

# ─────────────────────────────────────────────────
# move <wip-file>
# ─────────────────────────────────────────────────
cmd_move() {
  local src="$1"
  [ -z "$src" ] && { echo "사용법: docs-ops.sh move <wip-file>" >&2; exit 1; }
  [ ! -f "$src" ] && { echo "❌ 파일 없음: $src" >&2; exit 1; }
  [[ "$src" != docs/WIP/* ]] && { echo "❌ WIP 파일만 이동 가능: $src" >&2; exit 1; }

  local bn="${src##*/}"
  local prefix="${bn%%--*}"
  local rest="${bn#*--}"

  local target_folder=""
  case "$prefix" in
    decisions|guides|incidents|harness) target_folder="docs/$prefix" ;;
    *)
      echo "❌ 접두사 '$prefix--' 인식 불가. decisions/guides/incidents/harness 중 하나여야 함" >&2
      exit 1
      ;;
  esac

  # 날짜 suffix 거부
  if echo "$rest" | grep -qE '_[0-9]{6}\.md$'; then
    echo "❌ 파일명 날짜 suffix 금지 (naming.md): $rest" >&2
    exit 1
  fi

  # completed 전환 차단 검사 (rules/docs.md 키워드 구현)
  local body=$(awk '
    /^---$/{c++; next}
    c<2{next}
    /^## (처리 결과|원본|회고|처리|결과)/{skip=1}
    !skip
  ' "$src")

  local hits=$(echo "$body" | grep -nE -- '(TODO|FIXME)' | grep -vE '(✅|완료|처리됨|done)' || true)
  local headers=$(echo "$body" | grep -nE '^\s*##\s*(후속|미결|미결정|추후|나중에|별도로)' || true)
  local items=$(echo "$body" | grep -nE '^\s*[-*0-9.]+\s.*(후속|미결|미결정|추후|나중에|별도로).*$' \
    | grep -vE '(✅|완료|처리됨|done)' || true)

  if [ -n "$hits" ] || [ -n "$headers" ] || [ -n "$items" ]; then
    echo "🚫 completed 전환 차단: $src 본문에 미결 패턴 존재" >&2
    [ -n "$hits" ] && echo "$hits" | sed 's/^/   TODO: /' >&2
    [ -n "$headers" ] && echo "$headers" | sed 's/^/   HEADER: /' >&2
    [ -n "$items" ] && echo "$items" | sed 's/^/   ITEM: /' >&2
    echo "   대응: (a) 잔여를 별도 WIP로 분리 (b) 본문에서 키워드 제거 후 재시도" >&2
    exit 2
  fi

  local dest="$target_folder/$rest"
  git mv "$src" "$dest"

  # frontmatter 갱신: status → completed, updated → 오늘
  local today=$(date +%Y-%m-%d)
  # sed로 in-place 갱신 (GNU sed / BSD sed 양쪽 호환)
  if grep -q '^status:' "$dest"; then
    sed -i.bak -E "s/^status:[[:space:]]*.*$/status: completed/" "$dest" && rm -f "${dest}.bak"
  fi
  if grep -q '^updated:' "$dest"; then
    sed -i.bak -E "s/^updated:[[:space:]]*.*$/updated: $today/" "$dest" && rm -f "${dest}.bak"
  else
    # updated 없으면 created 뒤에 추가
    sed -i.bak -E "s/^(created:[[:space:]]*.*)$/\1\nupdated: $today/" "$dest" && rm -f "${dest}.bak"
  fi

  echo "## 문서 이동 완료"
  echo ""
  echo "이동됨: $src → $dest"
  echo "갱신됨: status=completed, updated=$today"
}

# ─────────────────────────────────────────────────
# reopen <completed-file>
# ─────────────────────────────────────────────────
cmd_reopen() {
  local src="$1"
  [ -z "$src" ] && { echo "사용법: docs-ops.sh reopen <completed-file>" >&2; exit 1; }
  [ ! -f "$src" ] && { echo "❌ 파일 없음: $src" >&2; exit 1; }
  [[ "$src" == docs/WIP/* ]] && { echo "❌ 이미 WIP: $src" >&2; exit 1; }

  local bn="${src##*/}"
  local folder=$(dirname "$src" | sed 's|^docs/||')
  local routing=""
  case "$folder" in
    decisions|guides|incidents|harness) routing="$folder" ;;
    *) echo "❌ 지원되지 않는 폴더: $folder" >&2; exit 1 ;;
  esac

  local dest="docs/WIP/${routing}--${bn}"
  git mv "$src" "$dest"

  # status: completed → in-progress
  sed -i.bak -E "s/^status:[[:space:]]*completed[[:space:]]*$/status: in-progress/" "$dest" \
    && rm -f "${dest}.bak"

  echo "## 완료 문서 재개"
  echo ""
  echo "되돌림: $src → $dest"
  echo "갱신됨: status=in-progress"
}

# ─────────────────────────────────────────────────
# cluster-update — 모든 clusters/*.md를 docs/ 현재 상태로 재생성
# ─────────────────────────────────────────────────
cmd_cluster_update() {
  mkdir -p docs/clusters
  local abbrs=$(extract_abbrs)
  [ -z "$abbrs" ] && { echo "❌ naming.md 약어 표 비어있음" >&2; exit 1; }
  # detect_abbr()이 매번 extract_abbrs()를 재호출하지 않도록 패턴을 미리 계산해 export.
  # 337파일 × 17약어 환경에서 I/O 호출 5,729회 → 1회로 감소.
  export ABBR_PATTERN=$(echo "$abbrs" | tr '\n' '|' | sed 's/|$//')

  local updated=0
  while IFS= read -r abbr; do
    [ -z "$abbr" ] && continue

    # 도메인 이름 찾기 (역매핑)
    local domain=$(awk -v ab="$abbr" '
      /^\| [a-z_]+[[:space:]]*\|[[:space:]]*[a-z]{2,3}[[:space:]]*\|/ {
        gsub(/\|/, " ")
        if ($2 == ab) { print $1 }
      }
    ' .claude/rules/naming.md | head -1)
    [ -z "$domain" ] && domain="$abbr"

    local cluster="docs/clusters/${domain}.md"
    local today=$(date +%Y-%m-%d)

    # 해당 abbr의 문서 수집 (WIP 제외, archived 제외)
    local docs_list=$(find docs -name '*.md' -type f \
      -not -path 'docs/WIP/*' -not -path 'docs/archived/*' -not -path 'docs/clusters/*' \
      2>/dev/null | while IFS= read -r f; do
      local detected=$(detect_abbr "$f" || true)
      if [ "$detected" = "$abbr" ]; then
        echo "$f"
      fi
    done | sort)

    {
      echo "---"
      echo "title: ${domain} 클러스터"
      echo "domain: ${domain}"
      echo "tags: [cluster, index]"
      echo "status: completed"
      echo "created: 2026-04-16"
      echo "updated: ${today}"
      echo "---"
      echo ""
      echo "# ${domain} 클러스터"
      echo ""
      echo "도메인 ${domain}(${abbr}) 소속 문서 목록. docs-ops.sh cluster-update 자동 생성."
      echo ""
      if [ -n "$docs_list" ]; then
        echo "## 문서"
        echo ""
        while IFS= read -r f; do
          local title=$(fm_field "$f" "title")
          [ -z "$title" ] && title="${f##*/}"
          echo "- [${title}](../${f#docs/})"
        done <<< "$docs_list"
      else
        echo "_(문서 없음)_"
      fi
    } > "$cluster"
    updated=$((updated + 1))
  done <<< "$abbrs"

  echo "clusters/ 갱신: ${updated}개 파일"
}

# ─────────────────────────────────────────────────
# verify-relates — relates-to.path 정합성 (pre-check Step 3.5와 별개, 전수)
# ─────────────────────────────────────────────────
cmd_verify_relates() {
  local errors=0
  while IFS= read -r file; do
    [ -z "$file" ] && continue
    [ ! -f "$file" ] && continue

    # frontmatter 내 relates-to.path 전부 순회
    local fm=$(extract_frontmatter "$file")
    [ -z "$fm" ] && continue
    local rt_paths=$(echo "$fm" | awk '
      /^relates-to:[[:space:]]*$/ { in_rt=1; next }
      in_rt && /^[^[:space:]]/ { in_rt=0 }
      in_rt && /^[[:space:]]+-[[:space:]]+path:[[:space:]]*/ {
        sub(/^[[:space:]]+-[[:space:]]+path:[[:space:]]*/, "")
        gsub(/^["'"'"']|["'"'"']$/, "")
        sub(/[[:space:]]*#.*$/, "")
        if (length($0)>0) print
      }
    ')
    [ -z "$rt_paths" ] && continue
    while IFS= read -r rp; do
      [ -z "$rp" ] && continue
      local resolved="$(dirname "$file")/$rp"
      resolved=$(echo "$resolved" | sed -e 's|/\./|/|g' -e ':a' -e 's|[^/]*/\.\./||' -e 'ta' -e 's|^\./||')
      local rpath="${resolved%%#*}"
      if [ ! -f "$rpath" ]; then
        echo "⚠️  $file: relates-to '$rp' (resolved: $rpath) 존재하지 않음"
        errors=$((errors + 1))
      fi
    done <<< "$rt_paths"
  done < <(find docs -name '*.md' -type f 2>/dev/null)

  echo ""
  echo "결과: 미연결 relates-to $errors 건"
  [ "$errors" -gt 0 ] && return 1
  return 0
}

# ─────────────────────────────────────────────────
# 라우팅
# ─────────────────────────────────────────────────
case "$CMD" in
  validate) cmd_validate ;;
  move) cmd_move "$@" ;;
  reopen) cmd_reopen "$@" ;;
  cluster-update) cmd_cluster_update ;;
  verify-relates) cmd_verify_relates ;;
  *)
    echo "사용법: docs-ops.sh {validate|move|reopen|cluster-update|verify-relates} [args]" >&2
    echo "" >&2
    echo "서브커맨드:" >&2
    echo "  validate                     프론트매터·약어 검증" >&2
    echo "  move <wip-file>              WIP 접두사로 대상 폴더 이동 + status=completed" >&2
    echo "  reopen <completed-file>      완료 문서를 WIP로 되돌림 + status=in-progress" >&2
    echo "  cluster-update               모든 clusters/*.md 재생성" >&2
    echo "  verify-relates               relates-to.path 정합성 전수 검사" >&2
    exit 1
    ;;
esac
