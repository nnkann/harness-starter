#!/bin/bash
# downstream-readiness.sh — 다운스트림 프로젝트 하네스 적용 누락 감지
#
# harness-upgrade의 "수동 액션"이 빠진 채로 운영되면 staging·review가
# silent fail. 본 스크립트는 자가 진단으로 누락 항목을 보고한다.
#
# 사용: bash .claude/scripts/downstream-readiness.sh
# 종료 코드: 0=문제 없음, 1=누락 있음

set -u
ISSUES=0
WARNINGS=0
REPORT=""

add_issue() {
  ISSUES=$((ISSUES + 1))
  REPORT="${REPORT}\n[누락] $1"
}

add_warning() {
  WARNINGS=$((WARNINGS + 1))
  REPORT="${REPORT}\n[경고] $1"
}

add_ok() {
  REPORT="${REPORT}\n[OK]   $1"
}

echo ""
echo "═══ 다운스트림 하네스 적용 자가 진단 ═══"

# ─────────────────────────────────────────────
# 1. HARNESS.json
# ─────────────────────────────────────────────
if [ ! -f ".claude/HARNESS.json" ]; then
  add_issue "HARNESS.json 없음 — harness-init 또는 harness-adopt 필요"
else
  add_ok "HARNESS.json 존재"
  IS_STARTER=$(grep -oE '"is_starter"[[:space:]]*:[[:space:]]*(true|false)' .claude/HARNESS.json | grep -oE '(true|false)')
  if [ -z "$IS_STARTER" ]; then
    add_issue "HARNESS.json: is_starter 필드 누락 — true/false 명시 필요"
  else
    add_ok "is_starter: $IS_STARTER"
  fi
fi

# ─────────────────────────────────────────────
# 2. naming.md 도메인 등급
# ─────────────────────────────────────────────
if [ ! -f ".claude/rules/naming.md" ]; then
  add_issue "naming.md 없음"
else
  CONFIRMED=$(grep -E '^확정:' .claude/rules/naming.md | sed 's/확정://' | tr ',' '\n' | sed 's/^ *//;s/ *$//' | grep -v '^$')
  if [ -z "$CONFIRMED" ]; then
    add_warning "naming.md 도메인 목록 비어 있음 — harness-init 필요"
  else
    GRADE_SECTION=$(awk '/^## 도메인 등급/{flag=1; next} /^## /{flag=0} flag' .claude/rules/naming.md)
    if [ -z "$GRADE_SECTION" ]; then
      add_issue "naming.md '도메인 등급' 섹션 없음 — staging S9 무력화"
    else
      # 확정 도메인 전체가 등급 분류됐는지 확인
      # critical/normal/meta 라인의 본문에서 도메인 단어 매칭 (콤마·공백 구분)
      GRADE_LINES=$(echo "$GRADE_SECTION" | grep -E '^\s*-\s*\*\*(critical|normal|meta)\*\*')
      UNCLASSIFIED=""
      for d in $CONFIRMED; do
        # 도메인명이 등급 라인에 단어로 등장하는지 (전후가 콤마·공백·줄끝)
        if ! echo "$GRADE_LINES" | grep -qE "(^|[[:space:],:])${d}([[:space:],]|$)"; then
          UNCLASSIFIED="${UNCLASSIFIED} ${d}"
        fi
      done
      if [ -n "$UNCLASSIFIED" ]; then
        add_warning "도메인 등급 미분류:${UNCLASSIFIED} — staging이 normal 폴백"
      else
        add_ok "확정 도메인 전체가 등급 분류됨"
      fi
    fi

    # 경로 매핑 섹션
    PATH_SECTION=$(awk '/^## 경로 → 도메인 매핑/{flag=1; next} /^## /{flag=0} flag' .claude/rules/naming.md)
    if [ -z "$PATH_SECTION" ] || ! echo "$PATH_SECTION" | grep -qE '\*\*[[:space:]]*→'; then
      # 매핑 라인이 없으면 (예시 코드 블록만 있고 실제 정의 없음)
      if ! echo "$PATH_SECTION" | grep -qE '^\s*[^#].*→\s*\w+'; then
        add_warning "naming.md '경로 → 도메인 매핑' 정의 없음 — 코드 파일 도메인 추출 안 됨"
      fi
    fi
  fi
fi

# ─────────────────────────────────────────────
# 3. settings.json hook 정합성
# ─────────────────────────────────────────────
if [ ! -f ".claude/settings.json" ]; then
  add_warning "settings.json 없음"
else
  # 핵심 hook 존재 확인
  for matcher in 'no-verify' 'pre-commit-check.sh' 'session-start.sh'; do
    if ! grep -q "$matcher" .claude/settings.json; then
      add_warning "settings.json: '$matcher' 관련 hook 누락 가능"
    fi
  done

  # 광역 매처 회귀 (-n 단독)
  if grep -q '"if": *"Bash(\* -n \*)"' .claude/settings.json; then
    add_issue "settings.json: 광역 -n 매처 발견 (Bash(* -n *)) — incident bash_n_flag_overblock 참조, git commit/push로 한정 필요"
  fi
fi

# ─────────────────────────────────────────────
# 4. pre-commit-check.sh 핵심 신호 출력 확인
# ─────────────────────────────────────────────
if [ ! -f ".claude/scripts/pre-commit-check.sh" ]; then
  add_issue "pre-commit-check.sh 없음"
else
  for key in 'signals:' 'recommended_stage:' 's1_level:' 'needs_test_strategist:'; do
    if ! grep -q "echo \"$key" .claude/scripts/pre-commit-check.sh; then
      add_warning "pre-commit-check.sh: '$key' stdout 누락 — 구버전 가능성"
    fi
  done
fi

# ─────────────────────────────────────────────
# 5. review.md 핵심 카테고리 확인
# ─────────────────────────────────────────────
if [ ! -f ".claude/agents/review.md" ]; then
  add_issue "review.md 없음"
else
  for category in '전제 컨텍스트' '오염 검토' '허위 후속 감지'; do
    if ! grep -q "$category" .claude/agents/review.md; then
      add_warning "review.md: '$category' 카테고리 누락 — 구버전 가능성"
    fi
  done
fi

# ─────────────────────────────────────────────
# 6. 회귀 테스트 스크립트 존재
# ─────────────────────────────────────────────
for s in test-pre-commit.sh test-hooks.sh; do
  if [ ! -f ".claude/scripts/$s" ]; then
    add_warning "$s 없음 — 회귀 검증 불가"
  fi
done

# ─────────────────────────────────────────────
# 결과
# ─────────────────────────────────────────────
echo -e "$REPORT"
echo ""
echo "═══ 결과 ═══"
echo "누락: $ISSUES (silent fail 위험)"
echo "경고: $WARNINGS (확인 권장)"

if [ "$ISSUES" -gt 0 ]; then
  echo ""
  echo "→ docs/harness/MIGRATIONS.md '수동 액션' 섹션 참조"
  exit 1
fi
exit 0
