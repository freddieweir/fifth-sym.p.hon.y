"""System Status Monitor - Albedo Status, VM Subagents, and Claude Code Context.

Standalone module showing system overview and working context.
Run with: uv run python -m agent_monitor.modules.system_status
"""

import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from agent_monitor.shared import Colors, KeyboardHandler, ModuleConfig, RichTableBuilder, Symbols
from agent_monitor.utils.relative_time import relative_time
from agent_monitor.utils.screenshot import take_screenshot
from rich import box
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.table import Table
from rich.text import Text


class SystemStatusMonitor:
    """Monitor Albedo Status, VM Subagents, and Claude Code Context."""

    def __init__(self):
        self.console = Console()
        self.config = ModuleConfig()
        self.running = True
        self.last_refresh = datetime.now()

        # Navigation state
        self.focused_panel = None  # "context" only (for now)
        self.selected_row = 0

        # Data
        self.context_files = []

        # Load initial data
        self.load_context_files()

    def load_context_files(self):
        """Load recently accessed files from Claude Code file-history."""
        self.context_files = []

        file_history_dir = Path.home() / ".claude" / "file-history"
        if not file_history_dir.exists():
            return

        try:
            # Find most recent session
            sessions = sorted(
                [s for s in file_history_dir.iterdir() if s.is_dir()],
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )

            if not sessions:
                return

            recent_session = sessions[0]

            # Group files by hash and track latest version + edit count
            file_data = defaultdict(lambda: {"latest_mtime": 0, "version_count": 0, "hash": ""})

            for file_path in recent_session.glob("*@v*"):
                try:
                    parts = file_path.name.split("@")
                    if len(parts) != 2:
                        continue

                    file_hash = parts[0]
                    version = int(parts[1].replace("v", ""))
                    mtime = file_path.stat().st_mtime

                    # Track highest version number and latest mtime
                    if mtime > file_data[file_hash]["latest_mtime"]:
                        file_data[file_hash]["latest_mtime"] = mtime

                    if version > file_data[file_hash]["version_count"]:
                        file_data[file_hash]["version_count"] = version
                        file_data[file_hash]["hash"] = file_hash

                except (ValueError, IndexError):
                    continue

            # Convert to list and sort by most recent access
            self.context_files = [
                {
                    "hash": data["hash"][:8],  # First 8 chars
                    "mtime": data["latest_mtime"],
                    "edits": data["version_count"]
                }
                for hash_key, data in file_data.items()
            ]

            # Sort by most recently accessed, take top 15
            self.context_files = sorted(
                self.context_files,
                key=lambda x: x["mtime"],
                reverse=True
            )[:15]

        except Exception:
            # Silently fail - don't crash if file-history unavailable
            self.context_files = []

    def create_albedo_status_panel(self):
        """Create Albedo status LED panel."""
        table = Table(
            box=box.SIMPLE,
            border_style=Colors.PRIMARY,
            show_header=False,
            expand=True,
            padding=(0, 0)
        )
        table.add_column("Status", justify="center", style=Colors.SUCCESS)

        # Albedo is running if we're executing this code :)
        status_indicator = f"[{Colors.SUCCESS}]{Symbols.ACTIVE} Albedo Active[/{Colors.SUCCESS}]"
        table.add_row(status_indicator)

        return table

    def create_vm_table(self):
        """Create VM Subagents status table."""
        table = RichTableBuilder.create_table(
            border_style=Colors.SECONDARY,
            columns=[
                ("St", {"justify": "center", "style": Colors.SUCCESS, "width": 3}),
                ("Task", {"style": Colors.SECONDARY, "overflow": "ellipsis"})
            ]
        )

        # Placeholder for VM subagents
        # TODO: Load actual VM task status
        table.add_row(Symbols.IDLE, "No active VM tasks")

        return table

    def create_context_table(self):
        """Create Claude Code Context Files table."""
        is_focused = self.focused_panel == "context"
        border_style = Colors.ACCENT if is_focused else Colors.PRIMARY

        table = RichTableBuilder.create_table(
            border_style=border_style,
            columns=[
                ("Hash", {"style": Colors.SECONDARY, "width": 8, "no_wrap": True}),
                ("Accessed", {"style": Colors.PRIMARY, "width": 10, "no_wrap": True}),
                ("Edits", {"style": Colors.DIM, "width": 5, "justify": "right"})
            ]
        )

        for idx, context_file in enumerate(self.context_files):
            try:
                time_str = relative_time(context_file["mtime"])
                hash_str = context_file["hash"]
                edits_str = f"v{context_file['edits']}"

                # Highlight selected row if focused
                if is_focused and idx == self.selected_row:
                    style = f"bold {Colors.ACCENT} on black"
                    table.add_row(
                        f"[{style}]{hash_str}[/{style}]",
                        f"[{style}]{time_str}[/{style}]",
                        f"[{style}]{edits_str}[/{style}]"
                    )
                else:
                    table.add_row(hash_str, time_str, edits_str)
            except Exception:
                continue

        if not self.context_files:
            table.add_row("", "No context", "")

        return table

    def move_selection_down(self):
        """Move selection down in focused panel."""
        if self.focused_panel == "context":
            max_rows = min(len(self.context_files), 15)
            if self.selected_row < max_rows - 1:
                self.selected_row += 1

    def move_selection_up(self):
        """Move selection up in focused panel."""
        if self.selected_row > 0:
            self.selected_row -= 1

    def create_layout(self):
        """Create module layout with all panels."""
        layout = Layout()

        # Split vertically
        context_size = min(len(self.context_files), 15) + 3

        layout.split_column(
            Layout(name="header", size=2),
            Layout(name="albedo_status", size=4),
            Layout(name="context", size=max(context_size, 5)),
            Layout(name="vm", size=4),
            Layout(name="footer", size=2)
        )

        # Header
        header_text = Text()
        header_text.append("System Status Monitor", style=f"bold {Colors.PRIMARY}")
        header_text.append(" | ", style=Colors.DIM)
        header_text.append(f"Last refresh: {self.last_refresh.strftime('%H:%M:%S')}", style=Colors.DIM)
        layout["header"].update(header_text)

        # Albedo Status panel
        layout["albedo_status"].update(
            RichTableBuilder.create_panel(
                self.create_albedo_status_panel(),
                title="Albedo Status",
                border_style=Colors.PRIMARY
            )
        )

        # Context Files panel
        layout["context"].update(
            RichTableBuilder.create_panel(
                self.create_context_table(),
                title=f"Claude Code Context ({len(self.context_files)})",
                border_style=Colors.SECONDARY
            )
        )

        # VM Status panel
        layout["vm"].update(
            RichTableBuilder.create_panel(
                self.create_vm_table(),
                title="VM Subagents",
                border_style=Colors.SECONDARY
            )
        )

        # Footer
        footer_text = Text()
        if self.focused_panel:
            footer_text.append("↑↓/JK", style=f"bold {Colors.ACCENT}")
            footer_text.append(":Navigate  ", style=Colors.DIM)
            footer_text.append("Esc", style=f"bold {Colors.ACCENT}")
            footer_text.append(":Unfocus  ", style=Colors.DIM)
        else:
            footer_text.append("Q", style=f"bold {Colors.ACCENT}")
            footer_text.append(":Quit  ", style=Colors.DIM)
            footer_text.append("R", style=f"bold {Colors.ACCENT}")
            footer_text.append(":Refresh  ", style=Colors.DIM)
            footer_text.append("C", style=f"bold {Colors.ACCENT}")
            footer_text.append(":Context  ", style=Colors.DIM)
            footer_text.append("S", style=f"bold {Colors.ACCENT}")
            footer_text.append(":Screenshot", style=Colors.DIM)
        layout["footer"].update(footer_text)

        return layout

    def run(self):
        """Main event loop."""
        with KeyboardHandler() as kbd:
            with Live(
                self.create_layout(),
                console=self.console,
                refresh_per_second=2,
                screen=True
            ) as live:
                while self.running:
                    # Handle keyboard input
                    key = kbd.get_key()

                    if key:
                        if key.lower() == "q":
                            self.running = False
                        elif key.lower() == "r":
                            self.load_context_files()
                            self.last_refresh = datetime.now()
                        elif key.lower() == "s":
                            take_screenshot(self.console, "system_status")
                            time.sleep(0.5)
                        elif key.lower() == "c":
                            self.focused_panel = "context"
                            self.selected_row = 0
                        elif key == "\x1b":  # Escape
                            self.focused_panel = None
                            self.selected_row = 0
                        elif self.focused_panel:
                            # Navigation keys
                            if key == "j" or ord(key) == 66:  # j or Down arrow
                                self.move_selection_down()
                            elif key == "k" or ord(key) == 65:  # k or Up arrow
                                self.move_selection_up()

                    # Update display
                    live.update(self.create_layout())
                    time.sleep(0.1)


def main():
    """Entry point for standalone execution."""
    try:
        monitor = SystemStatusMonitor()
        monitor.run()
    except KeyboardInterrupt:
        pass  # Clean exit on Ctrl+C


if __name__ == "__main__":
    main()
