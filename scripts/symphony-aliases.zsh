#!/usr/bin/env zsh
# Fifth-Symphony Script Aliases
# Add to your ~/.zshrc: source ~/git/internal/repos/fifth-symphony/scripts/symphony-aliases.zsh

# Path to fifth-symphony scripts
export FIFTH_SYMPHONY_SCRIPTS="$HOME/git/internal/repos/fifth-symphony/scripts"
export FIFTH_SYMPHONY_ROOT="$HOME/git/internal/repos/fifth-symphony"

# sasuga - Run favorite scripts from scripts/favorites/
# Usage: sasuga launch_agent_monitor.py
sasuga() {
    local script_name="$1"
    local favorites_dir="$FIFTH_SYMPHONY_SCRIPTS/favorites"

    if [[ -z "$script_name" ]]; then
        echo "Usage: sasuga <script_name>"
        echo ""
        echo "Available favorite scripts:"
        if [[ -d "$favorites_dir" ]]; then
            ls -1 "$favorites_dir"/*.py 2>/dev/null | xargs -n1 basename
        else
            echo "  (none - directory not found)"
        fi
        return 1
    fi

    local script_path="$favorites_dir/$script_name"

    if [[ ! -f "$script_path" ]]; then
        echo "❌ Script not found: $script_name"
        echo ""
        echo "Available favorite scripts:"
        ls -1 "$favorites_dir"/*.py 2>/dev/null | xargs -n1 basename
        return 1
    fi

    # Run with uv if in fifth-symphony, otherwise system python
    if [[ -f "$FIFTH_SYMPHONY_ROOT/pyproject.toml" ]]; then
        cd "$FIFTH_SYMPHONY_ROOT" && uv run python "$script_path" "$@[2,-1]"
    else
        python3 "$script_path" "$@[2,-1]"
    fi
}

# pyscript - Run any script from scripts/ directory (supports subdirectories)
# Usage: pyscript user-scripts/quick_test.py
pyscript() {
    local script_path="$1"

    if [[ -z "$script_path" ]]; then
        echo "Usage: pyscript <script_path>"
        echo ""
        echo "Examples:"
        echo "  pyscript launch_agent_monitor.py"
        echo "  pyscript user-scripts/quick_test.py"
        echo "  pyscript subdirectory/some_script.py"
        echo ""
        echo "Available scripts:"
        echo ""
        if [[ -d "$FIFTH_SYMPHONY_SCRIPTS" ]]; then
            # Show directory structure
            tree -L 2 -P "*.py" --prune "$FIFTH_SYMPHONY_SCRIPTS" 2>/dev/null || \
            find "$FIFTH_SYMPHONY_SCRIPTS" -name "*.py" -type f | sed "s|$FIFTH_SYMPHONY_SCRIPTS/||" | sort
        fi
        return 1
    fi

    local full_path="$FIFTH_SYMPHONY_SCRIPTS/$script_path"

    if [[ ! -f "$full_path" ]]; then
        echo "❌ Script not found: $script_path"
        echo ""
        echo "Looking in: $FIFTH_SYMPHONY_SCRIPTS"
        echo ""
        echo "Did you mean one of these?"
        find "$FIFTH_SYMPHONY_SCRIPTS" -name "*.py" -type f | grep -i "$(basename $script_path)" | sed "s|$FIFTH_SYMPHONY_SCRIPTS/||" | head -5
        return 1
    fi

    # Run with uv if in fifth-symphony, otherwise system python
    if [[ -f "$FIFTH_SYMPHONY_ROOT/pyproject.toml" ]]; then
        cd "$FIFTH_SYMPHONY_ROOT" && uv run python "$full_path" "$@[2,-1]"
    else
        python3 "$full_path" "$@[2,-1]"
    fi
}

# Tab completion for sasuga (favorite scripts)
_sasuga_completion() {
    local favorites_dir="$HOME/git/internal/repos/fifth-symphony/scripts/favorites"
    if [[ -d "$favorites_dir" ]]; then
        _files -W "$favorites_dir" -g "*.py"
    fi
}

# Tab completion for pyscript (all scripts)
_pyscript_completion() {
    local scripts_dir="$HOME/git/internal/repos/fifth-symphony/scripts"
    if [[ -d "$scripts_dir" ]]; then
        _files -W "$scripts_dir" -g "*.py"
    fi
}

# Register completions
compdef _sasuga_completion sasuga
compdef _pyscript_completion pyscript

# Helper: List all favorite scripts
sasuga-list() {
    local favorites_dir="$FIFTH_SYMPHONY_SCRIPTS/favorites"
    echo "📚 Favorite Scripts (use 'sasuga <name>'):"
    echo ""
    if [[ -d "$favorites_dir" ]]; then
        for script in "$favorites_dir"/*.py; do
            if [[ -f "$script" ]]; then
                local name=$(basename "$script")
                local first_line=$(head -n3 "$script" | grep -E '^"""' -A1 | tail -n1 | sed 's/"""//')
                printf "  %-30s %s\n" "$name" "$first_line"
            fi
        done
    else
        echo "  (none found)"
    fi
}

# Helper: List all scripts
pyscript-list() {
    echo "📚 All Scripts (use 'pyscript <path>'):"
    echo ""
    if [[ -d "$FIFTH_SYMPHONY_SCRIPTS" ]]; then
        tree -L 3 -P "*.py" --prune "$FIFTH_SYMPHONY_SCRIPTS" 2>/dev/null || \
        find "$FIFTH_SYMPHONY_SCRIPTS" -name "*.py" -type f | sed "s|$FIFTH_SYMPHONY_SCRIPTS/||" | sort
    fi
}

# Silent loading - output interferes with Powerlevel10k instant prompt
# To see available commands, run: sasuga-list or pyscript-list
