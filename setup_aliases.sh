#!/bin/bash
# Neural Orchestra - Setup Development Aliases
# Run this script to add development aliases to your shell

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detect shell
if [[ -n "$ZSH_VERSION" ]]; then
    SHELL_RC="$HOME/.zshrc"
elif [[ -n "$BASH_VERSION" ]]; then
    SHELL_RC="$HOME/.bashrc"
else
    echo "Unsupported shell. Please add aliases manually."
    exit 1
fi

# Aliases to add
ALIASES="
# Neural Orchestra Development Aliases
alias no-lint='cd \"$SCRIPT_DIR\" && ./lint.sh check'
alias no-fix='cd \"$SCRIPT_DIR\" && ./lint.sh fix'
alias no-test='cd \"$SCRIPT_DIR\" && ./lint.sh test'
alias no-all='cd \"$SCRIPT_DIR\" && ./lint.sh all'
alias no-run='cd \"$SCRIPT_DIR\" && ./run.sh'
alias no-gui='cd \"$SCRIPT_DIR\" && ./run_gui.sh'
alias no-sync='cd \"$SCRIPT_DIR\" && uv sync'
alias no-cd='cd \"$SCRIPT_DIR\"'
"

echo "Adding Neural Orchestra aliases to $SHELL_RC..."

# Check if aliases already exist
if grep -q "Neural Orchestra Development Aliases" "$SHELL_RC" 2>/dev/null; then
    echo "Aliases already exist in $SHELL_RC"
else
    echo "$ALIASES" >> "$SHELL_RC"
    echo "Aliases added to $SHELL_RC"
fi

echo ""
echo "Available aliases:"
echo "  no-lint  - Check code quality"
echo "  no-fix   - Auto-fix and check code"
echo "  no-test  - Run tests"
echo "  no-all   - Fix, check, and test everything"
echo "  no-run   - Run CLI interface"
echo "  no-gui   - Run GUI interface"  
echo "  no-sync  - Sync dependencies"
echo "  no-cd    - Navigate to project directory"
echo ""
echo "Restart your terminal or run: source $SHELL_RC"