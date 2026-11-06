#!/usr/bin/env bash
# Install the Claude Code session toolkit into ~/.claude.
#
#   ./install.sh          install script + slash commands into ~/.claude
#   ./install.sh --shell  also install the shell integration and hook it into ~/.zshrc
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"

mkdir -p "$CLAUDE_DIR/scripts" "$CLAUDE_DIR/commands"
cp "$HERE/scripts/sessions.py" "$CLAUDE_DIR/scripts/sessions.py"
chmod +x "$CLAUDE_DIR/scripts/sessions.py"
cp "$HERE"/commands/*.md "$CLAUDE_DIR/commands/"

echo "Installed:"
echo "  $CLAUDE_DIR/scripts/sessions.py"
echo "  $CLAUDE_DIR/commands/*.md"

if [ "${1:-}" = "--shell" ]; then
  mkdir -p "$CLAUDE_DIR/shell"
  cp "$HERE/shell/claude.zsh" "$CLAUDE_DIR/shell/claude.zsh"
  ZRC="$HOME/.zshrc"
  line='source "$HOME/.claude/shell/claude.zsh"'
  touch "$ZRC"
  if grep -qF 'shell/claude.zsh' "$ZRC"; then
    echo "Shell hook already present in $ZRC"
  else
    printf '\n# Claude Code session toolkit\n%s\n' "$line" >> "$ZRC"
    echo "Added shell hook to $ZRC (run: source ~/.zshrc, or open a new terminal)"
  fi
fi

echo
echo "In Claude Code: /sessions  /clean-sessions  /delete-session  /handoff"
echo "On the CLI:     claude-manager   (or: ccs list)"
