# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Fifth Symphony is an AI-powered distributed automation conductor that orchestrates Python, Bash, and AppleScript scripts across networks with voice synthesis and modular integration. It provides both CLI and GUI interfaces for script management with ADHD-friendly features.

## Architecture

### Core Components
- **`main.py`** - Core orchestrator and CLI interface with Rich terminal output
- **`gui.py`** - PySide6 GUI with dark theme and visual script cards
- **`gui_orchestrator.py`** - GUI-specific orchestration logic
- **`modules/`** - Core functionality modules:
  - `onepassword_manager.py` - 1Password CLI integration for secure credentials
  - `voice_handler.py` - ElevenLabs voice synthesis with priority queue
  - `script_runner.py` - Async script execution and monitoring
  - `output_translator.py` - Technical-to-conversational translation
  - `reminder_system.py` - ADHD-friendly attention management
  - `symlink_manager.py` - External script integration

### Configuration Structure
- **`config/settings.yaml`** - Main system configuration
- **`config/prompts/`** - Voice message templates (success, error, info, reminder)
- **`config/templates/`** - Output formatting rules
- **`config/onepassword/`** - Credential management settings

## Common Development Commands

```bash
# Setup and run (uses uv package manager)
./run.sh                    # Launch CLI interface
./run_gui.sh               # Launch GUI interface

# Install dependencies
uv sync                    # Install all dependencies from pyproject.toml
uv add [package]          # Add new dependency

# Development without launchers
uv run python main.py      # Run CLI directly
uv run python gui.py       # Run GUI directly

# Script management
# Place scripts in scripts/ directory - they auto-discover on startup
# Create symlinks for external scripts:
ln -s /path/to/external/script.py scripts/

# 1Password setup (for API keys)
op signin                  # Initialize 1Password session
# API keys are retrieved from vault "Development" as "ElevenLabs API Key"
```

## Key Development Patterns

### Async-First Architecture
All script execution and I/O operations use asyncio. When modifying script runners or handlers:
- Use `async def` for I/O-bound operations
- Implement proper exception handling with try/except blocks
- Use `asyncio.create_subprocess_exec()` for subprocess management
- Handle script input detection with configurable timeouts

### Module Communication
Modules communicate through dependency injection pattern:
```python
# Modules are initialized with configuration
voice_handler = VoiceHandler(config['elevenlabs'])
script_runner = ScriptRunner(voice_handler=voice_handler)
```

### 1Password Integration
Never hardcode API keys or secrets. All credentials flow through 1Password:
```python
# Credentials are retrieved via onepassword_manager module
api_key = await onepassword_manager.get_api_key("ElevenLabs API Key", "Development")
```

### Voice Synthesis Flow
1. Scripts trigger voice events through `voice_handler.py`
2. Messages are queued with priority levels (0-2)
3. ElevenLabs API synthesizes with configured voice settings
4. Audio plays asynchronously without blocking execution

## Testing Approach

```bash
# Run example scripts for testing
uv run python scripts/quick_test.py    # Fast completion demo
uv run python scripts/error_demo.py     # Error handling test

# Manual testing
./run.sh --list                         # List available scripts
./run.sh --run quick_test               # Run specific script
```

## GUI Development

The GUI uses PySide6 with qasync for asyncio integration:
- Visual updates must use Qt's signal/slot mechanism
- Long-running operations should emit progress signals
- Terminal output is captured and displayed in embedded widget
- Dark theme is applied via qdarktheme package

## Script Integration Requirements

Scripts discovered in `scripts/` directory must:
- Have a `.py` extension
- Include a docstring for description extraction
- Handle their own argument parsing if needed
- Return appropriate exit codes (0 for success)
- Output to stdout/stderr for capture

## Configuration Customization

### Voice Settings (config/settings.yaml)
- `voice_id`: ElevenLabs voice identifier
- `stability`: Voice consistency (0.0-1.0)
- `similarity_boost`: Voice matching (0.0-1.0)
- `style`: Speaking style intensity (0.0-1.0)

### Reminder System
- `intervals`: Time between reminder escalations
- `max_reminders`: Total reminders before giving up
- `messages`: Customizable reminder text by urgency level

## Security Considerations

- All API keys via 1Password CLI with biometric unlock
- Session tokens expire and auto-renew
- No credentials in environment variables or config files
- Vault categorization for different credential types

## Platform-Specific Features

### macOS
- Touch ID for 1Password unlock
- AppleScript support for system automation
- System notifications via osascript

### Linux
- Desktop notifications via notify-send
- Terminal-based 1Password authentication

### Windows
- Basic support with limited features
- No system tray integration