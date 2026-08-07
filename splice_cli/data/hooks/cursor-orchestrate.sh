#!/usr/bin/env bash
# Cursor UserPromptSubmit — silently accumulates context on EVERY prompt.
# When /harness is used, also refreshes the bundle file for the rule to read.
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
  echo '{"continue": true}'
  exit 0
fi

INPUT="$(cat)"

# Always accumulate context silently
$SPLICE_CMD orchestrate \
  --assistant cursor \
  --hook-mode \
  --always \
  --format markdown <<< "$INPUT" > /dev/null 2>&1 || true

# Cursor hook always returns continue
echo '{"continue": true}'
