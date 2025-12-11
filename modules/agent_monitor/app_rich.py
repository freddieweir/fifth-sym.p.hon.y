"""Albedo Agent Monitor TUI using Rich library (no mouse issues)."""

import os
import sys
import time
import select
import termios
import tty
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import yaml
import subprocess
import threading

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from .utils.relative_time import relative_time
from .utils.screenshot import take_screenshot

# Dynamic path resolution for ai-bedo repository
ALBEDO_ROOT = Path(os.getenv("ALBEDO_ROOT", Path.home() / "git" / "internal" / "repos" / "ai-bedo"))


class AlbedoMonitorRich:
    """Main Albedo Agent Monitor application using Rich."""

    def __init__(self):
        self.console = Console()
        self.running = True
        self.last_refresh = datetime.now()

        # Navigation state
        self.focused_panel = None  # Which panel has focus: "audio", "docs", "observatory"
        self.selected_row = 0  # Which row is selected in focused panel

        # Paths
        self.screenshot_dir = ALBEDO_ROOT / "screenshots"

        self.load_config()

        # State for interactive panels
        self.audio_files = []
        self.doc_files = []
        self.observatory_services = []
        self.mcp_servers = []
        self.context_files = []  # Claude Code context files

        # Track active agents/skills
        self.active_agents = set()
        self.active_skills = set()
        self.agent_last_used = {}  # agent_name -> timestamp
        self.skill_last_used = {}  # skill_name -> timestamp

        # Load initial data
        self.load_audio_history()
        self.load_documentation()
        self.load_observatory()
        self.load_mcp_servers()
        self.load_active_agents()  # Load agent usage history
        self.load_context_files()  # Load Claude Code context

    def load_config(self):
        """Load configuration from YAML file."""
        config_path = Path(__file__).parent / "config.yaml"
        try:
            with open(config_path) as f:
                self.config = yaml.safe_load(f)
        except Exception:
            self.config = {"display": {"refresh_interval": 2}}

    def load_audio_history(self):
        """Load audio history files from both active and processed directories."""
        locations = [
            # Check active directories first (unprocessed)
            ALBEDO_ROOT / "communications" / "vm-audio",
            ALBEDO_ROOT / "communications" / "main-audio",
            # Then processed directories
            ALBEDO_ROOT / "communications" / "audio" / ".processed",
            ALBEDO_ROOT / "communications" / "vm-audio" / ".processed",
            ALBEDO_ROOT / "communications" / "main-audio" / ".processed",
            ALBEDO_ROOT / "communications" / "audio" / "Audio" / ".processed",
        ]

        all_files = []

        for location in locations:
            if location.exists():
                for txt_file in location.glob("*.txt"):
                    # Skip files in .processed subdirectories if we already checked the parent
                    all_files.append(txt_file)

        # Sort by modification time and take the 20 most recent
        self.audio_files = sorted(
            all_files,
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )[:20]

    def load_documentation(self):
        """Load documentation files."""
        git_root = Path.home() / "git"
        doc_patterns = [
            "**/CLAUDE.md",
            "**/README.md",
            "**/docs/**/*.md",
        ]

        self.doc_files = []
        for pattern in doc_patterns:
            for md_file in git_root.glob(pattern):
                if not any(x in str(md_file) for x in ["node_modules", ".git", "venv"]):
                    self.doc_files.append(md_file)

        self.doc_files = sorted(self.doc_files, key=lambda x: x.stat().st_mtime, reverse=True)[:30]

    def load_observatory(self):
        """Load observatory/monitoring services."""
        self.observatory_services = [
            {"name": "Grafana", "url": "https://monitoring.corporateseas.com", "port": 3000, "status": "unknown"},
            {"name": "Prometheus", "url": "https://prometheus.corporateseas.com", "port": 9090, "status": "unknown"},
            {"name": "Loki", "url": "https://loki.corporateseas.com", "port": 3100, "status": "unknown"},
            {"name": "Alertmanager", "url": "https://alerts.corporateseas.com", "port": 9093, "status": "unknown"},
            {"name": "cAdvisor", "url": "https://cadvisor.corporateseas.com", "port": 8080, "status": "unknown"},
            {"name": "Node Exporter", "url": "https://node.corporateseas.com", "port": 9100, "status": "unknown"},
            {"name": "Promtail", "url": "https://logs.corporateseas.com", "port": None, "status": "unknown"},
        ]

    def load_mcp_servers(self):
        """Load MCP server configuration from .mcp.json."""
        import json

        self.mcp_servers = []

        # Try multiple possible locations for .mcp.json
        possible_paths = [
            ALBEDO_ROOT / ".mcp.json",
            Path.home() / ".claude" / ".mcp.json",
        ]

        for mcp_config_path in possible_paths:
            if mcp_config_path.exists():
                try:
                    with open(mcp_config_path, 'r') as f:
                        config = json.load(f)

                    for server_name, server_config in config.get("mcpServers", {}).items():
                        self.mcp_servers.append({
                            "name": server_name,
                            "command": server_config.get("command", "unknown"),
                            "status": "unknown"
                        })

                    if self.mcp_servers:
                        break  # Found servers, stop searching
                except Exception:
                    continue  # Try next path

        # Fallback to known servers if config not found
        if not self.mcp_servers:
            self.mcp_servers = [
                {"name": "elevenlabs", "command": "uv", "status": "unknown"},
                {"name": "floor-guardians", "command": "uv", "status": "unknown"},
            ]

    def load_active_agents(self):
        """Load currently active agents and skills from status directory."""
        import json
        from datetime import datetime, timedelta

        self.active_agents = set()
        self.active_skills = set()

        status_dir = ALBEDO_ROOT / "communications" / ".agent-status"
        if not status_dir.exists():
            return

        # Check for recent status files (within last 24 hours for history)
        cutoff_time = datetime.now() - timedelta(hours=24)
        active_cutoff = datetime.now() - timedelta(minutes=5)

        try:
            for status_file in status_dir.glob("*.json"):
                try:
                    file_mtime = datetime.fromtimestamp(status_file.stat().st_mtime)

                    # Skip files older than 24 hours
                    if file_mtime < cutoff_time:
                        continue

                    with open(status_file, 'r') as f:
                        status = json.load(f)

                    agent_name = status.get("name")
                    agent_type = status.get("type")

                    # Track last used time regardless of active status
                    if agent_type == "agent" and agent_name:
                        if agent_name not in self.agent_last_used or file_mtime > self.agent_last_used[agent_name]:
                            self.agent_last_used[agent_name] = file_mtime
                    elif agent_type == "skill" and agent_name:
                        if agent_name not in self.skill_last_used or file_mtime > self.skill_last_used[agent_name]:
                            self.skill_last_used[agent_name] = file_mtime

                    # Mark as active if within 5 minutes
                    if status.get("status") == "active" and file_mtime > active_cutoff:
                        if agent_type == "agent":
                            self.active_agents.add(agent_name)
                        elif agent_type == "skill":
                            self.active_skills.add(agent_name)
                except Exception:
                    continue
        except Exception:
            pass

    def load_context_files(self):
        """Load recently accessed files from Claude Code file-history."""
        from collections import defaultdict

        self.context_files = []

        file_history_dir = Path.home() / ".claude" / "file-history"
        if not file_history_dir.exists():
            return

        try:
            # Find most recent session (by modification time)
            sessions = sorted(
                [s for s in file_history_dir.iterdir() if s.is_dir()],
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )

            if not sessions:
                return

            recent_session = sessions[0]

            # Group files by hash and track latest version + edit count
            file_data = defaultdict(lambda: {"latest_mtime": 0, "version_count": 0, "hash": ""})

            for file_path in recent_session.glob("*@v*"):
                try:
                    parts = file_path.name.split("@")
                    if len(parts) != 2:
                        continue

                    file_hash = parts[0]
                    version = int(parts[1].replace("v", ""))
                    mtime = file_path.stat().st_mtime

                    # Track highest version number and latest mtime
                    if mtime > file_data[file_hash]["latest_mtime"]:
                        file_data[file_hash]["latest_mtime"] = mtime

                    if version > file_data[file_hash]["version_count"]:
                        file_data[file_hash]["version_count"] = version
                        file_data[file_hash]["hash"] = file_hash

                except (ValueError, IndexError):
                    continue

            # Convert to list and sort by most recent access
            self.context_files = [
                {
                    "hash": data["hash"][:8],  # First 8 chars
                    "mtime": data["latest_mtime"],
                    "edits": data["version_count"]
                }
                for hash_key, data in file_data.items()
            ]

            # Sort by most recently accessed, take top 15
            self.context_files = sorted(
                self.context_files,
                key=lambda x: x["mtime"],
                reverse=True
            )[:15]

        except Exception:
            # Silently fail - don't crash TUI if file-history unavailable
            self.context_files = []

    def create_albedo_status_panel(self) -> Table:
        """Create Albedo status LED panel showing Claude's current state."""
        table = Table(box=box.SIMPLE, border_style="magenta", show_header=False, expand=True, padding=(0, 0))
        table.add_column("LED", justify="center", width=4)
        table.add_column("Status", style="cyan", width=12)
        table.add_column("State", style="dim", overflow="ellipsis")

        # Determine current state
        # TODO: Connect to actual Claude state monitoring
        status = "●"
        state_color = "cyan"
        state_text = "Monitoring"
        detail = "Waiting for user input"

        table.add_row(
            f"[{state_color}]{status}[/{state_color}]",
            f"[{state_color}]{state_text}[/{state_color}]",
            detail
        )

        return table

    def create_floor_guardians_table(self) -> Table:
        """Create Floor Guardians status table."""
        table = Table(box=box.SIMPLE, border_style="cyan", show_header=True, expand=True, padding=(0, 0), collapse_padding=True)
        table.add_column("St", justify="center", style="magenta", width=3)
        table.add_column("Agent", style="cyan", overflow="ellipsis")
        table.add_column("Last Used", style="dim", width=10)

        guardians = [
            "incident-commander", "incident-responder",
            "security-auditor", "opsec-sanitizer", "git-history-rewriter",
            "code-reviewer", "refactoring-specialist", "pattern-follower",
            "architecture-designer", "api-designer", "integration-orchestrator",
            "infrastructure-auditor", "ci-debugger", "automation-architect", "monitoring-designer",
            "performance-optimizer", "dependency-analyzer",
            "project-planner", "migration-specialist", "documentation-strategist",
            "testing-strategist"
        ]

        for agent in guardians:  # Show all guardians
            if agent in self.active_agents:
                table.add_row("●", agent, "[green]Active[/green]")
            elif agent in self.agent_last_used:
                # Show relative time since last use
                last_used = relative_time(self.agent_last_used[agent])
                table.add_row("○", agent, last_used)
            else:
                table.add_row("○", agent, "Never")

        return table

    def create_skills_table(self) -> Table:
        """Create Pleiades Skills status table."""
        table = Table(box=box.SIMPLE, border_style="magenta", show_header=True, expand=True, padding=(0, 0), collapse_padding=True)
        table.add_column("St", justify="center", style="green", width=3)
        table.add_column("Skill", style="cyan", overflow="ellipsis")
        table.add_column("Last Used", style="dim", width=10)

        skills = [
            "api-documenter", "branch-manager", "changelog-generator", "commit-writer",
            "config-generator", "deduplication-engine", "dependency-updater", "docker-composer",
            "documentation-writer", "env-validator", "license-checker", "linting-fixer",
            "merge-coordinator", "metadata-extractor", "pattern-follower", "pr-reviewer",
            "secret-scanner", "style-enforcer", "test-generator", "vulnerability-scanner"
        ]

        skills_dir = Path.home() / ".claude" / "skills"
        for skill in skills:  # Show all skills
            skill_path = skills_dir / skill

            # Check if skill is currently active
            if skill in self.active_skills:
                table.add_row("●", skill, "[green]Active[/green]")
            elif skill in self.skill_last_used:
                # Show relative time since last use
                last_used = relative_time(self.skill_last_used[skill])
                table.add_row("●", skill, last_used)
            elif skill_path.exists():
                table.add_row("●", skill, "Ready")
            else:
                table.add_row("○", skill, "Never")

        return table

    def create_mcp_table(self) -> Table:
        """Create MCP servers status table."""
        table = Table(box=box.SIMPLE, border_style="cyan", show_header=True, expand=True, padding=(0, 0), collapse_padding=True)
        table.add_column("St", justify="center", style="green", width=3)
        table.add_column("Server", style="cyan", width=12)
        table.add_column("Command", style="dim", overflow="ellipsis")

        # Debug: Always reload MCP servers to ensure fresh data
        self.load_mcp_servers()

        # Use loaded MCP servers
        if not self.mcp_servers or len(self.mcp_servers) == 0:
            table.add_row("○", "No MCP servers", "-")
        else:
            for server in self.mcp_servers:
                # Assume connected if configured (TODO: check actual connection status)
                status = "●"
                table.add_row(status, server["name"], server["command"])

        return table

    def create_observatory_table(self) -> Table:
        """Create Observatory/Grafana services table."""
        is_focused = self.focused_panel == "observatory"
        border_style = "yellow" if is_focused else "magenta"
        table = Table(box=box.SIMPLE, border_style=border_style, show_header=True, expand=True, padding=(0, 0), collapse_padding=True)
        table.add_column("St", justify="center", style="green", width=3)
        table.add_column("Service", style="cyan", width=10)
        table.add_column("URL", style="dim", overflow="ellipsis")

        for idx, service in enumerate(self.observatory_services):
            status = "●" if service["status"] == "running" else "○"

            # Highlight selected row
            if is_focused and idx == self.selected_row:
                style = "bold yellow on black"
                table.add_row(f"[{style}]{status}[/{style}]",
                              f"[{style}]{service['name']}[/{style}]",
                              f"[{style}]{service['url']}[/{style}]")
            else:
                table.add_row(status, service["name"], service["url"])

        return table

    def create_audio_history_table(self) -> Table:
        """Create Audio History table."""
        is_focused = self.focused_panel == "audio"
        border_style = "yellow" if is_focused else "cyan"
        table = Table(box=box.SIMPLE, border_style=border_style, show_header=True, expand=True, padding=(0, 0), collapse_padding=True)
        table.add_column("Time", style="cyan", width=8, no_wrap=True)
        table.add_column("Proj", style="magenta", width=10, no_wrap=True)
        table.add_column("Message", style="dim", overflow="ellipsis")  # Dynamic width with ellipsis overflow

        for idx, audio_file in enumerate(self.audio_files[:10]):
            try:
                timestamp = datetime.fromtimestamp(audio_file.stat().st_mtime)
                time_str = relative_time(timestamp)

                # Parse filename for project
                parts = audio_file.stem.split("-")
                project = parts[2] if len(parts) > 2 else "unknown"

                # Read first line of content (Rich will handle truncation)
                with open(audio_file, 'r') as f:
                    message = f.readline().strip()

                # Highlight selected row
                if is_focused and idx == self.selected_row:
                    style = "bold yellow on black"
                    table.add_row(f"[{style}]{time_str}[/{style}]",
                                  f"[{style}]{project}[/{style}]",
                                  f"[{style}]{message}[/{style}]")
                else:
                    table.add_row(time_str, project, message)
            except Exception:
                continue

        if not self.audio_files:
            table.add_row("", "", "No audio history found")

        return table

    def create_documentation_table(self) -> Table:
        """Create Documentation browser table."""
        is_focused = self.focused_panel == "docs"
        border_style = "yellow" if is_focused else "magenta"
        table = Table(box=box.SIMPLE, border_style=border_style, show_header=True, expand=True, padding=(0, 0), collapse_padding=True)
        table.add_column("Mod", style="cyan", width=8, no_wrap=True)
        table.add_column("Type", style="magenta", width=10, no_wrap=True)
        table.add_column("File", style="dim", overflow="ellipsis")  # Dynamic width with ellipsis

        for idx, doc_file in enumerate(self.doc_files[:15]):
            try:
                timestamp = datetime.fromtimestamp(doc_file.stat().st_mtime)
                time_str = relative_time(timestamp)

                # Determine type
                if "CLAUDE.md" in doc_file.name:
                    doc_type = "Claude Guide"
                elif "README.md" in doc_file.name:
                    doc_type = "README"
                else:
                    doc_type = "Documentation"

                # Get relative path (Rich will handle truncation)
                try:
                    rel_path = doc_file.relative_to(Path.home() / "git")
                    file_str = str(rel_path)
                except ValueError:
                    file_str = doc_file.name

                # Highlight selected row
                if is_focused and idx == self.selected_row:
                    style = "bold yellow on black"
                    table.add_row(f"[{style}]{time_str}[/{style}]",
                                  f"[{style}]{doc_type}[/{style}]",
                                  f"[{style}]{file_str}[/{style}]")
                else:
                    table.add_row(time_str, doc_type, file_str)
            except Exception:
                continue

        if not self.doc_files:
            table.add_row("", "", "No documentation found")

        return table

    def create_context_table(self) -> Table:
        """Create Claude Code Context Files table."""
        is_focused = self.focused_panel == "context"
        border_style = "yellow" if is_focused else "cyan"
        table = Table(
            box=box.SIMPLE,
            border_style=border_style,
            show_header=True,
            expand=True,
            padding=(0, 0),
            collapse_padding=True
        )
        table.add_column("Hash", style="cyan", width=8, no_wrap=True)
        table.add_column("Accessed", style="magenta", width=10, no_wrap=True)
        table.add_column("Edits", style="dim", width=5, justify="right")

        for idx, context_file in enumerate(self.context_files):
            try:
                time_str = relative_time(context_file["mtime"])
                hash_str = context_file["hash"]
                edits_str = f"v{context_file['edits']}"

                # Highlight selected row if focused
                if is_focused and idx == self.selected_row:
                    style = "bold yellow on black"
                    table.add_row(
                        f"[{style}]{hash_str}[/{style}]",
                        f"[{style}]{time_str}[/{style}]",
                        f"[{style}]{edits_str}[/{style}]"
                    )
                else:
                    table.add_row(hash_str, time_str, edits_str)
            except Exception:
                continue

        if not self.context_files:
            table.add_row("", "No context", "")

        return table

    def create_vm_table(self) -> Table:
        """Create VM Subagents status table."""
        table = Table(box=box.SIMPLE, border_style="cyan", show_header=True, expand=True, padding=(0, 0), collapse_padding=True)
        table.add_column("St", justify="center", style="green", width=3)
        table.add_column("Task", style="cyan", overflow="ellipsis")
        table.add_column("Agent", style="dim", width=12)

        table.add_row("○", "No active tasks", "-")

        return table

    def create_layout(self) -> Layout:
        """Create the main layout."""
        layout = Layout()

        # Split into header, body, footer (minimal header/footer for max content space)
        layout.split(
            Layout(name="header", size=2),
            Layout(name="body"),
            Layout(name="footer", size=2)
        )

        # Header
        header_text = Text()
        header_text.append("Albedo Agent Monitor", style="bold magenta")
        header_text.append(" | ", style="dim")
        header_text.append("Main Machine", style="cyan")
        header_text.append(" | ", style="dim")
        header_text.append(f"Last refresh: {self.last_refresh.strftime('%H:%M:%S')}", style="dim")
        layout["header"].update(Panel(header_text, border_style="magenta", box=box.SIMPLE, padding=(0, 0)))

        # Body - split into panels (dynamic sizing based on actual content)
        # Calculate dynamic sizes: content rows + header + panel title + borders (3 extra lines per panel)
        guardians_size = 21 + 3  # Show all 21 guardians
        skills_size = 20 + 3     # Show all 20 skills
        mcp_size = len(self.mcp_servers) + 3  # Dynamic based on configured servers
        observatory_size = len(self.observatory_services) + 3  # All 7 services
        audio_size = min(len(self.audio_files), 10) + 3  # Up to 10 audio items
        docs_size = min(len(self.doc_files), 15) + 3  # Up to 15 docs
        context_size = min(len(self.context_files), 15) + 3  # Up to 15 context files

        layout["body"].split_column(
            Layout(name="albedo_status", size=4),  # Increased to ensure visibility
            Layout(name="guardians", size=guardians_size),
            Layout(name="skills", size=skills_size),
            Layout(name="mcp", size=max(mcp_size, 5)),  # Minimum 5 lines
            Layout(name="observatory", size=observatory_size),
            Layout(name="audio", size=max(audio_size, 5)),  # Minimum 5 lines
            Layout(name="docs", size=max(docs_size, 5)),  # Minimum 5 lines
            Layout(name="context", size=max(context_size, 5)),  # Minimum 5 lines
            Layout(name="vm", size=3),
        )

        # Populate panels (compact: no padding, simple boxes)
        layout["albedo_status"].update(Panel(
            self.create_albedo_status_panel(),
            title="[magenta]Albedo Status[/magenta]",
            border_style="magenta",
            padding=(0, 0)
        ))

        layout["guardians"].update(Panel(
            self.create_floor_guardians_table(),
            title="[magenta]Floor Guardians (21)[/magenta]",
            border_style="cyan",
            padding=(0, 0)
        ))

        layout["skills"].update(Panel(
            self.create_skills_table(),
            title="[magenta]Pleiades Skills (20)[/magenta]",
            border_style="magenta",
            padding=(0, 0)
        ))

        layout["mcp"].update(Panel(
            self.create_mcp_table(),
            title="[magenta]MCP Servers[/magenta]",
            border_style="cyan",
            padding=(0, 0)
        ))

        layout["observatory"].update(Panel(
            self.create_observatory_table(),
            title="[magenta]Observatory / Grafana[/magenta]",
            border_style="magenta",
            padding=(0, 0)
        ))

        layout["audio"].update(Panel(
            self.create_audio_history_table(),
            title="[magenta]Audio History[/magenta]",
            border_style="cyan",
            padding=(0, 0)
        ))

        layout["docs"].update(Panel(
            self.create_documentation_table(),
            title="[magenta]Documentation[/magenta]",
            border_style="magenta",
            padding=(0, 0)
        ))

        layout["context"].update(Panel(
            self.create_context_table(),
            title="[cyan]Claude Code Context[/cyan]",
            border_style="cyan",
            padding=(0, 0)
        ))

        layout["vm"].update(Panel(
            self.create_vm_table(),
            title="[magenta]VM Subagents[/magenta]",
            border_style="cyan",
            padding=(0, 0)
        ))

        # Footer - show different help based on focus state
        footer_text = Text()
        if self.focused_panel:
            footer_text.append("↑↓/JK", style="bold yellow")
            footer_text.append(":Navigate  ", style="dim")
            footer_text.append("Enter", style="bold yellow")
            footer_text.append(":Select  ", style="dim")
            footer_text.append("Esc", style="bold yellow")
            footer_text.append(":Unfocus  ", style="dim")
            footer_text.append("Q", style="bold yellow")
            footer_text.append(":Quit", style="dim")
        else:
            footer_text.append("Q", style="bold yellow")
            footer_text.append(":Quit  ", style="dim")
            footer_text.append("R", style="bold yellow")
            footer_text.append(":Refresh  ", style="dim")
            footer_text.append("S", style="bold yellow")
            footer_text.append(":Screenshot  ", style="dim")
            footer_text.append("A", style="bold yellow")
            footer_text.append(":Audio  ", style="dim")
            footer_text.append("D", style="bold yellow")
            footer_text.append(":Docs  ", style="dim")
            footer_text.append("C", style="bold yellow")
            footer_text.append(":Context  ", style="dim")
            footer_text.append("G", style="bold yellow")
            footer_text.append(":Grafana", style="dim")
        layout["footer"].update(Panel(footer_text, border_style="cyan", box=box.SIMPLE, padding=(0, 0)))

        return layout

    def move_selection_down(self):
        """Move selection down in focused panel."""
        if self.focused_panel == "audio":
            max_rows = min(len(self.audio_files), 10)
        elif self.focused_panel == "docs":
            max_rows = min(len(self.doc_files), 10)
        elif self.focused_panel == "context":
            max_rows = min(len(self.context_files), 15)
        elif self.focused_panel == "observatory":
            max_rows = len(self.observatory_services)
        else:
            return

        if self.selected_row < max_rows - 1:
            self.selected_row += 1

    def move_selection_up(self):
        """Move selection up in focused panel."""
        if self.selected_row > 0:
            self.selected_row -= 1

    def handle_selection(self):
        """Handle Enter key press on selected item."""
        if self.focused_panel == "audio":
            self.play_audio(self.selected_row)
        elif self.focused_panel == "docs":
            self.open_documentation(self.selected_row)
        elif self.focused_panel == "observatory":
            self.open_observatory_dashboard(self.selected_row)

    def play_audio(self, index: int):
        """Play the selected audio file."""
        if index >= len(self.audio_files):
            return

        audio_file = self.audio_files[index]
        mp3_path = audio_file.with_suffix('.mp3')

        if mp3_path.exists():
            subprocess.Popen(
                ["afplay", str(mp3_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

    def open_documentation(self, index: int):
        """Open the selected documentation file."""
        if index >= len(self.doc_files):
            return

        doc_file = self.doc_files[index]

        # Try Apple Notes first, then VSCodium
        applescript_path = (
            Path.home() / "git" / "internal" / "repos" /
            "applescript-arsenal" / "notes" / "import_markdown.applescript"
        )

        if applescript_path.exists():
            try:
                subprocess.Popen(
                    ["osascript", str(applescript_path), str(doc_file)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return
            except Exception:
                pass

        # Fallback to VSCodium
        subprocess.Popen(
            ["codium", str(doc_file)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    def open_observatory_dashboard(self, index: int):
        """Open the selected observatory/monitoring dashboard."""
        if index >= len(self.observatory_services):
            return

        service = self.observatory_services[index]
        subprocess.Popen(
            ["open", service["url"]],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    def action_screenshot(self):
        """Take a screenshot of the current TUI state."""
        success, svg_path, png_path = take_screenshot(
            self.console,
            self.screenshot_dir,
            title="Albedo Agent Monitor"
        )

        if success:
            if png_path:
                # Both SVG and PNG saved
                filename = png_path.name
                msg = f"Screenshot saved: {filename} (+ SVG)"
            elif svg_path:
                # Only SVG saved (ImageMagick not available)
                filename = svg_path.name
                msg = f"Screenshot saved: {filename}"
            # Note: We can't display notifications in Rich TUI easily,
            # so this will just be logged if we add logging later
        else:
            # Screenshot failed
            msg = "Screenshot failed!"

    def get_key_press(self):
        """Get a single key press (non-blocking)."""
        try:
            if sys.stdin.isatty() and select.select([sys.stdin], [], [], 0.1)[0]:
                return sys.stdin.read(1)
        except Exception:
            pass
        return None

    def run(self):
        """Run the TUI application."""
        old_settings = None

        try:
            # Only set raw mode if we have a real terminal
            if sys.stdin.isatty():
                old_settings = termios.tcgetattr(sys.stdin)
                tty.setcbreak(sys.stdin.fileno())

            with Live(self.create_layout(), console=self.console, refresh_per_second=2, screen=True) as live:
                while self.running:
                    # Check for key press
                    key = self.get_key_press()

                    if key:
                        if key.lower() == 'q':
                            self.running = False
                        elif key.lower() == 'r':
                            self.last_refresh = datetime.now()
                            self.load_audio_history()
                            self.load_documentation()
                            self.load_active_agents()  # Reload active agents/skills
                            self.load_context_files()  # Reload context files
                        elif key.lower() == 'a':
                            # Focus audio panel
                            self.focused_panel = "audio"
                            self.selected_row = 0
                        elif key.lower() == 'd':
                            # Focus docs panel
                            self.focused_panel = "docs"
                            self.selected_row = 0
                        elif key.lower() == 'c':
                            # Focus context panel
                            self.focused_panel = "context"
                            self.selected_row = 0
                        elif key.lower() == 'g':
                            # Focus observatory panel
                            self.focused_panel = "observatory"
                            self.selected_row = 0
                        elif key.lower() == 's':
                            # Take screenshot
                            self.action_screenshot()
                        elif key == '\x1b':  # Escape key
                            # Unfocus any panel
                            self.focused_panel = None
                            self.selected_row = 0
                        elif key == '\n' or key == '\r':  # Enter key
                            # Activate selected item
                            self.handle_selection()
                        elif self.focused_panel:
                            # Arrow key navigation (in focused panel)
                            if key == 'j' or ord(key) == 66:  # j or Down arrow
                                self.move_selection_down()
                            elif key == 'k' or ord(key) == 65:  # k or Up arrow
                                self.move_selection_up()
                        elif key == '?':
                            # Show help
                            pass

                    # Update layout
                    live.update(self.create_layout())
                    time.sleep(0.1)

        except KeyboardInterrupt:
            pass
        finally:
            # Restore terminal settings
            if old_settings:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


def main():
    """Launch the Agent Monitor TUI."""
    app = AlbedoMonitorRich()
    app.run()


if __name__ == "__main__":
    main()
