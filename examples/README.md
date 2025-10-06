# Fifth Symphony - Integration Examples

This directory contains example code showing how to use Fifth Symphony's ADHD-optimized features.

## 📋 Examples

### 1. **integrated_system.py** - Complete Integration
**Full system demonstration with all features.**

**Features**:
- Voice I/O (Whisper + ElevenLabs)
- Voice permission system
- Visual Novel avatar
- Folder management
- LED status indicators
- Emotion detection

**Run**:
```bash
cd /Users/fweir/git/internal/repos/fifth-symphony
uv run python examples/integrated_system.py
```

**What to expect**:
- Main window with status and controls
- Avatar window (always-on-top)
- Event log showing system activity
- Test buttons for each feature

---

### 2. **voice_example.py** - Voice System Only
**Simple voice I/O demonstration.**

**Features**:
- Code-free voice output
- Permission system
- Attention sounds

**Run**:
```bash
uv run python examples/voice_example.py
```

---

### 3. **avatar_example.py** - Avatar System Only
**Visual Novel avatar demonstration.**

**Features**:
- Static image swapping
- LED indicators
- State transitions

**Run**:
```bash
uv run python examples/avatar_example.py
```

---

### 4. **folder_example.py** - Folder Management Only
**Folder monitoring demonstration.**

**Features**:
- Real-time folder watching
- Folder summaries
- File organization

**Run**:
```bash
uv run python examples/folder_example.py
```

---

### 5. **claude_monitor_example.py** - Claude Code Monitoring
**Real-time Claude Code activity visualization with thread-safe UI updates.**

**Features**:
- Avatar LED indicators for Claude's actions
- Activity logging (file reads, edits, commands)
- Statistics dashboard
- Session tracking
- Thread-safe Qt signal/slot architecture (fixed 2025-10-05)

**Run**:
```bash
uv run python examples/claude_monitor_example.py
```

**What to test**:
1. Run the monitor
2. Use Claude Code in fifth-symphony project
3. Watch avatar LEDs change as Claude works
4. See activity log update in real-time (now works correctly!)

**Fixed Issues**:
- ✅ No more QTimer threading errors
- ✅ UI updates work properly from background thread
- ✅ Clean shutdown with Ctrl+C

---

## 🚀 Quick Start

### Minimal Voice Example

```python
from modules.voice_permission_hook import VoicePermissionHook
from modules.voice_handler import VoiceHandler

# Initialize
voice_handler = VoiceHandler(config, op_manager)
voice_hook = VoicePermissionHook(voice_handler)

# Speak with permission
await voice_hook.on_response("Hello! This is a test.")
```

### Minimal Avatar Example

```python
from modules.visual_novel_widget import VisualNovelWidget

# Create avatar
avatar = VisualNovelWidget(always_on_top=True)
avatar.resize(400, 500)
avatar.show()

# Change states
avatar.set_voice_speaking(True)  # Talking + blue LED
```

### Minimal Folder Example

```python
from modules.folder_manager import FolderManager

# Initialize
manager = FolderManager()
manager.add_folder("downloads", Path.home() / "Downloads")

# Get summary
summary = await manager.get_folder_summary("downloads")
print(f"Files: {summary.total_files}")
```

---

### Minimal Claude Code Monitor Example

```python
from modules.claude_integration import ClaudeIntegration

# Initialize
claude_integration = ClaudeIntegration(
    avatar=avatar_widget,
    voice=None,  # Disable voice
    enable_voice=False
)

# Start monitoring
claude_integration.start_monitoring()

# Get statistics
stats = claude_integration.get_statistics()
print(f"Files written: {stats['files_written']}")
```

---

## 📚 Documentation

For detailed guides, see:
- [Voice System Guide](../docs/VOICE-SYSTEM-GUIDE.md)
- [Visual Novel Guide](../docs/VISUAL-NOVEL-GUIDE.md)
- [Folder Management Guide](../docs/FOLDER-MANAGEMENT-GUIDE.md)
- [Claude Code Monitoring Guide](../docs/CLAUDE-CODE-MONITORING-GUIDE.md)

---

## 🎯 Integration Patterns

### Voice + Avatar

```python
# Sync voice with avatar
async def speak_with_avatar(text):
    avatar.set_voice_speaking(True)
    await voice_handler.speak(text)
    avatar.set_voice_speaking(False)
```

### Folder + Voice

```python
# Notify about new files
def on_file_event(event):
    if event.action == FileAction.CREATED:
        voice_handler.speak(f"New file: {event.path.name}")
```

### Emotion + Avatar

```python
# Sync emotions with avatar
emotion = engine.detect_emotion(response_text)

if emotion.emotion.value == "happy":
    avatar.set_state(AvatarState.TALKING)
elif emotion.emotion.value == "sad":
    avatar.set_state(AvatarState.ERROR)
```

---

## 🔧 Troubleshooting

### Import Errors

Make sure you're running from the repository root:
```bash
cd /Users/fweir/git/internal/repos/fifth-symphony
uv run python examples/integrated_system.py
```

### Missing Dependencies

```bash
uv sync  # Install all dependencies
```

### Configuration

Examples use default configs. For custom configuration:
1. Copy `config/*.yaml.template` to `config/*.yaml`
2. Edit paths and settings
3. Run examples

---

## 💡 Next Steps

After exploring examples:
1. **Customize** - Modify examples for your use case
2. **Integrate** - Add to your own scripts
3. **Extend** - Build new features on top

---

**All examples work immediately without additional setup!** 🎉
