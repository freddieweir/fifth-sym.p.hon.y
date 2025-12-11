#!/usr/bin/env python3
"""Migrate audio files to unified location with consistent naming.

This script consolidates audio files from multiple deprecated locations
into a single unified structure with environment suffixes.

Old locations (deprecated):
- ALBEDO_ROOT/communications/audio/
- ALBEDO_ROOT/communications/audio/Audio/.processed/
- ALBEDO_ROOT/communications/vm-audio/
- ALBEDO_ROOT/communications/main-audio/

New unified location:
- ALBEDO_ROOT/communications/audio/
  - active/ (monitored directory)
  - .processed/ (archived with environment suffixes)

Naming convention: YYYYMMDD-HHMMSS-{project}-{environment}.{txt|mp3}
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
import re

# Dynamic path resolution for ai-bedo repository
ALBEDO_ROOT = Path(os.getenv("ALBEDO_ROOT", Path.home() / "git" / "internal" / "repos" / "ai-bedo"))


class AudioMigrator:
    """Migrate and consolidate audio files."""

    def __init__(self):
        # Old locations
        self.old_locations = [
            ALBEDO_ROOT / "communications" / "audio",
            ALBEDO_ROOT / "communications" / "audio" / "Audio" / ".processed",
            ALBEDO_ROOT / "communications" / "vm-audio" / ".processed",
            ALBEDO_ROOT / "communications" / "main-audio" / ".processed",
        ]

        # New unified location
        self.new_base = ALBEDO_ROOT / "communications" / "audio"
        self.new_active = self.new_base / "active"
        self.new_processed = self.new_base / ".processed"

        # Stats
        self.migrated_count = 0
        self.skipped_count = 0
        self.error_count = 0

    def create_structure(self):
        """Create new directory structure."""
        print(f"Creating unified audio structure at {self.new_base}")
        self.new_active.mkdir(parents=True, exist_ok=True)
        self.new_processed.mkdir(parents=True, exist_ok=True)
        print("✓ Directory structure created")

    def detect_environment(self, filepath: Path) -> str:
        """Detect environment from file path or name.

        Returns: 'main', 'vm', or 'orchestrator'
        """
        path_str = str(filepath)

        # Check path for environment indicators
        if "vm-audio" in path_str or "-vm" in filepath.name:
            return "vm"
        elif "main-audio" in path_str or "-main" in filepath.name:
            return "main"
        elif "orchestrator" in filepath.name.lower():
            return "orchestrator"

        # Default to main for Ark legacy files
        if "Ark" in path_str:
            return "main"

        return "main"

    def extract_project_name(self, filename: str) -> str:
        """Extract project name from filename.

        Examples:
        - '20251027-013535-environment-test.txt' -> 'environment-test'
        - 'tui-migrated-to-fifth-symphony.txt' -> 'fifth-symphony'
        """
        # Remove extension
        name_without_ext = filename.rsplit('.', 1)[0]

        # Try to extract timestamp and project
        # Pattern: YYYYMMDD-HHMMSS-project-name or just project-name
        match = re.match(r'^\d{8}-\d{6}-(.+)$', name_without_ext)
        if match:
            return match.group(1)

        # If no timestamp, use the whole filename (minus extension)
        # Take last part if multiple hyphens exist
        parts = name_without_ext.split('-')
        if len(parts) > 2:
            return '-'.join(parts[-2:])  # Last 2 parts as project name

        return name_without_ext

    def standardize_filename(self, filepath: Path) -> str:
        """Convert filename to standard format.

        Format: YYYYMMDD-HHMMSS-{project}-{environment}.{ext}
        """
        filename = filepath.name
        extension = filepath.suffix

        # Detect environment
        environment = self.detect_environment(filepath)

        # Extract project name
        project = self.extract_project_name(filename)

        # Check if already has timestamp
        timestamp_match = re.match(r'^(\d{8}-\d{6})', filename)
        if timestamp_match:
            timestamp = timestamp_match.group(1)
        else:
            # Use file modification time for legacy files
            mtime = filepath.stat().st_mtime
            dt = datetime.fromtimestamp(mtime)
            timestamp = dt.strftime("%Y%m%d-%H%M%S")

        # Check if already has environment suffix
        if not filename.endswith(f"-{environment}{extension}"):
            new_filename = f"{timestamp}-{project}-{environment}{extension}"
        else:
            new_filename = filename

        return new_filename

    def find_audio_pairs(self, directory: Path) -> list:
        """Find matching .txt and .mp3 pairs in directory."""
        pairs = []
        txt_files = list(directory.glob("*.txt"))

        for txt_file in txt_files:
            mp3_file = txt_file.with_suffix('.mp3')
            pairs.append({
                'txt': txt_file,
                'mp3': mp3_file if mp3_file.exists() else None
            })

        return pairs

    def migrate_file(self, source: Path, destination: Path, dry_run: bool = False):
        """Migrate a single file to new location."""
        if not source.exists():
            return

        if destination.exists():
            self.skipped_count += 1
            print(f"  ⊗ Skipped (already exists): {destination.name}")
            return

        try:
            if not dry_run:
                shutil.copy2(source, destination)
            self.migrated_count += 1
            print(f"  ✓ Migrated: {source.name} → {destination.name}")
        except Exception as e:
            self.error_count += 1
            print(f"  ✗ Error migrating {source.name}: {e}")

    def migrate_from_location(self, old_location: Path, dry_run: bool = False):
        """Migrate all audio files from one old location."""
        if not old_location.exists():
            print(f"  ⊗ Skipped (not found): {old_location}")
            return

        print(f"\n📁 Migrating from: {old_location}")
        pairs = self.find_audio_pairs(old_location)

        if not pairs:
            print("  ⊗ No audio files found")
            return

        print(f"  Found {len(pairs)} audio file(s)")

        for pair in pairs:
            txt_file = pair['txt']
            mp3_file = pair['mp3']

            # Generate standardized filename
            new_filename = self.standardize_filename(txt_file)

            # Migrate to .processed (archived files)
            txt_dest = self.new_processed / new_filename
            self.migrate_file(txt_file, txt_dest, dry_run)

            if mp3_file:
                mp3_dest = self.new_processed / new_filename.replace('.txt', '.mp3')
                self.migrate_file(mp3_file, mp3_dest, dry_run)

    def run(self, dry_run: bool = False):
        """Run the migration process."""
        print("=" * 60)
        print("Audio File Migration Tool")
        print("=" * 60)

        if dry_run:
            print("🔍 DRY RUN MODE - No files will be moved\n")
        else:
            print("⚠️  LIVE MODE - Files will be migrated\n")

        # Create new structure
        if not dry_run:
            self.create_structure()

        # Migrate from each old location
        for old_location in self.old_locations:
            self.migrate_from_location(old_location, dry_run)

        # Print summary
        print("\n" + "=" * 60)
        print("Migration Summary")
        print("=" * 60)
        print(f"✓ Migrated: {self.migrated_count} files")
        print(f"⊗ Skipped:  {self.skipped_count} files")
        print(f"✗ Errors:   {self.error_count} files")

        if dry_run:
            print("\n💡 Run without --dry-run to perform actual migration")
        else:
            print(f"\n✓ Migration complete!")
            print(f"📁 New location: {self.new_base}")
            print(f"📁 Archived files: {self.new_processed}")
            print(f"📁 Active files: {self.new_active}")

    def cleanup_old_locations(self):
        """Remove old deprecated directories (with user confirmation)."""
        print("\n" + "=" * 60)
        print("Cleanup Old Locations")
        print("=" * 60)

        for old_location in self.old_locations:
            if not old_location.exists():
                continue

            files_remaining = list(old_location.glob("*"))
            if not files_remaining:
                print(f"📁 Empty directory: {old_location}")
                try:
                    old_location.rmdir()
                    print(f"  ✓ Removed")
                except Exception as e:
                    print(f"  ✗ Could not remove: {e}")
            else:
                print(f"📁 Not empty: {old_location} ({len(files_remaining)} files)")
                print(f"  ⊗ Manual cleanup required")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate audio files to unified location"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without migrating files"
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Remove empty old directories after migration"
    )

    args = parser.parse_args()

    migrator = AudioMigrator()
    migrator.run(dry_run=args.dry_run)

    if args.cleanup and not args.dry_run:
        response = input("\n⚠️  Remove empty old directories? [y/N]: ")
        if response.lower() == 'y':
            migrator.cleanup_old_locations()


if __name__ == "__main__":
    main()
