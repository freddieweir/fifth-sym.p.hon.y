#!/bin/bash
# Python Orchestrator Startup Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Python Orchestrator${NC}"
echo "====================="

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: uv is not installed${NC}"
    echo "Install with: pip install uv"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo -e "${RED}Error: main.py not found${NC}"
    echo "Please run this script from the orchestrator directory"
    exit 1
fi

# Install dependencies if needed
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    uv sync
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
elif op whoami &> /dev/null && op item get "Eleven Labs API" &> /dev/null; then
    echo -e "${GREEN}✓ ElevenLabs API key found in 1Password${NC}"
else
    echo -e "${YELLOW}⚠ ElevenLabs API key not found (optional)${NC}"
    echo "  Voice features will be disabled"
    echo "  Set ELEVENLABS_API_KEY or add 'Eleven Labs API' to 1Password"
fi

echo
echo -e "${BLUE}Starting Python Orchestrator...${NC}"

# Check if chat server is running (optional)
if nc -z localhost 8765 2>/dev/null; then
    echo -e "${GREEN}✓ Chat server detected on localhost:8765${NC}"
    echo -e "${YELLOW}  Tip: Use --with-chat to enable multi-agent chat${NC}"
else
    echo -e "${YELLOW}⚠ Chat server not running (optional)${NC}"
    echo "  Start with: ./start_chat_server.sh"
fi

echo

# Run the orchestrator with any passed arguments
uv run python main.py "$@"