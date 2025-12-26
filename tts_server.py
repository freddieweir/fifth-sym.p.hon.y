#!/usr/bin/env python3
"""
Fifth Symphony TTS Server
OpenAI-compatible TTS API server using fifth-symphony AudioTTS modules

Usage:
    uv run python tts_server.py

Configure in Open-WebUI:
    Settings > Audio > Text-to-Speech API URL: http://host.docker.internal:5050/v1/audio/speech
"""

import logging
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Import fifth-symphony AudioTTS
from modules.audio_tts import AudioTTS, AudioTTSError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Fifth Symphony TTS API",
    description="OpenAI-compatible TTS API using fifth-symphony AudioTTS",
    version="1.0.0"
)

# Initialize AudioTTS (environment-aware voice selection)
try:
    tts = AudioTTS()
    logger.info(f"✓ AudioTTS initialized with voice: {tts.voice_id}")
except Exception as e:
    logger.error(f"✗ AudioTTS initialization failed: {e}")
    tts = None


class TTSRequest(BaseModel):
    """OpenAI-compatible TTS request schema"""
    model: str = "tts-1"  # Ignored - we use fifth-symphony
    input: str
    voice: str = "albedo"  # Ignored - auto-selected based on environment
    response_format: str = "mp3"  # Only mp3 supported currently
    speed: float = 0.85  # Speech speed (0.25 to 4.0)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "tts_available": tts is not None,
        "voice_id": tts.voice_id if tts else None
    }


@app.post("/v1/audio/speech")
async def generate_speech(request: TTSRequest):
    """
    OpenAI-compatible text-to-speech endpoint

    Args:
        request: TTSRequest with text input

    Returns:
        Audio file (MP3)
    """
    if not tts:
        raise HTTPException(
            status_code=503,
            detail="TTS service unavailable - AudioTTS not initialized"
        )

    try:
        logger.info(f"🎵 Generating speech for: {request.input[:50]}...")

        # Generate audio using fifth-symphony
        audio_file = tts.generate_speech(
            request.input,
            # speed parameter could be added to AudioTTS if needed
        )

        if not audio_file or not Path(audio_file).exists():
            raise HTTPException(
                status_code=500,
                detail="Audio generation failed - file not created"
            )

        logger.info(f"✓ Audio generated: {audio_file}")

        # Return audio file
        return FileResponse(
            audio_file,
            media_type="audio/mpeg",
            filename=f"speech_{Path(audio_file).name}"
        )

    except AudioTTSError as e:
        logger.error(f"✗ AudioTTS error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        logger.error(f"✗ Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.get("/")
async def root():
    """API information"""
    return {
        "name": "Fifth Symphony TTS API",
        "version": "1.0.0",
        "description": "OpenAI-compatible TTS using fifth-symphony AudioTTS",
        "endpoints": {
            "health": "/health",
            "tts": "/v1/audio/speech (POST)"
        },
        "voice": {
            "id": tts.voice_id if tts else None,
            "name": "Albedo (auto-selected based on environment)"
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",  # Bind to all interfaces (accessible from Docker)
        port=5050,
        log_level="info"
    )
