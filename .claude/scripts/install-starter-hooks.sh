#!/bin/bash
# harness-starter 전용 git hook 설치.
# is_starter: true인 repo에서만 의미 있음.
# harness-sync Step 5 또는 수동으로 실행.

set -e

HOOK_FILE=".git/hooks/pre-commit"

# is_starter 확인
IS_STARTER=$(grep -o '"is_starter":[[:space:]]*true' .claude/HARNESS.json 2>/dev/null)
if [ -z "$IS_STARTER" ]; then
  echo "is_starter: false — starter hook 설치 스킵" >&2
  exit 0
fi

cat > "$HOOK_FILE" << 'HOOK'
#!/bin/bash
# 하네스 스타터 보호 + 시크릿 스캔 (Phase 1 hook 이중화 — 2026-05-02)
# threat-analyst: HARNESS_DEV=1 우회 시에도 시크릿 차단 필요

# ─────────────────────────────────────────────
# 1. 시크릿 line 스캔 (HARNESS_DEV 우회와 무관하게 항상 실행)
# pre_commit_check.py:431~434 S1_LINE_PAT 동등 + scripts/install-secret-scan-hook.sh 패턴 풀 통합
# ─────────────────────────────────────────────
STAGED=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null)
if [ -n "$STAGED" ]; then
  PATTERN='sb_secret_[A-Za-z0-9_]{10,}'
  PATTERN="$PATTERN"'|service_role'
  PATTERN="$PATTERN"'|AKIA[0-9A-Z]{16}|aws_secret_access_key'
  PATTERN="$PATTERN"'|sk_live_[0-9a-zA-Z]{20,}|sk_test_[0-9a-zA-Z]{20,}|rk_live_[0-9a-zA-Z]{10,}'
  PATTERN="$PATTERN"'|ghp_[0-9a-zA-Z]{36}|gho_[0-9a-zA-Z]{30,}|ghs_[0-9a-zA-Z]{30,}|ghu_[0-9a-zA-Z]{30,}'
  PATTERN="$PATTERN"'|glpat-[0-9a-zA-Z_-]{20,}'
  PATTERN="$PATTERN"'|xox[baprs]-[0-9a-zA-Z-]+'
  PATTERN="$PATTERN"'|AIza[0-9A-Za-z_-]{35}'
  PATTERN="$PATTERN"'|sk-ant-[a-zA-Z0-9_-]{20,}|sk-proj-[a-zA-Z0-9_-]{20,}'
  PATTERN="$PATTERN"'|-----BEGIN ((RSA|EC|DSA|OPENSSH|PGP) )?PRIVATE KEY-----'

  # S1_LINE_EXEMPT 면제: 하네스 자체가 시크릿 패턴을 SSOT로 문서화하는 위치
  # SSOT: pre_commit_check.py S1_LINE_EXEMPT — 동기화 필수
  EXEMPT_RE='^\.claude/(scripts|agents|rules|skills|memory)/'
  EXEMPT_RE="$EXEMPT_RE"'|^docs/(WIP|incidents|decisions|guides|harness)/'
  EXEMPT_RE="$EXEMPT_RE"'|^scripts/install-secret-scan-hook\.sh$'

  HITS=$(echo "$STAGED" | while IFS= read -r f; do
    [ -z "$f" ] && continue
    if echo "$f" | grep -qE "$EXEMPT_RE"; then continue; fi
    git diff --cached -- "$f" 2>/dev/null | grep -En "^\+.*($PATTERN)" || true
  done)

  if [ -n "$HITS" ]; then
    echo ""
    echo "🚫 시크릿 line-confirmed 발견. 커밋 차단 (HARNESS_DEV 우회와 무관)."
    echo "$HITS" | head -10
    echo ""
    echo "   → 해당 값은 환경변수로 옮기고 코드에서 직접 참조 금지."
    echo "   → 이미 git history에 진입했다면 즉시 rotation + history 재작성 필요."
    exit 1
  fi
fi

# ─────────────────────────────────────────────
# 2. 하네스 스타터 보호: HARNESS_DEV=1 없으면 커밋 차단
# ─────────────────────────────────────────────
if [ "$HARNESS_DEV" != "1" ]; then
  echo ""
  echo "🚫 이 repo는 하네스 스타터(템플릿)입니다."
  echo "   직접 커밋할 수 없습니다."
  echo ""
  echo "   하네스 개발이 목적이라면:"
  echo "     HARNESS_DEV=1 git commit ..."
  echo "   (시크릿 hook은 HARNESS_DEV 무관하게 항상 검사함)"
  echo ""
  exit 1
fi
# 버전 범프 체크는 pre_commit_check.py가 담당 (commit Step 4에서 Claude가 판단·갱신)
HOOK

chmod +x "$HOOK_FILE"
echo "✅ starter pre-commit hook 설치됨: $HOOK_FILE"

# HARNESS.json hook_installed 플래그 갱신
python3 - <<'PY'
import json
p = ".claude/HARNESS.json"
with open(p, encoding="utf-8") as f:
    d = json.load(f)
if d.get("hook_installed") is not True:
    d["hook_installed"] = True
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("✅ HARNESS.json hook_installed=true 갱신")
PY
