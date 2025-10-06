#!/usr/bin/env python3
"""
Fifth Symphony - Ultimate Interactive Claude Monitor

Textual-based TUI with full features:
- Auto-discover and monitor all Claude Code projects
- Individual chat windows per project
- Ollama LLM integration for AI assistance
- tmux-like window management
- Tabbed interface per project
- Real-time activity monitoring

Keybindings:
- Ctrl+O: Toggle Ollama chat
- Ctrl+D: Toggle dark mode
- Ctrl+Q: Quit
- Tab: Switch between panels
- Ctrl+T: Switch between tabs within panels
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    RichLog,
    Static,
    TabbedContent,
    TabPane,
)

try:
    import ollama

    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

from modules.claude_code_monitor import ClaudeCodeMonitor, ClaudeEvent, ClaudeEventType


class ActivityLog(RichLog):
    """Activity log widget for Claude Code events."""

    def add_event(self, icon: str, message: str, style: str = ""):
        """Add timestamped event."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        text = Text()
        text.append(f"[{timestamp}] ", style="dim")
        text.append(f"{icon} ", style=style)
        text.append(message, style=style)
        self.write(text)


class ChatMessages(VerticalScroll):
    """Scrollable chat message container."""

    pass


class ProjectMonitor(Container):
    """Monitor widget for a single Claude Code project."""

    def __init__(self, project_name: str, session_dir: Path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project_name = project_name
        self.session_dir = session_dir
        self.monitor = ClaudeCodeMonitor()

        # Sanitize project name for widget IDs (replace / and spaces)
        self.safe_id = project_name.replace("/", "-").replace(" ", "_")

        self.stats = {
            "user_prompts": 0,
            "files_read": 0,
            "files_written": 0,
            "files_edited": 0,
            "bash_commands": 0,
            "web_fetches": 0,
        }

    def compose(self) -> ComposeResult:
        """Create project monitor interface."""
        with TabbedContent(initial="activity"):
            # Activity tab
            with TabPane("📋 Activity", id="activity"):
                yield ActivityLog(max_lines=200, highlight=True, markup=True)

            # Chat tab
            with TabPane("💬 Chat", id="chat"):
                yield ChatMessages(id=f"chat_messages_{self.safe_id}")
                with Horizontal(classes="chat-input-row"):
                    yield Input(
                        placeholder="Chat with this Claude instance...",
                        id=f"chat_input_{self.safe_id}",
                    )
                    yield Button("Send", id=f"chat_send_{self.safe_id}", variant="primary")

            # Stats tab
            with TabPane("📊 Stats", id="stats"):
                yield Static(self._render_stats(), id=f"stats_{self.safe_id}")

    def on_mount(self) -> None:
        """Start monitoring on mount."""
        self._register_callbacks()
        self.monitor.start_monitoring(self.session_dir, self.project_name)

        # Log startup
        activity_log = self.query_one(ActivityLog)
        activity_log.add_event("🟢", f"Monitoring {self.project_name}", "green")

    def _register_callbacks(self):
        """Register Claude Code event callbacks."""
        self.monitor.add_callback(ClaudeEventType.USER_PROMPT, self._on_user_prompt)
        self.monitor.add_callback(ClaudeEventType.FILE_READ, self._on_file_read)
        self.monitor.add_callback(ClaudeEventType.FILE_WRITE, self._on_file_write)
        self.monitor.add_callback(ClaudeEventType.FILE_EDIT, self._on_file_edit)
        self.monitor.add_callback(ClaudeEventType.BASH_COMMAND, self._on_bash_command)
        self.monitor.add_callback(ClaudeEventType.WEB_FETCH, self._on_web_fetch)
        self.monitor.add_callback(ClaudeEventType.ASSISTANT_RESPONSE, self._on_assistant_response)

    def _log_event(self, icon: str, message: str, style: str = ""):
        """Add event to activity log."""
        try:
            activity_log = self.query_one(ActivityLog)
            activity_log.add_event(icon, message, style)
        except Exception:
            pass  # Widget may not be mounted yet

    def _on_user_prompt(self, event: ClaudeEvent):
        self.stats["user_prompts"] += 1
        self._log_event("🟣", f"User: {event.summary[:60]}", "magenta")
        self._update_stats()

    def _on_file_read(self, event: ClaudeEvent):
        self.stats["files_read"] += 1
        self._log_event("📖", f"Read: {event.summary[:60]}", "cyan")
        self._update_stats()

    def _on_file_write(self, event: ClaudeEvent):
        self.stats["files_written"] += 1
        self._log_event("✍️", f"Write: {event.summary[:60]}", "green")
        self._update_stats()

    def _on_file_edit(self, event: ClaudeEvent):
        self.stats["files_edited"] += 1
        self._log_event("✏️", f"Edit: {event.summary[:60]}", "yellow")
        self._update_stats()

    def _on_bash_command(self, event: ClaudeEvent):
        self.stats["bash_commands"] += 1
        self._log_event("⚡", f"Bash: {event.summary[:60]}", "yellow")
        self._update_stats()

    def _on_web_fetch(self, event: ClaudeEvent):
        self.stats["web_fetches"] += 1
        self._log_event("🌐", f"Web: {event.summary[:60]}", "blue")
        self._update_stats()

    def _on_assistant_response(self, event: ClaudeEvent):
        self._log_event("🔵", "Claude responding...", "blue")

    def _render_stats(self) -> str:
        """Render statistics display."""
        total = sum(self.stats.values())
        return f"""
## 📊 Project Statistics

**{self.project_name}**

- 🟣 **User Prompts**: {self.stats["user_prompts"]}
- 📖 **Files Read**: {self.stats["files_read"]}
- ✍️ **Files Written**: {self.stats["files_written"]}
- ✏️ **Files Edited**: {self.stats["files_edited"]}
- ⚡ **Bash Commands**: {self.stats["bash_commands"]}
- 🌐 **Web Fetches**: {self.stats["web_fetches"]}

---

**Total Events**: {total}
"""

    def _update_stats(self):
        """Update stats display."""
        try:
            stats_widget = self.query_one(f"#stats_{self.safe_id}", Static)
            stats_widget.update(self._render_stats())
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle chat send button."""
        if event.button.id == f"chat_send_{self.safe_id}":
            self._send_chat_message()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter in chat input."""
        if event.input.id == f"chat_input_{self.safe_id}":
            self._send_chat_message()

    def _send_chat_message(self):
        """Send message in project chat."""
        input_widget = self.query_one(f"#chat_input_{self.safe_id}", Input)
        message = input_widget.value.strip()

        if not message:
            return

        # Add to chat
        chat_container = self.query_one(f"#chat_messages_{self.safe_id}", ChatMessages)

        timestamp = datetime.now().strftime("%H:%M:%S")
        user_msg = Static(f"[{timestamp}] [bold cyan]You:[/] {message}")
        chat_container.mount(user_msg)

        # Clear input
        input_widget.value = ""

        # TODO: Send to Claude Code instance (would need API)
        response_msg = Static(
            f"[{timestamp}] [dim]Note: Direct chat with Claude Code not yet implemented.[/]"
        )
        chat_container.mount(response_msg)


class OllamaChat(Container):
    """Ollama LLM chat interface."""

    def compose(self) -> ComposeResult:
        """Create Ollama chat UI."""
        yield Label("🤖 Ollama Assistant", classes="panel-title")

        if not OLLAMA_AVAILABLE:
            yield Static(
                "[bold red]Ollama not available[/]\nInstall with: uv add ollama", classes="error"
            )
            return

        yield ChatMessages(id="ollama_messages")

        with Horizontal(classes="chat-input-row"):
            yield Input(placeholder="Ask Ollama anything...", id="ollama_input")
            yield Button("Send", id="ollama_send", variant="primary")

    def on_mount(self) -> None:
        """Initialize Ollama chat."""
        if OLLAMA_AVAILABLE:
            chat = self.query_one("#ollama_messages", ChatMessages)
            welcome = Static(
                "[dim]💡 Ollama chat ready! Ask questions about your monitored projects.[/]"
            )
            chat.mount(welcome)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle send button."""
        if event.button.id == "ollama_send":
            self._send_to_ollama()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key."""
        if event.input.id == "ollama_input":
            self._send_to_ollama()

    def _send_to_ollama(self):
        """Send message to Ollama."""
        if not OLLAMA_AVAILABLE:
            return

        input_widget = self.query_one("#ollama_input", Input)
        message = input_widget.value.strip()

        if not message:
            return

        # Add user message
        chat = self.query_one("#ollama_messages", ChatMessages)
        timestamp = datetime.now().strftime("%H:%M:%S")

        user_msg = Static(f"[{timestamp}] [bold cyan]You:[/] {message}")
        chat.mount(user_msg)

        # Clear input
        input_widget.value = ""

        # Add thinking indicator
        thinking = Static(f"[{timestamp}] [bold green]Ollama:[/] [dim italic]Thinking...[/]")
        chat.mount(thinking)

        # Call Ollama in background using run_worker
        self.run_worker(self._query_ollama(message, thinking), exclusive=True)

    async def _query_ollama(self, message: str, thinking_widget: Static):
        """Query Ollama asynchronously."""
        try:
            # Call Ollama
            response = await asyncio.to_thread(
                ollama.chat,
                model="llama3.2",  # Adjust model as needed
                messages=[{"role": "user", "content": message}],
            )

            # Remove thinking indicator
            thinking_widget.remove()

            # Add response
            chat = self.query_one("#ollama_messages", ChatMessages)
            timestamp = datetime.now().strftime("%H:%M:%S")

            response_text = response["message"]["content"]
            response_msg = Static(f"[{timestamp}] [bold green]Ollama:[/] {response_text}")
            chat.mount(response_msg)

        except Exception as e:
            thinking_widget.update(f"[bold red]Error:[/] {str(e)}")


class ClaudeMonitorUltimate(App):
    """Ultimate Claude Code monitor with chat and LLM integration."""

    CSS = """
    Screen {
        background: $surface;
    }

    .panel-title {
        dock: top;
        background: $primary;
        color: $text;
        padding: 1;
        text-align: center;
        text-style: bold;
    }

    .chat-input-row {
        dock: bottom;
        height: 3;
        padding: 0 1;
    }

    .chat-input-row Input {
        width: 4fr;
    }

    .chat-input-row Button {
        width: 1fr;
    }

    ProjectMonitor {
        height: auto;
        border: tall $primary;
        margin: 1 2;
        padding: 0;
        background: $panel;
    }

    ActivityLog {
        border: none;
        height: 100%;
        padding: 1 2;
        background: $surface;
    }

    ChatMessages {
        height: 1fr;
        padding: 1 2;
        border: none;
        background: $surface;
    }

    Static {
        padding: 1 2;
    }

    .error {
        color: $error;
        padding: 2;
    }

    TabbedContent {
        height: 100%;
        background: $surface;
    }

    TabPane {
        padding: 0;
    }

    #monitors_container {
        width: 3fr;
        border-right: solid $primary;
        padding: 0;
    }

    #ollama_container {
        width: 1fr;
        border: tall $accent;
        margin: 1;
        background: $panel;
    }

    Label {
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+o", "toggle_ollama", "Toggle Ollama"),
        Binding("ctrl+d", "toggle_dark", "Dark Mode"),
    ]

    TITLE = "🎭 Fifth Symphony - Ultimate Claude Monitor"
    SUB_TITLE = "Multi-Project + LLM Chat"

    show_ollama = reactive(False)

    def compose(self) -> ComposeResult:
        """Create main layout."""
        yield Header(show_clock=True)

        with Horizontal(id="main_layout"):
            # Left: Project monitors
            with Vertical(id="monitors_container"):
                yield Label("📊 Claude Code Projects", classes="panel-title")

                # Auto-discover projects
                projects = self._discover_projects()

                if not projects:
                    yield Static(
                        "\n[dim]No Claude Code projects found.\n\n"
                        "Use Claude Code in a project to create session files.[/]",
                        classes="error",
                    )
                else:
                    for project_name, session_dir in projects:
                        yield ProjectMonitor(project_name, session_dir)

            # Right: Ollama chat (toggleable)
            if self.show_ollama:
                with Vertical(id="ollama_container"):
                    yield OllamaChat()

        yield Footer()

    def _discover_projects(self, max_projects: int = 5):
        """Discover Claude Code projects (limited to most recent)."""
        claude_dir = Path.home() / ".claude" / "projects"

        if not claude_dir.exists():
            return []

        projects = []
        for session_dir in claude_dir.iterdir():
            if session_dir.is_dir() and not session_dir.name.startswith("."):
                # Check for .jsonl files
                jsonl_files = list(session_dir.glob("*.jsonl"))
                if jsonl_files:
                    # Get most recent modification time
                    most_recent = max(f.stat().st_mtime for f in jsonl_files)

                    # Extract project name (get last 2 parts for better names)
                    parts = session_dir.name.split("-")
                    if len(parts) > 4:
                        # Take last 2 parts: repos/fifth-symphony
                        project_name = f"{parts[-2]}/{parts[-1]}"
                    elif len(parts) > 2:
                        project_name = parts[-1]
                    else:
                        project_name = session_dir.name

                    projects.append((project_name, session_dir, most_recent))

        # Sort by modification time (most recent first) and limit
        projects.sort(key=lambda x: x[2], reverse=True)
        return [(name, path) for name, path, _ in projects[:max_projects]]

    def action_toggle_ollama(self) -> None:
        """Toggle Ollama chat panel."""
        self.show_ollama = not self.show_ollama
        self.refresh(recompose=True)

    def action_toggle_dark(self) -> None:
        """Toggle dark/light mode."""
        self.dark = not self.dark


def main():
    """Run the ultimate monitor."""
    app = ClaudeMonitorUltimate()
    app.run()


if __name__ == "__main__":
    main()
