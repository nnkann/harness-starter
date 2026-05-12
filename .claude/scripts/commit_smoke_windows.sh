#!/bin/bash
# commit_smoke_windows.sh — Windows + Git Bash 환경에서 커밋 파이프라인 사전 검증.
#
# §H-6 (v0.44.4~). 매 commit 전에 강제 실행하지 않는다 — 사용자가 명시
# 호출하거나 다운스트림 환경 셋업 직후 1회 진단 용도.
#
# 4축 검사:
#   1. CRLF — .claude/scripts/*.sh shebang에 CR 있는지
#   2. Hook shebang — .git/hooks/pre-commit shebang CRLF
#   3. Git identity — user.name·user.email 설정 여부
#   4. PowerShell→Git Bash env 전달 패턴 — 사용자가 PowerShell에서 `VAR=1 cmd`
#      형태로 호출했는지 (이건 호출자 측 검사 불가, 안내만)
#
# 출력:
#   - 통과 시: stdout 1줄 "smoke_pass: 4/4"
#   - 실패 시: stderr에 실패한 검사 + 다음 행동 안내
#
# 종료 코드:
#   0 통과
#   1 1개 이상 실패

set -e

pass=0
fail=()

# 1. CRLF — .claude/scripts/*.sh shebang
for f in .claude/scripts/*.sh; do
  [ -f "$f" ] || continue
  if head -1 "$f" 2>/dev/null | tr -d '\n' | grep -q $'\r'; then
    fail+=("CRLF shebang: $f → 정규화: sed -i 's/\\r\$//' $f")
  fi
done
if [ ${#fail[@]} -eq 0 ]; then
  pass=$((pass + 1))
fi

# 2. Hook shebang CRLF
crlf_hook_fail_before=${#fail[@]}
if [ -f .git/hooks/pre-commit ]; then
  if head -1 .git/hooks/pre-commit 2>/dev/null | tr -d '\n' | grep -q $'\r'; then
    fail+=("CRLF shebang: .git/hooks/pre-commit → 'sed -i s/\\r\$// .git/hooks/pre-commit'")
  fi
fi
if [ ${#fail[@]} -eq $crlf_hook_fail_before ]; then
  pass=$((pass + 1))
fi

# 3. Git identity
identity_fail_before=${#fail[@]}
name=$(git config user.name 2>/dev/null || echo "")
email=$(git config user.email 2>/dev/null || echo "")
if [ -z "$name" ] || [ -z "$email" ]; then
  fail+=("Git identity 미설정 → 'git config user.name <name>; git config user.email <email>'")
fi
if [ ${#fail[@]} -eq $identity_fail_before ]; then
  pass=$((pass + 1))
fi

# 4. PowerShell→Git Bash env 전달 안내 (검사 불가, 정보 표시)
# Windows + Git Bash 환경에서만 의미 있음. uname -s가 MINGW* / CYGWIN*면 Windows.
uname_s=$(uname -s 2>/dev/null || echo "unknown")
case "$uname_s" in
  MINGW*|CYGWIN*|MSYS*)
    echo "ℹ️  Windows + Git Bash 환경 감지. PowerShell에서 호출 시:" >&2
    echo "    \$env:HARNESS_DEV='1'; bash .claude/scripts/commit_smoke_windows.sh" >&2
    echo "    (Bash 문법 'HARNESS_DEV=1 bash ...'는 PowerShell이 인식 못함)" >&2
    ;;
esac
pass=$((pass + 1))  # 4번은 검사 불가, 정보 표시만 → 항상 통과로 카운트

if [ ${#fail[@]} -eq 0 ]; then
  echo "smoke_pass: $pass/4"
  exit 0
else
  echo "smoke_fail: $((4 - ${#fail[@]}))/4" >&2
  for msg in "${fail[@]}"; do
    echo "  ❌ $msg" >&2
  done
  exit 1
fi
