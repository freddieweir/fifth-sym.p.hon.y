#!/usr/bin/env python3
"""
Generate pre-recorded voice phrases using ElevenLabs for instant playback.

This script generates a library of commonly-used voice phrases that can be
played instantly without API latency. Perfect for git/gh operation confirmations.

Usage:
    python generate_voice_phrases.py                    # Generate all phrases
    python generate_voice_phrases.py --phrase git_pull  # Generate specific phrase
    python generate_voice_phrases.py --test             # Test with sample phrase
"""

import argparse
import sys
from pathlib import Path

# Add fifth-symphony to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.audio_tts import AudioTTS, AudioTTSError

# Voice phrase library for git/gh operations
VOICE_PHRASES: dict[str, str] = {
    # Git Operations (Primary)
    "git_pull": "git pull requested",
    "git_push": "git push requested",
    "git_fetch": "git fetch requested",
    "git_clone": "git clone requested",

    # Git Remote Operations
    "git_remote_add": "git remote add requested",
    "git_remote_update": "git remote update requested",
    "git_submodule_update": "git submodule update requested",

    # GitHub CLI - Pull Request Operations
    "gh_pr_create": "GitHub pull request creation requested",
    "gh_pr_merge": "GitHub pull request merge requested",
    "gh_pr_close": "GitHub pull request close requested",
    "gh_pr_reopen": "GitHub pull request reopen requested",
    "gh_pr_edit": "GitHub pull request edit requested",
    "gh_pr_ready": "GitHub pull request ready requested",
    "gh_pr_review": "GitHub pull request review requested",

    # GitHub CLI - Issue Operations
    "gh_issue_create": "GitHub issue creation requested",
    "gh_issue_close": "GitHub issue close requested",
    "gh_issue_reopen": "GitHub issue reopen requested",
    "gh_issue_edit": "GitHub issue edit requested",
    "gh_issue_delete": "GitHub issue delete requested",
    "gh_issue_transfer": "GitHub issue transfer requested",

    # GitHub CLI - Release Operations
    "gh_release_create": "GitHub release creation requested",
    "gh_release_delete": "GitHub release delete requested",
    "gh_release_edit": "GitHub release edit requested",
    "gh_release_upload": "GitHub release upload requested",

    # GitHub CLI - Repository Operations
    "gh_repo_create": "GitHub repository creation requested",
    "gh_repo_delete": "GitHub repository delete requested",
    "gh_repo_clone": "GitHub repository clone requested",
    "gh_repo_fork": "GitHub repository fork requested",
    "gh_repo_archive": "GitHub repository archive requested",
    "gh_repo_rename": "GitHub repository rename requested",

    # GitHub CLI - Workflow Operations
    "gh_workflow_run": "GitHub workflow run requested",
    "gh_workflow_enable": "GitHub workflow enable requested",
    "gh_workflow_disable": "GitHub workflow disable requested",

    # GitHub CLI - Secret Operations
    "gh_secret_set": "GitHub secret set requested",
    "gh_secret_delete": "GitHub secret delete requested",
    "gh_secret_removal": "GitHub secret removal requested",

    # GitHub CLI - Authentication Operations
    "gh_auth_login": "GitHub authentication login requested",
    "gh_auth_logout": "GitHub authentication logout requested",
    "gh_auth_refresh": "GitHub authentication refresh requested",
    "gh_auth_setup": "GitHub authentication setup requested",

    # Security Alerts
    "security_yubikey_bypass": "Warning: YubiKey enforcement bypassed",
    "security_enforcement_disabled": "Security alert: enforcement disabled",
}


class VoicePhraseGenerator:
    """Generate and manage pre-recorded voice phrases."""

    def __init__(self, voice_id: str | None = None, output_dir: Path | None = None):
        """
        Initialize voice phrase generator.

        Args:
            voice_id: ElevenLabs voice ID (default: environment-based)
            output_dir: Output directory for phrases (default: ~/.claude/voice-phrases)
        """
        self.output_dir = output_dir or Path.home() / ".claude" / "voice-phrases"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize AudioTTS with no auto-play (we're just generating files)
        self.tts = AudioTTS(
            output_dir=self.output_dir,
            voice_id=voice_id,
            auto_play=False,
            speed=1.0,  # Normal speed for confirmations
            stability=0.5,
            similarity_boost=0.75,
        )

        print(f"📁 Output directory: {self.output_dir}")
        print(f"🎤 Voice ID: {self.tts.voice_id}")

    def generate_phrase(self, phrase_id: str, text: str) -> Path:
        """
        Generate a single voice phrase.

        Args:
            phrase_id: Unique identifier for the phrase
            text: Text to synthesize

        Returns:
            Path to generated audio file
        """
        output_file = self.output_dir / f"{phrase_id}.mp3"

        try:
            print(f"🎙️  Generating: {phrase_id}")
            print(f'   Text: "{text}"')

            audio_file = self.tts.generate_speech(text, output_file=output_file)

            print(f"   ✅ Saved: {audio_file.name}")
            return audio_file

        except AudioTTSError as e:
            print(f"   ❌ Failed: {e}")
            raise

    def generate_all(self, phrases: dict[str, str] | None = None) -> int:
        """
        Generate all phrases in the library.

        Args:
            phrases: Dictionary of phrase_id -> text (default: VOICE_PHRASES)

        Returns:
            Number of phrases successfully generated
        """
        phrases = phrases or VOICE_PHRASES

        print(f"\n🎵 Generating {len(phrases)} voice phrases...\n")

        success_count = 0
        failed = []

        for phrase_id, text in phrases.items():
            try:
                self.generate_phrase(phrase_id, text)
                success_count += 1
            except AudioTTSError as e:
                failed.append((phrase_id, str(e)))
                continue

        # Summary
        print(f"\n✅ Generated {success_count}/{len(phrases)} phrases")

        if failed:
            print(f"\n❌ Failed to generate {len(failed)} phrases:")
            for phrase_id, error in failed:
                print(f"   - {phrase_id}: {error}")

        return success_count

    def list_generated(self) -> list[Path]:
        """List all generated phrase files."""
        return sorted(self.output_dir.glob("*.mp3"))


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate pre-recorded voice phrases for instant playback"
    )
    parser.add_argument(
        "--phrase",
        help="Generate specific phrase by ID (e.g., git_pull)",
    )
    parser.add_argument(
        "--voice-id",
        help="ElevenLabs voice ID to use (default: environment-based)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory (default: ~/.claude/voice-phrases)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available phrase IDs",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Generate a test phrase",
    )

    args = parser.parse_args()

    # List available phrases
    if args.list:
        print("📝 Available phrase IDs:\n")
        for i, phrase_id in enumerate(VOICE_PHRASES.keys(), 1):
            print(f'{i:2}. {phrase_id:<30} → "{VOICE_PHRASES[phrase_id]}"')
        return 0

    # Initialize generator
    generator = VoicePhraseGenerator(
        voice_id=args.voice_id,
        output_dir=args.output_dir,
    )

    # Test mode
    if args.test:
        print("\n🧪 Test Mode: Generating sample phrase\n")
        test_phrase = "git_pull"
        generator.generate_phrase(test_phrase, VOICE_PHRASES[test_phrase])
        print(f"\n✅ Test complete! Generated phrase: {test_phrase}")
        return 0

    # Generate specific phrase
    if args.phrase:
        if args.phrase not in VOICE_PHRASES:
            print(f"❌ Unknown phrase ID: {args.phrase}")
            print("\nUse --list to see available phrases")
            return 1

        generator.generate_phrase(args.phrase, VOICE_PHRASES[args.phrase])
        return 0

    # Generate all phrases
    success_count = generator.generate_all()
    return 0 if success_count == len(VOICE_PHRASES) else 1


if __name__ == "__main__":
    sys.exit(main())
