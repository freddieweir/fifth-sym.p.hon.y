"""
DEPRECATED: Media control has moved to tengen-tts.

This module is a compatibility shim. Please update your imports:

    # Old import (deprecated)
    from fifth_symphony.modules.smart_media_control import is_anything_playing

    # New import (recommended)
    from tengen_tts.media import is_anything_playing, is_music_playing

This shim will be removed in a future version.
"""

import warnings

warnings.warn(
    "fifth-symphony.modules.smart_media_control is deprecated. "
    "Use 'from tengen_tts.media import is_anything_playing' instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export from tengen-tts for backward compatibility
try:
    from tengen_tts.media import is_anything_playing, is_music_playing
    from tengen_tts.media.control import MediaController
except ImportError as e:
    raise ImportError(
        "tengen-tts package not installed. "
        "Install with: uv add tengen-tts (from internal/repos/tengen-tts)"
    ) from e


def smart_media_playpause() -> bool:
    """Toggle media playback ONLY if something is currently playing."""
    controller = MediaController()
    if is_anything_playing():
        return controller.toggle_playback()
    return False


def force_media_playpause() -> bool:
    """Force toggle media playback even if nothing is playing."""
    controller = MediaController()
    return controller.toggle_playback()


__all__ = [
    "is_anything_playing",
    "is_music_playing",
    "smart_media_playpause",
    "force_media_playpause",
]
