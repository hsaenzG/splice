#!/usr/bin/env bash
# Kiro UserPromptSubmit hook — fast, non-blocking
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

export GIT_PAGER=cat
export SPLICE_ASSISTANT=kiro

# Kiro sends JSON on stdin; read with 3s cap (portable on macOS — no GNU timeout required)
INPUT="$(python3 -c "
import select, sys
ready, _, _ = select.select([sys.stdin], [], [], 3)
print(sys.stdin.read() if ready else '', end='')
" 2>/dev/null || true)"

if [[ -z "$INPUT" ]]; then
  INPUT='{"prompt":"/harness"}'
fi

splice orchestrate \
  --assistant kiro \
  --format compact \
  --hook-mode \
  --fresh <<< "$INPUT"
