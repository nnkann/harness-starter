#!/bin/bash
# 거대 커밋(--bulk) 정량 가드. review 대신 실행.
# 실패 시 exit 2 + stderr에 원인·대응책.
# SSOT: .claude/rules/staging.md "--bulk Stage" 섹션.
set +e

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
cd "$ROOT" || { echo "ERR: git 저장소 아님" >&2; exit 2; }

FAIL=0
REPORT=""

log_pass() { echo "  [PASS] $1"; }
log_fail() {
  echo "  [FAIL] $1" >&2
  echo "         대응: $2" >&2
  REPORT="$REPORT\n- $1 — $2"
  FAIL=$((FAIL + 1))
}

echo "═══ --bulk 정량 가드 ═══"

# 가드 1: test-pre-commit.sh
echo "[1/4] test-pre-commit.sh"
if bash .claude/scripts/test-pre-commit.sh > /tmp/bulk-t1.log 2>&1; then
  log_pass "test-pre-commit (33 케이스)"
else
  log_fail "test-pre-commit 실패" "cat /tmp/bulk-t1.log 확인 후 해당 케이스 수정"
fi

# 가드 2: test-bash-guard.sh
echo "[2/4] test-bash-guard.sh"
if bash .claude/scripts/test-bash-guard.sh > /tmp/bulk-t2.log 2>&1; then
  log_pass "test-bash-guard (13 케이스)"
else
  log_fail "test-bash-guard 실패" "cat /tmp/bulk-t2.log 확인 후 해당 케이스 수정"
fi

# 가드 3: downstream-readiness.sh
echo "[3/4] downstream-readiness.sh"
DR_OUT=$(bash .claude/scripts/downstream-readiness.sh 2>&1)
DR_EXIT=$?
if [ $DR_EXIT -eq 0 ] && ! echo "$DR_OUT" | grep -qE "^누락: [1-9]"; then
  log_pass "downstream-readiness (누락 0)"
else
  echo "$DR_OUT" >&2
  log_fail "downstream-readiness 실패" "위 출력의 [누락]/[경고] 항목 해결"
fi

# 가드 4: 파일명·참조 정합성
echo "[4/4] 파일명·참조 정합성"

# 4a: 날짜 suffix 잔재 (archived 제외)
DATE_SUFFIX=$(find docs -name "*_[0-9][0-9][0-9][0-9][0-9][0-9].md" ! -path "*/archived/*" 2>/dev/null)
if [ -z "$DATE_SUFFIX" ]; then
  log_pass "날짜 suffix 잔재 0 (archived 제외)"
else
  echo "$DATE_SUFFIX" >&2
  log_fail "날짜 suffix 파일 존재" "naming.md 규칙: archived 외 날짜 suffix 금지. 위 파일 rename 또는 archived로 이동"
fi

# 4b: dead link (간이 — docs·rules·skills md 내 마크다운 링크)
DEAD_LINKS=""
while IFS= read -r src; do
  [ -z "$src" ] && continue
  # (path.md) 패턴만 (인라인 코드·블록 제외는 어려워 간이)
  grep -oE '\]\((\.\./|\./|docs/)[^)]+\.md[^)]*\)' "$src" 2>/dev/null \
    | sed -E 's/\]\(([^)]+)\)/\1/' | while read -r link; do
    [ -z "$link" ] && continue
    path="${link%%#*}"
    src_dir=$(dirname "$src")
    case "$path" in
      http*|/*|mailto:*) continue ;;
      docs/*) abs="$path" ;;
      *) abs="$src_dir/$path" ;;
    esac
    [ ! -f "$abs" ] && echo "DEAD: $src -> $link"
  done
done < <(find docs .claude -name "*.md" ! -path "*/archived/*" 2>/dev/null) > /tmp/bulk-deadlinks.log

if [ ! -s /tmp/bulk-deadlinks.log ]; then
  log_pass "dead link 0 (docs·rules·skills)"
else
  cat /tmp/bulk-deadlinks.log >&2
  log_fail "dead link 존재" "위 링크들이 실제 파일을 가리키도록 수정 (rename 후 참조 치환 누락일 가능성)"
fi

echo "═══ 결과 ═══"
if [ $FAIL -eq 0 ]; then
  echo "✅ 모든 가드 통과. --bulk 커밋 진행 가능."
  exit 0
else
  echo "🚫 $FAIL개 가드 실패. 커밋 차단." >&2
  echo -e "\n실패 항목:$REPORT" >&2
  echo "" >&2
  echo "대응 후 재시도. --bulk가 review 역할을 대체하므로 가드는 우회 불가." >&2
  exit 2
fi
