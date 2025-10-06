#!/usr/bin/env python3
"""
Fifth Symphony - Complete Integrated System Example

Demonstrates full integration of all Attention-optimized features:
- Voice I/O (speech-to-text + text-to-speech)
- Voice permission system with code-free output
- Visual Novel avatar with LED indicators
- Folder management with real-time monitoring
- HUD overlay with status indicators
- Emotion detection and avatar synchronization

This example shows how all components work together.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

from modules.avatar_emotion_engine import AvatarEmotionEngine
from modules.claude_integration import ClaudeIntegration
from modules.folder_manager import FileEvent, FolderManager
from modules.onepassword_manager import OnePasswordManager
from modules.visual_novel_widget import AvatarState, VisualNovelWidget
from modules.voice_handler import VoiceHandler
from modules.voice_permission_hook import VoicePermissionHook, VoicePermissionResponse


class IntegratedFifthSymphony(QMainWindow):
    """
    Complete Fifth Symphony integrated system.

    Combines:
    - Visual Novel avatar
    - Voice I/O with permissions
    - Folder management
    - HUD overlay
    - Emotion detection
    """

    def __init__(self):
        super().__init__()

        # Load configuration
        self.config = self._load_config()

        # Initialize components
        self._init_voice_system()
        self._init_avatar_system()
        self._init_folder_system()
        self._init_claude_monitoring()

        # Setup UI
        self._setup_ui()

        # Connect signals
        self._connect_signals()

        print("✅ Fifth Symphony Integrated System Ready!")
        print("\n🎯 Features Active:")
        print("  - 🎤 Voice I/O (Whisper + ElevenLabs)")
        print("  - 🎨 Visual Novel Avatar")
        print("  - 📁 Folder Management")
        print("  - 🔵 LED Status Indicators")
        print("  - 🤖 Emotion Detection")
        print("  - 🎭 Claude Code Monitoring")

    def _load_config(self) -> dict:
        """Load configuration files."""
        config = {}

        # Load main settings
        settings_path = Path(__file__).parent.parent / "config" / "settings.yaml"
        if settings_path.exists():
            with open(settings_path) as f:
                config.update(yaml.safe_load(f) or {})

        # Load folder config
        folders_path = Path(__file__).parent.parent / "config" / "folders.yaml"
        if folders_path.exists():
            with open(folders_path) as f:
                folders_config = yaml.safe_load(f) or {}
                config.update(folders_config)

        return config

    def _init_voice_system(self):
        """Initialize voice I/O system."""
        print("🎤 Initializing voice system...")

        # 1Password manager
        self.op_manager = OnePasswordManager(
            self.config.get("onepassword", {})
        )

        # Voice handler
        self.voice_handler = VoiceHandler(
            self.config.get("voice", {}),
            self.op_manager
        )

        # Voice permission hook
        self.voice_hook = VoicePermissionHook(
            voice_handler=self.voice_handler,
            config=self.config.get("voice_permission", {}),
            permission_callback=self._voice_permission_callback
        )

        print("  ✅ Voice system ready")

    def _init_avatar_system(self):
        """Initialize visual avatar system."""
        print("🎨 Initializing avatar system...")

        # Visual Novel widget
        self.avatar = VisualNovelWidget(always_on_top=True)
        self.avatar.resize(400, 500)

        # Emotion engine
        self.emotion_engine = AvatarEmotionEngine()

        print("  ✅ Avatar system ready")

    def _init_folder_system(self):
        """Initialize folder management."""
        print("📁 Initializing folder management...")

        # Folder manager
        self.folder_manager = FolderManager(self.config)

        # Add common folders
        self._setup_folders()

        print("  ✅ Folder management ready")

    def _init_claude_monitoring(self):
        """Initialize Claude Code monitoring."""
        print("🎭 Initializing Claude Code monitoring...")

        # Claude integration
        self.claude_integration = ClaudeIntegration(
            avatar=self.avatar,
            voice=self.voice_handler,
            enable_voice=False  # Disable voice to avoid noise
        )

        # Start monitoring (auto-detects session directory)
        self.claude_integration.start_monitoring()

        print("  ✅ Claude Code monitoring ready")

    def _setup_folders(self):
        """Setup common folders to manage."""
        common_folders = {
            "downloads": Path.home() / "Downloads",
            "documents": Path.home() / "Documents",
            "desktop": Path.home() / "Desktop"
        }

        for name, path in common_folders.items():
            if path.exists():
                try:
                    self.folder_manager.add_folder(name, path, watch=False)
                    # Start watching with callback
                    self.folder_manager.start_watching(name, callback=self._on_file_event)
                    print(f"  📁 Watching: {name}")
                except Exception as e:
                    print(f"  ⚠️ Couldn't watch {name}: {e}")

    def _setup_ui(self):
        """Setup user interface."""
        self.setWindowTitle("Fifth Symphony - Integrated System")
        self.resize(800, 600)

        # Main widget
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)

        # Add HUD (would normally be in dashboard)
        # For this example, we'll just track state

        # Status label
        from PySide6.QtWidgets import QLabel
        self.status_label = QLabel("System: Ready")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #2d2d2d;
                color: #00ff00;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.status_label)

        # Controls
        from PySide6.QtWidgets import QHBoxLayout, QPushButton
        controls = QHBoxLayout()

        btn_speak = QPushButton("🎤 Test Voice Output")
        btn_speak.clicked.connect(self.test_voice_output)
        controls.addWidget(btn_speak)

        btn_avatar = QPushButton("🎨 Show Avatar")
        btn_avatar.clicked.connect(self.show_avatar)
        controls.addWidget(btn_avatar)

        btn_folders = QPushButton("📁 Folder Summary")
        btn_folders.clicked.connect(self.show_folder_summary)
        controls.addWidget(btn_folders)

        btn_claude = QPushButton("🎭 Claude Stats")
        btn_claude.clicked.connect(self.show_claude_stats)
        controls.addWidget(btn_claude)

        layout.addLayout(controls)

        # Event log
        from PySide6.QtWidgets import QTextEdit
        self.event_log = QTextEdit()
        self.event_log.setReadOnly(True)
        self.event_log.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #00ff00;
                font-family: monospace;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.event_log)

        self.log("Fifth Symphony Integrated System Initialized")

    def _connect_signals(self):
        """Connect component signals."""
        # Avatar state changes
        self.avatar.state_changed.connect(self._on_avatar_state_changed)

    def log(self, message: str):
        """Add message to event log."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.event_log.append(f"[{timestamp}] {message}")

    # =========================================================================
    # Voice System Integration
    # =========================================================================

    async def _voice_permission_callback(self, request):
        """
        Handle voice permission request.

        This is where you'd show a UI dialog. For this example,
        we'll auto-approve simple responses.
        """
        self.log(f"🎤 Voice Permission Request (complexity: {request.parsed.complexity_score}/10)")

        # Auto-approve simple responses
        if request.parsed.complexity_score <= 5:
            self.log("  ✅ Auto-approved (simple response)")
            return VoicePermissionResponse.YES

        # For complex responses, ask user (simplified for demo)
        self.log("  ⏳ Awaiting user permission...")
        # In real implementation, show dialog
        return VoicePermissionResponse.YES

    def test_voice_output(self):
        """Test voice output with avatar synchronization."""
        asyncio.create_task(self._test_voice_output())

    async def _test_voice_output(self):
        """Test voice output (async)."""
        self.log("🎤 Testing voice output with avatar...")

        # Set avatar to talking state
        self.avatar.set_voice_speaking(True)
        self.log("  🎨 Avatar: Talking state + blue LED")

        # Process test response through voice hook
        test_response = """
Hello! I'm Fifth Symphony, your Attention-friendly AI assistant.

I can help you with automation, voice feedback, and file management.
"""

        await self.voice_hook.on_response(
            test_response,
            context={"source": "demo", "test": True}
        )

        # Reset avatar
        await asyncio.sleep(2)
        self.avatar.set_voice_speaking(False)
        self.log("  🎨 Avatar: Idle state")

    # =========================================================================
    # Avatar System Integration
    # =========================================================================

    def _on_avatar_state_changed(self, state: AvatarState):
        """Handle avatar state changes."""
        self.log(f"🎨 Avatar state: {state.value}")

    def show_avatar(self):
        """Show avatar window."""
        self.avatar.show()
        self.log("🎨 Avatar window displayed")

    async def demonstrate_emotions(self):
        """Demonstrate emotion detection and avatar sync."""
        self.log("🤖 Demonstrating emotion detection...")

        test_messages = [
            ("Success! Deployment complete.", "happy"),
            ("Error: Connection failed.", "sad"),
            ("Wow! Found something interesting!", "surprised"),
            ("Analyzing repository structure...", "thinking"),
        ]

        for message, expected_emotion in test_messages:
            # Detect emotion
            result = self.emotion_engine.detect_emotion(message)

            self.log(f"  📝 '{message}'")
            self.log(f"  🎭 Emotion: {result.emotion.value} ({result.confidence:.2f})")

            # Update avatar based on emotion
            if result.emotion.value in ["happy", "excited", "proud"]:
                self.avatar.set_state(AvatarState.TALKING)
            elif result.emotion.value in ["sad", "worried"]:
                self.avatar.set_state(AvatarState.ERROR)
            elif result.emotion.value == "thinking":
                self.avatar.set_state(AvatarState.PROCESSING)

            await asyncio.sleep(2)

        # Reset
        self.avatar.set_state(AvatarState.IDLE)
        self.log("  🎨 Emotion demo complete")

    # =========================================================================
    # Folder Management Integration
    # =========================================================================

    def show_folder_summary(self):
        """Show folder summary."""
        asyncio.create_task(self._show_folder_summary())

    async def _show_folder_summary(self):
        """Show folder summary (async)."""
        self.log("📁 Generating folder summary...")

        try:
            # Get downloads summary
            summary = await self.folder_manager.get_folder_summary("downloads")

            self.log(f"  📊 Total files: {summary.total_files}")
            self.log(f"  💾 Total size: {self.folder_manager.format_size(summary.total_size)}")

            # Top file types
            sorted_types = sorted(
                summary.file_types.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]

            self.log("  📝 Top file types:")
            for ext, count in sorted_types:
                self.log(f"    {ext}: {count} files")

            # Recent files
            if summary.recent_files:
                self.log(f"  🕐 Recent files: {len(summary.recent_files)}")

            # Cleanup suggestions
            if summary.old_files:
                self.log(f"  🗑️  Old files: {len(summary.old_files)} (cleanup?)")

        except Exception as e:
            self.log(f"  ❌ Error: {e}")

    def _on_file_event(self, event: FileEvent):
        """Handle file system events."""
        self.log(f"📁 {event.action.value.upper()}: {event.path.name}")

        # Flash special LED on avatar
        self.avatar.set_led("special", True, pulsing=True)

        # Turn off after 2 seconds
        QTimer.singleShot(2000, lambda: self.avatar.set_led("special", False))

    # =========================================================================
    # Claude Code Monitoring Integration
    # =========================================================================

    def show_claude_stats(self):
        """Show Claude Code activity statistics."""
        stats = self.claude_integration.get_statistics()
        sessions = self.claude_integration.get_active_sessions()

        self.log("🎭 Claude Code Activity Statistics:")
        self.log(f"  📊 User Prompts: {stats['user_prompts']}")
        self.log(f"  📖 Files Read: {stats['files_read']}")
        self.log(f"  ✍️  Files Written: {stats['files_written']}")
        self.log(f"  ✏️  Files Edited: {stats['files_edited']}")
        self.log(f"  💻 Bash Commands: {stats['bash_commands']}")
        self.log(f"  🌐 Web Fetches: {stats['web_fetches']}")
        self.log(f"  🎯 Active Sessions: {len(sessions)}")

        for session_id, session_info in sessions.items():
            self.log(f"    Session: {session_id[:8]}...")
            self.log(f"      CWD: {session_info.get('cwd', 'unknown')}")
            self.log(f"      Branch: {session_info.get('branch', 'unknown')}")


# =============================================================================
# Main Application
# =============================================================================

def main():
    """Run integrated system."""
    app = QApplication(sys.argv)

    # Create integrated system
    window = IntegratedFifthSymphony()
    window.show()

    # Show avatar
    window.avatar.show()

    # Log startup complete
    window.log("")
    window.log("🎉 All systems operational!")
    window.log("")
    window.log("💡 Try these:")
    window.log("  - Click 'Test Voice Output' for voice demo")
    window.log("  - Click 'Show Avatar' to display avatar window")
    window.log("  - Click 'Folder Summary' for file statistics")
    window.log("")
    window.log("🔵 Blue LED = Voice speaking")
    window.log("🟢 Green LED = Microphone recording")
    window.log("🟡 Yellow LED = AI processing")
    window.log("🔴 Red LED = Error state")
    window.log("🟣 Purple LED = Special event")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
