#!/bin/bash
# bash-guard.sh 회귀 테스트.
# 공식 PreToolUse hook 입력 형식(JSON via stdin)으로 호출하여 실제 hook
# 환경과 동일한 검증. (이전 test-hooks.sh는 bash glob로 matcher를 모사
# 했지만 공식 matcher 동작과 다름 — 거짓 안전감으로 폐기됨.)

set -u
PASS=0
FAIL=0
FAILED_CASES=""

run_case() {
  local name="$1"
  local cmd="$2"
  local expected="$3"  # 0 (allow) | 2 (block)

  local actual
  actual=$(echo "{\"tool_input\":{\"command\":\"$cmd\"}}" | bash .claude/scripts/bash-guard.sh 2>/dev/null; echo "EXIT:$?")
  local ec="${actual##*EXIT:}"

  if [ "$ec" = "$expected" ]; then
    echo "  [PASS] $name (exit $ec)"
    PASS=$((PASS + 1))
  else
    echo "  [FAIL] $name"
    echo "    cmd:      $cmd"
    echo "    expected: exit $expected"
    echo "    actual:   exit $ec"
    FAIL=$((FAIL + 1))
    FAILED_CASES="${FAILED_CASES}\n  - $name"
  fi
}

echo ""
echo "=== bash-guard.sh 회귀 테스트 ==="
echo ""

echo "[차단 대상]"
run_case "B1 git commit -n" "git commit -n" 2
run_case "B2 git commit -n -m fix" "git commit -n -m fix" 2
run_case "B3 git commit --no-verify" "git commit --no-verify" 2
run_case "B4 git push --no-verify" "git push --no-verify" 2
run_case "B5 npm test --no-verify" "npm test --no-verify" 2

echo ""
echo "[정당 명령 통과 — 이전 광역 매처가 잘못 차단했던 케이스]"
run_case "A1 bash -n script.sh" "bash -n script.sh" 0
run_case "A2 head -n 10 file" "head -n 10 file" 0
run_case "A3 grep -n pattern file" "grep -n pattern file" 0
run_case "A4 git push --dry-run" "git push --dry-run" 0
run_case "A5 git push origin main" "git push origin main" 0
run_case "A6 ls -1" "ls -1" 0
run_case "A7 awk script (no -n)" "awk 1 file" 0

echo ""
echo "[메시지 안 -n — 공식 권장은 통과시키는 것이 안전]"
# M1은 audit #8로 커밋 prefix가 없으면 차단으로 바뀜. 이스케이프 붙여 검증.
run_case "M1 prefix+git commit -m 'fix -n bug'" "HARNESS_DEV=1 git commit -m 'fix -n bug'" 0

echo ""
echo "[audit #8 — git commit 강제 경유]"
run_case "G1 git commit 직접 (prefix 없음) → 차단" "git commit -m 'x'" 2
run_case "G2 HARNESS_COMMIT_SKILL=1 git commit → 차단 (v0.20.5 이스케이프 폐기)" "HARNESS_COMMIT_SKILL=1 git commit -m 'x'" 2
run_case "G3 HARNESS_DEV=1 git commit (이스케이프) → 통과" "HARNESS_DEV=1 git commit -m 'x'" 0
run_case "G4 git commit --help → 통과 (읽기 전용)" "git commit --help" 0
run_case "G5 git commit --dry-run → 통과" "git commit --dry-run" 0

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
