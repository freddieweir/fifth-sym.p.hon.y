"""Entry point for agent monitor when run as module."""

import os
from .app import AlbedoMonitor


def main():
    """Launch the Agent Monitor TUI."""
    # Disable mouse support via environment variable
    os.environ['TEXTUAL_MOUSE'] = '0'

    app = AlbedoMonitor()
    app.run()


if __name__ == "__main__":
    main()
