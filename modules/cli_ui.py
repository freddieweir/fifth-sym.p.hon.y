"""
Eye-Grabbing CLI UI

Attention-friendly terminal interface with colors, animations, and visual hierarchy.
Designed for maximum visibility and engagement.
"""

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.layout import Layout
from rich.text import Text
from rich.box import ROUNDED, DOUBLE, HEAVY
from rich.align import Align
from rich import print as rprint
from rich.live import Live
from rich.markdown import Markdown
import time
from typing import Optional, List, Dict, Any
from enum import Enum


class RiskLevel(Enum):
    """Visual risk levels with colors and emojis"""

    LOW = ("🟢", "green", "LOW")
    MEDIUM = ("🟡", "yellow", "MEDIUM")
    HIGH = ("🟠", "bright_red", "HIGH")
    CRITICAL = ("🔴", "bold red on black", "CRITICAL")


class CLIUI:
    """
    Eye-grabbing terminal UI for Fifth Symphony.

    Features:
    - Colorful banners and headers
    - Animated progress indicators
    - Risk-level color coding
    - Attention-friendly visual hierarchy
    - Emoji-rich feedback
    """

    def __init__(self):
        """Initialize CLI UI with Rich console"""
        self.console = Console()

    def show_banner(self):
        """Display eye-grabbing startup banner"""
        banner_text = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🎵  FIFTH SYMPHONY ORCHESTRATOR  🎵                    ║
║                                                           ║
║   AI-Powered Permission & Approval System                ║
║   ═══════════════════════════════════════════════        ║
║                                                           ║
║   🔒 Secure  •  🎨 Visual  •  🔊 Voice-Enabled          ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
        """

        panel = Panel(
            Text(banner_text, style="bold cyan", justify="center"),
            box=HEAVY,
            border_style="bright_magenta",
            padding=(1, 2),
        )

        self.console.print(panel)
        self.console.print()

    def show_permission_request(
        self,
        action: str,
        risk_level: RiskLevel,
        agent: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Display eye-grabbing permission request.

        Args:
            action: Action being requested
            risk_level: Risk level (LOW/MEDIUM/HIGH/CRITICAL)
            agent: Agent making request
            details: Optional additional details
        """
        emoji, color, level_text = risk_level.value

        # Create header
        header = Text()
        header.append("⚡ PERMISSION REQUEST ⚡", style="bold bright_white on blue")

        # Create content
        content = Text()
        content.append(f"\n{emoji} ", style=color)
        content.append("Risk Level: ", style="bold white")
        content.append(f"{level_text}\n\n", style=f"bold {color}")

        content.append("🤖 Agent: ", style="bold cyan")
        content.append(f"{agent}\n\n", style="bright_white")

        content.append("📋 Action: ", style="bold magenta")
        content.append(f"{action}\n\n", style="bright_yellow")

        # Add details if provided
        if details:
            content.append("📝 Details:\n", style="bold cyan")
            for key, value in details.items():
                content.append(f"  • {key}: ", style="dim white")
                content.append(f"{value}\n", style="bright_white")
            content.append("\n")

        # Add decision prompt
        content.append("━" * 50 + "\n", style="dim white")
        content.append("\n🎯 Your Decision:\n\n", style="bold bright_cyan")
        content.append("  [Y]es     ", style="bold green")
        content.append("• Approve this time\n", style="dim green")
        content.append("  [N]o      ", style="bold red")
        content.append("• Deny this time\n", style="dim red")
        content.append("  [A]lways  ", style="bold bright_green")
        content.append("• Auto-approve this pattern\n", style="dim bright_green")
        content.append("  [C]ustom  ", style="bold magenta")
        content.append("• Provide custom instructions\n\n", style="dim magenta")

        # Box style based on risk
        box_styles = {
            RiskLevel.LOW: ("green", ROUNDED),
            RiskLevel.MEDIUM: ("yellow", ROUNDED),
            RiskLevel.HIGH: ("bright_red", HEAVY),
            RiskLevel.CRITICAL: ("bold red on black", DOUBLE),
        }

        border_style, box_type = box_styles[risk_level]

        panel = Panel(
            Align.center(content),
            title=header,
            box=box_type,
            border_style=border_style,
            padding=(1, 2),
        )

        self.console.print(panel)

    def show_approval_granted(self, action: str, agent: str):
        """Show approval granted message"""
        text = Text()
        text.append("✅ ", style="bold green")
        text.append("REQUEST APPROVED", style="bold bright_green")
        text.append(f"\n\n🤖 Agent: {agent}\n", style="cyan")
        text.append(f"📋 Action: {action}\n\n", style="yellow")
        text.append("⏳ Proceeding with execution...", style="dim white")

        panel = Panel(text, box=ROUNDED, border_style="green", padding=(1, 2))

        self.console.print(panel)

    def show_approval_denied(self, action: str, agent: str, reason: Optional[str] = None):
        """Show approval denied message"""
        text = Text()
        text.append("❌ ", style="bold red")
        text.append("REQUEST DENIED", style="bold bright_red")
        text.append(f"\n\n🤖 Agent: {agent}\n", style="cyan")
        text.append(f"📋 Action: {action}\n", style="yellow")

        if reason:
            text.append(f"\n💬 Reason: {reason}\n", style="dim white")

        text.append("\n🛑 Operation cancelled.", style="bold red")

        panel = Panel(text, box=ROUNDED, border_style="red", padding=(1, 2))

        self.console.print(panel)

    def show_status(self, status_type: str, message: str):
        """
        Show status message with appropriate styling.

        Args:
            status_type: success, error, warning, info
            message: Status message
        """
        styles = {
            "success": ("✅", "green", "SUCCESS"),
            "error": ("❌", "red", "ERROR"),
            "warning": ("⚠️", "yellow", "WARNING"),
            "info": ("ℹ️", "cyan", "INFO"),
        }

        emoji, color, label = styles.get(status_type, ("•", "white", "STATUS"))

        text = Text()
        text.append(f"{emoji} {label}: ", style=f"bold {color}")
        text.append(message, style="white")

        self.console.print(text)

    def show_changelog(self, limit: int = 10):
        """
        Display recent changelog entries.

        Args:
            limit: Number of recent entries to show
        """
        try:
            with open("CHANGELOG.md", "r") as f:
                content = f.read()

            md = Markdown(content)

            panel = Panel(
                md,
                title="📜 Recent Changes",
                box=ROUNDED,
                border_style="bright_cyan",
                padding=(1, 2),
            )

            self.console.print(panel)

        except FileNotFoundError:
            self.show_status("error", "CHANGELOG.md not found")

    def show_progress(self, description: str, total: int = 100):
        """
        Show progress bar with animation.

        Args:
            description: Task description
            total: Total progress units

        Returns:
            Progress context manager
        """
        return Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(complete_style="green", finished_style="bold green"),
            TextColumn("[bold]{task.percentage:>3.0f}%"),
            console=self.console,
        )

    def show_table(
        self, title: str, headers: List[str], rows: List[List[str]], style: str = "cyan"
    ):
        """
        Display data in a table.

        Args:
            title: Table title
            headers: Column headers
            rows: Table rows
            style: Border style color
        """
        table = Table(title=title, box=ROUNDED, border_style=style)

        for header in headers:
            table.add_column(header, style="bold")

        for row in rows:
            table.add_row(*row)

        self.console.print(table)

    def show_session_info(self, session_data: Dict[str, Any]):
        """Display current session information"""
        text = Text()
        text.append("🔗 SESSION INFO\n\n", style="bold bright_cyan")

        for key, value in session_data.items():
            text.append(f"  {key}: ", style="dim cyan")
            text.append(f"{value}\n", style="white")

        panel = Panel(text, box=ROUNDED, border_style="cyan", padding=(1, 2))

        self.console.print(panel)

    def clear(self):
        """Clear the console"""
        self.console.clear()

    def animate_thinking(self, message: str = "Processing"):
        """
        Show animated thinking indicator.

        Args:
            message: Message to display while thinking
        """
        with self.console.status(f"[bold cyan]{message}...", spinner="dots"):
            time.sleep(2)  # Simulated processing


# Example usage demonstration
if __name__ == "__main__":
    ui = CLIUI()

    # Show banner
    ui.show_banner()
    time.sleep(1)

    # Show changelog
    ui.show_changelog()
    time.sleep(2)

    # Show permission request
    ui.show_permission_request(
        action="Delete /etc/passwd",
        risk_level=RiskLevel.CRITICAL,
        agent="security-auditor",
        details={
            "File Type": "System credentials",
            "Impact": "System-wide authentication failure",
            "Reversible": "No",
        },
    )
    time.sleep(2)

    # Simulate approval
    ui.show_approval_granted("Delete /etc/passwd", "security-auditor")
    time.sleep(1)

    # Show status messages
    ui.show_status("success", "Operation completed successfully")
    ui.show_status("warning", "Resource usage high")
    ui.show_status("error", "Connection timeout")
    ui.show_status("info", "New update available")
