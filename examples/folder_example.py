#!/usr/bin/env python3
"""
Fifth Symphony - Folder Management Example

Demonstrates real-time folder monitoring and summaries.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.folder_manager import FileEvent, FolderManager


def on_file_event(event: FileEvent):
    """Handle file system events."""
    icons = {
        "created": "✨",
        "modified": "📝",
        "deleted": "🗑️",
        "moved": "📦"
    }

    icon = icons.get(event.action.value, "📄")
    print(f"{icon} {event.action.value.upper()}: {event.path.name}")


async def main():
    """Run folder management demo."""
    print("📁 Fifth Symphony - Folder Management Demo")
    print("="*60)

    # Initialize manager
    manager = FolderManager()

    print("\n📦 Adding folders...")

    # Add Downloads folder
    downloads = Path.home() / "Downloads"
    if downloads.exists():
        manager.add_folder("downloads", downloads)
        print(f"✅ Added: {downloads}")
    else:
        print("⚠️  Downloads folder not found")
        return

    # Get folder summary
    print("\n📊 Generating folder summary...")
    summary = await manager.get_folder_summary("downloads")

    print(f"\n{'='*60}")
    print("DOWNLOADS FOLDER SUMMARY")
    print(f"{'='*60}")
    print(f"📁 Path: {summary.path}")
    print(f"📊 Total Files: {summary.total_files}")
    print(f"💾 Total Size: {manager.format_size(summary.total_size)}")

    # File types
    print("\n📝 File Types (Top 10):")
    sorted_types = sorted(
        summary.file_types.items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]

    for ext, count in sorted_types:
        print(f"  {ext}: {count} files")

    # Recent files
    if summary.recent_files:
        print(f"\n🕐 Recent Files ({len(summary.recent_files)}):")
        for path in summary.recent_files[:5]:
            size = manager.format_size(path.stat().st_size)
            print(f"  {path.name} ({size})")

    # Old files
    if summary.old_files:
        print(f"\n🗑️  Old Files ({len(summary.old_files)}) - Consider cleanup:")
        for path in summary.old_files[:5]:
            from datetime import datetime
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            age_days = (datetime.now() - mtime).days
            size = manager.format_size(path.stat().st_size)
            print(f"  {path.name} ({age_days} days old, {size})")

    # Large files
    if summary.large_files:
        print(f"\n📦 Large Files ({len(summary.large_files)}):")
        for path in summary.large_files[:5]:
            size = manager.format_size(path.stat().st_size)
            print(f"  {path.name} ({size})")

    # Find files demo
    print("\n🔍 Finding PDF files...")
    pdfs = await manager.find_files("downloads", "*.pdf", max_results=10)
    print(f"Found {len(pdfs)} PDF files:")
    for pdf in pdfs[:5]:
        size = manager.format_size(pdf.stat().st_size)
        print(f"  {pdf.name} ({size})")

    # Watch folder for changes
    print("\n👀 Starting folder watch...")
    print("  (Create/modify files in Downloads to see events)")
    print("  (Press Ctrl+C to stop)")

    try:
        manager.start_watching("downloads", callback=on_file_event)

        # Keep running
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print(f"\n\n{'='*60}")
        print("Stopping folder watch...")
        manager.stop_all_watching()
        print("✅ Demo complete!")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
