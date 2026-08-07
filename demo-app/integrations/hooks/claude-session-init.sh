#!/usr/bin/env bash
# Claude Code SessionStart — init shared session and inject Splice instructions
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

splice init --assistant claude >/dev/null 2>&1 || true

BUNDLE=""
if [[ -f .splice/active-bundle.md ]]; then
  BUNDLE=$(cat .splice/active-bundle.md)
fi

python3 -c "
import json, sys
bundle = sys.stdin.read()
ctx = '''You are working with Splice (meta-tooling layer above Kiro, Cursor, and Claude Code).

When the user includes /harness or @harness in a prompt, orchestration runs automatically via hooks.
Always read .splice/active-bundle.md if it exists — it contains the reduced, prioritized context bundle.
Do not re-paste errors or files already in the bundle. Follow recommendedAgent and workflow from the bundle.

If assistantsUsed includes another IDE (kiro, cursor), continue the task using the bundle — do not re-triage.

Current bundle:
''' + (bundle or '(none yet — user can run /harness to populate)')
print(json.dumps({
  'hookSpecificOutput': {
    'hookEventName': 'SessionStart',
    'additionalContext': ctx
  }
}))
" <<< "$BUNDLE"
