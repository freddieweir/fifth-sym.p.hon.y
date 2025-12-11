"""Smart media control with playback detection to prevent unwanted app launches."""

import subprocess
import logging

logger = logging.getLogger(__name__)


def is_music_playing() -> bool:
    """
    Check if Music.app is currently playing.

    Returns:
        True if Music.app is playing, False otherwise
    """
    try:
        # Check if Music.app process is running
        result = subprocess.run(
            ["pgrep", "-x", "Music"],
            capture_output=True,
            timeout=2,
            check=False
        )

        if result.returncode != 0:
            # Music.app not running
            return False

        # Music.app is running - check playback state
        result = subprocess.run(
            ["osascript", "-e", 'tell application "Music" to get player state'],
            capture_output=True,
            text=True,
            timeout=2,
            check=False
        )

        return result.stdout.strip() == "playing"

    except Exception as e:
        logger.debug(f"Could not check Music.app state: {e}")
        return False


def is_anything_playing() -> bool:
    """
    Check if any media is currently playing system-wide.

    Checks multiple indicators:
    1. Music.app playback state
    2. System audio output (if available)

    Returns:
        True if any media is detected as playing
    """
    # Check Music.app
    if is_music_playing():
        return True

    # TODO: Add more checks for other apps
    # - Spotify via AppleScript
    # - Safari/Chrome via JavaScript
    # - System-wide audio detection

    return False


def smart_media_playpause() -> bool:
    """
    Toggle media playback ONLY if something is currently playing.

    This prevents Music.app from launching when nothing is playing.

    Returns:
        True if playback was toggled, False if nothing was playing
    """
    if is_anything_playing():
        # Something is playing - safe to toggle
        try:
            result = subprocess.run(
                ["shortcuts", "run", "MediaPlayPause"],
                capture_output=True,
                timeout=2,
                check=False
            )

            if result.returncode == 0:
                logger.info("Media playback toggled")
                return True
            else:
                logger.warning(f"MediaPlayPause failed: {result.stderr.decode()}")
                return False

        except Exception as e:
            logger.error(f"Failed to toggle media: {e}")
            return False
    else:
        # Nothing playing - do nothing
        logger.debug("No media playing - ignoring toggle command")
        return False


def force_media_playpause() -> bool:
    """
    Force toggle media playback even if nothing is playing.

    Use this if you explicitly want to start playback from a stopped state.

    Returns:
        True if command was sent successfully
    """
    try:
        result = subprocess.run(
            ["shortcuts", "run", "MediaPlayPause"],
            capture_output=True,
            timeout=2,
            check=False
        )

        return result.returncode == 0

    except Exception as e:
        logger.error(f"Failed to force toggle media: {e}")
        return False
