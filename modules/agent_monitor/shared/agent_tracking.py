"""Track active agents and skills from status files."""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

# Dynamic path resolution for ai-bedo repository
ALBEDO_ROOT = Path(os.getenv("ALBEDO_ROOT", Path.home() / "git" / "internal" / "repos" / "ai-bedo"))


class AgentTracker:
    """Monitor agent and skill activity from status JSON files."""

    def __init__(self):
        self.status_dir = ALBEDO_ROOT / "communications" / ".agent-status"
        self.active_agents: set[str] = set()
        self.active_skills: set[str] = set()
        self.agent_last_used: dict[str, datetime] = {}
        self.skill_last_used: dict[str, datetime] = {}

    def load_status(self):
        """Load current agent/skill status from JSON files.

        Scans the status directory for agent/skill activity within the last 24 hours.
        Marks agents as "active" if used within last 5 minutes.
        """
        self.active_agents.clear()
        self.active_skills.clear()

        if not self.status_dir.exists():
            return

        cutoff_time = datetime.now() - timedelta(hours=24)
        active_cutoff = datetime.now() - timedelta(minutes=5)

        try:
            for status_file in self.status_dir.glob("*.json"):
                try:
                    file_mtime = datetime.fromtimestamp(status_file.stat().st_mtime)

                    # Skip files older than 24 hours
                    if file_mtime < cutoff_time:
                        continue

                    with open(status_file) as f:
                        status = json.load(f)

                    agent_name = status.get("name")
                    agent_type = status.get("type")

                    # Track last used time
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

                except (json.JSONDecodeError, OSError):
                    continue

        except OSError:
            pass
