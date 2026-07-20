#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHON=${PYTHON:-python3.11}

if ! "$PYTHON" -c 'import sys; raise SystemExit(sys.version_info[:2] != (3, 11))'; then
  echo "h-setup.sh requires Python 3.11" >&2
  exit 2
fi

PYTHONPATH="$SCRIPT_DIR/runtime${PYTHONPATH:+:$PYTHONPATH}" \
  exec "$PYTHON" -m harness_runtime.binding_cli "$@"