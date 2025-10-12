# Fifth Symphony

An AI-powered distributed automation conductor orchestrating scripts across networks with voice synthesis and modular integration.

## Features

- **Neural orchestration** - AI-assisted coordination of Python, Bash, AppleScript and more
- **Voice feedback** - Real-time voice narration via Eleven Labs API
- **Proactive reminders** - Attention-grabbing alerts for long-running scripts
- **1Password integration** - Secure credential management via CLI
- **Output translation** - Convert technical output to conversational speech
- **Script monitoring** - Detect when scripts need user input
- **uv package management** - Modern Python dependency handling

## Quick Start

1. **Install dependencies with uv:**
   ```bash
   cd /path/to/fifth-symphony
   uv sync
   ```

2. **Set up 1Password CLI** (optional but recommended):
   ```bash
   brew install --cask 1password-cli
   op signin
   ```

3. **Configure Eleven Labs API** (optional for voice features):
   - Add your API key to 1Password as "Eleven Labs API"
   - Or set environment variable: `export ELEVENLABS_API_KEY=your_key_here`

4. **Run Fifth Symphony:**
   
   **GUI Mode (Recommended):**
   ```bash
   ./run_gui.sh
   ```
   
   **CLI Mode:**
   ```bash
   ./run.sh
   ```

## Usage

### GUI Mode (Visual Interface)
```bash
./run_gui.sh
```
Launches the beautiful dark-themed visual interface with:
- **Script Library**: Visual cards showing all your scripts with descriptions
- **Live Terminal**: Real-time output display with syntax highlighting  
- **Control Panel**: Easy start/stop buttons and voice/reminder toggles
- **Status Panel**: System status, active scripts, and performance monitoring
- **System Tray**: Minimize to background and quick access

### CLI Mode (Terminal Interface)
```bash
./run.sh
```
Shows a text menu of available scripts and lets you choose what to run.

### Direct Script Execution
```bash
uv run main.py script_name
uv run main.py example_long_task
```

### Command Line Options
```bash
uv run main.py --help
uv run main.py -q              # Quiet mode (no voice)
uv run main.py --no-reminders  # Disable reminder system
```

## Configuration

The system is configured via YAML files in the `config/` directory:

- `settings.yaml` - Main configuration
- `prompts/` - Voice message templates
- `templates/` - Output formatting rules
- `onepassword/` - Credential management settings

## Adding Your Scripts

1. Place Python scripts in the `scripts/` directory
2. Scripts will be auto-discovered and added to the menu
3. Add docstrings for better descriptions in the interface

Example script structure:
```python
#!/usr/bin/env python3
"""
My Automation Script
Brief description of what this script does
"""

def main():
    # Your script logic here
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

## Voice Features

Fifth Symphony provides conversational voice feedback including:

- Script start/completion announcements
- Error notifications with simplified explanations
- Progress updates for long-running tasks
- Proactive reminders when scripts wait for input
- Escalating alerts for stuck processes

Voice settings can be customized in `config/settings.yaml`.

## 1Password Integration

Store API keys and secrets securely:

- API keys: "Service Name API" (e.g., "Eleven Labs API")
- Certificates: "Certificate Name Certificate"
- Project secrets: "Project Name Secrets"

The system automatically retrieves credentials at runtime without storing them in code.

## Reminder System

Focus-friendly attention management:

- **Gentle reminders** after 2 minutes
- **Moderate alerts** after 5 minutes  
- **Urgent notifications** after 10 minutes
- **Visual alerts** on macOS/Linux for critical reminders
- **Customizable intervals** and escalation levels

## Example Scripts

Fifth Symphony includes example scripts:

- `quick_test.py` - Fast completion demo
- `example_long_task.py` - Long-running task with interactions
- `error_demo.py` - Error handling demonstration

## Architecture

```
fifth-symphony/
├── main.py                 # Fifth Symphony main conductor
├── modules/               # Core functionality modules
│   ├── audio_tts.py      # Text-to-speech with ElevenLabs (NEW!)
│   ├── onepassword_manager.py  # Secure credential management
│   ├── voice_handler.py
│   ├── script_runner.py
│   ├── output_translator.py
│   └── reminder_system.py
├── config/               # Configuration files
│   ├── settings.yaml
│   ├── prompts/         # Voice message templates
│   └── templates/       # Output formatting
├── scripts/             # Your Python scripts go here
└── pyproject.toml       # uv package configuration
```

### Modular Components

The `modules/` directory contains reusable components that can be imported into other projects:

- **audio_tts.py** - High-quality text-to-speech using ElevenLabs SDK
  - Voice differentiation (VM vs Main machine)
  - Automatic media pause/resume
  - 1Password API key integration
  - Simple usage: `AudioTTS(auto_play=True).generate_speech("Hello!")`

- **onepassword_manager.py** - Secure credential retrieval from 1Password CLI
- **voice_handler.py** - Voice synthesis coordination
- **script_runner.py** - Execute and monitor scripts across the network
- **output_translator.py** - Convert technical output to human-friendly speech
- **reminder_system.py** - Proactive attention-grabbing for long-running tasks

## Security

- No secrets stored in code or config files
- 1Password CLI integration for credential management
- Secure session management
- Environment variable fallbacks
- Audit trail via 1Password logs

## Troubleshooting

### Voice Not Working
- Check Eleven Labs API key in 1Password or environment
- Verify `elevenlabs` package installed: `uv add elevenlabs`
- Test with `--quiet` mode to disable voice temporarily

### 1Password Issues  
- Install CLI: `brew install --cask 1password-cli`
- Sign in: `op signin`
- Check item names match configuration

### Script Discovery Issues
- Ensure scripts are in `scripts/` directory
- Check file permissions (executable recommended)
- Verify Python syntax with `python -m py_compile script.py`

## Contributing

Fifth Symphony is designed to be your personal automation command center. Add your own:

- Scripts in the `scripts/` directory
- Voice message templates in `config/prompts/`
- Output formatting rules in `config/templates/`
- Custom reminder messages and escalation levels

The system automatically discovers and integrates new scripts without code changes.