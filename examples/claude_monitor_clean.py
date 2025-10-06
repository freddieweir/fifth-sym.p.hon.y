#!/usr/bin/env python3
"""
Fifth Symphony - Clean Visual Claude Monitor

Beautiful, simple TUI focusing on the 5 most recent projects.
Less clutter, more visual appeal.

Keybindings:
- Ctrl+O: Toggle Ollama chat
- Ctrl+D: Toggle dark mode
- Ctrl+Q: Quit
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Static, Input, Button, RichLog, TabbedContent, TabPane
from textual.binding import Binding
from textual.reactive import reactive

from rich.text import Text

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

from modules.claude_code_monitor import ClaudeCodeMonitor, ClaudeEvent, ClaudeEventType


class ProjectCard(Container):
    """Attractive card for a single project."""

    def __init__(self, project_name: str, session_dir: Path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project_name = project_name
        self.session_dir = session_dir
        self.monitor = ClaudeCodeMonitor()
        self.event_count = 0

    def compose(self) -> ComposeResult:
        """Create card layout."""
        # Project header
        yield Static(f"🎯 {self.project_name}", classes="project-name")

        # Activity log (sanitize ID - replace / with -)
        self.safe_id = self.project_name.replace("/", "-").replace(" ", "_")
        yield RichLog(max_lines=10, highlight=True, markup=True, id=f"log_{self.safe_id}")

        # Event counter
        yield Static("0 events", id=f"counter_{self.safe_id}", classes="event-counter")

    def on_mount(self) -> None:
        """Start monitoring."""
        self._register_callbacks()
        self.monitor.start_monitoring(self.session_dir, self.project_name)

        log = self.query_one(f"#log_{self.safe_id}", RichLog)
        log.write(Text("🟢 Monitoring started", style="green"))

    def _register_callbacks(self):
        """Register callbacks."""
        self.monitor.add_callback(ClaudeEventType.USER_PROMPT, self._on_event("🟣", "User", "magenta"))
        self.monitor.add_callback(ClaudeEventType.FILE_READ, self._on_event("📖", "Read", "cyan"))
        self.monitor.add_callback(ClaudeEventType.FILE_WRITE, self._on_event("✍️", "Write", "green"))
        self.monitor.add_callback(ClaudeEventType.FILE_EDIT, self._on_event("✏️", "Edit", "yellow"))
        self.monitor.add_callback(ClaudeEventType.BASH_COMMAND, self._on_event("⚡", "Bash", "yellow"))
        self.monitor.add_callback(ClaudeEventType.ASSISTANT_RESPONSE, self._on_event("🔵", "Claude", "blue"))

    def _on_event(self, icon: str, label: str, style: str):
        """Create event handler."""
        def handler(event: ClaudeEvent):
            self.event_count += 1

            log = self.query_one(f"#log_{self.safe_id}", RichLog)
            timestamp = datetime.now().strftime("%H:%M:%S")

            text = Text()
            text.append(f"[{timestamp}] ", style="dim")
            text.append(f"{icon} ", style=style)
            text.append(f"{label}: ", style=f"bold {style}")
            text.append(event.summary[:40], style=style)

            log.write(text)

            # Update counter
            counter = self.query_one(f"#counter_{self.safe_id}", Static)
            counter.update(f"{self.event_count} events")

        return handler


class CleanMonitor(App):
    """Clean, visual Claude Code monitor."""

    CSS = """
    Screen {
        background: $surface;
    }

    Header {
        background: $primary;
    }

    ProjectCard {
        height: 12;
        border: tall $accent;
        margin: 0 2;
        padding: 1;
        background: $panel;
    }

    .project-name {
        dock: top;
        text-align: center;
        text-style: bold;
        color: $accent;
        padding-bottom: 1;
    }

    .event-counter {
        dock: bottom;
        text-align: center;
        color: $success;
        padding-top: 0;
    }

    RichLog {
        background: $surface;
        border: none;
        height: 1fr;
    }

    #projects {
        width: 1fr;
        padding: 0;
    }

    #welcome {
        height: auto;
        border: double $primary;
        margin: 1 4;
        padding: 2;
        background: $boost;
    }
    """

    TITLE = "🎭 Fifth Symphony - Claude Monitor"
    SUB_TITLE = "Visual Dashboard"

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+d", "toggle_dark", "Dark Mode"),
    ]

    def compose(self) -> ComposeResult:
        """Create layout."""
        yield Header(show_clock=True)

        with Vertical(id="projects"):
            # Welcome message
            yield Static(
                """[bold cyan]📊 Monitoring Your Most Recent Claude Code Projects[/bold cyan]

[dim]Showing activity from the 5 most recently active projects.
Events update in real-time as Claude works.[/dim]

[bold yellow]Keybindings:[/bold yellow]
• [bold]Ctrl+D[/bold] - Toggle dark/light mode
• [bold]Ctrl+Q[/bold] - Quit

[dim]Scroll to see all projects ↓[/dim]""",
                id="welcome"
            )

            # Discover and show projects
            projects = self._discover_projects()

            if not projects:
                yield Static(
                    "\n\n[bold red]No Claude Code projects found[/bold red]\n\n"
                    "[dim]Use Claude Code in a project to create session files.[/dim]\n\n",
                    classes="error"
                )
            else:
                for project_name, session_dir in projects:
                    yield ProjectCard(project_name, session_dir)

        yield Footer()

    def _discover_projects(self, max_projects: int = 5):
        """Discover most recent Claude Code projects."""
        claude_dir = Path.home() / ".claude" / "projects"

        if not claude_dir.exists():
            return []

        projects = []
        for session_dir in claude_dir.iterdir():
            if session_dir.is_dir() and not session_dir.name.startswith('.'):
                jsonl_files = list(session_dir.glob("*.jsonl"))
                if jsonl_files:
                    most_recent = max(f.stat().st_mtime for f in jsonl_files)

                    # Extract nice project name
                    parts = session_dir.name.split('-')
                    if len(parts) > 4:
                        project_name = f"{parts[-2]}/{parts[-1]}"
                    elif len(parts) > 2:
                        project_name = parts[-1]
                    else:
                        project_name = session_dir.name

                    projects.append((project_name, session_dir, most_recent))

        # Sort by time and limit
        projects.sort(key=lambda x: x[2], reverse=True)
        return [(name, path) for name, path, _ in projects[:max_projects]]

    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.dark = not self.dark


def main():
    """Run the clean monitor."""
    app = CleanMonitor()
    app.run()


if __name__ == "__main__":
    main()
