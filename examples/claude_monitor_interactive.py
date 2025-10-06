#!/usr/bin/env python3
"""
Fifth Symphony - Interactive Claude Code Monitor

Textual-based interactive TUI with:
- Multiple Claude Code instance monitors
- Chat windows for each instance
- Ollama LLM integration
- tmux-like window management
- Customizable keybindings

Keybindings:
- Ctrl+N: New monitor panel
- Ctrl+C: Chat with selected instance
- Ctrl+O: Open Ollama chat
- Ctrl+Q: Quit
- Tab: Switch between panels
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Header, Footer, Static, Input, Button,
    Label, ListView, ListItem, RichLog, TabbedContent, TabPane
)
from textual.binding import Binding
from textual.reactive import reactive
from textual.message import Message

from rich.text import Text
from rich.panel import Panel
from datetime import datetime
from collections import deque

from modules.claude_code_monitor import ClaudeCodeMonitor, ClaudeEvent, ClaudeEventType


class ActivityLog(RichLog):
    """Widget for displaying Claude Code activity."""

    def __init__(self, project_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project_name = project_name
        self.border_title = f"🎯 {project_name}"
        self.can_focus = True

    def add_event(self, icon: str, message: str, style: str = ""):
        """Add an event to the activity log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        text = Text()
        text.append(f"[{timestamp}] ", style="dim")
        text.append(f"{icon} ", style=style)
        text.append(message, style=style)
        self.write(text)


class ChatWindow(VerticalScroll):
    """Chat window for interacting with Claude instances or Ollama."""

    def __init__(self, title: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.border_title = title
        self.messages = []

    def add_message(self, sender: str, message: str, style: str = ""):
        """Add a message to the chat."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        text = Text()
        text.append(f"[{timestamp}] ", style="dim")
        text.append(f"{sender}: ", style=f"bold {style}")
        text.append(message)

        label = Label(text)
        self.mount(label)
        self.messages.append((sender, message, timestamp))


class ProjectMonitorPanel(Container):
    """Panel for monitoring a single Claude Code project with chat integration."""

    def __init__(self, project_name: str, session_dir: Path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project_name = project_name
        self.session_dir = session_dir
        self.monitor = ClaudeCodeMonitor()

        self.stats = {
            "user_prompts": 0,
            "files_read": 0,
            "files_written": 0,
            "files_edited": 0,
            "bash_commands": 0,
        }

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with TabbedContent(initial="activity"):
            with TabPane("Activity", id="activity"):
                yield ActivityLog(
                    self.project_name,
                    id=f"log_{self.project_name}",
                    max_lines=100
                )

            with TabPane("Chat", id="chat"):
                yield ChatWindow(
                    f"💬 Chat: {self.project_name}",
                    id=f"chat_{self.project_name}"
                )

            with TabPane("Stats", id="stats"):
                yield Static(
                    self._render_stats(),
                    id=f"stats_{self.project_name}"
                )

    def on_mount(self) -> None:
        """Start monitoring when mounted."""
        self._register_callbacks()
        self.monitor.start_monitoring(self.session_dir, self.project_name)
        self._log_event("🟢", "Monitoring started", "green")

    def _register_callbacks(self):
        """Register event callbacks."""
        self.monitor.add_callback(ClaudeEventType.USER_PROMPT, self._on_user_prompt)
        self.monitor.add_callback(ClaudeEventType.FILE_READ, self._on_file_read)
        self.monitor.add_callback(ClaudeEventType.FILE_WRITE, self._on_file_write)
        self.monitor.add_callback(ClaudeEventType.FILE_EDIT, self._on_file_edit)
        self.monitor.add_callback(ClaudeEventType.BASH_COMMAND, self._on_bash_command)
        self.monitor.add_callback(ClaudeEventType.ASSISTANT_RESPONSE, self._on_assistant_response)

    def _log_event(self, icon: str, message: str, style: str = ""):
        """Log event to activity log."""
        log = self.query_one(f"#log_{self.project_name}", ActivityLog)
        log.add_event(icon, message, style)

    def _on_user_prompt(self, event: ClaudeEvent):
        self.stats["user_prompts"] += 1
        self._log_event("🟣", f"User: {event.summary[:50]}", "magenta")
        self._update_stats()

    def _on_file_read(self, event: ClaudeEvent):
        self.stats["files_read"] += 1
        self._log_event("📖", f"Read: {event.summary[:50]}", "cyan")
        self._update_stats()

    def _on_file_write(self, event: ClaudeEvent):
        self.stats["files_written"] += 1
        self._log_event("✍️", f"Write: {event.summary[:50]}", "green")
        self._update_stats()

    def _on_file_edit(self, event: ClaudeEvent):
        self.stats["files_edited"] += 1
        self._log_event("✏️", f"Edit: {event.summary[:50]}", "yellow")
        self._update_stats()

    def _on_bash_command(self, event: ClaudeEvent):
        self.stats["bash_commands"] += 1
        self._log_event("⚡", f"Bash: {event.summary[:50]}", "yellow")
        self._update_stats()

    def _on_assistant_response(self, event: ClaudeEvent):
        self._log_event("🔵", "Claude responding...", "blue")

    def _render_stats(self) -> str:
        """Render statistics as text."""
        total = sum(self.stats.values())
        return f"""
📊 Statistics

🟣 User Prompts:    {self.stats['user_prompts']}
📖 Files Read:      {self.stats['files_read']}
✍️  Files Written:   {self.stats['files_written']}
✏️  Files Edited:    {self.stats['files_edited']}
⚡ Bash Commands:   {self.stats['bash_commands']}

📊 Total Events:    {total}
"""

    def _update_stats(self):
        """Update statistics display."""
        stats_widget = self.query_one(f"#stats_{self.project_name}", Static)
        stats_widget.update(self._render_stats())


class OllamaChatPanel(Container):
    """Panel for chatting with Ollama LLM."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conversation_history = []

    def compose(self) -> ComposeResult:
        """Create chat interface."""
        yield Label("🤖 Ollama LLM Chat", classes="title")
        yield ChatWindow("Ollama Assistant", id="ollama_chat")

        with Horizontal(classes="input-row"):
            yield Input(placeholder="Type your message...", id="ollama_input")
            yield Button("Send", id="ollama_send", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle send button."""
        if event.button.id == "ollama_send":
            self._send_message()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input."""
        if event.input.id == "ollama_input":
            self._send_message()

    def _send_message(self):
        """Send message to Ollama."""
        input_widget = self.query_one("#ollama_input", Input)
        message = input_widget.value.strip()

        if not message:
            return

        # Add user message to chat
        chat = self.query_one("#ollama_chat", ChatWindow)
        chat.add_message("You", message, "cyan")

        # Clear input
        input_widget.value = ""

        # TODO: Integrate with Ollama SDK
        # For now, echo back
        chat.add_message("Ollama", f"[Demo] You said: {message}", "green")

        # Store in history
        self.conversation_history.append(("user", message))
        self.conversation_history.append(("assistant", f"Echo: {message}"))


class ClaudeMonitorApp(App):
    """Interactive Claude Code monitor with chat integration."""

    CSS = """
    Screen {
        background: $surface;
    }

    .title {
        background: $primary;
        color: $text;
        padding: 1;
        text-align: center;
        text-style: bold;
    }

    ActivityLog {
        border: solid $primary;
        height: 100%;
    }

    ChatWindow {
        border: solid $accent;
        height: 100%;
        padding: 1;
    }

    .input-row {
        dock: bottom;
        height: 3;
        padding: 0 1;
    }

    Input {
        width: 80%;
    }

    Button {
        width: 20%;
    }

    TabbedContent {
        height: 100%;
    }

    TabPane {
        padding: 1;
    }

    Static {
        padding: 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+o", "toggle_ollama", "Ollama Chat"),
        Binding("ctrl+d", "toggle_dark", "Toggle Dark Mode"),
        ("ctrl+c", "copy", "Copy"),
    ]

    TITLE = "🎭 Fifth Symphony - Interactive Claude Monitor"
    SUB_TITLE = "Multi-Project Monitoring with LLM Chat"

    show_ollama = reactive(False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.projects = []

    def compose(self) -> ComposeResult:
        """Create app layout."""
        yield Header()

        with Horizontal(id="main_container"):
            # Left side: Claude Code monitors
            with Vertical(id="monitors_container", classes="panel"):
                yield Label("📊 Claude Code Projects", classes="title")

                # Discover and create project monitors
                self._discover_projects()

            # Right side: Ollama chat (toggleable)
            if self.show_ollama:
                yield OllamaChatPanel(id="ollama_panel", classes="panel")

        yield Footer()

    def _discover_projects(self):
        """Discover Claude Code projects and create monitors."""
        claude_projects_dir = Path.home() / ".claude" / "projects"

        if not claude_projects_dir.exists():
            return

        for session_dir in claude_projects_dir.iterdir():
            if session_dir.is_dir() and not session_dir.name.startswith('.'):
                # Check for .jsonl files
                jsonl_files = list(session_dir.glob("*.jsonl"))
                if jsonl_files:
                    # Extract project name
                    parts = session_dir.name.split('-')
                    project_name = parts[-1] if len(parts) > 3 else session_dir.name

                    # Create monitor panel
                    panel = ProjectMonitorPanel(project_name, session_dir)
                    self.projects.append(panel)

    def on_mount(self) -> None:
        """Mount discovered projects."""
        container = self.query_one("#monitors_container")

        if not self.projects:
            container.mount(Label("No Claude Code projects found", classes="dim"))
        else:
            for project in self.projects:
                container.mount(project)

    def action_toggle_ollama(self) -> None:
        """Toggle Ollama chat panel."""
        self.show_ollama = not self.show_ollama
        self.refresh(layout=True)

    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.dark = not self.dark


def main():
    """Run the interactive monitor."""
    app = ClaudeMonitorApp()
    app.run()


if __name__ == "__main__":
    main()
