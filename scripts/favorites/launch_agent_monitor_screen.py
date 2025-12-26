#!/usr/bin/env python3
"""Launch Agent Monitor TUI in a named screen session."""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def get_session_name():
    """Generate dynamic screen session name."""
    # Check if we're in a git repo to get context
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            repo_path = Path(result.stdout.strip())
            repo_name = repo_path.name
            # Get current branch
            branch_result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=False
            )
            if branch_result.returncode == 0:
                branch = branch_result.stdout.strip()
                # Clean branch name for screen session
                branch_clean = branch.replace("/", "-").replace("_", "-")
                return f"albedo-{repo_name}-{branch_clean}"
    except Exception:
        pass

    # Fallback: Use timestamp
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    return f"albedo-monitor-{timestamp}"


def list_sessions():
    """List all screen sessions."""
    result = subprocess.run(
        ["screen", "-ls"],
        capture_output=True,
        text=True,
        check=False
    )
    return result.stdout


def main():
    """Launch Agent Monitor in screen session."""
    # Parse arguments
    if len(sys.argv) > 1:
        if sys.argv[1] in ["--list", "-l"]:
            print("📺 Active screen sessions:")
            print(list_sessions())
            return
        elif sys.argv[1] in ["--attach", "-a"]:
            session_pattern = "albedo-*" if len(sys.argv) < 3 else sys.argv[2]
            print(f"🔗 Attaching to session matching: {session_pattern}")
            os.execvp("screen", ["screen", "-r", session_pattern])
            return
        elif sys.argv[1] in ["--help", "-h"]:
            print("""
Launch Agent Monitor TUI in a named screen session.

Usage:
  launch_agent_monitor_screen.py [OPTIONS] [SESSION_NAME]

Options:
  --list, -l              List all screen sessions
  --attach, -a [PATTERN]  Attach to existing session
  --help, -h              Show this help

Examples:
  # Launch with auto-generated name
  launch_agent_monitor_screen.py

  # Launch with custom name
  launch_agent_monitor_screen.py albedo-migration

  # List sessions
  launch_agent_monitor_screen.py --list

  # Attach to session
  launch_agent_monitor_screen.py --attach albedo-*

Screen Commands:
  Detach:      Ctrl+A, D
  Reattach:    screen -r <name>
  List:        screen -ls
  Kill:        screen -X -S <name> quit
            """)
            return
        else:
            # Custom session name provided
            session_name = sys.argv[1]
    else:
        # Auto-generate session name
        session_name = get_session_name()

    print(f"🎭 Launching Agent Monitor in screen session: {session_name}")
    print()
    print("To detach: Ctrl+A, then D")
    print(f"To reattach: screen -r {session_name}")
    print()

    # Path to fifth-symphony
    fifth_symphony = Path.home() / "git" / "internal" / "repos" / "fifth-symphony"

    # Launch in screen session
    subprocess.run([
        "screen",
        "-S", session_name,
        "-dm",  # detached mode
        "bash", "-c",
        f"cd {fifth_symphony} && uv run python scripts/launch_agent_monitor.py"
    ])

    print(f"✅ Session '{session_name}' started!")
    print()
    print("Next steps:")
    print(f"  1. Attach: screen -r {session_name}")
    print("  2. Or list all: screen -ls")


if __name__ == "__main__":
    main()
