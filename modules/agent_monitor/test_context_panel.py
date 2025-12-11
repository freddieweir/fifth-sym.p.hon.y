#!/usr/bin/env python3
"""Quick test to display Context panel data without full TUI."""

from pathlib import Path
from datetime import datetime
from collections import defaultdict

def relative_time(timestamp):
    """Convert timestamp to relative time string."""
    if isinstance(timestamp, float):
        timestamp = datetime.fromtimestamp(timestamp)

    now = datetime.now()
    delta = now - timestamp

    seconds = delta.total_seconds()

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes}m ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours}h ago"
    else:
        days = int(seconds / 86400)
        return f"{days}d ago"

def load_context_files():
    """Load recently accessed files from Claude Code file-history."""
    context_files = []

    file_history_dir = Path.home() / ".claude" / "file-history"
    if not file_history_dir.exists():
        print("❌ No file-history directory found")
        return []

    try:
        # Find most recent session
        sessions = sorted(
            [s for s in file_history_dir.iterdir() if s.is_dir()],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

        if not sessions:
            print("❌ No sessions found")
            return []

        recent_session = sessions[0]
        print(f"✅ Found recent session: {recent_session.name}")

        # Group files by hash
        file_data = defaultdict(lambda: {"latest_mtime": 0, "version_count": 0, "hash": ""})

        for file_path in recent_session.glob("*@v*"):
            try:
                parts = file_path.name.split("@")
                if len(parts) != 2:
                    continue

                file_hash = parts[0]
                version = int(parts[1].replace("v", ""))
                mtime = file_path.stat().st_mtime

                if mtime > file_data[file_hash]["latest_mtime"]:
                    file_data[file_hash]["latest_mtime"] = mtime

                if version > file_data[file_hash]["version_count"]:
                    file_data[file_hash]["version_count"] = version
                    file_data[file_hash]["hash"] = file_hash

            except (ValueError, IndexError):
                continue

        # Convert to list
        context_files = [
            {
                "hash": data["hash"][:8],
                "mtime": data["latest_mtime"],
                "edits": data["version_count"]
            }
            for hash_key, data in file_data.items()
        ]

        # Sort by most recent
        context_files = sorted(
            context_files,
            key=lambda x: x["mtime"],
            reverse=True
        )[:15]

        print(f"✅ Loaded {len(context_files)} context files\n")

        return context_files

    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def display_context_panel(context_files):
    """Display context panel as it will appear in TUI."""
    print("┌─ Claude Code Context ──────────────────────────┐")
    print("│ Hash      Accessed    Edits                    │")
    print("├────────────────────────────────────────────────┤")

    if not context_files:
        print("│           No context                           │")
    else:
        for cf in context_files:
            hash_str = cf["hash"].ljust(8)
            time_str = relative_time(cf["mtime"]).ljust(10)
            edits_str = f"v{cf['edits']}".rjust(5)
            print(f"│ {hash_str}  {time_str}  {edits_str}                   │")

    print("└────────────────────────────────────────────────┘")
    print("\n💡 Press 'C' in TUI to focus this panel")
    print("💡 Use arrow keys or j/k to navigate")
    print("💡 Press 'R' to refresh data")

if __name__ == "__main__":
    print("🔍 Testing Context Visualization Panel\n")
    context_files = load_context_files()
    print()
    display_context_panel(context_files)
