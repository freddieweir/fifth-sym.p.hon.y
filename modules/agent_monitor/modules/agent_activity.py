"""Agent Activity Monitor - Floor Guardians and Pleiades Skills.

Standalone module showing AI agent and skill usage.
Run with: uv run python -m agent_monitor.modules.agent_activity
"""

import time
from datetime import datetime
from pathlib import Path

from agent_monitor.shared import (
    AgentTracker,
    Colors,
    KeyboardHandler,
    ModuleConfig,
    RichTableBuilder,
    Symbols,
)
from agent_monitor.utils.relative_time import relative_time
from agent_monitor.utils.screenshot import take_screenshot
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.text import Text


class AgentActivityMonitor:
    """Monitor Floor Guardians and Pleiades Skills activity."""

    # All 21 Floor Guardian agents
    GUARDIANS = [
        "incident-commander", "incident-responder",
        "security-auditor", "opsec-sanitizer", "git-history-rewriter",
        "code-reviewer", "refactoring-specialist", "pattern-follower",
        "architecture-designer", "api-designer", "integration-orchestrator",
        "infrastructure-auditor", "ci-debugger", "automation-architect",
        "monitoring-designer", "performance-optimizer", "dependency-analyzer",
        "project-planner", "migration-specialist", "documentation-strategist",
        "testing-strategist"
    ]

    # All 20 Pleiades Skills
    SKILLS = [
        "api-documenter", "branch-manager", "changelog-generator", "commit-writer",
        "config-generator", "deduplication-engine", "dependency-updater", "docker-composer",
        "documentation-writer", "env-validator", "license-checker", "linting-fixer",
        "merge-coordinator", "metadata-extractor", "pattern-follower", "pr-reviewer",
        "secret-scanner", "style-enforcer", "test-generator", "vulnerability-scanner"
    ]

    def __init__(self):
        self.console = Console()
        self.config = ModuleConfig()
        self.tracker = AgentTracker()
        self.running = True
        self.last_refresh = datetime.now()

        # Load initial data
        self.tracker.load_status()

    def create_guardians_table(self):
        """Create Floor Guardians status table."""
        table = RichTableBuilder.create_table(
            border_style=Colors.SECONDARY,
            columns=[
                ("St", {"justify": "center", "style": Colors.PRIMARY, "width": 3}),
                ("Agent", {"style": Colors.SECONDARY, "overflow": "ellipsis"}),
                ("Last Used", {"style": Colors.DIM, "width": 10})
            ]
        )

        for agent in self.GUARDIANS:
            if agent in self.tracker.active_agents:
                table.add_row(
                    Symbols.ACTIVE,
                    agent,
                    f"[{Colors.SUCCESS}]Active[/{Colors.SUCCESS}]"
                )
            elif agent in self.tracker.agent_last_used:
                last_used = relative_time(self.tracker.agent_last_used[agent])
                table.add_row(Symbols.IDLE, agent, last_used)
            else:
                table.add_row(Symbols.IDLE, agent, "Never")

        return table

    def create_skills_table(self):
        """Create Pleiades Skills status table."""
        table = RichTableBuilder.create_table(
            border_style=Colors.PRIMARY,
            columns=[
                ("St", {"justify": "center", "style": Colors.SUCCESS, "width": 3}),
                ("Skill", {"style": Colors.SECONDARY, "overflow": "ellipsis"}),
                ("Last Used", {"style": Colors.DIM, "width": 10})
            ]
        )

        skills_dir = Path.home() / ".claude" / "skills"

        for skill in self.SKILLS:
            skill_path = skills_dir / skill

            if skill in self.tracker.active_skills:
                table.add_row(
                    Symbols.ACTIVE,
                    skill,
                    f"[{Colors.SUCCESS}]Active[/{Colors.SUCCESS}]"
                )
            elif skill in self.tracker.skill_last_used:
                last_used = relative_time(self.tracker.skill_last_used[skill])
                table.add_row(Symbols.ACTIVE, skill, last_used)
            elif skill_path.exists():
                table.add_row(Symbols.ACTIVE, skill, "Ready")
            else:
                table.add_row(Symbols.IDLE, skill, "Never")

        return table

    def create_layout(self):
        """Create module layout with both panels."""
        layout = Layout()

        # Split vertically: guardians on top, skills on bottom
        layout.split_column(
            Layout(name="header", size=2),
            Layout(name="guardians", size=24),  # 21 rows + header + borders
            Layout(name="skills", size=23),      # 20 rows + header + borders
            Layout(name="footer", size=2)
        )

        # Header
        header_text = Text()
        header_text.append("Agent Activity Monitor", style=f"bold {Colors.PRIMARY}")
        header_text.append(" | ", style=Colors.DIM)
        header_text.append(f"Last refresh: {self.last_refresh.strftime('%H:%M:%S')}", style=Colors.DIM)
        layout["header"].update(header_text)

        # Guardians panel
        layout["guardians"].update(
            RichTableBuilder.create_panel(
                self.create_guardians_table(),
                title=f"Floor Guardians ({len(self.GUARDIANS)})",
                border_style=Colors.SECONDARY
            )
        )

        # Skills panel
        layout["skills"].update(
            RichTableBuilder.create_panel(
                self.create_skills_table(),
                title=f"Pleiades Skills ({len(self.SKILLS)})",
                border_style=Colors.PRIMARY
            )
        )

        # Footer
        footer_text = Text()
        footer_text.append("Q", style=f"bold {Colors.ACCENT}")
        footer_text.append(":Quit  ", style=Colors.DIM)
        footer_text.append("R", style=f"bold {Colors.ACCENT}")
        footer_text.append(":Refresh  ", style=Colors.DIM)
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
                            self.tracker.load_status()
                            self.last_refresh = datetime.now()
                        elif key.lower() == "s":
                            take_screenshot(self.console, "agent_activity")
                            # Brief pause to show screenshot was taken
                            time.sleep(0.5)

                    # Update display
                    live.update(self.create_layout())
                    time.sleep(0.1)


def main():
    """Entry point for standalone execution."""
    try:
        monitor = AgentActivityMonitor()
        monitor.run()
    except KeyboardInterrupt:
        pass  # Clean exit on Ctrl+C


if __name__ == "__main__":
    main()
