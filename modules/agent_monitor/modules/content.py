"""Content Monitor - Audio History and Documentation Browser.

Standalone module showing audio summaries and documentation files.
Run with: uv run python -m agent_monitor.modules.content
"""

import os
import time
import subprocess
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.text import Text

from agent_monitor.shared import (
    ModuleConfig,
    KeyboardHandler,
    RichTableBuilder,
    Colors,
    Symbols
)
from agent_monitor.utils.relative_time import relative_time
from agent_monitor.utils.screenshot import take_screenshot

# Dynamic path resolution for ai-bedo repository
ALBEDO_ROOT = Path(os.getenv("ALBEDO_ROOT", Path.home() / "git" / "internal" / "repos" / "ai-bedo"))


class ContentMonitor:
    """Monitor Audio History and Documentation files."""

    def __init__(self):
        self.console = Console()
        self.config = ModuleConfig()
        self.running = True
        self.last_refresh = datetime.now()

        # Navigation state
        self.focused_panel = None  # "audio" or "docs"
        self.selected_row = 0

        # Data
        self.audio_files = []
        self.doc_files = []

        # Load initial data
        self.load_audio_history()
        self.load_documentation()

    def load_audio_history(self):
        """Load audio history files from both active and processed directories."""
        locations = [
            # Check active directories first (unprocessed)
            ALBEDO_ROOT / "communications" / "vm-audio",
            ALBEDO_ROOT / "communications" / "main-audio",
            # Then processed directories
            ALBEDO_ROOT / "communications" / "audio" / ".processed",
            ALBEDO_ROOT / "communications" / "vm-audio" / ".processed",
            ALBEDO_ROOT / "communications" / "main-audio" / ".processed",
        ]

        all_files = []
        for location in locations:
            if location.exists():
                for txt_file in location.glob("*.txt"):
                    all_files.append(txt_file)

        # Sort by modification time, keep top 20
        self.audio_files = sorted(
            all_files,
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )[:20]

    def load_documentation(self):
        """Load documentation files (CLAUDE.md, README.md) from git repos."""
        git_dir = Path.home() / "git"
        if not git_dir.exists():
            self.doc_files = []
            return

        all_docs = []

        # Search for CLAUDE.md and README.md files
        for pattern in ["**/CLAUDE.md", "**/README.md"]:
            for doc_file in git_dir.glob(pattern):
                # Skip certain directories
                if any(skip in str(doc_file) for skip in [".git/", "node_modules/", "venv/"]):
                    continue
                all_docs.append(doc_file)

        # Sort by modification time, keep top 20
        self.doc_files = sorted(
            all_docs,
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )[:20]

    def create_audio_table(self):
        """Create Audio History table."""
        is_focused = self.focused_panel == "audio"
        border_style = Colors.ACCENT if is_focused else Colors.SECONDARY

        table = RichTableBuilder.create_table(
            border_style=border_style,
            columns=[
                ("Time", {"style": Colors.SECONDARY, "width": 8, "no_wrap": True}),
                ("Project", {"style": Colors.PRIMARY, "width": 20, "overflow": "ellipsis"}),
                ("Age", {"style": Colors.DIM, "width": 8, "no_wrap": True})
            ]
        )

        for idx, audio_file in enumerate(self.audio_files[:10]):
            try:
                timestamp = datetime.fromtimestamp(audio_file.stat().st_mtime)
                time_str = timestamp.strftime("%H:%M:%S")
                age_str = relative_time(timestamp)

                # Extract project name from filename
                # Format: YYYYMMDD-HHMMSS-project.txt
                parts = audio_file.stem.split("-")
                project = parts[2] if len(parts) >= 3 else "unknown"

                # Highlight selected row if focused
                if is_focused and idx == self.selected_row:
                    style = f"bold {Colors.ACCENT} on black"
                    table.add_row(
                        f"[{style}]{time_str}[/{style}]",
                        f"[{style}]{project}[/{style}]",
                        f"[{style}]{age_str}[/{style}]"
                    )
                else:
                    table.add_row(time_str, project, age_str)

            except Exception:
                continue

        if not self.audio_files:
            table.add_row("", "No audio files", "")

        return table

    def create_docs_table(self):
        """Create Documentation browser table."""
        is_focused = self.focused_panel == "docs"
        border_style = Colors.ACCENT if is_focused else Colors.PRIMARY

        table = RichTableBuilder.create_table(
            border_style=border_style,
            columns=[
                ("Mod", {"style": Colors.SECONDARY, "width": 8, "no_wrap": True}),
                ("Type", {"style": Colors.PRIMARY, "width": 10, "no_wrap": True}),
                ("File", {"style": Colors.DIM, "overflow": "ellipsis"})
            ]
        )

        for idx, doc_file in enumerate(self.doc_files[:15]):
            try:
                timestamp = datetime.fromtimestamp(doc_file.stat().st_mtime)
                time_str = relative_time(timestamp)

                # Determine type
                if "CLAUDE.md" in doc_file.name:
                    doc_type = "Claude"
                elif "README.md" in doc_file.name:
                    doc_type = "README"
                else:
                    doc_type = "Doc"

                # Get relative path
                try:
                    rel_path = doc_file.relative_to(Path.home() / "git")
                    file_str = str(rel_path)
                except ValueError:
                    file_str = doc_file.name

                # Highlight selected row if focused
                if is_focused and idx == self.selected_row:
                    style = f"bold {Colors.ACCENT} on black"
                    table.add_row(
                        f"[{style}]{time_str}[/{style}]",
                        f"[{style}]{doc_type}[/{style}]",
                        f"[{style}]{file_str}[/{style}]"
                    )
                else:
                    table.add_row(time_str, doc_type, file_str)

            except Exception:
                continue

        if not self.doc_files:
            table.add_row("", "", "No documentation found")

        return table

    def play_audio(self, index: int):
        """Play selected audio file."""
        if index < len(self.audio_files):
            audio_file = self.audio_files[index]
            try:
                # Read audio summary
                with open(audio_file) as f:
                    content = f.read().strip()

                # Play using afplay (macOS text-to-speech could be added here)
                # For now, just open the file
                subprocess.run(["open", str(audio_file)], check=False)
            except Exception:
                pass

    def open_documentation(self, index: int):
        """Open selected documentation file."""
        if index < len(self.doc_files):
            doc_file = self.doc_files[index]
            try:
                subprocess.run(["open", str(doc_file)], check=False)
            except Exception:
                pass

    def handle_selection(self):
        """Handle Enter key on selected item."""
        if self.focused_panel == "audio":
            self.play_audio(self.selected_row)
        elif self.focused_panel == "docs":
            self.open_documentation(self.selected_row)

    def move_selection_down(self):
        """Move selection down in focused panel."""
        if self.focused_panel == "audio":
            max_rows = min(len(self.audio_files), 10)
        elif self.focused_panel == "docs":
            max_rows = min(len(self.doc_files), 15)
        else:
            return

        if self.selected_row < max_rows - 1:
            self.selected_row += 1

    def move_selection_up(self):
        """Move selection up in focused panel."""
        if self.selected_row > 0:
            self.selected_row -= 1

    def create_layout(self):
        """Create module layout with both panels."""
        layout = Layout()

        # Split vertically
        audio_size = min(len(self.audio_files), 10) + 3
        docs_size = min(len(self.doc_files), 15) + 3

        layout.split_column(
            Layout(name="header", size=2),
            Layout(name="audio", size=max(audio_size, 5)),
            Layout(name="docs", size=max(docs_size, 5)),
            Layout(name="footer", size=2)
        )

        # Header
        header_text = Text()
        header_text.append("Content Monitor", style=f"bold {Colors.PRIMARY}")
        header_text.append(" | ", style=Colors.DIM)
        header_text.append(f"Last refresh: {self.last_refresh.strftime('%H:%M:%S')}", style=Colors.DIM)
        layout["header"].update(header_text)

        # Audio panel
        layout["audio"].update(
            RichTableBuilder.create_panel(
                self.create_audio_table(),
                title=f"Audio History ({len(self.audio_files)})",
                border_style=Colors.SECONDARY
            )
        )

        # Documentation panel
        layout["docs"].update(
            RichTableBuilder.create_panel(
                self.create_docs_table(),
                title=f"Documentation ({len(self.doc_files)})",
                border_style=Colors.PRIMARY
            )
        )

        # Footer
        footer_text = Text()
        if self.focused_panel:
            footer_text.append("↑↓/JK", style=f"bold {Colors.ACCENT}")
            footer_text.append(":Navigate  ", style=Colors.DIM)
            footer_text.append("Enter", style=f"bold {Colors.ACCENT}")
            footer_text.append(":Open  ", style=Colors.DIM)
            footer_text.append("Esc", style=f"bold {Colors.ACCENT}")
            footer_text.append(":Unfocus  ", style=Colors.DIM)
        else:
            footer_text.append("Q", style=f"bold {Colors.ACCENT}")
            footer_text.append(":Quit  ", style=Colors.DIM)
            footer_text.append("R", style=f"bold {Colors.ACCENT}")
            footer_text.append(":Refresh  ", style=Colors.DIM)
            footer_text.append("A", style=f"bold {Colors.ACCENT}")
            footer_text.append(":Audio  ", style=Colors.DIM)
            footer_text.append("D", style=f"bold {Colors.ACCENT}")
            footer_text.append(":Docs  ", style=Colors.DIM)
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
                        if key.lower() == 'q':
                            self.running = False
                        elif key.lower() == 'r':
                            self.load_audio_history()
                            self.load_documentation()
                            self.last_refresh = datetime.now()
                        elif key.lower() == 's':
                            screenshot_path = take_screenshot(self.console, "content")
                            time.sleep(0.5)
                        elif key.lower() == 'a':
                            self.focused_panel = "audio"
                            self.selected_row = 0
                        elif key.lower() == 'd':
                            self.focused_panel = "docs"
                            self.selected_row = 0
                        elif key == '\x1b':  # Escape
                            self.focused_panel = None
                            self.selected_row = 0
                        elif key == '\n' or key == '\r':  # Enter
                            self.handle_selection()
                        elif self.focused_panel:
                            # Navigation keys
                            if key == 'j' or ord(key) == 66:  # j or Down arrow
                                self.move_selection_down()
                            elif key == 'k' or ord(key) == 65:  # k or Up arrow
                                self.move_selection_up()

                    # Update display
                    live.update(self.create_layout())
                    time.sleep(0.1)


def main():
    """Entry point for standalone execution."""
    try:
        monitor = ContentMonitor()
        monitor.run()
    except KeyboardInterrupt:
        pass  # Clean exit on Ctrl+C


if __name__ == "__main__":
    main()
