#!/bin/bash
# Fifth Symphony - Interactive Monitor Launcher
# Textual TUI with chat windows and Ollama LLM integration

cd "$(dirname "$0")"

echo "🎭 Starting Interactive Claude Monitor..."
echo ""
echo "✨ Features:"
echo "   📊 Auto-detects all Claude Code projects"
echo "   💬 Chat windows per project"
echo "   🤖 Ollama LLM integration (Ctrl+O)"
echo "   ⌨️  tmux-style keybindings"
echo ""
echo "⌨️  Keybindings:"
echo "   Ctrl+O - Toggle Ollama chat"
echo "   Ctrl+D - Toggle dark mode"
echo "   Ctrl+Q - Quit"
echo "   Tab    - Navigate between widgets"
echo ""

# Check if Ollama is running
if ! pgrep -x "ollama" > /dev/null; then
    echo "⚠️  Ollama not detected. LLM chat will be disabled."
    echo "   To enable: Run 'ollama serve' in another terminal"
    echo ""
fi

uv run python examples/claude_monitor_ultimate.py
