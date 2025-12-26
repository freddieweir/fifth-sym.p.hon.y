# Fifth-Symphony Script Aliases

Quick access to Python scripts via convenient shell aliases.

## Installation

```bash
cd /Users/fweir/git/internal/repos/fifth-symphony/scripts
./install-aliases.sh
source ~/.zshrc
```

Or manually add to `~/.zshrc`:
```bash
source ~/git/internal/repos/fifth-symphony/scripts/symphony-aliases.zsh
```

## Usage

### `sasuga` - Favorite Scripts

Run curated scripts from `scripts/favorites/`:

```bash
# Launch agent monitor
sasuga launch_agent_monitor.py

# List available favorites
sasuga

# List with descriptions
sasuga-list
```

**Why "sasuga"?** - Japanese phrase meaning "as expected" or "well done" - perfect for your favorite, well-tested scripts!

### `pyscript` - Any Script

Run any script from `scripts/` directory, including subdirectories:

```bash
# Top-level script
pyscript launch_agent_monitor.py

# Subdirectory script
pyscript user-scripts/quick_test.py

# Deep nested script
pyscript tools/audio/voice_tester.py

# List all scripts
pyscript

# List with tree view
pyscript-list
```

## Features

### Automatic Environment Detection
- Uses `uv run` when in fifth-symphony directory
- Falls back to system Python elsewhere
- Automatically sets `PYTHONPATH` for module imports

### Tab Completion
Both aliases support tab completion:

```bash
sasuga <TAB>         # Shows favorite scripts
pyscript <TAB>       # Shows all scripts with paths
```

### Error Handling
- Suggests similar scripts if not found
- Shows available options on error
- Validates script exists before running

### Pass Arguments
Both aliases support passing arguments to scripts:

```bash
sasuga launch_agent_monitor.py --debug
pyscript user-scripts/quick_test.py --verbose --config test.yaml
```

## Favorites Directory

Add your most-used scripts to `scripts/favorites/` for quick access with `sasuga`.

**Current favorites**:
- `launch_agent_monitor.py` - Albedo Agent Monitor TUI

**Adding new favorites**:
```bash
# Copy or symlink script to favorites
cp scripts/some_script.py scripts/favorites/
# Or
ln -s ../some_script.py scripts/favorites/some_script.py

# Make executable
chmod +x scripts/favorites/some_script.py

# Now accessible via sasuga
sasuga some_script.py
```

## Directory Structure

```
scripts/
├── favorites/                    # Curated favorite scripts (sasuga)
│   └── launch_agent_monitor.py
├── user-scripts/                 # User-specific scripts
│   └── quick_test.py
├── tools/                        # Utility scripts
├── symphony-aliases.zsh          # Alias definitions
├── install-aliases.sh            # Installation script
└── README-ALIASES.md             # This file
```

## Examples

### Launch Agent Monitor (Quick)
```bash
sasuga launch_agent_monitor.py
```

### Run User Script with Arguments
```bash
pyscript user-scripts/test_voice.py --voice "Albedo v2" --text "Hello world"
```

### List All Scripts by Category
```bash
pyscript-list
```

Output:
```
📚 All Scripts (use 'pyscript <path>'):

scripts/
├── favorites/
│   └── launch_agent_monitor.py
├── user-scripts/
│   ├── quick_test.py
│   └── voice_tester.py
└── tools/
    └── audio/
        └── media_control.py
```

### Find a Script
```bash
pyscript monitor  # Will suggest scripts matching "monitor"
```

## Advanced Usage

### Environment Variables

The aliases set these environment variables:

- `FIFTH_SYMPHONY_SCRIPTS` - Path to scripts directory
- `FIFTH_SYMPHONY_ROOT` - Path to fifth-symphony root

Use in your scripts:
```python
import os
from pathlib import Path

scripts_dir = Path(os.environ.get('FIFTH_SYMPHONY_SCRIPTS', '~/git/internal/repos/fifth-symphony/scripts'))
root_dir = Path(os.environ.get('FIFTH_SYMPHONY_ROOT', '~/git/internal/repos/fifth-symphony'))
```

### Custom Favorites Location

Override the favorites directory:
```bash
export FIFTH_SYMPHONY_FAVORITES="$HOME/my-custom-favorites"
sasuga my_script.py
```

### Dry Run Mode

Add to `symphony-aliases.zsh` for dry run:
```bash
sasuga --dry launch_agent_monitor.py  # Show command without running
```

## Troubleshooting

### Aliases not found
```bash
# Reload shell configuration
source ~/.zshrc

# Or restart terminal
```

### Script not found
```bash
# List available scripts
sasuga          # For favorites
pyscript        # For all scripts

# Check script path
ls -la ~/git/internal/repos/fifth-symphony/scripts/favorites/
```

### Permission denied
```bash
# Make script executable
chmod +x ~/git/internal/repos/fifth-symphony/scripts/favorites/your_script.py
```

### Import errors
```bash
# Ensure fifth-symphony dependencies are installed
cd ~/git/internal/repos/fifth-symphony
uv sync
```

## Integration with Other Projects

### Albedo
Albedo can use these aliases to launch fifth-symphony modules:

```bash
# From anywhere
sasuga launch_agent_monitor.py
```

### Custom Projects
Add fifth-symphony scripts to your favorites:

```bash
ln -s ~/git/my-project/scripts/my_tool.py ~/git/internal/repos/fifth-symphony/scripts/favorites/
sasuga my_tool.py
```

## Best Practices

1. **Favorites**: Keep favorites small and well-tested
2. **Documentation**: Add docstrings to script headers
3. **Executable**: Always `chmod +x` new scripts
4. **Organization**: Use subdirectories in `scripts/` for categories
5. **Dependencies**: Document required packages in script headers

## Related

- [Fifth-Symphony README](../README.md)
- [Module Documentation](../docs/)
- [Agent Monitor TUI](../modules/agent_monitor/)

---

**Status**: Active
**Shell**: Zsh
**Compatibility**: macOS, Linux
