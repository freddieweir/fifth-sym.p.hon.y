"""Shared configuration loading for all modules."""

from pathlib import Path
import yaml
from typing import Dict, Any, Optional


class ModuleConfig:
    """Load and access config.yaml settings shared across all modules."""

    def __init__(self):
        self.config_path = Path(__file__).parent.parent / "config.yaml"
        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """Load YAML config with fallback defaults."""
        try:
            with open(self.config_path) as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {
                "display": {"refresh_interval": 2},
                "monitoring": {},
                "integrations": {}
            }

    def get(self, key_path: str, default: Optional[Any] = None) -> Any:
        """Get nested config value via dot notation.

        Args:
            key_path: Dot-separated path (e.g., 'display.refresh_interval')
            default: Default value if key not found

        Returns:
            Config value or default
        """
        keys = key_path.split('.')
        value = self.config

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key, {})
            else:
                return default

        return value if value != {} else default

    @property
    def refresh_interval(self) -> int:
        """Get display refresh interval in seconds."""
        return self.get('display.refresh_interval', 2)

    @property
    def screenshot_dir(self) -> Path:
        """Get screenshot directory path."""
        default_dir = Path.home() / "git" / "ai-bedo" / "screenshots"
        screenshot_path = self.get('display.screenshot_dir', str(default_dir))
        return Path(screenshot_path)
