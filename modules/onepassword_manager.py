"""
DEPRECATED: 1Password manager has moved to tengen-tts.

This module is a compatibility shim. Please update your imports:

    # Old import (deprecated)
    from fifth_symphony.modules.onepassword_manager import OnePasswordManager

    # New import (recommended)
    from tengen_tts.credentials import OnePasswordManager

This shim will be removed in a future version.
"""

import warnings

warnings.warn(
    "fifth-symphony.modules.onepassword_manager is deprecated. "
    "Use 'from tengen_tts.credentials import OnePasswordManager' instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export from tengen-tts for backward compatibility
try:
    from tengen_tts.credentials import OnePasswordManager
except ImportError as e:
    raise ImportError(
        "tengen-tts package not installed. "
        "Install with: uv add tengen-tts (from internal/repos/tengen-tts)"
    ) from e

__all__ = ["OnePasswordManager"]
