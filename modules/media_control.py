#!/usr/bin/env python3
"""
Smart Media Control for macOS
Detects which app is currently playing media and toggles it intelligently.

Part of fifth-symphony modular automation ecosystem.
"""

import subprocess


class MediaController:
    """Intelligent media playback controller for macOS."""

    # Priority order for checking apps (Zen first since it's most common for YouTube)
    BROWSER_APPS = ["Zen Browser", "Safari", "Google Chrome", "Firefox", "Arc"]
    MUSIC_APPS = ["Music", "Spotify", "iTunes"]

    # Map of app display names to process names
    APP_PROCESS_NAMES = {
        "Zen Browser": "zen",
        "Safari": "Safari",
        "Google Chrome": "Google Chrome",
        "Firefox": "Firefox",
        "Arc": "Arc",
        "Music": "Music",
        "Spotify": "Spotify"
    }

    def __init__(self):
        self.last_playing_app: str | None = None

    def execute_applescript(self, script: str) -> tuple[bool, str]:
        """Execute AppleScript and return (success, output)."""
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0, result.stdout.strip()
        except subprocess.TimeoutExpired:
            return False, "Script timed out"
        except Exception as e:
            return False, str(e)

    def is_browser_playing(self, browser_name: str) -> bool:
        """Check if browser has playing media (YouTube, etc.)."""
        # Get process name from mapping
        process_name = self.APP_PROCESS_NAMES.get(browser_name, browser_name)

        # Check if browser process is running
        check_running = f"""
        tell application "System Events"
            return exists (process "{process_name}")
        end tell
        """
        success, output = self.execute_applescript(check_running)
        if not success or output != "true":
            return False

        # Browser is running, assume it might be playing
        # (Detecting actual playback in browsers is tricky without browser extensions)
        return True

    def toggle_browser(self, browser_name: str) -> tuple[bool, str]:
        """Toggle browser media using keyboard shortcut (k for YouTube)."""
        # Get process name from mapping
        process_name = self.APP_PROCESS_NAMES.get(browser_name, browser_name)

        # For YouTube and most video sites, 'k' is the play/pause hotkey
        script = f"""
        tell application "System Events"
            tell process "{process_name}"
                set frontmost to true
                delay 0.3
                keystroke "k"
            end tell
        end tell
        """
        success, output = self.execute_applescript(script)
        if success:
            return True, f"Toggled {browser_name}"
        else:
            return False, f"Failed to toggle {browser_name}: {output}"

    def is_music_app_playing(self, app_name: str) -> tuple[bool, str]:
        """Check if Music/Spotify is playing and get state."""
        if app_name == "Music":
            script = """
            tell application "Music"
                if it is running then
                    return player state as string
                else
                    return "stopped"
                end if
            end tell
            """
        elif app_name == "Spotify":
            script = """
            tell application "Spotify"
                if it is running then
                    return player state as string
                else
                    return "stopped"
                end if
            end tell
            """
        else:
            return False, "stopped"

        success, state = self.execute_applescript(script)
        if success:
            is_playing = state == "playing"
            return is_playing, state
        return False, "stopped"

    def toggle_music_app(self, app_name: str) -> tuple[bool, str]:
        """Toggle Music or Spotify playback."""
        if app_name == "Music":
            script = """
            tell application "Music"
                if player state is playing then
                    pause
                    return "paused"
                else
                    play
                    return "playing"
                end if
            end tell
            """
        elif app_name == "Spotify":
            script = """
            tell application "Spotify"
                playpause
                if player state is playing then
                    return "playing"
                else
                    return "paused"
                end if
            end tell
            """
        else:
            return False, "Unknown app"

        success, state = self.execute_applescript(script)
        return success, f"{app_name} {state}"

    def detect_and_toggle(self) -> str:
        """
        Detect which app is playing media and toggle it.
        Returns status message.
        """
        # First, check music apps (they have reliable state detection)
        for music_app in self.MUSIC_APPS:
            is_playing, state = self.is_music_app_playing(music_app)
            if is_playing:
                success, message = self.toggle_music_app(music_app)
                if success:
                    self.last_playing_app = music_app
                    return message

        # Check if any music app was recently playing (even if paused)
        for music_app in self.MUSIC_APPS:
            is_playing, state = self.is_music_app_playing(music_app)
            if state == "paused":
                # Resume paused music
                success, message = self.toggle_music_app(music_app)
                if success:
                    self.last_playing_app = music_app
                    return message

        # Check browsers (priority: last known, then Zen, then Safari, etc.)
        browser_order = self.BROWSER_APPS.copy()
        if self.last_playing_app and self.last_playing_app in browser_order:
            # Try last known browser first
            browser_order.remove(self.last_playing_app)
            browser_order.insert(0, self.last_playing_app)

        for browser in browser_order:
            if self.is_browser_playing(browser):
                success, message = self.toggle_browser(browser)
                if success:
                    self.last_playing_app = browser
                    return message

        return "No media playing detected"

    def get_status(self) -> str:
        """Get current media playback status."""
        status_parts = []

        # Check music apps
        for music_app in self.MUSIC_APPS:
            is_playing, state = self.is_music_app_playing(music_app)
            if state != "stopped":
                status_parts.append(f"{music_app}: {state}")

        # Check browsers
        for browser in self.BROWSER_APPS:
            if self.is_browser_playing(browser):
                status_parts.append(f"{browser}: likely playing")

        if status_parts:
            return ", ".join(status_parts)
        else:
            return "No active media"


def main():
    """CLI interface for media control."""
    import argparse

    parser = argparse.ArgumentParser(description="Smart media control for macOS")
    parser.add_argument(
        "action",
        choices=["toggle", "status"],
        help="Action to perform"
    )
    args = parser.parse_args()

    controller = MediaController()

    if args.action == "toggle":
        result = controller.detect_and_toggle()
        print(result)
    elif args.action == "status":
        status = controller.get_status()
        print(status)


if __name__ == "__main__":
    main()
