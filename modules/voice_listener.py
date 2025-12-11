"""Voice listener module with dynamic model switching based on power state."""

import logging
import subprocess
import sys
from collections.abc import Callable
from contextlib import contextmanager

import numpy as np
import pyaudio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class VoiceListenerError(Exception):
    """Exception raised for voice listener errors."""
    pass


class PowerState:
    """Enumeration of power states."""
    AC = "ac"
    BATTERY = "battery"


class VoiceListener:
    """
    Voice command listener with power-aware model selection.

    Features:
    - Dynamic model switching (AC: high performance, Battery: efficient)
    - Real-time audio capture and transcription
    - Simple command parsing
    - MediaPlayPause integration

    Power States:
    - AC Power: Uses Parakeet v3 (future) or MLX-Whisper base
    - Battery High: MLX-Whisper base
    - Battery Low (<20%): MLX-Whisper tiny

    Example:
        listener = VoiceListener()
        listener.listen_continuous()
    """

    def __init__(
        self,
        media_shortcut: str = "MediaPlayPause",
        ac_model: str = "base",  # Will use Parakeet in future
        battery_model: str = "base",
        low_battery_model: str = "tiny",
        low_battery_threshold: int = 20,
        sample_rate: int = 16000,
        chunk_size: int = 1024,
        listen_duration: int = 3,  # seconds per capture
    ):
        """
        Initialize voice listener.

        Args:
            media_shortcut: Name of macOS Shortcut for media control
            ac_model: Model to use on AC power
            battery_model: Model to use on battery (high charge)
            low_battery_model: Model to use on battery (low charge)
            low_battery_threshold: Battery percent to switch to low model
            sample_rate: Audio sample rate (16kHz for speech)
            chunk_size: Audio buffer size
            listen_duration: Seconds to capture per transcription cycle
        """
        self.media_shortcut = media_shortcut
        self.ac_model_name = ac_model
        self.battery_model_name = battery_model
        self.low_battery_model_name = low_battery_model
        self.low_battery_threshold = low_battery_threshold

        # Audio settings
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.listen_duration = listen_duration

        # State
        self.running = False
        self.power_state = None
        self.battery_percent = None
        self.model = None
        self.current_model_name = None

        # Command mapping
        self.commands: dict[str, Callable] = {
            "play": self._media_control,
            "pause": self._media_control,
            "stop": self._media_control,
            "resume": self._media_control,
        }

        # Initialize
        self._update_power_state()
        self._load_model()

        logger.info("Voice listener initialized")
        logger.info(f"Power state: {self.power_state}, Battery: {self.battery_percent}%")
        logger.info(f"Model: {self.current_model_name}")

    def _detect_power_state(self) -> tuple[str, int | None]:
        """
        Detect if running on battery or AC power.

        Returns:
            Tuple of (power_state, battery_percent)
            power_state: "ac" or "battery"
            battery_percent: Battery percentage (0-100) or None
        """
        try:
            result = subprocess.run(
                ["pmset", "-g", "batt"],
                capture_output=True,
                text=True,
                timeout=2,
                check=False
            )

            output = result.stdout

            # Determine power source
            if "AC Power" in output:
                power_state = PowerState.AC
            else:
                power_state = PowerState.BATTERY

            # Extract battery percentage
            battery_percent = None
            import re
            match = re.search(r"(\d+)%", output)
            if match:
                battery_percent = int(match.group(1))

            return power_state, battery_percent

        except Exception as e:
            logger.warning(f"Failed to detect power state: {e}")
            # Default to battery mode (conservative)
            return PowerState.BATTERY, None

    def _update_power_state(self):
        """Update power state and battery level."""
        self.power_state, self.battery_percent = self._detect_power_state()

    def _select_model_name(self) -> str:
        """
        Select appropriate model based on current power state.

        Returns:
            Model name string
        """
        if self.power_state == PowerState.AC:
            return self.ac_model_name
        else:
            # On battery - check battery level
            if self.battery_percent and self.battery_percent < self.low_battery_threshold:
                return self.low_battery_model_name
            else:
                return self.battery_model_name

    def _load_model(self):
        """Load appropriate Whisper model based on power state."""
        model_name = self._select_model_name()

        # Skip reload if already loaded
        if self.model and model_name == self.current_model_name:
            return

        try:
            import mlx_whisper

            logger.info(f"Loading MLX-Whisper model: {model_name}")
            self.model = mlx_whisper.load_model(model_name)
            self.current_model_name = model_name

            logger.info(f"Model loaded successfully: {model_name}")

        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            raise VoiceListenerError(f"Cannot load model: {e}") from e

    def _check_and_reload_model(self):
        """Check if power state changed and reload model if needed."""
        old_state = self.power_state
        old_battery = self.battery_percent

        self._update_power_state()

        # Check if model should change
        new_model_name = self._select_model_name()

        if new_model_name != self.current_model_name:
            logger.info(
                f"Power state changed: {old_state} ({old_battery}%) → "
                f"{self.power_state} ({self.battery_percent}%)"
            )
            logger.info(f"Switching model: {self.current_model_name} → {new_model_name}")

            self._load_model()

    def _media_control(self):
        """Execute MediaPlayPause shortcut."""
        try:
            result = subprocess.run(
                ["shortcuts", "run", self.media_shortcut],
                capture_output=True,
                timeout=2,
                check=False
            )

            if result.returncode == 0:
                logger.info("Media control executed")
                return True
            else:
                logger.warning(f"Media control failed: {result.stderr.decode()}")
                return False

        except Exception as e:
            logger.error(f"Failed to execute media control: {e}")
            return False

    @contextmanager
    def _audio_stream(self):
        """Context manager for audio stream."""
        audio = pyaudio.PyAudio()

        try:
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )

            yield stream

        finally:
            if "stream" in locals():
                stream.stop_stream()
                stream.close()
            audio.terminate()

    def capture_audio(self) -> np.ndarray:
        """
        Capture audio chunk for transcription.

        Returns:
            Numpy array of audio samples (int16)
        """
        with self._audio_stream() as stream:
            frames = []
            num_chunks = int(self.sample_rate / self.chunk_size * self.listen_duration)

            for _ in range(num_chunks):
                data = stream.read(self.chunk_size, exception_on_overflow=False)
                frames.append(data)

            # Convert to numpy array
            audio_data = np.frombuffer(b"".join(frames), dtype=np.int16)

            # Convert to float32 and normalize to [-1, 1] for Whisper
            audio_float = audio_data.astype(np.float32) / 32768.0

            return audio_float

    def transcribe(self, audio: np.ndarray) -> str:
        """
        Transcribe audio using current model.

        Args:
            audio: Audio data as numpy array (float32, normalized)

        Returns:
            Transcribed text (lowercase)
        """
        try:
            import mlx_whisper

            # Transcribe using MLX-Whisper
            result = mlx_whisper.transcribe(
                audio,
                path_or_hf_repo=self.current_model_name,
                fp16=False  # Use float32 for better accuracy
            )

            text = result.get("text", "").strip().lower()

            if text:
                logger.debug(f"Transcribed: {text}")

            return text

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return ""

    def parse_commands(self, text: str) -> bool:
        """
        Parse transcribed text for commands.

        Args:
            text: Transcribed text (lowercase)

        Returns:
            True if command was found and executed
        """
        if not text:
            return False

        # Check for known commands
        for command, action in self.commands.items():
            if command in text:
                logger.info(f"Command detected: {command}")
                action()
                return True

        return False

    def listen_once(self) -> bool:
        """
        Listen for one audio chunk and process commands.

        Returns:
            True if command was executed
        """
        # Check power state periodically
        self._check_and_reload_model()

        # Capture audio
        logger.debug("Listening...")
        audio = self.capture_audio()

        # Transcribe
        text = self.transcribe(audio)

        # Parse commands
        if text:
            return self.parse_commands(text)

        return False

    def listen_continuous(self):
        """
        Continuous listening loop.

        Listens for voice commands in a loop until stopped.
        Press Ctrl+C to stop.
        """
        self.running = True

        logger.info("Starting continuous listening...")
        logger.info("Say 'play', 'pause', 'stop', or 'resume' to control media")
        logger.info("Press Ctrl+C to stop")

        try:
            while self.running:
                self.listen_once()

        except KeyboardInterrupt:
            logger.info("Stopping listener...")
            self.running = False

        except Exception as e:
            logger.error(f"Listener error: {e}")
            self.running = False
            raise


def main():
    """CLI entry point for voice listener."""
    import argparse

    parser = argparse.ArgumentParser(description="Voice command listener")
    parser.add_argument("--test", action="store_true", help="Test mode (single listen)")
    parser.add_argument("--duration", type=int, default=3, help="Listen duration in seconds")
    args = parser.parse_args()

    try:
        listener = VoiceListener(listen_duration=args.duration)

        if args.test:
            # Test mode - single listen
            logger.info("Test mode: listening once...")
            listener.listen_once()
            logger.info("Test complete")
        else:
            # Continuous mode
            listener.listen_continuous()

    except KeyboardInterrupt:
        logger.info("Stopped by user")
    except Exception as e:
        logger.error(f"Failed to start listener: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
