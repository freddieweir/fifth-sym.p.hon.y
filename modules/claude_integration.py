"""
Claude Code integration for Fifth Symphony.

Connects Claude Code monitoring with avatar visuals and voice feedback.
Provides real-time awareness of Claude's activities.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QTimer, QObject, Signal

from modules.claude_code_monitor import ClaudeCodeMonitor, ClaudeEvent, ClaudeEventType

# Optional imports (may not be available in all contexts)
try:
    from modules.visualization_widget import VisualNovelWidget, AvatarState

    AVATAR_AVAILABLE = True
except ImportError:
    AVATAR_AVAILABLE = False

try:
    from modules.voice_handler import VoiceHandler

    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

logger = logging.getLogger(__name__)


class ClaudeIntegration(QObject):
    """
    Integrate Claude Code monitoring with Fifth Symphony feedback systems.

    Features:
    - Avatar LED indicators for Claude activity
    - Voice announcements for significant events
    - Activity logging and statistics

    Example:
        integration = ClaudeIntegration(avatar=avatar_widget, voice=voice_handler)
        integration.start_monitoring(session_dir)
    """

    # Qt Signals (thread-safe communication from watchdog thread to main thread)
    user_prompt_detected = Signal(object)  # ClaudeEvent
    file_read_detected = Signal(object)
    file_write_detected = Signal(object)
    file_edit_detected = Signal(object)
    bash_command_detected = Signal(object)
    assistant_response_detected = Signal(object)
    web_fetch_detected = Signal(object)

    def __init__(
        self,
        avatar: Optional["VisualNovelWidget"] = None,
        voice: Optional["VoiceHandler"] = None,
        enable_voice: bool = False,
    ):
        """
        Initialize Claude Code integration.

        Args:
            avatar: Visual novel widget for LED indicators
            voice: Voice handler for audio feedback
            enable_voice: Enable voice announcements (can be noisy)
        """
        super().__init__()  # Initialize QObject

        self.avatar = avatar
        self.voice = voice
        self.enable_voice = enable_voice

        # Initialize monitor
        self.monitor = ClaudeCodeMonitor()

        # Register callbacks (these emit signals from watchdog thread)
        self._register_callbacks()

        # Connect signals to handlers (handlers run in main thread)
        self._connect_signals()

        # Activity statistics
        self.stats = {
            "user_prompts": 0,
            "files_read": 0,
            "files_written": 0,
            "files_edited": 0,
            "bash_commands": 0,
            "web_fetches": 0,
        }

        logger.info("Claude Code integration initialized")

    def _register_callbacks(self):
        """Register event callbacks with monitor (emit signals from watchdog thread)."""

        # User prompts - Emit signal (thread-safe)
        self.monitor.add_callback(
            ClaudeEventType.USER_PROMPT, lambda event: self.user_prompt_detected.emit(event)
        )

        # File operations - Emit signals
        self.monitor.add_callback(
            ClaudeEventType.FILE_READ, lambda event: self.file_read_detected.emit(event)
        )
        self.monitor.add_callback(
            ClaudeEventType.FILE_WRITE, lambda event: self.file_write_detected.emit(event)
        )
        self.monitor.add_callback(
            ClaudeEventType.FILE_EDIT, lambda event: self.file_edit_detected.emit(event)
        )

        # Bash commands - Emit signal
        self.monitor.add_callback(
            ClaudeEventType.BASH_COMMAND, lambda event: self.bash_command_detected.emit(event)
        )

        # Assistant responses - Emit signal
        self.monitor.add_callback(
            ClaudeEventType.ASSISTANT_RESPONSE,
            lambda event: self.assistant_response_detected.emit(event),
        )

        # Web fetches - Emit signal
        self.monitor.add_callback(
            ClaudeEventType.WEB_FETCH, lambda event: self.web_fetch_detected.emit(event)
        )

    def _connect_signals(self):
        """Connect signals to handlers (handlers run in main thread)."""
        self.user_prompt_detected.connect(self._handle_user_prompt)
        self.file_read_detected.connect(self._handle_file_read)
        self.file_write_detected.connect(self._handle_file_write)
        self.file_edit_detected.connect(self._handle_file_edit)
        self.bash_command_detected.connect(self._handle_bash_command)
        self.assistant_response_detected.connect(self._handle_assistant_response)
        self.web_fetch_detected.connect(self._handle_web_fetch)

    # =========================================================================
    # Event Handlers (run in main thread via Qt signals)
    # =========================================================================

    def _handle_user_prompt(self, event: ClaudeEvent):
        """Handle user prompt event (runs in main thread)."""
        self.stats["user_prompts"] += 1
        logger.info(f"User prompt: {event.summary}")

        # Flash purple LED - now safe to use QTimer
        if self.avatar:
            self.avatar.set_led("special", True, pulsing=True)
            QTimer.singleShot(1000, lambda: self.avatar.set_led("special", False))

    def _handle_file_read(self, event: ClaudeEvent):
        """Handle file read event (runs in main thread)."""
        self.stats["files_read"] += 1
        logger.info(f"Claude reading: {event.summary}")

        # Show processing LED - safe in main thread
        if self.avatar:
            self.avatar.set_led("processing", True, pulsing=True)
            self.avatar.set_state(AvatarState.PROCESSING)
            QTimer.singleShot(
                500,
                lambda: (
                    self.avatar.set_led("processing", False),
                    self.avatar.set_state(AvatarState.IDLE),
                ),
            )

    def _handle_file_write(self, event: ClaudeEvent):
        """Handle file write event (runs in main thread)."""
        self.stats["files_written"] += 1
        logger.info(f"Claude writing: {event.summary}")

        if self.avatar:
            self.avatar.set_led("processing", True, pulsing=True)
            self.avatar.set_state(AvatarState.PROCESSING)
            QTimer.singleShot(
                1000,
                lambda: (
                    self.avatar.set_led("processing", False),
                    self.avatar.set_state(AvatarState.IDLE),
                ),
            )

    def _handle_file_edit(self, event: ClaudeEvent):
        """Handle file edit event (runs in main thread)."""
        self.stats["files_edited"] += 1
        logger.info(f"Claude editing: {event.summary}")

        if self.avatar:
            self.avatar.set_led("processing", True, pulsing=True)
            self.avatar.set_state(AvatarState.PROCESSING)
            QTimer.singleShot(
                800,
                lambda: (
                    self.avatar.set_led("processing", False),
                    self.avatar.set_state(AvatarState.IDLE),
                ),
            )

    def _handle_bash_command(self, event: ClaudeEvent):
        """Handle bash command event (runs in main thread)."""
        self.stats["bash_commands"] += 1
        logger.info(f"Claude running: {event.summary}")

        if self.avatar:
            self.avatar.set_led("processing", True, pulsing=True)
            QTimer.singleShot(500, lambda: self.avatar.set_led("processing", False))

    def _handle_assistant_response(self, event: ClaudeEvent):
        """Handle assistant response event (runs in main thread)."""
        logger.debug(f"Claude responding: {event.summary}")

        if self.avatar:
            self.avatar.set_led("voice", True, pulsing=True)
            self.avatar.set_state(AvatarState.TALKING)
            QTimer.singleShot(
                1500,
                lambda: (
                    self.avatar.set_led("voice", False),
                    self.avatar.set_state(AvatarState.IDLE),
                ),
            )

    def _handle_web_fetch(self, event: ClaudeEvent):
        """Handle web fetch event (runs in main thread)."""
        self.stats["web_fetches"] += 1
        logger.info(f"Claude fetching: {event.summary}")

        if self.avatar:
            self.avatar.set_led("special", True, pulsing=True)
            QTimer.singleShot(1000, lambda: self.avatar.set_led("special", False))

    # =========================================================================
    # Control Methods
    # =========================================================================

    def start_monitoring(
        self, session_dir: Optional[Path] = None, project_name: Optional[str] = None
    ):
        """
        Start monitoring Claude Code sessions.

        Args:
            session_dir: Path to Claude Code project session directory
                        If None, auto-detects current project
            project_name: Display name for project
        """
        if session_dir is None:
            # Auto-detect session directory for fifth-symphony
            session_dir = (
                Path.home()
                / ".claude"
                / "projects"
                / "-path-to-git-internal-repos-project-name"
            )

        if not session_dir.exists():
            logger.error(f"Claude Code session directory not found: {session_dir}")
            logger.info("Make sure Claude Code has been run in this project at least once")
            return

        self.monitor.start_monitoring(session_dir, project_name or "Fifth Symphony")

        logger.info(f"🎭 Claude Code monitoring active: {project_name or 'Fifth Symphony'}")

        # Initial avatar state (safe - called from main thread during initialization)
        if self.avatar:
            self.avatar.set_state(AvatarState.LISTENING)

    def stop_monitoring(self):
        """Stop monitoring Claude Code sessions."""
        self.monitor.stop_monitoring()

        logger.info("Claude Code monitoring stopped")

        # Reset avatar (safe - called from main thread)
        if self.avatar:
            self.avatar.set_state(AvatarState.IDLE)
            for led_name in ["voice", "processing", "special"]:
                self.avatar.set_led(led_name, False)

    def get_statistics(self) -> dict:
        """
        Get activity statistics.

        Returns:
            Dict with event counts
        """
        return self.stats.copy()

    def get_active_sessions(self) -> dict:
        """
        Get active Claude Code sessions.

        Returns:
            Dict mapping session IDs to metadata
        """
        return self.monitor.get_active_sessions()
