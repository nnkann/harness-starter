#!/bin/bash
# 커밋 전 검사. 실패하면 exit 2로 커밋 차단.
#
# 출력 채널 분리:
# - stderr: 사용자 노출용 에러/경고 메시지
# - stdout: commit 스킬이 review 에이전트에 전달할 요약 (key: value 라인)
ERRORS=0

# review 전달용 요약 누적 변수 (stdout으로 마지막에 출력)
ALREADY_VERIFIED="lint todo_fixme test_location wip_cleanup"
RISK_FACTORS_SUMMARY=""

# 1. TODO/FIXME/HACK 검사 (staged 파일만)
# 제외: docs/, *.md, README/CHANGELOG (문서는 키워드 언급 정당)
#       .claude/scripts/ (하네스 스크립트 자체가 키워드를 검사하므로 자기 자신 제외)
todo_files=$(git diff --cached --name-only | grep -vE '^docs/|\.(md|mdx)$|README|CHANGELOG|^\.claude/scripts/' | xargs grep -l "TODO\|FIXME\|HACK" 2>/dev/null)
if [ -n "$todo_files" ]; then
  echo "❌ TODO/FIXME/HACK 발견. 코드가 아니라 docs/WIP/에 기록하라." >&2
  echo "$todo_files" | while read f; do
    echo "   $f" >&2
  done
  ERRORS=$((ERRORS + 1))
fi

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

# 3. tests/ 밖에 테스트 파일 있는지 검사
test_outside=$(git diff --cached --name-only | grep -E '\.test\.|\.spec\.|_test\.' | grep -v '^tests/' | grep -v '^__tests__/')
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

  # 5a. 변경 파일 수 5개 이상
  CHANGED_COUNT=$(git diff --cached --name-only | wc -l | tr -d ' ')
  if [ "$CHANGED_COUNT" -ge 5 ]; then
    RISK_REASONS="${RISK_REASONS}\n   - 변경 파일 ${CHANGED_COUNT}개 (≥5)"
  fi

  # 5b. 삭제 라인 50줄 이상
  DELETED_LINES=$(git diff --cached --numstat | awk '{s+=$2} END {print s+0}')
  if [ "$DELETED_LINES" -ge 50 ]; then
    RISK_REASONS="${RISK_REASONS}\n   - 삭제 ${DELETED_LINES}줄 (≥50)"
  fi

  # 5c. 핵심 설정 파일 변경
  CORE_FILES=$(git diff --cached --name-only | grep -E '^(CLAUDE\.md|\.claude/settings\.json|\.claude/rules/|\.claude/scripts/)' 2>/dev/null)
  if [ -n "$CORE_FILES" ]; then
    RISK_REASONS="${RISK_REASONS}\n   - 핵심 설정 파일 변경"
  fi

  # 5d. 보안 관련 패턴
  SEC_MATCH=$(git diff --cached --name-only | grep -iE 'auth|token|secret|key|credential|password' 2>/dev/null)
  if [ -z "$SEC_MATCH" ]; then
    SEC_MATCH=$(git diff --cached -U0 | grep -iE '^\+.*(auth|token|secret|key|credential|password)' 2>/dev/null | head -1)
  fi
  if [ -n "$SEC_MATCH" ]; then
    RISK_REASONS="${RISK_REASONS}\n   - 보안 관련 패턴 감지"
  fi

  # 5e. 인프라/배포 파일
  INFRA_FILES=$(git diff --cached --name-only | grep -iE '(Dockerfile|docker-compose|\.github/workflows/|\.gitlab-ci|deploy)' 2>/dev/null)
  if [ -n "$INFRA_FILES" ]; then
    RISK_REASONS="${RISK_REASONS}\n   - 인프라/배포 파일 변경"
  fi

  # 5f. 단일 파일에서 추가+삭제 동시 30줄 이상
  COMPLEX=$(git diff --cached --numstat | awk '$1+0 >= 30 && $2+0 >= 30 {print $3}')
  if [ -n "$COMPLEX" ]; then
    RISK_REASONS="${RISK_REASONS}\n   - 구조적 수정 감지: $(echo "$COMPLEX" | head -1)"
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
REPEAT_EXEMPT_REGEX='^(\.claude/HARNESS\.json|docs/harness/promotion-log\.md|docs/INDEX\.md|docs/clusters/.*\.md)$'

RECENT_FILES=$(git log -${REPEAT_RANGE} --name-only --format= 2>/dev/null | grep -v '^$' | sort)
REPEAT_WARN_HIT=""
REPEAT_BLOCK_HIT=""

while IFS= read -r f; do
  [ -z "$f" ] && continue
  if echo "$f" | grep -qE "$REPEAT_EXEMPT_REGEX"; then
    continue
  fi
  COUNT=$(echo "$RECENT_FILES" | grep -cFx "$f")
  if [ "$COUNT" -ge 3 ]; then
    REPEAT_BLOCK_HIT="${REPEAT_BLOCK_HIT}\n   - $f (최근 ${REPEAT_RANGE}커밋 중 ${COUNT}회)"
  elif [ "$COUNT" -ge 2 ]; then
    REPEAT_WARN_HIT="${REPEAT_WARN_HIT}\n   - $f (최근 ${REPEAT_RANGE}커밋 중 ${COUNT}회)"
  fi
done <<< "$(git diff --cached --name-only)"

# diff 통계 (review 전달용)
DIFF_STATS=$(git diff --cached --numstat 2>/dev/null | awk '
  { files++; added+=$1; deleted+=$2 }
  END { printf "files=%d,+%d,-%d", files+0, added+0, deleted+0 }
')

# 7. Staging 신호 감지 (rules/staging.md 참조)
# 변경 성격에 맞는 review 강도(stage)를 자동 결정하기 위한 신호 감지.
# 출력: signals=S1,S2,...; domains=...; domain_grades=...;
#       multi_domain=true|false; repeat_count=max=N; recommended_stage=...
SIGNALS=""
STAGED_FILES=$(git diff --cached --name-only 2>/dev/null)
STAGED_NAME_STATUS=$(git diff --cached --name-status 2>/dev/null)
TOTAL_FILES=$(echo "$STAGED_FILES" | grep -cv '^$')
ADDED_LINES=$(git diff --cached --numstat 2>/dev/null | awk '{a+=$1} END{print a+0}')
DELETED_LINES_TOTAL=$(git diff --cached --numstat 2>/dev/null | awk '{d+=$2} END{print d+0}')
TOTAL_LINES=$((ADDED_LINES + DELETED_LINES_TOTAL))

# helper: 신호 추가
add_signal() {
  if [ -z "$SIGNALS" ]; then SIGNALS="$1"; else SIGNALS="${SIGNALS},$1"; fi
}

# S1. 보안·시크릿 — 파일명 hit과 라인 hit을 분리해서 강도 차등 적용
# - S1_LINES (실제 시크릿 패턴): 항상 deep
# - S1_FILES (파일명만): standard로 완화 (auth-helper.ts 같은 일반 보조 파일 면제)
# 면제: 테스트·docs·예제 파일은 파일명만 hit이어도 무시 (시크릿 가능성 낮음)
S1_FILES=$(echo "$STAGED_FILES" | \
  grep -iE 'auth|token|secret|key|credential|password|\.env' 2>/dev/null | \
  grep -vE '\.(test|spec)\.|/tests?/|/__tests__/|^docs/|\.md$|/example|-helper\.|-utils?\.' \
  2>/dev/null)
S1_LINES=$(git diff --cached -U0 2>/dev/null | grep -iE '^\+.*(sb_secret_|service_role|sk_live_|sk_test_|ghp_|AKIA[0-9A-Z]{16}|password\s*=)' 2>/dev/null | head -1)
S1_LEVEL=""  # "" | "file-only" | "line-confirmed"
if [ -n "$S1_LINES" ]; then
  add_signal "S1"
  S1_LEVEL="line-confirmed"
elif [ -n "$S1_FILES" ]; then
  add_signal "S1"
  S1_LEVEL="file-only"
fi

# S2. 핵심 설정 (CLAUDE.md, .claude/settings.json, rules/, scripts/, hooks/, infra)
S2_HIT=$(echo "$STAGED_FILES" | grep -E '^(CLAUDE\.md|\.claude/settings\.json|\.claude/rules/|\.claude/scripts/|\.claude/hooks/|Dockerfile|docker-compose|\.github/workflows/)' 2>/dev/null)
if [ -n "$S2_HIT" ]; then
  add_signal "S2"
fi

# S3. 신규 파일만 (모든 staged가 ^A)
if [ "$TOTAL_FILES" -gt 0 ]; then
  NON_ADDED=$(echo "$STAGED_NAME_STATUS" | grep -cvE '^A')
  if [ "$NON_ADDED" = "0" ] || [ -z "$NON_ADDED" ]; then
    # 모두 추가 파일
    add_signal "S3"
  fi
fi

# S4. lock 파일만
LOCK_REGEX='^(package-lock\.json|pnpm-lock\.yaml|yarn\.lock|bun\.lockb|uv\.lock|Cargo\.lock|go\.sum|composer\.lock|Gemfile\.lock)$'
NON_LOCK=$(echo "$STAGED_FILES" | grep -vE "$LOCK_REGEX" | grep -cv '^$')
LOCK_COUNT=$(echo "$STAGED_FILES" | grep -cE "$LOCK_REGEX")
if [ "$LOCK_COUNT" -gt 0 ] && [ "$NON_LOCK" = "0" ]; then
  add_signal "S4"
fi

# S5. 면제 메타만 (REPEAT_EXEMPT_REGEX와 같은 정의 + memory + CHANGELOG)
META_REGEX='^(\.claude/HARNESS\.json|docs/harness/promotion-log\.md|docs/INDEX\.md|docs/clusters/.*\.md|\.claude/memory/.*\.md|CHANGELOG\.md)$'
NON_META=$(echo "$STAGED_FILES" | grep -vE "$META_REGEX" | grep -cv '^$')
META_COUNT=$(echo "$STAGED_FILES" | grep -cE "$META_REGEX")
if [ "$META_COUNT" -gt 0 ] && [ "$NON_META" = "0" ]; then
  add_signal "S5"
fi

# S6. 문서만 (docs/**, *.md — 단 README/CHANGELOG 제외, 메타 제외)
NON_DOC=$(echo "$STAGED_FILES" | grep -vE '^(docs/|.*\.md$)' | grep -cv '^$')
DOC_COUNT=$(echo "$STAGED_FILES" | grep -cE '^(docs/|.*\.md$)')
if [ "$DOC_COUNT" -gt 0 ] && [ "$NON_DOC" = "0" ] && [ -z "$(echo ",$SIGNALS," | grep ',S5,')" ]; then
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
  # TypeScript/JavaScript: export 선언 (default·named 모두)
  S8_TS=$(git diff --cached -U0 -- '*.ts' '*.tsx' '*.js' '*.jsx' 2>/dev/null | \
    grep -E '^[+-]export[[:space:]]+(default[[:space:]]+)?(async[[:space:]]+)?(class|function|interface|type|enum|const|let|var)[[:space:]]+' | head -1)
  # Python: 모듈 레벨 def·class (들여쓰기 0)
  S8_PY=$(git diff --cached -U0 -- '*.py' 2>/dev/null | \
    grep -E '^[+-](async[[:space:]]+)?(def|class)[[:space:]]+[a-zA-Z_]' | head -1)
  # Go: export 함수·타입 (대문자 시작)
  S8_GO=$(git diff --cached -U0 -- '*.go' 2>/dev/null | \
    grep -E '^[+-](func|type|var|const)[[:space:]]+[A-Z][a-zA-Z0-9_]*' | head -1)
  # Java/C#: public 선언
  S8_JAVA=$(git diff --cached -U0 -- '*.java' '*.cs' 2>/dev/null | \
    grep -E '^[+-][[:space:]]*public[[:space:]]+(static[[:space:]]+)?(class|interface|enum|[a-zA-Z<>]+[[:space:]]+[a-zA-Z_])' | head -1)

  if [ -n "$S8_TS" ] || [ -n "$S8_PY" ] || [ -n "$S8_GO" ] || [ -n "$S8_JAVA" ]; then
    S8_HIT="yes"
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

# S11. 빌드/CI 스크립트 (프로젝트 scripts/, .husky/, Makefile — .claude/scripts는 S2)
S11_HIT=$(echo "$STAGED_FILES" | grep -E '^(scripts/.*\.sh$|\.husky/|Makefile$)' 2>/dev/null)
if [ -n "$S11_HIT" ]; then
  add_signal "S11"
fi

# S14. DB 마이그레이션
S14_HIT=$(echo "$STAGED_FILES" | grep -E '(^|/)migrations/|^alembic/versions/|^prisma/migrations/' 2>/dev/null)
if [ -n "$S14_HIT" ]; then
  add_signal "S14"
fi

# S15. 패키지 manifest
S15_HIT=$(echo "$STAGED_FILES" | grep -E '^(package\.json|pyproject\.toml|Cargo\.toml|go\.mod|requirements.*\.txt|Gemfile|composer\.json)$' 2>/dev/null)
if [ -n "$S15_HIT" ]; then
  add_signal "S15"
fi

# S7. 일반 코드 (위 신호들 중 S5/S6/S4/S3 어디에도 안 속하면)
HAS_META_OR_DOC=$(echo ",$SIGNALS," | grep -E ',(S3|S4|S5|S6),' | head -1)
if [ "$TOTAL_FILES" -gt 0 ] && [ -z "$HAS_META_OR_DOC" ]; then
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
NEW_FUNC_LINES=$(git diff --cached -U0 2>/dev/null | \
  grep -E '^\+[[:space:]]*(export[[:space:]]+)?(async[[:space:]]+)?(function|def|class|func)[[:space:]]+[a-zA-Z_]' | head -1)
NEW_FUNC_FILES=""
if [ -n "$NEW_FUNC_LINES" ]; then
  NEW_FUNC_FILES=$(git diff --cached --name-only 2>/dev/null | \
    grep -E '\.(ts|tsx|js|jsx|py|go|rs|java|rb)$' | \
    grep -vE '\.(test|spec)\.|/tests?/|/__tests__/' | head -5)
fi

if [ -n "$NEW_CODE_FILES" ] || [ -n "$NEW_FUNC_FILES" ]; then
  NEEDS_TEST_STRATEGIST="true"
  TEST_TARGETS=$(printf "%s\n%s\n" "$NEW_CODE_FILES" "$NEW_FUNC_FILES" | grep -v '^$' | sort -u | paste -sd',' -)
fi

# Stage 결정 (1단계: 기본 stage)
RECOMMENDED_STAGE="standard"  # 안전한 기본값

# 도메인에 critical이 있으면
HAS_CRITICAL=$(echo ",$DOMAIN_GRADES," | grep -E ',critical,')
HAS_META=$(echo ",$DOMAIN_GRADES," | grep -E ',meta,')

# 우선순위 순 평가
if [ -n "$HAS_CRITICAL" ]; then
  RECOMMENDED_STAGE="deep"
elif [ "$S1_LEVEL" = "line-confirmed" ]; then
  RECOMMENDED_STAGE="deep"
elif echo ",$SIGNALS," | grep -qE ',(S2|S8),'; then
  RECOMMENDED_STAGE="deep"
elif echo ",$SIGNALS," | grep -qE ',S14,'; then
  RECOMMENDED_STAGE="deep"
elif [ "$S1_LEVEL" = "file-only" ]; then
  RECOMMENDED_STAGE="standard"
elif echo ",$SIGNALS," | grep -qE ',S5,' && [ -n "$HAS_META" ]; then
  RECOMMENDED_STAGE="skip"
elif echo ",$SIGNALS," | grep -qE ',S5,'; then
  RECOMMENDED_STAGE="skip"
elif echo ",$SIGNALS," | grep -qE ',S4,' && ! echo ",$SIGNALS," | grep -qE ',S7,'; then
  RECOMMENDED_STAGE="skip"
elif echo ",$SIGNALS," | grep -qE ',S6,' && [ -n "$HAS_META" ]; then
  RECOMMENDED_STAGE="skip"
elif echo ",$SIGNALS," | grep -qE ',S4,' && echo ",$SIGNALS," | grep -qE ',S7,'; then
  RECOMMENDED_STAGE="standard"
elif echo ",$SIGNALS," | grep -qE ',S15,' && echo ",$SIGNALS," | grep -qE ',S7,'; then
  RECOMMENDED_STAGE="standard"
elif echo ",$SIGNALS," | grep -qE ',S11,'; then
  RECOMMENDED_STAGE="standard"
elif echo ",$SIGNALS," | grep -qE ',S3,' && ! echo ",$SIGNALS," | grep -qE ',S7,'; then
  RECOMMENDED_STAGE="micro"
elif echo ",$SIGNALS," | grep -qE ',S6,' && [ "$HARNESS_LEVEL" = "light" ]; then
  RECOMMENDED_STAGE="skip"
elif echo ",$SIGNALS," | grep -qE ',S6,' && [ "$TOTAL_LINES" -le 5 ]; then
  RECOMMENDED_STAGE="skip"
elif echo ",$SIGNALS," | grep -qE ',S6,'; then
  RECOMMENDED_STAGE="micro"
elif echo ",$SIGNALS," | grep -qE ',S7,'; then
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

# A: 다중 도메인 hit + critical 동반이면 이미 deep, 아니면 격상
if [ "$MULTI_DOMAIN" = "true" ] && [ -n "$HAS_CRITICAL" ]; then
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
  exit 2
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
