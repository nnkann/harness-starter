#!/bin/bash
# pre-commit 검사 래퍼 — 로직은 pre_commit_check.py가 담당.
# Python 재작성으로 Windows Git Bash fork 오버헤드 제거 (1,414ms → ~160ms).
# 필수: Python 3.8 이상 (python3 명령이 PATH에 있어야 함)
if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ python3를 찾을 수 없습니다." >&2
  echo "   pre-commit-check는 Python 3.8 이상이 필요합니다." >&2
  echo "   설치: https://python.org/downloads" >&2
  echo "   Windows Git Bash: ~/.bashrc에 'alias python3=python' 추가" >&2
  exit 2
fi
exec python3 "$(dirname "$0")/pre_commit_check.py" "$@"
