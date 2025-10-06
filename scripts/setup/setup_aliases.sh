#!/bin/bash
# Fifth Symphony - Setup Development Aliases
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
# Fifth Symphony Development Aliases
alias fs-lint='cd \"$SCRIPT_DIR\" && ./lint.sh check'
alias fs-fix='cd \"$SCRIPT_DIR\" && ./lint.sh fix'
alias fs-test='cd \"$SCRIPT_DIR\" && ./lint.sh test'
alias fs-all='cd \"$SCRIPT_DIR\" && ./lint.sh all'
alias fs-run='cd \"$SCRIPT_DIR\" && ./run.sh'
alias fs-gui='cd \"$SCRIPT_DIR\" && ./run_gui.sh'
alias fs-sync='cd \"$SCRIPT_DIR\" && uv sync'
alias fs-cd='cd \"$SCRIPT_DIR\"'
"

echo "Adding Fifth Symphony aliases to $SHELL_RC..."

# Check if aliases already exist
if grep -q "Fifth Symphony Development Aliases" "$SHELL_RC" 2>/dev/null; then
    echo "Aliases already exist in $SHELL_RC"
else
    echo "$ALIASES" >> "$SHELL_RC"
    echo "Aliases added to $SHELL_RC"
fi

echo ""
echo "Available aliases:"
echo "  fs-lint  - Check code quality"
echo "  fs-fix   - Auto-fix and check code"
echo "  fs-test  - Run tests"
echo "  fs-all   - Fix, check, and test everything"
echo "  fs-run   - Run CLI interface"
echo "  fs-gui   - Run GUI interface"
echo "  fs-sync  - Sync dependencies"
echo "  fs-cd    - Navigate to project directory"
echo ""
echo "Restart your terminal or run: source $SHELL_RC"