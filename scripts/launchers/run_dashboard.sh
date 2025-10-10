#!/bin/bash
# Fifth Symphony Multi-Pane Dashboard Launcher

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${MAGENTA}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}║  🎵 Fifth Symphony Multi-Pane Dashboard              ║${NC}"
echo -e "${MAGENTA}╚════════════════════════════════════════════════════════╝${NC}"
echo

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: uv is not installed${NC}"
    echo "Install with: pip install uv"
    exit 1
fi

# Install dependencies if needed
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    uv sync
fi

# Check if chat server is running
if nc -z localhost 8765 2>/dev/null; then
    echo -e "${GREEN}✓ Chat server detected on localhost:8765${NC}"
else
    echo -e "${YELLOW}⚠ Chat server not running${NC}"
    echo -e "  ${BLUE}Start in another terminal:${NC} ./start_chat_server.sh"
    echo
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo
echo -e "${BLUE}Dashboard Layout:${NC}"
echo "  📱 Left:   Live chat feed (color-coded agents)"
echo "  📁 Top Right:    Project directory tree"
echo "  🧠 Middle Right: Ollama model output"
echo "  📊 Bottom:       Status & logs"
echo
echo -e "${BLUE}Keyboard Shortcuts:${NC}"
echo "  Ctrl+C - Quit dashboard"
echo "  Ctrl+S - Send chat message"
echo "  Ctrl+R - Refresh directory tree"
echo
echo -e "${GREEN}Starting dashboard...${NC}"
echo

# Run dashboard
uv run python dashboard.py
