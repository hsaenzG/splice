#!/usr/bin/env bash
# Claude Code SessionStart — auto-inject existing bundle as context (zero-friction)
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
$SPLICE_CMD init --assistant claude >/dev/null 2>&1 || true

# If a bundle exists, inject it so Claude has full context from any prior IDE session
BUNDLE=""
if [[ -f .splice/active-bundle.md ]]; then
  BUNDLE=$(cat .splice/active-bundle.md)
fi

python3 -c "
import json, sys
bundle = sys.stdin.read()
if not bundle.strip():
    bundle = '(No bundle yet — Splice will track context as you work.)'
ctx = '''You are working with Splice (meta-tooling layer above Kiro, Cursor, and Claude Code).
Context is tracked automatically across IDEs. The bundle below contains the latest orchestrated context from this project — it may come from another IDE or another machine.
Do not re-paste errors or files already in the bundle. Follow recommendedAgent and workflow from the bundle.

Current bundle:
''' + bundle
print(json.dumps({
  'hookSpecificOutput': {
    'hookEventName': 'SessionStart',
    'additionalContext': ctx
  }
}))
" <<< "\$BUNDLE"
