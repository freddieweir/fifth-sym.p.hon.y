"""
Speech-to-Text voice input module.

Provides keyboard-activated voice input using Whisper.
Attention-friendly with visual feedback and hotkey toggle.
"""

import asyncio
import logging
import tempfile
from collections.abc import Callable
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf
import whisper

logger = logging.getLogger(__name__)


class VoiceInput:
    """
    Speech-to-text voice input with keyboard toggle.

    Features:
    - Hotkey activation (Cmd+Shift+V)
    - Real-time recording indicator
    - Whisper transcription
    - Attention-friendly visual feedback
    """

    def __init__(
        self,
        model_size: str = "base",
        sample_rate: int = 16000,
        callback: Callable[[str], None] | None = None,
    ):
        """
        Initialize voice input.

        Args:
            model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
            sample_rate: Audio sample rate (default: 16000)
            callback: Function to call with transcribed text
        """
        self.model_size = model_size
        self.sample_rate = sample_rate
        self.callback = callback

        # State
        self.is_recording = False
        self.recording_data = []

        # Load Whisper model
        logger.info(f"Loading Whisper model: {model_size}")
        self.model = whisper.load_model(model_size)
        logger.info("Whisper model loaded")

    async def toggle_recording(self):
        """Toggle voice recording on/off."""
        if self.is_recording:
            await self.stop_recording()
        else:
            await self.start_recording()

    async def start_recording(self):
        """Start voice recording."""
        if self.is_recording:
            return

        self.is_recording = True
        self.recording_data = []

        logger.info("🎤 Started voice recording")

        # Start recording in background task
        asyncio.create_task(self._record_audio())

    async def stop_recording(self):
        """Stop recording and transcribe."""
        if not self.is_recording:
            return

        self.is_recording = False

        logger.info("🎤 Stopped voice recording, transcribing...")

        # Transcribe recorded audio
        text = await self._transcribe_audio()

        if text and self.callback:
            self.callback(text)

        return text

    async def _record_audio(self):
        """Record audio in background."""

        def audio_callback(indata, frames, time, status):
            """Callback for audio stream."""
            if status:
                logger.warning(f"Audio stream status: {status}")

            if self.is_recording:
                self.recording_data.append(indata.copy())

        # Start audio stream
        with sd.InputStream(channels=1, samplerate=self.sample_rate, callback=audio_callback):
            # Keep stream open while recording
            while self.is_recording:
                await asyncio.sleep(0.1)

    async def _transcribe_audio(self) -> str | None:
        """
        Transcribe recorded audio with Whisper.

        Returns:
            Transcribed text or None
        """
        if not self.recording_data:
            logger.warning("No audio data to transcribe")
            return None

        try:
            # Combine audio chunks
            audio = np.concatenate(self.recording_data, axis=0).flatten()

            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = f.name
                sf.write(temp_path, audio, self.sample_rate)

            # Transcribe with Whisper
            result = await asyncio.to_thread(self.model.transcribe, temp_path, language="en")

            # Clean up temp file
            Path(temp_path).unlink()

            text = result["text"].strip()
            logger.info(f"🎤 Transcribed: {text}")

            return text

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None


class VoiceInputWidget:
    """
    Voice input widget for Textual dashboard.

    Displays recording status and transcription results.
    """

    def __init__(self, voice_input: VoiceInput):
        """
        Initialize voice input widget.

        Args:
            voice_input: VoiceInput instance
        """
        self.voice_input = voice_input
        self.status_text = "🎤 Press Cmd+Shift+V to start recording"

    async def on_key(self, event):
        """Handle keyboard events."""
        # Check for Cmd+Shift+V hotkey
        if event.key == "v" and event.ctrl and event.shift:
            await self.voice_input.toggle_recording()

            if self.voice_input.is_recording:
                self.status_text = "🔴 Recording... (Press Cmd+Shift+V to stop)"
            else:
                self.status_text = "⏳ Transcribing..."

    def render(self):
        """Render voice input status."""
        return self.status_text
