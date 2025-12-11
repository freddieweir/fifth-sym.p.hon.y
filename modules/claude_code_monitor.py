"""
Claude Code session monitoring module.

Monitors Claude Code activity via session JSONL files and filesystem events.
Provides real-time notifications about Claude's actions (file reads, edits, bash commands, etc.)
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Callable, List
from datetime import datetime
from enum import Enum
from queue import Queue
import threading

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

logger = logging.getLogger(__name__)


class ClaudeEventType(Enum):
    """Types of Claude Code events."""

    USER_PROMPT = "user"
    ASSISTANT_RESPONSE = "assistant"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_EDIT = "file_edit"
    BASH_COMMAND = "bash_command"
    WEB_FETCH = "web_fetch"
    ERROR = "error"


class ClaudeEvent:
    """
    Represents a Claude Code activity event.

    Attributes:
        event_type: Type of event
        timestamp: When the event occurred
        session_id: Claude Code session identifier
        data: Event-specific data
        summary: Human-readable summary
    """

    def __init__(
        self,
        event_type: ClaudeEventType,
        timestamp: datetime,
        session_id: str,
        data: Dict,
        summary: str,
    ):
        self.event_type = event_type
        self.timestamp = timestamp
        self.session_id = session_id
        self.data = data
        self.summary = summary

    def __repr__(self) -> str:
        return f"<ClaudeEvent {self.event_type.value}: {self.summary}>"


class SessionFileHandler(FileSystemEventHandler):
    """Watches Claude Code session files for changes."""

    def __init__(self, callback: Callable[[Path], None]):
        super().__init__()
        self.callback = callback
        self._processing = set()
        self._lock = threading.Lock()

    def on_modified(self, event: FileSystemEvent):
        """Handle session file modification."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Only process .jsonl session files
        if file_path.suffix != ".jsonl":
            return

        # Prevent duplicate processing (thread-safe)
        with self._lock:
            if file_path in self._processing:
                return
            self._processing.add(file_path)

        try:
            # Call synchronously from watchdog thread
            self.callback(file_path)
        finally:
            # Schedule cleanup with timer (no asyncio needed)
            timer = threading.Timer(0.5, self._cleanup_processing, [file_path])
            timer.daemon = True
            timer.start()

    def _cleanup_processing(self, file_path: Path):
        """Remove file from processing set after delay."""
        with self._lock:
            self._processing.discard(file_path)


class ClaudeCodeMonitor:
    """
    Monitor Claude Code session activity.

    Features:
    - Real-time session file monitoring
    - Event parsing and classification
    - Callback notifications for specific event types
    - Session history tracking

    Example:
        monitor = ClaudeCodeMonitor()
        monitor.add_callback(ClaudeEventType.FILE_WRITE, on_file_written)
        monitor.start_monitoring("~/.claude/projects/...")
    """

    def __init__(self):
        self.callbacks: Dict[ClaudeEventType, List[Callable]] = {}
        self.observer: Optional[Observer] = None
        self.last_processed_line: Dict[Path, int] = {}
        self.active_sessions: Dict[str, Dict] = {}

    def add_callback(self, event_type: ClaudeEventType, callback: Callable):
        """
        Register callback for specific event type.

        Args:
            event_type: Type of event to listen for
            callback: Async function to call when event occurs
                     Signature: async def callback(event: ClaudeEvent)
        """
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []

        self.callbacks[event_type].append(callback)
        logger.info(f"Registered callback for {event_type.value} events")

    def start_monitoring(self, session_dir: Path, project_name: Optional[str] = None):
        """
        Start monitoring Claude Code session directory.

        Args:
            session_dir: Path to Claude Code project session directory
                        (e.g., ~/.claude/projects/-path-to-git-internal-repos-project-name)
            project_name: Optional project name for display
        """
        session_dir = Path(session_dir)

        if not session_dir.exists():
            logger.error(f"Session directory does not exist: {session_dir}")
            return

        logger.info(f"Starting Claude Code monitor for: {project_name or session_dir.name}")

        # Setup file watcher
        event_handler = SessionFileHandler(callback=self._on_file_modified)

        self.observer = Observer()
        self.observer.schedule(event_handler, str(session_dir), recursive=False)
        self.observer.start()

        logger.info(f"Monitoring active: {session_dir}")

    def stop_monitoring(self):
        """Stop monitoring session files."""
        if self.observer:
            try:
                self.observer.stop()
                self.observer.join(timeout=2.0)  # Wait max 2 seconds
                logger.info("Stopped Claude Code monitoring")
            except Exception as e:
                logger.warning(f"Error stopping observer: {e}")
            finally:
                self.observer = None

    def _on_file_modified(self, file_path: Path):
        """Handle session file modification (called from watchdog thread)."""
        # Parse synchronously from watchdog thread
        # This is safe because we're only reading files
        self._parse_session_file_sync(file_path)

    def _parse_session_file_sync(self, file_path: Path):
        """
        Parse session JSONL file for new events.

        Args:
            file_path: Path to session .jsonl file
        """
        try:
            # Get last processed line index
            last_line = self.last_processed_line.get(file_path, 0)

            # Read new lines only
            with open(file_path, "r") as f:
                lines = f.readlines()

            new_lines = lines[last_line:]

            if not new_lines:
                return

            # Update last processed line
            self.last_processed_line[file_path] = len(lines)

            # Parse each new line
            for line in new_lines:
                try:
                    entry = json.loads(line.strip())
                    self._process_session_entry(entry)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in session file: {line[:100]}")
                    continue

        except Exception as e:
            logger.error(f"Error parsing session file: {e}")

    def _process_session_entry(self, entry: Dict):
        """
        Process individual session entry and generate events.

        Args:
            entry: Parsed JSONL entry
        """
        entry_type = entry.get("type")
        session_id = entry.get("sessionId", "unknown")
        timestamp_str = entry.get("timestamp")

        if not timestamp_str:
            return

        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

        # Update active session tracking
        self.active_sessions[session_id] = {
            "last_activity": timestamp,
            "cwd": entry.get("cwd"),
            "branch": entry.get("gitBranch"),
        }

        # Parse user prompts
        if entry_type == "user":
            message = entry.get("message", {})
            content = message.get("content", [])

            # Check for user text prompt
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text", "")
                    event = ClaudeEvent(
                        event_type=ClaudeEventType.USER_PROMPT,
                        timestamp=timestamp,
                        session_id=session_id,
                        data={"prompt": text},
                        summary=f"User: {text[:80]}{'...' if len(text) > 80 else ''}",
                    )
                    self._notify_callbacks(event)

                # Check for tool results (File reads, bash output, etc.)
                elif isinstance(item, dict) and item.get("type") == "tool_result":
                    self._process_tool_result(item, timestamp, session_id)

        # Parse assistant responses
        elif entry_type == "assistant":
            message = entry.get("message", {})
            content = message.get("content", [])

            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        text = item.get("text", "")
                        event = ClaudeEvent(
                            event_type=ClaudeEventType.ASSISTANT_RESPONSE,
                            timestamp=timestamp,
                            session_id=session_id,
                            data={"response": text},
                            summary=f"Claude: {text[:80]}{'...' if len(text) > 80 else ''}",
                        )
                        self._notify_callbacks(event)

                    elif item.get("type") == "tool_use":
                        self._process_tool_use(item, timestamp, session_id)

    def _process_tool_result(self, tool_result: Dict, timestamp: datetime, session_id: str):
        """Process tool result entries."""
        content = tool_result.get("content", "")

        # File read detection
        if isinstance(content, str) and content.startswith("     1→"):
            # This is a file read (cat -n format)
            lines = content.split("\n")
            num_lines = len([line for line in lines if line.strip()])

            event = ClaudeEvent(
                event_type=ClaudeEventType.FILE_READ,
                timestamp=timestamp,
                session_id=session_id,
                data={"content": content, "num_lines": num_lines},
                summary=f"Read file ({num_lines} lines)",
            )
            self._notify_callbacks(event)

        # Bash command output
        elif "stdout" in str(content) or "stderr" in str(content):
            event = ClaudeEvent(
                event_type=ClaudeEventType.BASH_COMMAND,
                timestamp=timestamp,
                session_id=session_id,
                data={"output": content},
                summary="Bash command executed",
            )
            self._notify_callbacks(event)

    def _process_tool_use(self, tool_use: Dict, timestamp: datetime, session_id: str):
        """Process tool use entries."""
        tool_name = tool_use.get("name", "")
        tool_input = tool_use.get("input", {})

        # File operations
        if tool_name == "Read":
            file_path = tool_input.get("file_path", "")
            event = ClaudeEvent(
                event_type=ClaudeEventType.FILE_READ,
                timestamp=timestamp,
                session_id=session_id,
                data={"file_path": file_path},
                summary=f"Reading: {Path(file_path).name}",
            )
            self._notify_callbacks(event)

        elif tool_name == "Write":
            file_path = tool_input.get("file_path", "")
            event = ClaudeEvent(
                event_type=ClaudeEventType.FILE_WRITE,
                timestamp=timestamp,
                session_id=session_id,
                data={"file_path": file_path},
                summary=f"Writing: {Path(file_path).name}",
            )
            self._notify_callbacks(event)

        elif tool_name == "Edit":
            file_path = tool_input.get("file_path", "")
            event = ClaudeEvent(
                event_type=ClaudeEventType.FILE_EDIT,
                timestamp=timestamp,
                session_id=session_id,
                data={"file_path": file_path},
                summary=f"Editing: {Path(file_path).name}",
            )
            self._notify_callbacks(event)

        elif tool_name == "Bash":
            command = tool_input.get("command", "")
            event = ClaudeEvent(
                event_type=ClaudeEventType.BASH_COMMAND,
                timestamp=timestamp,
                session_id=session_id,
                data={"command": command},
                summary=f"Running: {command[:50]}{'...' if len(command) > 50 else ''}",
            )
            self._notify_callbacks(event)

        elif tool_name == "WebFetch":
            url = tool_input.get("url", "")
            event = ClaudeEvent(
                event_type=ClaudeEventType.WEB_FETCH,
                timestamp=timestamp,
                session_id=session_id,
                data={"url": url},
                summary=f"Fetching: {url}",
            )
            self._notify_callbacks(event)

    def _notify_callbacks(self, event: ClaudeEvent):
        """
        Notify registered callbacks about event.

        Note: Called from watchdog thread, so we can't use await.
        For async callbacks, we schedule them in the event loop if available.

        Args:
            event: Claude Code event
        """
        callbacks = self.callbacks.get(event.event_type, [])

        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    # Try to schedule in event loop if one exists
                    try:
                        loop = asyncio.get_running_loop()
                        loop.call_soon_threadsafe(asyncio.create_task, callback(event))
                    except RuntimeError:
                        # No event loop running, skip async callback
                        logger.warning(
                            f"Cannot call async callback {callback.__name__} - no event loop"
                        )
                else:
                    # Synchronous callback - call directly
                    callback(event)
            except Exception as e:
                logger.error(f"Error in callback for {event.event_type.value}: {e}")

    def get_active_sessions(self) -> Dict[str, Dict]:
        """
        Get currently active Claude Code sessions.

        Returns:
            Dict mapping session IDs to session metadata
        """
        return self.active_sessions.copy()
