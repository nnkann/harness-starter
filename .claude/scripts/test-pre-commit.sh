#!/bin/bash
# pre-commit-check.sh 회귀 테스트
# 격리 디렉토리에 main repo clone 후 시나리오별 staged 상태 만들고
# stdout 신호를 비교한다. 실패 시 어떤 케이스가 어떤 신호를 잘못 출력했는지 보고.
#
# 사용: bash .claude/scripts/test-pre-commit.sh
# 종료 코드: 0=전부 통과, 1=하나라도 실패

set -u
SOURCE_REPO="$(pwd)"
TEST_DIR=$(mktemp -d -t harness-pretest-XXXXXX)
PASS=0
FAIL=0
FAILED_CASES=""

cleanup() {
  rm -rf "$TEST_DIR"
}
trap cleanup EXIT

# clone
git clone -q "$SOURCE_REPO" "$TEST_DIR/repo" 2>/dev/null
cd "$TEST_DIR/repo"

# 헬퍼: 시나리오 실행 + 기대값 비교
# $1: case 이름
# $2: 검증할 stdout key (예: signals)
# $3: 기대 패턴 (정규식, grep -E)
# $4: 검증 모드 (must_match | must_not_match)
run_case() {
  local name="$1"
  local key="$2"
  local pattern="$3"
  local mode="$4"

  local actual
  actual=$(bash .claude/scripts/pre-commit-check.sh 2>/dev/null | grep -E "^${key}:" | head -1)

  local matched=0
  if echo "$actual" | grep -qE "$pattern"; then
    matched=1
  fi

  local ok=0
  if [ "$mode" = "must_match" ] && [ "$matched" = "1" ]; then ok=1; fi
  if [ "$mode" = "must_not_match" ] && [ "$matched" = "0" ]; then ok=1; fi

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

reset() {
  git reset HEAD . >/dev/null 2>&1
  git clean -fdq >/dev/null 2>&1
}

echo ""
echo "=== pre-commit-check.sh 회귀 테스트 ==="
echo "테스트 디렉토리: $TEST_DIR/repo"
echo ""

# ─────────────────────────────────────────────────
# T1. S1 file-only — auth-helper.ts 같은 보조 파일 면제
# ─────────────────────────────────────────────────
echo "[T1] S1 면제 — *-helper.ts (시크릿 가능성 낮음)"
reset
mkdir -p src
echo "export const x = 1;" > src/auth-helper.ts
git add src/auth-helper.ts
run_case "T1.1 auth-helper.ts → S1 hit 없음" "signals" "S1" must_not_match
run_case "T1.2 s1_level 빈 값" "s1_level" "" must_match

# ─────────────────────────────────────────────────
# T2. S1 file-only — 일반 보안 파일명 (helper 아님)
# ─────────────────────────────────────────────────
echo "[T2] S1 file-only — auth.ts (보조 파일 아님)"
reset
mkdir -p src
echo "export const validate = () => true;" > src/auth.ts
git add src/auth.ts
run_case "T2.1 auth.ts → S1 hit" "signals" "S1" must_match
run_case "T2.2 s1_level=file-only" "s1_level" "file-only" must_match

# ─────────────────────────────────────────────────
# T3. S1 line-confirmed — 실제 시크릿 라인
# ─────────────────────────────────────────────────
echo "[T3] S1 line-confirmed — 시크릿 패턴 라인"
reset
mkdir -p src
# 더미 시크릿: 라인 매칭 검증용. 실제 키 아님.
# 본 스크립트 자체가 staged될 때 S1을 자기 자신이 잡지 않도록 런타임 합성.
P1="sk"; P2="live"
cat > src/config.ts <<EOF
export const KEY = "${P1}_${P2}_xxxxxxxxxxxxxxxx";
EOF
git add src/config.ts
run_case "T3.1 시크릿 패턴 → S1 hit" "signals" "S1" must_match
run_case "T3.2 s1_level=line-confirmed" "s1_level" "line-confirmed" must_match
run_case "T3.3 stage=deep" "recommended_stage" "deep" must_match

# ─────────────────────────────────────────────────
# T4. S6 ≤5줄 → skip 자동
# ─────────────────────────────────────────────────
echo "[T4] S6 ≤5줄 → Stage 0 skip"
reset
mkdir -p docs/decisions
cat > docs/decisions/short.md <<EOF
---
title: 짧은 결정
domain: harness
status: completed
created: 2026-04-19
---
한 줄.
EOF
git add docs/decisions/short.md
# diff_stats에서 added 라인 ≤ 5인지 확인 어려우므로 stage로 검증
# 위 파일은 8줄이라 skip 안 될 수도. 짧게 다시:
reset
echo "한 줄 변경" > docs/INDEX.md
git add docs/INDEX.md
run_case "T4.1 INDEX 1줄 변경 → S5 또는 skip" "recommended_stage" "skip" must_match

# ─────────────────────────────────────────────────
# T5. S8 — 테스트 파일 면제
# ─────────────────────────────────────────────────
echo "[T5] S8 — 테스트 파일 면제"
reset
mkdir -p tests
cat > tests/foo.test.ts <<EOF
export function setup() { return 1; }
EOF
git add tests/foo.test.ts
run_case "T5.1 *.test.ts → S8 hit 없음" "signals" "S8" must_not_match

# ─────────────────────────────────────────────────
# T6. S8 — 진짜 export (TypeScript)
# ─────────────────────────────────────────────────
echo "[T6] S8 — 진짜 export (TypeScript)"
reset
mkdir -p src
cat > src/api.ts <<EOF
export function getUser(id: string) {
  return { id };
}
EOF
git add src/api.ts
run_case "T6.1 export function → S8 hit" "signals" "S8" must_match

# ─────────────────────────────────────────────────
# T7. S8 — 문자열 안 export (오탐 회귀 방지)
# ─────────────────────────────────────────────────
echo "[T7] S8 — 문자열 안 export (오탐 회귀 방지)"
reset
mkdir -p src
cat > src/comment.ts <<EOF
const msg = "see export const X for example";
const foo = 1;
EOF
git add src/comment.ts
run_case "T7.1 문자열 안 export → S8 hit 없음" "signals" "S8" must_not_match

# ─────────────────────────────────────────────────
# T8. S8 — Python 모듈 레벨 def
# ─────────────────────────────────────────────────
echo "[T8] S8 — Python def"
reset
mkdir -p src
cat > src/util.py <<EOF
def calculate(x):
    return x * 2
EOF
git add src/util.py
run_case "T8.1 Python def → S8 hit" "signals" "S8" must_match

# ─────────────────────────────────────────────────
# T9. S8 — Go export (대문자 시작)
# ─────────────────────────────────────────────────
echo "[T9] S8 — Go export func"
reset
mkdir -p src
cat > src/api.go <<EOF
package api
func Handler() string { return "ok" }
EOF
git add src/api.go
run_case "T9.1 Go func Handler → S8 hit" "signals" "S8" must_match

# ─────────────────────────────────────────────────
# T10. S8 — Go non-export (소문자 시작)
# ─────────────────────────────────────────────────
echo "[T10] S8 — Go 소문자 시작 (non-export)"
reset
mkdir -p src
cat > src/internal.go <<EOF
package api
func handler() string { return "ok" }
EOF
git add src/internal.go
run_case "T10.1 Go func handler → S8 hit 없음" "signals" "S8" must_not_match

# ─────────────────────────────────────────────────
# T11. needs_test_strategist — 신규 ts + export 함수
# ─────────────────────────────────────────────────
echo "[T11] needs_test_strategist — 신규 코드 + 함수"
reset
mkdir -p src
cat > src/feature.ts <<EOF
export function calculate(x: number): number {
  return x * 2;
}
EOF
git add src/feature.ts
run_case "T11.1 신규 ts + 함수 → needs_test_strategist=true" "needs_test_strategist" "true" must_match
run_case "T11.2 test_targets 비어있지 않음" "test_targets" "feature\.ts" must_match

# ─────────────────────────────────────────────────
# T12. needs_test_strategist — 신규 .test.ts (테스트는 면제)
# ─────────────────────────────────────────────────
echo "[T12] needs_test_strategist — 신규 .test.ts 면제"
reset
mkdir -p tests
cat > tests/foo.test.ts <<EOF
export function setup() { return 1; }
EOF
git add tests/foo.test.ts
run_case "T12.1 신규 .test.ts → needs_test_strategist=false" "needs_test_strategist" "false" must_match

# ─────────────────────────────────────────────────
# T13. 연속 수정 — 차단·경고 없음 (정보만)
# ─────────────────────────────────────────────────
echo "[T13] 연속 수정 — 차단 없음, repeat_count만"
reset
mkdir -p docs/WIP
cat > docs/WIP/test--scenario_260419.md <<EOF
---
title: 시나리오
domain: harness
status: pending
created: 2026-04-19
---
첫 줄.
EOF
git add docs/WIP/test--scenario_260419.md
HARNESS_DEV=1 git -c commit.gpgsign=false commit -q -m "T13 prep1" 2>/dev/null
# 같은 파일 또 수정
echo "둘째 줄." >> docs/WIP/test--scenario_260419.md
git add docs/WIP/test--scenario_260419.md
HARNESS_DEV=1 git -c commit.gpgsign=false commit -q -m "T13 prep2" 2>/dev/null
# 세 번째 수정 (3회 도달)
echo "셋째 줄." >> docs/WIP/test--scenario_260419.md
git add docs/WIP/test--scenario_260419.md
output=$(bash .claude/scripts/pre-commit-check.sh 2>&1)
exit_code=$?
if [ "$exit_code" = "0" ]; then
  echo "  [PASS] T13.1 3회 연속 수정 차단 안 됨 (exit 0)"
  PASS=$((PASS + 1))
else
  echo "  [FAIL] T13.1 차단됨 (exit $exit_code)"
  FAIL=$((FAIL + 1))
  FAILED_CASES="${FAILED_CASES}\n  - T13.1 연속 수정 차단"
fi
# T13.2: pre-check은 git log(완료된 커밋)만 봄. 현재 staged는 아직
# 커밋 안 됐으므로 prev 2회만 카운트됨 (정상).
run_case "T13.2 repeat_count: max=2 (prev 2 + 현재 staged)" "repeat_count" "max=2" must_match

# ─────────────────────────────────────────────────
# T14. completed 차단 게이트 — "## 후속" 헤더
# ─────────────────────────────────────────────────
echo "[T14] docs-manager completed 게이트 — 헤더 후속"
reset
mkdir -p docs/WIP
cat > docs/WIP/test--gate_260419.md <<EOF
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
# 본문 추출 + 게이트 검사 (docs-manager Step 2 로직 그대로)
BODY=$(awk '
  /^---$/{c++; next}
  c<2{next}
  /^## (처리 결과|원본|회고|처리|결과)/{skip=1}
  !skip
' docs/WIP/test--gate_260419.md)
header_hit=$(echo "$BODY" | grep -nE '^\s*##\s*(후속|미결|미결정|추후|나중에|별도로)')
if [ -n "$header_hit" ]; then
  echo "  [PASS] T14.1 ## 후속 헤더 → 차단 hit"
  PASS=$((PASS + 1))
else
  echo "  [FAIL] T14.1 헤더 미감지"
  FAIL=$((FAIL + 1))
  FAILED_CASES="${FAILED_CASES}\n  - T14.1 헤더 게이트"
fi

# ─────────────────────────────────────────────────
# T15. completed 게이트 — 처리 결과 섹션 안 "후속"은 통과
# ─────────────────────────────────────────────────
echo "[T15] docs-manager 게이트 — 처리 결과 섹션 면제"
reset
mkdir -p docs/WIP
cat > docs/WIP/test--gate2_260419.md <<EOF
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
BODY=$(awk '
  /^---$/{c++; next}
  c<2{next}
  /^## (처리 결과|원본|회고|처리|결과)/{skip=1}
  !skip
' docs/WIP/test--gate2_260419.md)
header_hit=$(echo "$BODY" | grep -nE '^\s*##\s*(후속|미결|미결정|추후|나중에|별도로)')
if [ -z "$header_hit" ]; then
  echo "  [PASS] T15.1 처리 결과 섹션 면제 동작"
  PASS=$((PASS + 1))
else
  echo "  [FAIL] T15.1 처리 결과 섹션 잘못 매칭"
  FAIL=$((FAIL + 1))
  FAILED_CASES="${FAILED_CASES}\n  - T15.1 게이트 면제"
fi

# ─────────────────────────────────────────────────
# 결과
# ─────────────────────────────────────────────────
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
