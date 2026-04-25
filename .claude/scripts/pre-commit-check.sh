#!/bin/bash
# 커밋 전 검사. 실패하면 exit 2로 커밋 차단.
#
# 출력 채널 분리:
# - stderr: 사용자 노출용 에러/경고 메시지
# - stdout: commit 스킬이 review 에이전트에 전달할 요약 (key: value 라인)
#
# 단일 실행 경로 (audit #1, 2026-04-22): 린트 + 전체 검사 1회로 통합.
# --lint-only 모드는 폐기 (Step 0 조기 종료 이점 미미 실측).
#
# stderr 정책 (audit #14, 2026-04-22):
# - 기본: 실패·위험·경고만 출력 (차단 ❌·위험 ⚡·잔여 ⚠·린트 실패 등)
# - 정상 상태 알림(연속 수정 카운트 등)은 출력하지 않음 (주석으로만 기록)
# - 정보성 메시지(HARNESS_EXPAND 통과 등)는 VERBOSE=1일 때만 출력

ERRORS=0

# review 전달용 요약 누적 변수 (stdout으로 마지막에 출력)
ALREADY_VERIFIED="lint todo_fixme test_location wip_cleanup"
RISK_FACTORS_SUMMARY=""

# 2. 린터 검사 (CLAUDE.md의 패키지 매니저 설정을 읽어서 동적 결정)
LINT_CMD=""
PKG_MGR=""

# CLAUDE.md에서 패키지 매니저 읽기
if [ -f "CLAUDE.md" ]; then
  PKG_MGR=$(grep -m1 '패키지 매니저:' CLAUDE.md 2>/dev/null | sed 's/.*패키지 매니저:[[:space:]]*//' | tr -d ' ')
fi

# 패키지 매니저 기반 lint 명령 결정
case "$PKG_MGR" in
  npm)  [ -f "package.json" ] && grep -q '"lint"' package.json 2>/dev/null && LINT_CMD="npm run lint --silent" ;;
  pnpm) [ -f "package.json" ] && grep -q '"lint"' package.json 2>/dev/null && LINT_CMD="pnpm lint" ;;
  yarn) [ -f "package.json" ] && grep -q '"lint"' package.json 2>/dev/null && LINT_CMD="yarn lint" ;;
  bun)  [ -f "package.json" ] && grep -q '"lint"' package.json 2>/dev/null && LINT_CMD="bun run lint" ;;
  pip|poetry|uv)
    if command -v ruff &>/dev/null; then
      LINT_CMD="ruff check . --quiet"
    fi
    ;;
  *)
    # 패키지 매니저 미설정 시 자동 감지 (기존 방식)
    if [ -f "package.json" ] && grep -q '"lint"' package.json 2>/dev/null; then
      if [ -f "pnpm-lock.yaml" ]; then LINT_CMD="pnpm lint"
      elif [ -f "yarn.lock" ]; then LINT_CMD="yarn lint"
      elif [ -f "bun.lockb" ]; then LINT_CMD="bun run lint"
      else LINT_CMD="npm run lint --silent"
      fi
    elif [ -f "pyproject.toml" ] && command -v ruff &>/dev/null; then
      LINT_CMD="ruff check . --quiet"
    fi
    ;;
esac

if [ -n "$LINT_CMD" ]; then
  # stdout/stderr 모두 버림 — pre-check stdout은 commit 스킬·review가
  # key:value로 파싱하므로 lint 출력이 섞이면 신호 누락 발생
  # (실측: 다운스트림 monorepo lint stdout이 test-pre-commit.sh 결과 12/21로 떨어짐)
  LINT_OUTPUT=$($LINT_CMD 2>&1)
  LINT_EXIT=$?
  if [ "$LINT_EXIT" -ne 0 ]; then
    # 도구 실종(shell이 바이너리 자체를 못 찾음)과 실제 lint 실패(rule 위반·
    # 플러그인 에러·crash)를 구분. 실종 → warn + skip (환경 문제, 커밋 계속).
    # 실패 → 차단 (ERRORS++).
    # incident: hn_test_isolation_git_log_leak.md (v0.18.3 원인 확정)
    #         + hn_lint_enoent_pattern_gaps.md (v0.18.4 패턴 정교화)
    #
    # 패턴 설계 원칙: shell이 "명령을 찾지 못함"을 알리는 고유 형식만 매칭.
    # ENOENT·"Cannot find module"·"No such file or directory"는 ESLint
    # 내부 crash와 구분 불가라 제거 (v0.18.4).
    #
    # 지원 환경:
    # - Windows cmd: `'X' is not recognized as an internal or external command`
    # - bash/zsh/sh/dash: `X: command not found` (라인 끝 고정)
    # - Alpine/BusyBox: `exec: X: not found`
    # - Dash/POSIX sh: `sh: N: X: not found`
    # - pnpm 고유: `ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL`
    if echo "$LINT_OUTPUT" | grep -qE \
"is not recognized as an internal or external command|\
: command not found$|\
command not found: [a-zA-Z0-9_./+-]+$|\
^exec: [^:]+: not found$|\
^sh: [0-9]+: [^:]+: not found$|\
ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL"; then
      echo "⚠ 린터 도구 미설치 또는 PATH 누락. 린트 스킵 (커밋 계속)." >&2
      echo "   (실행: $LINT_CMD — node_modules 확인 또는 \`npm install\` 검토)" >&2
      echo "$LINT_OUTPUT" | tail -5 >&2
      # ERRORS 증가시키지 않음 — 환경 문제는 다운스트림이 해결
    else
      echo "❌ 린터 에러. 에러 0에서만 커밋 가능. (실행: $LINT_CMD)" >&2
      echo "$LINT_OUTPUT" | tail -20 >&2
      ERRORS=$((ERRORS + 1))
    fi
  fi
fi

# ─────────────────────────────────────────────
# git diff 캐시 (22회 → 3회)
# Windows에서 git 프로세스 부팅이 호출당 ~30ms. 아래 3개만 실제 git 호출,
# 이후 모든 블록은 변수 재사용. staged 상태는 스크립트 실행 중 변하지 않음.
#
# TEST_MODE=1: _TEST_NAME_STATUS·_TEST_NUMSTAT·_TEST_DIFF_U0 환경변수로
# 입력 주입 가능. git 호출 없이 신호 판정 로직만 단위 테스트.
# ─────────────────────────────────────────────
if [ "${TEST_MODE:-0}" = "1" ] && [ -n "${_TEST_NAME_STATUS+x}" ]; then
  STAGED_NAME_STATUS="${_TEST_NAME_STATUS}"
  STAGED_NUMSTAT="${_TEST_NUMSTAT:-}"
  STAGED_DIFF_U0="${_TEST_DIFF_U0:-}"
else
  STAGED_NAME_STATUS=$(git diff --cached --name-status 2>/dev/null)
  STAGED_NUMSTAT=$(git diff --cached --numstat 2>/dev/null)
  STAGED_DIFF_U0=$(git diff --cached -U0 2>/dev/null)
fi
# 파생 (awk 1회로 이름 추출 — grep 파이프 제거)
STAGED_FILES=$(echo "$STAGED_NAME_STATUS" | awk 'NF>=2 {print $2}')

# diff stats 사전 계산 (numstat을 awk 1회로 added/deleted/files 모두 추출)
read -r ADDED_LINES DELETED_LINES_TOTAL TOTAL_FILES <<EOF
$(echo "$STAGED_NUMSTAT" | awk '
  NF>=3 { a+=$1; d+=$2; f++ }
  END   { printf "%d %d %d", a+0, d+0, f+0 }
')
EOF
TOTAL_LINES=$((ADDED_LINES + DELETED_LINES_TOTAL))
DIFF_STATS="files=${TOTAL_FILES},+${ADDED_LINES},-${DELETED_LINES_TOTAL}"

# 1. TODO/FIXME/HACK 검사 (staged 파일만)
# 제외: docs/, *.md, README/CHANGELOG (문서는 키워드 언급 정당)
#       .claude/scripts/ (하네스 스크립트 자체가 키워드를 검사하므로 자기 자신 제외)
todo_candidates=$(echo "$STAGED_FILES" | grep -vE '^docs/|\.(md|mdx)$|README|CHANGELOG|^\.claude/scripts/' 2>/dev/null)
if [ -n "$todo_candidates" ]; then
  todo_files=$(echo "$todo_candidates" | xargs grep -l "TODO\|FIXME\|HACK" 2>/dev/null)
  if [ -n "$todo_files" ]; then
    echo "❌ TODO/FIXME/HACK 발견. 코드가 아니라 docs/WIP/에 기록하라." >&2
    echo "$todo_files" | while read f; do
      echo "   $f" >&2
    done
    ERRORS=$((ERRORS + 1))
  fi
fi

# 3. tests/ 밖에 테스트 파일 있는지 검사
test_outside=$(echo "$STAGED_FILES" | grep -E '\.test\.|\.spec\.|_test\.' | grep -v '^tests/' | grep -v '^__tests__/')
if [ -n "$test_outside" ]; then
  echo "❌ 테스트 파일이 tests/ 밖에 있음:" >&2
  echo "$test_outside" | while read f; do
    echo "   $f" >&2
  done
  ERRORS=$((ERRORS + 1))
fi

# 3.5. dead link 증분 검사 (v0.18.6)
# 원칙: pre-check은 정적 검사. dead link는 구조적 정합성이라 pre-check 영역.
#
# 검사 범위 (증분):
#   A. 삭제·rename된 파일을 가리키는 기존 md 링크 (cluster·relates-to 등)
#   B. 추가·수정된 md 파일 안의 새 링크 대상이 실제로 존재하는지
#
# 이번 커밋이 유발한 dead link만 감지 → O(변경 규모).
DEAD_LINKS_FOUND=""

# A. 삭제·rename된 파일 목록 (name-status에서 D 또는 R의 원본 경로)
#    rename은 "R<score>\told\tnew" 형식. 원본(old)이 없어진 경로.
DELETED_OR_MOVED=$(echo "$STAGED_NAME_STATUS" | awk '
  $1 == "D"         { print $2 }
  $1 ~ /^R/ && NF>=3 { print $2 }
' | grep -E '\.md$' 2>/dev/null)

if [ -n "$DELETED_OR_MOVED" ]; then
  # 이 파일들을 가리키는 기존 md 링크 grep (docs/**, .claude/** md만).
  # basename으로 1차 후보 수집 후, 각 매치 링크의 **경로를 해석해
  # 실제 삭제된 파일과 일치할 때만 dead 판정** (audit #12 후속, 과탐 방지).
  while IFS= read -r removed; do
    [ -z "$removed" ] && continue
    removed_base=$(basename "$removed")
    # 1차 후보: basename만 매치
    HITS=$(grep -rn --include='*.md' -E "\]\([^)]*${removed_base}[^)]*\)" docs .claude 2>/dev/null)
    [ -z "$HITS" ] && continue
    while IFS= read -r hit; do
      # 형식: path:lineno:matched_line
      src=$(echo "$hit" | cut -d: -f1)
      # 해당 소스 파일이 이번 커밋에서 삭제·수정됐으면 스킵 (같이 정리됐을 것)
      if echo "$STAGED_FILES" | grep -qFx "$src"; then
        continue
      fi
      # 2차: 매치된 링크의 실제 경로를 파싱해 `removed`와 일치하는지 확인
      # hit 라인에서 ](path) 형태 모두 추출 후 각 경로를 src 기준 해석
      matched_line=$(echo "$hit" | cut -d: -f3-)
      # md 링크 path 추출 (앵커·쿼리 제거)
      while IFS= read -r link; do
        [ -z "$link" ] && continue
        link_clean="${link%%#*}"  # 앵커 제거
        link_clean="${link_clean%% *}"  # 공백 제거 방어
        # 경로 해석
        case "$link_clean" in
          /*) continue ;;  # 절대 경로 skip
          http*|mailto:*) continue ;;
          *) resolved="$(dirname "$src")/$link_clean" ;;
        esac
        resolved=$(echo "$resolved" | sed -e 's|/\./|/|g' -e ':a' -e 's|[^/]*/\.\./||' -e 'ta' -e 's|^\./||')
        # 해석된 경로가 삭제된 경로와 일치할 때만 dead
        if [ "$resolved" = "$removed" ]; then
          DEAD_LINKS_FOUND="${DEAD_LINKS_FOUND}\n   $hit"
          break  # 한 줄에 여러 링크 있어도 한 번만 보고
        fi
      done < <(echo "$matched_line" | grep -oE '\]\([^)]+\)' | sed -E 's/^\]\(|\)$//g')
    done <<< "$HITS"
  done <<< "$DELETED_OR_MOVED"
fi

# B. 추가·수정된 md 파일의 새 링크 대상 존재 검증
#    staged diff에서 추가된 라인(+)의 md 링크만 추출.
#    수정된 md만 대상. 전수 grep 아님.
MODIFIED_MD=$(echo "$STAGED_FILES" | grep -E '\.md$' 2>/dev/null)
if [ -n "$MODIFIED_MD" ]; then
  # 추가된 라인에서 md 링크 추출 (format: src\tlink_path)
  # awk로 diff 헤더 추적 + 추가 라인(+)에서 ](path.md) 패턴만
  # 중요: 현재 diff 대상 파일이 md일 때만 링크 추출. 코드 파일(.sh·.ts 등)
  # 안의 `](path.md)` 같은 정규식 예시·문자열은 링크 아님 → 오탐 방지.
  LINK_PAIRS=$(echo "$STAGED_DIFF_U0" | awk '
    /^diff --git / {
      path=$NF; sub(/^b\//, "", path)
      is_md = (path ~ /\.md$/)
      next
    }
    /^\+\+\+/ || /^---/ { next }
    is_md && /^\+/ {
      line=$0
      # 백틱 안의 매칭은 링크 아님 (인라인 코드 · 코드 예시). 휴리스틱으로
      # 백틱으로 감싸인 구간을 먼저 제거 후 남은 텍스트에서 링크 추출.
      # 완벽한 md 파서 아님 — 한 줄 안에서만 처리. 실측 오탐의 대부분 케이스
      # ("`](path.md)`"·"`](abbr.md)`" 같은 설명용 예시) 해소.
      gsub(/`[^`]*`/, "", line)
      while (match(line, /\]\(([^)]+\.md)([)#][^)]*)?\)/, m)) {
        link=m[1]
        # 외부·앵커만 skip
        if (link !~ /^https?:\/\// && link !~ /^mailto:/) {
          printf "%s\t%s\n", path, link
        }
        line=substr(line, RSTART+RLENGTH)
      }
    }
  ')

  if [ -n "$LINK_PAIRS" ]; then
    while IFS=$'\t' read -r src link; do
      [ -z "$src" ] || [ -z "$link" ] && continue
      # 경로 해석
      case "$link" in
        docs/*) resolved="$link" ;;
        /*) continue ;;  # 절대 경로는 저장소 밖, skip
        *) resolved="$(dirname "$src")/$link" ;;
      esac
      # 정규화: ./ 제거, a/b/../ → a/
      resolved=$(echo "$resolved" | sed -e 's|/\./|/|g' -e ':a' -e 's|[^/]*/\.\./||' -e 'ta' -e 's|^\./||')
      # 앵커 분리
      resolved_path="${resolved%%#*}"
      # 존재 확인 (staged add된 파일도 고려 — staging 영역이므로 FS에 있음)
      if [ ! -f "$resolved_path" ]; then
        DEAD_LINKS_FOUND="${DEAD_LINKS_FOUND}\n   $src → $link (resolved: $resolved_path, 파일 없음)"
      fi
    done <<< "$LINK_PAIRS"
  fi
fi

# C. frontmatter `relates-to.path` dead link (audit #12, T36)
#    B와 달리 diff 라인이 아닌 staged 파일의 현재 frontmatter 전체를 검사.
#    이유: relates-to는 frontmatter 상단에 있어 수정 안 한 커밋에서도 기존
#    relates-to가 dead일 수 있음 — 이번 커밋이 대상 파일을 삭제/rename했다면.
#    하지만 증분 원칙 유지: 이번 커밋에서 추가/수정된 md만 검사.
if [ -n "$MODIFIED_MD" ]; then
  while IFS= read -r md_src; do
    [ -z "$md_src" ] && continue
    [ ! -f "$md_src" ] && continue
    # frontmatter 블록만 추출: 첫 `---` ~ 두 번째 `---` 사이
    FM=$(awk 'BEGIN{n=0} /^---[[:space:]]*$/{n++; next} n==1{print} n>=2{exit}' "$md_src")
    [ -z "$FM" ] && continue
    # relates-to 섹션 안의 `- path: ...` 라인만 추출 (멀티라인 YAML 리스트)
    # 간단 파서: `relates-to:` 뒤 들여쓴 블록만. 다른 top-key 만나면 종료.
    RT_PATHS=$(echo "$FM" | awk '
      /^relates-to:[[:space:]]*$/ { in_rt=1; next }
      in_rt && /^[^[:space:]]/ { in_rt=0 }
      in_rt && /^[[:space:]]+-[[:space:]]+path:[[:space:]]*/ {
        sub(/^[[:space:]]+-[[:space:]]+path:[[:space:]]*/, "")
        gsub(/^["'"'"']|["'"'"']$/, "")
        sub(/[[:space:]]*#.*$/, "")  # 인라인 주석 제거
        if (length($0)>0) print
      }
    ')
    [ -z "$RT_PATHS" ] && continue
    while IFS= read -r rt_path; do
      [ -z "$rt_path" ] && continue
      # 경로 해석: rules/docs.md 규칙에 따라 **docs/ 루트 기준 상대 경로**
      # (예: `relates-to: harness/hn_X.md` → `docs/harness/hn_X.md`).
      # `../`로 시작하는 명시적 상대경로는 md 파일 기준으로 해석 (다운스트림
      # 호환성 — 일부 기존 파일이 `../harness/...` 형식 사용).
      case "$rt_path" in
        /*) continue ;;
        ../*|./*)
          resolved="$(dirname "$md_src")/$rt_path"
          ;;
        *)
          # docs/ 루트 기준 (규칙 원본)
          resolved="docs/$rt_path"
          ;;
      esac
      resolved=$(echo "$resolved" | sed -e 's|/\./|/|g' -e ':a' -e 's|[^/]*/\.\./||' -e 'ta' -e 's|^\./||')
      resolved_path="${resolved%%#*}"
      if [ ! -f "$resolved_path" ]; then
        DEAD_LINKS_FOUND="${DEAD_LINKS_FOUND}\n   $md_src frontmatter relates-to: $rt_path (resolved: $resolved_path, 파일 없음)"
      fi
    done <<< "$RT_PATHS"
  done <<< "$MODIFIED_MD"
fi

if [ -n "$DEAD_LINKS_FOUND" ]; then
  echo "❌ dead link 감지 (이번 커밋이 유발):" >&2
  echo -e "$DEAD_LINKS_FOUND" >&2
  echo "   대응: 링크를 수정하거나, 이동된 파일의 새 경로로 갱신" >&2
  ERRORS=$((ERRORS + 1))
fi

# 4. docs/WIP/에 completed/abandoned 파일이 남아있는지
if [ -d "docs/WIP" ]; then
  # 프론트매터 또는 인라인 status에서 completed/abandoned 감지
  stale=$(grep -rl '^status:.*\(completed\|abandoned\)\|^> status:.*\(completed\|abandoned\)' docs/WIP/ 2>/dev/null)
  if [ -n "$stale" ]; then
    echo "⚠️ docs/WIP/에 완료/중단 문서가 남아있음. 이동 필요:" >&2
    echo "$stale" | while read f; do
      echo "   $(basename "$f")" >&2
    done
  fi
fi

# 5. 위험도 수집 (audit #2·9, 2026-04-22 — 모드 조건 제거).
# staging이 stage를 결정하지만, review prompt의 우선순위 가중치는
# risk_factors가 담당. 모드 불문 항상 수집.
RISK_REASONS=""

# 5a. 변경 파일 수 5개 이상 (TOTAL_FILES 사전 계산 재사용)
if [ "$TOTAL_FILES" -ge 5 ]; then
  RISK_REASONS="${RISK_REASONS}\n   - 변경 파일 ${TOTAL_FILES}개 (≥5)"
fi

# 5b. 삭제 라인 50줄 이상 (DELETED_LINES_TOTAL 사전 계산 재사용)
if [ "$DELETED_LINES_TOTAL" -ge 50 ]; then
  RISK_REASONS="${RISK_REASONS}\n   - 삭제 ${DELETED_LINES_TOTAL}줄 (≥50)"
fi

# 5c. 핵심 설정 파일 변경
if echo "$STAGED_FILES" | grep -qE '^(CLAUDE\.md|\.claude/settings\.json|\.claude/rules/|\.claude/scripts/)'; then
  RISK_REASONS="${RISK_REASONS}\n   - 핵심 설정 파일 변경"
fi

# 5d. 보안 관련 패턴 (파일명 우선, 없으면 diff 본문)
if echo "$STAGED_FILES" | grep -qiE 'auth|token|secret|key|credential|password' \
   || echo "$STAGED_DIFF_U0" | grep -qiE '^\+.*(auth|token|secret|key|credential|password)'; then
  RISK_REASONS="${RISK_REASONS}\n   - 보안 관련 패턴 감지"
fi

# 5e. 인프라/배포 파일
if echo "$STAGED_FILES" | grep -qiE '(Dockerfile|docker-compose|\.github/workflows/|\.gitlab-ci|deploy)'; then
  RISK_REASONS="${RISK_REASONS}\n   - 인프라/배포 파일 변경"
fi

# 5f. 단일 파일에서 추가+삭제 동시 30줄 이상 (numstat 재사용)
COMPLEX=$(echo "$STAGED_NUMSTAT" | awk '$1+0 >= 30 && $2+0 >= 30 {print $3; exit}')
if [ -n "$COMPLEX" ]; then
  RISK_REASONS="${RISK_REASONS}\n   - 구조적 수정 감지: ${COMPLEX}"
fi

if [ -n "$RISK_REASONS" ]; then
  # review 전달용: 한 줄로 압축 (개행 → '; ')
  RISK_FACTORS_SUMMARY=$(echo -e "$RISK_REASONS" | sed 's/^[[:space:]]*-[[:space:]]*//' | grep -v '^$' | paste -sd';' -)
fi

# 6. 같은 파일 연속 수정 카운트 (정보용 — 차단·경고 없음)
# staging.md S10 신호와 review가 참고. 사용자 가시 메시지는 출력하지 않음.
# 면제 파일: 버전 범프·이력 갱신처럼 매 커밋마다 같이 변경되는 정상 패턴
REPEAT_RANGE=5
REPEAT_EXEMPT_REGEX='^(\.claude/HARNESS\.json|docs/clusters/.*\.md)$'

# TEST_MODE=1: git log skip — S10 연속 수정 감지는 실제 커밋 이력 필요,
# 단위 테스트 대상 아님. T13·T39.4 같은 S10 케이스는 통합 테스트로 분리.
if [ "${TEST_MODE:-0}" = "1" ]; then
  RECENT_FILES=""
else
  RECENT_FILES=$(git log -${REPEAT_RANGE} --name-only --format= 2>/dev/null | grep -v '^$' | sort)
fi
REPEAT_WARN_HIT=""
REPEAT_BLOCK_HIT=""
REPEAT_BLOCK_CORE=""  # 차단 대상 핵심 파일: "파일명\t카운트" 형식, newline 구분

# 핵심 설정 파일 — 연속 수정 시 차단 복원 (단순화 작업으로 일반 차단은
# 제거됐지만, settings.json·rules/·scripts/ 같은 핵심 파일은 반복 수정
# 시 추측 수정 패턴 가능성 높아 차단)

# S10 루프: while + grep-cFx(N×1 fork) → awk 1패스 (hash 사전 구축)
# RECENT_FILES를 hash에 쌓고 STAGED_FILES 행을 O(1) 조회.
# sentinel(---STAGED---) 방식으로 두 입력을 단일 stdin에 연결.
_s10_result=$(awk -v rng="$REPEAT_RANGE" '
  /^---STAGED---$/ { phase=1; next }
  !phase { cnt[$0]++; next }
  phase {
    f = $0
    if (f == "") next
    if (f ~ /^\.claude\/HARNESS\.json$/ || f ~ /^docs\/clusters\//) next
    c = cnt[f] + 0
    is_core = (f == "CLAUDE.md" || f ~ /^\.claude\/settings\.json$/ \
               || f ~ /^\.claude\/rules\// || f ~ /^\.claude\/scripts\//)
    if (c >= 3) {
      if (is_core) print "CORE\t" f "\t" c
      else         print "BLOCK\t" f "\t" c "\t" rng
    } else if (c >= 2) {
      print "WARN\t" f "\t" c "\t" rng
    }
  }
' <<< "$(printf "%s\n---STAGED---\n%s" "$RECENT_FILES" "$STAGED_FILES")")

while IFS=$'\t' read -r kind f c rng_; do
  case "$kind" in
    CORE)
      REPEAT_BLOCK_CORE="${REPEAT_BLOCK_CORE}${f}	${c}"$'\n'
      REPEAT_BLOCK_HIT="${REPEAT_BLOCK_HIT}\n   - $f (최근 ${REPEAT_RANGE}커밋 중 ${c}회)"
      ;;
    BLOCK)
      REPEAT_BLOCK_HIT="${REPEAT_BLOCK_HIT}\n   - $f (최근 ${REPEAT_RANGE}커밋 중 ${c}회)"
      ;;
    WARN)
      REPEAT_WARN_HIT="${REPEAT_WARN_HIT}\n   - $f (최근 ${REPEAT_RANGE}커밋 중 ${c}회)"
      ;;
  esac
done <<< "$_s10_result"

# 핵심 파일 차단 처리
if [ -n "$REPEAT_BLOCK_CORE" ]; then
  while IFS=$'\t' read -r f c; do
    [ -z "$f" ] && continue
    echo "" >&2
    echo "❌ 핵심 설정 파일 ${c}회 연속 수정: $f" >&2
    echo "   추측 수정 가능성. 다음을 먼저 확인:" >&2
    echo "   1. git log -5 -- $f (이전 수정 사유)" >&2
    echo "   2. docs/incidents/ (관련 사례)" >&2
    echo "   3. 공식 문서 (rules/internal-first.md)" >&2
    echo "   정당한 점진 확장이면 HARNESS_EXPAND=1 prefix로 우회:" >&2
    echo "     HARNESS_EXPAND=1 git commit -m \"...\"" >&2
    # HARNESS_EXPAND=1은 bash-guard.sh가 command prefix에서 파싱해 env로 전달.
    if [ "$HARNESS_EXPAND" = "1" ]; then
      [ -n "$VERBOSE" ] && echo "   (HARNESS_EXPAND=1 감지 — 통과)" >&2
    else
      ERRORS=$((ERRORS + 1))
    fi
  done <<< "$REPEAT_BLOCK_CORE"
fi

# DIFF_STATS·TOTAL_FILES·ADDED_LINES·DELETED_LINES_TOTAL·TOTAL_LINES는
# 공유 변수 블록에서 이미 계산됨 (중복 제거).

# 7. Staging 신호 감지 (rules/staging.md 참조)
# 변경 성격에 맞는 review 강도(stage)를 자동 결정하기 위한 신호 감지.
# 출력: signals=S1,S2,...; domains=...; domain_grades=...;
#       multi_domain=true|false; repeat_count=max=N; recommended_stage=...
SIGNALS=""

# helper: 신호 추가 (문자열 + 연관 배열 동시 갱신)
# 문자열은 stdout 출력용, 배열은 내부 조회용 (서브쉘 grep 제거)
declare -A SIG_SET=()
add_signal() {
  if [ -z "$SIGNALS" ]; then SIGNALS="$1"; else SIGNALS="${SIGNALS},$1"; fi
  SIG_SET[$1]=1
}
# 내부 조회 (exit status로 반환 — 서브쉘 grep 대비 ~10ms 절감 × 호출당)
has_sig() { [ -n "${SIG_SET[$1]:-}" ]; }

# ─────────────────────────────────────────────
# S1~S6·S11·S14·S15 통합 분류 (awk 1패스)
# 기존: 블록별 echo|grep|grep 파이프라인 ~20회 (~300ms)
# 변경: STAGED_FILES를 awk가 한 번 훑으며 각 카테고리 카운트 반환.
#       "단독 여부"(S4/S5/S6)는 bash에서 TOTAL_FILES - 카테고리카운트로 산출.
# 참고: https://www.howtogeek.com/i-found-using-grep-or-sed-in-bash-scripts-is-painfully-slow-but-heres-how-i-fixed-it/
# ─────────────────────────────────────────────
# lock·meta·doc은 상호 배타 (앞선 매치에서 next로 빠짐 → 이중 카운트 방지).
# S11·S14·S15·S1·S2는 다른 카테고리와 공존 가능하므로 존재 플래그만.
read -r S1_FILE_HIT S2_HIT LOCK_COUNT META_COUNT DOC_COUNT S11_HIT S14_HIT S15_HIT <<EOF
$(echo "$STAGED_FILES" | awk '
  {
    # S1 파일명: 테스트·docs·예제·helper/utils 면제
    if (tolower($0) ~ /auth|token|secret|key|credential|password|\.env/ \
        && !($0 ~ /\.(test|spec)\.|\/tests?\/|\/__tests__\/|^docs\/|\.md$|\/example|-helper\.|-utils?\./)) s1=1
    # S2 핵심 설정
    if (/^(CLAUDE\.md|\.claude\/settings\.json|\.claude\/rules\/|\.claude\/scripts\/|\.claude\/hooks\/|Dockerfile|docker-compose|\.github\/workflows\/)/) s2=1
    # S11 빌드/CI
    if (/^(scripts\/.*\.sh$|\.husky\/|Makefile$)/) s11=1
    # S14 마이그레이션
    if (/(^|\/)migrations\/|^alembic\/versions\/|^prisma\/migrations\//) s14=1
    # S15 패키지 manifest
    if (/^(package\.json|pyproject\.toml|Cargo\.toml|go\.mod|requirements.*\.txt|Gemfile|composer\.json)$/) s15=1
  }
  # 상호 배타 카테고리 (lock > meta > doc 우선순위)
  /^(package-lock\.json|pnpm-lock\.yaml|yarn\.lock|bun\.lockb|uv\.lock|Cargo\.lock|go\.sum|composer\.lock|Gemfile\.lock)$/ { lock++; next }
  # S5 메타: HARNESS.json·clusters·memory·CHANGELOG (is_starter 무관)
  /^(\.claude\/HARNESS\.json|docs\/clusters\/.*\.md|\.claude\/memory\/.*\.md|CHANGELOG\.md)$/ { meta++; next }
  /^(docs\/|.*\.md$)/ { doc++; next }
  END {
    printf "%d %d %d %d %d %d %d %d",
      s1+0, s2+0, lock+0, meta+0, doc+0, s11+0, s14+0, s15+0
  }
')
EOF
NON_LOCK=$((TOTAL_FILES - LOCK_COUNT))
NON_META=$((TOTAL_FILES - META_COUNT))
NON_DOC=$((TOTAL_FILES - DOC_COUNT))

# S1 라인 hit: 실제 시크릿 패턴 (전체 diff 대상, 단일 grep 유지 — 대형 텍스트라 awk도 이점 적음)
S1_LINES=$(echo "$STAGED_DIFF_U0" | grep -m1 -iE '^\+.*(sb_secret_|service_role|sk_live_|sk_test_|ghp_|AKIA[0-9A-Z]{16}|password\s*=)' 2>/dev/null)

S1_LEVEL=""  # "" | "file-only" | "line-confirmed"
if [ -n "$S1_LINES" ]; then
  add_signal "S1"
  S1_LEVEL="line-confirmed"
elif [ "$S1_FILE_HIT" = "1" ]; then
  add_signal "S1"
  S1_LEVEL="file-only"
fi

[ "$S2_HIT" = "1" ] && add_signal "S2"

# S3. 신규 파일만 (모든 staged가 ^A) — name-status 필요, awk 1회
if [ "$TOTAL_FILES" -gt 0 ]; then
  NON_ADDED=$(echo "$STAGED_NAME_STATUS" | awk '$1!="A"{c++} END{print c+0}')
  [ "$NON_ADDED" = "0" ] && add_signal "S3"
fi

# S4·S5·S6: 단독 여부 판정 (위 awk에서 나온 카운트 사용)
# "단독"은 다른 카테고리 카운트가 0이어야 성립. NON_LOCK·NON_META·NON_DOC는
# 위 awk에서 "자기 외 모든 카운트 합"으로 계산됨.
if [ "$LOCK_COUNT" -gt 0 ] && [ "$NON_LOCK" = "0" ]; then
  add_signal "S4"
fi
if [ "$META_COUNT" -gt 0 ] && [ "$NON_META" = "0" ]; then
  add_signal "S5"
fi
if [ "$DOC_COUNT" -gt 0 ] && [ "$NON_DOC" = "0" ] && ! has_sig S5; then
  add_signal "S6"
fi

# S7. 일반 코드 (S1~S6·S11·S14·S15 어디에도 안 속함)
# 일단 다른 신호 다 본 뒤 마지막에 결정 (아래)

# S8. 공유 모듈 변경 — 언어별 시그니처 패턴
# 라인 시작 부분의 진짜 선언만 잡음 (문자열·주석 안 잡힘)
# 면제: 테스트 파일 (export 흔하지만 공유 모듈 아님)
S8_HIT=""
S8_FILES=$(echo "$STAGED_FILES" | grep -vE '\.(test|spec)\.|/tests?/|/__tests__/' 2>/dev/null)
if [ -n "$S8_FILES" ]; then
  # awk 1패스: diff --git 헤더로 현재 파일 확장자 추적 + 확장자별 패턴 매칭.
  # 테스트 파일은 제외. 언어 4개를 단일 pass로 처리해 git 호출 4회 → 0회.
  S8_HIT=$(echo "$STAGED_DIFF_U0" | awk '
    /^diff --git / {
      # "diff --git a/path b/path" → b/path 경로
      path=$NF; sub(/^b\//, "", path)
      ext=""
      if (path ~ /\.(test|spec)\.|\/tests?\/|\/__tests__\//) { ext=""; next }
      if (path ~ /\.(ts|tsx|js|jsx)$/) ext="js"
      else if (path ~ /\.py$/)         ext="py"
      else if (path ~ /\.go$/)         ext="go"
      else if (path ~ /\.(java|cs)$/)  ext="java"
      next
    }
    ext=="js"   && /^[+-]export[[:space:]]+(default[[:space:]]+)?(async[[:space:]]+)?(class|function|interface|type|enum|const|let|var)[[:space:]]+/ { print "hit"; exit }
    ext=="py"   && /^[+-](async[[:space:]]+)?(def|class)[[:space:]]+[a-zA-Z_]/                                                                       { print "hit"; exit }
    ext=="go"   && /^[+-](func|type|var|const)[[:space:]]+[A-Z][a-zA-Z0-9_]*/                                                                         { print "hit"; exit }
    ext=="java" && /^[+-][[:space:]]*public[[:space:]]+(static[[:space:]]+)?(class|interface|enum|[a-zA-Z<>]+[[:space:]]+[a-zA-Z_])/                  { print "hit"; exit }
  ')
  if [ -n "$S8_HIT" ]; then
    add_signal "S8"
  fi
fi

# S9. 도메인 추출 + 등급 매핑
DOMAINS=""
DOMAIN_GRADES=""

# 9.1. docs 파일 프론트매터 domain 필드 추출 (while+grep 루프 → awk 1패스)
# 각 docs/*.md 파일을 awk로 직접 읽어 첫 번째 'domain:' 행 추출.
# 기존: while read f; grep -m1 | sed = N×2 forks → awk 0 forks (내장 getline)
_doc_files=$(echo "$STAGED_FILES" | grep -E '^docs/.*\.md$')
DOC_DOMAINS=""
if [ -n "$_doc_files" ]; then
  DOC_DOMAINS=$(echo "$_doc_files" | awk '
    {
      f = $0
      if (system("test -f " f) != 0) next
      while ((getline line < f) > 0) {
        if (line ~ /^domain:[[:space:]]*/) {
          d = line; sub(/^domain:[[:space:]]*/, "", d); gsub(/[[:space:]]/, "", d)
          if (d != "") print d
          close(f); break
        }
        if (line ~ /^---/ && NR > 1) { close(f); break }
      }
    }
  ' | sort -u)
fi

# 9.2. WIP 파일명 접두사 (grep+sed → awk 1패스)
WIP_DOMAINS=$(echo "$STAGED_FILES" | awk -F'/' '
  /^docs\/WIP\/[^-]+--/ {
    fname = $NF; sub(/--.*/, "", fname); print fname
  }
' | sort -u)

ALL_DOMAINS=$(printf "%s\n%s\n" "$DOC_DOMAINS" "$WIP_DOMAINS" | grep -v '^$' | sort -u | paste -sd',' -)
DOMAINS="$ALL_DOMAINS"

# 9.3. 등급 매핑 (naming.md 1패스 awk — grep+sed 파이프 제거)
if [ -n "$ALL_DOMAINS" ] && [ -f ".claude/rules/naming.md" ]; then
  # awk로 naming.md "도메인 등급" 섹션을 1패스로 읽고 critical/meta 도메인 리스트 추출.
  # 결과: "CRITICAL domain1 domain2 ..." + "META domain1 ..." 두 줄
  _grade_info=$(awk '
    /^## 도메인 등급/ { flag=1; next }
    /^## / { flag=0 }
    flag && /\*\*critical\*\*/ {
      line = $0; sub(/.*:/, "", line); gsub(/[*()[:space:]]/, " ", line)
      gsub(/,/, " ", line); print "CRITICAL " line
    }
    flag && /\*\*meta\*\*/ {
      line = $0; sub(/.*:/, "", line); gsub(/[*()[:space:]]/, " ", line)
      gsub(/,/, " ", line); print "META " line
    }
  ' .claude/rules/naming.md)

  # bash 연관 배열로 등급 조회 (서브쉘 grep 0회)
  declare -A GRADE_MAP=()
  while IFS=' ' read -r kind rest; do
    for d in $rest; do
      [ -z "$d" ] && continue
      if [ "$kind" = "CRITICAL" ]; then GRADE_MAP[$d]="critical"
      elif [ "$kind" = "META" ];     then GRADE_MAP[$d]="meta"
      fi
    done
  done <<< "$_grade_info"

  GRADES=""
  for d in $(echo "$ALL_DOMAINS" | tr ',' ' '); do
    [ -z "$d" ] && continue
    g="${GRADE_MAP[$d]:-normal}"
    if [ -z "$GRADES" ]; then GRADES="$g"; else GRADES="${GRADES},${g}"; fi
  done
  DOMAIN_GRADES="$GRADES"

  [ -n "$DOMAIN_GRADES" ] && add_signal "S9"
fi

# 다중 도메인
DOMAIN_COUNT=$(echo "$ALL_DOMAINS" | tr ',' '\n' | grep -cv '^$')
MULTI_DOMAIN="false"
[ "$DOMAIN_COUNT" -ge 2 ] && MULTI_DOMAIN="true"

# S10. 연속 수정 (이미 step 6에서 감지 — REPEAT_WARN_HIT/REPEAT_BLOCK_HIT 재활용)
REPEAT_MAX=0
if [ -n "$REPEAT_BLOCK_HIT" ]; then
  REPEAT_MAX=$(echo -e "$REPEAT_BLOCK_HIT" | grep -oE '[0-9]+회' | grep -oE '[0-9]+' | sort -nr | head -1)
elif [ -n "$REPEAT_WARN_HIT" ]; then
  REPEAT_MAX=$(echo -e "$REPEAT_WARN_HIT" | grep -oE '[0-9]+회' | grep -oE '[0-9]+' | sort -nr | head -1)
fi
[ -z "$REPEAT_MAX" ] && REPEAT_MAX=0
if [ "$REPEAT_MAX" -ge 2 ]; then
  add_signal "S10"
fi

# S11·S14·S15: 위 통합 awk에서 이미 플래그 설정됨
[ "$S11_HIT" = "1" ] && add_signal "S11"
[ "$S14_HIT" = "1" ] && add_signal "S14"
[ "$S15_HIT" = "1" ] && add_signal "S15"

# S7. 일반 코드 (위 신호들 중 S5/S6/S4/S3 어디에도 안 속하면)
if [ "$TOTAL_FILES" -gt 0 ] && ! (has_sig S3 || has_sig S4 || has_sig S5 || has_sig S6); then
  add_signal "S7"
fi

# 8. 범용성 오염 검출은 review 에이전트로 이전 (rules/contamination.md 삭제됨).
# 셸 정규식은 한글 형태소·문맥 판단 불가 → LLM이 staged diff로 직접 판단.
# is_starter 정보는 commit 스킬이 review prompt의 "전제 컨텍스트"에 주입한다.

# 9. (제거) test-strategist 신호 — audit #7/#15 2026-04-22 폐기.
# 114초 실측 대비 효용 부족으로 에이전트·호출 로직·pre-check 신호 전부 제거.

# Stage 결정 (v0.17.0 — 5줄 룰, SSOT: .claude/rules/staging.md)
# 경로 기반 이진 판정. 신호 값(S1~S15)은 review prompt용으로 여전히 유지.
#
# 룰 1~4 첫 매칭 (2026-04-22 — bulk 스테이지 폐기):
#   1. 업스트림 위험 경로 (.claude/scripts|agents|hooks|settings.json) → deep
#   2. S1 line-confirmed OR S14 OR S8                                  → deep
#   3. S5 OR S4 OR WIP cleanup 단독                                    → skip
#   4. 나머지                                                          → standard

RECOMMENDED_STAGE=""

# 룰 1: 업스트림 위험 경로 hit
if echo "$STAGED_FILES" | grep -qE '^(\.claude/scripts/|\.claude/agents/|\.claude/hooks/|\.claude/settings\.json$)'; then
  RECOMMENDED_STAGE="deep"
fi

# 룰 2: 치명 신호
if [ -z "$RECOMMENDED_STAGE" ]; then
  if [ "$S1_LEVEL" = "line-confirmed" ] || has_sig S14 || has_sig S8; then
    RECOMMENDED_STAGE="deep"
  fi
fi

# 룰 3: skip 조건 (메타·lock 단독, WIP 단독, 문서 ≤5줄, 이동 커밋)
if [ -z "$RECOMMENDED_STAGE" ]; then
  # 이동 커밋: staged 전체가 R(rename) + M(meta only) 조합만
  # 기존: grep -c + grep -v + wc -l + grep -c (8 forks) → awk 1패스 (0 fork)
  read -r RENAME_COUNT NON_MOVE M_NON_META <<< "$(echo "$STAGED_NAME_STATUS" | awk '
    BEGIN { rename=0; non_move=0; m_non_meta=0 }
    /^R/ { rename++; next }
    /^M/ {
      f = $2
      if (f !~ /^docs\/clusters\/|^\.claude\/HARNESS\.json$|^\.claude\/memory\/|^CHANGELOG\.md$/)
        m_non_meta++
      next
    }
    { non_move++ }
    END { print rename, non_move, m_non_meta }
  ')"
  if [ "${RENAME_COUNT:-0}" -gt 0 ] && [ "${NON_MOVE:-0}" -eq 0 ] && [ "${M_NON_META:-0}" -eq 0 ]; then
    RECOMMENDED_STAGE="skip"
    IS_MOVE_COMMIT=1  # 격상 면제 플래그
  # S5 단독 (메타 파일만)
  elif has_sig S5 && ! (has_sig S7 || has_sig S2 || has_sig S8 || has_sig S14); then
    RECOMMENDED_STAGE="skip"
  # S4 단독 (lock 파일만, S7 미동반)
  elif has_sig S4 && ! has_sig S7; then
    RECOMMENDED_STAGE="skip"
  # S6 단독 + docs/WIP/ 파일만 — 계획 문서 수정은 review 대상 아님.
  # 코드·메타·설정 동반이면 제외.
  # has_sig 조합: bash 연관 배열 조회 (서브쉘 0) — grep -qE 2회 제거.
  elif has_sig S6 \
       && ! (has_sig S7 || has_sig S2 || has_sig S8 || has_sig S14 || has_sig S11) \
       && ! echo "$STAGED_FILES" | grep -qE '^\.claude/(skills|agents)/' \
       && echo "$STAGED_FILES" | grep -qE '^docs/WIP/' \
       && ! echo "$STAGED_FILES" | grep -vqE '^docs/WIP/'; then
    RECOMMENDED_STAGE="skip"
  # S6 단독 + ≤5줄 (문서 경미 수정) — audit #17, 2026-04-22.
  elif has_sig S6 && [ "$TOTAL_LINES" -le 5 ] \
       && ! (has_sig S7 || has_sig S2 || has_sig S8 || has_sig S14 || has_sig S11) \
       && ! echo "$STAGED_FILES" | grep -qE '^\.claude/(skills|agents)/'; then
    RECOMMENDED_STAGE="skip"
  fi
fi

# 룰 5: 나머지 → standard
if [ -z "$RECOMMENDED_STAGE" ]; then
  RECOMMENDED_STAGE="standard"
fi

# Stage 결정 (2단계: 격상 — 유지)
# 이동 커밋(rename+meta only)은 S10 격상 면제 — 내용 변경 없는 이동에 격상 불필요
IS_MOVE_COMMIT="${IS_MOVE_COMMIT:-0}"
# B/C: S10 연속 수정 격상
if [ "$IS_MOVE_COMMIT" = "1" ]; then
  : # 이동 커밋 — 격상 스킵
elif [ "$REPEAT_MAX" -ge 3 ]; then
  RECOMMENDED_STAGE="deep"
elif [ "$REPEAT_MAX" = "2" ]; then
  case "$RECOMMENDED_STAGE" in
    skip) RECOMMENDED_STAGE="standard" ;;  # skip→micro 대신 standard 직행 (5줄 룰에서 micro 없음)
    micro) RECOMMENDED_STAGE="standard" ;;
    standard) RECOMMENDED_STAGE="deep" ;;
  esac
fi

# 룰 A(다중 도메인 격상)는 5줄 룰에서 폐기 — staging.md 참조.
# 경로 기반 룰 1이 이미 "업스트림 혼합 시 deep" 효과 커버.

# 결과
if [ $ERRORS -gt 0 ]; then
  echo "" >&2
  echo "🚫 커밋 차단. 위 문제를 해결하라." >&2
  # 차단 시에도 stdout 요약 출력 (디버깅·로그용). exit 2 후 commit 스킬은 무시.
  echo "pre_check_passed: false"
  echo "already_verified: ${ALREADY_VERIFIED}"
  echo "risk_factors: ${RISK_FACTORS_SUMMARY}"
  echo "diff_stats: ${DIFF_STATS}"
  echo "signals: ${SIGNALS}"
  echo "domains: ${DOMAINS}"
  echo "domain_grades: ${DOMAIN_GRADES}"
  echo "multi_domain: ${MULTI_DOMAIN}"
  echo "repeat_count: max=${REPEAT_MAX}"
  echo "recommended_stage: ${RECOMMENDED_STAGE}"
  echo "s1_level: ${S1_LEVEL}"
  exit 2
fi

# 거대 변경 감지 → stderr 경고 (강제 아님, 사용자 선택)
# incident `hn_review_maxturns_verdict_miss`: review maxTurns(6) 상한이
# 거대 diff에서 verdict 미출력 유발. --bulk 우회 경로는 2026-04-22 폐기.
# 답은 스코프 분리.
if [ "${TOTAL_FILES:-0}" -gt 30 ] || [ "${ADDED_LINES:-0}" -gt 1500 ] \
   || [ "${DELETED_LINES_TOTAL:-0}" -gt 1500 ]; then
  echo "⚠ 대규모 변경 감지 (files=${TOTAL_FILES}, +${ADDED_LINES}, -${DELETED_LINES_TOTAL})." >&2
  echo "  review maxTurns 한계로 verdict 신뢰도 저하 + 검토 피로 누적 가능." >&2
  echo "  권장: 스코프를 나눠 작은 커밋 여러 개로 분리. 논리 단위별로 staging." >&2
fi

# ─────────────────────────────────────────────
# 커밋 분리 판정 (audit #18 — 글로벌 원칙, 1회 판정)
# 규칙:
#   1. HARNESS_SPLIT_SUB=1 → 판정 블록 스킵 (이미 분리된 sub-커밋)
#   2. 그룹화 축 (첫 매치):
#      - naming.md "경로 → 도메인 매핑" (다운스트림)
#      - docs/ 하위는 **파일 1개 = 그룹 1개** (각 문서가 독립 task)
#      - .claude/skills/{N}/** → `skill:{N}` (각 스킬별 task)
#      - .claude/scripts/** → `scripts`
#      - .claude/agents/** → `agents`
#      - .claude/rules/** → `rules`
#      - .claude/hooks/** → `hooks`
#      - .claude/HARNESS.json / .claude/settings.json / CLAUDE.md / README.md
#        → `config`
#      - 나머지 → `misc`
#   3. 그룹 수 1 → 분리 불필요
#   4. 그룹 수 2+ → split 권장
# ─────────────────────────────────────────────
SPLIT_PLAN=0
SPLIT_ACTION="single"
GROUP_ASSIGN=""

if [ "${HARNESS_SPLIT_SUB:-0}" = "1" ]; then
  SPLIT_PLAN=1
  SPLIT_ACTION="sub"
elif [ "${TEST_MODE:-0}" != "1" ] && [ "${TOTAL_FILES:-0}" -gt 0 ] && [ -x .claude/scripts/task-groups.sh ]; then
  # task × abbr × kind 3축 그룹화 (audit #18, task-groups.sh 위임).
  # 실패 시 경로 기반 폴백.
  # TEST_MODE=1: split 판정 skip — 단위 테스트 대상 아님.
  GROUP_ASSIGN=$(bash .claude/scripts/task-groups.sh 2>/dev/null || echo "")
  if [ -n "$GROUP_ASSIGN" ]; then
    SPLIT_PLAN=$(echo "$GROUP_ASSIGN" | awk -F'\t' 'NF>=2{print $1}' | sort -u | wc -l)
    if [ "$SPLIT_PLAN" -ge 2 ]; then
      SPLIT_ACTION="split"
    else
      SPLIT_ACTION="single"
    fi
  fi
fi

# prior_session_files: 세션 시작 시점 unstaged 파일 중 현재 staged와 교집합.
# 이전 세션 잔여물이 staged에 섞였을 가능성 신호. 자동 분리 아님 — 경고용.
PRIOR_FILES="none"
if [ -f ".claude/memory/session-start-unstaged.txt" ]; then
  STAGED_LIST=$(git diff --cached --name-only 2>/dev/null)
  if [ -n "$STAGED_LIST" ]; then
    PRIOR_FILES=$(comm -12 \
      <(sort .claude/memory/session-start-unstaged.txt 2>/dev/null) \
      <(echo "$STAGED_LIST" | sort) \
      | tr '\n' ',' | sed 's/,$//')
    [ -z "$PRIOR_FILES" ] && PRIOR_FILES="none"
  fi
fi

# 통과 시 stdout 요약 (commit 스킬이 캡처해서 review prompt에 주입)
echo "pre_check_passed: true"
echo "already_verified: ${ALREADY_VERIFIED}"
echo "risk_factors: ${RISK_FACTORS_SUMMARY}"
echo "diff_stats: ${DIFF_STATS}"
echo "signals: ${SIGNALS}"
echo "domains: ${DOMAINS}"
echo "domain_grades: ${DOMAIN_GRADES}"
echo "multi_domain: ${MULTI_DOMAIN}"
echo "repeat_count: max=${REPEAT_MAX}"
echo "recommended_stage: ${RECOMMENDED_STAGE}"
echo "s1_level: ${S1_LEVEL}"
echo "split_plan: ${SPLIT_PLAN}"
echo "split_action_recommended: ${SPLIT_ACTION}"
echo "prior_session_files: ${PRIOR_FILES}"

# 그룹 상세 (split 권장 시만 출력, stdout 비대화 방지)
if [ "$SPLIT_ACTION" = "split" ] && [ -n "$GROUP_ASSIGN" ]; then
  # 그룹 순서 고정: scripts → agents → skills → hooks → rules → config → docs → misc
  echo "$GROUP_ASSIGN" | awk -F'\t' '
    BEGIN {
      # 우선순위 부여
      prio["scripts"]=1; prio["agents"]=2; prio["rules"]=3; prio["hooks"]=4
      prio["config"]=5; prio["misc"]=99
    }
    {
      g=$1; f=$2
      if (!($1 in order)) { order[$1]=NR }
      group_files[g]=group_files[g] (group_files[g]?",":"") f
    }
    END {
      # 우선순위 정해진 것은 정렬, 그 외는 첫 등장 순서
      n=0
      for (g in group_files) {
        keys[++n]=g
      }
      # 버블 정렬 (작은 데이터)
      for (i=1; i<=n; i++) {
        for (j=i+1; j<=n; j++) {
          pi=(keys[i] in prio)?prio[keys[i]]:(10+order[keys[i]])
          pj=(keys[j] in prio)?prio[keys[j]]:(10+order[keys[j]])
          # skill:X 계열은 agents 뒤, rules 앞 (우선순위 2.5 효과)
          if (keys[i] ~ /^skill:/) pi=2.5
          if (keys[j] ~ /^skill:/) pj=2.5
          # doc:X 계열은 config 뒤 (우선순위 5.5)
          if (keys[i] ~ /^doc:/) pi=5.5
          if (keys[j] ~ /^doc:/) pj=5.5
          if (pi > pj) { t=keys[i]; keys[i]=keys[j]; keys[j]=t }
        }
      }
      for (i=1; i<=n; i++) {
        g=keys[i]
        printf "split_group_%d_name: %s\n", i, g
        printf "split_group_%d_files: %s\n", i, group_files[g]
      }
    }
  '
fi
