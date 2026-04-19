#!/bin/bash
# settings.json 매처 회귀 테스트
# claude-code 매처가 명령 텍스트에 substring 매칭하는지·anchor 동작 확인.
#
# 주의: 이 스크립트는 "이런 명령이 차단되어야 한다/되지 말아야 한다"를
# claude-code matcher 로직 모사로 검증. 실제 hook 실행은 안 함.
# 매처 패턴 변경 후 회귀 방지가 목적.

set -u
PASS=0
FAIL=0
FAILED_CASES=""

# claude-code Bash matcher는 "Bash(<pattern>)" 형식. 패턴 안의 *는
# substring 와일드카드(추정). 실제 동작 확인 사례는 incidents/bash_n_flag_overblock.

# 매처 패턴 (settings.json과 동일 — 변경 시 양쪽 동기화)
PATTERNS=(
  "* --no-verify*"
  "*--no-verify *"
  "git commit -n*"
  "git commit* -n*"
)

# bash glob extension 변환: matcher의 * → bash glob *
# bash [[ str == pattern ]]는 glob 매칭 — claude-code matcher와 유사
matches() {
  local cmd="$1"
  local pat
  for pat in "${PATTERNS[@]}"; do
    # shellcheck disable=SC2053
    if [[ "$cmd" == $pat ]]; then
      return 0
    fi
  done
  return 1
}

run_case() {
  local name="$1"
  local cmd="$2"
  local expected="$3"  # blocked | allowed

  local actual="allowed"
  if matches "$cmd"; then
    actual="blocked"
  fi

  if [ "$actual" = "$expected" ]; then
    echo "  [PASS] $name"
    PASS=$((PASS + 1))
  else
    echo "  [FAIL] $name"
    echo "    cmd:      $cmd"
    echo "    expected: $expected"
    echo "    actual:   $actual"
    FAIL=$((FAIL + 1))
    FAILED_CASES="${FAILED_CASES}\n  - $name"
  fi
}

echo ""
echo "=== settings.json 매처 회귀 테스트 ==="
echo ""

# 차단되어야 하는 케이스
echo "[차단 대상]"
run_case "B1 git commit --no-verify" "git commit --no-verify" blocked
run_case "B2 git push --no-verify" "git push --no-verify" blocked
run_case "B3 git commit -n -m 'fix'" "git commit -n -m 'fix'" blocked
run_case "B4 git commit -m 'x' -n" "git commit -m 'x' -n" blocked

# 정당해서 통과해야 하는 케이스 (오탐 회귀 방지)
echo ""
echo "[정당 명령 통과]"
run_case "A1 bash -n script.sh (구문 체크)" "bash -n script.sh" allowed
run_case "A2 head -n 10 file" "head -n 10 file" allowed
run_case "A3 git push --dry-run" "git push --dry-run" allowed
run_case "A4 grep -n pattern file" "grep -n pattern file" allowed
run_case "A5 awk 'NR<=5' file" "awk 'NR<=5' file" allowed
run_case "A6 git commit -m 'normal msg'" "git commit -m 'normal msg'" allowed
run_case "A7 ls -1" "ls -1" allowed

# 알려진 한계 — 메시지 안 -n 매칭
# claude-code matcher가 quote 인식 안 하는 것으로 확인됨 (hook_flow_efficiency abandoned 사유)
echo ""
echo "[알려진 한계 — 회귀 추적용, 통과는 기대하지 않음]"
echo "  - git commit -m 'fix -n bug' 같은 메시지 안 -n은 잘못 차단됨."
echo "    incidents/bash_n_flag_overblock 참고. 운영적으로 우회 (메시지 표현 변경)."

# ─────────────────────────────────────────────
# starter pre-push hook 회귀 (incident starter_push_skipped)
# ─────────────────────────────────────────────
echo ""
echo "[starter push 보호 — .git/hooks/pre-push]"
if [ -f ".git/hooks/pre-push" ]; then
  IS_STARTER=$(grep -oE '"is_starter"[[:space:]]*:[[:space:]]*(true|false)' .claude/HARNESS.json 2>/dev/null | grep -oE '(true|false)')
  HOOK_BLOCKS=$(grep -c 'HARNESS_DEV' .git/hooks/pre-push 2>/dev/null)

  if [ "$IS_STARTER" = "true" ] && [ "$HOOK_BLOCKS" -gt 0 ]; then
    echo "  [PASS] S1 starter + pre-push가 HARNESS_DEV 검사함"
    PASS=$((PASS + 1))
  elif [ "$IS_STARTER" != "true" ]; then
    echo "  [SKIP] S1 다운스트림 (is_starter=false) — pre-push 보호 불필요"
  else
    echo "  [FAIL] S1 starter인데 pre-push가 HARNESS_DEV 안 검사 — silent push 위험"
    FAIL=$((FAIL + 1))
    FAILED_CASES="${FAILED_CASES}\n  - S1 starter pre-push 보호 누락"
  fi
else
  echo "  [SKIP] S1 .git/hooks/pre-push 없음 (clone 직후·hook 미설치 케이스)"
fi

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
