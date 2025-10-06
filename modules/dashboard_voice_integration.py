"""
Dashboard Voice Integration

Integrates voice permission system with Textual dashboard chat pane.
Provides visual permission prompts and voice output for LLM responses.
"""

import asyncio
import logging
from typing import Optional
from textual.widgets import Static, Input, Button
from textual.containers import Container, Horizontal
from textual.reactive import reactive
from rich.panel import Panel
from rich.text import Text

from modules.voice_permission_hook import (
    VoicePermissionHook,
    VoicePermissionRequest,
    VoicePermissionResponse
)
from modules.voice_handler import VoiceHandler

logger = logging.getLogger(__name__)


class VoicePermissionPrompt(Static):
    """
    Visual permission prompt widget for dashboard.

    Displays voice permission request with response options:
    - (y) Yes - Speak this time
    - (n) No - Don't speak
    - (a) Always - Auto-approve similar
    - (v) Never - Auto-deny similar
    - (m) Mute - Mute voice system
    """

    # Reactive state
    show_prompt = reactive(False)
    request_pending = reactive(False)

    def __init__(self):
        super().__init__()
        self.current_request: Optional[VoicePermissionRequest] = None
        self.response_future: Optional[asyncio.Future] = None

    def render(self):
        """Render permission prompt."""
        if not self.show_prompt or not self.current_request:
            return ""

        request = self.current_request
        parsed = request.parsed

        # Build prompt content
        content = Text()

        # Header
        content.append("🎤 Voice Permission Request\n\n", style="bold cyan")

        # Voice output preview
        content.append("Would speak: ", style="dim")
        voice_preview = parsed.voice[:150]
        if len(parsed.voice) > 150:
            voice_preview += "..."
        content.append(f"{voice_preview}\n\n", style="white")

        # Metadata
        content.append(f"Complexity: {parsed.complexity_score}/10", style="dim")
        if parsed.has_code:
            content.append(f" | Code: {parsed.code_summary}", style="dim")
        content.append("\n\n")

        # Options
        content.append("Options:\n", style="bold yellow")
        content.append("  (y) Yes - Speak this time\n", style="green")
        content.append("  (n) No - Don't speak\n", style="red")
        content.append("  (a) Always - Auto-approve similar\n", style="cyan")
        content.append("  (v) Never - Auto-deny similar\n", style="magenta")
        content.append("  (m) Mute - Mute voice system\n", style="dim")

        return Panel(
            content,
            title="[bold]🔊 Voice System[/bold]",
            border_style="cyan"
        )

    async def show_permission_request(
        self,
        request: VoicePermissionRequest
    ) -> VoicePermissionResponse:
        """
        Show permission request and wait for user response.

        Args:
            request: Voice permission request

        Returns:
            User's response
        """
        self.current_request = request
        self.show_prompt = True
        self.request_pending = True

        # Create future for response
        self.response_future = asyncio.Future()

        # Wait for user response
        response = await self.response_future

        # Hide prompt
        self.show_prompt = False
        self.request_pending = False
        self.current_request = None

        return response

    async def on_key(self, event):
        """Handle keyboard input for permission response."""
        if not self.request_pending:
            return

        key = event.key.lower()

        response = None

        if key == "y":
            response = VoicePermissionResponse.YES
        elif key == "n":
            response = VoicePermissionResponse.NO
        elif key == "a":
            response = VoicePermissionResponse.ALWAYS
        elif key == "v":
            response = VoicePermissionResponse.NEVER
        elif key == "m":
            response = VoicePermissionResponse.MUTE

        if response and self.response_future:
            self.response_future.set_result(response)


class VoiceDashboardIntegration:
    """
    Integrates voice system with dashboard.

    Features:
    - Visual permission prompts
    - Voice output for chat messages
    - Auto-approve pattern management
    - Voice system status display
    """

    def __init__(
        self,
        voice_handler: VoiceHandler,
        config: Optional[dict] = None
    ):
        """
        Initialize dashboard voice integration.

        Args:
            voice_handler: VoiceHandler instance
            config: Configuration dictionary
        """
        self.voice_handler = voice_handler
        self.config = config or {}

        # Permission prompt widget (to be added to dashboard)
        self.permission_prompt = VoicePermissionPrompt()

        # Voice permission hook
        self.voice_hook = VoicePermissionHook(
            voice_handler=voice_handler,
            config=config,
            permission_callback=self._permission_callback
        )

    async def _permission_callback(
        self,
        request: VoicePermissionRequest
    ) -> VoicePermissionResponse:
        """
        Permission callback for voice hook.

        Shows visual prompt in dashboard.

        Args:
            request: Voice permission request

        Returns:
            User's response
        """
        return await self.permission_prompt.show_permission_request(request)

    async def on_chat_message(self, message: str, username: str = "Unknown"):
        """
        Handle incoming chat message.

        If message is from LLM, offer to speak it.

        Args:
            message: Chat message content
            username: Message sender
        """
        # Only voice LLM responses (not user messages)
        llm_usernames = [
            "Fifth-Symphony",
            "Nazarick-Agent",
            "Code-Assistant",
            "VM-Claude"
        ]

        if username in llm_usernames:
            # Process through voice hook
            await self.voice_hook.on_response(
                message,
                context={"username": username, "source": "dashboard_chat"}
            )

    def get_permission_prompt_widget(self) -> VoicePermissionPrompt:
        """
        Get permission prompt widget for dashboard.

        Returns:
            VoicePermissionPrompt widget
        """
        return self.permission_prompt

    def unmute(self):
        """Unmute voice system."""
        self.voice_hook.unmute()

    def get_status(self) -> dict:
        """
        Get voice system status.

        Returns:
            Status dictionary
        """
        return {
            "muted": self.voice_hook.is_muted,
            "auto_approve_patterns": len(self.voice_hook.get_auto_approve_patterns()),
            "complexity_threshold": self.voice_hook.complexity_threshold
        }


# Example integration with dashboard
class VoiceIntegratedChatPane(Static):
    """
    Enhanced chat pane with voice integration.

    Extends standard ChatPane with voice output capabilities.
    """

    def __init__(
        self,
        server_url: str,
        voice_integration: VoiceDashboardIntegration
    ):
        super().__init__()
        self.server_url = server_url
        self.voice_integration = voice_integration

    async def on_message_received(self, data: dict):
        """
        Handle received chat message.

        Args:
            data: Message data from WebSocket
        """
        username = data.get("username", "Unknown")
        content = data.get("content", "")

        # Display message visually (implement standard chat display)
        # ... (chat display logic)

        # Offer to voice the message
        await self.voice_integration.on_chat_message(content, username)
