"""
Docker container monitoring module.

Provides container status tracking and log streaming with filtering.
"""

import asyncio
import logging
from typing import List, Dict, Optional, AsyncIterator
from datetime import datetime

import docker
from docker.errors import DockerException

logger = logging.getLogger(__name__)


class DockerMonitor:
    """
    Monitor Docker containers with status and log streaming.

    Features:
    - Container status (running/stopped/health)
    - Live log streaming
    - Container filtering by name pattern
    """

    def __init__(self, watched_containers: List[str] = None):
        """
        Initialize Docker monitor.

        Args:
            watched_containers: List of container name patterns to monitor
                               (e.g., ["co-*", "el-*"] for Carian Observatory and EchoLink)
        """
        try:
            self.client = docker.from_env()
            self.connected = True
        except DockerException as e:
            logger.error(f"Failed to connect to Docker: {e}")
            self.connected = False
            self.client = None

        self.watched_containers = watched_containers or []

    def get_container_status(self) -> List[Dict[str, str]]:
        """
        Get status of all watched containers.

        Returns:
            List of dicts with container info (name, status, health, id)
        """
        if not self.connected:
            return []

        statuses = []

        try:
            all_containers = self.client.containers.list(all=True)

            for container in all_containers:
                name = container.name

                # Filter by watched patterns
                if self.watched_containers:
                    if not any(
                        self._matches_pattern(name, pattern) for pattern in self.watched_containers
                    ):
                        continue

                # Get container details
                status = container.status

                # Check health status if available
                health = "N/A"
                if container.attrs.get("State", {}).get("Health"):
                    health = container.attrs["State"]["Health"]["Status"]

                statuses.append(
                    {
                        "name": name,
                        "status": status,
                        "health": health,
                        "id": container.short_id,
                        "image": container.image.tags[0] if container.image.tags else "unknown",
                    }
                )

        except DockerException as e:
            logger.error(f"Error getting container status: {e}")

        return statuses

    def _matches_pattern(self, name: str, pattern: str) -> bool:
        """
        Check if container name matches pattern.

        Supports:
        - Exact match: "container-name"
        - Prefix wildcard: "co-*" matches "co-nginx", "co-redis"
        - Suffix wildcard: "*-service" matches "web-service", "api-service"

        Args:
            name: Container name
            pattern: Pattern to match

        Returns:
            True if name matches pattern
        """
        if pattern == "*":
            return True

        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return name.startswith(prefix)

        if pattern.startswith("*"):
            suffix = pattern[1:]
            return name.endswith(suffix)

        return name == pattern

    async def stream_logs(
        self, container_name: str, lines: int = 50, follow: bool = True
    ) -> AsyncIterator[str]:
        """
        Stream logs from container.

        Args:
            container_name: Container name or ID
            lines: Number of recent lines to fetch (tail)
            follow: Continue streaming new logs

        Yields:
            Log lines as strings
        """
        if not self.connected:
            yield "[ERROR] Not connected to Docker"
            return

        try:
            container = self.client.containers.get(container_name)

            # Stream logs
            for log_line in container.logs(stream=follow, tail=lines, timestamps=True):
                # Decode bytes to string
                line = log_line.decode("utf-8", errors="ignore").strip()
                yield line

                # Small delay to prevent overwhelming the UI
                await asyncio.sleep(0.01)

        except docker.errors.NotFound:
            yield f"[ERROR] Container '{container_name}' not found"
        except DockerException as e:
            yield f"[ERROR] {e}"

    def get_watched_containers(self) -> List[str]:
        """Get list of currently watched container patterns."""
        return self.watched_containers

    def set_watched_containers(self, patterns: List[str]):
        """Update watched container patterns."""
        self.watched_containers = patterns

    def is_connected(self) -> bool:
        """Check if connected to Docker daemon."""
        return self.connected

    async def refresh_connection(self):
        """Attempt to reconnect to Docker."""
        try:
            self.client = docker.from_env()
            self.connected = True
            logger.info("Reconnected to Docker")
        except DockerException as e:
            logger.error(f"Failed to reconnect to Docker: {e}")
            self.connected = False
