#!/usr/bin/env python3
"""
Overseerr Webhook Listener

Receives webhook events from Overseerr and generates audio notifications.
Integrates with existing AudioTTS module and audio monitor service.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Configuration
AUDIO_OUTPUT_DIR = Path("/Users/fweir/git/ai-bedo/communications/audio")

# Notification templates for different event types
NOTIFICATION_TEMPLATES = {
    "MEDIA_PENDING": "{user} requested {media_title}",
    "MEDIA_APPROVED": "{media_title} approved for download",
    "MEDIA_AVAILABLE": "{media_title} is now available in Plex",
    "MEDIA_AUTO_APPROVED": "{media_title} automatically approved for download",
    "MEDIA_DECLINED": "{media_title} request declined",
    "MEDIA_FAILED": "Download failed for {media_title}",
    "TEST_NOTIFICATION": "Overseerr webhook test received successfully",
}

# Event type mapping (Overseerr may use different naming conventions)
EVENT_TYPE_ALIASES = {
    "media.requested": "MEDIA_PENDING",
    "media.pending": "MEDIA_PENDING",
    "media.approved": "MEDIA_APPROVED",
    "media.autoapproved": "MEDIA_AUTO_APPROVED",
    "media.available": "MEDIA_AVAILABLE",
    "media.declined": "MEDIA_DECLINED",
    "media.failed": "MEDIA_FAILED",
    "test": "TEST_NOTIFICATION",
}


app = FastAPI(title="Overseerr Audio Notifier", version="1.0.0")


def format_notification(
    event_type: str, subject: str, message: str, payload: Dict[str, Any]
) -> str:
    """
    Format notification text based on event type and payload.

    Args:
        event_type: The notification type from Overseerr
        subject: The subject line from webhook payload
        message: The message body from webhook payload
        payload: Full webhook payload for extracting additional details

    Returns:
        Formatted notification text for TTS
    """
    # Normalize event type
    normalized_event = EVENT_TYPE_ALIASES.get(event_type.lower(), event_type)

    # Get template or use generic format
    template = NOTIFICATION_TEMPLATES.get(
        normalized_event, "{subject}: {message}"
    )

    # Extract media title (prefer subject, fallback to message parsing)
    media_title = subject or "Unknown Title"

    # Extract user if available (from {{requestedBy_username}} or similar)
    user = "User"

    # Check for requestedBy fields in payload
    if "requestedBy_username" in payload:
        user = payload["requestedBy_username"]
    elif "request" in payload and isinstance(payload["request"], dict):
        request_data = payload["request"]
        if "requestedBy_username" in request_data:
            user = request_data["requestedBy_username"]

    # Format using template
    try:
        notification = template.format(
            user=user,
            media_title=media_title,
            subject=subject,
            message=message,
        )
    except KeyError:
        # Fallback to simple format if template variables don't match
        notification = f"{subject}: {message}"

    return notification


def write_audio_file(text: str, event_type: str, source: str = "main") -> Path:
    """
    Write audio notification text file for audio monitor to pick up.

    Args:
        text: Notification text for TTS
        event_type: Event type for filename
        source: "main" or "vm" for voice selection (default: main)

    Returns:
        Path to written audio file
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    # Sanitize event type for filename
    safe_event = event_type.replace(".", "-").replace("_", "-").lower()

    # Add source suffix for voice selection
    suffix = f"-{source}" if source else ""

    filename = f"{timestamp}-overseerr-{safe_event}{suffix}.txt"
    audio_file = AUDIO_OUTPUT_DIR / filename

    # Ensure directory exists
    audio_file.parent.mkdir(parents=True, exist_ok=True)

    # Write notification text
    audio_file.write_text(text, encoding="utf-8")

    logger.info(f"Audio notification written: {audio_file}")

    return audio_file


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "Overseerr Audio Notifier",
        "status": "operational",
        "webhook_endpoint": "/webhook/overseerr",
    }


@app.get("/health")
async def health_check():
    """Detailed health check."""
    audio_dir_exists = AUDIO_OUTPUT_DIR.exists()
    audio_dir_writable = False

    if audio_dir_exists:
        try:
            # Test write permissions
            test_file = AUDIO_OUTPUT_DIR / ".health_check"
            test_file.write_text("test")
            test_file.unlink()
            audio_dir_writable = True
        except Exception as e:
            logger.warning(f"Audio directory not writable: {e}")

    return {
        "status": "healthy" if (audio_dir_exists and audio_dir_writable) else "degraded",
        "audio_output_dir": str(AUDIO_OUTPUT_DIR),
        "audio_dir_exists": audio_dir_exists,
        "audio_dir_writable": audio_dir_writable,
    }


@app.post("/webhook/overseerr")
async def handle_overseerr_webhook(request: Request):
    """
    Handle incoming Overseerr webhook events.

    Expected payload structure (based on Overseerr template variables):
    {
      "notification_type": "MEDIA_PENDING",
      "event": "New Request",
      "subject": "Movie Title (2024)",
      "message": "Overview/synopsis of the media",
      "image": "https://image.tmdb.org/...",
      "requestedBy_username": "user123",
      "requestedBy_email": "user@example.com",
      "requestedBy_avatar": "https://...",
      "media": {...},
      "request": {...},
      "extra": [...]
    }
    """
    try:
        # Parse JSON payload
        payload = await request.json()

        # Log received webhook (censor sensitive data)
        logger.info(f"Received webhook: {payload.get('notification_type', 'UNKNOWN')}")

        # Extract key fields
        notification_type = payload.get("notification_type", "UNKNOWN")
        event = payload.get("event", "")
        subject = payload.get("subject", "")
        message = payload.get("message", "")

        # Format notification text
        notification_text = format_notification(
            event_type=notification_type,
            subject=subject,
            message=message,
            payload=payload,
        )

        # Determine source (main machine vs VM)
        # Default to "main" since Overseerr runs on main machine
        source = "main"

        # Write audio file for monitoring service
        audio_file = write_audio_file(
            text=notification_text,
            event_type=notification_type,
            source=source,
        )

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Audio notification generated",
                "audio_file": str(audio_file.name),
                "notification_text": notification_text,
            },
        )

    except Exception as e:
        logger.error(f"Webhook processing error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process webhook: {str(e)}",
        )


@app.post("/webhook/test")
async def test_webhook():
    """Test endpoint to verify webhook functionality."""
    try:
        test_notification = "Overseerr webhook test successful"

        audio_file = write_audio_file(
            text=test_notification,
            event_type="TEST_NOTIFICATION",
            source="main",
        )

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Test notification generated",
                "audio_file": str(audio_file.name),
                "notification_text": test_notification,
            },
        )
    except Exception as e:
        logger.error(f"Test webhook error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Test failed: {str(e)}",
        )


def main():
    """Run the webhook listener server."""
    import uvicorn

    # Server configuration
    host = "0.0.0.0"  # Listen on all interfaces
    port = 8765  # Default port for Overseerr webhooks

    logger.info(f"Starting Overseerr Audio Notifier on {host}:{port}")
    logger.info(f"Webhook endpoint: http://{host}:{port}/webhook/overseerr")
    logger.info(f"Audio output directory: {AUDIO_OUTPUT_DIR}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    main()
