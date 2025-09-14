#!/bin/bash
# Neural Orchestra - Quick Lint Script
# Usage: ./lint.sh [fix|check|all]

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

run_ruff_check() {
    print_header "Running Ruff (Linter)"
    if uv run ruff check . --statistics; then
        echo -e "${GREEN}✓ Ruff linting passed${NC}"
    else
        echo -e "${RED}✗ Ruff found issues${NC}"
        return 1
    fi
}

run_ruff_fix() {
    print_header "Running Ruff (Auto-fix)"
    uv run ruff check . --fix --unsafe-fixes
    uv run ruff format .
    echo -e "${GREEN}✓ Ruff auto-fixes applied${NC}"
}

run_pylint() {
    print_header "Running Pylint"
    if uv run pylint main.py modules/*.py scripts/*.py gui*.py --output-format=colorized --reports=n; then
        echo -e "${GREEN}✓ Pylint passed${NC}"
    else
        echo -e "${YELLOW}⚠ Pylint found issues (check score above)${NC}"
    fi
}

run_tests() {
    print_header "Running Tests"
    if uv run pytest -v; then
        echo -e "${GREEN}✓ All tests passed${NC}"
    else
        echo -e "${RED}✗ Some tests failed${NC}"
        return 1
    fi
}

case "${1:-check}" in
    "fix")
        print_header "Auto-fixing code issues"
        run_ruff_fix
        run_ruff_check
        run_pylint
        ;;
    "check")
        print_header "Checking code quality"
        run_ruff_check
        run_pylint
        ;;
    "test")
        run_tests
        ;;
    "all")
        print_header "Complete code quality check"
        run_ruff_fix
        run_ruff_check
        run_pylint
        run_tests
        ;;
    *)
        echo "Usage: $0 [fix|check|test|all]"
        echo "  fix   - Auto-fix issues and check"
        echo "  check - Check code quality (default)"
        echo "  test  - Run tests only"
        echo "  all   - Fix, check, and test everything"
        exit 1
        ;;
esac

echo -e "${GREEN}Done!${NC}"