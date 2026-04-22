#!/bin/bash
# task-groups.sh — staged 파일을 task × abbr × kind 3축으로 그룹화 (audit #18).
#
# 축:
#   1. WIP 소속 — 어느 논리 단위의 task인지
#   2. abbr — 파일명 약어 (naming.md 도메인 약어). 없으면 no-abbr
#   3. kind — task 블록의 `> kind:` 마커. 없으면 feature
#
# 그룹 키 형식:
#   wip:<slug>:<abbr>:<kind>
#   path:기타:<abbr>:<kind>   — WIP 매칭 실패 폴백
#   meta:config                — 메타 파일 (흡수 대상)
#
# 출력 (stdout, tab-separated):
#   group_name<TAB>file_path

set -e

STAGED=$(git diff --cached --name-only 2>/dev/null)
[ -z "$STAGED" ] && exit 0

# ─────────────────────────────────────────────
# 1. WIP 본문에서 (task, kind, 영향 파일) 추출
#    IMPACT_MAP 형식: wip_slug\ttask_id\tkind\tfile_pattern
# ─────────────────────────────────────────────
IMPACT_MAP=$(mktemp)
RAW_ASSIGN=$(mktemp)
trap "rm -f $IMPACT_MAP $RAW_ASSIGN" EXIT

for wip in docs/WIP/*.md; do
  [ ! -f "$wip" ] && continue
  wip_bn=$(basename "$wip" .md)
  wip_slug="${wip_bn#*--}"

  awk -v wip_slug="$wip_slug" '
    BEGIN { in_block=0; task_id=""; kind="feature"; explicit_kind=0; in_impact=0; scan_lines=0 }
    /^### #?[0-9]/ {
      in_block=1; in_impact=0; kind="feature"; explicit_kind=0; scan_lines=0
      match($0, /^### #?([0-9·]+)\./, m)
      task_id=m[1]
      gsub(/·/, "-", task_id)
      # 헤더 자체에서 자동 추론
      header=tolower($0)
      if (header ~ /근본 수정|버그|오탐|fix:|hotfix/) kind="bug"
      next
    }
    /^### / && in_block { in_block=0; in_impact=0; next }
    /^---[[:space:]]*$/ && in_block { in_block=0; in_impact=0; next }
    in_block && !explicit_kind {
      # 명시적 `> kind: X` 마커 우선 (헤더 추론 override)
      if ($0 ~ /^>[[:space:]]*kind:[[:space:]]*[a-z]+/) {
        match($0, /kind:[[:space:]]*([a-z]+)/, km)
        kind=km[1]
        explicit_kind=1
        next
      }
      # 본문 초반 5줄에서 자동 추론 (헤더 매치 없을 때)
      if (kind == "feature" && scan_lines < 5 && $0 !~ /^[[:space:]]*$/) {
        body=tolower($0)
        if (body ~ /근본 수정|버그|오탐|fix:|hotfix|회귀/) kind="bug"
        scan_lines++
      }
    }
    in_block && /^\*\*영향 파일\*\*/ { in_impact=1 }
    in_block && in_impact {
      line=$0
      while (match(line, /`([^`]+)`/, m)) {
        p=m[1]
        if (p ~ /[\/.]/ && p !~ /^--/ && p !~ /^(Step|--)/) {
          print wip_slug "\t" task_id "\t" kind "\t" p
        }
        line=substr(line, RSTART+RLENGTH)
      }
      if ($0 ~ /^[[:space:]]*$/ || $0 ~ /^\*\*[^영]/) in_impact=0
    }
  ' "$wip" >> "$IMPACT_MAP"
done

# ─────────────────────────────────────────────
# 2. 유틸
# ─────────────────────────────────────────────
# naming.md "도메인 약어" 표에서 abbr 목록 추출
extract_abbrs() {
  awk '
    /^\| [a-z_]+[[:space:]]*\|[[:space:]]*[a-z]{2,3}[[:space:]]*\|/ {
      gsub(/\|/, " ")
      print $2
    }
  ' .claude/rules/naming.md 2>/dev/null | sort -u
}

ABBR_LIST=$(extract_abbrs | tr '\n' '|' | sed 's/|$//')

# 파일명에서 abbr 추출 (첫 매치, 라우팅·불투명 prefix 통과)
detect_abbr() {
  local filename="$1"
  local basename="${filename##*/}"
  basename="${basename%.md}"
  basename="${basename#*--}"  # 라우팅 접두사 제거
  [ -z "$ABBR_LIST" ] && { echo "no-abbr"; return; }
  local abbr=$(echo "$basename" | grep -oE "(^|[_-])(${ABBR_LIST})_" | head -1 \
    | sed -E "s/^[_-]?(${ABBR_LIST})_\$/\1/")
  echo "${abbr:-no-abbr}"
}

is_meta_file() {
  case "$1" in
    .claude/HARNESS.json|docs/harness/promotion-log.md|docs/harness/MIGRATIONS.md|README.md|CHANGELOG.md) return 0 ;;
    docs/clusters/*.md) return 0 ;;
    *) return 1 ;;
  esac
}

# 파일 → (wip_slug, kind) 매칭
# 성공: echo "slug<TAB>kind" + return 0
# 실패: return 1
match_wip_task() {
  local f="$1"
  local bn=$(basename "$f")
  local best_slug="" best_kind=""
  while IFS=$'\t' read -r wip_slug task_id kind pattern; do
    [ -z "$pattern" ] && continue
    if [ "$f" = "$pattern" ]; then
      echo "${wip_slug}	${kind}"; return 0
    fi
    case "$f" in
      */"$pattern") echo "${wip_slug}	${kind}"; return 0 ;;
    esac
    if [ "$bn" = "$(basename "$pattern")" ] && [ -z "$best_slug" ]; then
      best_slug="$wip_slug"; best_kind="$kind"
    fi
  done < "$IMPACT_MAP"
  [ -n "$best_slug" ] && { echo "${best_slug}	${best_kind}"; return 0; }
  return 1
}

# ─────────────────────────────────────────────
# 3. 1차 할당: wip:<slug>:<abbr>:<kind> 키 생성
# ─────────────────────────────────────────────
while IFS= read -r f; do
  [ -z "$f" ] && continue

  # 메타 파일
  if is_meta_file "$f"; then
    echo -e "meta:config\t${f}" >> "$RAW_ASSIGN"
    continue
  fi

  abbr=$(detect_abbr "$f")

  # WIP 본문 자체
  if [[ "$f" == docs/WIP/*.md ]]; then
    wip_bn=$(basename "$f" .md)
    wip_slug="${wip_bn#*--}"
    # WIP 본문 자체의 kind는 feature (WIP은 여러 task를 담는 컨테이너)
    echo -e "wip:${wip_slug}:${abbr}:feature\t${f}" >> "$RAW_ASSIGN"
    continue
  fi

  # task 매칭
  if matched=$(match_wip_task "$f"); then
    slug=$(echo "$matched" | cut -f1)
    kind=$(echo "$matched" | cut -f2)
    echo -e "wip:${slug}:${abbr}:${kind}\t${f}" >> "$RAW_ASSIGN"
  else
    echo -e "path:기타:${abbr}:feature\t${f}" >> "$RAW_ASSIGN"
  fi
done <<< "$STAGED"

# ─────────────────────────────────────────────
# 4. 메타 흡수: meta:config → 가장 큰 non-meta 그룹에 흡수
# ─────────────────────────────────────────────
LARGEST=$(awk -F'\t' '$1 != "meta:config" {count[$1]++} END{
  max=0; best=""
  for (k in count) if (count[k] > max) { max=count[k]; best=k }
  print best
}' "$RAW_ASSIGN")

if [ -n "$LARGEST" ]; then
  awk -F'\t' -v largest="$LARGEST" '
    $1 == "meta:config" { print largest "\t" $2; next }
    { print $0 }
  ' "$RAW_ASSIGN"
else
  cat "$RAW_ASSIGN"
fi
