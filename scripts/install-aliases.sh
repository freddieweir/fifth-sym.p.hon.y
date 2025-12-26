#!/usr/bin/env bash
# Install Fifth-Symphony aliases to your shell

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ALIASES_FILE="$SCRIPT_DIR/symphony-aliases.zsh"
ZSHRC="$HOME/.zshrc"

echo "🎭 Installing Fifth-Symphony Aliases..."
echo ""

# Check if zsh is the shell
if [[ "$SHELL" != *"zsh"* ]]; then
    echo "⚠️  Warning: Current shell is not zsh ($SHELL)"
    echo "These aliases are designed for zsh."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if already installed
if grep -q "symphony-aliases.zsh" "$ZSHRC" 2>/dev/null; then
    echo "✓ Aliases already installed in $ZSHRC"
    echo ""
    echo "To reload:"
    echo "  source ~/.zshrc"
    exit 0
fi

# Add to .zshrc
echo "" >> "$ZSHRC"
echo "# Fifth-Symphony Script Aliases" >> "$ZSHRC"
echo "source $ALIASES_FILE" >> "$ZSHRC"

echo "✅ Aliases installed to $ZSHRC"
echo ""
echo "Available commands:"
echo "  sasuga <script>         - Run favorite scripts"
echo "  pyscript <path>         - Run any script from scripts/"
echo "  sasuga-list             - List favorite scripts"
echo "  pyscript-list           - List all scripts"
echo ""
echo "To activate now:"
echo "  source ~/.zshrc"
echo ""
echo "Examples:"
echo "  sasuga launch_agent_monitor.py"
echo "  pyscript user-scripts/quick_test.py"
