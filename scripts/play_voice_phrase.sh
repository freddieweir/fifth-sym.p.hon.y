#!/bin/bash
#
# Play pre-generated voice phrase for instant audio feedback
#
# Usage:
#   play_voice_phrase.sh git_pull              # Play git_pull phrase
#   play_voice_phrase.sh gh_pr_create          # Play GitHub PR create phrase
#   play_voice_phrase.sh security_yubikey_bypass  # Play security alert
#
# Integration example (in git wrapper):
#   play_voice_phrase.sh "git_${1}"  # Where $1 is git command (pull, push, etc.)

set -euo pipefail

PHRASE_LIBRARY="${HOME}/.claude/voice-phrases"
PHRASE_ID="${1:-}"

# Show usage if no argument
if [ -z "$PHRASE_ID" ]; then
    echo "Usage: $0 <phrase_id>"
    echo ""
    echo "Available phrases:"
    ls "$PHRASE_LIBRARY"/*.mp3 2>/dev/null | xargs -n 1 basename | sed 's/.mp3$//' | sort
    exit 1
fi

PHRASE_FILE="$PHRASE_LIBRARY/${PHRASE_ID}.mp3"

# Check if phrase exists
if [ ! -f "$PHRASE_FILE" ]; then
    echo "Error: Phrase not found: $PHRASE_ID" >&2
    echo "Available phrases:" >&2
    ls "$PHRASE_LIBRARY"/*.mp3 2>/dev/null | xargs -n 1 basename | sed 's/.mp3$//' | sort >&2
    exit 1
fi

# Play phrase (macOS with afplay, Linux would use paplay/aplay)
if command -v afplay &> /dev/null; then
    afplay "$PHRASE_FILE" &
elif command -v paplay &> /dev/null; then
    paplay "$PHRASE_FILE" &
elif command -v aplay &> /dev/null; then
    aplay "$PHRASE_FILE" &
else
    echo "Error: No audio player found (afplay, paplay, or aplay)" >&2
    exit 1
fi
