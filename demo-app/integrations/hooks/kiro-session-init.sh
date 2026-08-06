#!/usr/bin/env bash
# Kiro SessionStart — init session silently (no JSON dumped into agent context)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
python3 "$ROOT/scripts/splice-cli.py" init --assistant kiro >/dev/null 2>&1 || true
exit 0
