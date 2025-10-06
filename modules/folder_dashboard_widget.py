"""
Folder Management Dashboard Widget

Textual widget for displaying folder summaries and quick access.
Attention-friendly with visual file organization and quick actions.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from textual.widget import Widget
from textual.widgets import Static, DataTable, Tree
from textual.reactive import reactive
from textual.containers import Container, Vertical, Horizontal
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree as RichTree

from modules.folder_manager import FolderManager, FolderSummary, FileEvent

logger = logging.getLogger(__name__)


class FolderSummaryWidget(Static):
    """
    Display summary of folder contents.

    Shows:
    - Total files and size
    - File type breakdown
    - Recent files
    - Cleanup suggestions
    """

    # Reactive state
    current_folder = reactive("downloads")
    summary: Optional[FolderSummary] = None

    def __init__(self, folder_manager: FolderManager):
        super().__init__()
        self.folder_manager = folder_manager

    async def on_mount(self):
        """Load summary on mount."""
        await self.refresh_summary()

    async def refresh_summary(self):
        """Refresh folder summary."""
        try:
            self.summary = await self.folder_manager.get_folder_summary(self.current_folder)
            self.refresh()
        except Exception as e:
            logger.error(f"Failed to get folder summary: {e}")

    def render(self):
        """Render folder summary."""
        if not self.summary:
            return Text("Loading folder summary...", style="dim")

        # Build summary table
        table = Table.grid(padding=(0, 2))
        table.add_column(justify="left", style="cyan")
        table.add_column(justify="left", style="white")

        # Overview
        table.add_row("📁 Folder:", str(self.summary.path.name))
        table.add_row("📊 Total Files:", str(self.summary.total_files))
        table.add_row("💾 Total Size:", self.folder_manager.format_size(self.summary.total_size))

        table.add_row("", "")  # Spacer

        # File types
        table.add_row("📝 File Types:", "")

        # Top 5 file types
        sorted_types = sorted(self.summary.file_types.items(), key=lambda x: x[1], reverse=True)[:5]

        for ext, count in sorted_types:
            table.add_row("", f"  {ext}: {count} files")

        table.add_row("", "")  # Spacer

        # Recent files
        if self.summary.recent_files:
            table.add_row("🕐 Recent Files:", f"{len(self.summary.recent_files)} files")

        # Old files (cleanup suggestion)
        if self.summary.old_files:
            table.add_row(
                "🗑️  Old Files:", f"{len(self.summary.old_files)} files (cleanup?)", style="yellow"
            )

        # Large files
        if self.summary.large_files:
            table.add_row(
                "📦 Large Files:", f"{len(self.summary.large_files)} files", style="yellow"
            )

        return Panel(
            table,
            title=f"[bold cyan]📁 {self.current_folder.upper()} SUMMARY[/bold cyan]",
            border_style="cyan",
        )

    async def set_folder(self, folder_name: str):
        """
        Change current folder.

        Args:
            folder_name: Name of folder to display
        """
        self.current_folder = folder_name
        await self.refresh_summary()


class FolderEventsWidget(Static):
    """
    Display real-time folder events.

    Shows recent file system events from watched folders.
    """

    def __init__(self, max_events: int = 10):
        super().__init__()
        self.max_events = max_events
        self.events: list[FileEvent] = []

    def add_event(self, event: FileEvent):
        """
        Add file system event to display.

        Args:
            event: File system event
        """
        self.events.insert(0, event)
        if len(self.events) > self.max_events:
            self.events.pop()
        self.refresh()

    def render(self):
        """Render recent events."""
        if not self.events:
            return Text("No recent events", style="dim")

        # Build events list
        events_text = Text()

        for event in self.events:
            # Time
            time_str = event.timestamp.strftime("%H:%M:%S")
            events_text.append(f"[{time_str}] ", style="dim")

            # Action icon
            action_icons = {"created": "✨", "modified": "📝", "deleted": "🗑️", "moved": "📦"}
            icon = action_icons.get(event.action.value, "📄")
            events_text.append(f"{icon} ", style="white")

            # Action
            action_colors = {
                "created": "green",
                "modified": "yellow",
                "deleted": "red",
                "moved": "cyan",
            }
            color = action_colors.get(event.action.value, "white")
            events_text.append(f"{event.action.value.upper()}: ", style=color)

            # File name
            events_text.append(f"{event.path.name}\n", style="white")

        return Panel(
            events_text, title="[bold yellow]🔔 RECENT EVENTS[/bold yellow]", border_style="yellow"
        )


class QuickAccessWidget(Static):
    """
    Quick access buttons for common folder operations.

    Actions:
    - Open in Finder/Explorer
    - Refresh summary
    - Find files
    - Organize files
    - Clean up old files
    """

    def __init__(self, folder_manager: FolderManager):
        super().__init__()
        self.folder_manager = folder_manager

    def render(self):
        """Render quick access menu."""
        menu_text = Text()

        menu_text.append("Quick Actions:\n\n", style="bold cyan")

        actions = [
            ("(o) Open Folder", "Open in Finder/Explorer"),
            ("(r) Refresh", "Refresh folder summary"),
            ("(f) Find Files", "Search for files"),
            ("(g) Organize", "Auto-organize by type"),
            ("(c) Cleanup", "Suggest old files for cleanup"),
        ]

        for shortcut, description in actions:
            menu_text.append(f"  {shortcut}", style="green")
            menu_text.append(f" - {description}\n", style="dim")

        return Panel(
            menu_text, title="[bold green]⚡ QUICK ACCESS[/bold green]", border_style="green"
        )


class FolderDashboardPane(Static):
    """
    Complete folder management dashboard pane.

    Combines:
    - Folder summary
    - Recent events
    - Quick access actions
    """

    def __init__(self, folder_manager: FolderManager, config: dict):
        super().__init__()
        self.folder_manager = folder_manager
        self.config = config

        # Widgets
        self.summary_widget = FolderSummaryWidget(folder_manager)
        self.events_widget = FolderEventsWidget(max_events=10)
        self.quick_access_widget = QuickAccessWidget(folder_manager)

        # Start watching folders if enabled
        if config.get("watcher", {}).get("enabled", True):
            self._start_watching()

    def _start_watching(self):
        """Start watching configured folders."""
        folders = self.config.get("folders", {})

        for name, folder_config in folders.items():
            if folder_config.get("watch", False):
                try:
                    self.folder_manager.start_watching(name, callback=self._on_file_event)
                    logger.info(f"Watching folder: {name}")
                except Exception as e:
                    logger.error(f"Failed to watch folder {name}: {e}")

    def _on_file_event(self, event: FileEvent):
        """
        Handle file system event.

        Args:
            event: File system event
        """
        # Add to events widget
        self.events_widget.add_event(event)

        # Optional voice notification
        if self.config.get("notifications", {}).get("voice_notifications", False):
            if event.action.value == "created":
                # Notify about new files
                asyncio.create_task(self._notify_new_file(event))

    async def _notify_new_file(self, event: FileEvent):
        """
        Notify about new file creation.

        Args:
            event: File system event
        """
        # TODO: Integrate with voice handler
        logger.info(f"New file created: {event.path.name}")

    def compose(self):
        """Compose dashboard layout."""
        yield self.summary_widget
        yield self.events_widget
        yield self.quick_access_widget

    async def on_key(self, event):
        """Handle keyboard shortcuts."""
        key = event.key.lower()

        if key == "o":
            # Open folder in file manager
            await self._open_folder()
        elif key == "r":
            # Refresh summary
            await self.summary_widget.refresh_summary()
        elif key == "f":
            # Find files (TODO: implement search dialog)
            pass
        elif key == "g":
            # Organize files
            await self._organize_files()
        elif key == "c":
            # Cleanup suggestions
            await self._suggest_cleanup()

    async def _open_folder(self):
        """Open current folder in file manager."""
        import subprocess
        import sys

        folder = self.folder_manager.get_folder(self.summary_widget.current_folder)

        if folder:
            if sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])
            elif sys.platform == "linux":
                subprocess.Popen(["xdg-open", str(folder)])
            elif sys.platform == "win32":
                subprocess.Popen(["explorer", str(folder)])

    async def _organize_files(self):
        """Auto-organize files by extension."""
        # Show preview first
        organized = await self.folder_manager.organize_by_extension(
            self.summary_widget.current_folder, dry_run=True
        )

        logger.info(f"Would organize {sum(len(files) for files in organized.values())} files")

        # TODO: Show confirmation dialog before actually organizing

    async def _suggest_cleanup(self):
        """Suggest files for cleanup."""
        summary = self.summary_widget.summary
        if summary and summary.old_files:
            logger.info(f"Suggest cleaning up {len(summary.old_files)} old files")
            # TODO: Show cleanup dialog


# Example integration
async def demo():
    """Demonstrate folder dashboard."""
    from textual.app import App

    class FolderDashboardApp(App):
        def compose(self):
            # Load config
            config = {
                "folders": {"downloads": {"path": "~/Downloads", "watch": True}},
                "watcher": {"enabled": True},
            }

            manager = FolderManager(config)
            pane = FolderDashboardPane(manager, config)

            yield pane

    app = FolderDashboardApp()
    app.run()


if __name__ == "__main__":
    asyncio.run(demo())
