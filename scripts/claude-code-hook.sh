#!/bin/bash
# claude-code-hook.sh - UserPromptSubmit hook for Fifth Symphony integration
#
# This hook notifies Fifth Symphony about Claude Code activity via IPC
# Enables avatar LED indicators and voice feedback for Claude's actions

set -e

# Fifth Symphony notification endpoint (Unix socket or HTTP)
SYMPHONY_SOCKET="/tmp/fifth-symphony.sock"
SYMPHONY_HTTP="http://localhost:9000/claude-event"

# Log file for debugging
LOG_FILE="$HOME/.claude/fifth-symphony-hook.log"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Function to notify Fifth Symphony
notify_symphony() {
    local event_type="$1"
    local summary="$2"
    local session_id="$3"

    # Try Unix socket first (fastest)
    if [ -S "$SYMPHONY_SOCKET" ]; then
        echo "{\"type\":\"$event_type\",\"summary\":\"$summary\",\"session\":\"$session_id\"}" | nc -U "$SYMPHONY_SOCKET" 2>/dev/null && return 0
    fi

    # Fallback to HTTP endpoint
    curl -s -X POST "$SYMPHONY_HTTP" \
        -H "Content-Type: application/json" \
        -d "{\"type\":\"$event_type\",\"summary\":\"$summary\",\"session\":\"$session_id\"}" \
        2>/dev/null && return 0

    # If both fail, log and continue silently
    log_message "Failed to notify Fifth Symphony (service may not be running)"
    return 1
}

# Main hook logic
main() {
    # Read stdin (hook data from Claude Code)
    local hook_data
    hook_data=$(cat)

    # Extract session ID if available
    local session_id
    session_id=$(echo "$hook_data" | jq -r '.session_id // "unknown"' 2>/dev/null || echo "unknown")

    # Extract prompt if available
    local prompt
    prompt=$(echo "$hook_data" | jq -r '.prompt // ""' 2>/dev/null || echo "")

    # Log activity
    log_message "Hook triggered - Session: $session_id"

    # Notify Fifth Symphony
    notify_symphony "user_prompt" "$prompt" "$session_id"

    # Pass through original hook data unchanged
    echo "$hook_data"
}

# Execute main function
main "$@"
