"""Agent Monitor TUI - Monitor Floor Guardians and Pleiades Skills."""

import os
from .app import AlbedoMonitor

__version__ = "0.1.0"
__all__ = ["AlbedoMonitor"]


def main():
    """Entry point with mouse disabled."""
    os.environ['TEXTUAL_MOUSE'] = '0'
    app = AlbedoMonitor()
    app.run()
