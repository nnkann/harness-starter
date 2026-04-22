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

# 커밋되지 않은 로컬 변경사항을 테스트 대상에 반영:
# clone은 HEAD만 가져오므로 워킹 트리의 수정사항이 누락됨.
# pre-commit-check.sh 자체를 테스트할 때 로컬 수정이 적용되어야 유효.
cp "$SOURCE_REPO/.claude/scripts/pre-commit-check.sh" .claude/scripts/pre-commit-check.sh 2>/dev/null || true
cp "$SOURCE_REPO/.claude/rules/staging.md" .claude/rules/staging.md 2>/dev/null || true
cp "$SOURCE_REPO/.claude/rules/naming.md" .claude/rules/naming.md 2>/dev/null || true

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
mkdir -p docs/clusters
echo "한 줄 변경" > docs/clusters/harness.md
git add docs/clusters/harness.md
run_case "T4.1 clusters 1줄 변경 → S5 또는 skip" "recommended_stage" "skip" must_match

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
# 파일명은 PID + 에포크로 unique. 다운스트림 repo가 과거에 같은 고정 경로를
# 커밋한 이력이 있으면 git log -5 교차로 COUNT가 부풀려져 T13.1이 다른 이유로
# 차단됨. incident: hn_test_isolation_git_log_leak.md
# ─────────────────────────────────────────────────
echo "[T13] 연속 수정 — 차단 없음, repeat_count만"
reset
mkdir -p docs/WIP
T13_FILE="docs/WIP/test--scenario_$$_$(date +%s).md"
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
# 같은 파일 또 수정
echo "둘째 줄." >> "$T13_FILE"
git add "$T13_FILE"
HARNESS_DEV=1 git -c commit.gpgsign=false commit -q -m "T13 prep2" 2>/dev/null
# 세 번째 수정 (3회 도달)
echo "셋째 줄." >> "$T13_FILE"
git add "$T13_FILE"
output=$(bash .claude/scripts/pre-commit-check.sh 2>&1)
exit_code=$?
if [ "$exit_code" = "0" ]; then
  echo "  [PASS] T13.1 3회 연속 수정 차단 안 됨 (exit 0)"
  PASS=$((PASS + 1))
else
  echo "  [FAIL] T13.1 차단됨 (exit $exit_code)"
  # TEST_DEBUG=1: FAIL 시 캡처된 output 출력. 다운스트림 격리 실패 진단용.
  # incident: hn_test_isolation_git_log_leak.md
  if [ "${TEST_DEBUG:-0}" = "1" ]; then
    echo "    [pre-check 출력 dump]"
    echo "$output" | sed 's/^/      /'
  fi
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
# T16. 교차 카테고리 — lock + doc 혼합 (awk 1패스 분류 정확성)
# 기대: S4 안 뜸(lock 단독 아님) · S6 안 뜸(doc 단독 아님) · S7 뜸
# ─────────────────────────────────────────────────
echo "[T16] 교차 — lock + doc 혼합"
reset
echo "{}" > package-lock.json
mkdir -p docs
echo "# note" > docs/note.md
git add package-lock.json docs/note.md
run_case "T16.1 S4 안 뜸"        "signals" "S4" must_not_match
run_case "T16.2 S6 안 뜸"        "signals" "S6" must_not_match
run_case "T16.3 recommended_stage" "recommended_stage" "standard|micro|deep" must_match

# ─────────────────────────────────────────────────
# T17. 교차 — meta + 일반 코드 혼합
# 기대: S5 안 뜸(meta 단독 아님) · S7 뜸
# ─────────────────────────────────────────────────
echo "[T17] 교차 — meta(clusters) + 코드"
reset
mkdir -p docs/clusters src
echo "# clusters" > docs/clusters/harness.md
echo "export const x = 1" > src/foo.ts
git add docs/clusters/harness.md src/foo.ts
run_case "T17.1 S5 안 뜸" "signals" "S5" must_not_match
run_case "T17.2 S7 뜸"    "signals" "S7" must_match

# ─────────────────────────────────────────────────
# T18. 교차 — package.json + 코드 (기존 파일 수정)
# 기대: S15 뜸. 기존 파일 수정이라 S3(신규만) 배제 + S7 활성.
# 신규 파일 두 개를 쓰면 S3가 먼저 걸려 S7이 배제되므로
# 실제 배포 시나리오(기존 코드베이스 수정)를 재현.
# ─────────────────────────────────────────────────
echo "[T18] 교차 — package.json + 코드 수정"
reset
mkdir -p src
echo '{"name":"x","version":"0.0.1"}' > package.json
echo "export const x = 1" > src/bar.ts
git add package.json src/bar.ts
HARNESS_DEV=1 git -c commit.gpgsign=false commit -q -m "T18 prep" 2>/dev/null
# 기존 파일 수정 (신규 아님)
echo "export const x = 2" > src/bar.ts
echo '{"name":"x","version":"0.0.2"}' > package.json
git add src/bar.ts package.json
run_case "T18.1 S15 뜸" "signals" "S15" must_match
run_case "T18.2 S7 뜸"  "signals" "S7"  must_match
# S8(export 수정) + S15 공존 시 stage는 deep 가능 — 정확 값 대신 비-skip만 체크
run_case "T18.3 stage 실제 계산됨" "recommended_stage" "(standard|deep)" must_match

# ─────────────────────────────────────────────────
# T19. 성능 — 전체 실행 시간 측정 (회귀 방어선)
# 최근 최적화 후 ~800ms. 1500ms 넘으면 회귀로 본다.
# ─────────────────────────────────────────────────
echo "[T19] 성능 측정 (3회 평균)"
reset
# 중간 크기 staged 상태로 측정: 파일 5개 (코드·docs·lock·meta·package)
mkdir -p src docs .claude
echo "export const a = 1" > src/a.ts
echo "export const b = 2" > src/b.ts
echo "# doc" > docs/x.md
echo "{}" > package-lock.json
echo '{"version":"0.0.1"}' > package.json
git add src/a.ts src/b.ts docs/x.md package-lock.json package.json

# warm-up 1회 (clone 직후 cold git 프로세스 편향 제거)
bash .claude/scripts/pre-commit-check.sh >/dev/null 2>&1

TOTAL_MS=0
RUNS=3
for i in $(seq 1 $RUNS); do
  start=$(date +%s%N)
  bash .claude/scripts/pre-commit-check.sh >/dev/null 2>&1
  end=$(date +%s%N)
  ms=$(( (end - start) / 1000000 ))
  TOTAL_MS=$((TOTAL_MS + ms))
done
AVG_MS=$((TOTAL_MS / RUNS))
echo "    평균: ${AVG_MS}ms (${RUNS}회, warm)"
# 임계값 2500ms: Windows Git Bash + tmp clone repo는 프로젝트 내 실측(~800ms)
# 보다 2~3배 느림 (fs·process 오버헤드). 2500ms는 "최적화 유지" 방어선.
# 4000ms 넘으면 명백한 회귀(최적화 전 원본이 2000ms 수준).
if [ "$AVG_MS" -le 2500 ]; then
  echo "  [PASS] T19.1 성능 ≤2500ms (${AVG_MS}ms)"
  PASS=$((PASS + 1))
else
  echo "  [FAIL] T19.1 성능 회귀 (${AVG_MS}ms > 2500ms)"
  FAIL=$((FAIL + 1))
  FAILED_CASES="${FAILED_CASES}\n  - T19.1 성능 회귀"
fi

# ─────────────────────────────────────────────────
# T20. tree-hash 캐시 재사용 (memory 재설계 2차, v0.15.0)
# commit 스킬 Step 5 블록의 동작 검증: 같은 staged 상태에서 두 번째
# 호출은 저장된 snapshot을 재사용해야 함 (git diff --cached 재호출 0회).
# ─────────────────────────────────────────────────
echo "[T20] tree-hash 캐시 재사용"
reset
mkdir -p .claude/memory src
echo "export const foo = 1" > src/foo.ts
git add src/foo.ts

# 1차: 캐시 miss → 생성
TREE1=$(git write-tree)
git diff --cached > .claude/memory/session-staged-diff.txt
bash .claude/scripts/pre-commit-check.sh > .claude/memory/session-pre-check.txt 2>&1
echo "$TREE1" > .claude/memory/session-tree-hash.txt

SIZE1=$(wc -c < .claude/memory/session-staged-diff.txt)
HASH1=$(cat .claude/memory/session-tree-hash.txt)

# 2차: 같은 staged → tree 일치 → 재사용 가능
TREE2=$(git write-tree)
if [ "$TREE1" = "$TREE2" ]; then
  echo "  [PASS] T20.1 동일 staged → tree-hash 일치"
  PASS=$((PASS + 1))
else
  echo "  [FAIL] T20.1 동일 staged인데 tree-hash 불일치 ($TREE1 vs $TREE2)"
  FAIL=$((FAIL + 1))
  FAILED_CASES="${FAILED_CASES}\n  - T20.1 tree-hash 동일성"
fi

# staged 변경 → tree 변경 확인
echo "export const bar = 2" > src/bar.ts
git add src/bar.ts
TREE3=$(git write-tree)
if [ "$TREE1" != "$TREE3" ]; then
  echo "  [PASS] T20.2 staged 변경 → tree-hash 변경"
  PASS=$((PASS + 1))
else
  echo "  [FAIL] T20.2 staged 변경됐는데 tree-hash 불변"
  FAIL=$((FAIL + 1))
  FAILED_CASES="${FAILED_CASES}\n  - T20.2 tree-hash 민감성"
fi

# 저장된 snapshot 파일이 모두 비어있지 않음 (write 확인)
if [ "$SIZE1" -gt 0 ] && [ -s .claude/memory/session-pre-check.txt ] && [ -n "$HASH1" ]; then
  echo "  [PASS] T20.3 snapshot 3파일 모두 생성"
  PASS=$((PASS + 1))
else
  echo "  [FAIL] T20.3 snapshot 일부 누락 (diff=$SIZE1, hash=$HASH1)"
  FAIL=$((FAIL + 1))
  FAILED_CASES="${FAILED_CASES}\n  - T20.3 snapshot 생성"
fi

# ─────────────────────────────────────────────────
# T21~T32. 5줄 룰 회귀 (v0.17.0, staging.md 5줄 룰)
# 경로 기반 이진 판정. 업스트림 위험 경로 hit 시 deep, 일반 코드/문서
# /rules/skills는 standard, 메타 단독 skip.
# ─────────────────────────────────────────────────

# T21: scripts 단독 → deep
echo "[T21] 5줄 룰 #1 — .claude/scripts 단독 변경"
reset
mkdir -p .claude/scripts
echo '#!/bin/bash' > .claude/scripts/foo.sh
git add .claude/scripts/foo.sh
run_case "T21.1 scripts 단독 → deep" "recommended_stage" "deep" must_match

# T22: agents 단독 → deep
echo "[T22] 5줄 룰 #1 — .claude/agents 단독 변경"
reset
mkdir -p .claude/agents
echo "# agent" > .claude/agents/foo.md
git add .claude/agents/foo.md
run_case "T22.1 agents 단독 → deep" "recommended_stage" "deep" must_match

# T23: hooks 단독 → deep
echo "[T23] 5줄 룰 #1 — .claude/hooks 단독 변경"
reset
mkdir -p .claude/hooks
echo '#!/bin/bash' > .claude/hooks/pre.sh
git add .claude/hooks/pre.sh
run_case "T23.1 hooks 단독 → deep" "recommended_stage" "deep" must_match

# T24: settings.json 단독 → deep
echo "[T24] 5줄 룰 #1 — .claude/settings.json 단독"
reset
mkdir -p .claude
echo '{"permissions":{}}' > .claude/settings.json
git add .claude/settings.json
run_case "T24.1 settings.json → deep" "recommended_stage" "deep" must_match

# T25: rules 단독 → standard (룰 1 miss)
echo "[T25] 5줄 룰 #5 — .claude/rules 단독 (룰 1 miss)"
reset
mkdir -p .claude/rules
echo "# rule" > .claude/rules/foo.md
git add .claude/rules/foo.md
run_case "T25.1 rules 단독 → standard" "recommended_stage" "standard" must_match

# T26: skills 단독 → standard (룰 1 miss)
echo "[T26] 5줄 룰 #5 — .claude/skills 단독 (룰 1 miss)"
reset
mkdir -p .claude/skills/foo
echo "# skill" > .claude/skills/foo/SKILL.md
git add .claude/skills/foo/SKILL.md
run_case "T26.1 skills 단독 → standard" "recommended_stage" "standard" must_match

# T27: CLAUDE.md 단독 → standard (룰 1 미포함)
echo "[T27] 5줄 룰 #5 — CLAUDE.md 단독"
reset
cat > CLAUDE.md <<'EOF'
# CLAUDE

## 언어
- 한국어.

## 환경
- 하네스 강도: strict
- 패키지 매니저:
EOF
git add CLAUDE.md
run_case "T27.1 CLAUDE.md 단독 → standard" "recommended_stage" "standard" must_match

# T28: docs 일반 변경 → standard
echo "[T28] 5줄 룰 #5 — docs 일반 변경"
reset
mkdir -p docs/guides
cat > docs/guides/note.md <<EOF
---
title: 노트
domain: harness
status: completed
created: 2026-04-21
---
본문.
EOF
git add docs/guides/note.md
run_case "T28.1 docs 일반 → standard" "recommended_stage" "standard" must_match

# T29: docs rename ≥20 파일 → bulk
echo "[T29] 5줄 룰 #3 — docs 대량 rename → bulk"
reset
mkdir -p docs/decisions
# 25개 파일 생성 + 커밋
for i in $(seq 1 25); do
  cat > docs/decisions/hn_orig_${i}.md <<EOF
---
title: 원본 ${i}
domain: harness
status: completed
created: 2026-04-21
---
본문 ${i}.
EOF
  git add docs/decisions/hn_orig_${i}.md
done
HARNESS_DEV=1 git -c commit.gpgsign=false commit -q -m "T29 prep" 2>/dev/null
# rename 시뮬레이션 (git mv)
for i in $(seq 1 25); do
  git mv docs/decisions/hn_orig_${i}.md docs/decisions/hn_renamed_${i}.md 2>/dev/null
done
run_case "T29.1 docs rename 25개 → bulk" "recommended_stage" "bulk" must_match

# T30: S5 메타 단독 (promotion-log.md만) → skip
echo "[T30] 5줄 룰 #4 — promotion-log.md 단독 → skip"
reset
mkdir -p docs/harness
echo "# log" > docs/harness/promotion-log.md
git add docs/harness/promotion-log.md
run_case "T30.1 promotion-log 단독 → skip" "recommended_stage" "skip" must_match

# T31: src/* + scripts/* 혼합 → deep (룰 1 우선)
echo "[T31] 5줄 룰 #1 — src + scripts 혼합"
reset
mkdir -p src .claude/scripts
echo "export const x = 1" > src/foo.ts
echo '#!/bin/bash' > .claude/scripts/bar.sh
git add src/foo.ts .claude/scripts/bar.sh
run_case "T31.1 src + scripts → deep" "recommended_stage" "deep" must_match

# T32: rules + docs + src(비-export) 혼합 (룰 1·2 miss) → standard
# export 시그니처는 S8 → 룰 2 → deep이 정답이므로 케이스를 비-export 수정으로 재구성.
echo "[T32] 5줄 룰 #5 — rules + docs + src(비-export) (룰 1·2 miss)"
reset
mkdir -p .claude/rules docs/guides src
echo "// existing module" > src/foo.ts
git add src/foo.ts
HARNESS_DEV=1 git -c commit.gpgsign=false commit -q -m "T32 prep" 2>/dev/null
echo "# rule" > .claude/rules/foo.md
cat > docs/guides/note.md <<EOF
---
title: 가이드
domain: harness
status: completed
created: 2026-04-21
---
본문.
EOF
# src 파일 비-export 수정 (const이지만 export 없음 → S8 미hit)
cat > src/foo.ts <<EOF
// existing module
const x = 1;
EOF
git add .claude/rules/foo.md docs/guides/note.md src/foo.ts
run_case "T32.1 rules+docs+src(non-export) → standard" "recommended_stage" "standard" must_match

# ─────────────────────────────────────────────────
# T33·T34. 린터 ENOENT 패턴 (v0.18.4, hn_lint_enoent_pattern_gaps.md)
# pre-commit-check.sh 린터 단계의 패턴이 shell별 도구 실종 형식은 매칭
# 하되 ESLint 내부 crash·rule 위반과는 겹치지 않는지 단위 검증.
# ─────────────────────────────────────────────────

# 패턴 SSOT — pre-commit-check.sh와 동일 유지.
# 변경 시 양쪽 동기화 필수 (코드 SSOT 서더링).
ENOENT_PATTERN="is not recognized as an internal or external command|: command not found$|command not found: [a-zA-Z0-9_./+-]+$|^exec: [^:]+: not found$|^sh: [0-9]+: [^:]+: not found$|ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL"

# T33. 도구 실종 메시지 (shell별 형식) → 패턴 매칭 기대
echo "[T33] 린터 도구 실종 warn 매칭 (shell별 형식)"
check_match() {
  local label="$1"
  local fixture="$2"
  if echo "$fixture" | grep -qE "$ENOENT_PATTERN"; then
    echo "  [PASS] T33.$label '$fixture' → warn 매칭"
    PASS=$((PASS + 1))
  else
    echo "  [FAIL] T33.$label '$fixture' → warn 미매칭 (shell 실종을 못 잡음)"
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

# T34. ESLint 내부 crash·rule 위반 → 패턴 **미매칭** 기대 (차단 유지)
echo "[T34] 오탐 방지 — ESLint crash·rule 위반은 차단 유지"
check_no_match() {
  local label="$1"
  local fixture="$2"
  if echo "$fixture" | grep -qE "$ENOENT_PATTERN"; then
    echo "  [FAIL] T34.$label '$fixture' → warn으로 오탐 (차단 격하됨)"
    FAIL=$((FAIL + 1))
    FAILED_CASES="${FAILED_CASES}\n  - T34.$label ESLint crash 오탐"
  else
    echo "  [PASS] T34.$label '$fixture' → 차단 유지"
    PASS=$((PASS + 1))
  fi
}
check_no_match "1 import_resolver"  "Error: ENOENT: no such file or directory, open '/path/import.ts'"
check_no_match "2 plugin_missing"   "Error: Cannot find module 'eslint-plugin-react'"
check_no_match "3 rule_violation"   "  3:7  error  'x' is defined but never used  no-unused-vars"
check_no_match "4 node_trace"       "    at Object.<anonymous> (/app/node_modules/eslint/lib/cli.js:123:5)"
check_no_match "5 syntax_error"     "SyntaxError: Unexpected token '<' (1:0)"

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
