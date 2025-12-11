"""Consistent color scheme and styling for all modules."""


class Colors:
    """Dracula-inspired color palette for consistent theming."""

    PRIMARY = "magenta"      # Hot pink - titles, headers
    SECONDARY = "cyan"       # Cyan - data, borders
    ACCENT = "yellow"        # Yellow - highlights, focus
    SUCCESS = "green"        # Green - active, success states
    WARNING = "yellow"       # Yellow - warnings
    ERROR = "red"            # Red - errors, failures
    DIM = "dim"              # Dimmed - secondary info


class Symbols:
    """Status indicators and icons."""

    ACTIVE = "●"      # Active/connected/running
    IDLE = "○"        # Idle/disconnected/stopped
    UNKNOWN = "⊗"     # Unknown/error state
    CHECK = "✓"       # Success/confirmed
    CROSS = "✗"       # Failure/denied
