#!/usr/bin/env python3
"""
Fifth Symphony - Multi-Project Claude Code Monitor

Auto-detects all active Claude Code projects and displays them in a unified dashboard.
Monitors multiple projects simultaneously with separate activity feeds per project.

Features:
- Auto-discovery of all Claude Code project sessions
- Separate panel per active project
- Unified statistics view
- Real-time activity tracking across all projects
"""

import sys
import signal
import time
from pathlib import Path
from datetime import datetime
from collections import deque, defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.columns import Columns

from modules.claude_code_monitor import ClaudeCodeMonitor, ClaudeEvent, ClaudeEventType


class ProjectMonitor:
    """Monitor for a single Claude Code project."""

    def __init__(self, project_name: str, session_dir: Path, max_log_entries: int = 10):
        self.project_name = project_name
        self.session_dir = session_dir
        self.monitor = ClaudeCodeMonitor()
        self.activity_log = deque(maxlen=max_log_entries)

        self.stats = {
            "user_prompts": 0,
            "files_read": 0,
            "files_written": 0,
            "files_edited": 0,
            "bash_commands": 0,
            "web_fetches": 0,
            "assistant_responses": 0
        }

        self.last_event_time = None
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

    def _add_log_entry(self, icon: str, message: str, style: str = ""):
        """Add entry to activity log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.activity_log.append((timestamp, icon, message, style))
        self.last_event_time = datetime.now()

    def _on_user_prompt(self, event: ClaudeEvent):
        self.stats["user_prompts"] += 1
        self._add_log_entry("🟣", f"User: {event.summary[:40]}", "bold magenta")

    def _on_file_read(self, event: ClaudeEvent):
        self.stats["files_read"] += 1
        self._add_log_entry("📖", f"Read: {event.summary[:40]}", "cyan")

    def _on_file_write(self, event: ClaudeEvent):
        self.stats["files_written"] += 1
        self._add_log_entry("✍️", f"Write: {event.summary[:40]}", "green")

    def _on_file_edit(self, event: ClaudeEvent):
        self.stats["files_edited"] += 1
        self._add_log_entry("✏️", f"Edit: {event.summary[:40]}", "yellow")

    def _on_bash_command(self, event: ClaudeEvent):
        self.stats["bash_commands"] += 1
        self._add_log_entry("⚡", f"Bash: {event.summary[:40]}", "bold yellow")

    def _on_web_fetch(self, event: ClaudeEvent):
        self.stats["web_fetches"] += 1
        self._add_log_entry("🌐", f"Web: {event.summary[:40]}", "blue")

    def _on_assistant_response(self, event: ClaudeEvent):
        self.stats["assistant_responses"] += 1
        self._add_log_entry("🔵", "Claude responding...", "bold blue")

    def start(self):
        """Start monitoring this project."""
        self.monitor.start_monitoring(self.session_dir, self.project_name)

    def stop(self):
        """Stop monitoring this project."""
        self.monitor.stop_monitoring()

    def get_status_text(self) -> Text:
        """Get status indicator."""
        if self.last_event_time and (datetime.now() - self.last_event_time).total_seconds() < 10:
            return Text("🟢 Active", style="bold green")
        elif self.last_event_time:
            return Text("🟡 Idle", style="bold yellow")
        else:
            return Text("⚪ Waiting", style="dim")

    def get_total_events(self) -> int:
        """Get total event count."""
        return sum(self.stats.values())


class MultiProjectMonitor:
    """Monitor multiple Claude Code projects simultaneously."""

    def __init__(self):
        self.console = Console()
        self.projects = {}  # project_name -> ProjectMonitor
        self.start_time = datetime.now()
        self.claude_projects_dir = Path.home() / ".claude" / "projects"

    def discover_projects(self):
        """Auto-discover all Claude Code project sessions."""
        if not self.claude_projects_dir.exists():
            self.console.print(f"[bold red]❌ Claude projects directory not found:[/bold red] {self.claude_projects_dir}")
            return []

        discovered = []
        for session_dir in self.claude_projects_dir.iterdir():
            if session_dir.is_dir() and not session_dir.name.startswith('.'):
                # Check if there are any .jsonl files (active sessions)
                jsonl_files = list(session_dir.glob("*.jsonl"))
                if jsonl_files:
                    # Extract project name from directory name
                    # Format: -Users-username-path-to-project
                    parts = session_dir.name.split('-')
                    if len(parts) > 3:
                        project_name = parts[-1]  # Last part is usually project name
                    else:
                        project_name = session_dir.name

                    discovered.append((project_name, session_dir))

        return discovered

    def start_monitoring(self):
        """Start monitoring all discovered projects."""
        projects = self.discover_projects()

        if not projects:
            self.console.print("[bold red]❌ No Claude Code projects found![/bold red]")
            self.console.print("   Use Claude Code in at least one project to create session files.")
            return False

        for project_name, session_dir in projects:
            monitor = ProjectMonitor(project_name, session_dir, max_log_entries=8)
            monitor.start()
            self.projects[project_name] = monitor

        return True

    def stop_monitoring(self):
        """Stop monitoring all projects."""
        for monitor in self.projects.values():
            monitor.stop()

    def create_header(self) -> Panel:
        """Create header panel."""
        runtime = datetime.now() - self.start_time
        hours, remainder = divmod(int(runtime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)

        header_text = Text()
        header_text.append("🎭 FIFTH SYMPHONY ", style="bold cyan")
        header_text.append("─ ", style="dim")
        header_text.append("Multi-Project Claude Code Monitor", style="bold white")
        header_text.append(f"\nMonitoring {len(self.projects)} project(s) ", style="dim")
        header_text.append(f"│ Runtime: {hours:02d}:{minutes:02d}:{seconds:02d}", style="dim")

        return Panel(
            Align.center(header_text),
            style="cyan",
            border_style="bright_cyan"
        )

    def create_global_stats_panel(self) -> Panel:
        """Create global statistics panel."""
        # Aggregate stats from all projects
        total_stats = defaultdict(int)
        for monitor in self.projects.values():
            for key, value in monitor.stats.items():
                total_stats[key] += value

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Label", style="cyan")
        table.add_column("Count", style="bold yellow", justify="right")

        table.add_row("🟣 User Prompts", str(total_stats["user_prompts"]))
        table.add_row("📖 Files Read", str(total_stats["files_read"]))
        table.add_row("✍️  Files Written", str(total_stats["files_written"]))
        table.add_row("✏️  Files Edited", str(total_stats["files_edited"]))
        table.add_row("⚡ Bash Commands", str(total_stats["bash_commands"]))
        table.add_row("🌐 Web Fetches", str(total_stats["web_fetches"]))
        table.add_row("🔵 Responses", str(total_stats["assistant_responses"]))

        total = sum(total_stats.values())
        table.add_row("", "")
        table.add_row("📊 Total", str(total), style="bold green")

        return Panel(
            table,
            title="[bold cyan]📊 Global Statistics[/bold cyan]",
            border_style="cyan",
            padding=(1, 1)
        )

    def create_project_panel(self, project_name: str, monitor: ProjectMonitor) -> Panel:
        """Create panel for individual project."""
        content = Text()

        # Status and event count
        status_line = Text()
        status_line.append(monitor.get_status_text())
        status_line.append(f"  │  {monitor.get_total_events()} events", style="dim")
        content.append(status_line)
        content.append("\n\n")

        # Recent activity
        if not monitor.activity_log:
            content.append("Waiting for activity...", style="dim italic")
        else:
            for timestamp, icon, message, style in monitor.activity_log:
                # Truncate to fit panel
                max_len = 35
                if len(message) > max_len:
                    message = message[:max_len-3] + "..."
                content.append(f"{icon} {message}\n", style=style)

        # Determine border color based on activity
        if monitor.last_event_time and (datetime.now() - monitor.last_event_time).total_seconds() < 10:
            border_style = "green"
        else:
            border_style = "dim"

        return Panel(
            content,
            title=f"[bold white]🎯 {project_name}[/bold white]",
            border_style=border_style,
            padding=(1, 1)
        )

    def create_footer(self) -> Panel:
        """Create footer panel."""
        footer_text = Text()
        footer_text.append("Press ", style="dim")
        footer_text.append("Ctrl+C", style="bold yellow")
        footer_text.append(" to stop  │  ", style="dim")
        footer_text.append("🟢 Active ", style="green")
        footer_text.append("🟡 Idle ", style="yellow")
        footer_text.append("⚪ Waiting", style="dim")

        return Panel(
            Align.center(footer_text),
            style="dim",
            border_style="dim"
        )

    def create_layout(self) -> Layout:
        """Create the main layout."""
        layout = Layout()

        layout.split_column(
            Layout(name="header", size=4),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )

        # Split body into projects and stats
        layout["body"].split_row(
            Layout(name="projects", ratio=3),
            Layout(name="stats", ratio=1)
        )

        # Populate header and footer
        layout["header"].update(self.create_header())
        layout["footer"].update(self.create_footer())
        layout["stats"].update(self.create_global_stats_panel())

        # Create project panels
        if self.projects:
            # Split projects area based on number of projects
            num_projects = len(self.projects)

            if num_projects == 1:
                # Single project - full height
                project_name, monitor = list(self.projects.items())[0]
                layout["projects"].update(self.create_project_panel(project_name, monitor))
            elif num_projects == 2:
                # Two projects - split vertically
                layout["projects"].split_column(
                    Layout(name="project_0"),
                    Layout(name="project_1")
                )
                for i, (project_name, monitor) in enumerate(self.projects.items()):
                    layout["projects"][f"project_{i}"].update(
                        self.create_project_panel(project_name, monitor)
                    )
            else:
                # Three or more - grid layout
                layout["projects"].split_column(
                    Layout(name="top_row"),
                    Layout(name="bottom_row")
                )

                # Split rows
                projects_list = list(self.projects.items())
                mid = (num_projects + 1) // 2

                # Top row
                if mid == 1:
                    project_name, monitor = projects_list[0]
                    layout["projects"]["top_row"].update(
                        self.create_project_panel(project_name, monitor)
                    )
                else:
                    layout["projects"]["top_row"].split_row(
                        *[Layout(name=f"top_{i}") for i in range(mid)]
                    )
                    for i, (project_name, monitor) in enumerate(projects_list[:mid]):
                        layout["projects"]["top_row"][f"top_{i}"].update(
                            self.create_project_panel(project_name, monitor)
                        )

                # Bottom row
                remaining = num_projects - mid
                if remaining == 1:
                    project_name, monitor = projects_list[mid]
                    layout["projects"]["bottom_row"].update(
                        self.create_project_panel(project_name, monitor)
                    )
                else:
                    layout["projects"]["bottom_row"].split_row(
                        *[Layout(name=f"bottom_{i}") for i in range(remaining)]
                    )
                    for i, (project_name, monitor) in enumerate(projects_list[mid:]):
                        layout["projects"]["bottom_row"][f"bottom_{i}"].update(
                            self.create_project_panel(project_name, monitor)
                        )
        else:
            layout["projects"].update(
                Panel("No active projects", style="dim", border_style="dim")
            )

        return layout

    def render(self) -> Layout:
        """Render current state."""
        return self.create_layout()


def main():
    """Run multi-project monitor."""
    console = Console()

    # Create monitor
    monitor = MultiProjectMonitor()

    # Setup signal handlers
    def signal_handler(sig, frame):
        console.print("\n[bold red]🛑 Shutting down...[/bold red]")
        monitor.stop_monitoring()

        # Print final stats per project
        console.print("\n[bold cyan]📊 Final Statistics by Project:[/bold cyan]\n")
        for project_name, proj_monitor in monitor.projects.items():
            console.print(f"[bold white]{project_name}:[/bold white]")
            console.print(f"  Events: {proj_monitor.get_total_events()}")
            console.print(f"  User Prompts: {proj_monitor.stats['user_prompts']}")
            console.print(f"  Files Read: {proj_monitor.stats['files_read']}")
            console.print(f"  Files Written: {proj_monitor.stats['files_written']}")
            console.print(f"  Files Edited: {proj_monitor.stats['files_edited']}")
            console.print()

        console.print("[bold green]✅ Monitor stopped[/bold green]\n")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start monitoring
    console.print("[bold cyan]🔍 Discovering Claude Code projects...[/bold cyan]")
    if not monitor.start_monitoring():
        sys.exit(1)

    console.print(f"[bold green]✅ Monitoring {len(monitor.projects)} project(s)![/bold green]")
    for project_name in monitor.projects.keys():
        console.print(f"   🎯 {project_name}")
    console.print()

    # Run live display
    with Live(monitor.render(), refresh_per_second=2, console=console) as live:
        try:
            while True:
                time.sleep(0.5)
                live.update(monitor.render())
        except KeyboardInterrupt:
            signal_handler(signal.SIGINT, None)


if __name__ == "__main__":
    main()
