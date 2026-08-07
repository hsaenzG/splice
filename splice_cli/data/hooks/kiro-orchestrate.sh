#!/usr/bin/env bash
# Kiro UserPromptSubmit — silently accumulates context on EVERY prompt.
# When /harness is used, also outputs the bundle to the agent.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

export GIT_PAGER=cat
export SPLICE_ASSISTANT=kiro

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

# Read stdin from Kiro (JSON with prompt)
INPUT="$(python3 -c "
import select, sys
ready, _, _ = select.select([sys.stdin], [], [], 3)
print(sys.stdin.read() if ready else '', end='')
" 2>/dev/null || true)"

if [[ -z "$INPUT" ]]; then
  exit 0
fi

# Extract prompt to check if user explicitly wants bundle output
PROMPT=$(python3 -c "
import json, sys
try:
    data = json.loads(sys.argv[1])
    print(data.get('prompt', ''))
except:
    print(sys.argv[1])
" "$INPUT" 2>/dev/null || echo "")

PROMPT_LOWER=$(echo "$PROMPT" | tr '[:upper:]' '[:lower:]')

# Always accumulate context silently (tracking happens in background)
$SPLICE_CMD orchestrate \
  --assistant kiro \
  --format compact \
  --hook-mode \
  --fresh <<< "$INPUT" > /dev/null 2>&1 || true

# Only output bundle to agent when user explicitly triggers /harness
if [[ "$PROMPT_LOWER" == *"/harness"* ]] || [[ "$PROMPT_LOWER" == *"@harness"* ]]; then
  if [[ -f .splice/active-bundle.md ]]; then
    cat .splice/active-bundle.md
  fi
fi

exit 0
