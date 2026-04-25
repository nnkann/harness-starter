#!/bin/bash
# docs-ops 래퍼 — 로직은 docs_ops.py가 담당.
if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ python3를 찾을 수 없습니다. Python 3.8 이상 필요." >&2
  exit 1
fi
exec python3 "$(dirname "$0")/docs_ops.py" "$@"
