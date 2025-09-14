"""
Voice Handler Module - Eleven Labs Integration
Provides voice synthesis and feedback capabilities
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

try:
    from elevenlabs import VoiceSettings, generate, stream
    from elevenlabs.client import ElevenLabs

    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False
    logging.warning("ElevenLabs not installed. Voice features disabled.")

logger = logging.getLogger(__name__)


@dataclass(order=True)
class VoiceMessage:
    priority: int
    timestamp: float = field(compare=False)
    message: str = field(compare=False)
    voice_settings: dict = field(default_factory=dict, compare=False)


class VoiceHandler:
    PRIORITY_LEVELS = {"critical": 0, "high": 1, "normal": 2, "low": 3}

    def __init__(self, config: dict[str, Any], op_manager=None):
        self.config = config
        self.op_manager = op_manager
        self.enabled = config.get("enabled", True) and ELEVENLABS_AVAILABLE

        # Voice configuration
        self.voice_id = config.get("voice_id", "Albedo")
        self.model = config.get("model", "eleven_monolingual_v1")
        self.stability = config.get("stability", 0.5)
        self.similarity_boost = config.get("similarity_boost", 0.75)
        self.style = config.get("style", 0.0)
        self.use_speaker_boost = config.get("use_speaker_boost", True)

        # Initialize client
        self.client = None
        self.api_key = None

        # Message queue for prioritization
        self.message_queue = asyncio.Queue()
        self.voice_task = None

        # Load prompt templates
        self.prompts = self._load_prompts()

        # Initialize if enabled
        if self.enabled:
            asyncio.create_task(self._initialize_client())

    def _load_prompts(self) -> dict[str, dict[str, str]]:
        """Load voice prompt templates"""
        prompts = {}
        prompts_dir = Path(__file__).parent.parent / "config" / "prompts"

        if prompts_dir.exists():
            for prompt_file in prompts_dir.glob("*.yaml"):
                with open(prompt_file, encoding="utf-8") as f:
                    category = prompt_file.stem
                    prompts[category] = yaml.safe_load(f) or {}

        # Default prompts if files don't exist
        if not prompts:
            prompts = {
                "system": {
                    "startup": "System initialized and ready.",
                    "shutdown": "Shutting down. Goodbye!",
                    "error": "An error occurred: {error}",
                },
                "reminders": {
                    "gentle": "Hey, just checking in. {script} is still running.",
                    "moderate": "Attention needed. {script} has been running for a while.",
                    "urgent": "Important! {script} needs your attention now.",
                },
                "completion": {
                    "success": "{script} completed successfully!",
                    "failure": "{script} failed with an error.",
                    "partial": "{script} partially completed.",
                },
            }

        return prompts

    async def _initialize_client(self):
        """Initialize ElevenLabs client with API key"""
        if not ELEVENLABS_AVAILABLE:
            self.enabled = False
            return

        # Get API key from 1Password or environment
        if self.op_manager:
            api_key = self.op_manager.get_api_key("Eleven Labs")
        else:
            api_key = os.environ.get("ELEVENLABS_API_KEY")

        if not api_key:
            # Try to load from config file
            api_key = self.config.get("api_key")

        if api_key:
            self.api_key = api_key
            try:
                self.client = ElevenLabs(api_key=api_key)
                logger.info("ElevenLabs client initialized successfully")

                # Start voice processing task
                self.voice_task = asyncio.create_task(self._process_voice_queue())

            except Exception as e:
                logger.error(f"Failed to initialize ElevenLabs: {e}")
                self.enabled = False
        else:
            logger.warning("No ElevenLabs API key found. Voice disabled.")
            self.enabled = False

    async def set_enabled(self, enabled: bool):
        """Enable or disable voice output"""
        self.enabled = enabled and ELEVENLABS_AVAILABLE
        if not self.enabled and self.voice_task:
            self.voice_task.cancel()

    def get_prompt(self, category: str, prompt_key: str, **kwargs) -> str:
        """Get a formatted prompt from templates"""
        if category in self.prompts and prompt_key in self.prompts[category]:
            template = self.prompts[category][prompt_key]
            try:
                return template.format(**kwargs)
            except KeyError:
                return template
        return prompt_key

    async def speak(self, message: str, priority: str = "normal", **voice_overrides):
        """Add a message to the voice queue"""
        if not self.enabled:
            logger.debug(f"Voice disabled. Message: {message}")
            return

        priority_value = self.PRIORITY_LEVELS.get(priority, 2)

        # Apply any voice setting overrides
        voice_settings = {
            "stability": voice_overrides.get("stability", self.stability),
            "similarity_boost": voice_overrides.get("similarity_boost", self.similarity_boost),
            "style": voice_overrides.get("style", self.style),
            "use_speaker_boost": voice_overrides.get("use_speaker_boost", self.use_speaker_boost),
        }

        voice_msg = VoiceMessage(
            priority=priority_value,
            timestamp=asyncio.get_event_loop().time(),
            message=message,
            voice_settings=voice_settings,
        )

        await self.message_queue.put(voice_msg)

    async def _process_voice_queue(self):
        """Process queued voice messages"""
        while True:
            try:
                # Get next message
                msg = await self.message_queue.get()

                # Generate and play audio
                await self._generate_speech(msg.message, msg.voice_settings)

                # Small delay between messages
                await asyncio.sleep(0.5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing voice message: {e}")

    async def _generate_speech(self, text: str, voice_settings: dict):
        """Generate and play speech using ElevenLabs"""
        if not self.client:
            return

        try:
            # Create voice settings
            settings = VoiceSettings(
                stability=voice_settings.get("stability", self.stability),
                similarity_boost=voice_settings.get("similarity_boost", self.similarity_boost),
                style=voice_settings.get("style", self.style),
                use_speaker_boost=voice_settings.get("use_speaker_boost", self.use_speaker_boost),
            )

            # Generate audio
            audio = generate(
                client=self.client,
                text=text,
                voice=self.voice_id,
                model=self.model,
                voice_settings=settings,
            )

            # Play audio (stream directly)
            stream(audio)

        except Exception as e:
            logger.error(f"Failed to generate speech: {e}")

    async def speak_system_message(self, message_type: str, **kwargs):
        """Speak a system message from templates"""
        message = self.get_prompt("system", message_type, **kwargs)
        await self.speak(message, priority="high")

    async def speak_reminder(self, urgency: str, script_name: str):
        """Speak a reminder message"""
        message = self.get_prompt("reminders", urgency, script=script_name)
        priority = (
            "normal" if urgency == "gentle" else "high" if urgency == "moderate" else "critical"
        )
        await self.speak(message, priority=priority)

    async def speak_completion(self, status: str, script_name: str):
        """Speak a completion message"""
        message = self.get_prompt("completion", status, script=script_name)
        await self.speak(message, priority="normal")

    def change_voice(self, voice_id: str):
        """Change the voice being used"""
        self.voice_id = voice_id
        logger.info(f"Voice changed to: {voice_id}")

    def update_voice_settings(self, **settings):
        """Update voice settings"""
        if "stability" in settings:
            self.stability = settings["stability"]
        if "similarity_boost" in settings:
            self.similarity_boost = settings["similarity_boost"]
        if "style" in settings:
            self.style = settings["style"]
        if "use_speaker_boost" in settings:
            self.use_speaker_boost = settings["use_speaker_boost"]

    async def list_available_voices(self) -> list[dict]:
        """Get list of available voices"""
        if not self.client:
            return []

        try:
            voices = self.client.voices.get_all()
            return [{"voice_id": v.voice_id, "name": v.name} for v in voices]
        except Exception as e:
            logger.error(f"Failed to get voices: {e}")
            return []

    async def cleanup(self):
        """Clean up voice handler resources"""
        if self.voice_task:
            self.voice_task.cancel()
            try:
                await self.voice_task
            except asyncio.CancelledError:
                pass

        # Clear any remaining messages
        while not self.message_queue.empty():
            try:
                self.message_queue.get_nowait()
            except Exception:
                break
