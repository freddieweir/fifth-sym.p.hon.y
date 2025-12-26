#!/usr/bin/env python3
"""Test TUI startup to capture any errors."""

import sys
import traceback

try:
    from modules.agent_monitor import AlbedoMonitor

    print("✓ Import successful", file=sys.stderr)

    app = AlbedoMonitor()
    print("✓ App instantiation successful", file=sys.stderr)

    print("✓ Starting TUI...", file=sys.stderr)
    app.run()

except Exception as e:
    print(f"✗ Error: {e}", file=sys.stderr)
    traceback.print_exc()
    sys.exit(1)
