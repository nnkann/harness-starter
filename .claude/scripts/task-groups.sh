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

# name-status -M25로 rename 감지 확대 (기본 50% → 25% 유사도).
# WIP → completed 이동 시 본문이 갱신되어 유사도 낮아도 같은 논리 단위.
# STAGED는 "처리 대상 경로 전체" — R 라인은 old/new 둘 다 포함해야 그룹
# 할당 루프가 둘을 모두 같은 키에 매핑 가능.
NAME_STATUS=$(git diff --cached --name-status -M25 2>/dev/null)
[ -z "$NAME_STATUS" ] && exit 0

STAGED=$(echo "$NAME_STATUS" | awk -F'\t' '
  /^R[0-9]+\t/ { print $2; print $3; next }
  /^[ACDMT]\t/ { print $2 }
')

# rename pair 매핑 (R 라인 + WIP 라우팅 폴백)
# 1단계: git이 R로 인식한 쌍
RENAME_MAP=$(echo "$NAME_STATUS" | awk -F'\t' '
  /^R[0-9]+\t/ { print $2 "\t" $3 }
')
# 2단계: WIP 라우팅 폴백 — `docs/WIP/<folder>--<base>.md` 삭제 +
# `docs/<folder>/<base>.md` 추가 쌍은 확정적 WIP 이동 패턴. git이 rename
# 감지 실패해도(유사도 25% 미만) 본 휴리스틱이 같은 그룹으로 묶는다.
# 오탐 위험 없음 — 라우팅 태그가 경로 구조를 고유하게 만든다.
WIP_MOVE_MAP=$(echo "$NAME_STATUS" | awk -F'\t' '
  /^D\tdocs\/WIP\// {
    bn=$2; sub(/^docs\/WIP\//, "", bn)
    if (match(bn, /^([a-z]+)--(.+\.md)$/, m)) {
      dels[m[1] "/" m[2]] = $2
    }
    next
  }
  /^A\tdocs\// {
    rel=$2; sub(/^docs\//, "", rel)
    if (rel in dels) print dels[rel] "\t" $2
  }
')
RENAME_MAP="${RENAME_MAP}${RENAME_MAP:+$'\n'}${WIP_MOVE_MAP}"

rename_new_of() {
  local old="$1"
  [ -z "$RENAME_MAP" ] && return
  echo "$RENAME_MAP" | awk -F'\t' -v o="$old" '$1 == o { print $2; exit }'
}

# ─────────────────────────────────────────────
# 1. WIP 본문에서 (task, kind, 영향 파일) 추출
#    IMPACT_MAP 형식: wip_slug\ttask_id\tkind\tfile_pattern
# ─────────────────────────────────────────────
IMPACT_MAP=$(mktemp)
RAW_ASSIGN=$(mktemp)
trap "rm -f $IMPACT_MAP $RAW_ASSIGN" EXIT

# awk 단일 호출로 전체 WIP 처리 (파일당 fork 제거 — WIP 10+ 환경 성능 fix).
# FILENAME 기반으로 wip_slug 재계산. 파일 경계는 FNR==1로 감지해 상태 리셋.
WIP_FILES=(docs/WIP/*.md)
if [ -f "${WIP_FILES[0]}" ]; then
  awk '
    function reset_state() { in_block=0; task_id=""; kind="feature"; explicit_kind=0; in_impact=0; scan_lines=0 }
    FNR == 1 {
      # 파일 경계 — wip_slug 재계산 + 상태 리셋
      fn = FILENAME
      sub(/.*\//, "", fn); sub(/\.md$/, "", fn); sub(/^[^-]*--/, "", fn)
      wip_slug = fn
      reset_state()
    }
    /^### #?[0-9]/ {
      reset_state(); in_block=1
      match($0, /^### #?([0-9·]+)\./, m)
      task_id=m[1]
      gsub(/·/, "-", task_id)
      header=tolower($0)
      if (header ~ /근본 수정|버그|오탐|fix:|hotfix/) kind="bug"
      next
    }
    /^### / && in_block { in_block=0; in_impact=0; next }
    /^---[[:space:]]*$/ && in_block { in_block=0; in_impact=0; next }
    in_block && !explicit_kind {
      if ($0 ~ /^>[[:space:]]*kind:[[:space:]]*[a-z]+/) {
        match($0, /kind:[[:space:]]*([a-z]+)/, km)
        kind=km[1]
        explicit_kind=1
        next
      }
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
  ' "${WIP_FILES[@]}" >> "$IMPACT_MAP"
fi

# ─────────────────────────────────────────────
# 2. 유틸
# ─────────────────────────────────────────────
# naming.md "## 도메인 약어 (abbr)" 섹션 한정 추출.
# 파일 전역 스캔 시 "후보 도메인" 같은 다른 표와 충돌 가능.
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
    .claude/HARNESS.json|docs/harness/MIGRATIONS.md|README.md|CHANGELOG.md) return 0 ;;
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

  # rename의 old 경로면 new 경로로 그룹 판정 위임 (같은 논리 단위 보존).
  # 예: WIP/decisions--foo.md → decisions/foo.md 이동은 new 기준 그룹에 묶임.
  judge_path="$f"
  new_of=$(rename_new_of "$f")
  if [ -n "$new_of" ]; then
    judge_path="$new_of"
  fi

  # 메타 파일 (판정 경로 기준)
  if is_meta_file "$judge_path"; then
    echo -e "meta:config\t${f}" >> "$RAW_ASSIGN"
    continue
  fi

  abbr=$(detect_abbr "$judge_path")

  # WIP 본문 자체 (판정 경로 기준)
  if [[ "$judge_path" == docs/WIP/*.md ]]; then
    wip_bn=$(basename "$judge_path" .md)
    wip_slug="${wip_bn#*--}"
    echo -e "wip:${wip_slug}:${abbr}:feature\t${f}" >> "$RAW_ASSIGN"
    continue
  fi

  # task 매칭 (판정 경로 기준)
  if matched=$(match_wip_task "$judge_path"); then
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
