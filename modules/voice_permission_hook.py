"""
Voice Permission Hook

Intercepts LLM responses and requests permission to speak them.
Integrates with permission engine for auto-approve rules and
attention sound notifications.

Attention-optimized with:
- Audio cue notifications
- Auto-approve patterns
- Voice-friendly output parsing
- Non-blocking permission flow
"""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from modules.response_voice_adapter import ParsedResponse, ResponseVoiceAdapter
from modules.voice_handler import VoiceHandler

logger = logging.getLogger(__name__)


class VoicePermissionResponse(Enum):
    """User response to voice permission request."""

    YES = "yes"  # Speak this time
    NO = "no"  # Don't speak this time
    ALWAYS = "always"  # Auto-speak similar responses
    NEVER = "never"  # Never speak similar responses
    MUTE = "mute"  # Mute voice system temporarily


@dataclass
class VoicePermissionRequest:
    """
    Voice permission request data.

    Attributes:
        response_text: Original LLM response
        parsed: Parsed response with visual/voice versions
        context: Optional context about the response
        session_id: Session identifier
    """

    response_text: str
    parsed: ParsedResponse
    context: dict[str, Any]
    session_id: str


class VoicePermissionHook:
    """
    Hooks into LLM response flow to request voice permission.

    Features:
    - Response interception
    - Permission evaluation (auto-approve rules)
    - Attention sound playback
    - Voice-friendly output parsing
    - Auto-approve pattern learning
    """

    def __init__(
        self,
        voice_handler: VoiceHandler,
        config: dict[str, Any] | None = None,
        permission_callback: Callable[[VoicePermissionRequest], asyncio.Future] | None = None,
    ):
        """
        Initialize voice permission hook.

        Args:
            voice_handler: VoiceHandler instance for speech synthesis
            config: Configuration dictionary
            permission_callback: Async function to call for permission (returns VoicePermissionResponse)
        """
        self.voice_handler = voice_handler
        self.config = config or {}
        self.permission_callback = permission_callback

        # Initialize components
        self.voice_adapter = ResponseVoiceAdapter()

        # State
        self.is_muted = False
        self.auto_approve_patterns: dict[str, bool] = {}  # Pattern hash -> approve/deny
        self.session_id = "default"

        # Attention sounds
        self.attention_sounds_enabled = self.config.get("attention_sounds_enabled", True)
        self.attention_sound_path = Path(
            self.config.get(
                "attention_sound_path",
                Path(__file__).parent.parent / "config" / "audio" / "attention_normal.wav",
            )
        )

        # Complexity threshold for auto-voice (0-10)
        self.complexity_threshold = self.config.get("complexity_threshold", 7)

        # Auto-approve threshold (how many times to see pattern before auto-approving)
        self.auto_approve_threshold = self.config.get("auto_approve_threshold", 3)
        self.pattern_counts: dict[str, int] = {}

    async def on_response(self, response: str, context: dict[str, Any] | None = None) -> None:
        """
        Called when LLM generates response.

        Flow:
        1. Parse response for voice-friendliness
        2. Check if muted
        3. Check complexity threshold
        4. Check auto-approve rules
        5. Play attention sound (if configured)
        6. Request permission (if needed)
        7. Speak via VoiceHandler

        Args:
            response: LLM response text (markdown)
            context: Optional context dictionary
        """
        if self.is_muted:
            logger.info("Voice system muted, skipping response")
            return

        # Parse response
        parsed = self.voice_adapter.parse_response(response)

        # Check if response should be voiced (complexity check)
        if not self.voice_adapter.should_voice_response(parsed, self.complexity_threshold):
            logger.info(
                f"Response complexity too high ({parsed.complexity_score}/10), skipping voice"
            )
            return

        # Create permission request
        request = VoicePermissionRequest(
            response_text=response, parsed=parsed, context=context or {}, session_id=self.session_id
        )

        # Check auto-approve rules
        auto_decision = await self._check_auto_approve(request)

        if auto_decision == VoicePermissionResponse.YES:
            logger.info("Auto-approved voice output")
            await self._speak_response(request)
            return

        elif auto_decision == VoicePermissionResponse.NO:
            logger.info("Auto-denied voice output")
            return

        # Need user permission - play attention sound
        if self.attention_sounds_enabled:
            await self._play_attention_sound()

        # Request permission from user
        permission = await self._request_permission(request)

        # Handle permission response
        await self._handle_permission_response(request, permission)

    async def _check_auto_approve(
        self, request: VoicePermissionRequest
    ) -> VoicePermissionResponse | None:
        """
        Check if request matches auto-approve rules.

        Args:
            request: Voice permission request

        Returns:
            VoicePermissionResponse if auto-decided, None if needs user input
        """
        # Generate pattern hash from response characteristics
        pattern_hash = self._generate_pattern_hash(request)

        # Check if pattern has auto-approve rule
        if pattern_hash in self.auto_approve_patterns:
            decision = self.auto_approve_patterns[pattern_hash]
            if decision:
                return VoicePermissionResponse.YES
            else:
                return VoicePermissionResponse.NO

        # Track pattern frequency for future auto-approve
        self.pattern_counts[pattern_hash] = self.pattern_counts.get(pattern_hash, 0) + 1

        # If seen pattern multiple times, suggest auto-approve
        if self.pattern_counts[pattern_hash] >= self.auto_approve_threshold:
            logger.info(
                f"Pattern seen {self.pattern_counts[pattern_hash]} times, consider auto-approving"
            )

        return None

    def _generate_pattern_hash(self, request: VoicePermissionRequest) -> str:
        """
        Generate pattern hash for auto-approve matching.

        Uses response characteristics:
        - Has code
        - Complexity score
        - Response length category

        Args:
            request: Voice permission request

        Returns:
            Pattern hash string
        """
        parsed = request.parsed

        # Categorize length
        length_category = (
            "short" if len(parsed.voice) < 100 else "medium" if len(parsed.voice) < 300 else "long"
        )

        # Complexity category
        complexity_category = (
            "simple"
            if parsed.complexity_score < 4
            else "moderate"
            if parsed.complexity_score < 7
            else "complex"
        )

        return f"{length_category}_{complexity_category}_{'code' if parsed.has_code else 'text'}"

    async def _play_attention_sound(self, sound_type: str = "normal"):
        """
        Play attention sound notification.

        Args:
            sound_type: Type of sound (gentle, normal, urgent)
        """
        try:
            # Try to find appropriate sound file
            sound_files = {
                "gentle": "attention_gentle.wav",
                "normal": "attention_normal.wav",
                "urgent": "attention_urgent.wav",
            }

            sound_file = sound_files.get(sound_type, "attention_normal.wav")
            sound_path = Path(__file__).parent.parent / "config" / "audio" / sound_file

            if not sound_path.exists():
                logger.warning(f"Attention sound not found: {sound_path}")
                return

            # Platform-specific audio playback
            import sys

            if sys.platform == "darwin":
                # macOS - use afplay
                import subprocess

                subprocess.Popen(
                    ["afplay", str(sound_path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            elif sys.platform == "linux":
                # Linux - use aplay or paplay
                import subprocess

                try:
                    subprocess.Popen(
                        ["paplay", str(sound_path)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                except FileNotFoundError:
                    subprocess.Popen(
                        ["aplay", str(sound_path)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )

        except Exception as e:
            logger.error(f"Failed to play attention sound: {e}")

    async def _request_permission(self, request: VoicePermissionRequest) -> VoicePermissionResponse:
        """
        Request permission from user to speak response.

        Args:
            request: Voice permission request

        Returns:
            User's permission response
        """
        if self.permission_callback:
            try:
                # Call user-provided callback
                response = await self.permission_callback(request)
                return response
            except Exception as e:
                logger.error(f"Permission callback error: {e}")
                return VoicePermissionResponse.NO

        # Default: auto-approve if no callback provided
        logger.warning("No permission callback configured, auto-approving")
        return VoicePermissionResponse.YES

    async def _handle_permission_response(
        self, request: VoicePermissionRequest, response: VoicePermissionResponse
    ):
        """
        Handle user's permission response.

        Args:
            request: Original permission request
            response: User's response
        """
        if response == VoicePermissionResponse.YES:
            # Speak this time
            await self._speak_response(request)

        elif response == VoicePermissionResponse.NO:
            # Don't speak
            logger.info("User declined voice output")

        elif response == VoicePermissionResponse.ALWAYS:
            # Auto-approve this pattern in future
            pattern_hash = self._generate_pattern_hash(request)
            self.auto_approve_patterns[pattern_hash] = True
            logger.info(f"Auto-approve pattern created: {pattern_hash}")

            # Also speak this time
            await self._speak_response(request)

        elif response == VoicePermissionResponse.NEVER:
            # Auto-deny this pattern in future
            pattern_hash = self._generate_pattern_hash(request)
            self.auto_approve_patterns[pattern_hash] = False
            logger.info(f"Auto-deny pattern created: {pattern_hash}")

        elif response == VoicePermissionResponse.MUTE:
            # Mute voice system
            self.is_muted = True
            logger.info("Voice system muted")

    async def _speak_response(self, request: VoicePermissionRequest):
        """
        Speak the response using VoiceHandler.

        Args:
            request: Voice permission request
        """
        try:
            # Use voice-friendly version
            voice_text = request.parsed.voice

            # Add code summary if present
            if request.parsed.has_code and request.parsed.code_summary:
                voice_text = f"{voice_text} {request.parsed.code_summary}"

            # Speak via voice handler
            await self.voice_handler.speak(voice_text, priority="normal")

            logger.info(f"Spoke response: {voice_text[:50]}...")

        except Exception as e:
            logger.error(f"Failed to speak response: {e}")

    def unmute(self):
        """Unmute voice system."""
        self.is_muted = False
        logger.info("Voice system unmuted")

    def clear_auto_approve_patterns(self):
        """Clear all auto-approve patterns."""
        self.auto_approve_patterns.clear()
        self.pattern_counts.clear()
        logger.info("Cleared all auto-approve patterns")

    def get_auto_approve_patterns(self) -> dict[str, bool]:
        """
        Get current auto-approve patterns.

        Returns:
            Dictionary of pattern hashes and their approve/deny status
        """
        return self.auto_approve_patterns.copy()

    def set_complexity_threshold(self, threshold: int):
        """
        Set complexity threshold for auto-voicing.

        Args:
            threshold: Complexity threshold (0-10)
        """
        self.complexity_threshold = max(0, min(threshold, 10))
        logger.info(f"Complexity threshold set to: {self.complexity_threshold}")


# Example usage
async def demo():
    """Demonstrate VoicePermissionHook."""
    from modules.voice_handler import VoiceHandler

    # Mock permission callback
    async def mock_permission_callback(request: VoicePermissionRequest) -> VoicePermissionResponse:
        print("\n=== Permission Request ===")
        print(f"Voice output: {request.parsed.voice}")
        print(f"Complexity: {request.parsed.complexity_score}/10")
        print("\nOptions: (y)es, (n)o, (a)lways, (never), (m)ute")

        # For demo, auto-approve
        return VoicePermissionResponse.YES

    # Initialize (would normally use real voice handler)
    voice_handler = VoiceHandler({"enabled": False})
    hook = VoicePermissionHook(
        voice_handler=voice_handler, permission_callback=mock_permission_callback
    )

    # Test response
    response = """
Here's the solution:

```python
def greet(name: str) -> str:
    return f"Hello, {name}!"
```

This function takes a name and returns a greeting.
"""

    await hook.on_response(response, context={"source": "demo"})


if __name__ == "__main__":
    asyncio.run(demo())
