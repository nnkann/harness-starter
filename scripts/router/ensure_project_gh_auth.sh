#!/usr/bin/env bash
set -euo pipefail

# Ensure GitHub auth works from Hermes/Harness non-interactive workers.
# This avoids macOS Keychain prompts/errors such as:
#   fatal: could not read Username for 'https://github.com': Device not configured

PROJECT_ROOT="${PROJECT_ROOT:-$(git rev-parse --show-toplevel)}"
GH_CONFIG_DIR="${GH_CONFIG_DIR:-$PROJECT_ROOT/.config/gh}"
CENTRAL_GH_HOSTS="${CENTRAL_GH_HOSTS:-/Users/kann/projects/.auth/gh/default/hosts.yml}"
GH_BIN="${GH_BIN:-$(command -v gh)}"
BRANCH="${1:-$(git -C "$PROJECT_ROOT" branch --show-current)}"

export PROJECT_ROOT GH_CONFIG_DIR GH_PROMPT_DISABLED=1 GIT_TERMINAL_PROMPT=0

if [[ -z "$GH_BIN" || ! -x "$GH_BIN" ]]; then
  echo "BLOCKED: gh CLI not found" >&2
  exit 1
fi

mkdir -p "$GH_CONFIG_DIR"

if [[ ! -e "$GH_CONFIG_DIR/hosts.yml" ]]; then
  if [[ -f "$CENTRAL_GH_HOSTS" ]]; then
    ln -s "$CENTRAL_GH_HOSTS" "$GH_CONFIG_DIR/hosts.yml"
  else
    echo "BLOCKED: project-local gh hosts.yml missing: $GH_CONFIG_DIR/hosts.yml" >&2
    echo "Also missing central hosts.yml: $CENTRAL_GH_HOSTS" >&2
    exit 1
  fi
fi

# Keep the credential symlink/config out of commits even if a worker creates it.
if ! grep -qxF '.config/gh/' "$PROJECT_ROOT/.git/info/exclude" 2>/dev/null; then
  {
    echo ''
    echo '# project-local gh credential symlink (managed outside git)'
    echo '.config/gh/'
  } >> "$PROJECT_ROOT/.git/info/exclude"
fi

# Force this repo to use gh's credential helper with the project-local GH_CONFIG_DIR.
# The helper is repo-local and does not depend on macOS Keychain being available to the worker.
git -C "$PROJECT_ROOT" config --local --unset-all credential.helper || true
git -C "$PROJECT_ROOT" config --local --unset-all credential.https://github.com.helper || true
git -C "$PROJECT_ROOT" config --local credential.https://github.com.helper ""
git -C "$PROJECT_ROOT" config --local --add credential.https://github.com.helper \
  "!GH_CONFIG_DIR=$GH_CONFIG_DIR $GH_BIN auth git-credential"

"$GH_BIN" auth status >/dev/null
printf 'protocol=https\nhost=github.com\n\n' \
  | git -C "$PROJECT_ROOT" credential fill \
  | grep -q '^password='

git -C "$PROJECT_ROOT" push --dry-run origin "$BRANCH" >/dev/null

echo "OK: GitHub auth ready for $PROJECT_ROOT on branch $BRANCH"
echo "GH_CONFIG_DIR=$GH_CONFIG_DIR"
echo "hosts.yml=$(readlink "$GH_CONFIG_DIR/hosts.yml" 2>/dev/null || printf '%s' "$GH_CONFIG_DIR/hosts.yml")"
