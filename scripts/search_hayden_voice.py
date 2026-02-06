#!/usr/bin/env python3
"""Search for Hayden voice ID in ElevenLabs account."""

import sys
from pathlib import Path

# Add fifth-symphony to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.audio_tts import AudioTTS


def main():
    """Search for Hayden voices."""
    print("Searching for Hayden voices in ElevenLabs account...")
    print("-" * 60)

    # Initialize AudioTTS to verify credentials work
    AudioTTS()

    # Get all voices
    from elevenlabs.client import ElevenLabs

    from modules.onepassword_manager import OnePasswordManager

    # Get API key from 1Password
    op_config = {"vault": "API"}
    op = OnePasswordManager(op_config)
    api_key = op.get_api_key("Eleven Labs -")  # get_api_key appends " API"

    # Initialize client
    client = ElevenLabs(api_key=api_key)
    voices = client.voices.get_all()

    # Search for Hayden
    hayden_voices = [v for v in voices.voices if "hayden" in v.name.lower()]

    if not hayden_voices:
        print("❌ No Hayden voices found")
        print("\nSearching for 'v2' voices instead:")
        v2_voices = [v for v in voices.voices if "v2" in v.name.lower()]
        for voice in v2_voices[:10]:  # Show first 10
            print(f"  - {voice.name}: {voice.voice_id}")
    else:
        print(f"✅ Found {len(hayden_voices)} Hayden voice(s):")
        for voice in hayden_voices:
            print(f"\nName: {voice.name}")
            print(f"Voice ID: {voice.voice_id}")
            print(f"Labels: {voice.labels if hasattr(voice, 'labels') else 'N/A'}")
            print("-" * 60)


if __name__ == "__main__":
    main()
