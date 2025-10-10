#!/bin/bash
# Fifth Symphony - Claude Code Terminal Monitor Launcher
# Simple script to launch the terminal-only monitor

cd "$(dirname "$0")"

echo "🎭 Starting Claude Code Terminal Monitor..."
echo ""

uv run python examples/claude_monitor_terminal.py
