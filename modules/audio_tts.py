"""
DEPRECATED: Audio TTS module has moved to tengen-tts.

This module is a compatibility shim. Please update your imports:

    # Old import (deprecated)
    from fifth_symphony.modules.audio_tts import AudioTTS, AudioTTSError

    # New import (recommended)
    from tengen_tts.core import AudioTTS, AudioTTSError

This shim will be removed in a future version.
"""

import warnings

warnings.warn(
    "fifth-symphony.modules.audio_tts is deprecated. "
    "Use 'from tengen_tts.core import AudioTTS, AudioTTSError' instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export from tengen-tts for backward compatibility
try:
    from tengen_tts.core import (
        AudioTTS,
        AudioTTSError,
        get_voice_id_for_filepath,
    )
    from tengen_tts.core.voice_selection import (
        VOICE_ALBEDO_V1,
        VOICE_ALBEDO_V2,
        censor_voice_id,
        detect_environment,
        get_voice_id_for_environment,
    )
except ImportError as e:
    raise ImportError(
        "tengen-tts package not installed. "
        "Install with: uv add tengen-tts (from internal/repos/tengen-tts)"
    ) from e


__all__ = [
    "AudioTTS",
    "AudioTTSError",
    "VOICE_ALBEDO_V1",
    "VOICE_ALBEDO_V2",
    "detect_environment",
    "get_voice_id_for_environment",
    "get_voice_id_for_filepath",
    "censor_voice_id",
]
