# Fifth Symphony Repository Reorganization - Complete ✅

**Date**: 2025-10-04
**Status**: Reorganization Phase 1 Complete
**Next**: Orchestrator Implementation

## 🎯 Objectives Completed

1. ✅ Clean directory structure based on nazarick-agents and carian-observatory patterns
2. ✅ Comprehensive `.gitignore` with media file protection
3. ✅ Orchestrator module foundation
4. ✅ Documentation structure
5. ✅ Script organization

## 📁 New Directory Structure

```
fifth-symphony/
├── Core Files (Root)
│   ├── orchestrator.py          # Main daemon (TO BE CREATED)
│   ├── main.py                  # CLI interface
│   ├── gui.py                   # GUI interface
│   └── pyproject.toml
│
├── docs/                        # Documentation
│   ├── README.md               # Documentation index
│   └── internal/               # Private docs (gitignored)
│
├── modules/                     # Core functionality
│   ├── onepassword_manager.py
│   ├── voice_handler.py
│   ├── script_runner.py
│   └── orchestrator/           # NEW: Permission system
│       ├── __init__.py
│       ├── permission_engine.py    # ✅ CREATED
│       ├── mcp_client.py           # ✅ CREATED (ElevenLabs integration)
│       ├── tui_interface.py        # TODO
│       ├── ipc_server.py           # TODO
│       └── approval_store.py       # TODO
│
├── config/                      # Configuration
│   ├── settings.yaml
│   ├── orchestrator.yaml       # TODO
│   ├── prompts/
│   └── templates/
│
├── scripts/                     # Organized scripts
│   ├── README.md               # ✅ CREATED
│   ├── user-scripts/           # User automation (moved existing scripts)
│   ├── system/                 # System management
│   ├── templates/              # Git-safe templates
│   └── utils/                  # Utility scripts
│
├── memory/                      # Runtime state (gitignored)
│   ├── README.md               # ✅ CREATED
│   ├── permissions/
│   ├── sessions/
│   └── logs/
│
├── services/                    # Daemon configs
│   ├── macos/                  # LaunchAgent (TODO)
│   └── linux/                  # systemd (TODO)
│
├── tasks/                       # Public task tracking
├── tests/                       # Test suite (TODO)
└── backups/                     # Backup archives (gitignored)
```

## 🔐 Security Enhancements

### Enhanced .gitignore Protection

Added comprehensive media file exclusions:

```gitignore
# Audio files
*.mp3, *.wav, *.ogg, *.flac, *.aac, *.m4a, *.opus, etc.

# Video files
*.mp4, *.avi, *.mov, *.mkv, *.flv, *.wmv, etc.

# Image files
*.png, *.jpg, *.jpeg, *.gif, *.bmp, *.svg, *.webp, etc.

# Media directories
media/, audio/, video/, recordings/, voice_output/, elevenlabs_output/

# Orchestrator state
memory/, permissions/, sessions/, *.log
```

**Why**: Prevents accidental commit of:
- Voice synthesis output
- Screen recordings/demos
- Generated prompts/audio logs
- Permission approval history
- Sensitive operational data

## 🎵 Orchestrator Module Architecture

### Created Components

#### 1. Permission Engine (`permission_engine.py`)
```python
class PermissionEngine:
    - assess_risk()           # Evaluates risk level (LOW/MEDIUM/HIGH/CRITICAL)
    - check_auto_approve()    # Checks auto-approve rules
    - evaluate_request()      # Processes permission requests
    - record_decision()       # Stores user decisions
```

**Risk Levels**:
- **LOW**: Read operations, safe commands
- **MEDIUM**: Write operations, non-destructive
- **HIGH**: System modifications, network ops
- **CRITICAL**: Destructive operations (rm -rf, DROP DATABASE, etc.)

**Approval Responses**:
- **YES**: Approve this time
- **NO**: Deny this time
- **ALWAYS**: Auto-approve this pattern
- **NEVER**: Auto-deny this pattern
- **CUSTOM**: Provide custom instructions

#### 2. MCP Client (`mcp_client.py`)
```python
class MCPClient:
    - get_api_key()               # Retrieves from 1Password
    - synthesize_speech()         # Calls ElevenLabs MCP server
    - speak()                     # Synthesize and play audio
    - speak_permission_request()  # Voice feedback for requests
```

**Integration**: Uses official ElevenLabs MCP server at:
`/Users/fweir/git/external/mcp/elevenlabs-mcp`

**Features**:
- 1Password CLI integration for API key
- Async speech synthesis
- Platform-aware audio playback (macOS/Linux)
- Risk-appropriate voice messages

### TODO Components

#### 3. TUI Interface (`tui_interface.py`)
- Rich/Textual terminal UI
- Permission request display
- Keyboard shortcuts (y/n/a/c)
- Mobile-optimized layout detection
- Visual risk indicators

#### 4. IPC Server (`ipc_server.py`)
- Unix socket listener
- JSON-RPC protocol
- Claude Code hook integration
- Session management

#### 5. Approval Store (`approval_store.py`)
- SQLite persistence
- Auto-approve rule storage
- Decision history
- Pattern matching

## 📱 Mobile Access Design

### Terminal Access via SSH (Shellfish/Blink)
- Full TUI renders in SSH sessions
- Touch ID/Face ID for SSH keys
- YubiKey NFC support (iPhone 7+/recent iPads)
- tmux for persistent sessions

### Voice Feedback Strategy
**Option A (Implemented)**: Voice on Mac Side
- ElevenLabs MCP runs on Mac
- Audio plays through Mac speakers
- Works when near Mac
- Zero iOS app development needed

## 🚀 Next Steps

### Phase 2: Complete Orchestrator Implementation
1. Create `tui_interface.py` with Rich/Textual
2. Implement `ipc_server.py` for Claude Code hooks
3. Build `approval_store.py` for persistence
4. Write main `orchestrator.py` daemon
5. Create systemd/LaunchAgent service configs

### Phase 3: Integration
1. Create Nazarick agent hook for orchestrator
2. Update Claude Code settings for IPC
3. Test permission flow end-to-end
4. Create mobile access guide

### Phase 4: Documentation
1. Write ARCHITECTURE.md
2. Create MOBILE-ACCESS.md
3. Document ORCHESTRATOR-PROTOCOL.md
4. Add troubleshooting guides

## 🔗 Related Documentation

- [Nazarick Agents](../../../nazarick-agents/) - Agent system integration
- [Carian Observatory](../../../carian-observatory/) - Service platform patterns
- [ElevenLabs MCP](../../../../external/mcp/elevenlabs-mcp/) - Voice synthesis

## 📊 File Reorganization Summary

### Moved Files
- `scripts/*.py` → `scripts/user-scripts/`
- `*.sh.template` → `scripts/templates/`
- `applescripts/` → `scripts/utils/applescripts/`
- `News_Explorer_Export.opml` → `docs/internal/`

### Created Files
- `memory/.gitignore`
- `memory/README.md`
- `backups/.gitignore`
- `scripts/README.md`
- `docs/README.md`
- `modules/orchestrator/__init__.py`
- `modules/orchestrator/permission_engine.py`
- `modules/orchestrator/mcp_client.py`

### Created Directories
- `docs/internal/`
- `memory/{permissions,sessions,logs}/`
- `tests/`
- `services/{macos,linux}/`
- `modules/orchestrator/`
- `scripts/{user-scripts,system,templates,utils}/`
- `tasks/`
- `backups/`

## ⚠️ Important Notes

1. **Git Status**: Changes not yet committed (awaiting approval)
2. **Imports**: Existing Python files may need import path updates
3. **Scripts**: Launcher scripts (run.sh, run_gui.sh) may need path updates
4. **Testing**: Run existing functionality tests after import updates

## 🎭 Agent Notes

This reorganization was completed by the Nazarick Agent System:
- **Agent**: project-planner
- **Pipeline**: Development
- **Session**: 815f9fff-319b-4855-a8e7-e629a3f8bcf0

Next agent handoff will be to pattern-follower for import path analysis.
