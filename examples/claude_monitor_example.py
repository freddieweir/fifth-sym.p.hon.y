#!/usr/bin/env python3
"""
Fifth Symphony - Claude Code Monitoring Example

Demonstrates real-time monitoring of Claude Code activity with:
- Avatar LED indicators
- Voice notifications (optional)
- Activity logging
- Statistics tracking

Run this while using Claude Code in the fifth-symphony project to see
real-time feedback about what Claude is doing.
"""

import signal
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QTextEdit, QVBoxLayout, QWidget

from modules.claude_integration import ClaudeIntegration
from modules.visual_novel_widget import VisualNovelWidget


class ClaudeMonitorDemo(QMainWindow):
    """
    Demonstration of Claude Code monitoring.

    Shows:
    - Avatar with LED indicators
    - Activity log
    - Statistics
    """

    def __init__(self):
        super().__init__()

        # Initialize components
        self.avatar = VisualNovelWidget(always_on_top=True)
        self.avatar.resize(400, 500)

        # Claude Code integration (voice disabled for demo)
        self.claude_integration = ClaudeIntegration(
            avatar=self.avatar,
            voice=None,  # Set to voice_handler to enable voice
            enable_voice=False
        )

        # Setup UI
        self._setup_ui()

        # Connect event signals to activity log
        self._connect_event_signals()

        # Start monitoring
        self._start_monitoring()

        # Update statistics periodically
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self._update_statistics)
        self.stats_timer.start(2000)  # Update every 2 seconds

    def _setup_ui(self):
        """Setup user interface."""
        self.setWindowTitle("Fifth Symphony - Claude Code Monitor")
        self.resize(600, 400)

        # Main widget
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)

        # Title
        title = QLabel("🎭 Claude Code Activity Monitor")
        title.setStyleSheet("""
            QLabel {
                background-color: #2d2d2d;
                color: #00ffff;
                padding: 15px;
                font-size: 18px;
                font-weight: bold;
            }
        """)
        layout.addWidget(title)

        # Statistics label
        self.stats_label = QLabel("Initializing...")
        self.stats_label.setStyleSheet("""
            QLabel {
                background-color: #1e1e1e;
                color: #00ff00;
                padding: 10px;
                font-family: monospace;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.stats_label)

        # Activity log
        log_label = QLabel("📋 Activity Log")
        log_label.setStyleSheet("color: #ffffff; font-weight: bold; padding: 5px;")
        layout.addWidget(log_label)

        self.activity_log = QTextEdit()
        self.activity_log.setReadOnly(True)
        self.activity_log.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #00ff00;
                font-family: monospace;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.activity_log)

        # Instructions
        instructions = QLabel(
            "💡 Use Claude Code in fifth-symphony to see real-time monitoring!\n"
            "Watch the avatar LEDs change as Claude reads files, runs commands, etc."
        )
        instructions.setStyleSheet("""
            QLabel {
                background-color: #2d2d2d;
                color: #ffff00;
                padding: 10px;
                font-size: 11px;
            }
        """)
        layout.addWidget(instructions)

        self.log("Fifth Symphony Claude Code Monitor initialized")

    def _connect_event_signals(self):
        """Connect Claude integration signals to activity log."""
        # Connect each event type to log messages
        self.claude_integration.user_prompt_detected.connect(
            lambda event: self.log(f"🟣 User prompt: {event.summary}")
        )
        self.claude_integration.file_read_detected.connect(
            lambda event: self.log(f"📖 File read: {event.summary}")
        )
        self.claude_integration.file_write_detected.connect(
            lambda event: self.log(f"✍️  File written: {event.summary}")
        )
        self.claude_integration.file_edit_detected.connect(
            lambda event: self.log(f"✏️  File edited: {event.summary}")
        )
        self.claude_integration.bash_command_detected.connect(
            lambda event: self.log(f"⚡ Bash command: {event.summary}")
        )
        self.claude_integration.assistant_response_detected.connect(
            lambda event: self.log("🔵 Claude responding...")
        )
        self.claude_integration.web_fetch_detected.connect(
            lambda event: self.log(f"🌐 Web fetch: {event.summary}")
        )

    def _start_monitoring(self):
        """Start Claude Code monitoring."""
        self.log("🔍 Starting Claude Code monitoring...")

        # Auto-detect session directory
        session_dir = Path.home() / ".claude" / "projects" / "-path-to-git-internal-repos-project-name"

        if not session_dir.exists():
            self.log(f"❌ Session directory not found: {session_dir}")
            self.log("   Make sure you've used Claude Code in this project at least once!")
            return

        self.claude_integration.start_monitoring(
            session_dir=session_dir,
            project_name="Fifth Symphony"
        )

        self.log(f"✅ Monitoring active: {session_dir.name}")
        self.log("")
        self.log("🎯 LED Indicator Guide:")
        self.log("  🔵 Blue LED = Claude responding/speaking")
        self.log("  🟡 Yellow LED = Processing (file operations, bash commands)")
        self.log("  🟣 Purple LED = User prompt or web fetch")
        self.log("")

    def _update_statistics(self):
        """Update statistics display."""
        stats = self.claude_integration.get_statistics()
        sessions = self.claude_integration.get_active_sessions()

        stats_text = f"""📊 Activity Statistics:
  User Prompts: {stats['user_prompts']}
  Files Read: {stats['files_read']}
  Files Written: {stats['files_written']}
  Files Edited: {stats['files_edited']}
  Bash Commands: {stats['bash_commands']}
  Web Fetches: {stats['web_fetches']}

🎭 Active Sessions: {len(sessions)}
"""

        self.stats_label.setText(stats_text)

    def log(self, message: str):
        """Add message to activity log."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.activity_log.append(f"[{timestamp}] {message}")

    def closeEvent(self, event):
        """Handle window close."""
        self.log("Stopping monitoring...")

        # Stop statistics timer
        self.stats_timer.stop()

        # Stop Claude monitoring
        try:
            self.claude_integration.stop_monitoring()
        except Exception as e:
            self.log(f"Error stopping monitor: {e}")

        # Close avatar
        try:
            self.avatar.close()
        except Exception as e:
            self.log(f"Error closing avatar: {e}")

        self.log("Cleanup complete")
        event.accept()


def main():
    """Run Claude Code monitor demo."""
    app = QApplication(sys.argv)

    # Create monitor window
    window = ClaudeMonitorDemo()
    window.show()

    # Show avatar
    window.avatar.show()

    # Setup signal handlers for clean shutdown
    def signal_handler(sig, frame):
        print("\n\n🛑 Shutting down...")
        window.close()
        app.quit()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Allow Ctrl+C to work with Qt
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(100)  # Process signals every 100ms

    print("=" * 70)
    print("Fifth Symphony - Claude Code Monitor")
    print("=" * 70)
    print()
    print("🎭 Monitor is running!")
    print()
    print("To test:")
    print("1. Open Claude Code in the fifth-symphony project")
    print("2. Ask Claude to read a file, run a command, or create something")
    print("3. Watch the avatar LEDs change in real-time")
    print()
    print("LED Guide:")
    print("  🔵 Blue LED = Claude responding")
    print("  🟡 Yellow LED = Processing/working")
    print("  🟣 Purple LED = User input or network activity")
    print()
    print("Press Ctrl+C or close window to stop")
    print("=" * 70)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
