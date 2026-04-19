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
  $LINT_CMD 2>/dev/null
  if [ $? -ne 0 ]; then
    echo "❌ 린터 에러. 에러 0에서만 커밋 가능. (실행: $LINT_CMD)" >&2
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

# 6. 같은 영역 연속 수정 감지 (근본 원인 미해결 의심)
# 임계값: 2회 경고, 3회 차단. 최근 5커밋 범위.
# 이스케이프: 커밋 메시지에 [expand] 또는 환경변수 FORCE_REPEAT=1
# 면제 파일: 버전 범프·이력 갱신처럼 매 커밋마다 같이 변경되는 정상 패턴
REPEAT_WARN=2
REPEAT_BLOCK=3
REPEAT_RANGE=5

# 항상 면제되는 파일 (정상 패턴 — 연속 수정 감지의 의도와 무관)
# - HARNESS.json: 모든 minor/patch 버전 범프마다 갱신
# - promotion-log.md: 모든 하네스 변경 이력 추가
# - INDEX.md, clusters/: 문서 추가·이동마다 갱신
REPEAT_EXEMPT_REGEX='^(\.claude/HARNESS\.json|docs/harness/promotion-log\.md|docs/INDEX\.md|docs/clusters/.*\.md)$'

# 정당한 확장 패턴 면제: COMMIT_EDITMSG에 [expand] 태그 또는 FORCE_REPEAT=1
SKIP_REPEAT=0
if [ "$FORCE_REPEAT" = "1" ]; then
  SKIP_REPEAT=1
elif [ -f ".git/COMMIT_EDITMSG" ] && grep -q '\[expand\]' .git/COMMIT_EDITMSG 2>/dev/null; then
  SKIP_REPEAT=1
fi

if [ "$SKIP_REPEAT" = "0" ]; then
  RECENT_FILES=$(git log -${REPEAT_RANGE} --name-only --format= 2>/dev/null | grep -v '^$' | sort)
  REPEAT_WARN_HIT=""
  REPEAT_BLOCK_HIT=""

  while IFS= read -r f; do
    [ -z "$f" ] && continue
    # 면제 파일은 카운트 안 함 (정상 패턴)
    if echo "$f" | grep -qE "$REPEAT_EXEMPT_REGEX"; then
      continue
    fi
    COUNT=$(echo "$RECENT_FILES" | grep -cFx "$f")
    if [ "$COUNT" -ge "$REPEAT_BLOCK" ]; then
      REPEAT_BLOCK_HIT="${REPEAT_BLOCK_HIT}\n   - $f (최근 ${REPEAT_RANGE}커밋 중 ${COUNT}회)"
    elif [ "$COUNT" -ge "$REPEAT_WARN" ]; then
      REPEAT_WARN_HIT="${REPEAT_WARN_HIT}\n   - $f (최근 ${REPEAT_RANGE}커밋 중 ${COUNT}회)"
    fi
  done <<< "$(git diff --cached --name-only)"

  if [ -n "$REPEAT_BLOCK_HIT" ]; then
    echo "" >&2
    echo "❌ 같은 파일 ${REPEAT_BLOCK}회 이상 반복 수정. 근본 원인 재점검 필요:" >&2
    echo -e "$REPEAT_BLOCK_HIT" >&2
    echo "" >&2
    echo "   증상 완화 반복일 수 있다. 다음 중 하나로 진행:" >&2
    echo "   1. 근본 원인을 찾고 수정 (권장)" >&2
    echo "   2. 정당한 확장이면 커밋 메시지에 [expand] 태그 포함" >&2
    echo "   3. 일시 우회: FORCE_REPEAT=1 git commit ..." >&2
    ERRORS=$((ERRORS + 1))
  elif [ -n "$REPEAT_WARN_HIT" ]; then
    echo "" >&2
    echo "⚠️  같은 파일 ${REPEAT_WARN}회 반복 수정 감지. 근본 원인 미해결 의심:" >&2
    echo -e "$REPEAT_WARN_HIT" >&2
    # review 전달: 연속 수정 경고도 risk factor로 합침
    REPEAT_SUMMARY=$(echo -e "$REPEAT_WARN_HIT" | sed 's/^[[:space:]]*-[[:space:]]*//' | grep -v '^$' | paste -sd',' -)
    if [ -n "$RISK_FACTORS_SUMMARY" ]; then
      RISK_FACTORS_SUMMARY="${RISK_FACTORS_SUMMARY};연속 수정: ${REPEAT_SUMMARY}"
    else
      RISK_FACTORS_SUMMARY="연속 수정: ${REPEAT_SUMMARY}"
    fi
  fi
fi

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

# S1. 보안·시크릿 (이미 위 step 5d에서 SEC_MATCH로 부분 감지 — 재활용)
S1_FILES=$(echo "$STAGED_FILES" | grep -iE 'auth|token|secret|key|credential|password|\.env' 2>/dev/null)
S1_LINES=$(git diff --cached -U0 2>/dev/null | grep -iE '^\+.*(sb_secret_|service_role|sk_live_|sk_test_|ghp_|AKIA[0-9A-Z]{16}|password\s*=)' 2>/dev/null | head -1)
if [ -n "$S1_FILES" ] || [ -n "$S1_LINES" ]; then
  add_signal "S1"
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

# S8. 공유 모듈 변경 (export·시그니처 라인 변경 — 셸 한계, 휴리스틱)
S8_HIT=$(git diff --cached -U0 2>/dev/null | grep -E '^[+-][[:space:]]*(export|public[[:space:]]+(class|function|interface|type|const|let|var)|def[[:space:]]|func[[:space:]])' 2>/dev/null | head -1)
if [ -n "$S8_HIT" ]; then
  add_signal "S8"
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

# 8. 범용성 오염 검출 (harness-starter 전용 — rules/contamination.md)
# is_starter 리포에서만 활성. 다운스트림 고유명사 의심 단어 추출 + 허용어 필터.
CONTAMINATION_HIT=""
if [ -f ".claude/HARNESS.json" ] && grep -q '"is_starter":[[:space:]]*true' .claude/HARNESS.json 2>/dev/null; then
  # 허용어 리스트 (rules/contamination.md의 영문 + 한글 허용어 합집합)
  # 정규식 회피 위해 단순 단어 리스트 (^단어$ 매칭용)
  ALLOWLIST=$(cat <<'EOF'
Claude
Anthropic
CLAUDE
HARNESS
README
CHANGELOG
Bash
Read
Glob
Grep
Edit
Write
Agent
Task
TodoWrite
PreToolUse
PostToolUse
SessionStart
SessionEnd
Stop
PostCompact
UserPromptSubmit
PreCompact
Notification
SubagentStop
Context7
WebSearch
WebFetch
MCP
SDK
Opus
Sonnet
Haiku
TODO
FIXME
HACK
NOTE
XXX
BUG
WIP
JSON
YAML
XML
HTML
CSS
URL
URI
API
CLI
GUI
IDE
HTTP
HTTPS
TCP
UDP
TLS
SSL
DNS
REST
GraphQL
RPC
SQL
NoSQL
OAuth
JWT
CSRF
XSS
CORS
CSP
CVE
OWASP
Git
GitHub
GitLab
Docker
Kubernetes
Linux
Windows
Ubuntu
Node
Python
Java
Rust
Ruby
PHP
TypeScript
JavaScript
React
Vue
Angular
Svelte
Next
Nuxt
Express
Django
Flask
Rails
PostgreSQL
MySQL
MongoDB
Redis
SQLite
Stage
Signal
Skill
Hook
Matcher
Tool
Subagent
Permission
Workflow
Pipeline
Manifest
Lock
Migration
Frontmatter
일반
사용자
하네스
스킬
에이전트
훅
락
매처
도구
서브에이전트
권한
워크플로
파이프라인
매니페스트
마이그레이션
프론트매터
도메인
메타
코드
문서
파일
폴더
경로
변수
함수
클래스
모듈
프로젝트
레포
리포
세션
메시지
명령
옵션
플래그
버전
검토
통합
적용
사용
설정
실행
처리
관리
수정
변경
추가
제거
생성
삭제
확인
검증
필요
가능
불가능
상태
결과
입력
출력
호출
응답
요청
단계
방법
기준
구조
설계
구현
테스트
배포
EOF
)

  # 면제 파일은 git pathspec exclude로 단일 관리 (rules/contamination.md
  # "면제 파일" 섹션과 동기화 의무).
  # 사유:
  # - docs/incidents/: 사고 기록은 실명이 검색 키
  # - docs/harness/promotion-log.md: 이력 본문에 메타 단어 자주 등장
  # - .claude/HARNESS.json: 스키마 단어가 잡힘
  # - .claude/scripts/, .claude/hooks/: 셸 변수명·heredoc 마커 오탐
  # - .claude/rules/contamination.md: 허용어 리스트 자체가 잡힘
  SUSPECT=$(git diff --cached -- \
    ':(exclude)docs/incidents/**' \
    ':(exclude)docs/harness/promotion-log.md' \
    ':(exclude).claude/HARNESS.json' \
    ':(exclude).claude/scripts/**' \
    ':(exclude).claude/hooks/**' \
    ':(exclude).claude/rules/contamination.md' \
    2>/dev/null | \
    grep -E '^\+[^+]' | \
    grep -oE '[A-Z][a-zA-Z0-9]{2,}|[가-힣]{2,}' | \
    sort -u)

  if [ -n "$SUSPECT" ]; then
    # 허용어 제외
    CONTAMINATION_HIT=$(echo "$SUSPECT" | grep -vFx -f <(echo "$ALLOWLIST") | head -10)
    if [ -n "$CONTAMINATION_HIT" ]; then
      echo "" >&2
      echo "⚠️  harness-starter에 고유명사 의심 단어 감지 (rules/contamination.md):" >&2
      echo "$CONTAMINATION_HIT" | sed 's/^/   - /' >&2
      echo "" >&2
      echo "   다운스트림 프로젝트 특유 이름이면 <제품명> 같은 placeholder로 교체." >&2
      echo "   하네스 도메인 정당 용어면 rules/contamination.md 허용어에 추가." >&2
      # risk_factors에 합침 (review가 보도록)
      CONTAM_SUMMARY=$(echo "$CONTAMINATION_HIT" | paste -sd',' -)
      if [ -n "$RISK_FACTORS_SUMMARY" ]; then
        RISK_FACTORS_SUMMARY="${RISK_FACTORS_SUMMARY};오염 의심: ${CONTAM_SUMMARY}"
      else
        RISK_FACTORS_SUMMARY="오염 의심: ${CONTAM_SUMMARY}"
      fi
    fi
  fi
fi

# Stage 결정 (1단계: 기본 stage)
RECOMMENDED_STAGE="standard"  # 안전한 기본값

# 도메인에 critical이 있으면
HAS_CRITICAL=$(echo ",$DOMAIN_GRADES," | grep -E ',critical,')
HAS_META=$(echo ",$DOMAIN_GRADES," | grep -E ',meta,')

# 우선순위 순 평가
if [ -n "$HAS_CRITICAL" ]; then
  RECOMMENDED_STAGE="deep"
elif echo ",$SIGNALS," | grep -qE ',(S1|S2|S8),'; then
  RECOMMENDED_STAGE="deep"
elif echo ",$SIGNALS," | grep -qE ',S14,'; then
  RECOMMENDED_STAGE="deep"
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
