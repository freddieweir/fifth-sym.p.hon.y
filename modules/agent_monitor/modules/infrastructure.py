"""Infrastructure Monitor - MCP Servers and Observatory Services.

Standalone module showing backend systems and observability infrastructure.
Run with: uv run python -m agent_monitor.modules.infrastructure
"""

import subprocess
import time
from datetime import datetime

from agent_monitor.shared import (
    Colors,
    KeyboardHandler,
    MCPManager,
    ModuleConfig,
    RichTableBuilder,
    Symbols,
)
from agent_monitor.utils.screenshot import take_screenshot
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.text import Text


class InfrastructureMonitor:
    """Monitor MCP Servers and Observatory Services."""

    # Observatory monitoring services
    OBSERVATORY_SERVICES = [
        {"name": "Grafana", "url": "http://localhost:3001", "icon": "📊"},
        {"name": "Prometheus", "url": "http://localhost:9090", "icon": "📈"},
        {"name": "Loki", "url": "http://localhost:3100", "icon": "📝"},
        {"name": "Tempo", "url": "http://localhost:3200", "icon": "🔍"},
        {"name": "Mimir", "url": "http://localhost:9009", "icon": "💾"},
        {"name": "Alertmanager", "url": "http://localhost:9093", "icon": "🚨"},
        {"name": "Node Exporter", "url": "http://localhost:9100/metrics", "icon": "🖥️"},
    ]

    def __init__(self):
        self.console = Console()
        self.config = ModuleConfig()
        self.mcp_manager = MCPManager()
        self.running = True
        self.last_refresh = datetime.now()

        # Navigation state
        self.focused_panel = None  # "mcp" or "observatory"
        self.selected_row = 0

        # Load initial data
        self.mcp_manager.load_servers()

    def create_mcp_table(self):
        """Create MCP Servers status table."""
        is_focused = self.focused_panel == "mcp"
        border_style = Colors.ACCENT if is_focused else Colors.SECONDARY

        table = RichTableBuilder.create_table(
            border_style=border_style,
            columns=[
                ("St", {"justify": "center", "style": Colors.SUCCESS, "width": 3}),
                ("Server", {"style": Colors.SECONDARY, "width": 15}),
                ("Command", {"style": Colors.DIM, "overflow": "ellipsis"})
            ]
        )

        for idx, server in enumerate(self.mcp_manager.servers):
            status_symbol = Symbols.ACTIVE if server["status"] == "connected" else Symbols.IDLE

            # Highlight selected row if focused
            if is_focused and idx == self.selected_row:
                style = f"bold {Colors.ACCENT} on black"
                table.add_row(
                    f"[{style}]{status_symbol}[/{style}]",
                    f"[{style}]{server['name']}[/{style}]",
                    f"[{style}]{server['command']}[/{style}]"
                )
            else:
                table.add_row(status_symbol, server["name"], server["command"])

        if not self.mcp_manager.servers:
            table.add_row(Symbols.IDLE, "No servers", "-")

        return table

    def create_observatory_table(self):
        """Create Observatory Services status table."""
        is_focused = self.focused_panel == "observatory"
        border_style = Colors.ACCENT if is_focused else Colors.PRIMARY

        table = RichTableBuilder.create_table(
            border_style=border_style,
            columns=[
                ("St", {"justify": "center", "style": Colors.SUCCESS, "width": 3}),
                ("Service", {"style": Colors.SECONDARY, "width": 15}),
                ("URL", {"style": Colors.DIM, "overflow": "ellipsis"})
            ]
        )

        for idx, service in enumerate(self.OBSERVATORY_SERVICES):
            # Check if service is running (basic check)
            status = self.check_service_status(service["url"])
            status_symbol = Symbols.ACTIVE if status else Symbols.IDLE

            # Highlight selected row if focused
            if is_focused and idx == self.selected_row:
                style = f"bold {Colors.ACCENT} on black"
                table.add_row(
                    f"[{style}]{status_symbol}[/{style}]",
                    f"[{style}]{service['icon']} {service['name']}[/{style}]",
                    f"[{style}]{service['url']}[/{style}]"
                )
            else:
                table.add_row(
                    status_symbol,
                    f"{service['icon']} {service['name']}",
                    service["url"]
                )

        return table

    def check_service_status(self, url: str) -> bool:
        """Check if service is running (quick check)."""
        try:
            # Extract port from URL
            port = url.split(":")[-1].split("/")[0]
            result = subprocess.run(
                ["lsof", "-i", f":{port}"],
                capture_output=True,
                timeout=0.5
            )
            return result.returncode == 0
        except Exception:
            return False

    def open_url(self, url: str):
        """Open URL in default browser."""
        try:
            subprocess.run(["open", url], check=False)
        except Exception:
            pass

    def handle_selection(self):
        """Handle Enter key on selected item."""
        if self.focused_panel == "observatory" and self.selected_row < len(self.OBSERVATORY_SERVICES):
            service = self.OBSERVATORY_SERVICES[self.selected_row]
            self.open_url(service["url"])

    def move_selection_down(self):
        """Move selection down in focused panel."""
        if self.focused_panel == "mcp":
            max_rows = len(self.mcp_manager.servers)
        elif self.focused_panel == "observatory":
            max_rows = len(self.OBSERVATORY_SERVICES)
        else:
            return

        if self.selected_row < max_rows - 1:
            self.selected_row += 1

    def move_selection_up(self):
        """Move selection up in focused panel."""
        if self.selected_row > 0:
            self.selected_row -= 1

    def create_layout(self):
        """Create module layout with both panels."""
        layout = Layout()

        # Split vertically: header, mcp, observatory, footer
        mcp_size = len(self.mcp_manager.servers) + 3
        observatory_size = len(self.OBSERVATORY_SERVICES) + 3

        layout.split_column(
            Layout(name="header", size=2),
            Layout(name="mcp", size=max(mcp_size, 5)),
            Layout(name="observatory", size=max(observatory_size, 5)),
            Layout(name="footer", size=2)
        )

        # Header
        header_text = Text()
        header_text.append("Infrastructure Monitor", style=f"bold {Colors.PRIMARY}")
        header_text.append(" | ", style=Colors.DIM)
        header_text.append(f"Last refresh: {self.last_refresh.strftime('%H:%M:%S')}", style=Colors.DIM)
        layout["header"].update(header_text)

        # MCP Servers panel
        layout["mcp"].update(
            RichTableBuilder.create_panel(
                self.create_mcp_table(),
                title=f"MCP Servers ({len(self.mcp_manager.servers)})",
                border_style=Colors.SECONDARY
            )
        )

        # Observatory panel
        layout["observatory"].update(
            RichTableBuilder.create_panel(
                self.create_observatory_table(),
                title=f"Observatory Services ({len(self.OBSERVATORY_SERVICES)})",
                border_style=Colors.PRIMARY
            )
        )

        # Footer
        footer_text = Text()
        if self.focused_panel:
            footer_text.append("↑↓/JK", style=f"bold {Colors.ACCENT}")
            footer_text.append(":Navigate  ", style=Colors.DIM)
            footer_text.append("Enter", style=f"bold {Colors.ACCENT}")
            footer_text.append(":Open  ", style=Colors.DIM)
            footer_text.append("Esc", style=f"bold {Colors.ACCENT}")
            footer_text.append(":Unfocus  ", style=Colors.DIM)
        else:
            footer_text.append("Q", style=f"bold {Colors.ACCENT}")
            footer_text.append(":Quit  ", style=Colors.DIM)
            footer_text.append("R", style=f"bold {Colors.ACCENT}")
            footer_text.append(":Refresh  ", style=Colors.DIM)
            footer_text.append("M", style=f"bold {Colors.ACCENT}")
            footer_text.append(":MCP  ", style=Colors.DIM)
            footer_text.append("O", style=f"bold {Colors.ACCENT}")
            footer_text.append(":Observatory  ", style=Colors.DIM)
            footer_text.append("S", style=f"bold {Colors.ACCENT}")
            footer_text.append(":Screenshot", style=Colors.DIM)
        layout["footer"].update(footer_text)

        return layout

    def run(self):
        """Main event loop."""
        with KeyboardHandler() as kbd:
            with Live(
                self.create_layout(),
                console=self.console,
                refresh_per_second=2,
                screen=True
            ) as live:
                while self.running:
                    # Handle keyboard input
                    key = kbd.get_key()

                    if key:
                        if key.lower() == "q":
                            self.running = False
                        elif key.lower() == "r":
                            self.mcp_manager.load_servers()
                            self.last_refresh = datetime.now()
                        elif key.lower() == "s":
                            take_screenshot(self.console, "infrastructure")
                            time.sleep(0.5)
                        elif key.lower() == "m":
                            self.focused_panel = "mcp"
                            self.selected_row = 0
                        elif key.lower() == "o":
                            self.focused_panel = "observatory"
                            self.selected_row = 0
                        elif key == "\x1b":  # Escape
                            self.focused_panel = None
                            self.selected_row = 0
                        elif key == "\n" or key == "\r":  # Enter
                            self.handle_selection()
                        elif self.focused_panel:
                            # Navigation keys
                            if key == "j" or ord(key) == 66:  # j or Down arrow
                                self.move_selection_down()
                            elif key == "k" or ord(key) == 65:  # k or Up arrow
                                self.move_selection_up()

                    # Update display
                    live.update(self.create_layout())
                    time.sleep(0.1)


def main():
    """Entry point for standalone execution."""
    try:
        monitor = InfrastructureMonitor()
        monitor.run()
    except KeyboardInterrupt:
        pass  # Clean exit on Ctrl+C


if __name__ == "__main__":
    main()
