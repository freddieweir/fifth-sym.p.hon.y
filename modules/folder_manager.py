"""
Folder Management System

Provides organized access to frequently used directories with:
- Real-time folder monitoring (watchdog)
- File organization helpers
- Quick access to common folders
- Attention-friendly folder summaries
- Automatic cleanup suggestions

Common folders:
- Resume folder
- Downloads folder
- Project directories
- Custom watched folders
"""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

try:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers import Observer

    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    logging.warning("watchdog not available - folder monitoring disabled")

logger = logging.getLogger(__name__)


class FileAction(Enum):
    """File system action types."""

    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"


@dataclass
class FileEvent:
    """
    File system event data.

    Attributes:
        action: Type of action (created, modified, deleted, moved)
        path: Path to file/folder
        is_directory: Whether event is for directory
        timestamp: When event occurred
        metadata: Optional additional metadata
    """

    action: FileAction
    path: Path
    is_directory: bool
    timestamp: datetime
    metadata: dict[str, Any] | None = None


@dataclass
class FolderSummary:
    """
    Summary of folder contents.

    Attributes:
        path: Folder path
        total_files: Total number of files
        total_size: Total size in bytes
        file_types: Count by file extension
        recent_files: Recently modified files
        old_files: Files not modified in 30+ days
        large_files: Files > 10MB
    """

    path: Path
    total_files: int
    total_size: int
    file_types: dict[str, int]
    recent_files: list[Path]
    old_files: list[Path]
    large_files: list[Path]


class FolderWatcher(FileSystemEventHandler):
    """
    Watches folder for file system events.

    Integrates with watchdog for real-time monitoring.
    """

    def __init__(self, folder_path: Path, callback: Callable[[FileEvent], None] | None = None):
        """
        Initialize folder watcher.

        Args:
            folder_path: Path to watch
            callback: Function to call on file events
        """
        super().__init__()
        self.folder_path = folder_path
        self.callback = callback

    def on_created(self, event: FileSystemEvent):
        """Handle file/folder creation."""
        self._handle_event(FileAction.CREATED, event)

    def on_modified(self, event: FileSystemEvent):
        """Handle file/folder modification."""
        self._handle_event(FileAction.MODIFIED, event)

    def on_deleted(self, event: FileSystemEvent):
        """Handle file/folder deletion."""
        self._handle_event(FileAction.DELETED, event)

    def on_moved(self, event: FileSystemEvent):
        """Handle file/folder move."""
        self._handle_event(FileAction.MOVED, event)

    def _handle_event(self, action: FileAction, event: FileSystemEvent):
        """
        Process file system event.

        Args:
            action: Type of action
            event: Watchdog event object
        """
        file_event = FileEvent(
            action=action,
            path=Path(event.src_path),
            is_directory=event.is_directory,
            timestamp=datetime.now(),
            metadata={"event_type": event.event_type},
        )

        if self.callback:
            self.callback(file_event)


class FolderManager:
    """
    Manages access to frequently used folders.

    Features:
    - Folder watching with real-time notifications
    - File organization helpers
    - Folder summaries
    - Cleanup suggestions
    - Quick file access
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize folder manager.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.watched_folders: dict[str, Path] = {}
        self.observers: dict[str, Observer] = {}
        self.event_callbacks: dict[str, list[Callable]] = {}

        # Load configured folders
        self._load_configured_folders()

    def _load_configured_folders(self):
        """Load folders from configuration."""
        folders = self.config.get("folders", {})

        for name, path_str in folders.items():
            path = Path(path_str).expanduser()
            if path.exists():
                self.watched_folders[name] = path
                logger.info(f"Loaded folder: {name} -> {path}")
            else:
                logger.warning(f"Folder not found: {name} -> {path}")

    def add_folder(self, name: str, path: Path, watch: bool = False):
        """
        Add folder to managed folders.

        Args:
            name: Folder identifier
            path: Path to folder
            watch: Whether to watch for changes
        """
        if not path.exists():
            raise FileNotFoundError(f"Folder not found: {path}")

        if not path.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")

        self.watched_folders[name] = path
        logger.info(f"Added folder: {name} -> {path}")

        if watch and WATCHDOG_AVAILABLE:
            self.start_watching(name)

    def remove_folder(self, name: str):
        """
        Remove folder from management.

        Args:
            name: Folder identifier
        """
        if name in self.watched_folders:
            # Stop watching if active
            if name in self.observers:
                self.stop_watching(name)

            del self.watched_folders[name]
            logger.info(f"Removed folder: {name}")

    def get_folder(self, name: str) -> Path | None:
        """
        Get path to managed folder.

        Args:
            name: Folder identifier

        Returns:
            Path to folder or None if not found
        """
        return self.watched_folders.get(name)

    def list_folders(self) -> dict[str, Path]:
        """
        Get all managed folders.

        Returns:
            Dictionary of folder names to paths
        """
        return self.watched_folders.copy()

    def start_watching(self, name: str, callback: Callable[[FileEvent], None] | None = None):
        """
        Start watching folder for changes.

        Args:
            name: Folder identifier
            callback: Optional callback for file events
        """
        if not WATCHDOG_AVAILABLE:
            logger.warning("watchdog not available - cannot watch folders")
            return

        if name not in self.watched_folders:
            raise ValueError(f"Unknown folder: {name}")

        if name in self.observers:
            logger.warning(f"Already watching: {name}")
            return

        folder_path = self.watched_folders[name]

        # Create watcher
        watcher = FolderWatcher(folder_path, callback)

        # Create observer
        observer = Observer()
        observer.schedule(watcher, str(folder_path), recursive=True)
        observer.start()

        self.observers[name] = observer
        logger.info(f"Started watching: {name} ({folder_path})")

    def stop_watching(self, name: str):
        """
        Stop watching folder.

        Args:
            name: Folder identifier
        """
        if name in self.observers:
            observer = self.observers[name]
            observer.stop()
            observer.join(timeout=5)
            del self.observers[name]
            logger.info(f"Stopped watching: {name}")

    def stop_all_watching(self):
        """Stop watching all folders."""
        for name in list(self.observers.keys()):
            self.stop_watching(name)

    async def get_folder_summary(
        self, name: str, recent_days: int = 7, old_days: int = 30, large_file_mb: int = 10
    ) -> FolderSummary:
        """
        Get summary of folder contents.

        Args:
            name: Folder identifier
            recent_days: Days to consider file "recent"
            old_days: Days to consider file "old"
            large_file_mb: Size in MB to consider file "large"

        Returns:
            FolderSummary object
        """
        if name not in self.watched_folders:
            raise ValueError(f"Unknown folder: {name}")

        folder_path = self.watched_folders[name]

        # Collect file statistics
        total_files = 0
        total_size = 0
        file_types: dict[str, int] = {}
        recent_files: list[Path] = []
        old_files: list[Path] = []
        large_files: list[Path] = []

        recent_threshold = datetime.now() - timedelta(days=recent_days)
        old_threshold = datetime.now() - timedelta(days=old_days)
        large_threshold = large_file_mb * 1024 * 1024  # Convert to bytes

        # Walk directory
        for item in folder_path.rglob("*"):
            if item.is_file():
                total_files += 1

                # Size
                size = item.stat().st_size
                total_size += size

                # File type
                ext = item.suffix.lower() or "no_extension"
                file_types[ext] = file_types.get(ext, 0) + 1

                # Modification time
                mtime = datetime.fromtimestamp(item.stat().st_mtime)

                # Recent files
                if mtime > recent_threshold:
                    recent_files.append(item)

                # Old files
                if mtime < old_threshold:
                    old_files.append(item)

                # Large files
                if size > large_threshold:
                    large_files.append(item)

        # Sort lists
        recent_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        old_files.sort(key=lambda p: p.stat().st_mtime)
        large_files.sort(key=lambda p: p.stat().st_size, reverse=True)

        return FolderSummary(
            path=folder_path,
            total_files=total_files,
            total_size=total_size,
            file_types=file_types,
            recent_files=recent_files[:10],  # Top 10 most recent
            old_files=old_files[:10],  # Top 10 oldest
            large_files=large_files[:10],  # Top 10 largest
        )

    async def find_files(self, name: str, pattern: str = "*", max_results: int = 100) -> list[Path]:
        """
        Find files in folder matching pattern.

        Args:
            name: Folder identifier
            pattern: Glob pattern (e.g., "*.pdf", "resume_*")
            max_results: Maximum number of results

        Returns:
            List of matching file paths
        """
        if name not in self.watched_folders:
            raise ValueError(f"Unknown folder: {name}")

        folder_path = self.watched_folders[name]
        matches = list(folder_path.rglob(pattern))[:max_results]

        return matches

    async def organize_by_extension(self, name: str, dry_run: bool = True) -> dict[str, list[Path]]:
        """
        Organize files into folders by extension.

        Args:
            name: Folder identifier
            dry_run: If True, don't actually move files

        Returns:
            Dictionary of extension to list of files
        """
        if name not in self.watched_folders:
            raise ValueError(f"Unknown folder: {name}")

        folder_path = self.watched_folders[name]
        organized: dict[str, list[Path]] = {}

        for item in folder_path.iterdir():
            if item.is_file():
                ext = item.suffix.lower() or "no_extension"

                if ext not in organized:
                    organized[ext] = []

                organized[ext].append(item)

                if not dry_run:
                    # Create extension folder if needed
                    ext_folder = folder_path / ext.lstrip(".")
                    ext_folder.mkdir(exist_ok=True)

                    # Move file
                    new_path = ext_folder / item.name
                    item.rename(new_path)
                    logger.info(f"Moved: {item} -> {new_path}")

        return organized

    def format_size(self, size_bytes: int) -> str:
        """
        Format file size in human-readable format.

        Args:
            size_bytes: Size in bytes

        Returns:
            Formatted string (e.g., "1.5 MB")
        """
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"


# Example usage
async def demo():
    """Demonstrate folder management."""
    manager = FolderManager()

    # Add folders
    downloads = Path.home() / "Downloads"
    if downloads.exists():
        manager.add_folder("downloads", downloads)

        # Get summary
        summary = await manager.get_folder_summary("downloads")
        print("\n=== Downloads Summary ===")
        print(f"Total files: {summary.total_files}")
        print(f"Total size: {manager.format_size(summary.total_size)}")
        print("\nFile types:")
        for ext, count in sorted(summary.file_types.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {ext}: {count} files")

        print(f"\nRecent files ({len(summary.recent_files)}):")
        for path in summary.recent_files[:5]:
            print(f"  {path.name}")

        print(f"\nOld files ({len(summary.old_files)}):")
        for path in summary.old_files[:5]:
            print(f"  {path.name}")


if __name__ == "__main__":
    asyncio.run(demo())
