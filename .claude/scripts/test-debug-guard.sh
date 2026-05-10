#!/bin/bash
# debug-guard.sh 회귀 테스트.
# UserPromptSubmit hook 입력 형식(JSON via stdin)으로 호출.
# 키워드 사전: 에러·버그·실패·오류·원인·error·bug·fail.
# hit 시 debug-specialist + BIT 안내 둘 다 출력.

set -u
PASS=0
FAIL=0
FAILED_CASES=""

run_case() {
  local name="$1"
  local prompt="$2"
  local expect_hit="$3"  # 1=두 안내 모두 출력 기대, 0=둘 다 미출력

  local json
  json=$(python3 -c "import json,sys; print(json.dumps({'prompt': sys.argv[1]}))" "$prompt")

  local out
  out=$(echo "$json" | bash .claude/scripts/debug-guard.sh 2>&1)

  local has_debug=0
  local has_bit=0
  if echo "$out" | grep -q "\[debug-guard\]"; then has_debug=1; fi
  if echo "$out" | grep -q "\[debug-guard/BIT\]"; then has_bit=1; fi

  local actual_hit=0
  if [ "$has_debug" = "1" ] && [ "$has_bit" = "1" ]; then actual_hit=1; fi
  # 둘 다 미출력만 미hit으로 인정. 한쪽만 출력은 버그.
  if [ "$has_debug" = "0" ] && [ "$has_bit" = "0" ]; then actual_hit=0; fi

  if [ "$actual_hit" = "$expect_hit" ] && [ "$has_debug" = "$has_bit" ]; then
    echo "  [PASS] $name"
    PASS=$((PASS + 1))
  else
    echo "  [FAIL] $name"
    echo "    prompt:   $prompt"
    echo "    expected: hit=$expect_hit (둘 다 출력 또는 둘 다 미출력)"
    echo "    actual:   debug=$has_debug bit=$has_bit"
    FAIL=$((FAIL + 1))
    FAILED_CASES="${FAILED_CASES}\n  - $name"
  fi
}

echo ""
echo "=== debug-guard.sh 회귀 테스트 ==="
echo ""

echo "[키워드 hit — 두 안내 모두 출력 기대]"
run_case "H1 에러" "에러 났다" 1
run_case "H2 버그" "이건 버그다" 1
run_case "H3 실패" "테스트 실패" 1
run_case "H4 오류" "오류 발생" 1
run_case "H6 error" "TypeError: undefined" 1
run_case "H7 bug" "found a bug" 1
run_case "H8 fail" "build failed" 1
run_case "H9 크래시" "앱 크래시" 1
run_case "H10 충돌" "merge 충돌" 1
run_case "H11 exception" "uncaught exception" 1
run_case "H12 panic" "runtime panic" 1
run_case "H13 crash" "app crash detected" 1
run_case "H14 traceback" "Traceback (most recent call last)" 1
run_case "H15 stacktrace" "stacktrace below" 1
run_case "H16 regression" "regression in v0.38" 1
run_case "H17 broken" "this is broken" 1
run_case "H18 conflict" "merge conflict" 1

echo ""
echo "[키워드 미hit — 통과]"
run_case "M1 커밋 요청" "커밋해줘" 0
run_case "M2 문서 갱신" "문서 갱신" 0
run_case "M3 함수 추가" "함수 추가" 0
run_case "M4 빈 프롬프트" "" 0
run_case "M5 원인 분석 (false-positive 가드)" "이 결정의 원인 분석해줘" 0

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
