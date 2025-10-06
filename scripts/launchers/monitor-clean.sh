#!/bin/bash
# Fifth Symphony - Clean Visual Monitor
# Simple, beautiful TUI showing your 5 most recent projects

cd "$(dirname "$0")"

echo "🎭 Starting Clean Visual Monitor..."
echo ""
echo "✨ Features:"
echo "   📊 Shows 5 most recent projects"
echo "   🎨 Clean, card-based layout"
echo "   📈 Real-time event tracking"
echo "   ⌨️  Simple keybindings"
echo ""

uv run python examples/claude_monitor_clean.py
