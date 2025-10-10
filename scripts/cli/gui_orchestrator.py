"""
GUI Orchestrator Integration
Bridges the PySide6 GUI with the existing orchestrator backend
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QThread, QTimer, Signal

# Import existing orchestrator modules
sys.path.insert(0, str(Path(__file__).parent))
from modules.onepassword_manager import OnePasswordManager
from modules.output_translator import OutputTranslator
from modules.reminder_system import ReminderSystem
from modules.script_runner import ScriptRunner
from modules.voice_handler import VoiceHandler

logger = logging.getLogger(__name__)


class ScriptRunnerThread(QThread):
    """Thread for running scripts without blocking the GUI"""

    # Signals for communicating with the main thread
    output_received = Signal(str, str)  # output_text, output_type
    script_started = Signal(str)  # script_name
    script_finished = Signal(str, int)  # script_name, exit_code
    script_error = Signal(str, str)  # script_name, error_message
    waiting_for_input = Signal(str)  # script_name

    def __init__(self, script_path: Path, args: list[str] = None, parent=None):
        super().__init__(parent)
        self.script_path = script_path
        self.args = args or []
        self.script_runner = ScriptRunner(script_path.parent)
        self.should_stop = False

    def run(self):
        """Run the script in this thread"""
        script_name = self.script_path.stem

        try:
            self.script_started.emit(script_name)

            # Set up async event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                loop.run_until_complete(self._run_script_async())
            finally:
                loop.close()

        except Exception as e:
            logger.error(f"Error running script {script_name}: {e}")
            self.script_error.emit(script_name, str(e))

    async def _run_script_async(self):
        """Async script execution"""
        script_name = self.script_path.stem

        try:
            async for output_type, output in self.script_runner.run_script_async(
                self.script_path, self.args
            ):
                if self.should_stop:
                    break

                # Emit output to GUI
                self.output_received.emit(output, output_type)

                # Check if script is waiting for input
                if self.script_runner.is_waiting_for_input(output):
                    self.waiting_for_input.emit(script_name)

            # Script completed successfully
            self.script_finished.emit(script_name, 0)

        except Exception as e:
            self.script_error.emit(script_name, str(e))

    def stop_script(self):
        """Request script to stop"""
        self.should_stop = True
        self.quit()


class GuiOrchestrator(QObject):
    """Integration layer between GUI and orchestrator backend"""

    # Signals for updating the GUI
    scripts_discovered = Signal(list)  # List of script metadata
    script_output = Signal(str, str)  # output_text, output_type
    script_status_changed = Signal(str, str)  # script_name, status
    voice_status_changed = Signal(bool, bool)  # enabled, connected
    onepassword_status_changed = Signal(bool)  # connected
    reminder_triggered = Signal(str, str)  # script_name, message

    def __init__(self, config_path: Path = None, parent=None):
        super().__init__(parent)

        self.config_path = config_path or Path(__file__).parent / "config"
        self.scripts_path = Path(__file__).parent / "scripts"
        self.symlinks_path = Path(__file__).parent / "symlinks"

        # Load configuration
        self.config = self._load_config()

        # Initialize backend modules
        self.op_manager = None
        self.voice_handler = None
        self.output_translator = None
        self.reminder_system = None
        self.script_runner = ScriptRunner(self.scripts_path)
        self.symlink_manager = None  # Will be initialized with other modules

        # Track running scripts
        self.running_scripts: dict[str, ScriptRunnerThread] = {}
        self.script_metadata: dict[str, dict] = {}

        # Performance monitoring
        self.perf_timer = QTimer()
        self.perf_timer.timeout.connect(self.update_performance)
        self.perf_timer.start(2000)  # Update every 2 seconds

        # Initialize async components
        QTimer.singleShot(100, self.initialize_async_components)

    def _load_config(self) -> dict:
        """Load configuration from settings.yaml"""
        import yaml

        config_file = self.config_path / "settings.yaml"
        if config_file.exists():
            with open(config_file, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}

        # Default configuration
        return {
            "voice": {"enabled": True},
            "onepassword": {"vault": "Development"},
            "reminders": {"enabled": True},
            "scripts": {"auto_discover": True},
        }

    def initialize_async_components(self):
        """Initialize async components"""
        asyncio.create_task(self._init_async())

    async def _init_async(self):
        """Async initialization"""
        try:
            # Initialize 1Password manager
            self.op_manager = OnePasswordManager(self.config.get("onepassword", {}))

            # Try to initialize 1Password session
            op_connected = False
            try:
                op_connected = await self.op_manager.initialize_session()
            except Exception as e:
                logger.warning(f"1Password initialization failed: {e}")

            self.onepassword_status_changed.emit(op_connected)

            # Initialize voice handler
            self.voice_handler = VoiceHandler(self.config.get("voice", {}), self.op_manager)

            voice_enabled = self.config.get("voice", {}).get("enabled", True)
            voice_connected = (
                hasattr(self.voice_handler, "client") and self.voice_handler.client is not None
            )
            self.voice_status_changed.emit(voice_enabled, voice_connected)

            # Initialize output translator
            self.output_translator = OutputTranslator(self.config.get("translation", {}))

            # Initialize reminder system
            self.reminder_system = ReminderSystem(
                self.voice_handler, self.config.get("reminders", {})
            )

            # Initialize symlink manager
            from modules.symlink_manager import SymlinkManager

            self.symlink_manager = SymlinkManager(self.symlinks_path)

            logger.info("Orchestrator backend initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize orchestrator backend: {e}")

    async def discover_scripts(self) -> list[dict]:
        """Discover and analyze scripts in the scripts directory and symlinks"""
        scripts = []
        excluded_patterns = self.config.get("scripts", {}).get("excluded_patterns", [])

        # Discover scripts in main directory
        if self.scripts_path.exists():
            for script_file in self.scripts_path.glob("*.py"):
                # Skip excluded patterns
                if any(pattern in script_file.name for pattern in excluded_patterns):
                    continue

                # Analyze script
                metadata = self.script_runner.analyze_script(script_file)
                metadata["is_symlink"] = False
                metadata["type_icon"] = "📦"
                scripts.append(metadata)

                # Cache metadata
                self.script_metadata[script_file.stem] = metadata

        # Discover symlinked scripts
        if self.symlinks_path.exists() and self.symlink_manager:
            for item in self.symlinks_path.iterdir():
                # Skip metadata file
                if item.name.startswith("."):
                    continue

                # Check if it's a valid symlink to a script
                if item.is_symlink() and item.exists():
                    # Support both Python and shell scripts
                    if item.suffix in [".py", ".sh", ".bash"]:
                        # Skip excluded patterns
                        if any(pattern in item.name for pattern in excluded_patterns):
                            continue

                        # Get symlink info
                        symlink_info = self.symlink_manager.get_symlink_info(item.name)

                        # Analyze script if Python
                        if item.suffix == ".py":
                            metadata = self.script_runner.analyze_script(item)
                        else:
                            # Basic metadata for shell scripts
                            metadata = {
                                "name": item.stem,
                                "path": str(item),
                                "size": item.stat().st_size if item.exists() else 0,
                                "modified": datetime.fromtimestamp(item.stat().st_mtime)
                                if item.exists()
                                else None,
                                "has_main": True,
                                "imports": [],
                                "functions": [],
                                "classes": [],
                                "docstring": f"Shell script from {item.resolve().parent.name}",
                                "requirements": [],
                            }

                        metadata["is_symlink"] = True
                        metadata["type_icon"] = "🔗"
                        metadata["target_path"] = symlink_info.get("target_path", "Unknown")
                        scripts.append(metadata)

                        # Cache metadata
                        self.script_metadata[item.stem] = metadata

        # Sort by name
        scripts.sort(key=lambda x: x["name"])

        self.scripts_discovered.emit(scripts)
        return scripts

    def run_script(self, script_name: str, args: list[str] = None):
        """Start running a script"""
        if script_name in self.running_scripts:
            logger.warning(f"Script {script_name} is already running")
            return

        # Try to find script in various locations
        script_path = None

        # Check scripts directory
        for attempt in [
            self.scripts_path / f"{script_name}.py",
            self.scripts_path / script_name,
        ]:
            if attempt.exists():
                script_path = attempt
                break

        # If not found, check symlinks directory
        if not script_path:
            for attempt in [
                self.symlinks_path / script_name,
                self.symlinks_path / f"{script_name}.py",
                self.symlinks_path / f"{script_name}.sh",
                self.symlinks_path / f"{script_name}.bash",
            ]:
                if attempt.exists():
                    script_path = attempt
                    break

        if not script_path:
            logger.error(f"Script not found: {script_name}")
            return

        # Create and start script runner thread
        runner_thread = ScriptRunnerThread(script_path, args, parent=self)

        # Connect signals
        runner_thread.output_received.connect(self._on_script_output)
        runner_thread.script_started.connect(self._on_script_started)
        runner_thread.script_finished.connect(self._on_script_finished)
        runner_thread.script_error.connect(self._on_script_error)
        runner_thread.waiting_for_input.connect(self._on_script_waiting)

        # Start the thread
        self.running_scripts[script_name] = runner_thread
        runner_thread.start()

        logger.info(f"Started script: {script_name}")

    def stop_script(self, script_name: str):
        """Stop a running script"""
        if script_name in self.running_scripts:
            runner_thread = self.running_scripts[script_name]
            runner_thread.stop_script()

            # Wait for thread to finish (with timeout)
            if runner_thread.wait(5000):  # 5 second timeout
                del self.running_scripts[script_name]
                self.script_status_changed.emit(script_name, "stopped")
                logger.info(f"Stopped script: {script_name}")
            else:
                logger.warning(f"Script {script_name} did not stop gracefully")

    def stop_all_scripts(self):
        """Stop all running scripts"""
        for script_name in list(self.running_scripts.keys()):
            self.stop_script(script_name)

    def get_running_scripts(self) -> list[str]:
        """Get list of currently running scripts"""
        return list(self.running_scripts.keys())

    def is_script_running(self, script_name: str) -> bool:
        """Check if a script is currently running"""
        return script_name in self.running_scripts

    def set_voice_enabled(self, enabled: bool):
        """Enable/disable voice feedback"""
        if self.voice_handler:
            asyncio.create_task(self.voice_handler.set_enabled(enabled))
            self.voice_status_changed.emit(enabled, True)

    def set_reminders_enabled(self, enabled: bool):
        """Enable/disable reminder system"""
        if self.reminder_system:
            self.reminder_system.set_enabled(enabled)

    def _on_script_output(self, output_text: str, output_type: str):
        """Handle script output"""
        self.script_output.emit(output_text, output_type)

        # Translate for voice if enabled
        if self.voice_handler and self.output_translator:
            asyncio.create_task(self._handle_voice_translation(output_text))

    async def _handle_voice_translation(self, output_text: str):
        """Handle voice translation of output"""
        try:
            if self.output_translator.should_voice_output(output_text):
                voice_message = await self.output_translator.translate_for_voice(output_text)
                if voice_message:
                    await self.voice_handler.speak(voice_message, priority="low")
        except Exception as e:
            logger.error(f"Error in voice translation: {e}")

    def _on_script_started(self, script_name: str):
        """Handle script started"""
        self.script_status_changed.emit(script_name, "running")

        # Start reminder monitoring if enabled
        if self.reminder_system:
            asyncio.create_task(self.reminder_system.monitor_script(script_name))

        # Voice announcement
        if self.voice_handler:
            asyncio.create_task(self.voice_handler.speak(f"Starting execution of {script_name}"))

    def _on_script_finished(self, script_name: str, exit_code: int):
        """Handle script finished"""
        if script_name in self.running_scripts:
            del self.running_scripts[script_name]

        status = "completed" if exit_code == 0 else "failed"
        self.script_status_changed.emit(script_name, status)

        # Stop reminder monitoring
        if self.reminder_system:
            asyncio.create_task(self.reminder_system.stop_monitoring(script_name))

        # Voice announcement
        if self.voice_handler:
            if exit_code == 0:
                asyncio.create_task(
                    self.voice_handler.speak(f"{script_name} completed successfully")
                )
            else:
                asyncio.create_task(
                    self.voice_handler.speak(
                        f"{script_name} failed with exit code {exit_code}", priority="high"
                    )
                )

    def _on_script_error(self, script_name: str, error_message: str):
        """Handle script error"""
        if script_name in self.running_scripts:
            del self.running_scripts[script_name]

        self.script_status_changed.emit(script_name, "error")

        # Voice error notification
        if self.voice_handler and self.output_translator:
            simplified_error = self.output_translator.simplify_error(error_message)
            asyncio.create_task(
                self.voice_handler.speak(
                    f"Error in {script_name}: {simplified_error}", priority="high"
                )
            )

    def _on_script_waiting(self, script_name: str):
        """Handle script waiting for input"""
        self.script_status_changed.emit(script_name, "waiting")

        # Voice notification
        if self.voice_handler:
            asyncio.create_task(
                self.voice_handler.speak(
                    f"{script_name} is waiting for your input", priority="high"
                )
            )

    def update_performance(self):
        """Update performance metrics"""
        # This will be connected to update GUI performance indicators

    def cleanup(self):
        """Clean up resources"""
        # Stop all running scripts
        self.stop_all_scripts()

        # Cleanup backend modules
        if self.voice_handler:
            asyncio.create_task(self.voice_handler.cleanup())

        if self.op_manager:
            asyncio.create_task(self.op_manager.cleanup())

        if self.reminder_system:
            asyncio.create_task(self.reminder_system.stop_all_monitoring())
