#!/usr/bin/env bash
# Kiro SessionStart — auto-inject existing bundle as context (zero-friction)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

# Resolve splice CLI
SPLICE_CMD=""
if command -v splice &>/dev/null; then
  SPLICE_CMD="splice"
elif python3 -m splice_cli.cli --version &>/dev/null 2>&1; then
  SPLICE_CMD="python3 -m splice_cli.cli"
elif [[ -f "$ROOT/scripts/splice-cli.py" ]]; then
  SPLICE_CMD="python3 $ROOT/scripts/splice-cli.py"
else
  exit 0
fi

# Init/resume session silently
$SPLICE_CMD init --assistant kiro >/dev/null 2>&1 || true

# If a bundle exists (from a previous session, another IDE, or another machine via git),
# inject it into the agent context automatically
if [[ -f .splice/active-bundle.md ]]; then
  BUNDLE=$(cat .splice/active-bundle.md)
  echo "[Splice] Loaded existing context bundle from .splice/active-bundle.md"
  echo ""
  echo "$BUNDLE"
fi

exit 0
