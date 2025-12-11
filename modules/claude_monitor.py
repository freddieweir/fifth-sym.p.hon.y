"""
Claude Instance Monitor

Detects when Claude Code instances in iTerm2 are waiting for responses.
Provides physical (Stream Deck LED) and audio notifications.
"""

import logging
import subprocess
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class ClaudeInstance:
    """Represents a detected Claude Code instance."""

    def __init__(self, window_id: str, tab_id: str, title: str):
        self.window_id = window_id
        self.tab_id = tab_id
        self.title = title
        self.last_activity = datetime.now()
        self.pending_since = None
        self.alerted = False

    def is_pending(self) -> bool:
        """Check if this instance is pending a response."""
        # Claude Code shows "⏳" or "Thinking..." in title when working
        # Or inactive for > 30 seconds after activity
        return self.pending_since is not None

    def mark_pending(self):
        """Mark instance as pending response."""
        if not self.pending_since:
            self.pending_since = datetime.now()
            logger.info(f"Claude instance pending: {self.title}")

    def mark_active(self):
        """Mark instance as active (received response)."""
        if self.pending_since:
            wait_time = datetime.now() - self.pending_since
            logger.info(f"Claude instance active after {wait_time.total_seconds():.1f}s")

        self.pending_since = None
        self.alerted = False
        self.last_activity = datetime.now()


class ClaudeMonitor:
    """Monitor Claude Code instances in iTerm2."""

    def __init__(
        self,
        check_interval: int = 2,
        alert_threshold: int = 5,  # seconds before alerting
        audio_alerts: bool = True,
        stream_deck_alerts: bool = True,
    ):
        self.check_interval = check_interval
        self.alert_threshold = alert_threshold
        self.audio_alerts = audio_alerts
        self.stream_deck_alerts = stream_deck_alerts

        self.instances: dict[str, ClaudeInstance] = {}
        self.alert_file = Path("/tmp/claude-pending.flag")

    def get_iterm_tabs(self) -> list[dict]:
        """Get all iTerm2 tabs using AppleScript."""
        script = """
        tell application "iTerm"
            set output to ""
            repeat with theWindow in windows
                repeat with theTab in tabs of theWindow
                    set tabTitle to name of current session of theTab
                    set windowID to id of theWindow
                    set tabID to id of theTab
                    set output to output & windowID & "|" & tabID & "|" & tabTitle & "\\n"
                end repeat
            end repeat
            return output
        end tell
        """

        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=5,
                check=False
            )

            if result.returncode != 0:
                return []

            tabs = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                parts = line.split("|")
                if len(parts) == 3:
                    tabs.append({
                        "window_id": parts[0],
                        "tab_id": parts[1],
                        "title": parts[2],
                    })

            return tabs

        except Exception as e:
            logger.error(f"Failed to get iTerm tabs: {e}")
            return []

    def is_claude_tab(self, title: str) -> bool:
        """Check if tab title indicates Claude Code instance."""
        indicators = [
            "claude",
            "claude-code",
            "vscodium",
            "⏳",  # Thinking indicator
            "Thinking...",
        ]

        title_lower = title.lower()
        return any(indicator in title_lower for indicator in indicators)

    def is_waiting(self, title: str) -> bool:
        """Check if Claude is waiting for response."""
        waiting_indicators = [
            "⏳",
            "thinking",
            "please wait",
            "processing",
        ]

        title_lower = title.lower()
        return any(indicator in title_lower for indicator in waiting_indicators)

    def detect_instances(self) -> list[ClaudeInstance]:
        """Detect all Claude Code instances."""
        tabs = self.get_iterm_tabs()
        instances = []

        for tab in tabs:
            if self.is_claude_tab(tab["title"]):
                instance = ClaudeInstance(
                    window_id=tab["window_id"],
                    tab_id=tab["tab_id"],
                    title=tab["title"],
                )

                # Check if waiting
                if self.is_waiting(tab["title"]):
                    instance.mark_pending()

                instances.append(instance)

        return instances

    def trigger_audio_alert(self, instance: ClaudeInstance):
        """Play audio notification for pending instance."""
        if not self.audio_alerts:
            return

        # Use AudioTTS to speak notification
        try:
            from .audio_tts import AudioTTS

            tts = AudioTTS(auto_play=True)
            tts.generate_speech("Claude is waiting for your response")

            logger.info(f"Audio alert triggered for: {instance.title}")

        except Exception as e:
            logger.error(f"Failed to play audio alert: {e}")

    def trigger_stream_deck_alert(self, pending: bool):
        """Set Stream Deck indicator for pending Claude instances."""
        if not self.stream_deck_alerts:
            return

        if pending:
            # Create flag file for Stream Deck to detect
            self.alert_file.write_text(datetime.now().isoformat())
            logger.debug("Stream Deck alert flag set")
        else:
            # Remove flag file
            if self.alert_file.exists():
                self.alert_file.unlink()
                logger.debug("Stream Deck alert flag cleared")

    def check_and_alert(self):
        """Check all instances and trigger alerts if needed."""
        instances = self.detect_instances()

        # Update tracked instances
        current_ids = set()
        any_pending = False

        for instance in instances:
            instance_id = f"{instance.window_id}-{instance.tab_id}"
            current_ids.add(instance_id)

            if instance.is_pending():
                any_pending = True

                # Check if we should alert
                if instance.pending_since:
                    wait_time = datetime.now() - instance.pending_since
                    if wait_time.total_seconds() > self.alert_threshold and not instance.alerted:
                        # Trigger alerts
                        self.trigger_audio_alert(instance)
                        instance.alerted = True

            self.instances[instance_id] = instance

        # Remove closed instances
        for instance_id in list(self.instances.keys()):
            if instance_id not in current_ids:
                del self.instances[instance_id]

        # Update Stream Deck
        self.trigger_stream_deck_alert(any_pending)

    def monitor_loop(self):
        """Main monitoring loop."""
        logger.info("Claude monitor started")
        logger.info(f"Alert threshold: {self.alert_threshold}s")

        try:
            while True:
                self.check_and_alert()
                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            logger.info("Claude monitor stopped")
            # Clean up alert flags
            if self.alert_file.exists():
                self.alert_file.unlink()


def main():
    """CLI entry point for Claude monitor."""
    import argparse

    parser = argparse.ArgumentParser(description="Monitor Claude Code instances")
    parser.add_argument("--interval", type=int, default=2, help="Check interval (seconds)")
    parser.add_argument("--threshold", type=int, default=5, help="Alert threshold (seconds)")
    parser.add_argument("--no-audio", action="store_true", help="Disable audio alerts")
    parser.add_argument("--no-stream-deck", action="store_true", help="Disable Stream Deck alerts")
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    monitor = ClaudeMonitor(
        check_interval=args.interval,
        alert_threshold=args.threshold,
        audio_alerts=not args.no_audio,
        stream_deck_alerts=not args.no_stream_deck,
    )

    monitor.monitor_loop()


if __name__ == "__main__":
    main()
