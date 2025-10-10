#!/bin/bash
# Fifth Symphony - Multi-Project Claude Code Monitor Launcher
# Auto-detects and monitors all Claude Code projects simultaneously

cd "$(dirname "$0")"

echo "🎭 Starting Multi-Project Claude Code Monitor..."
echo ""

uv run python examples/claude_monitor_multi.py
