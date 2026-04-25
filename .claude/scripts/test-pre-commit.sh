#!/bin/bash
# pre-commit-check.sh 회귀 테스트
#
# 사용: bash .claude/scripts/test-pre-commit.sh
# 종료 코드: 0=전부 통과, 1=하나라도 실패
#
# 구조 (2026-04-25 재설계):
#   단위 테스트 — _TEST_NAME_STATUS·_TEST_NUMSTAT·_TEST_DIFF_U0 주입 + TEST_MODE=1
#                  git 호출 없음. 신호 판정·stage 결정 로직만 검증.
#   통합 테스트 — 실제 git repo + staged 상태. dead link·S10·이동 커밋처럼
#                  실제 git 이력·파일 시스템이 필요한 케이스만.
#
# 성능 목표: < 10초 (이전: 139초)

set -u
SOURCE_REPO="$(pwd)"
PASS=0
FAIL=0
FAILED_CASES=""

# ─────────────────────────────────────────────
# 단위 테스트 헬퍼
# ─────────────────────────────────────────────

# run_unit: 변수 주입 방식. git 호출 없음.
# $1: case 이름
# $2: 검증할 stdout key
# $3: 기대 패턴 (grep -E)
# $4: must_match | must_not_match
# 환경: _TEST_NAME_STATUS, _TEST_NUMSTAT, _TEST_DIFF_U0 설정 후 호출
UNIT_CACHE=""
UNIT_CACHE_KEY=""

run_unit() {
  local name="$1"
  local key="$2"
  local pattern="$3"
  local mode="$4"

  # 캐시 키: 세 입력 변수 합산 해시 (같은 fixture 내 다중 key 재실행 제거)
  local cache_key="${_TEST_NAME_STATUS:-}|${_TEST_NUMSTAT:-}|${_TEST_DIFF_U0:-}"
  if [ "$cache_key" != "$UNIT_CACHE_KEY" ] || [ -z "$UNIT_CACHE" ]; then
    UNIT_CACHE=$(TEST_MODE=1 \
      _TEST_NAME_STATUS="${_TEST_NAME_STATUS:-}" \
      _TEST_NUMSTAT="${_TEST_NUMSTAT:-}" \
      _TEST_DIFF_U0="${_TEST_DIFF_U0:-}" \
      bash "$SOURCE_REPO/.claude/scripts/pre-commit-check.sh" 2>/dev/null)
    UNIT_CACHE_KEY="$cache_key"
  fi

  _assert "$name" "$key" "$pattern" "$mode" "$UNIT_CACHE"
}

# 캐시 무효화 (fixture 변경 시)
reset_unit() {
  UNIT_CACHE=""
  UNIT_CACHE_KEY=""
  unset _TEST_NAME_STATUS _TEST_NUMSTAT _TEST_DIFF_U0 2>/dev/null || true
}

# ─────────────────────────────────────────────
# 통합 테스트 헬퍼 (실제 git repo)
# ─────────────────────────────────────────────

SANDBOX_BASE="$SOURCE_REPO/.claude/.test-sandbox"
TEST_DIR="$SANDBOX_BASE/run_$$_$(date +%s)"
INTEG_CACHE=""

cleanup() {
  cd "$SOURCE_REPO" 2>/dev/null || true
  rm -rf "$TEST_DIR"
  rmdir "$SANDBOX_BASE" 2>/dev/null || true
}
trap cleanup EXIT

_setup_integ_repo() {
  [ -d "$TEST_DIR/repo" ] && return
  mkdir -p "$TEST_DIR"
  git clone -q "$SOURCE_REPO" "$TEST_DIR/repo" 2>/dev/null
  cp "$SOURCE_REPO/.claude/scripts/pre-commit-check.sh" \
     "$TEST_DIR/repo/.claude/scripts/pre-commit-check.sh" 2>/dev/null || true
  cp "$SOURCE_REPO/.claude/rules/staging.md" \
     "$TEST_DIR/repo/.claude/rules/staging.md" 2>/dev/null || true
  cp "$SOURCE_REPO/.claude/rules/naming.md" \
     "$TEST_DIR/repo/.claude/rules/naming.md" 2>/dev/null || true
}

run_case() {
  local name="$1"
  local key="$2"
  local pattern="$3"
  local mode="$4"

  _setup_integ_repo
  [ "$(pwd)" != "$TEST_DIR/repo" ] && cd "$TEST_DIR/repo"

  if [ -z "$INTEG_CACHE" ]; then
    INTEG_CACHE=$(bash .claude/scripts/pre-commit-check.sh 2>/dev/null)
  fi

  _assert "$name" "$key" "$pattern" "$mode" "$INTEG_CACHE"
}

reset() {
  [ -d "$TEST_DIR/repo" ] && (cd "$TEST_DIR/repo" && git reset HEAD . >/dev/null 2>&1 && git clean -fdq >/dev/null 2>&1)
  INTEG_CACHE=""
}

# ─────────────────────────────────────────────
# 공통 assert
# ─────────────────────────────────────────────

_assert() {
  local name="$1" key="$2" pattern="$3" mode="$4" output="$5"

  local actual
  actual=$(echo "$output" | grep -E "^${key}:" | head -1)

  local matched=0
  echo "$actual" | grep -qE "$pattern" && matched=1

  local ok=0
  [ "$mode" = "must_match" ]     && [ "$matched" = "1" ] && ok=1
  [ "$mode" = "must_not_match" ] && [ "$matched" = "0" ] && ok=1

  if [ "$ok" = "1" ]; then
    echo "  [PASS] $name"
    PASS=$((PASS + 1))
  else
    echo "  [FAIL] $name"
    echo "    key:      $key"
    echo "    expected: $mode '$pattern'"
    echo "    actual:   $actual"
    FAIL=$((FAIL + 1))
    FAILED_CASES="${FAILED_CASES}\n  - $name"
  fi
}

echo ""
echo "=== pre-commit-check.sh 회귀 테스트 ==="
echo ""

# ═════════════════════════════════════════════
# 단위 테스트 구간 — git 없음, 변수 주입
# ═════════════════════════════════════════════

echo "── 단위 테스트 ──"

# ─────────────────────────────────────────────
# T1. S1 file-only — auth-helper.ts 면제
# ─────────────────────────────────────────────
echo "[T1] S1 면제 — *-helper.ts"
_TEST_NAME_STATUS="M src/auth-helper.ts"
_TEST_DIFF_U0="$(printf '+export const x = 1;\n')"
_TEST_NUMSTAT="1 0 src/auth-helper.ts"
run_unit "T1.1 auth-helper.ts → S1 hit 없음" "signals" "S1" must_not_match
run_unit "T1.2 s1_level 빈 값" "s1_level" "^s1_level: $" must_match

# ─────────────────────────────────────────────
# T2. S1 file-only — auth.ts (보조 파일 아님)
# ─────────────────────────────────────────────
echo "[T2] S1 file-only — auth.ts"
reset_unit
_TEST_NAME_STATUS="M src/auth.ts"
_TEST_DIFF_U0="$(printf '+export const validate = () => true;\n')"
_TEST_NUMSTAT="1 0 src/auth.ts"
run_unit "T2.1 auth.ts → S1 hit" "signals" "S1" must_match
run_unit "T2.2 s1_level=file-only" "s1_level" "file-only" must_match

# ─────────────────────────────────────────────
# T3. S1 line-confirmed — 시크릿 패턴
# ─────────────────────────────────────────────
echo "[T3] S1 line-confirmed — 시크릿 패턴"
reset_unit
P1="sk"; P2="live"
_TEST_NAME_STATUS="M src/config.ts"
_TEST_DIFF_U0="$(printf '+export const KEY = "%s_%s_xxxxxxxxxxxxxxxx";\n' "$P1" "$P2")"
_TEST_NUMSTAT="1 0 src/config.ts"
run_unit "T3.1 시크릿 패턴 → S1 hit" "signals" "S1" must_match
run_unit "T3.2 s1_level=line-confirmed" "s1_level" "line-confirmed" must_match
run_unit "T3.3 stage=deep" "recommended_stage" "deep" must_match

# ─────────────────────────────────────────────
# T4. S5 단독 → skip
# ─────────────────────────────────────────────
echo "[T4] S5 단독 → skip"
reset_unit
_TEST_NAME_STATUS="M docs/clusters/harness.md"
_TEST_NUMSTAT="1 0 docs/clusters/harness.md"
_TEST_DIFF_U0="$(printf '+한 줄 변경\n')"
run_unit "T4.1 clusters 단독 → skip" "recommended_stage" "skip" must_match

# ─────────────────────────────────────────────
# T5. S8 음성 — 테스트 파일·문자열 export·Go 소문자
# (3파일 동시 staged 주입 — pre-check 1회)
# ─────────────────────────────────────────────
echo "[T5/T7/T10] S8 음성"
reset_unit
_TEST_NAME_STATUS="$(printf 'M tests/foo.test.ts\nM src/comment.ts\nM src/internal.go')"
_TEST_NUMSTAT="$(printf '1 0 tests/foo.test.ts\n1 0 src/comment.ts\n1 0 src/internal.go')"
_TEST_DIFF_U0="$(printf 'diff --git a/tests/foo.test.ts b/tests/foo.test.ts\n+export function setup() { return 1; }\ndiff --git a/src/comment.ts b/src/comment.ts\n+const msg = "see export const X";\ndiff --git a/src/internal.go b/src/internal.go\n+func handler() string { return "ok" }\n')"
run_unit "T5.1 *.test.ts → S8 hit 없음" "signals" "S8" must_not_match
run_unit "T7.1 문자열 안 export → S8 hit 없음" "signals" "S8" must_not_match
run_unit "T10.1 Go func handler → S8 hit 없음" "signals" "S8" must_not_match

# ─────────────────────────────────────────────
# T6. S8 양성 — TS export·Python def·Go 대문자
# ─────────────────────────────────────────────
echo "[T6/T8/T9] S8 양성"
reset_unit
_TEST_NAME_STATUS="$(printf 'M src/api.ts\nM src/util.py\nM src/api.go')"
_TEST_NUMSTAT="$(printf '3 0 src/api.ts\n2 0 src/util.py\n2 0 src/api.go')"
# diff --git 헤더 필수 — S8 awk가 헤더로 파일 확장자 추출
_TEST_DIFF_U0="$(printf 'diff --git a/src/api.ts b/src/api.ts\n+export function getUser(id: string) { return { id }; }\ndiff --git a/src/util.py b/src/util.py\n+def calculate(x):\n+    return x * 2\ndiff --git a/src/api.go b/src/api.go\n+func Handler() string { return "ok" }\n')"
run_unit "T6.1 export function → S8 hit" "signals" "S8" must_match
run_unit "T8.1 Python def → S8 hit" "signals" "S8" must_match
run_unit "T9.1 Go func Handler → S8 hit" "signals" "S8" must_match

# ─────────────────────────────────────────────
# T16. 교차 — lock + doc 혼합
# ─────────────────────────────────────────────
echo "[T16] 교차 — lock + doc 혼합"
reset_unit
_TEST_NAME_STATUS="$(printf 'M package-lock.json\nM docs/note.md')"
_TEST_NUMSTAT="$(printf '1 0 package-lock.json\n1 0 docs/note.md')"
_TEST_DIFF_U0="$(printf '+{}\n+# note\n')"
run_unit "T16.1 S4 안 뜸" "signals" "S4" must_not_match
run_unit "T16.2 S6 안 뜸" "signals" "S6" must_not_match
run_unit "T16.3 stage 계산됨" "recommended_stage" "standard|micro|deep" must_match

# ─────────────────────────────────────────────
# T17. 교차 — meta + 코드
# ─────────────────────────────────────────────
echo "[T17] 교차 — meta + 코드"
reset_unit
_TEST_NAME_STATUS="$(printf 'M docs/clusters/harness.md\nM src/foo.ts')"
_TEST_NUMSTAT="$(printf '1 0 docs/clusters/harness.md\n1 0 src/foo.ts')"
_TEST_DIFF_U0="$(printf '+# clusters\n+export const x = 1\n')"
run_unit "T17.1 S5 안 뜸" "signals" "S5" must_not_match
run_unit "T17.2 S7 뜸" "signals" "S7" must_match

# ─────────────────────────────────────────────
# T21-T24. 업스트림 위험 경로 → deep
# ─────────────────────────────────────────────
echo "[T21-T24] 업스트림 위험 경로 → deep"
reset_unit
_TEST_NAME_STATUS="$(printf 'M .claude/scripts/foo.sh\nM .claude/agents/foo.md\nM .claude/hooks/pre.sh\nM .claude/settings.json')"
_TEST_NUMSTAT="$(printf '1 0 .claude/scripts/foo.sh\n1 0 .claude/agents/foo.md\n1 0 .claude/hooks/pre.sh\n1 0 .claude/settings.json')"
_TEST_DIFF_U0="$(printf '+#!/bin/bash\n+# agent\n+#!/bin/bash\n+{}\n')"
run_unit "T21.1 scripts → deep" "recommended_stage" "deep" must_match
run_unit "T22.1 agents → deep" "recommended_stage" "deep" must_match
run_unit "T23.1 hooks → deep" "recommended_stage" "deep" must_match
run_unit "T24.1 settings.json → deep" "recommended_stage" "deep" must_match

# ─────────────────────────────────────────────
# T25-T27. 업스트림 비위험 경로 → standard
# ─────────────────────────────────────────────
echo "[T25-T27] 비위험 경로 → standard"
reset_unit
_TEST_NAME_STATUS="$(printf 'M .claude/rules/foo.md\nM .claude/skills/foo/SKILL.md\nM CLAUDE.md')"
_TEST_NUMSTAT="$(printf '1 0 .claude/rules/foo.md\n1 0 .claude/skills/foo/SKILL.md\n5 0 CLAUDE.md')"
_TEST_DIFF_U0="$(printf '+# rule\n+# skill\n+# CLAUDE\n')"
run_unit "T25.1 rules → standard" "recommended_stage" "standard" must_match
run_unit "T26.1 skills → standard" "recommended_stage" "standard" must_match
run_unit "T27.1 CLAUDE.md → standard" "recommended_stage" "standard" must_match

# ─────────────────────────────────────────────
# T28. docs 일반 → standard
# ─────────────────────────────────────────────
echo "[T28] docs 일반 → standard"
reset_unit
_TEST_NAME_STATUS="M docs/guides/note.md"
_TEST_NUMSTAT="8 0 docs/guides/note.md"
_TEST_DIFF_U0="$(printf '+---\n+title: 노트\n+domain: harness\n+status: completed\n+created: 2026-04-21\n+---\n+본문.\n')"
run_unit "T28.1 docs 일반 → standard" "recommended_stage" "standard" must_match

# ─────────────────────────────────────────────
# T30. S5 메타 단독 → skip
# ─────────────────────────────────────────────
echo "[T30] S5 메타 단독 → skip"
reset_unit
_TEST_NAME_STATUS="M .claude/HARNESS.json"
_TEST_NUMSTAT="1 1 .claude/HARNESS.json"
_TEST_DIFF_U0='+"version": "0.20.19"'
run_unit "T30.1 HARNESS.json 단독 → skip" "recommended_stage" "skip" must_match

# ─────────────────────────────────────────────
# T31. src + scripts 혼합 → deep
# ─────────────────────────────────────────────
echo "[T31] src + scripts 혼합 → deep"
reset_unit
_TEST_NAME_STATUS="$(printf 'M src/foo.ts\nM .claude/scripts/bar.sh')"
_TEST_NUMSTAT="$(printf '1 0 src/foo.ts\n1 0 .claude/scripts/bar.sh')"
_TEST_DIFF_U0="$(printf '+export const x = 1\n+#!/bin/bash\n')"
run_unit "T31.1 src + scripts → deep" "recommended_stage" "deep" must_match

# ─────────────────────────────────────────────
# T32. rules + docs + src(비-export) → standard
# ─────────────────────────────────────────────
echo "[T32] rules + docs + src(비-export) → standard"
reset_unit
_TEST_NAME_STATUS="$(printf 'M .claude/rules/foo.md\nM docs/guides/note.md\nM src/foo.ts')"
_TEST_NUMSTAT="$(printf '1 0 .claude/rules/foo.md\n8 0 docs/guides/note.md\n2 1 src/foo.ts')"
_TEST_DIFF_U0="$(printf '+# rule\n+본문.\n+const x = 1;\n')"
run_unit "T32.1 rules+docs+src(non-export) → standard" "recommended_stage" "standard" must_match

# ─────────────────────────────────────────────
# T37. S6 단독 ≤5줄 → skip / >5줄 → standard
# ─────────────────────────────────────────────
echo "[T37] S6 ≤5줄 → skip"
reset_unit
_TEST_NAME_STATUS="M docs/guides/hn_probe.md"
_TEST_NUMSTAT="1 0 docs/guides/hn_probe.md"
_TEST_DIFF_U0="$(printf '+추가 한 줄.\n')"
run_unit "T37.1 docs 1줄 수정 → skip" "recommended_stage" "skip" must_match

reset_unit
_TEST_NAME_STATUS="M docs/guides/hn_probe2.md"
_TEST_NUMSTAT="10 0 docs/guides/hn_probe2.md"
_TEST_DIFF_U0="$(printf '+줄1\n+줄2\n+줄3\n+줄4\n+줄5\n+줄6\n+줄7\n+줄8\n+줄9\n+줄10\n')"
run_unit "T37.2 docs 10줄 수정 → standard" "recommended_stage" "standard" must_match

reset_unit
_TEST_NAME_STATUS="$(printf 'M docs/guides/hn_probe3.md\nM src/foo.ts')"
_TEST_NUMSTAT="$(printf '1 0 docs/guides/hn_probe3.md\n1 0 src/foo.ts')"
_TEST_DIFF_U0="$(printf '+한줄.\n+export const foo = 1\n')"
run_unit "T37.3 docs + 코드 동반 → skip 아님" "recommended_stage" "skip" must_not_match

# ─────────────────────────────────────────────
# T33·T34. 린터 ENOENT 패턴 단위 검증
# (pre-check 호출 없음 — 패턴 직접 검증)
# ─────────────────────────────────────────────
ENOENT_PATTERN="is not recognized as an internal or external command|: command not found$|command not found: [a-zA-Z0-9_./+-]+$|^exec: [^:]+: not found$|^sh: [0-9]+: [^:]+: not found$|ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL"

echo "[T33] 린터 도구 실종 warn 매칭"
check_match() {
  local label="$1" fixture="$2"
  if echo "$fixture" | grep -qE "$ENOENT_PATTERN"; then
    echo "  [PASS] T33.$label"
    PASS=$((PASS + 1))
  else
    echo "  [FAIL] T33.$label '$fixture' → warn 미매칭"
    FAIL=$((FAIL + 1))
    FAILED_CASES="${FAILED_CASES}\n  - T33.$label 실종 형식 미매칭"
  fi
}
check_match "1 windows_cmd" "'eslint' is not recognized as an internal or external command"
check_match "2 bash"        "bash: eslint: command not found"
check_match "3 zsh"         "zsh: command not found: eslint"
check_match "4 sh_plain"    "sh: eslint: command not found"
check_match "5 alpine"      "exec: eslint: not found"
check_match "6 dash_posix"  "sh: 5: eslint: not found"
check_match "7 pnpm"        "ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL  Command failed"

echo "[T34] 오탐 방지 — ESLint crash·rule 위반 차단 유지"
check_no_match() {
  local label="$1" fixture="$2"
  if echo "$fixture" | grep -qE "$ENOENT_PATTERN"; then
    echo "  [FAIL] T34.$label → warn 오탐"
    FAIL=$((FAIL + 1))
    FAILED_CASES="${FAILED_CASES}\n  - T34.$label ESLint crash 오탐"
  else
    echo "  [PASS] T34.$label"
    PASS=$((PASS + 1))
  fi
}
check_no_match "1 import_resolver"  "Error: ENOENT: no such file or directory, open '/path/import.ts'"
check_no_match "2 plugin_missing"   "Error: Cannot find module 'eslint-plugin-react'"
check_no_match "3 rule_violation"   "  3:7  error  'x' is defined but never used  no-unused-vars"
check_no_match "4 node_trace"       "    at Object.<anonymous> (/app/node_modules/eslint/lib/cli.js:123:5)"
check_no_match "5 syntax_error"     "SyntaxError: Unexpected token '<' (1:0)"

# ─────────────────────────────────────────────
# T14·T15. completed 차단 게이트 (인라인 로직 검증)
# ─────────────────────────────────────────────
echo "[T14] completed 게이트 — 헤더 후속"
BODY=$(awk '
  /^---$/{c++; next}
  c<2{next}
  /^## (처리 결과|원본|회고|처리|결과)/{skip=1}
  !skip
' <<'EOF'
---
title: 게이트 테스트
domain: harness
status: pending
created: 2026-04-19
---

# 본문

## 후속
- TODO 작업.
EOF
)
header_hit=$(echo "$BODY" | grep -nE '^\s*##\s*(후속|미결|미결정|추후|나중에|별도로)')
if [ -n "$header_hit" ]; then
  echo "  [PASS] T14.1 ## 후속 헤더 → 차단 hit"
  PASS=$((PASS + 1))
else
  echo "  [FAIL] T14.1 헤더 미감지"
  FAIL=$((FAIL + 1))
  FAILED_CASES="${FAILED_CASES}\n  - T14.1 헤더 게이트"
fi

echo "[T15] completed 게이트 — 처리 결과 섹션 면제"
BODY=$(awk '
  /^---$/{c++; next}
  c<2{next}
  /^## (처리 결과|원본|회고|처리|결과)/{skip=1}
  !skip
' <<'EOF'
---
title: 게이트 테스트 2
domain: harness
status: pending
created: 2026-04-19
---

# 본문

## 처리 결과
- 후속 작업 없음.
- TODO 다 처리됨 ✅
EOF
)
header_hit=$(echo "$BODY" | grep -nE '^\s*##\s*(후속|미결|미결정|추후|나중에|별도로)')
if [ -z "$header_hit" ]; then
  echo "  [PASS] T15.1 처리 결과 섹션 면제"
  PASS=$((PASS + 1))
else
  echo "  [FAIL] T15.1 처리 결과 섹션 잘못 매칭"
  FAIL=$((FAIL + 1))
  FAILED_CASES="${FAILED_CASES}\n  - T15.1 게이트 면제"
fi

# ─────────────────────────────────────────────
# T18. S15 + S7 (package.json + 코드 수정)
# ─────────────────────────────────────────────
echo "[T18] S15 + S7 — package.json + 코드 수정"
reset_unit
# 신규 아닌 수정: name-status M
_TEST_NAME_STATUS="$(printf 'M src/bar.ts\nM package.json')"
_TEST_NUMSTAT="$(printf '1 1 src/bar.ts\n1 1 package.json')"
_TEST_DIFF_U0="$(printf '-export const x = 1\n+export const x = 2\n-\"version\":\"0.0.1\"\n+\"version\":\"0.0.2\"\n')"
run_unit "T18.1 S15 뜸" "signals" "S15" must_match
run_unit "T18.2 S7 뜸" "signals" "S7" must_match
run_unit "T18.3 stage 실제 계산됨" "recommended_stage" "standard|deep" must_match

# ─────────────────────────────────────────────
# T19. 성능 측정 (참고값, 단위 테스트 1회 시간)
# ─────────────────────────────────────────────
echo "[T19] 성능 측정 (참고값)"
reset_unit
_TEST_NAME_STATUS="$(printf 'M src/a.ts\nM src/b.ts\nM docs/x.md\nM package-lock.json\nM package.json')"
_TEST_NUMSTAT="$(printf '1 0 src/a.ts\n1 0 src/b.ts\n1 0 docs/x.md\n1 0 package-lock.json\n1 0 package.json')"
_TEST_DIFF_U0="$(printf '+export const a = 1\n+export const b = 2\n+# doc\n+{}\n+{}\n')"
start=$(date +%s%N)
TEST_MODE=1 \
  _TEST_NAME_STATUS="$_TEST_NAME_STATUS" \
  _TEST_NUMSTAT="$_TEST_NUMSTAT" \
  _TEST_DIFF_U0="$_TEST_DIFF_U0" \
  bash "$SOURCE_REPO/.claude/scripts/pre-commit-check.sh" >/dev/null 2>&1
end=$(date +%s%N)
MS=$(( (end - start) / 1000000 ))
echo "    단위 테스트 pre-check 1회: ${MS}ms"

# ═════════════════════════════════════════════
# 통합 테스트 구간 — 실제 git 필요
# (dead link, S10 반복 수정, 이동 커밋)
# ═════════════════════════════════════════════

echo ""
echo "── 통합 테스트 (실제 git) ──"

_setup_integ_repo
cd "$TEST_DIR/repo"

# ─────────────────────────────────────────────
# T13. 연속 수정 — S10 감지 (실제 git log 필요)
# ─────────────────────────────────────────────
echo "[T13] 연속 수정 — S10"
T13_FILE="docs/WIP/test--scenario_$$_$(date +%s).md"
mkdir -p docs/WIP
cat > "$T13_FILE" <<EOF
---
title: 시나리오
domain: harness
status: pending
created: 2026-04-19
---
첫 줄.
EOF
git add "$T13_FILE"
HARNESS_DEV=1 git -c commit.gpgsign=false commit -q -m "T13 prep1" 2>/dev/null
echo "둘째 줄." >> "$T13_FILE"
git add "$T13_FILE"
HARNESS_DEV=1 git -c commit.gpgsign=false commit -q -m "T13 prep2" 2>/dev/null
echo "셋째 줄." >> "$T13_FILE"
git add "$T13_FILE"
PRECHECK_CACHE=$(bash .claude/scripts/pre-commit-check.sh 2>/dev/null)
output="$PRECHECK_CACHE"
exit_code=$?
if [ "$exit_code" = "0" ]; then
  echo "  [PASS] T13.1 3회 연속 수정 차단 안 됨 (exit 0)"
  PASS=$((PASS + 1))
else
  echo "  [FAIL] T13.1 차단됨 (exit $exit_code)"
  if [ "${TEST_DEBUG:-0}" = "1" ]; then
    echo "    [pre-check 출력 dump]"
    echo "$output" | sed 's/^/      /'
  fi
  FAIL=$((FAIL + 1))
  FAILED_CASES="${FAILED_CASES}\n  - T13.1 연속 수정 차단"
fi
INTEG_CACHE="$PRECHECK_CACHE"
run_case "T13.2 repeat_count: max=2" "repeat_count" "max=2" must_match

reset

# ─────────────────────────────────────────────
# T35. dead link 증분 감지
# ─────────────────────────────────────────────
echo "[T35] dead link 증분 감지"
mkdir -p docs/test_target docs/test_cluster
cat > docs/test_target/hn_dummy.md <<'EOF'
---
title: dummy
domain: harness
tags: []
status: completed
created: 2026-04-22
---
# dummy
EOF
cat > docs/test_cluster/harness.md <<'EOF'
---
title: harness cluster
domain: harness
tags: []
status: completed
created: 2026-04-22
---
# harness cluster
- [dummy](../test_target/hn_dummy.md)
EOF
git add docs/test_target/hn_dummy.md docs/test_cluster/harness.md
git commit -q -m "prep T35 baseline" 2>/dev/null
git rm -q docs/test_target/hn_dummy.md 2>/dev/null
run_case "T35.1 dummy 삭제 + cluster dead link → 차단" "pre_check_passed" "false" must_match
reset

mkdir -p docs/test_cluster2
cat > docs/test_cluster2/broken.md <<'EOF'
---
title: broken
domain: harness
tags: []
status: in-progress
created: 2026-04-22
---
- [없는 파일](../test_target/hn_nonexistent.md)
EOF
git add docs/test_cluster2/broken.md
run_case "T35.2 새 md + 없는 링크 → 차단" "pre_check_passed" "false" must_match
reset

mkdir -p docs/test_cluster3 docs/test_target3
cat > docs/test_target3/hn_new.md <<'EOF'
---
title: new target
domain: harness
tags: []
status: in-progress
created: 2026-04-22
---
# new
EOF
cat > docs/test_cluster3/linker.md <<'EOF'
---
title: linker
domain: harness
tags: []
status: in-progress
created: 2026-04-22
---
- [new](../test_target3/hn_new.md)
EOF
git add docs/test_target3/hn_new.md docs/test_cluster3/linker.md
run_case "T35.3 링크 대상도 같이 staged → 통과" "pre_check_passed" "true" must_match
reset

# ─────────────────────────────────────────────
# T36. relates-to.path dead link
# ─────────────────────────────────────────────
echo "[T36] relates-to dead link"

mkdir -p docs/t36_target docs/t36_src
cat > docs/t36_target/hn_existing.md <<'EOF'
---
title: existing
domain: harness
tags: []
status: completed
created: 2026-04-22
---
EOF
cat > docs/t36_src/hn_refer.md <<'EOF'
---
title: refer
domain: harness
tags: []
relates-to:
  - path: ../t36_target/hn_existing.md
    rel: extends
status: in-progress
created: 2026-04-22
---
EOF
git add docs/t36_target/hn_existing.md docs/t36_src/hn_refer.md
run_case "T36.1 relates-to 존재 → 통과" "pre_check_passed" "true" must_match
reset

mkdir -p docs/t36b
cat > docs/t36b/hn_broken_rt.md <<'EOF'
---
title: broken
domain: harness
tags: []
relates-to:
  - path: ../nowhere/hn_ghost.md
    rel: references
status: in-progress
created: 2026-04-22
---
EOF
git add docs/t36b/hn_broken_rt.md
run_case "T36.2 relates-to 미존재 → 차단" "pre_check_passed" "false" must_match
reset

mkdir -p docs/t36c_target docs/t36c_src
cat > docs/t36c_target/hn_anchor_target.md <<'EOF'
---
title: anchor target
domain: harness
tags: []
status: completed
created: 2026-04-22
---
## section
EOF
cat > docs/t36c_src/hn_anchor_refer.md <<'EOF'
---
title: anchor refer
domain: harness
tags: []
relates-to:
  - path: ../t36c_target/hn_anchor_target.md#section
    rel: references
status: in-progress
created: 2026-04-22
---
EOF
git add docs/t36c_target/hn_anchor_target.md docs/t36c_src/hn_anchor_refer.md
run_case "T36.3 앵커 포함 → 통과" "pre_check_passed" "true" must_match
reset

mkdir -p docs/t36d_src docs/t36d_target
cat > docs/t36d_target/hn_staged.md <<'EOF'
---
title: staged target
domain: harness
tags: []
status: in-progress
created: 2026-04-22
---
EOF
cat > docs/t36d_src/hn_staged_refer.md <<'EOF'
---
title: staged refer
domain: harness
tags: []
relates-to:
  - path: ../t36d_target/hn_staged.md
    rel: references
status: in-progress
created: 2026-04-22
---
EOF
git add docs/t36d_target/hn_staged.md docs/t36d_src/hn_staged_refer.md
run_case "T36.4 대상도 같이 staged → 통과" "pre_check_passed" "true" must_match
reset

mkdir -p docs/t36e_target docs/t36e_src
cat > docs/t36e_target/hn_ok.md <<'EOF'
---
title: ok
domain: harness
tags: []
status: completed
created: 2026-04-22
---
EOF
cat > docs/t36e_src/hn_multi.md <<'EOF'
---
title: multi
domain: harness
tags: []
relates-to:
  - path: ../t36e_target/hn_ok.md
    rel: extends
  - path: ../t36e_target/hn_missing.md
    rel: references
status: in-progress
created: 2026-04-22
---
EOF
git add docs/t36e_target/hn_ok.md docs/t36e_src/hn_multi.md
run_case "T36.5 멀티 중 1건 dead → 차단" "pre_check_passed" "false" must_match
reset

mkdir -p docs/t36f
cat > docs/t36f/hn_norelatespath.md <<'EOF'
---
title: no path
domain: harness
tags: []
relates-to:
  - rel: references
status: in-progress
created: 2026-04-22
---
EOF
git add docs/t36f/hn_norelatespath.md
run_case "T36.6 path 없는 항목 → 통과" "pre_check_passed" "true" must_match
reset

mkdir -p docs/t36g_target docs/t36g_src
cat > docs/t36g_target/hn_rootabs.md <<'EOF'
---
title: root abs target
domain: harness
tags: []
status: completed
created: 2026-04-22
---
EOF
cat > docs/t36g_src/hn_rootabs_refer.md <<'EOF'
---
title: root abs refer
domain: harness
tags: []
relates-to:
  - path: t36g_target/hn_rootabs.md
    rel: extends
status: in-progress
created: 2026-04-22
---
EOF
git add docs/t36g_target/hn_rootabs.md docs/t36g_src/hn_rootabs_refer.md
run_case "T36.7 docs/ 루트 기준 경로 → 통과" "pre_check_passed" "true" must_match
reset

mkdir -p docs/t36h
cat > docs/t36h/hn_rootabs_broken.md <<'EOF'
---
title: root abs broken
domain: harness
tags: []
relates-to:
  - path: nowhere/hn_ghost.md
    rel: references
status: in-progress
created: 2026-04-22
---
EOF
git add docs/t36h/hn_rootabs_broken.md
run_case "T36.8 docs/ 루트 기준 미존재 → 차단" "pre_check_passed" "false" must_match
reset

# ─────────────────────────────────────────────
# T38. 같은 basename 다른 경로 오탐 방지
# ─────────────────────────────────────────────
echo "[T38] 같은 basename 다른 경로 오탐 방지"
mkdir -p docs/t38a_a docs/t38a_b
cat > docs/t38a_a/hn_sibling.md <<'EOF'
---
title: a sibling
domain: harness
tags: []
status: completed
created: 2026-04-22
---
EOF
cat > docs/t38a_b/hn_sibling.md <<'EOF'
---
title: b sibling
domain: harness
tags: []
status: completed
created: 2026-04-22
---
EOF
cat > docs/t38a_a/hn_ref_to_a.md <<'EOF'
---
title: ref to a
domain: harness
tags: []
status: completed
created: 2026-04-22
---
- [A](./hn_sibling.md)
EOF
git add docs/t38a_a/hn_sibling.md docs/t38a_b/hn_sibling.md docs/t38a_a/hn_ref_to_a.md
git commit -q -m "prep T38 baseline" 2>/dev/null
git rm -q docs/t38a_b/hn_sibling.md 2>/dev/null
run_case "T38.1 같은 basename 다른 경로 → 오탐 없음" "pre_check_passed" "true" must_match
reset

# ─────────────────────────────────────────────
# T39. 이동 커밋 skip (rename + meta)
# ─────────────────────────────────────────────
echo "[T39] 이동 커밋 skip"
mkdir -p docs/WIP docs/incidents
cat > docs/WIP/incidents--hn_move_probe.md <<'EOF'
---
title: move probe
domain: harness
tags: []
status: completed
created: 2026-04-25
---
EOF
cat > docs/WIP/incidents--hn_move_probe2.md <<'EOF'
---
title: move probe2
domain: harness
tags: []
status: completed
created: 2026-04-25
---
EOF
cat > docs/WIP/incidents--hn_move_probe4.md <<'EOF'
---
title: move probe4
domain: harness
tags: []
status: completed
created: 2026-04-25
---
EOF
git add docs/WIP/incidents--hn_move_probe.md docs/WIP/incidents--hn_move_probe2.md docs/WIP/incidents--hn_move_probe4.md
git commit -q -m "prep T39 baseline" 2>/dev/null
git commit -q --allow-empty -m "prep T39 s10 v2" 2>/dev/null
git commit -q --allow-empty -m "prep T39 s10 v3" 2>/dev/null

git mv docs/WIP/incidents--hn_move_probe.md docs/incidents/hn_move_probe.md
git add docs/incidents/hn_move_probe.md
run_case "T39.1 rename 단독 → skip" "recommended_stage" "skip" must_match
reset

git mv docs/WIP/incidents--hn_move_probe2.md docs/incidents/hn_move_probe2.md
echo "- [probe2](../incidents/hn_move_probe2.md)" >> docs/clusters/harness.md
git add docs/incidents/hn_move_probe2.md docs/clusters/harness.md
run_case "T39.2 rename + cluster M → skip" "recommended_stage" "skip" must_match
reset

mkdir -p docs/WIP docs/incidents .claude/scripts
cat > docs/WIP/incidents--hn_move_probe3.md <<'EOF'
---
title: move probe3
domain: harness
tags: []
status: completed
created: 2026-04-25
---
EOF
git add docs/WIP/incidents--hn_move_probe3.md
git commit -q -m "prep T39.3 baseline" 2>/dev/null
git mv docs/WIP/incidents--hn_move_probe3.md docs/incidents/hn_move_probe3.md
echo "# change" >> .claude/scripts/pre-commit-check.sh
git add docs/incidents/hn_move_probe3.md .claude/scripts/pre-commit-check.sh
run_case "T39.3 rename + 코드 M → skip 아님" "recommended_stage" "skip" must_not_match
reset

git mv docs/WIP/incidents--hn_move_probe4.md docs/incidents/hn_move_probe4.md
echo "- [probe4](../incidents/hn_move_probe4.md)" >> docs/clusters/harness.md
git add docs/incidents/hn_move_probe4.md docs/clusters/harness.md
run_case "T39.4 rename + cluster + S10 → skip" "recommended_stage" "skip" must_match
reset

# ═════════════════════════════════════════════
# 결과
# ═════════════════════════════════════════════
echo ""
echo "=== 결과 ==="
echo "통과: $PASS"
echo "실패: $FAIL"
if [ "$FAIL" -gt 0 ]; then
  echo ""
  echo "실패 케이스:"
  echo -e "$FAILED_CASES"
  exit 1
fi
exit 0
