#!/usr/bin/env bash
# Deprecated: use install-splice.sh instead
# This script is kept for backward compatibility
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$SCRIPT_DIR/install-splice.sh" "$@"
