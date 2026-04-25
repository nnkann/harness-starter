#!/bin/bash
# pre-commit-check.sh 회귀 테스트
# 격리 디렉토리에 main repo clone 후 시나리오별 staged 상태 만들고
# stdout 신호를 비교한다. 실패 시 어떤 케이스가 어떤 신호를 잘못 출력했는지 보고.
#
# 사용: bash .claude/scripts/test-pre-commit.sh
# 종료 코드: 0=전부 통과, 1=하나라도 실패
#
# 성능 (v0.20.10): tmp 디렉토리(`mktemp -d -t ...`) → 리포 내
# `.claude/.test-sandbox/` 사용. Windows Git Bash에서 tmp 디렉토리의 fs
# 오버헤드가 리포 내 디렉토리보다 2배 느려 pre-check 1회가 1.2초 → 2.3초
# 로 증폭됐던 것을 제거. 실측 sandbox 경로는 sandbox가 `.gitignore`됨.

set -u
SOURCE_REPO="$(pwd)"
# 리포 내 sandbox 사용 — tmp 디렉토리 fs 오버헤드 회피
SANDBOX_BASE="$SOURCE_REPO/.claude/.test-sandbox"
# 충돌 방지: PID + 에포크
TEST_DIR="$SANDBOX_BASE/run_$$_$(date +%s)"
PASS=0
FAIL=0
FAILED_CASES=""

cleanup() {
  # 현재 디렉토리가 삭제될 TEST_DIR 안이면 먼저 이동 (Windows fs error 방지)
  cd "$SOURCE_REPO" 2>/dev/null || true
  rm -rf "$TEST_DIR"
  # sandbox base가 비었으면 같이 정리
  rmdir "$SANDBOX_BASE" 2>/dev/null || true
}
trap cleanup EXIT

mkdir -p "$TEST_DIR"

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
# fixture 캐시: 같은 fixture에서 run_case 여러 번 호출되면 stdout 재사용.
# reset() 호출 시 무효화. T1·T3·T18 같은 다중 key 검증에서 pre-check 중복
# 실행 제거 — 스위트 체감 시간 큰 폭 절감.
PRECHECK_CACHE=""

run_case() {
  local name="$1"
  local key="$2"
  local pattern="$3"
  local mode="$4"

  if [ -z "$PRECHECK_CACHE" ]; then
    PRECHECK_CACHE=$(bash .claude/scripts/pre-commit-check.sh 2>/dev/null)
  fi

  local actual
  actual=$(echo "$PRECHECK_CACHE" | grep -E "^${key}:" | head -1)

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
  PRECHECK_CACHE=""  # fixture 바뀜 → 캐시 무효화
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

# T11·T12 제거 (audit #7/#15, 2026-04-22) — needs_test_strategist 신호 폐기.

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
# T19. 성능 — 측정값 기록만 (PASS/FAIL 판정 없음)
#
# 과거 2500ms·3500ms 임계값을 두었으나 tmp clone + Windows Git Bash 환경은
# fork·fs 오버헤드 변동이 커서 임계값 튜닝 게임이 됨(실측 ~5~7초 관찰).
# 회귀 방어선 역할을 잃고 테스트 스위트만 느리게 만듦. 임계값 제거하고
# 기록 전용으로 전환. 실제 회귀 감지는 프로젝트 내 `time pre-commit-check.sh`
# 로 수행 (업스트림 실측 ~1.2초). 관련: CLAUDE.md "성능 측정 1회 원칙".
# ─────────────────────────────────────────────────
echo "[T19] 성능 측정 (참고값, PASS/FAIL 없음)"
reset
mkdir -p src docs .claude
echo "export const a = 1" > src/a.ts
echo "export const b = 2" > src/b.ts
echo "# doc" > docs/x.md
echo "{}" > package-lock.json
echo '{"version":"0.0.1"}' > package.json
git add src/a.ts src/b.ts docs/x.md package-lock.json package.json

start=$(date +%s%N)
bash .claude/scripts/pre-commit-check.sh >/dev/null 2>&1
end=$(date +%s%N)
MS=$(( (end - start) / 1000000 ))
echo "    pre-check 1회 실행: ${MS}ms (tmp clone + Windows 기준)"

# T20 제거 (audit #5, 2026-04-22) — tree-hash 캐싱 자체가 폐기됨.

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

# T29: (2026-04-22 삭제) 과거 "docs rename ≥20 → bulk" 룰 폐기. bulk 스테이지
# 자체가 사라졌다. 거대 커밋은 사용자가 스코프 분리한다.

# T30: S5 메타 단독 (HARNESS.json만) → skip
# promotion-log.md 폐기(v0.20.7) 이후 S5 메타 skip 검증을 HARNESS.json 단독
# 변경으로 대체. is_starter 분기 없이 공통 regex가 적용됨.
echo "[T30] 5줄 룰 #4 — HARNESS.json 단독 → skip"
reset
mkdir -p .claude
# staged에 포함될 HARNESS.json 변경 생성 (기존 파일 유지 + 변경점 추가)
cat > .claude/HARNESS.json <<'EOF'
{ "profile": "minimal", "is_starter": true, "version": "test" }
EOF
git add .claude/HARNESS.json
run_case "T30.1 HARNESS.json 단독 → skip" "recommended_stage" "skip" must_match

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
# T35. dead link 증분 감지 (v0.18.6)
# pre-check이 이번 커밋이 유발한 dead link를 잡아 차단하는지 검증.
# ─────────────────────────────────────────────────
reset

# T35.1: 삭제된 md를 가리키는 기존 cluster 링크 → 차단 (pre_check_passed: false)
mkdir -p docs/test_cluster docs/test_target
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

# 이제 dummy 파일 삭제 스테이징. cluster는 여전히 옛 경로 유지.
git rm -q docs/test_target/hn_dummy.md 2>/dev/null
run_case "T35.1 dummy 삭제 + cluster dead link → 차단" "pre_check_passed" "false" must_match

reset

# T35.2: 새로 추가한 md의 링크 대상이 없으면 차단
mkdir -p docs/test_cluster2
cat > docs/test_cluster2/broken.md <<'EOF'
---
title: broken link doc
domain: harness
tags: []
status: in-progress
created: 2026-04-22
---
# broken link
- [없는 파일](../test_target/hn_nonexistent.md)
EOF
git add docs/test_cluster2/broken.md
run_case "T35.2 새 md + 없는 링크 → 차단" "pre_check_passed" "false" must_match

reset

# T35.3: 링크 대상이 같은 커밋에 staged로 추가되면 통과
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
# linker
- [new](../test_target3/hn_new.md)
EOF
git add docs/test_target3/hn_new.md docs/test_cluster3/linker.md
run_case "T35.3 링크 대상도 같이 staged → 통과" "pre_check_passed" "true" must_match

reset

# ─────────────────────────────────────────────────
# T36. frontmatter relates-to.path dead link (audit #12)
# pre-check이 frontmatter의 relates-to.path dead link를 잡아 차단하는지 검증.
# ─────────────────────────────────────────────────

# T36.1: relates-to.path가 존재 파일 → 통과
mkdir -p docs/t36_target docs/t36_src
cat > docs/t36_target/hn_existing.md <<'EOF'
---
title: existing target
domain: harness
tags: []
status: completed
created: 2026-04-22
---
# existing
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
# refer
EOF
git add docs/t36_target/hn_existing.md docs/t36_src/hn_refer.md
run_case "T36.1 relates-to 존재 파일 → 통과" "pre_check_passed" "true" must_match

reset

# T36.2: relates-to.path가 미존재 파일 → 차단
mkdir -p docs/t36b
cat > docs/t36b/hn_broken_rt.md <<'EOF'
---
title: broken relates-to
domain: harness
tags: []
relates-to:
  - path: ../nowhere/hn_ghost.md
    rel: references
status: in-progress
created: 2026-04-22
---
# broken rt
EOF
git add docs/t36b/hn_broken_rt.md
run_case "T36.2 relates-to 미존재 파일 → 차단" "pre_check_passed" "false" must_match

reset

# T36.3: relates-to.path 앵커 포함 → 파일 존재하면 통과
mkdir -p docs/t36c_target docs/t36c_src
cat > docs/t36c_target/hn_anchor_target.md <<'EOF'
---
title: anchor target
domain: harness
tags: []
status: completed
created: 2026-04-22
---
# anchor target
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
# anchor refer
EOF
git add docs/t36c_target/hn_anchor_target.md docs/t36c_src/hn_anchor_refer.md
run_case "T36.3 relates-to 앵커 포함 + 파일 존재 → 통과" "pre_check_passed" "true" must_match

reset

# T36.4: 대상 md도 같은 커밋에 staged → 통과 (오탐 방지)
mkdir -p docs/t36d_src docs/t36d_target
cat > docs/t36d_target/hn_staged.md <<'EOF'
---
title: staged target
domain: harness
tags: []
status: in-progress
created: 2026-04-22
---
# staged target
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
# staged refer
EOF
git add docs/t36d_target/hn_staged.md docs/t36d_src/hn_staged_refer.md
run_case "T36.4 relates-to 대상도 같이 staged → 통과" "pre_check_passed" "true" must_match

reset

# T36.5: 멀티 항목 relates-to — 한 항목이 dead이면 차단
mkdir -p docs/t36e_target docs/t36e_src
cat > docs/t36e_target/hn_ok.md <<'EOF'
---
title: ok
domain: harness
tags: []
status: completed
created: 2026-04-22
---
# ok
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
# multi
EOF
git add docs/t36e_target/hn_ok.md docs/t36e_src/hn_multi.md
run_case "T36.5 relates-to 멀티 항목 중 1건 dead → 차단" "pre_check_passed" "false" must_match

reset

# T36.6: rel만 있고 path 없음 → skip (파싱 오류 회피, 통과)
mkdir -p docs/t36f
cat > docs/t36f/hn_norelatespath.md <<'EOF'
---
title: no relates path
domain: harness
tags: []
relates-to:
  - rel: references
status: in-progress
created: 2026-04-22
---
# no path
EOF
git add docs/t36f/hn_norelatespath.md
run_case "T36.6 path 없는 relates-to 항목 → skip/통과" "pre_check_passed" "true" must_match

reset

# T36.7: relates-to docs/ 루트 기준 상대 경로 (rules/docs.md 원본 규칙)
mkdir -p docs/t36g_target docs/t36g_src
cat > docs/t36g_target/hn_rootabs.md <<'EOF'
---
title: root abs target
domain: harness
tags: []
status: completed
created: 2026-04-22
---
# root abs
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
# refer
EOF
git add docs/t36g_target/hn_rootabs.md docs/t36g_src/hn_rootabs_refer.md
run_case "T36.7 relates-to docs/ 루트 기준 경로 → 통과" "pre_check_passed" "true" must_match

reset

# T36.8: relates-to docs/ 루트 기준 + 미존재 → 차단
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
# broken
EOF
git add docs/t36h/hn_rootabs_broken.md
run_case "T36.8 relates-to docs/ 루트 기준 미존재 → 차단" "pre_check_passed" "false" must_match

reset

# ─────────────────────────────────────────────────
# T38. 검사 A 경로 해석 정밀화 (근본 수정 2026-04-22)
# basename grep 후보 중 실제 링크 경로가 삭제 경로와 일치할 때만 dead.
# ─────────────────────────────────────────────────

# T38.1: 같은 basename 다른 경로 → 오탐 없음
mkdir -p docs/t38a_a docs/t38a_b
cat > docs/t38a_a/hn_sibling.md <<'EOF'
---
title: a sibling
domain: harness
tags: []
status: completed
created: 2026-04-22
---
# A
EOF
cat > docs/t38a_b/hn_sibling.md <<'EOF'
---
title: b sibling
domain: harness
tags: []
status: completed
created: 2026-04-22
---
# B
EOF
cat > docs/t38a_a/hn_ref_to_a.md <<'EOF'
---
title: ref to a
domain: harness
tags: []
status: completed
created: 2026-04-22
---
# ref
- [A](./hn_sibling.md)
EOF
git add docs/t38a_a/hn_sibling.md docs/t38a_b/hn_sibling.md docs/t38a_a/hn_ref_to_a.md
git commit -q -m "prep T38 baseline" 2>/dev/null

# 이제 b의 sibling만 삭제 — a의 ref는 **유지되어야** (오탐 방지)
git rm -q docs/t38a_b/hn_sibling.md 2>/dev/null
run_case "T38.1 같은 basename 다른 경로 → 오탐 없음 (통과)" "pre_check_passed" "true" must_match

reset

# ─────────────────────────────────────────────────
# T37. S6 단독 + ≤5줄 → Stage 0 자동화 (audit #17)
# staging.md "C. 완화"의 자동화. 문서 경미 수정은 skip.
# ─────────────────────────────────────────────────

# T37.1: docs/에서 1줄 수정 → skip
mkdir -p docs/guides
cat > docs/guides/hn_probe.md <<'EOF'
---
title: probe
domain: harness
tags: []
status: completed
created: 2026-04-22
---
# probe
기존 내용.
EOF
git add docs/guides/hn_probe.md
git commit -q -m "prep T37 baseline" 2>/dev/null

# 1줄만 추가
echo "추가 한 줄." >> docs/guides/hn_probe.md
git add docs/guides/hn_probe.md
run_case "T37.1 docs 1줄 수정 → skip" "recommended_stage" "skip" must_match

reset

# T37.2: docs/에서 10줄 수정 → standard (S6 ≤5줄 조건 미충족)
mkdir -p docs/guides
cat > docs/guides/hn_probe2.md <<'EOF'
---
title: probe2
domain: harness
tags: []
status: completed
created: 2026-04-22
---
# probe2
EOF
git add docs/guides/hn_probe2.md
git commit -q -m "prep T37.2 baseline" 2>/dev/null

# 10줄 추가
for i in $(seq 1 10); do echo "줄 ${i}" >> docs/guides/hn_probe2.md; done
git add docs/guides/hn_probe2.md
run_case "T37.2 docs 10줄 수정 → standard (≤5줄 아님)" "recommended_stage" "standard" must_match

reset

# T37.3: docs + 코드 동반 → standard (단독 아님)
mkdir -p docs/guides src
cat > docs/guides/hn_probe3.md <<'EOF'
---
title: probe3
domain: harness
tags: []
status: completed
created: 2026-04-22
---
# probe3
EOF
echo "export const foo = 1" > src/foo.ts
git add docs/guides/hn_probe3.md src/foo.ts
run_case "T37.3 docs 1줄 + 코드 동반 → deep/standard (skip 아님)" "recommended_stage" "skip" must_not_match

reset

# T39. 이동 커밋 → skip (WIP→완료 이동 + cluster 갱신 패턴)
# ─────────────────────────────────────────────────

# T39.1: docs rename 단독 → skip
mkdir -p docs/WIP docs/incidents
cat > docs/WIP/incidents--hn_move_probe.md <<'EOF'
---
title: move probe
domain: harness
tags: []
status: completed
created: 2026-04-25
---
# move probe
EOF
git add docs/WIP/incidents--hn_move_probe.md
git commit -q -m "prep T39.1 baseline" 2>/dev/null

git mv docs/WIP/incidents--hn_move_probe.md docs/incidents/hn_move_probe.md
git add docs/incidents/hn_move_probe.md
run_case "T39.1 docs rename 단독 → skip" "recommended_stage" "skip" must_match

reset

# T39.2: docs rename + clusters M 동반 → skip (이동 커밋 전형 패턴)
mkdir -p docs/WIP docs/incidents
cat > docs/WIP/incidents--hn_move_probe2.md <<'EOF'
---
title: move probe2
domain: harness
tags: []
status: completed
created: 2026-04-25
---
# move probe2
EOF
git add docs/WIP/incidents--hn_move_probe2.md
git commit -q -m "prep T39.2 baseline" 2>/dev/null

git mv docs/WIP/incidents--hn_move_probe2.md docs/incidents/hn_move_probe2.md
echo "- [move probe2](../incidents/hn_move_probe2.md)" >> docs/clusters/harness.md
git add docs/incidents/hn_move_probe2.md docs/clusters/harness.md
run_case "T39.2 docs rename + cluster M → skip" "recommended_stage" "skip" must_match

reset

# T39.3: docs rename + 코드 파일 M 동반 → skip 아님 (코드 변경 포함)
mkdir -p docs/WIP docs/incidents .claude/scripts
cat > docs/WIP/incidents--hn_move_probe3.md <<'EOF'
---
title: move probe3
domain: harness
tags: []
status: completed
created: 2026-04-25
---
# move probe3
EOF
git add docs/WIP/incidents--hn_move_probe3.md
git commit -q -m "prep T39.3 baseline" 2>/dev/null

git mv docs/WIP/incidents--hn_move_probe3.md docs/incidents/hn_move_probe3.md
echo "# change" >> .claude/scripts/pre-commit-check.sh
git add docs/incidents/hn_move_probe3.md .claude/scripts/pre-commit-check.sh
run_case "T39.3 docs rename + 코드 M → skip 아님" "recommended_stage" "skip" must_not_match

reset

# T39.4: docs rename + cluster M + S10(반복수정) → 이동 커밋 면제로 skip 유지
mkdir -p docs/WIP docs/incidents
cat > docs/WIP/incidents--hn_move_probe4.md <<'EOF'
---
title: move probe4
domain: harness
tags: []
status: completed
created: 2026-04-25
---
# move probe4
EOF
git add docs/WIP/incidents--hn_move_probe4.md
git commit -q -m "prep T39.4 baseline v1" 2>/dev/null
git commit -q --allow-empty -m "prep T39.4 baseline v2" 2>/dev/null
git commit -q --allow-empty -m "prep T39.4 baseline v3" 2>/dev/null

git mv docs/WIP/incidents--hn_move_probe4.md docs/incidents/hn_move_probe4.md
echo "- [probe4](../incidents/hn_move_probe4.md)" >> docs/clusters/harness.md
git add docs/incidents/hn_move_probe4.md docs/clusters/harness.md
run_case "T39.4 docs rename + cluster M + S10 → 이동 커밋 면제로 skip" "recommended_stage" "skip" must_match

reset

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
