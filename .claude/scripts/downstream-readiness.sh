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
HARNESS_SKILLS=""
RUNTIME_ADAPTERS=""

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

add_observation() {
  REPORT="${REPORT}\n[관측] $1"
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

  RUNTIME_STACK=$(python3 -c "import json; data=json.load(open('.claude/HARNESS.json', encoding='utf-8')); print(data.get('runtime_stack', 'legacy-claude-codex'))" 2>/dev/null || echo "legacy-claude-codex")
  add_observation "runtime_stack: $RUNTIME_STACK"

  RUNTIME_ADAPTERS=$(python3 -c "import json; data=json.load(open('.claude/HARNESS.json', encoding='utf-8')); adapters=data.get('runtime_adapters') or {'claude':'primary-adapter','codex':'bridge'}; print(','.join(adapters.keys()) if isinstance(adapters, dict) else 'claude,codex')" 2>/dev/null || echo "claude,codex")
  add_observation "runtime_adapters: $RUNTIME_ADAPTERS"

  HARNESS_SKILLS=$(python3 -c "import json; data=json.load(open('.claude/HARNESS.json', encoding='utf-8')); print(data.get('skills', ''))" 2>/dev/null || echo "")

  if echo ",$RUNTIME_ADAPTERS," | grep -q ",agy,"; then
    if [ -f ".claude/scripts/agy-review.sh" ]; then
      add_ok "agy runner: .claude/scripts/agy-review.sh"
      add_observation "agy handoff: ${AGY_HANDOFF_FILE:-.claude/memory/session-agy-review.md}" # fallback runtime handoff path
      add_observation "agy permission_mode: ${AGY_PERMISSION_MODE:-full}"
      if ! grep -q -- '--dangerously-skip-permissions' .claude/scripts/agy-review.sh; then
        add_warning "agy runner가 full permission advisory 계약을 드러내지 않음 — 최신 agy-review.sh 필요"
      fi
    else
      add_warning "agy runner 없음 — 공통 Agy advisory 호출은 .claude/scripts/agy-review.sh 필요"
    fi

    if [ -n "${AGY_BIN:-}" ] && [ -x "$AGY_BIN" ]; then
      add_observation "agy callable: $AGY_BIN"
    elif command -v agy >/dev/null 2>&1; then
      add_observation "agy callable: $(command -v agy)"
    elif [ -x "/Users/kann/.local/bin/agy" ]; then
      add_observation "agy callable: /Users/kann/.local/bin/agy"
    else
      add_warning "agy executable 미발견 — AGY_BIN 또는 PATH 설정 필요"
    fi
  fi
fi

# ─────────────────────────────────────────────
# 1.5. 핵심 skill surface 정합성
# ─────────────────────────────────────────────
for skill in commit implementation harness-upgrade; do
  if [ -n "$HARNESS_SKILLS" ] && ! echo ",$HARNESS_SKILLS," | grep -q ",$skill,"; then
    add_issue "HARNESS.json skills에 핵심 스킬 '$skill' 누락 — 스킬 discovery silent fail 위험"
  fi
  if [ ! -f ".claude/skills/$skill/SKILL.md" ]; then
    add_issue ".claude/skills/$skill/SKILL.md 없음 — Claude/legacy skill surface 누락"
  else
    add_ok ".claude skill: $skill"
  fi
done

if echo ",$RUNTIME_ADAPTERS," | grep -q ",codex,"; then
  if [ ! -f "AGENTS.md" ]; then
    add_issue "Codex adapter 감지됐지만 AGENTS.md 없음 — Codex가 하네스 스킬 진입점을 못 읽을 수 있음"
  else
    add_ok "Codex entrypoint: AGENTS.md"
  fi
  for skill in commit implementation harness-upgrade; do
    if [ ! -f ".agents/skills/$skill/SKILL.md" ]; then
      add_issue ".agents/skills/$skill/SKILL.md 없음 — Codex adapter skill surface 누락"
    else
      add_ok ".agents skill: $skill"
    fi
  done
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
  for matcher in 'session-start.py' 'bash-guard.sh'; do
    if ! grep -q "$matcher" .claude/settings.json; then
      add_warning "settings.json: '$matcher' 관련 hook 누락 가능"
    fi
  done
  # bash-guard.sh는 --no-verify 차단 책임. pre-commit-check 호출은
  # commit 스킬이 직접 수행(매 Bash 호출마다 pre-check 돌면 성능 폭증).
  if [ -f ".claude/scripts/bash-guard.sh" ]; then
    if ! grep -q 'no-verify' .claude/scripts/bash-guard.sh; then
      add_warning "bash-guard.sh: --no-verify 차단 로직 누락"
    fi
  fi

  # settings.json schema 유효성 (Claude Code 재로드 시 ~20k 토큰 에러 덤프 방지)
  if [ -f ".claude/scripts/validate-settings.sh" ]; then
    if ! bash .claude/scripts/validate-settings.sh .claude/settings.json >/dev/null 2>&1; then
      add_issue "settings.json schema 검증 실패 — Claude Code 재로드 시 20k 토큰 에러 덤프"
    fi
  fi

  # argument-constraint 광역 매처 감지 (rules/hooks.md 금지)
  # 패턴: "if": "Bash(... -X ...)" 또는 "Bash(* ... *)" — 공백+- 또는 --
  BAD_MATCHERS=$(grep -nE '"if":[[:space:]]*"Bash\([^)]*[[:space:]]--?[a-zA-Z][^)]*\)"' .claude/settings.json 2>/dev/null)
  if [ -n "$BAD_MATCHERS" ]; then
    add_issue "settings.json: argument-constraint 광역 매처 발견 (rules/hooks.md 금지). bash-guard.sh 단일 hook으로 통합 필요:"
    echo "$BAD_MATCHERS" | sed 's/^/         /' >&2
  fi
  # bash-guard.sh 통합 매처 확인 (v1.9.0 이후 권장 패턴)
  if ! grep -q 'bash-guard\.sh' .claude/settings.json; then
    add_warning "settings.json: bash-guard.sh hook 없음 — 광역 매처 패턴 fragility (공식 문서 경고) 회피 권장"
  fi
fi

# bash-guard.sh 자체 존재
if [ ! -f ".claude/scripts/bash-guard.sh" ]; then
  add_warning "bash-guard.sh 없음 — 구버전 settings.json 매처 패턴 사용 중일 가능성"
fi

# ─────────────────────────────────────────────
# 4. pre_commit_check.py 핵심 신호 출력 확인
# ─────────────────────────────────────────────
if [ ! -f ".claude/scripts/pre_commit_check.py" ]; then
  add_issue "pre_commit_check.py 없음"
else
  for key in 'pre_check_passed:' 'recommended_stage:' 's1_level:'; do
    if ! grep -q "\"$key" .claude/scripts/pre_commit_check.py; then
      add_warning "pre_commit_check.py: '$key' stdout 누락 — 구버전 가능성"
    fi
  done
fi

# ─────────────────────────────────────────────
# 5. review.md 핵심 카테고리 확인
# ─────────────────────────────────────────────
if [ ! -f ".claude/agents/review.md" ]; then
  add_issue "review.md 없음"
else
  for category in '전제 컨텍스트' '오염 검토' 'implementation 스킬 우회 감지'; do
    if ! grep -q "$category" .claude/agents/review.md; then
      add_warning "review.md: '$category' 카테고리 누락 — 구버전 가능성"
    fi
  done
fi

# ─────────────────────────────────────────────
# 6. 회귀 테스트 스크립트 존재
# ─────────────────────────────────────────────
if [ ! -f ".claude/scripts/tests/test_pre_commit.py" ]; then
  add_warning "tests/test_pre_commit.py 없음 — 회귀 검증 불가"
fi
if [ ! -f ".claude/scripts/test-bash-guard.sh" ]; then
  add_warning "test-bash-guard.sh 없음 — 회귀 검증 불가"
fi

# ─────────────────────────────────────────────
# 7. 검증 도구 가용성 관측
# ─────────────────────────────────────────────
for tool in ruff pyright mypy shellcheck; do
  if command -v "$tool" >/dev/null 2>&1; then
    add_ok "검증 도구 '$tool' 사용 가능"
  else
    add_observation "검증 도구 '$tool' 없음 — 해당 lint/LSP 검사는 실행되지 않을 수 있음"
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
