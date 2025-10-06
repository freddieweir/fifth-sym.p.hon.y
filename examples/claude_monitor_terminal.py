#!/usr/bin/env python3
"""
Fifth Symphony - Claude Code Terminal Monitor

Terminal-only version of Claude Code monitoring.
No GUI, just clean terminal output with activity logging.

Run this to see Claude's activities in real-time without the avatar window.
"""

import signal
import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.claude_code_monitor import ClaudeCodeMonitor, ClaudeEvent, ClaudeEventType


class TerminalMonitor:
    """Terminal-only Claude Code monitor."""

    def __init__(self):
        self.monitor = ClaudeCodeMonitor()
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

    def _log(self, message: str, icon: str = "•"):
        """Print timestamped message."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {icon} {message}")

    def _on_user_prompt(self, event: ClaudeEvent):
        """Handle user prompt."""
        self.stats["user_prompts"] += 1
        self._log(f"User prompt: {event.summary}", "🟣")

    def _on_file_read(self, event: ClaudeEvent):
        """Handle file read."""
        self.stats["files_read"] += 1
        self._log(f"File read: {event.summary}", "📖")

    def _on_file_write(self, event: ClaudeEvent):
        """Handle file write."""
        self.stats["files_written"] += 1
        self._log(f"File written: {event.summary}", "✍️")

    def _on_file_edit(self, event: ClaudeEvent):
        """Handle file edit."""
        self.stats["files_edited"] += 1
        self._log(f"File edited: {event.summary}", "✏️")

    def _on_bash_command(self, event: ClaudeEvent):
        """Handle bash command."""
        self.stats["bash_commands"] += 1
        self._log(f"Bash command: {event.summary}", "⚡")

    def _on_web_fetch(self, event: ClaudeEvent):
        """Handle web fetch."""
        self.stats["web_fetches"] += 1
        self._log(f"Web fetch: {event.summary}", "🌐")

    def _on_assistant_response(self, event: ClaudeEvent):
        """Handle assistant response."""
        self.stats["assistant_responses"] += 1
        self._log("Claude responding...", "🔵")

    def start_monitoring(self, session_dir: Path = None):
        """Start monitoring Claude Code sessions."""
        if session_dir is None:
            # Auto-detect session directory
            session_dir = Path.home() / ".claude" / "projects" / "-path-to-git-internal-repos-project-name"

        if not session_dir.exists():
            print(f"❌ Session directory not found: {session_dir}")
            print("   Make sure Claude Code has been used in this project at least once!")
            return False

        self.monitor.start_monitoring(session_dir, "Fifth Symphony")
        return True

    def stop_monitoring(self):
        """Stop monitoring."""
        self.monitor.stop_monitoring()

    def print_statistics(self):
        """Print current statistics."""
        runtime = datetime.now() - self.start_time
        hours, remainder = divmod(int(runtime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)

        print("\n" + "═" * 60)
        print("📊 STATISTICS")
        print("═" * 60)
        print(f"Runtime:          {hours:02d}:{minutes:02d}:{seconds:02d}")
        print(f"User Prompts:     {self.stats['user_prompts']}")
        print(f"Files Read:       {self.stats['files_read']}")
        print(f"Files Written:    {self.stats['files_written']}")
        print(f"Files Edited:     {self.stats['files_edited']}")
        print(f"Bash Commands:    {self.stats['bash_commands']}")
        print(f"Web Fetches:      {self.stats['web_fetches']}")
        print(f"Claude Responses: {self.stats['assistant_responses']}")
        print("═" * 60 + "\n")


def main():
    """Run terminal monitor."""
    # Print header
    print("\n" + "═" * 70)
    print("🎭 FIFTH SYMPHONY - CLAUDE CODE TERMINAL MONITOR")
    print("═" * 70)
    print()

    # Create monitor
    monitor = TerminalMonitor()

    # Setup signal handlers for clean shutdown
    def signal_handler(sig, frame):
        print("\n\n🛑 Shutting down...")
        monitor.print_statistics()
        monitor.stop_monitoring()
        print("✅ Monitor stopped\n")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start monitoring
    print("🔍 Starting Claude Code monitoring...")
    if not monitor.start_monitoring():
        sys.exit(1)

    print("✅ Monitoring active!\n")
    print("📋 Activity Log:")
    print("─" * 70)

    # Print statistics every 30 seconds
    last_stats = time.time()
    stats_interval = 30

    try:
        while True:
            time.sleep(1)

            # Print statistics periodically
            if time.time() - last_stats >= stats_interval:
                monitor.print_statistics()
                last_stats = time.time()

    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)


if __name__ == "__main__":
    main()
