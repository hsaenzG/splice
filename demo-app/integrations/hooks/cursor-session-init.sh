#!/usr/bin/env bash
# Cursor sessionStart — init shared session and inject Splice instructions
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

splice init --assistant cursor >/dev/null 2>&1 || true

splice orchestrate \
  --assistant cursor \
  --prompt "Session start — index demo-app bug context" \
  --always \
  --format markdown >/dev/null 2>&1 || true

BUNDLE=""
if [[ -f .splice/active-bundle.md ]]; then
  BUNDLE=$(cat .splice/active-bundle.md)
fi

python3 -c "
import json, sys
bundle = sys.stdin.read()
print(json.dumps({
  'additional_context': '''You are working with Splice (meta-tooling layer).

When the user includes /harness or @harness in a prompt, orchestration runs automatically.
Always read .splice/active-bundle.md at the start of each turn if it exists — it contains the reduced context bundle.

Demo bug: demo-app/UserList.tsx crashes because API returns { items: [] } not a raw array.

Session bundle:
''' + bundle
}))
" <<< "$BUNDLE"
