#!/bin/bash
# pre-commit 검사 래퍼 — 로직은 pre_commit_check.py가 담당.
# Python 재작성으로 Windows Git Bash fork 오버헤드 제거 (1,414ms → ~160ms).
exec python3 "$(dirname "$0")/pre_commit_check.py" "$@"
