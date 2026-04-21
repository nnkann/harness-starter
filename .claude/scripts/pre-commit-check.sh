#!/bin/bash
# 커밋 전 검사. 실패하면 exit 2로 커밋 차단.
#
# 출력 채널 분리:
# - stderr: 사용자 노출용 에러/경고 메시지
# - stdout: commit 스킬이 review 에이전트에 전달할 요약 (key: value 라인)
#
# 모드:
# - (기본): 전체 검사 + stdout 요약 출력
# - --lint-only: 린터만 빠르게 검사 (commit 스킬 Step 0 조기 종료용).
#                TODO·test 위치·WIP 잔여·signals 모두 건너뜀. stdout 요약도 없음.
LINT_ONLY=0
if [ "$1" = "--lint-only" ]; then
  LINT_ONLY=1
fi

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
    echo "❌ 린터 에러. 에러 0에서만 커밋 가능. (실행: $LINT_CMD)" >&2
    echo "$LINT_OUTPUT" | tail -20 >&2
    ERRORS=$((ERRORS + 1))
  fi
fi

# --lint-only 모드는 린터 결과만 반환하고 즉시 종료 (Step 0 조기 종료용)
if [ "$LINT_ONLY" -eq 1 ]; then
  [ "$ERRORS" -gt 0 ] && exit 2
  exit 0
fi

# ─────────────────────────────────────────────
# git diff 캐시 (22회 → 3회)
# Windows에서 git 프로세스 부팅이 호출당 ~30ms. 아래 3개만 실제 git 호출,
# 이후 모든 블록은 변수 재사용. staged 상태는 스크립트 실행 중 변하지 않음.
# --lint-only는 이 지점 전에 종료하므로 린트 실패 시 git 호출 발생 안 함.
# ─────────────────────────────────────────────
STAGED_NAME_STATUS=$(git diff --cached --name-status 2>/dev/null)
STAGED_NUMSTAT=$(git diff --cached --numstat 2>/dev/null)
STAGED_DIFF_U0=$(git diff --cached -U0 2>/dev/null)
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

# 5. 위험도 기반 리뷰 게이트 (light 모드일 때만)
HARNESS_LEVEL=""
if [ -f "CLAUDE.md" ]; then
  HARNESS_LEVEL=$(grep -m1 '하네스 강도:' CLAUDE.md 2>/dev/null | sed 's/.*하네스 강도:[[:space:]]*//' | tr -d ' ')
fi

if [ "$HARNESS_LEVEL" = "light" ]; then
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
    echo "" >&2
    echo "⚡ 위험도 감지 — 리뷰 에이전트가 자동 실행됩니다:" >&2
    echo -e "$RISK_REASONS" >&2
    echo "" >&2
    # review 전달용: 한 줄로 압축 (개행 → '; ')
    RISK_FACTORS_SUMMARY=$(echo -e "$RISK_REASONS" | sed 's/^[[:space:]]*-[[:space:]]*//' | grep -v '^$' | paste -sd';' -)
  fi
fi

# 6. 같은 파일 연속 수정 카운트 (정보용 — 차단·경고 없음)
# staging.md S10 신호와 review가 참고. 사용자 가시 메시지는 출력하지 않음.
# 면제 파일: 버전 범프·이력 갱신처럼 매 커밋마다 같이 변경되는 정상 패턴
REPEAT_RANGE=5
REPEAT_EXEMPT_REGEX='^(\.claude/HARNESS\.json|docs/harness/promotion-log\.md|docs/clusters/.*\.md)$'

RECENT_FILES=$(git log -${REPEAT_RANGE} --name-only --format= 2>/dev/null | grep -v '^$' | sort)
REPEAT_WARN_HIT=""
REPEAT_BLOCK_HIT=""

# 핵심 설정 파일 — 연속 수정 시 차단 복원 (단순화 작업으로 일반 차단은
# 제거됐지만, settings.json·rules/·scripts/ 같은 핵심 파일은 반복 수정
# 시 추측 수정 패턴 가능성 높아 차단)
CORE_CONFIG_REGEX='^(\.claude/settings\.json|\.claude/rules/.*\.md|\.claude/scripts/.*\.sh|CLAUDE\.md)$'

while IFS= read -r f; do
  [ -z "$f" ] && continue
  if echo "$f" | grep -qE "$REPEAT_EXEMPT_REGEX"; then
    continue
  fi
  COUNT=$(echo "$RECENT_FILES" | grep -cFx "$f")
  # 핵심 설정 파일이 3회 이상 연속 수정되면 차단 (no-speculation·
  # internal-first 위반 방지 — 같은 파일 반복 수정은 추측 수정 신호)
  if [ "$COUNT" -ge 3 ] && echo "$f" | grep -qE "$CORE_CONFIG_REGEX"; then
    echo "" >&2
    echo "❌ 핵심 설정 파일 ${COUNT}회 연속 수정: $f" >&2
    echo "   추측 수정 가능성. 다음을 먼저 확인:" >&2
    echo "   1. git log -5 -- $f (이전 수정 사유)" >&2
    echo "   2. docs/incidents/ (관련 사례)" >&2
    echo "   3. 공식 문서 (rules/internal-first.md)" >&2
    echo "   정당한 점진 확장이면 HARNESS_EXPAND=1 prefix로 우회:" >&2
    echo "     HARNESS_EXPAND=1 git commit -m \"...\"" >&2
    # HARNESS_EXPAND=1은 bash-guard.sh가 command prefix에서 파싱해 env로 전달.
    # COMMIT_EDITMSG 방식은 PreToolUse 시점에 직전 커밋 메시지라 쓸 수 없음
    # (incident matcher_false_block_and_readme_overwrite 인근 — review 지적).
    if [ "$HARNESS_EXPAND" = "1" ]; then
      echo "   (HARNESS_EXPAND=1 감지 — 통과)" >&2
    else
      ERRORS=$((ERRORS + 1))
    fi
  fi
  if [ "$COUNT" -ge 3 ]; then
    REPEAT_BLOCK_HIT="${REPEAT_BLOCK_HIT}\n   - $f (최근 ${REPEAT_RANGE}커밋 중 ${COUNT}회)"
  elif [ "$COUNT" -ge 2 ]; then
    REPEAT_WARN_HIT="${REPEAT_WARN_HIT}\n   - $f (최근 ${REPEAT_RANGE}커밋 중 ${COUNT}회)"
  fi
done <<< "$STAGED_FILES"

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
  /^(\.claude\/HARNESS\.json|docs\/harness\/promotion-log\.md|docs\/clusters\/.*\.md|\.claude\/memory\/.*\.md|CHANGELOG\.md)$/ { meta++; next }
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
# 9.1. 변경된 docs 파일의 프론트매터 domain 필드
DOC_DOMAINS=$(echo "$STAGED_FILES" | grep -E '^docs/.*\.md$' | while read f; do
  if [ -f "$f" ]; then
    grep -m1 '^domain:' "$f" 2>/dev/null | sed 's/^domain:[[:space:]]*//' | tr -d ' '
  fi
done | grep -v '^$' | sort -u)

# 9.2. WIP 파일명 접두사
WIP_DOMAINS=$(echo "$STAGED_FILES" | grep -E '^docs/WIP/[^-]+--' | sed 's|.*/||; s|--.*||' | sort -u)

ALL_DOMAINS=$(printf "%s\n%s\n" "$DOC_DOMAINS" "$WIP_DOMAINS" | grep -v '^$' | sort -u | paste -sd',' -)
DOMAINS="$ALL_DOMAINS"

# 9.3. 등급 매핑 (naming.md의 "도메인 등급" 섹션에서 추출)
# 섹션 헤더부터 다음 ## 헤더 전까지 본문을 읽고, "**critical**...:" / "**meta**...:" 라인에서 도메인 추출
if [ -n "$ALL_DOMAINS" ] && [ -f ".claude/rules/naming.md" ]; then
  GRADE_SECTION=$(awk '/^## 도메인 등급/{flag=1; next} /^## /{flag=0} flag' .claude/rules/naming.md)
  CRITICAL_DOMAINS=$(echo "$GRADE_SECTION" | grep -E '^\s*-\s*\*\*critical\*\*' | sed 's/.*://' | tr -d '*()' | tr ',' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | grep -v '^$')
  META_DOMAINS=$(echo "$GRADE_SECTION" | grep -E '^\s*-\s*\*\*meta\*\*' | sed 's/.*://' | tr -d '*()' | tr ',' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | grep -v '^$')

  GRADES=""
  for d in $(echo "$ALL_DOMAINS" | tr ',' ' '); do
    [ -z "$d" ] && continue
    if echo "$CRITICAL_DOMAINS" | grep -qFx "$d"; then
      g="critical"
    elif echo "$META_DOMAINS" | grep -qFx "$d"; then
      g="meta"
    else
      g="normal"
    fi
    if [ -z "$GRADES" ]; then GRADES="$g"; else GRADES="${GRADES},${g}"; fi
  done
  DOMAIN_GRADES="$GRADES"

  if [ -n "$DOMAIN_GRADES" ]; then
    add_signal "S9"
  fi
fi

# 다중 도메인
DOMAIN_COUNT=$(echo "$ALL_DOMAINS" | tr ',' '\n' | grep -cv '^$')
MULTI_DOMAIN="false"
if [ "$DOMAIN_COUNT" -ge 2 ]; then
  MULTI_DOMAIN="true"
fi

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

# 9. test-strategist 자동 호출 신호 (self-verify.md 트리거)
# 새 함수·새 모듈·시그니처 변경이 staged에 포함되면 commit 스킬이 review와
# 병렬로 test-strategist를 호출한다.
NEEDS_TEST_STRATEGIST="false"
TEST_TARGETS=""

# 9a. 신규 코드 파일 (테스트 파일 자체는 제외)
NEW_CODE_FILES=$(echo "$STAGED_NAME_STATUS" | awk '$1=="A" {print $2}' | \
  grep -E '\.(ts|tsx|js|jsx|py|go|rs|java|rb)$' | \
  grep -vE '\.(test|spec)\.|/tests?/|/__tests__/' | head -5)

# 9b. 새 함수·메소드·클래스 라인 추가 (휴리스틱)
# NEW_FUNC_LINES_FULL: 정보 흐름 누수 #2 해소용 — test-strategist prompt에
# 인라인 박을 함수 추가 줄 전체 (최대 20줄, 길어지면 truncated 표시).
# 보고서: docs/WIP/harness--hn_info_flow_leak_audit.md
NEW_FUNC_LINES_FULL=$(echo "$STAGED_DIFF_U0" | \
  grep -E '^\+[[:space:]]*(export[[:space:]]+)?(async[[:space:]]+)?(function|def|class|func)[[:space:]]+[a-zA-Z_]' | head -20)
NEW_FUNC_LINES=$(echo "$NEW_FUNC_LINES_FULL" | head -1)  # 호환성: 기존 감지용 (1줄)
NEW_FUNC_FILES=""
if [ -n "$NEW_FUNC_LINES" ]; then
  NEW_FUNC_FILES=$(echo "$STAGED_FILES" | \
    grep -E '\.(ts|tsx|js|jsx|py|go|rs|java|rb)$' | \
    grep -vE '\.(test|spec)\.|/tests?/|/__tests__/' | head -5)
fi

if [ -n "$NEW_CODE_FILES" ] || [ -n "$NEW_FUNC_FILES" ]; then
  NEEDS_TEST_STRATEGIST="true"
  TEST_TARGETS=$(printf "%s\n%s\n" "$NEW_CODE_FILES" "$NEW_FUNC_FILES" | grep -v '^$' | sort -u | paste -sd',' -)
fi

# Stage 결정 (1단계: 기본 stage)
RECOMMENDED_STAGE="standard"  # 안전한 기본값

# 도메인 등급 판정 (bash 내장 패턴 매칭 — 서브쉘 grep 제거)
HAS_CRITICAL=""; HAS_META=""
[[ ,$DOMAIN_GRADES, == *,critical,* ]] && HAS_CRITICAL="yes"
[[ ,$DOMAIN_GRADES, == *,meta,* ]]     && HAS_META="yes"

# 우선순위 순 평가
# critical 도메인이라도 메타·문서 단독(S5/S6만)이면 deep 강제 안 함.
# 실제 코드·핵심설정 변경(S7/S2/S8) 또는 마이그레이션(S14) 동반 시에만 deep.
# (incident: doc-only commit이 deep 호출되어 48k tokens 소모)
HAS_CODE_OR_CORE=""
if has_sig S7 || has_sig S2 || has_sig S8 || has_sig S14; then
  HAS_CODE_OR_CORE="yes"
fi

if [ -n "$HAS_CRITICAL" ] && [ -n "$HAS_CODE_OR_CORE" ]; then
  RECOMMENDED_STAGE="deep"
elif [ "$S1_LEVEL" = "line-confirmed" ]; then
  RECOMMENDED_STAGE="deep"
elif has_sig S2 || has_sig S8; then
  RECOMMENDED_STAGE="deep"
elif has_sig S14; then
  RECOMMENDED_STAGE="deep"
elif [ "$S1_LEVEL" = "file-only" ]; then
  RECOMMENDED_STAGE="standard"
elif has_sig S5 && [ -n "$HAS_META" ]; then
  RECOMMENDED_STAGE="skip"
elif has_sig S5; then
  RECOMMENDED_STAGE="skip"
elif has_sig S4 && ! has_sig S7; then
  RECOMMENDED_STAGE="skip"
elif has_sig S6 && [ -n "$HAS_META" ]; then
  RECOMMENDED_STAGE="skip"
elif has_sig S4 && has_sig S7; then
  RECOMMENDED_STAGE="standard"
elif has_sig S15 && has_sig S7; then
  RECOMMENDED_STAGE="standard"
elif has_sig S11; then
  RECOMMENDED_STAGE="standard"
elif has_sig S3 && ! has_sig S7; then
  RECOMMENDED_STAGE="micro"
elif has_sig S6 && [ "$HARNESS_LEVEL" = "light" ]; then
  RECOMMENDED_STAGE="skip"
elif has_sig S6 && [ "$TOTAL_LINES" -le 5 ]; then
  RECOMMENDED_STAGE="skip"
elif has_sig S6; then
  RECOMMENDED_STAGE="micro"
elif has_sig S7; then
  if [ "$TOTAL_LINES" -le 50 ] && [ "$TOTAL_FILES" -le 3 ]; then
    RECOMMENDED_STAGE="micro"
  elif [ "$TOTAL_LINES" -le 300 ] && [ "$TOTAL_FILES" -le 10 ]; then
    RECOMMENDED_STAGE="standard"
  else
    RECOMMENDED_STAGE="deep"
  fi
fi

# Stage 결정 (2단계: 격상)
# B/C: S10 연속 수정 격상
if [ "$REPEAT_MAX" -ge 3 ]; then
  RECOMMENDED_STAGE="deep"
elif [ "$REPEAT_MAX" = "2" ]; then
  case "$RECOMMENDED_STAGE" in
    skip) RECOMMENDED_STAGE="micro" ;;
    micro) RECOMMENDED_STAGE="standard" ;;
    standard) RECOMMENDED_STAGE="deep" ;;
  esac
fi

# A: 다중 도메인 hit + critical 동반이면 격상
# 단, 메타·문서 단독(S5/S6만, 코드/핵심설정/마이그레이션/빌드 동반 X)은 격상 면제.
# 룰 0a 정신: 1단계에서 "S6 단독이면 critical 무시"한 결정을 2단계가 짓밟지 못하도록.
# (incident: c976255 — S6 + S9 critical에서 1단계 micro 결정 → 2단계가 deep 격상)
IS_DOC_ONLY=""
if (has_sig S5 || has_sig S6) && \
   ! (has_sig S7 || has_sig S2 || has_sig S8 || has_sig S14 || has_sig S11); then
  IS_DOC_ONLY="yes"
fi

if [ "$MULTI_DOMAIN" = "true" ] && [ -n "$HAS_CRITICAL" ] && [ -z "$IS_DOC_ONLY" ]; then
  RECOMMENDED_STAGE="deep"
fi

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
  echo "needs_test_strategist: ${NEEDS_TEST_STRATEGIST}"
  echo "test_targets: ${TEST_TARGETS}"
  echo "s1_level: ${S1_LEVEL}"
  # new_func_lines_b64: 멀티라인이라 base64 인코딩. commit 스킬이 base64 -d로
  # 복원해 test-strategist prompt에 인라인 박음 (정보 흐름 누수 #2 해소).
  echo "new_func_lines_b64: $(printf '%s' "$NEW_FUNC_LINES_FULL" | base64 -w0 2>/dev/null || printf '%s' "$NEW_FUNC_LINES_FULL" | base64 | tr -d '\n')"
  exit 2
fi

# 거대 변경 감지 → stderr 경고 (강제 아님, 사용자 선택)
# incident `hn_review_maxturns_verdict_miss`: review maxTurns(6) 상한이
# 거대 diff에서 verdict 미출력 유발. --bulk 제안으로 우회 경로 안내.
if [ "${TOTAL_FILES:-0}" -gt 30 ] || [ "${ADDED_LINES:-0}" -gt 1500 ] \
   || [ "${DELETED_LINES_TOTAL:-0}" -gt 1500 ]; then
  echo "⚠ 대규모 변경 감지 (files=${TOTAL_FILES}, +${ADDED_LINES}, -${DELETED_LINES_TOTAL})." >&2
  echo "  review maxTurns 한계로 verdict 신뢰도 저하 가능. \`/commit --bulk\` 고려." >&2
  echo "  (--bulk: review 대신 정량 가드 4종으로 대체. SSOT: .claude/rules/staging.md)" >&2
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
echo "needs_test_strategist: ${NEEDS_TEST_STRATEGIST}"
echo "test_targets: ${TEST_TARGETS}"
echo "s1_level: ${S1_LEVEL}"
# 누수 #2 해소 (위 차단 블록과 동일)
echo "new_func_lines_b64: $(printf '%s' "$NEW_FUNC_LINES_FULL" | base64 -w0 2>/dev/null || printf '%s' "$NEW_FUNC_LINES_FULL" | base64 | tr -d '\n')"
