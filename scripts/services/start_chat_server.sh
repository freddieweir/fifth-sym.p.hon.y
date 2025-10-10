#!/bin/bash
# Start Fifth Symphony Multi-Agent Chat Server

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🎵 Starting Fifth Symphony Chat Server..."
echo "   Server will run on ws://localhost:8765"
echo "   Press Ctrl+C to stop"
echo ""

# Run chat server
uv run python -m modules.chat.chat_server
