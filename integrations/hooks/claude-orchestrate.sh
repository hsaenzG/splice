#!/usr/bin/env bash
# Claude Code UserPromptSubmit — inject orchestrated context when user invokes /harness
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

export GIT_PAGER=cat
export SPLICE_ASSISTANT=claude

INPUT="$(python3 -c "
import select, sys
ready, _, _ = select.select([sys.stdin], [], [], 3)
print(sys.stdin.read() if ready else '', end='')
" 2>/dev/null || true)"

if [[ -z "$INPUT" ]]; then
  exit 0
fi

# Fast path: hook runs on every prompt — skip orchestration unless triggered
if ! python3 -c "
import json, sys
raw = sys.argv[1]
try:
    data = json.loads(raw) if raw.strip() else {}
except json.JSONDecodeError:
    data = {}
prompt = (data.get('prompt') or '').lower()
sys.exit(0 if any(t in prompt for t in ('/harness', '@harness', 'splice')) else 1)
" "$INPUT"; then
  exit 0
fi

python3 "$ROOT/scripts/splice-cli.py" orchestrate \
  --assistant claude \
  --format claude \
  --hook-mode \
  --fresh <<< "$INPUT"
