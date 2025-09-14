"""
Symlink Manager Module
Manages symlinks to external scripts for the orchestrator
"""

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class SymlinkManager:
    """Manages symlinks to external scripts"""

    def __init__(self, symlinks_dir: Path):
        self.symlinks_dir = symlinks_dir
        self.metadata_file = symlinks_dir / ".symlink_metadata.json"

        # Create symlinks directory if it doesn't exist
        self.symlinks_dir.mkdir(parents=True, exist_ok=True)

        # Load metadata
        self.metadata = self._load_metadata()

    def _load_metadata(self) -> dict:
        """Load symlink metadata from file"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load symlink metadata: {e}")
        return {}

    def _save_metadata(self):
        """Save symlink metadata to file"""
        try:
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(self.metadata, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save symlink metadata: {e}")

    def add_symlink(self, external_path: str, alias: str | None = None) -> tuple[bool, str]:
        """
        Create a symlink to an external script

        Args:
            external_path: Path to the external script
            alias: Optional alias for the symlink (defaults to script name)

        Returns:
            Tuple of (success, message)
        """
        external_path = Path(external_path).resolve()

        # Validate external path
        if not external_path.exists():
            return False, f"External script not found: {external_path}"

        if not external_path.is_file():
            return False, f"Path is not a file: {external_path}"

        # Determine symlink name
        if alias:
            symlink_name = (
                alias if alias.endswith(external_path.suffix) else f"{alias}{external_path.suffix}"
            )
        else:
            symlink_name = external_path.name

        symlink_path = self.symlinks_dir / symlink_name

        # Check for existing symlink
        if symlink_path.exists():
            if symlink_path.is_symlink():
                # Update existing symlink
                symlink_path.unlink()
            else:
                return False, f"Non-symlink file already exists: {symlink_name}"

        try:
            # Create symlink
            symlink_path.symlink_to(external_path)

            # Store metadata
            self.metadata[symlink_name] = {
                "original_path": str(external_path),
                "created": datetime.now().isoformat(),
                "alias": alias,
                "type": "external",
                "description": f"External script from {external_path.parent.name}",
            }
            self._save_metadata()

            logger.info(f"Created symlink: {symlink_name} -> {external_path}")
            return True, f"Successfully linked {symlink_name} to {external_path}"

        except Exception as e:
            logger.error(f"Failed to create symlink: {e}")
            return False, f"Failed to create symlink: {e}"

    def remove_symlink(self, name: str) -> tuple[bool, str]:
        """
        Remove a symlink

        Args:
            name: Name of the symlink to remove

        Returns:
            Tuple of (success, message)
        """
        symlink_path = self.symlinks_dir / name

        if not symlink_path.exists():
            return False, f"Symlink not found: {name}"

        if not symlink_path.is_symlink():
            return False, f"Not a symlink: {name}"

        try:
            # Remove symlink
            symlink_path.unlink()

            # Remove metadata
            if name in self.metadata:
                del self.metadata[name]
                self._save_metadata()

            logger.info(f"Removed symlink: {name}")
            return True, f"Successfully removed symlink: {name}"

        except Exception as e:
            logger.error(f"Failed to remove symlink: {e}")
            return False, f"Failed to remove symlink: {e}"

    def list_symlinks(self) -> list[dict]:
        """
        List all symlinks with their metadata

        Returns:
            List of symlink information dictionaries
        """
        symlinks = []

        for item in self.symlinks_dir.iterdir():
            if item.is_symlink():
                info = {
                    "name": item.name,
                    "target": str(item.resolve()) if item.exists() else "BROKEN",
                    "valid": item.exists(),
                }

                # Add metadata if available
                if item.name in self.metadata:
                    info.update(self.metadata[item.name])

                symlinks.append(info)

        return symlinks

    def validate_symlinks(self) -> list[str]:
        """
        Check for broken symlinks

        Returns:
            List of broken symlink names
        """
        broken = []

        for item in self.symlinks_dir.iterdir():
            if item.is_symlink() and not item.exists():
                broken.append(item.name)
                logger.warning(f"Broken symlink detected: {item.name}")

        return broken

    def get_symlink_info(self, name: str) -> dict | None:
        """
        Get detailed information about a symlink

        Args:
            name: Name of the symlink

        Returns:
            Dictionary with symlink information or None if not found
        """
        symlink_path = self.symlinks_dir / name

        if not symlink_path.exists() or not symlink_path.is_symlink():
            return None

        info = {
            "name": name,
            "symlink_path": str(symlink_path),
            "target_path": str(symlink_path.resolve()) if symlink_path.exists() else None,
            "valid": symlink_path.exists(),
            "size": symlink_path.stat().st_size if symlink_path.exists() else 0,
            "modified": datetime.fromtimestamp(symlink_path.stat().st_mtime).isoformat()
            if symlink_path.exists()
            else None,
        }

        # Add metadata if available
        if name in self.metadata:
            info.update(self.metadata[name])

        return info

    def clean_broken_symlinks(self) -> list[str]:
        """
        Remove all broken symlinks

        Returns:
            List of removed symlink names
        """
        removed = []
        broken = self.validate_symlinks()

        for name in broken:
            success, _ = self.remove_symlink(name)
            if success:
                removed.append(name)

        return removed
