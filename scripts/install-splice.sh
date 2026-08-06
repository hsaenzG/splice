#!/usr/bin/env bash
# Install Splice into any git project (Kiro + Cursor + Claude Code)
set -euo pipefail

SOURCE="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="$(cd "${1:-.}" && pwd)"

echo "Installing Splice into: $TARGET"

copy_tree() {
  local src="$1" dst="$2"
  mkdir -p "$dst"
  cp -R "$src/." "$dst/"
}

# Core runtime
copy_tree "$SOURCE/src/shared" "$TARGET/src/shared"
mkdir -p "$TARGET/scripts"
cp "$SOURCE/scripts/splice-cli.py" "$TARGET/scripts/splice-cli.py"
chmod +x "$TARGET/scripts/splice-cli.py"

copy_tree "$SOURCE/integrations/hooks" "$TARGET/integrations/hooks"
chmod +x "$TARGET/integrations/hooks/"*.sh

# Config
mkdir -p "$TARGET/.splice"
if [[ ! -f "$TARGET/.splice/config.json" ]]; then
  cp "$SOURCE/integrations/templates/config.json.example" "$TARGET/.splice/config.json"
  echo "  Created .splice/config.json"
fi

# Cursor
mkdir -p "$TARGET/.cursor/rules"
if [[ ! -f "$TARGET/.cursor/rules/splice.mdc" ]]; then
  cp "$SOURCE/integrations/templates/cursor-rules-splice.mdc" "$TARGET/.cursor/rules/splice.mdc"
  echo "  Created .cursor/rules/splice.mdc"
fi
if [[ ! -f "$TARGET/.cursor/hooks.json" ]]; then
  cp "$SOURCE/integrations/templates/cursor-hooks.json" "$TARGET/.cursor/hooks.json"
  echo "  Created .cursor/hooks.json"
else
  echo "  NOTE: .cursor/hooks.json already exists — merge sessionStart/beforeSubmitPrompt manually"
fi

# Claude Code
mkdir -p "$TARGET/.claude"
if [[ ! -f "$TARGET/.claude/settings.json" ]]; then
  cp "$SOURCE/integrations/templates/claude-settings.json" "$TARGET/.claude/settings.json"
  echo "  Created .claude/settings.json"
else
  echo "  NOTE: .claude/settings.json already exists — merge SessionStart/UserPromptSubmit hooks manually"
fi
if [[ ! -f "$TARGET/.claude/CLAUDE.md" ]]; then
  cp "$SOURCE/integrations/templates/claude-claude.md" "$TARGET/.claude/CLAUDE.md"
  echo "  Created .claude/CLAUDE.md"
fi

# Kiro
mkdir -p "$TARGET/.kiro/hooks" "$TARGET/.kiro/steering"
if [[ ! -f "$TARGET/.kiro/hooks/splice.json" ]]; then
  cp "$SOURCE/integrations/templates/kiro-hooks-splice.json" "$TARGET/.kiro/hooks/splice.json"
  echo "  Created .kiro/hooks/splice.json"
fi
if [[ ! -f "$TARGET/.kiro/steering/splice.md" ]]; then
  cp "$SOURCE/integrations/templates/kiro-steering-splice.md" "$TARGET/.kiro/steering/splice.md"
  echo "  Created .kiro/steering/splice.md"
fi

# gitignore snippet
GITIGNORE="$TARGET/.gitignore"
MARKER="# splice"
if [[ -f "$GITIGNORE" ]] && ! grep -q "$MARKER" "$GITIGNORE" 2>/dev/null; then
  cat >> "$GITIGNORE" <<'EOF'

# splice
.splice/session.json
.splice/active-bundle.md
.splice/last-error.log
EOF
  echo "  Updated .gitignore"
elif [[ ! -f "$GITIGNORE" ]]; then
  cat > "$GITIGNORE" <<'EOF'
# splice
.splice/session.json
.splice/active-bundle.md
.splice/last-error.log
EOF
  echo "  Created .gitignore"
fi

echo ""
echo "Done. Next steps:"
echo "  1. Edit $TARGET/.splice/config.json for your project"
echo "  2. Restart Kiro, Cursor, and/or Claude Code"
echo "  3. In any assistant: /harness <your task>"
echo ""
echo "Optional: pipe errors before /harness"
echo "  npm test 2>&1 | python3 scripts/splice-cli.py capture-error"
