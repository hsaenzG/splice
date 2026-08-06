#!/usr/bin/env bash
# Shared orchestration hook — used by Kiro (stdout → prompt) and Cursor (writes bundle file)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

ASSISTANT="${SPLICE_ASSISTANT:-kiro}"
INPUT="$(cat)"

python3 scripts/splice-cli.py orchestrate \
  --assistant "$ASSISTANT" \
  --format compact <<< "$INPUT"
