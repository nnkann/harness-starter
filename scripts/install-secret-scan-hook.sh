#!/usr/bin/env bash
# scripts/install-secret-scan-hook.sh
#
# pre-commit hook에 시크릿 스캔을 추가한다.
# gitleaks가 설치되어 있으면 우선 사용, 없으면 grep 폴백.
#
# 사용법:
#   bash scripts/install-secret-scan-hook.sh
#
# 이미 pre-commit hook이 있으면 덮어쓰지 않고 "secret-scan" 섹션만 추가한다.
#
# 주의: grep 폴백은 best-effort 방어다.
#   - 리터럴 분할("sb_" + "secret_"), Base64 인코딩, 변수 보간은 탐지 불가.
#   - 실제 방어가 중요하면 gitleaks 설치 필수: https://github.com/gitleaks/gitleaks
#   - 서버측(pre-receive) 훅이 가장 확실한 방어선이다. CLI의 --no-verify는 로컬 훅 전체를 우회한다.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK_FILE="$REPO_ROOT/.git/hooks/pre-commit"
MARKER_START="# >>> secret-scan (managed) >>>"
MARKER_END="# <<< secret-scan (managed) <<<"

SCAN_BLOCK=$(cat <<'HOOK_EOF'
# >>> secret-scan (managed) >>>
# 스테이징된 파일에서 시크릿 패턴 검사.
# gitleaks 있으면 우선, 없으면 grep 폴백.
if command -v gitleaks >/dev/null 2>&1; then
  if ! gitleaks protect --staged --redact --verbose; then
    echo ""
    echo "🚫 시크릿 패턴 발견. 커밋 차단."
    echo "   → 해당 값은 .env.local로 옮기고 process.env.X로 참조하라."
    echo "   → 이미 커밋 이력이 있다면 키 rotation + git history 재작성 필요."
    exit 1
  fi
else
  STAGED=$(git diff --cached --name-only --diff-filter=ACM -z | tr '\0' '\n')
  if [ -n "$STAGED" ]; then
    # 패턴: AWS / Stripe / GitHub / GitLab / Slack / Supabase / Google / OpenAI / Anthropic / JWT / PEM / 일반.
    # 최소 길이와 고유 접두사를 함께 사용해 오탐을 줄인다.
    PATTERN='sb_secret_[A-Za-z0-9_]{10,}'
    PATTERN="$PATTERN"'|service_role'
    PATTERN="$PATTERN"'|AKIA[0-9A-Z]{16}'
    PATTERN="$PATTERN"'|aws_secret_access_key'
    PATTERN="$PATTERN"'|sk_live_[0-9a-zA-Z]{20,}|sk_test_[0-9a-zA-Z]{20,}|rk_live_[0-9a-zA-Z]{10,}'
    PATTERN="$PATTERN"'|ghp_[0-9a-zA-Z]{36}|gho_[0-9a-zA-Z]{30,}|ghs_[0-9a-zA-Z]{30,}|ghu_[0-9a-zA-Z]{30,}'
    PATTERN="$PATTERN"'|glpat-[0-9a-zA-Z_-]{20,}'
    PATTERN="$PATTERN"'|xox[baprs]-[0-9a-zA-Z-]+'
    PATTERN="$PATTERN"'|AIza[0-9A-Za-z_-]{35}'                                # Google API key
    PATTERN="$PATTERN"'|sk-ant-[a-zA-Z0-9_-]{20,}'                            # Anthropic
    PATTERN="$PATTERN"'|sk-proj-[a-zA-Z0-9_-]{20,}'                           # OpenAI project
    PATTERN="$PATTERN"'|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'  # JWT (3-part)
    PATTERN="$PATTERN"'|-----BEGIN ((RSA|EC|DSA|OPENSSH|PGP) )?PRIVATE KEY-----'
    PATTERN="$PATTERN"'|(api[_-]?key|secret|token|password)[[:space:]]*[:=][[:space:]]*["'\''\`][^"'\''\`]{8,}["'\''\`]'
    # S1_LINE_EXEMPT 동기화: pre_commit_check.py S1_LINE_EXEMPT와 동일 면제 목록 유지
    EXEMPT_RE='^\.claude/(scripts|agents|rules|skills|memory)/'
    EXEMPT_RE="$EXEMPT_RE"'|^docs/(WIP|incidents|decisions|guides|harness)/'
    EXEMPT_RE="$EXEMPT_RE"'|^scripts/install-secret-scan-hook\.sh$'
    EXEMPT_RE="$EXEMPT_RE"'|^[^/]+\.md$'
    HITS=$(echo "$STAGED" | while IFS= read -r f; do
      [ -z "$f" ] && continue
      if echo "$f" | grep -qE "$EXEMPT_RE"; then continue; fi
      git diff --cached -- "$f" 2>/dev/null
    done | grep -En "$PATTERN" || true)
    if [ -n "$HITS" ]; then
      echo ""
      echo "🚫 시크릿 패턴 발견 (grep 폴백). 커밋 차단."
      echo "$HITS" | head -20
      echo ""
      echo "   주의: grep은 리터럴 분할·Base64 우회를 탐지하지 못한다."
      echo "   더 정확한 검사: gitleaks 설치 (https://github.com/gitleaks/gitleaks)"
      exit 1
    fi
  fi
fi
# <<< secret-scan (managed) <<<
HOOK_EOF
)

mkdir -p "$REPO_ROOT/.git/hooks"

if [ ! -f "$HOOK_FILE" ]; then
  cat > "$HOOK_FILE" <<EOF
#!/usr/bin/env bash
set -euo pipefail

$SCAN_BLOCK
EOF
  chmod +x "$HOOK_FILE"
  echo "✅ pre-commit hook 신규 설치 완료: $HOOK_FILE"

  # HARNESS.json hook_installed 플래그 갱신 (있으면)
  HARNESS_JSON="$REPO_ROOT/.claude/HARNESS.json"
  if [ -f "$HARNESS_JSON" ]; then
    python3 - "$HARNESS_JSON" <<'PY'
import json, sys
p = sys.argv[1]
with open(p, encoding="utf-8") as f:
    d = json.load(f)
if d.get("hook_installed") is not True:
    d["hook_installed"] = True
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"✅ {p} hook_installed=true 갱신")
PY
  fi

  exit 0
fi

if grep -qF "$MARKER_START" "$HOOK_FILE"; then
  echo "ℹ️  secret-scan 섹션이 이미 존재합니다. 건너뜀."
  exit 0
fi

{
  echo ""
  echo "$SCAN_BLOCK"
} >> "$HOOK_FILE"

chmod +x "$HOOK_FILE"
echo "✅ 기존 pre-commit hook에 secret-scan 섹션 추가 완료."
echo "   확인: cat $HOOK_FILE"

# HARNESS.json hook_installed 플래그 갱신 (있으면)
HARNESS_JSON="$REPO_ROOT/.claude/HARNESS.json"
if [ -f "$HARNESS_JSON" ]; then
  python3 - "$HARNESS_JSON" <<'PY'
import json, sys
p = sys.argv[1]
with open(p, encoding="utf-8") as f:
    d = json.load(f)
if d.get("hook_installed") is not True:
    d["hook_installed"] = True
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"✅ {p} hook_installed=true 갱신")
PY
fi
