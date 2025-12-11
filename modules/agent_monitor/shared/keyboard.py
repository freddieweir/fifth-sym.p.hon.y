"""Keyboard input handling for all modules."""

import select
import sys
import termios
import tty


class KeyboardHandler:
    """Non-blocking keyboard input with terminal mode management.

    Usage:
        with KeyboardHandler() as kbd:
            while running:
                key = kbd.get_key()
                if key == 'q':
                    break
    """

    def __init__(self):
        self.old_settings = None

    def __enter__(self):
        """Set terminal to raw mode for character-by-character input."""
        if sys.stdin.isatty():
            self.old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
        return self

    def __exit__(self, *args):
        """Restore terminal to original settings."""
        if self.old_settings:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)

    def get_key(self, timeout: float = 0.1) -> str | None:
        """Get single key press (non-blocking).

        Args:
            timeout: How long to wait for input in seconds

        Returns:
            Single character key or None if no input
        """
        try:
            if sys.stdin.isatty():
                # Check if input is available within timeout
                ready, _, _ = select.select([sys.stdin], [], [], timeout)
                if ready:
                    return sys.stdin.read(1)
        except Exception:
            pass

        return None
