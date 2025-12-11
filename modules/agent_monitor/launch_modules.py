#!/usr/bin/env python3
"""Launch all Albedo Agent Monitor modules in separate terminal tabs.

This script opens iTerm2 (or Terminal.app) and creates 4 tabs, each running
one of the standalone monitor modules.

Usage:
    python launch_modules.py              # Launch all 4 modules
    python launch_modules.py --help       # Show help
"""

import subprocess
import sys
from pathlib import Path


def launch_iterm():
    """Launch modules in iTerm2 tabs using AppleScript."""

    script_dir = Path(__file__).parent.absolute()

    applescript = f"""
    tell application "iTerm"
        activate

        -- Create new window
        create window with default profile

        -- Tab 1: Agent Activity
        tell current session of current window
            write text "cd {script_dir} && uv run python -m agent_monitor.modules.agent_activity"
            set name to "Agents & Skills"
        end tell

        -- Tab 2: Infrastructure
        tell current window
            create tab with default profile
            tell current session
                write text "cd {script_dir} && uv run python -m agent_monitor.modules.infrastructure"
                set name to "Infrastructure"
            end tell
        end tell

        -- Tab 3: Content
        tell current window
            create tab with default profile
            tell current session
                write text "cd {script_dir} && uv run python -m agent_monitor.modules.content"
                set name to "Content"
            end tell
        end tell

        -- Tab 4: System Status
        tell current window
            create tab with default profile
            tell current session
                write text "cd {script_dir} && uv run python -m agent_monitor.modules.system_status"
                set name to "System"
            end tell
        end tell

        -- Focus first tab
        tell current window
            select first tab
        end tell
    end tell
    """

    try:
        subprocess.run(
            ["osascript", "-e", applescript],
            check=True,
            capture_output=True,
            text=True
        )
        print("✅ Launched all 4 modules in iTerm2")
        print("\n📊 Module Overview:")
        print("  Tab 1: Agent Activity    - Floor Guardians + Pleiades Skills")
        print("  Tab 2: Infrastructure    - MCP Servers + Observatory")
        print("  Tab 3: Content           - Audio History + Documentation")
        print("  Tab 4: System Status     - Albedo + VM + Context Files")
        print("\n💡 Press Q in any tab to quit that module")

    except subprocess.CalledProcessError as e:
        print(f"❌ Error launching iTerm2: {e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ osascript not found. Are you on macOS?")
        sys.exit(1)


def launch_terminal():
    """Launch modules in Terminal.app tabs using AppleScript."""

    script_dir = Path(__file__).parent.absolute()

    applescript = f"""
    tell application "Terminal"
        activate

        -- Tab 1: Agent Activity
        do script "cd {script_dir} && uv run python -m agent_monitor.modules.agent_activity"
        set custom title of front window to "Agents & Skills"

        -- Tab 2: Infrastructure
        tell application "System Events" to keystroke "t" using command down
        delay 0.5
        do script "cd {script_dir} && uv run python -m agent_monitor.modules.infrastructure" in front window
        set custom title of front window to "Infrastructure"

        -- Tab 3: Content
        tell application "System Events" to keystroke "t" using command down
        delay 0.5
        do script "cd {script_dir} && uv run python -m agent_monitor.modules.content" in front window
        set custom title of front window to "Content"

        -- Tab 4: System Status
        tell application "System Events" to keystroke "t" using command down
        delay 0.5
        do script "cd {script_dir} && uv run python -m agent_monitor.modules.system_status" in front window
        set custom title of front window to "System"
    end tell
    """

    try:
        subprocess.run(
            ["osascript", "-e", applescript],
            check=True,
            capture_output=True,
            text=True
        )
        print("✅ Launched all 4 modules in Terminal.app")
        print("\n📊 Module Overview:")
        print("  Tab 1: Agent Activity    - Floor Guardians + Pleiades Skills")
        print("  Tab 2: Infrastructure    - MCP Servers + Observatory")
        print("  Tab 3: Content           - Audio History + Documentation")
        print("  Tab 4: System Status     - Albedo + VM + Context Files")
        print("\n💡 Press Q in any tab to quit that module")

    except subprocess.CalledProcessError as e:
        print(f"❌ Error launching Terminal.app: {e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ osascript not found. Are you on macOS?")
        sys.exit(1)


def detect_terminal():
    """Detect which terminal application to use."""
    # Check if iTerm2 is running or installed
    try:
        result = subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to get name of processes'],
            capture_output=True,
            text=True,
            check=True
        )
        if "iTerm2" in result.stdout:
            return "iterm"
    except Exception:
        pass

    # Default to Terminal.app
    return "terminal"


def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h"]:
        print(__doc__)
        sys.exit(0)

    print("🚀 Launching Albedo Agent Monitor Modules...")
    print()

    terminal_app = detect_terminal()

    if terminal_app == "iterm":
        print("📱 Detected iTerm2")
        launch_iterm()
    else:
        print("📱 Using Terminal.app")
        launch_terminal()


if __name__ == "__main__":
    main()
