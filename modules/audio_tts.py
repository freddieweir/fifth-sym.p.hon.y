"""Audio TTS module using ElevenLabs Python SDK with 1Password integration."""

import os
import sys
import re
import subprocess
from pathlib import Path
from typing import Optional, List, Dict
from contextlib import contextmanager
import logging
from datetime import datetime

# Suppress httpx INFO logs to prevent voice ID exposure in API request URLs
logging.getLogger("httpx").setLevel(logging.WARNING)

try:
    from elevenlabs.client import ElevenLabs
    from elevenlabs import play, save
except ImportError:
    print("Error: elevenlabs package not found. Install with: uv add elevenlabs")
    sys.exit(1)

from .onepassword_manager import OnePasswordManager
from .smart_media_control import is_anything_playing

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Voice IDs for environment-specific selection
# Original Albedo (v1) → VM files
# Albedo v2 → Main machine files
VOICE_ALBEDO_V1 = "ugizIPhoOxPnNuPGr01h"  # VM (Original Albedo - from "ElevenLabs Voice IDs" vault)
VOICE_ALBEDO_V2 = "Sr4DTtH3Kmyd0sUrsL97"  # Main Mac (Albedo v2 - from "ElevenLabs Voice IDs" vault)

# Media control configuration
DEFAULT_MEDIA_SHORTCUT = "MediaPlayPause"  # Default macOS Shortcut name for media control


def censor_voice_id(voice_id: str) -> str:
    """Censor voice ID for logging to prevent exposure in demos."""
    if voice_id == VOICE_ALBEDO_V1:
        return "Albedo OG"
    elif voice_id == VOICE_ALBEDO_V2:
        return "Albedo v2"
    else:
        return "******"


def detect_environment() -> str:
    """
    Detect if running on Main Mac or VM.

    Returns:
        "main" if on main macOS machine (standard user paths)
        "vm" if on VM (shared volume paths or virtualgit)
    """
    cwd = Path.cwd()
    cwd_str = str(cwd)

    # Check for VM indicators
    vm_indicators = [
        "/Volumes/",  # Any mounted volume
        "virtualgit"  # Virtual git directory
    ]

    for indicator in vm_indicators:
        if indicator in cwd_str:
            logger.info(f"Environment detected: VM (matched: {indicator})")
            return "vm"

    # Check for standard user home directory structure (main Mac)
    if cwd_str.startswith("/Users/"):
        logger.info("Environment detected: Main Mac")
        return "main"

    # Default to main if uncertain
    logger.warning(f"Unable to determine environment from path: {cwd_str}, defaulting to main")
    return "main"


def detect_source_from_filepath(filepath: Path) -> str:
    """
    Detect if file came from VM or main machine based on its path.

    Priority order:
    1. Explicit prefix directories (vm-audio, main-audio, albedos-desk)
    2. VM indicators (mounted volumes, virtualgit)
    3. Standard user home paths (main machine)
    4. Default to main

    Args:
        filepath: Path to the audio file

    Returns:
        "vm" if file is from VM paths, "main" otherwise
    """
    filepath_str = str(filepath.resolve())

    # Priority 1: Explicit prefix directories (most reliable)
    if "vm-audio" in filepath_str or "albedos-desk" in filepath_str:
        logger.info(f"File source detected: VM (explicit directory marker)")
        return "vm"

    if "main-audio" in filepath_str:
        logger.info(f"File source detected: Main Mac (explicit prefix 'main-audio')")
        return "main"

    # Priority 2: Path-based VM indicators
    vm_indicators = [
        "/Volumes/",  # Any mounted volume (VM indicator)
        "virtualgit",  # Virtual git directory
        "claude-agent-reports"  # Agent reports are typically from VM
    ]

    for indicator in vm_indicators:
        if indicator in filepath_str:
            logger.info(f"File source detected: VM (path contains '{indicator}')")
            return "vm"

    # Priority 3: Standard user home paths (main machine)
    if filepath_str.startswith("/Users/"):
        logger.info(f"File source detected: Main Mac (standard user path)")
        return "main"

    # Priority 4: Default to main
    logger.info(f"File source detected: Main Mac (default)")
    return "main"


def get_voice_id_for_environment(env: Optional[str] = None) -> str:
    """
    Get appropriate voice ID based on environment.

    Args:
        env: Environment string ("main" or "vm"). If None, auto-detects.

    Returns:
        Voice ID string for ElevenLabs
    """
    if env is None:
        env = detect_environment()

    if env == "vm":
        voice_id = os.getenv("ELEVENLABS_VOICE_VM", VOICE_ALBEDO_V1)
        logger.info(f"Using VM voice: {censor_voice_id(voice_id)}")
        return voice_id
    else:
        voice_id = os.getenv("ELEVENLABS_VOICE_MAIN", VOICE_ALBEDO_V2)
        logger.info(f"Using Main Mac voice: {censor_voice_id(voice_id)}")
        return voice_id


def get_voice_id_for_filepath(filepath: Path) -> str:
    """
    Get appropriate voice ID based on file path.

    This is used by the audio monitor which runs on main machine
    but processes files from both main and VM.

    Args:
        filepath: Path to the audio file

    Returns:
        Voice ID string for ElevenLabs
    """
    source = detect_source_from_filepath(filepath)
    return get_voice_id_for_environment(source)


class AudioTTSError(Exception):
    """Exception raised for audio TTS errors."""

    pass


class AudioTTS:
    """
    Audio text-to-speech manager using ElevenLabs SDK with automatic media pause/resume.

    This is a reusable module for generating high-quality speech from text, with smart
    features for different environments and automatic media control.

    Key Features:
    - Voice differentiation: Automatically uses different voices for VM vs Main machine
    - Media control: Pauses your music/videos before speaking, resumes after
    - Notification sounds: Plays Blow sound before, Submarine sound after speaking
    - Multi-app support: Works with Music, Safari, Zen Browser, YouTube
    - Keyboard-friendly: Compatible with Karabiner-Elements (uses Shortcuts.app)

    Quick Setup (macOS):
    1. Install ElevenLabs Python SDK: `uv add elevenlabs` or `pip install elevenlabs`
    2. Store your ElevenLabs API key in 1Password:
       - Vault: "API"
       - Item name: "Eleven Labs - API"
       - Field: "credential"
    3. Create a macOS Shortcut named "MediaPlayPause":
       - Open Shortcuts.app
       - Create new shortcut with single "Play/Pause" action
       - Name it "MediaPlayPause"

    Optional Configuration (environment variables):
    - ELEVENLABS_VOICE_VM: Voice ID for VM speech (default: Albedo v1)
    - ELEVENLABS_VOICE_MAIN: Voice ID for Main machine (default: Albedo v2)
    - MEDIA_SHORTCUT: Custom shortcut name (default: "MediaPlayPause")

    Example Usage:
        from modules.audio_tts import AudioTTS

        # Simple usage - auto-detects environment and voice
        tts = AudioTTS(auto_play=True)
        tts.generate_speech("Hello world!")

        # Advanced - specify voice and no auto-play
        tts = AudioTTS(voice_id="your-voice-id", auto_play=False)
        audio_file = tts.generate_speech("Custom voice")
        print(f"Saved to: {audio_file}")
    """

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        voice_id: Optional[str] = None,
        model: str = "eleven_monolingual_v1",
        auto_play: bool = True,
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.3,
        use_speaker_boost: bool = True,
        speed: float = 0.85,
        media_shortcut: Optional[str] = None,
        notification_mode: str = "both",
    ):
        """
        Initialize AudioTTS.

        Args:
            output_dir: Directory to save audio files (default: ~/.claude/audio-summaries)
            voice_id: ElevenLabs voice ID (default: auto-selected based on environment)
            model: ElevenLabs model to use
            auto_play: Automatically play generated audio with media pause/resume
            stability: Voice stability (0-1, lower = more expressive)
            similarity_boost: Voice similarity (0-1, higher = closer to original)
            style: Style exaggeration (0-1, higher = more emotion)
            use_speaker_boost: Enable speaker boost for clarity
            speed: Playback speed (0.7-1.2, default 0.85 for slightly slower clarity)
            media_shortcut: Name of macOS Shortcut for media control (default: MediaPlayPause,
                          can override with MEDIA_SHORTCUT env var)
        """
        self.output_dir = output_dir or Path.home() / ".claude" / "audio-summaries"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Voice settings with environment-aware selection
        if voice_id:
            # Explicit voice ID provided
            self.voice_id = voice_id
        else:
            # Auto-select based on environment
            # Try ELEVENLABS_VOICE_ID env var first for backward compatibility
            env_voice = os.getenv("ELEVENLABS_VOICE_ID")
            if env_voice:
                self.voice_id = env_voice
            else:
                # Use environment-aware selection
                self.voice_id = get_voice_id_for_environment()

        self.model = model
        self.auto_play = auto_play

        # Voice quality settings (can be overridden by env vars)
        self.stability = float(os.getenv("ELEVENLABS_STABILITY", stability))
        self.similarity_boost = float(os.getenv("ELEVENLABS_SIMILARITY", similarity_boost))
        self.style = float(os.getenv("ELEVENLABS_STYLE", style))
        self.use_speaker_boost = os.getenv("ELEVENLABS_SPEAKER_BOOST", "true").lower() == "true" if os.getenv("ELEVENLABS_SPEAKER_BOOST") else use_speaker_boost
        self.speed = float(os.getenv("ELEVENLABS_SPEED", speed))

        # Media control configuration (env var > parameter > default)
        self.media_shortcut = os.getenv("MEDIA_SHORTCUT", media_shortcut or DEFAULT_MEDIA_SHORTCUT)
        logger.debug(f"Media control shortcut configured: {self.media_shortcut}")

        # Notification sound mode
        self.notification_mode = notification_mode
        logger.debug(f"Notification mode: {notification_mode}")

        # Initialize ElevenLabs client
        try:
            # Initialize 1Password manager with default config
            op_config = {"vault": "API"}  # API credentials vault
            op_manager = OnePasswordManager(op_config)

            # Get API key from 1Password (checks env var first, then 1Password)
            # Note: get_api_key() appends " API" to the service name
            api_key = op_manager.get_api_key("Eleven Labs -")

            if not api_key:
                raise AudioTTSError(
                    "ElevenLabs API key not found. "
                    "Set ELEVEN_LABS_API_KEY env var or store in 1Password as 'Eleven Labs - API'"
                )

            self.client = ElevenLabs(api_key=api_key)
            logger.info("ElevenLabs client initialized successfully")
        except AudioTTSError:
            raise
        except Exception as e:
            logger.error(f"Failed to initialize ElevenLabs client: {e}")
            raise AudioTTSError(f"Cannot initialize audio TTS: {e}") from e

    def _toggle_media_playback(self) -> bool:
        """
        Toggle media playback using MediaPlayPause Shortcut.

        Uses macOS Shortcuts.app to control media playback universally across
        all apps: YouTube, Spotify, Music, Safari, Zen Browser, etc.

        Works with Karabiner-Elements since it uses official media control APIs
        instead of simulating key presses.

        Returns:
            True if toggle command was sent successfully, False otherwise
        """
        if sys.platform != "darwin":
            return False

        try:
            # Use Shortcuts.app to toggle media playback
            # This bypasses keyboard remappers like Karabiner-Elements
            result = subprocess.run(
                ["shortcuts", "run", self.media_shortcut],
                capture_output=True,
                timeout=2,
                check=False
            )

            if result.returncode == 0:
                logger.debug(f"Toggled media playback via Shortcuts '{self.media_shortcut}'")
                return True
            else:
                # Log detailed error for troubleshooting
                stderr = result.stderr.decode().strip() if result.stderr else "No error output"
                if "not found" in stderr.lower() or "does not exist" in stderr.lower():
                    logger.warning(
                        f"Shortcut '{self.media_shortcut}' not found. "
                        f"Create it in Shortcuts.app or set MEDIA_SHORTCUT env var. "
                        f"Media will not be paused/resumed."
                    )
                else:
                    logger.debug(f"Shortcuts command failed: {stderr}")
                return False

        except FileNotFoundError:
            # shortcuts command not found (shouldn't happen on macOS Monterey+)
            logger.warning(
                "Shortcuts.app CLI not available. Media pause/resume disabled. "
                "Ensure macOS is Monterey or later."
            )
            return False
        except subprocess.TimeoutExpired:
            logger.warning("Shortcuts command timed out")
            return False
        except Exception as e:
            logger.debug(f"Could not toggle media: {e}")
            return False

    @contextmanager
    def _manage_media_playback(self):
        """
        Smart media pause/resume using MediaPlayPause Shortcut.

        Only pauses media if something is currently playing (prevents Music.app
        from launching when nothing is playing).

        Works with YouTube, Spotify, Music, Safari, and any media app.

        Environment Variables:
            FORCE_MEDIA_CONTROL: Set to "true" to force media pause/resume
                                even if playback detection returns False.
                                Useful for VM environments where detection may not work.
        """
        # Only manage media on macOS
        if sys.platform != "darwin":
            yield
            return

        # Check environment variable for forced media control
        force_control = os.getenv("FORCE_MEDIA_CONTROL", "false").lower() == "true"

        # Check if anything is playing before toggling
        media_was_playing = is_anything_playing()

        if media_was_playing or force_control:
            # Something is playing (or forced) - safe to pause
            if force_control and not media_was_playing:
                logger.debug("Forcing media control (FORCE_MEDIA_CONTROL=true)")
            else:
                logger.debug("Media detected playing - pausing")

            paused = self._toggle_media_playback()

            if paused:
                logger.info("Paused media playback")
        else:
            # Nothing playing - skip pause to avoid launching Music.app
            logger.debug("No media playing - skipping pause")
            paused = False

        try:
            # Allow audio playback to proceed
            yield
        finally:
            # Only resume if we actually paused something
            if paused:
                # Small delay to ensure audio has finished
                import time
                time.sleep(0.5)

                logger.info("Resuming media playback")
                self._toggle_media_playback()

    def clean_text_for_tts(self, text: str) -> str:
        """
        Clean text for natural speech synthesis.

        Removes:
        - Markdown code blocks
        - Inline code
        - Markdown links
        - Headers
        - Bold/italic formatting
        - Special characters

        Expands:
        - Common abbreviations (VS → Visual Studio, VM → Virtual Machine, etc.)
        - Technical terms for better pronunciation

        Args:
            text: Raw text with markdown

        Returns:
            Cleaned text suitable for TTS
        """
        # Remove code blocks
        text = re.sub(r"```[^`]*```", "", text)

        # Remove inline code
        text = re.sub(r"`[^`]*`", "", text)

        # Remove markdown links [text](url) -> text
        text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)

        # Remove markdown headers
        text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)

        # Remove markdown bold/italic
        text = re.sub(r"\*\*([^*]*)\*\*", r"\1", text)
        text = re.sub(r"\*([^*]*)\*", r"\1", text)

        # Remove em/en dashes (replace with space)
        text = text.replace("—", " ").replace("–", " ")

        # Expand common abbreviations for better pronunciation
        # IDE and Editor names
        text = re.sub(r'\bV\s*S\s*Codium\b', 'vee-ess-codium', text, flags=re.IGNORECASE)
        text = re.sub(r'\bVS\s*Code\b', 'vee-ess-code', text, flags=re.IGNORECASE)
        text = re.sub(r'\bV\s*S\s*Code\b', 'vee-ess-code', text, flags=re.IGNORECASE)

        # Virtual Machine
        text = re.sub(r'\bV\s*M\b', 'virtual machine', text)
        text = re.sub(r'\bVMs\b', 'virtual machines', text)

        # Common tech abbreviations
        text = re.sub(r'\bAPI\b', 'A-P-I', text)
        text = re.sub(r'\bAPIs\b', 'A-P-Is', text)
        text = re.sub(r'\bCLI\b', 'C-L-I', text)
        text = re.sub(r'\bGUI\b', 'G-U-I', text)
        text = re.sub(r'\bURL\b', 'U-R-L', text)
        text = re.sub(r'\bURLs\b', 'U-R-Ls', text)
        text = re.sub(r'\bSSH\b', 'S-S-H', text)
        text = re.sub(r'\bHTTP\b', 'H-T-T-P', text)
        text = re.sub(r'\bHTTPS\b', 'H-T-T-P-S', text)
        text = re.sub(r'\bJSON\b', 'J-SON', text)
        text = re.sub(r'\bYAML\b', 'yam-ul', text)
        text = re.sub(r'\bSQL\b', 'sequel', text)

        # Operating systems
        text = re.sub(r'\bmacOS\b', 'mac-oh-ess', text)
        text = re.sub(r'\bLinux\b', 'linux', text)

        # Version control
        text = re.sub(r'\bgit\b', 'git', text, flags=re.IGNORECASE)
        text = re.sub(r'\bGitHub\b', 'git-hub', text)
        text = re.sub(r'\bGitLab\b', 'git-lab', text)

        # Container tech
        text = re.sub(r'\bDocker\b', 'docker', text)
        text = re.sub(r'\bK8s\b', 'kubernetes', text)
        text = re.sub(r'\bKubernetes\b', 'kubernetes', text)

        # File formats
        text = re.sub(r'\bPDF\b', 'P-D-F', text)
        text = re.sub(r'\bCSV\b', 'C-S-V', text)
        text = re.sub(r'\bXML\b', 'X-M-L', text)

        # Programming languages
        text = re.sub(r'\bJS\b', 'javascript', text)
        text = re.sub(r'\bTS\b', 'typescript', text)
        text = re.sub(r'\bPy\b', 'python', text)

        # Common commands
        text = re.sub(r'\bcd\b', 'change directory', text)
        text = re.sub(r'\bls\b', 'list', text)
        text = re.sub(r'\bpwd\b', 'print working directory', text)
        text = re.sub(r'\bmkdir\b', 'make directory', text)

        # Clean up excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    def extract_audio_summary(self, message: str) -> Optional[str]:
        """
        Extract text after "Audio Summary:" marker.

        Args:
            message: Full message text

        Returns:
            Extracted audio summary text, or None if marker not found
        """
        # Case-insensitive search for "Audio Summary:" with optional colon and emoji prefix
        # Matches: "Audio Summary:", "Audio Summary\n", "🎵 Audio Summary", etc.
        match = re.search(r"(?:🎵\s*)?audio\s+summary[:\s]+(.+)", message, re.IGNORECASE | re.DOTALL)

        if match:
            return match.group(1).strip()

        return None

    def generate_speech(self, text: str, output_file: Optional[Path] = None, source_filepath: Optional[Path] = None) -> Path:
        """
        Generate speech from text using ElevenLabs.

        Args:
            text: Text to convert to speech
            output_file: Optional output file path (auto-generated if not provided)
            source_filepath: Optional path to source file (for voice selection based on location)

        Returns:
            Path to generated audio file

        Raises:
            AudioTTSError: If speech generation fails
        """
        try:
            # Clean text for TTS
            clean_text = self.clean_text_for_tts(text)

            if not clean_text:
                raise AudioTTSError("No text to synthesize after cleaning")

            logger.info(f"Generating speech for text: {clean_text[:100]}...")

            # Auto-generate filename if not provided
            if not output_file:
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                output_file = self.output_dir / f"summary-{timestamp}.mp3"

            # Determine voice ID based on source file path (if provided)
            voice_id = self.voice_id
            if source_filepath:
                voice_id = get_voice_id_for_filepath(source_filepath)
                logger.info(f"Using filepath-based voice selection: {censor_voice_id(voice_id)}")

            # Generate audio using ElevenLabs SDK with voice settings
            from elevenlabs import VoiceSettings

            # Build voice settings - speed parameter may not be in all SDK versions
            voice_settings_params = {
                "stability": self.stability,
                "similarity_boost": self.similarity_boost,
                "style": self.style,
                "use_speaker_boost": self.use_speaker_boost,
            }

            # Try to add speed if supported
            try:
                voice_settings_params["speed"] = self.speed
            except TypeError:
                # Speed parameter not supported in this SDK version
                logger.debug("Speed parameter not supported, using default")

            audio_data = self.client.text_to_speech.convert(
                voice_id=voice_id,
                text=clean_text,
                model_id=self.model,
                voice_settings=VoiceSettings(**voice_settings_params),
            )

            # Save audio to file
            with open(output_file, "wb") as f:
                for chunk in audio_data:
                    f.write(chunk)

            logger.info(f"Audio saved to: {output_file}")

            # Auto-play if enabled (notification mode controlled by self.notification_mode)
            if self.auto_play:
                self.play_audio(output_file)

            return output_file

        except Exception as e:
            logger.error(f"Failed to generate speech: {e}")
            raise AudioTTSError(f"Speech generation failed: {e}") from e

    def _play_audio_raw(self, audio_file: Path, skip_media_management: bool = False) -> None:
        """
        Play audio file with notification sounds (internal method).

        Args:
            audio_file: Path to audio file
            skip_media_management: If True, don't use media pause/resume context manager
        """
        # Play start notification sound (based on notification_mode)
        if self.notification_mode in ["both", "start"]:
            if sys.platform == "darwin":
                # Use macOS system sound - "Blow" is a nice attention-grabbing start sound
                try:
                    subprocess.run(
                        ["afplay", "/System/Library/Sounds/Blow.aiff"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=2,
                        check=False
                    )
                    logger.debug("Played macOS start notification (Blow)")
                except Exception as e:
                    logger.debug(f"Could not play start notification: {e}")

        # macOS: use afplay - BLOCKING to ensure audio completes
        if sys.platform == "darwin":
            subprocess.run(
                ["afplay", str(audio_file)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            logger.info(f"Playing audio: {audio_file}")

            # Play end notification after audio finishes (based on notification_mode)
            if self.notification_mode in ["both", "end"]:
                try:
                    # Use "Submarine" sound for completion (different from "Blow" start notification)
                    subprocess.run(
                        ["afplay", "/System/Library/Sounds/Submarine.aiff"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=2,
                        check=False
                    )
                    logger.debug("Played macOS end notification (Submarine)")
                except Exception as e:
                    logger.debug(f"Could not play end notification: {e}")

            return

        # Linux: try common players
        for player in ["paplay", "aplay", "mpg123", "ffplay"]:
            try:
                subprocess.Popen(
                    [player, str(audio_file)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                logger.info(f"Playing audio with {player}: {audio_file}")
                return
            except FileNotFoundError:
                continue

        logger.warning("No audio player found")

    def play_audio(self, audio_file: Path, skip_media_management: bool = False) -> None:
        """
        Play audio file with notification sounds based on self.notification_mode.

        Automatically pauses any playing media (Music, Safari, Zen Browser)
        before playing audio and resumes after (unless skip_media_management=True).

        Args:
            audio_file: Path to audio file
            skip_media_management: If True, don't pause/resume media (for batch processing)
        """
        try:
            if skip_media_management:
                # Play without media management (caller handles pause/resume)
                self._play_audio_raw(audio_file, skip_media_management=True)
            else:
                # Use media playback manager to pause/resume media apps
                with self._manage_media_playback():
                    self._play_audio_raw(audio_file, skip_media_management=False)

        except Exception as e:
            logger.warning(f"Failed to play audio: {e}")

    def process_message(self, message: str) -> Optional[Path]:
        """
        Process message, extract audio summary if present, and generate speech.

        Args:
            message: Full message text

        Returns:
            Path to generated audio file, or None if no audio summary found
        """
        audio_text = self.extract_audio_summary(message)

        if not audio_text:
            logger.debug("No audio summary found in message")
            return None

        logger.info("Audio summary detected - generating speech")
        return self.generate_speech(audio_text)


def main():
    """CLI entry point for testing audio TTS."""
    import argparse

    parser = argparse.ArgumentParser(description="Nazarick Audio TTS")
    parser.add_argument("text", nargs="?", help="Text to synthesize")
    parser.add_argument("--test", action="store_true", help="Run test with sample message")
    parser.add_argument(
        "--no-play", action="store_true", help="Don't auto-play generated audio"
    )
    parser.add_argument("--voice", help="Voice ID to use")
    args = parser.parse_args()

    # Initialize TTS
    tts = AudioTTS(auto_play=not args.no_play, voice_id=args.voice)

    if args.test:
        # Test with sample message
        test_message = (
            "Here's some preliminary text.\n\n"
            "Audio Summary: This is a test of the audio summary system using the "
            "Python elevenlabs SDK with 1Password service account integration. "
            "If you can hear this, everything is working correctly."
        )
        print("🧪 Testing audio TTS with sample message...\n")
        audio_file = tts.process_message(test_message)

        if audio_file:
            print(f"✅ Audio generated: {audio_file}")
            print(f"📊 File size: {audio_file.stat().st_size} bytes")
        else:
            print("❌ No audio summary found in test message")

    elif args.text:
        # Generate from provided text
        audio_file = tts.generate_speech(args.text)
        print(f"✅ Audio generated: {audio_file}")

    else:
        # Read from stdin (for hook integration)
        message = sys.stdin.read()

        audio_file = tts.process_message(message)

        if audio_file:
            print(f"\n🔊 Audio Summary Generated")
            print(f"File: {audio_file}")
            if tts.auto_play:
                print("Playing audio...")
        else:
            # No audio summary - exit silently
            pass


if __name__ == "__main__":
    main()
