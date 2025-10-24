"""
Fifth Symphony Automation Dashboard

Real-time TUI for monitoring and controlling automation services, scripts, and system resources.
Built with Textual for beautiful terminal interfaces.
"""

import psutil
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Static, DataTable, Log
from textual.reactive import reactive
from rich.text import Text
from rich.panel import Panel
from rich.table import Table


class ServiceStatus:
    """Track service status via PID files."""

    def __init__(self, pid_dir: Path = Path("/tmp")):
        self.pid_dir = pid_dir

    def is_running(self, service_name: str) -> bool:
        """Check if service is running."""
        pid_file = self.pid_dir / f"{service_name}.pid"

        if not pid_file.exists():
            return False

        try:
            pid = int(pid_file.read_text().strip())
            return psutil.pid_exists(pid)
        except:
            return False

    def get_process_info(self, service_name: str) -> Optional[Dict]:
        """Get process information for running service."""
        if not self.is_running(service_name):
            return None

        pid_file = self.pid_dir / f"{service_name}.pid"
        try:
            pid = int(pid_file.read_text().strip())
            process = psutil.Process(pid)

            return {
                "pid": pid,
                "cpu": process.cpu_percent(interval=0.1),
                "ram": process.memory_info().rss / 1024 / 1024,  # MB
                "uptime": datetime.now() - datetime.fromtimestamp(process.create_time()),
                "status": process.status(),
            }
        except:
            return None


class ServicePanel(Static):
    """Display service status panel."""

    services = reactive({})

    def __init__(self, title: str, **kwargs):
        super().__init__(**kwargs)
        self.border_title = title

    def compose(self) -> ComposeResult:
        yield Static(id="service-content")

    def on_mount(self) -> None:
        """Set up panel styling."""
        self.styles.border = ("heavy", "cyan")
        self.styles.height = "50%"

    def watch_services(self, services: Dict) -> None:
        """Update service display when services change."""
        content = self.query_one("#service-content", Static)

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Status", style="bold")
        table.add_column("Name")
        table.add_column("Info", style="dim")

        for name, info in services.items():
            if info.get("running"):
                status = "[green]●[/]"
                state = "[green]RUNNING[/]"
                if info.get("cpu") is not None:
                    extra = f"CPU: {info['cpu']:.1f}% | RAM: {info['ram']:.0f}MB"
                else:
                    extra = ""
            else:
                status = "[dim]○[/]"
                state = "[dim]STOPPED[/]"
                extra = ""

            table.add_row(status, f"{name:20}", f"{state:15} {extra}")

        content.update(table)


class SystemStatsPanel(Static):
    """Display system statistics."""

    stats = reactive({})

    def compose(self) -> ComposeResult:
        yield Static(id="stats-content")

    def on_mount(self) -> None:
        """Set up panel styling."""
        self.styles.border = ("heavy", "cyan")
        self.styles.height = "50%"
        self.border_title = "System Status"

    def watch_stats(self, stats: Dict) -> None:
        """Update stats display."""
        content = self.query_one("#stats-content", Static)

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Metric", style="bold cyan")
        table.add_column("Value")

        # CPU
        cpu = stats.get("cpu", 0)
        cpu_bar = "█" * int(cpu / 10) + "░" * (10 - int(cpu / 10))
        table.add_row("CPU", f"[cyan]{cpu_bar}[/] {cpu:.1f}%")

        # RAM
        ram = stats.get("ram", {})
        ram_pct = ram.get("percent", 0)
        ram_bar = "█" * int(ram_pct / 10) + "░" * (10 - int(ram_pct / 10))
        ram_used = ram.get("used_gb", 0)
        ram_total = ram.get("total_gb", 0)
        table.add_row("RAM", f"[green]{ram_bar}[/] {ram_used:.1f}/{ram_total:.1f}GB")

        # Disk
        disk = stats.get("disk", {})
        disk_pct = disk.get("percent", 0)
        disk_bar = "█" * int(disk_pct / 10) + "░" * (10 - int(disk_pct / 10))
        table.add_row("Disk", f"[yellow]{disk_bar}[/] {disk_pct:.1f}%")

        # Power
        power = stats.get("power", "Unknown")
        battery_pct = stats.get("battery_percent")
        if battery_pct:
            power_str = f"{power} ({battery_pct}%)"
        else:
            power_str = power
        table.add_row("Power", power_str)

        content.update(table)


class EventLogPanel(Static):
    """Display event log."""

    def compose(self) -> ComposeResult:
        yield Log(id="event-log")

    def on_mount(self) -> None:
        """Set up panel styling."""
        self.styles.border = ("heavy", "cyan")
        self.styles.height = "30%"
        self.border_title = "Recent Events"

    def add_event(self, level: str, source: str, message: str) -> None:
        """Add event to log."""
        log = self.query_one("#event-log", Log)

        timestamp = datetime.now().strftime("%H:%M:%S")

        # Color by level
        level_colors = {
            "ERROR": "red",
            "WARNING": "yellow",
            "INFO": "blue",
            "DEBUG": "dim",
        }
        color = level_colors.get(level, "white")

        log.write_line(f"[dim]{timestamp}[/] [{color}]{level:7}[/] {source:15} | {message}")


class DashboardApp(App):
    """Fifth Symphony Automation Dashboard."""

    CSS = """
    Screen {
        background: $surface;
    }

    #top-row {
        height: 70%;
        layout: horizontal;
    }

    #services {
        width: 50%;
    }

    #system {
        width: 50%;
    }

    #events {
        height: 30%;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("d", "toggle_dark", "Toggle Dark Mode"),
    ]

    def __init__(self):
        super().__init__()
        self.service_status = ServiceStatus()

        # Services to monitor
        self.services = {
            "audio-monitor": {},
            "voice-listener": {},
            "keyword-listener": {},
            "claude-monitor": {},
        }

    def compose(self) -> ComposeResult:
        """Create dashboard layout."""
        yield Header(show_clock=True)

        with Container(id="top-row"):
            yield ServicePanel("Services", id="services")
            yield SystemStatsPanel(id="system")

        yield EventLogPanel(id="events")
        yield Footer()

    def on_mount(self) -> None:
        """Start monitoring on mount."""
        # Initial update
        self.refresh_all()

        # Set up periodic refresh
        self.set_interval(1.0, self.refresh_all)

        # Welcome message
        events = self.query_one("#events", EventLogPanel)
        events.add_event("INFO", "dashboard", "Fifth Symphony Dashboard started")

    def refresh_all(self) -> None:
        """Refresh all dashboard panels."""
        self.refresh_services()
        self.refresh_system_stats()
        self.check_claude_instances()

    def refresh_services(self) -> None:
        """Update service status."""
        services_panel = self.query_one("#services", ServicePanel)

        updated_services = {}

        for service_name in self.services:
            running = self.service_status.is_running(service_name)
            info = {"running": running}

            if running:
                proc_info = self.service_status.get_process_info(service_name)
                if proc_info:
                    info.update(proc_info)

            updated_services[service_name] = info

        services_panel.services = updated_services

    def refresh_system_stats(self) -> None:
        """Update system statistics."""
        stats_panel = self.query_one("#system", SystemStatsPanel)

        # CPU
        cpu = psutil.cpu_percent(interval=0.1)

        # RAM
        ram = psutil.virtual_memory()
        ram_info = {
            "percent": ram.percent,
            "used_gb": ram.used / 1024**3,
            "total_gb": ram.total / 1024**3,
        }

        # Disk
        disk = psutil.disk_usage('/')
        disk_info = {
            "percent": disk.percent,
            "used_gb": disk.used / 1024**3,
            "total_gb": disk.total / 1024**3,
        }

        # Power
        try:
            result = subprocess.run(
                ["pmset", "-g", "batt"],
                capture_output=True,
                text=True,
                timeout=1,
                check=False
            )
            if "AC Power" in result.stdout:
                power = "🔌 AC Power"
                battery_pct = None
            else:
                power = "🔋 Battery"
                import re
                match = re.search(r'(\d+)%', result.stdout)
                battery_pct = int(match.group(1)) if match else None
        except:
            power = "Unknown"
            battery_pct = None

        stats_panel.stats = {
            "cpu": cpu,
            "ram": ram_info,
            "disk": disk_info,
            "power": power,
            "battery_percent": battery_pct,
        }

    def action_refresh(self) -> None:
        """Manual refresh action."""
        self.refresh_all()
        events = self.query_one("#events", EventLogPanel)
        events.add_event("INFO", "dashboard", "Manual refresh triggered")

    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.dark = not self.dark

    def check_claude_instances(self) -> None:
        """Check for pending Claude Code instances."""
        from pathlib import Path

        # Check for claude-pending flag file
        flag_file = Path("/tmp/claude-pending.flag")

        events = self.query_one("#events", EventLogPanel)

        if flag_file.exists():
            try:
                timestamp = flag_file.read_text().strip()
                # Only alert if flag is recent (within last 30 seconds)
                from datetime import datetime
                flag_time = datetime.fromisoformat(timestamp)
                age = (datetime.now() - flag_time).total_seconds()

                if age < 30:
                    # Check if we already alerted recently
                    if not hasattr(self, '_last_claude_alert'):
                        self._last_claude_alert = None

                    if self._last_claude_alert is None or (datetime.now() - self._last_claude_alert).total_seconds() > 60:
                        events.add_event("WARNING", "claude-monitor", "Claude Code instance waiting for response")
                        self._last_claude_alert = datetime.now()
            except Exception:
                pass


def main():
    """Launch dashboard."""
    app = DashboardApp()
    app.run()


if __name__ == "__main__":
    main()
