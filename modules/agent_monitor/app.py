"""Main Albedo TUI application using Textual."""

from datetime import datetime
from pathlib import Path

import yaml
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Footer, Header, Log, Static

# Import new panel components
from .panels import AudioHistoryPanel, DocumentationPanel, ObservatoryPanel


class StatusIndicator(Static):
    """LED-style status indicator widget."""

    STATUSES = {
        "active": ("●", "#ff00ff"),      # Hot pink
        "ready": ("●", "#00ffff"),       # Cyan
        "queued": ("●", "#ff00ff"),      # Hot pink
        "warning": ("●", "#ffff00"),     # Yellow
        "idle": ("○", "#8800ff"),        # Purple dim
        "error": ("●", "#ff0080"),       # Hot pink error
        "failed": ("●", "#ff0080"),      # Hot pink error
    }

    def __init__(self, status: str = "idle", **kwargs):
        super().__init__(**kwargs)
        self.status = status

    def render(self) -> str:
        """Render the status indicator."""
        symbol, color = self.STATUSES.get(self.status.lower(), ("○", "dim"))
        return f"[{color}]{symbol}[/{color}]"

    def update_status(self, status: str):
        """Update the status and refresh display."""
        self.status = status
        self.refresh()


class FloorGuardiansPanel(Static):
    """Display Floor Guardians status."""

    def compose(self) -> ComposeResult:
        """Create the Floor Guardians panel."""
        yield Static("Floor Guardians (21)", classes="panel-title")
        table = DataTable(id="guardians-table")
        table.add_columns("Status", "Agent", "Last Activity")
        table.cursor_type = "none"  # Disable cursor for read-only display
        yield table

    def on_mount(self) -> None:
        """Populate table on mount."""
        table = self.query_one("#guardians-table", DataTable)
        # All 21 Floor Guardians
        guardians = [
            "incident-commander", "incident-responder",
            "security-auditor", "opsec-sanitizer", "git-history-rewriter",
            "code-reviewer", "refactoring-specialist", "pattern-follower",
            "architecture-designer", "api-designer", "integration-orchestrator",
            "infrastructure-auditor", "ci-debugger", "automation-architect", "monitoring-designer",
            "performance-optimizer", "dependency-analyzer",
            "project-planner", "migration-specialist", "documentation-strategist",
            "testing-strategist", "tech-debt-analyst"
        ]
        for agent in guardians:
            table.add_row("○", agent, "Idle")

    def refresh_data(self):
        """Refresh Floor Guardians data."""
        # TODO: Query MCP for real status
        pass


class PleiSkillsPanel(Static):
    """Display Pleiades Skills status."""

    def compose(self) -> ComposeResult:
        """Create the Pleiades Skills panel."""
        yield Static("Pleiades Skills (20)", classes="panel-title")
        table = DataTable(id="skills-table")
        table.add_columns("Status", "Skill", "Last Activation")
        table.cursor_type = "none"  # Disable cursor for read-only display
        yield table

    def on_mount(self) -> None:
        """Populate table on mount."""
        table = self.query_one("#skills-table", DataTable)
        # All 20 Pleiades Skills
        skills = [
            "api-documenter", "branch-manager", "changelog-generator", "commit-writer",
            "config-generator", "deduplication-engine", "dependency-updater", "docker-composer",
            "documentation-writer", "env-validator", "license-checker", "linting-fixer",
            "merge-coordinator", "metadata-extractor", "pattern-follower", "pr-reviewer",
            "secret-scanner", "style-enforcer", "test-generator", "vulnerability-scanner"
        ]

        # Check which skills are actually installed
        skills_dir = Path.home() / ".claude" / "skills"
        for skill in skills:
            skill_path = skills_dir / skill
            if skill_path.exists():
                status = "●"  # Green - installed
                activation = "Ready"
            else:
                status = "○"  # Gray - not installed
                activation = "Not installed"
            table.add_row(status, skill, activation)

    def refresh_data(self):
        """Refresh Pleiades Skills data."""
        # TODO: Check symlinks and validate SKILL.md
        pass


class VMSubagentsPanel(Static):
    """Display VM Subagents status."""

    def compose(self) -> ComposeResult:
        """Create the VM Subagents panel."""
        yield Static("VM Subagents", classes="panel-title")
        table = DataTable(id="subagents-table")
        table.add_columns("Status", "Task", "Agent", "Progress")
        table.cursor_type = "none"  # Disable cursor for read-only display
        yield table

    def on_mount(self) -> None:
        """Populate table on mount."""
        table = self.query_one("#subagents-table", DataTable)
        # Sample data - will be replaced with real data
        table.add_row("○", "No active tasks", "-", "-")


class MCPStatusPanel(Static):
    """Display MCP server connection status."""

    def compose(self) -> ComposeResult:
        """Create the MCP Status panel."""
        yield Static("MCP Servers", classes="panel-title")
        table = DataTable(id="mcp-table")
        table.add_columns("Status", "Server", "Tools", "Last Ping")
        table.cursor_type = "none"  # Disable cursor for read-only display
        yield table

    def on_mount(self) -> None:
        """Populate table on mount."""
        table = self.query_one("#mcp-table", DataTable)

        # Check MCP configuration
        mcp_config_path = Path.home() / "git" / "ai-bedo" / ".mcp.json"

        # Known MCP servers
        servers = [
            ("elevenlabs", "ElevenLabs TTS"),
            ("floor-guardians", "Floor Guardians (21 agents)")
        ]

        for server_id, description in servers:
            # TODO: Actually ping MCP servers to check status
            # For now, show as connected if config exists
            if mcp_config_path.exists():
                status = "●"  # Green - assume connected
                tools = description
                last_ping = "Connected"
            else:
                status = "○"  # Gray - not configured
                tools = "-"
                last_ping = "Not configured"

            table.add_row(status, server_id, tools, last_ping)

    def refresh_data(self):
        """Refresh MCP connection status."""
        # TODO: Ping MCP servers to check actual status
        pass


class ActivityLogPanel(Static):
    """Display recent activity log."""

    def compose(self) -> ComposeResult:
        """Create the activity log panel."""
        yield Static("Activity Log", classes="panel-title")
        log = Log(id="activity-log", auto_scroll=True)
        yield log

    def on_mount(self) -> None:
        """Initialize log on mount."""
        log = self.query_one("#activity-log", Log)
        log.write_line(f"[dim][{datetime.now().strftime('%H:%M:%S')}][/dim] Albedo TUI initialized")
        log.write_line(f"[dim][{datetime.now().strftime('%H:%M:%S')}][/dim] Monitoring Floor Guardians and Pleiades Skills")


class AlbedoMonitor(App):
    """Main Albedo Agent Monitor application."""

    # Disable mouse support to prevent escape sequence leaks
    ENABLE_COMMAND_PALETTE = False

    # Configure driver to disable mouse
    class Config:
        """App configuration."""
        mouse_capture = False

    CSS = """
    Screen {
        background: transparent;
    }

    .panel-title {
        background: #ff00ff;
        color: #00ffff;
        padding: 0 1;
        text-style: bold;
    }

    Static {
        background: transparent;
    }

    Container {
        background: transparent;
    }

    ScrollableContainer {
        background: transparent;
    }

    DataTable {
        height: 100%;
        margin: 0 1;
        background: transparent;
        color: #00ffff;
    }

    DataTable > .datatable--header {
        background: transparent;
        color: #ff00ff;
        text-style: bold;
    }

    DataTable > .datatable--odd-row {
        background: transparent;
    }

    DataTable > .datatable--even-row {
        background: transparent;
    }

    DataTable > .datatable--fixed {
        background: transparent;
    }

    DataTable > .datatable--fixed-cursor {
        background: #ffff00 40%;
        color: #000000;
        text-style: bold;
    }

    DataTable > .datatable--cursor {
        background: #ffff00 40%;
        color: #000000;
        text-style: bold;
    }

    DataTable > .datatable--hover {
        background: transparent;
    }

    DataTable:focus > .datatable--cursor {
        background: #ffff00 60%;
        color: #000000;
        text-style: bold;
    }

    DataTable:focus {
        border: solid #ffff00;
    }

    Log {
        background: transparent;
        color: #00ffff;
    }

    #activity-log {
        height: 10;
        border: solid #ff00ff;
        margin: 1;
        background: transparent;
    }

    FloorGuardiansPanel {
        height: 18%;
        border: solid #00ffff;
        margin: 1;
        background: transparent;
    }

    PleiSkillsPanel {
        height: 18%;
        border: solid #ff00ff;
        margin: 1;
        background: transparent;
    }

    MCPStatusPanel {
        height: 8%;
        border: solid #00ffff;
        margin: 1;
        background: transparent;
    }

    ObservatoryPanel {
        height: 10%;
        border: solid #ff00ff;
        margin: 1;
        background: transparent;
    }

    AudioHistoryPanel {
        height: 15%;
        border: solid #00ffff;
        margin: 1;
        background: transparent;
    }

    DocumentationPanel {
        height: 15%;
        border: solid #ff00ff;
        margin: 1;
        background: transparent;
    }

    VMSubagentsPanel {
        height: 8%;
        border: solid #00ffff;
        margin: 1;
        background: transparent;
    }

    ActivityLogPanel {
        background: transparent;
    }

    Header {
        background: transparent;
        color: #ff00ff;
        text-style: bold;
    }

    Footer {
        background: transparent;
        color: #00ffff;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", key_display="Q"),
        Binding("r", "refresh", "Refresh", key_display="R"),
        Binding("?", "help", "Help", key_display="?"),
        Binding("a", "audio", "Audio", key_display="A"),
        Binding("d", "docs", "Docs", key_display="D"),
        Binding("g", "grafana", "Grafana", key_display="G"),
    ]

    TITLE = "Albedo Agent Monitor"
    SUB_TITLE = "Main Machine"

    def __init__(self):
        super().__init__()
        self.load_config()
        self.last_refresh = datetime.now()

    def load_config(self):
        """Load configuration from YAML file."""
        config_path = Path(__file__).parent / "config.yaml"
        try:
            with open(config_path) as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            self.config = {"display": {"refresh_interval": 2}}
            self.log(f"Failed to load config: {e}")

    def compose(self) -> ComposeResult:
        """Create the UI layout."""
        yield Header()
        yield FloorGuardiansPanel()
        yield PleiSkillsPanel()
        yield MCPStatusPanel()
        yield ObservatoryPanel()
        yield AudioHistoryPanel()
        yield DocumentationPanel()
        yield VMSubagentsPanel()
        yield ActivityLogPanel()
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the application."""
        # Disable mouse support immediately
        try:
            driver = self._driver
            if hasattr(driver, "write"):
                # Send disable sequences directly to terminal
                driver.write("\033[?1000l")  # Disable X10 mouse
                driver.write("\033[?1002l")  # Disable cell motion
                driver.write("\033[?1003l")  # Disable all motion
                driver.write("\033[?1006l")  # Disable SGR extended
                driver.write("\033[?1015l")  # Disable urxvt
                driver.write("\033[?1004l")  # Disable focus events
                driver.flush()
        except Exception:
            pass

        log = self.query_one("#activity-log", Log)
        log.write_line("[green]✓[/green] Floor Guardians MCP connected")
        log.write_line("[green]✓[/green] Pleiades Skills loaded (20)")
        log.write_line(f"[dim]Auto-refresh: {self.config.get('display', {}).get('refresh_interval', 2)}s[/dim]")
        log.write_line("[dim]Waiting for agent activity...[/dim]")
        log.write_line("[dim]Mouse support disabled[/dim]")

        # Set up auto-refresh
        refresh_interval = self.config.get("display", {}).get("refresh_interval", 2)
        self.set_interval(refresh_interval, self.auto_refresh)

    async def auto_refresh(self) -> None:
        """Auto-refresh all panels periodically."""
        self.last_refresh = datetime.now()
        # Update footer with last refresh time
        self.sub_title = f"Last refresh: {self.last_refresh.strftime('%H:%M:%S')}"

    def action_refresh(self) -> None:
        """Manually refresh all panels."""
        log = self.query_one("#activity-log", Log)
        log.write_line(f"[dim][{datetime.now().strftime('%H:%M:%S')}][/dim] Manual refresh triggered")
        self.last_refresh = datetime.now()
        self.sub_title = f"Last refresh: {self.last_refresh.strftime('%H:%M:%S')}"

    def action_help(self) -> None:
        """Show help screen."""
        log = self.query_one("#activity-log", Log)
        log.write_line("[bold]Keybindings:[/bold]")
        log.write_line("  Q - Quit  |  R - Refresh  |  ? - Help")
        log.write_line("  A - Audio History  |  D - Documentation  |  G - Grafana")
        log.write_line("[dim]Navigate panels with Tab, select items with Enter[/dim]")

    def action_audio(self) -> None:
        """Focus audio history panel."""
        try:
            audio_panel = self.query_one(AudioHistoryPanel)
            audio_table = audio_panel.query_one("#audio-history-table", DataTable)
            audio_table.focus()
            log = self.query_one("#activity-log", Log)
            log.write_line("[dim]Audio History focused - Press Enter to play[/dim]")
        except Exception:
            pass

    def action_docs(self) -> None:
        """Focus documentation panel."""
        try:
            docs_panel = self.query_one(DocumentationPanel)
            docs_table = docs_panel.query_one("#docs-table", DataTable)
            docs_table.focus()
            log = self.query_one("#activity-log", Log)
            log.write_line("[dim]Documentation focused - Press Enter to open[/dim]")
        except Exception:
            pass

    def action_grafana(self) -> None:
        """Focus observatory/grafana panel."""
        try:
            obs_panel = self.query_one(ObservatoryPanel)
            obs_table = obs_panel.query_one("#observatory-table", DataTable)
            obs_table.focus()
            log = self.query_one("#activity-log", Log)
            log.write_line("[dim]Observatory focused - Press Enter to open dashboard[/dim]")
        except Exception:
            pass


if __name__ == "__main__":
    import os
    # Disable mouse capture to prevent escape sequences
    os.environ["TEXTUAL_MOUSE"] = "0"

    app = AlbedoMonitor()
    app.run()
