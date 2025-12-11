"""MCP server configuration utilities."""

import json
import os
from pathlib import Path
from typing import Any

# Dynamic path resolution for ai-bedo repository
ALBEDO_ROOT = Path(os.getenv("ALBEDO_ROOT", Path.home() / "git" / "internal" / "repos" / "ai-bedo"))


class MCPManager:
    """Load and manage MCP server configurations."""

    def __init__(self):
        self.servers: list[dict[str, Any]] = []

    def load_servers(self):
        """Load MCP servers from .mcp.json configuration.

        Searches common locations for MCP configuration and parses
        server definitions.
        """
        self.servers = []

        possible_paths = [
            ALBEDO_ROOT / ".mcp.json",
            Path.home() / ".claude" / ".mcp.json",
        ]

        for config_path in possible_paths:
            if config_path.exists():
                try:
                    with open(config_path) as f:
                        config = json.load(f)

                    for server_name, server_config in config.get("mcpServers", {}).items():
                        command = server_config.get("command", "unknown")
                        args = server_config.get("args", [])

                        # Build command display (truncate if too long)
                        if args:
                            command_display = f"{command} {' '.join(args[:2])}"
                            if len(args) > 2:
                                command_display += "..."
                        else:
                            command_display = command

                        self.servers.append({
                            "name": server_name,
                            "command": command_display,
                            "status": "connected"  # TODO: implement actual status check
                        })

                    # If we found servers, stop searching
                    if self.servers:
                        break

                except (json.JSONDecodeError, OSError):
                    continue

        # Fallback to known defaults if no config found
        if not self.servers:
            self.servers = [
                {"name": "elevenlabs", "command": "uvx mcp-server-elevenlabs", "status": "unknown"},
                {"name": "floor-guardians", "command": "uv run python -m ...", "status": "unknown"},
            ]
