#!/usr/bin/env python3
"""
Standalone test for overseerr_webhook module.
Tests without importing the full modules package.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Dynamic path resolution for ai-bedo repository
ALBEDO_ROOT = Path(os.getenv("ALBEDO_ROOT", Path.home() / "git" / "internal" / "repos" / "ai-bedo"))

# Test notification formatting logic
NOTIFICATION_TEMPLATES = {
    "MEDIA_PENDING": "{user} requested {media_title}",
    "MEDIA_APPROVED": "{media_title} approved for download",
    "MEDIA_AVAILABLE": "{media_title} is now available in Plex",
}

EVENT_TYPE_ALIASES = {
    "media.pending": "MEDIA_PENDING",
    "media.approved": "MEDIA_APPROVED",
    "media.available": "MEDIA_AVAILABLE",
}


def format_notification(event_type, subject, message, payload):
    """Test notification formatting."""
    normalized_event = EVENT_TYPE_ALIASES.get(event_type.lower(), event_type)
    template = NOTIFICATION_TEMPLATES.get(normalized_event, "{subject}: {message}")

    media_title = subject or "Unknown Title"
    user = "User"

    if "requestedBy_username" in payload:
        user = payload["requestedBy_username"]

    try:
        notification = template.format(
            user=user,
            media_title=media_title,
            subject=subject,
            message=message,
        )
    except KeyError:
        notification = f"{subject}: {message}"

    return notification


def test_formatting():
    """Test notification formatting."""
    print("Testing notification formatting...")

    tests = [
        {
            "event": "MEDIA_PENDING",
            "subject": "The Matrix (1999)",
            "payload": {"requestedBy_username": "testuser"},
            "expected": "testuser requested The Matrix (1999)",
        },
        {
            "event": "MEDIA_APPROVED",
            "subject": "Inception (2010)",
            "payload": {},
            "expected": "Inception (2010) approved for download",
        },
    ]

    for test in tests:
        result = format_notification(
            test["event"],
            test["subject"],
            "Test message",
            test["payload"],
        )

        status = "✅" if result == test["expected"] else "❌"
        print(f"{status} {test['event']}: {result}")
        if result != test["expected"]:
            print(f"   Expected: {test['expected']}")

    print()


def test_audio_file_write():
    """Test audio file writing."""
    print("Testing audio file writing...")

    audio_dir = ALBEDO_ROOT / "communications" / "audio"

    # Check if directory exists
    if not audio_dir.exists():
        print(f"⚠️  Audio directory doesn't exist: {audio_dir}")
        print("   This is expected on VM without syncthing")
        return

    # Create test file
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    test_file = audio_dir / f"{timestamp}-test-webhook-main.txt"

    try:
        test_file.write_text("Test notification from overseerr webhook")
        print(f"✅ Test file created: {test_file.name}")

        # Clean up
        test_file.unlink()
        print("✅ Test file cleaned up")

    except Exception as e:
        print(f"❌ Error: {e}")

    print()


def main():
    """Run tests."""
    print("=" * 60)
    print("Overseerr Webhook Standalone Tests")
    print("=" * 60)
    print()

    test_formatting()
    test_audio_file_write()

    print("=" * 60)
    print("Tests complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
