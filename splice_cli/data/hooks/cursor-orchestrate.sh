#!/usr/bin/env bash
# Cursor beforeSubmitPrompt — refresh bundle when user invokes /harness
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

INPUT="$(cat)"

splice orchestrate \
  --assistant cursor \
  --hook-mode \
  --format markdown <<< "$INPUT"
