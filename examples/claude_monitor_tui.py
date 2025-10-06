#!/usr/bin/env python3
"""
Fifth Symphony - Claude Code TUI Monitor

Rich TUI (Text User Interface) with multiple panels:
- Live activity log
- Real-time statistics
- Session information
- Event feed

Beautiful, CLI-friendly dashboard for monitoring Claude Code activity.
"""

import sys
import signal
import time
from pathlib import Path
from datetime import datetime
from collections import deque

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align

from modules.claude_code_monitor import ClaudeCodeMonitor, ClaudeEvent, ClaudeEventType


class TUIMonitor:
    """Rich TUI monitor with multiple panels."""

    def __init__(self, max_log_entries: int = 20):
        self.console = Console()
        self.monitor = ClaudeCodeMonitor()
        self.max_log_entries = max_log_entries

        # Activity log (recent events)
        self.activity_log = deque(maxlen=max_log_entries)

        # Statistics
        self.stats = {
            "user_prompts": 0,
            "files_read": 0,
            "files_written": 0,
            "files_edited": 0,
            "bash_commands": 0,
            "web_fetches": 0,
            "assistant_responses": 0
        }

        self.start_time = datetime.now()
        self.last_event_time = None
        self.session_count = 0

        self._register_callbacks()

    def _register_callbacks(self):
        """Register event callbacks."""
        self.monitor.add_callback(ClaudeEventType.USER_PROMPT, self._on_user_prompt)
        self.monitor.add_callback(ClaudeEventType.FILE_READ, self._on_file_read)
        self.monitor.add_callback(ClaudeEventType.FILE_WRITE, self._on_file_write)
        self.monitor.add_callback(ClaudeEventType.FILE_EDIT, self._on_file_edit)
        self.monitor.add_callback(ClaudeEventType.BASH_COMMAND, self._on_bash_command)
        self.monitor.add_callback(ClaudeEventType.WEB_FETCH, self._on_web_fetch)
        self.monitor.add_callback(ClaudeEventType.ASSISTANT_RESPONSE, self._on_assistant_response)

    def _add_log_entry(self, message: str, icon: str, style: str = ""):
        """Add entry to activity log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.activity_log.append((timestamp, icon, message, style))
        self.last_event_time = datetime.now()

    def _on_user_prompt(self, event: ClaudeEvent):
        """Handle user prompt."""
        self.stats["user_prompts"] += 1
        self._add_log_entry(f"User: {event.summary}", "🟣", "bold magenta")

    def _on_file_read(self, event: ClaudeEvent):
        """Handle file read."""
        self.stats["files_read"] += 1
        self._add_log_entry(f"Read: {event.summary}", "📖", "cyan")

    def _on_file_write(self, event: ClaudeEvent):
        """Handle file write."""
        self.stats["files_written"] += 1
        self._add_log_entry(f"Write: {event.summary}", "✍️", "green")

    def _on_file_edit(self, event: ClaudeEvent):
        """Handle file edit."""
        self.stats["files_edited"] += 1
        self._add_log_entry(f"Edit: {event.summary}", "✏️", "yellow")

    def _on_bash_command(self, event: ClaudeEvent):
        """Handle bash command."""
        self.stats["bash_commands"] += 1
        self._add_log_entry(f"Bash: {event.summary}", "⚡", "bold yellow")

    def _on_web_fetch(self, event: ClaudeEvent):
        """Handle web fetch."""
        self.stats["web_fetches"] += 1
        self._add_log_entry(f"Web: {event.summary}", "🌐", "blue")

    def _on_assistant_response(self, event: ClaudeEvent):
        """Handle assistant response."""
        self.stats["assistant_responses"] += 1
        self._add_log_entry("Claude responding...", "🔵", "bold blue")

    def start_monitoring(self, session_dir: Path = None):
        """Start monitoring Claude Code sessions."""
        if session_dir is None:
            # Auto-detect session directory
            session_dir = Path.home() / ".claude" / "projects" / "-path-to-git-internal-repos-project-name"

        if not session_dir.exists():
            self.console.print(f"[bold red]❌ Session directory not found:[/bold red] {session_dir}")
            self.console.print("   Make sure Claude Code has been used in this project at least once!")
            return False

        self.monitor.start_monitoring(session_dir, "Fifth Symphony")

        # Get active sessions count
        sessions = self.monitor.get_active_sessions()
        self.session_count = len(sessions)

        return True

    def stop_monitoring(self):
        """Stop monitoring."""
        self.monitor.stop_monitoring()

    def create_header(self) -> Panel:
        """Create header panel."""
        runtime = datetime.now() - self.start_time
        hours, remainder = divmod(int(runtime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)

        header_text = Text()
        header_text.append("🎭 FIFTH SYMPHONY ", style="bold cyan")
        header_text.append("─ ", style="dim")
        header_text.append("Claude Code Monitor", style="bold white")
        header_text.append(f"\nRuntime: {hours:02d}:{minutes:02d}:{seconds:02d}", style="dim")

        return Panel(
            Align.center(header_text),
            style="cyan",
            border_style="bright_cyan"
        )

    def create_stats_panel(self) -> Panel:
        """Create statistics panel."""
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Label", style="cyan")
        table.add_column("Count", style="bold yellow", justify="right")

        table.add_row("🟣 User Prompts", str(self.stats["user_prompts"]))
        table.add_row("📖 Files Read", str(self.stats["files_read"]))
        table.add_row("✍️  Files Written", str(self.stats["files_written"]))
        table.add_row("✏️  Files Edited", str(self.stats["files_edited"]))
        table.add_row("⚡ Bash Commands", str(self.stats["bash_commands"]))
        table.add_row("🌐 Web Fetches", str(self.stats["web_fetches"]))
        table.add_row("🔵 Claude Responses", str(self.stats["assistant_responses"]))

        # Total activity
        total = sum(self.stats.values())
        table.add_row("", "")  # Spacer
        table.add_row("📊 Total Events", str(total), style="bold green")

        return Panel(
            table,
            title="[bold cyan]📊 Statistics[/bold cyan]",
            border_style="cyan",
            padding=(1, 2)
        )

    def create_activity_panel(self) -> Panel:
        """Create activity log panel."""
        if not self.activity_log:
            content = Text("Waiting for Claude Code activity...", style="dim italic")
        else:
            content = Text()
            for timestamp, icon, message, style in self.activity_log:
                # Truncate long messages
                max_msg_len = 60
                if len(message) > max_msg_len:
                    message = message[:max_msg_len-3] + "..."

                content.append(f"[{timestamp}] ", style="dim")
                content.append(f"{icon} ", style=style)
                content.append(f"{message}\n", style=style)

        return Panel(
            content,
            title="[bold cyan]📋 Activity Log[/bold cyan]",
            border_style="cyan",
            padding=(1, 2)
        )

    def create_session_panel(self) -> Panel:
        """Create session info panel."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Label", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("🎭 Active Sessions", str(self.session_count))

        if self.last_event_time:
            time_since = datetime.now() - self.last_event_time
            seconds = int(time_since.total_seconds())
            if seconds < 60:
                time_str = f"{seconds}s ago"
            else:
                minutes = seconds // 60
                time_str = f"{minutes}m {seconds % 60}s ago"
            table.add_row("⏱️  Last Event", time_str)
        else:
            table.add_row("⏱️  Last Event", "None yet", style="dim")

        # Status indicator
        if self.last_event_time and (datetime.now() - self.last_event_time).total_seconds() < 5:
            status = Text("🟢 Active", style="bold green")
        else:
            status = Text("🟡 Idle", style="bold yellow")

        table.add_row("📡 Status", status)

        return Panel(
            table,
            title="[bold cyan]🔍 Session Info[/bold cyan]",
            border_style="cyan",
            padding=(1, 2)
        )

    def create_footer(self) -> Panel:
        """Create footer panel."""
        footer_text = Text()
        footer_text.append("Press ", style="dim")
        footer_text.append("Ctrl+C", style="bold yellow")
        footer_text.append(" to stop monitoring", style="dim")

        return Panel(
            Align.center(footer_text),
            style="dim",
            border_style="dim"
        )

    def create_layout(self) -> Layout:
        """Create the main layout."""
        layout = Layout()

        # Main structure
        layout.split_column(
            Layout(name="header", size=4),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )

        # Body split into left and right
        layout["body"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=1)
        )

        # Left side split into activity and session
        layout["left"].split_column(
            Layout(name="activity", ratio=3),
            Layout(name="session", size=9)
        )

        # Right side is stats
        layout["right"].update(Layout(name="stats"))

        # Populate panels
        layout["header"].update(self.create_header())
        layout["activity"].update(self.create_activity_panel())
        layout["stats"].update(self.create_stats_panel())
        layout["session"].update(self.create_session_panel())
        layout["footer"].update(self.create_footer())

        return layout

    def render(self) -> Layout:
        """Render current state."""
        return self.create_layout()


def main():
    """Run TUI monitor."""
    console = Console()

    # Create monitor
    monitor = TUIMonitor(max_log_entries=20)

    # Setup signal handlers for clean shutdown
    def signal_handler(sig, frame):
        console.print("\n[bold red]🛑 Shutting down...[/bold red]")
        monitor.stop_monitoring()

        # Print final statistics
        console.print("\n[bold cyan]📊 Final Statistics:[/bold cyan]")
        runtime = datetime.now() - monitor.start_time
        hours, remainder = divmod(int(runtime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)

        console.print(f"Runtime:          {hours:02d}:{minutes:02d}:{seconds:02d}")
        console.print(f"User Prompts:     {monitor.stats['user_prompts']}")
        console.print(f"Files Read:       {monitor.stats['files_read']}")
        console.print(f"Files Written:    {monitor.stats['files_written']}")
        console.print(f"Files Edited:     {monitor.stats['files_edited']}")
        console.print(f"Bash Commands:    {monitor.stats['bash_commands']}")
        console.print(f"Web Fetches:      {monitor.stats['web_fetches']}")
        console.print(f"Claude Responses: {monitor.stats['assistant_responses']}")
        console.print("\n[bold green]✅ Monitor stopped[/bold green]\n")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start monitoring
    console.print("[bold cyan]🔍 Starting Claude Code monitoring...[/bold cyan]")
    if not monitor.start_monitoring():
        sys.exit(1)

    console.print("[bold green]✅ Monitoring active![/bold green]\n")

    # Run live display
    with Live(monitor.render(), refresh_per_second=2, console=console) as live:
        try:
            while True:
                time.sleep(0.5)  # Update twice per second
                live.update(monitor.render())
        except KeyboardInterrupt:
            signal_handler(signal.SIGINT, None)


if __name__ == "__main__":
    main()
