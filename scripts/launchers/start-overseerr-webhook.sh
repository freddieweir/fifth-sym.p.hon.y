#!/bin/bash
#
# Overseerr Webhook Listener Launcher
#
# Starts the FastAPI webhook listener for Overseerr audio notifications.
# This service receives webhook events from Overseerr and writes text files
# to the audio monitor directory for automatic voice synthesis and playback.
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo -e "${GREEN}[Overseerr Webhook Listener]${NC}"
echo "Project root: $PROJECT_ROOT"
echo ""

# Change to project root
cd "$PROJECT_ROOT" || exit 1

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: uv package manager not found${NC}"
    echo "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check if audio output directory exists
AUDIO_DIR="/Users/fweir/git/ai-bedo/communications/audio"
if [ ! -d "$AUDIO_DIR" ]; then
    echo -e "${YELLOW}Warning: Audio output directory does not exist: $AUDIO_DIR${NC}"
    echo "Creating directory..."
    mkdir -p "$AUDIO_DIR"
fi

# Check if FastAPI dependencies are installed
echo "Checking dependencies..."
if ! uv run python -c "import fastapi, uvicorn" &> /dev/null; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    uv sync
fi

echo ""
echo -e "${GREEN}Starting Overseerr webhook listener...${NC}"
echo "Endpoint: http://0.0.0.0:8765/webhook/overseerr"
echo "Test endpoint: http://0.0.0.0:8765/webhook/test"
echo "Health check: http://0.0.0.0:8765/health"
echo ""
echo "Audio output directory: $AUDIO_DIR"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

# Run the webhook listener
exec uv run python -m modules.overseerr_webhook
