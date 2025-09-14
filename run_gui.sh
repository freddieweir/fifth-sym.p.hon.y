#!/bin/bash
# Python Orchestrator GUI Launcher

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}🎛️  Python Orchestrator GUI${NC}"
echo "============================"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: uv is not installed${NC}"
    echo "Install with: pip install uv"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "gui.py" ]; then
    echo -e "${RED}Error: gui.py not found${NC}"
    echo "Please run this script from the orchestrator directory"
    exit 1
fi

# Install/update dependencies if needed
echo -e "${YELLOW}📦 Updating dependencies...${NC}"
uv sync

# System checks
echo -e "${BLUE}🔍 System Checks${NC}"

# Check for PySide6
if uv run python -c "import PySide6" 2>/dev/null; then
    echo -e "${GREEN}✓ PySide6 GUI framework ready${NC}"
else
    echo -e "${RED}✗ PySide6 not available${NC}"
    exit 1
fi

# Check for dark theme  
if uv run python -c "import qdarktheme" 2>/dev/null; then
    echo -e "${GREEN}✓ Dark theme support ready${NC}"
else
    echo -e "${YELLOW}⚠ Dark theme not available (optional)${NC}"
fi

# Check for 1Password CLI (optional)
if command -v op &> /dev/null; then
    echo -e "${GREEN}✓ 1Password CLI found${NC}"
    if op whoami &> /dev/null; then
        echo -e "${GREEN}✓ 1Password session active${NC}"
    else
        echo -e "${YELLOW}⚠ 1Password not signed in (optional)${NC}"
        echo "  Run 'op signin' to enable secure credential management"
    fi
else
    echo -e "${YELLOW}⚠ 1Password CLI not found (optional)${NC}"
    echo "  Install with: brew install --cask 1password-cli"
fi

# Check for ElevenLabs API key (optional)
if [ -n "$ELEVENLABS_API_KEY" ]; then
    echo -e "${GREEN}✓ ElevenLabs API key found in environment${NC}"
elif op whoami &> /dev/null && op item get "Eleven Labs API" &> /dev/null 2>&1; then
    echo -e "${GREEN}✓ ElevenLabs API key found in 1Password${NC}"
else
    echo -e "${YELLOW}⚠ ElevenLabs API key not found (optional)${NC}"
    echo "  Voice features will be disabled"
    echo "  Set ELEVENLABS_API_KEY or add 'Eleven Labs API' to 1Password"
fi

echo
echo -e "${CYAN}🚀 Launching Python Orchestrator GUI...${NC}"
echo

# Launch the GUI with any passed arguments
uv run python gui.py "$@"