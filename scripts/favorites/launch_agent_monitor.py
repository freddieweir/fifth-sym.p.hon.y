#!/usr/bin/env python3
"""Launch the Albedo Agent Monitor TUI from fifth-symphony."""

import sys
from pathlib import Path

# Add fifth-symphony root to path
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root))

from modules.agent_monitor import AlbedoMonitor


def main():
    """Launch the Agent Monitor TUI."""
    print("🎭 Launching Albedo Agent Monitor TUI...")
    print()

    app = AlbedoMonitor()
    app.run()


if __name__ == "__main__":
    main()
