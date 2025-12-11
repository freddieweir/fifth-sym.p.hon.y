"""Relative time formatting utilities."""

from datetime import datetime, timedelta
from typing import Union


def relative_time(dt: Union[datetime, float]) -> str:
    """
    Convert datetime or timestamp to human-readable relative time.

    Args:
        dt: datetime object or Unix timestamp (float)

    Returns:
        Relative time string (e.g., "2m ago", "5h ago", "3d ago")

    Examples:
        >>> from datetime import datetime, timedelta
        >>> now = datetime.now()
        >>> relative_time(now - timedelta(minutes=5))
        '5m ago'
        >>> relative_time(now - timedelta(hours=2))
        '2h ago'
        >>> relative_time(now - timedelta(days=3))
        '3d ago'
    """
    # Convert timestamp to datetime if needed
    if isinstance(dt, (int, float)):
        dt = datetime.fromtimestamp(dt)

    now = datetime.now()
    delta = now - dt

    # Handle future dates
    if delta.total_seconds() < 0:
        return "in the future"

    # Just now (< 1 minute)
    if delta < timedelta(minutes=1):
        return "just now"

    # Minutes ago (< 1 hour)
    elif delta < timedelta(hours=1):
        mins = int(delta.total_seconds() / 60)
        return f"{mins}m ago"

    # Hours ago (< 1 day)
    elif delta < timedelta(days=1):
        hours = int(delta.total_seconds() / 3600)
        return f"{hours}h ago"

    # Days ago (< 1 week)
    elif delta < timedelta(days=7):
        days = delta.days
        return f"{days}d ago"

    # Weeks ago (< 30 days)
    elif delta < timedelta(days=30):
        weeks = delta.days // 7
        return f"{weeks}w ago"

    # Months ago (< 1 year)
    elif delta < timedelta(days=365):
        months = delta.days // 30
        return f"{months}mo ago"

    # Fall back to date for very old items
    else:
        return dt.strftime("%Y-%m-%d")


def format_relative_time(dt: Union[datetime, float], include_absolute: bool = False) -> str:
    """
    Format relative time with optional absolute timestamp.

    Args:
        dt: datetime object or Unix timestamp
        include_absolute: If True, include absolute time in parentheses

    Returns:
        Formatted time string

    Examples:
        >>> format_relative_time(datetime.now() - timedelta(hours=2))
        '2h ago'
        >>> format_relative_time(datetime.now() - timedelta(hours=2), include_absolute=True)
        '2h ago (14:30)'
    """
    relative = relative_time(dt)

    if include_absolute:
        if isinstance(dt, (int, float)):
            dt = datetime.fromtimestamp(dt)
        absolute = dt.strftime("%H:%M")
        return f"{relative} ({absolute})"

    return relative


# For backwards compatibility
def humanize_time(dt: Union[datetime, float]) -> str:
    """Alias for relative_time() for backwards compatibility."""
    return relative_time(dt)
