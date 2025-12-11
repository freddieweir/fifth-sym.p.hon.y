# Albedo Agent Monitor - Modular Architecture

Standalone Python modules for monitoring AI agents, infrastructure, content, and system status in separate terminal tabs.

## Overview

The Albedo Agent Monitor is split into 4 independent modules that can run simultaneously in different terminal tabs/windows:

```
┌─────────────────────┬─────────────────────┐
│ 1. Agent Activity   │ 2. Infrastructure   │
│ • Floor Guardians   │ • MCP Servers       │
│ • Pleiades Skills   │ • Observatory       │
└─────────────────────┴─────────────────────┘
┌─────────────────────┬─────────────────────┐
│ 3. Content          │ 4. System Status    │
│ • Audio History     │ • Albedo Status     │
│ • Documentation     │ • Context Files     │
└─────────────────────┴─────────────────────┘
```

## Quick Start

### Launch All Modules

**Option 1: Python Launcher** (Recommended)
```bash
cd /Users/fweir/git/internal/repos/fifth-symphony/modules/agent_monitor
python launch_modules.py
```

This automatically detects your terminal (iTerm2 or Terminal.app) and opens all 4 modules in separate tabs.

### Launch Individual Modules

Run any module standalone:

```bash
cd /Users/fweir/git/internal/repos/fifth-symphony/modules

# Module 1: Agent Activity
uv run python -m agent_monitor.modules.agent_activity

# Module 2: Infrastructure
uv run python -m agent_monitor.modules.infrastructure

# Module 3: Content
uv run python -m agent_monitor.modules.content

# Module 4: System Status
uv run python -m agent_monitor.modules.system_status
```

## Module Details

### 1. Agent Activity Monitor

**Purpose**: Track AI agent and skill usage

**Panels**:
- **Floor Guardians** (21 agents): incident-commander, security-auditor, code-reviewer, etc.
- **Pleiades Skills** (20 skills): api-documenter, commit-writer, test-generator, etc.

**Features**:
- Live activation tracking (shows agents/skills currently in use)
- Last-used timestamps with relative time display
- Visual status indicators: ● Active / ○ Idle / Never

**Keyboard Shortcuts**:
- `Q` - Quit
- `R` - Refresh data
- `S` - Take screenshot

**Display**: ~40 rows (21 guardians + 20 skills)

---

### 2. Infrastructure Monitor

**Purpose**: Monitor backend systems and observability

**Panels**:
- **MCP Servers**: ElevenLabs, Floor Guardians, etc.
- **Observatory Services**: Grafana, Prometheus, Loki, Tempo, Mimir, Alertmanager, Node Exporter

**Features**:
- MCP server connection status
- Service availability checking (port scanning)
- Dashboard URL launching (press Enter on selected service)
- Interactive navigation

**Keyboard Shortcuts**:
- `Q` - Quit
- `R` - Refresh data
- `M` - Focus MCP servers panel
- `O` - Focus Observatory panel
- `↑/↓` or `J/K` - Navigate (when focused)
- `Enter` - Open dashboard URL in browser
- `Esc` - Unfocus panel
- `S` - Take screenshot

**Display**: ~15 rows (dynamic based on services)

---

### 3. Content Monitor

**Purpose**: Access audio summaries and documentation

**Panels**:
- **Audio History** (10 most recent): Audio summaries from Claude Code sessions
- **Documentation** (15 most recent): CLAUDE.md, README.md files from git repos

**Features**:
- Audio file browsing with timestamps
- Documentation file browser with modification times
- File opening (press Enter to open in default app)
- Project name extraction from audio filenames

**Keyboard Shortcuts**:
- `Q` - Quit
- `R` - Refresh data
- `A` - Focus Audio panel
- `D` - Focus Docs panel
- `↑/↓` or `J/K` - Navigate (when focused)
- `Enter` - Open selected file
- `Esc` - Unfocus panel
- `S` - Take screenshot

**Display**: ~25 rows (10 audio + 15 docs)

---

### 4. System Status Monitor

**Purpose**: System overview and working context

**Panels**:
- **Albedo Status**: LED indicator showing Claude is active
- **Context Files** (15 most recent): Files from Claude Code file-history
- **VM Subagents**: VM task status (placeholder for future expansion)

**Features**:
- Claude Code context visualization (file hashes, access times, edit counts)
- File version tracking (shows how many times each file was edited)
- Live Albedo status indicator

**Keyboard Shortcuts**:
- `Q` - Quit
- `R` - Refresh data
- `C` - Focus Context panel
- `↑/↓` or `J/K` - Navigate (when focused)
- `Esc` - Unfocus panel
- `S` - Take screenshot

**Display**: ~20 rows (1 status + 15 context + VM)

## Architecture

### Directory Structure

```
agent_monitor/
├── shared/                    # Shared utilities
│   ├── config.py             # YAML config loading
│   ├── keyboard.py           # Keyboard input handling
│   ├── rich_utils.py         # Rich table/panel builders
│   ├── agent_tracking.py     # Agent status tracking
│   ├── mcp_utils.py          # MCP server management
│   └── styling.py            # Color scheme constants
├── modules/                   # Standalone modules
│   ├── agent_activity.py     # Module 1
│   ├── infrastructure.py     # Module 2
│   ├── content.py            # Module 3
│   └── system_status.py      # Module 4
├── utils/                     # Utilities
│   ├── relative_time.py      # Time formatting
│   └── screenshot.py         # Screenshot capture
├── config.yaml               # Shared configuration
├── launch_modules.py         # Python launcher script
├── app_rich.py               # Original monolithic TUI (still functional)
└── MODULAR_README.md         # This file
```

### Design Principles

1. **Python-Focused**: All modules use Python + Rich library, no bash scripts
2. **Shared Utilities**: Common code extracted to `shared/` directory
3. **Independent Execution**: Each module runs standalone
4. **Consistent Styling**: Dracula-inspired color scheme across all modules
5. **Minimal Dependencies**: Only Rich library and standard library

### Color Scheme

- **Primary** (Magenta): Titles, headers
- **Secondary** (Cyan): Data, borders
- **Accent** (Yellow): Highlights, focus indicators
- **Success** (Green): Active states, success indicators
- **Dim**: Secondary information, timestamps

### Status Indicators

- `●` - Active/Connected/Running
- `○` - Idle/Disconnected/Stopped
- `⊗` - Unknown/Error

## Configuration

Edit `config.yaml` to customize:

```yaml
display:
  refresh_interval: 2  # Seconds between refreshes
  screenshot_dir: /Users/fweir/git/ai-bedo/screenshots

monitoring:
  # Add custom monitoring configs here

integrations:
  # Add custom integrations here
```

## Data Sources

### Agent Activity
- **Status Files**: `/Users/fweir/git/ai-bedo/communications/.agent-status/*.json`
- **Format**: JSON files with agent/skill activation timestamps

### Infrastructure
- **MCP Config**: `/Users/fweir/git/ai-bedo/.mcp.json`
- **Services**: Port scanning via `lsof`

### Content
- **Audio**: `/Users/fweir/git/ai-bedo/communications/{main,vm}-audio/*.txt`
- **Docs**: Markdown files from `~/git/**/{CLAUDE,README}.md`

### System Status
- **Context**: `~/.claude/file-history/{session-id}/*@v*`
- **Format**: Hash-based files with version numbers

## Development

### Adding a New Module

1. Create new file in `modules/` directory
2. Import shared utilities:
   ```python
   from agent_monitor.shared import (
       ModuleConfig,
       KeyboardHandler,
       RichTableBuilder,
       Colors,
       Symbols
   )
   ```
3. Follow existing module patterns
4. Add to launcher script

### Testing Individual Modules

```bash
cd /Users/fweir/git/internal/repos/fifth-symphony/modules

# Test imports
uv run python -c "from agent_monitor.modules.agent_activity import AgentActivityMonitor; print('OK')"

# Run standalone
uv run python -m agent_monitor.modules.agent_activity
```

## Benefits vs Monolithic TUI

| Feature | Monolithic (`app_rich.py`) | Modular |
|---------|---------------------------|---------|
| **Code Size** | 888 lines | ~250 lines per module |
| **Independent Refresh** | ❌ All panels refresh together | ✅ Each module refreshes independently |
| **Focused Workflow** | ❌ See all data always | ✅ Focus on relevant panels |
| **Terminal Arrangement** | ❌ Fixed layout | ✅ Arrange tabs as desired |
| **Easy Testing** | ❌ Test entire app | ✅ Test modules individually |
| **Performance** | ❌ Larger rendering footprint | ✅ Smaller per-module footprint |

## Troubleshooting

### Module Won't Start

**Problem**: Import errors or module not found

**Solution**:
```bash
cd /Users/fweir/git/internal/repos/fifth-symphony/modules
uv sync  # Ensure dependencies installed
```

### Launcher Script Fails

**Problem**: AppleScript errors

**Solution**:
- Ensure you're on macOS
- Grant Terminal/iTerm2 permissions in System Preferences > Privacy
- Try launching modules manually

### No Data Showing

**Problem**: Empty panels or "No X found" messages

**Solution**:
- Press `R` to refresh
- Check data source paths in code
- Verify file permissions

### Colors Look Wrong

**Problem**: Terminal doesn't support colors

**Solution**:
- Use iTerm2 or modern Terminal.app
- Ensure terminal supports 256 colors
- Check `$TERM` environment variable

## Screenshots

Each module supports screenshot capture (press `S`). Screenshots saved to:
```
/Users/fweir/git/ai-bedo/screenshots/{module}_{timestamp}.png
```

## Migration from Monolithic TUI

The original `app_rich.py` still works and remains available. Use it if you prefer a single-window view:

```bash
cd /Users/fweir/git/internal/repos/fifth-symphony/modules
uv run python -m agent_monitor
```

## Future Enhancements

- [ ] VM subagent tracking implementation
- [ ] Real MCP server connection status checking
- [ ] Audio playback integration (currently just opens file)
- [ ] Context file path resolution (currently shows hashes)
- [ ] Custom layout configurations
- [ ] tmux session support
- [ ] Remote monitoring via SSH

## License

Part of the Albedo AI Development Ecosystem.

---

**Created**: 2025-10-29
**Last Updated**: 2025-10-29
**Version**: 1.0.0
