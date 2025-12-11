"""
Chat integration for orchestrator agent.

Posts updates, permission requests, and approval decisions to shared chat.
"""

import json
import logging

import websockets

logger = logging.getLogger(__name__)


class OrchestratorChatClient:
    """
    Chat client for orchestrator agent.

    Posts updates and requests to shared chat hub.
    """

    def __init__(self, server_url: str = "ws://localhost:8765", username: str = "Fifth-Symphony"):
        """
        Initialize orchestrator chat client.

        Args:
            server_url: WebSocket server URL
            username: Display name (default: Fifth-Symphony)
        """
        self.server_url = server_url
        self.username = username
        self.websocket: websockets.WebSocketClientProtocol | None = None
        self.connected = False

    async def connect(self):
        """Connect to chat server."""
        try:
            self.websocket = await websockets.connect(self.server_url)
            self.connected = True
            logger.info(f"Connected to chat server as {self.username}")
        except Exception as e:
            logger.warning(f"Failed to connect to chat server: {e}")
            self.connected = False

    async def disconnect(self):
        """Disconnect from chat server."""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            logger.info("Disconnected from chat server")

    async def post_message(self, content: str):
        """
        Post message to chat.

        Args:
            content: Message content
        """
        if not self.connected:
            logger.debug(f"Not connected to chat, skipping message: {content}")
            return

        try:
            message = {
                "username": self.username,
                "content": content,
            }
            await self.websocket.send(json.dumps(message))
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Connection closed, reconnecting...")
            self.connected = False
            await self.connect()
        except Exception as e:
            logger.error(f"Error posting message: {e}")

    async def announce_permission_request(
        self, action: str, risk_level: str, agent: str = "Claude Code"
    ):
        """
        Announce permission request to chat.

        Args:
            action: Action being requested
            risk_level: Risk level (LOW/MEDIUM/HIGH/CRITICAL)
            agent: Agent requesting permission
        """
        risk_emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "CRITICAL": "🔴"}

        emoji = risk_emoji.get(risk_level, "⚠️")
        message = f"{emoji} Permission requested: {action} (Risk: {risk_level}) by {agent}"
        await self.post_message(message)

    async def announce_approval(self, action: str):
        """
        Announce approval decision.

        Args:
            action: Action that was approved
        """
        await self.post_message(f"✅ Approved: {action}")

    async def announce_denial(self, action: str, reason: str = ""):
        """
        Announce denial decision.

        Args:
            action: Action that was denied
            reason: Reason for denial (optional)
        """
        message = f"❌ Denied: {action}"
        if reason:
            message += f" (Reason: {reason})"
        await self.post_message(message)

    async def announce_auto_approval(self, action: str):
        """
        Announce auto-approval from stored rules.

        Args:
            action: Action that was auto-approved
        """
        await self.post_message(f"⚡ Auto-approved: {action}")

    async def announce_startup(self):
        """Announce orchestrator startup."""
        await self.post_message("🎵 Orchestrator started and ready")

    async def announce_shutdown(self):
        """Announce orchestrator shutdown."""
        await self.post_message("🎵 Orchestrator shutting down")

    async def announce_error(self, error: str):
        """
        Announce error to chat.

        Args:
            error: Error message
        """
        await self.post_message(f"⚠️ Error: {error}")


# Context manager for orchestrator chat
class OrchestratorChatContext:
    """Context manager for orchestrator chat connection."""

    def __init__(self, server_url: str = "ws://localhost:8765", username: str = "Fifth-Symphony"):
        """
        Initialize chat context.

        Args:
            server_url: WebSocket server URL
            username: Display name
        """
        self.client = OrchestratorChatClient(server_url, username)

    async def __aenter__(self):
        """Connect to chat server."""
        await self.client.connect()
        if self.client.connected:
            await self.client.announce_startup()
        return self.client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Disconnect from chat server."""
        if self.client.connected:
            await self.client.announce_shutdown()
            await self.client.disconnect()
