#!/bin/bash
# Start Fifth Symphony Chat Client

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Default username
USERNAME="${1:-User}"

echo "🎵 Starting Fifth Symphony Chat Client..."
echo "   Connecting to ws://localhost:8765"
echo "   Username: $USERNAME"
echo ""
echo "Available usernames:"
echo "  - User (👤 Cyan)"
echo "  - Fifth-Symphony (🎵 Magenta)"
echo "  - Nazarick-Agent (🎭 Blue)"
echo "  - Code-Assistant (🤖 Green)"
echo "  - VM-Claude (🖥️ Yellow)"
echo ""
echo "Commands:"
echo "  /quit, /exit, /q - Disconnect"
echo ""

# Run chat client
uv run python -m modules.chat.chat_client --username "$USERNAME"
