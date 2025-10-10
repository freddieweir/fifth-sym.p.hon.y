"""
MCP Client for ElevenLabs Voice Synthesis

Integrates with ElevenLabs MCP server for voice feedback.
Handles text-to-speech requests for permission prompts.
"""

import asyncio
import json
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
import tempfile

logger = logging.getLogger(__name__)


class MCPClient:
    """
    Client for ElevenLabs MCP server integration.

    Uses the official ElevenLabs MCP server at:
    $GIT_ROOT/external/mcp/elevenlabs-mcp
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize MCP client.

        Args:
            config: Configuration dictionary with ElevenLabs settings
        """
        self.config = config
        # Default path - override via config if needed
        self.mcp_server_path = Path.home() / "git" / "external" / "mcp" / "elevenlabs-mcp"
        self.voice_id = config.get("voice_id", "default")
        self.api_key_vault_item = config.get("elevenlabs_api_key_item", "ElevenLabs API Key")
        self.logger = logging.getLogger(__name__)

    async def get_api_key(self) -> str:
        """
        Retrieve ElevenLabs API key from 1Password.

        Returns:
            API key string
        """
        try:
            # Use 1Password CLI to get API key
            result = subprocess.run(
                ["op", "item", "get", self.api_key_vault_item, "--fields", "credential"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to retrieve API key from 1Password: {e}")
            raise

    async def synthesize_speech(
        self, text: str, output_path: Optional[Path] = None, voice_id: Optional[str] = None
    ) -> Path:
        """
        Synthesize speech using ElevenLabs MCP server.

        Args:
            text: Text to synthesize
            output_path: Optional output file path (temp file if not provided)
            voice_id: Optional voice ID (uses config default if not provided)

        Returns:
            Path to generated audio file
        """
        api_key = await self.get_api_key()
        voice = voice_id or self.voice_id

        # Create temp file if no output path provided
        if output_path is None:
            temp_dir = tempfile.gettempdir()
            output_path = Path(temp_dir) / f"fifth_symphony_tts_{id(text)}.mp3"

        try:
            # Call ElevenLabs MCP server via uvx
            # The MCP server expects JSON-RPC format
            mcp_request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "elevenlabs_text_to_speech",
                    "arguments": {"text": text, "voice_id": voice, "output_path": str(output_path)},
                },
                "id": 1,
            }

            # Run MCP server with request
            process = await asyncio.create_subprocess_exec(
                "uvx",
                "elevenlabs-mcp",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={"ELEVENLABS_API_KEY": api_key},
            )

            stdout, stderr = await process.communicate(json.dumps(mcp_request).encode())

            if process.returncode != 0:
                self.logger.error(f"MCP server error: {stderr.decode()}")
                raise RuntimeError(f"MCP server failed: {stderr.decode()}")

            self.logger.info(f"Generated speech: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Speech synthesis failed: {e}")
            raise

    async def speak(self, text: str, priority: int = 1) -> None:
        """
        Speak text immediately (synthesize and play).

        Args:
            text: Text to speak
            priority: Priority level (higher = more urgent)
        """
        try:
            # Synthesize speech
            audio_path = await self.synthesize_speech(text)

            # Play audio (macOS uses afplay, Linux uses aplay/paplay)
            import platform

            system = platform.system()

            if system == "Darwin":  # macOS
                player = "afplay"
            elif system == "Linux":
                player = "paplay"  # PulseAudio (most modern Linux)
            else:
                self.logger.warning(f"Unsupported platform for audio playback: {system}")
                return

            # Play audio file
            subprocess.run([player, str(audio_path)], check=True)

            # Clean up temp file
            audio_path.unlink()

        except Exception as e:
            self.logger.error(f"Failed to speak text: {e}")
            # Don't raise - voice is nice-to-have, not critical

    async def speak_permission_request(self, action: str, risk_level: str, agent: str) -> None:
        """
        Speak permission request with appropriate tone.

        Args:
            action: Action being requested
            risk_level: Risk level (low/medium/high/critical)
            agent: Agent making the request
        """
        # Craft message based on risk level
        risk_messages = {
            "low": f"{agent} requests permission to {action}. This is a low-risk operation.",
            "medium": f"{agent} requests permission to {action}. Please review.",
            "high": f"Attention: {agent} wants to {action}. This is a high-risk operation. Review carefully.",
            "critical": f"CRITICAL: {agent} is requesting to {action}. This is a dangerous operation. Please confirm.",
        }

        message = risk_messages.get(risk_level, f"{agent} requests: {action}")
        await self.speak(message, priority=2 if risk_level in ["high", "critical"] else 1)
