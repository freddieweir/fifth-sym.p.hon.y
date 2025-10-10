#!/usr/bin/env python3
"""
Python Orchestrator GUI
Modern PySide6 interface with dark theme and embedded terminal
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import qasync

# Third-party imports
import qdarktheme
import qtawesome as qta
from PySide6.QtCore import (
    QSettings,
    Qt,
    QTimer,
    Signal,
    Slot,
)
from PySide6.QtGui import (
    QAction,
    QFont,
    QTextCursor,
)

# PySide6 imports
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMenu,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStatusBar,
    QSystemTrayIcon,
    QTextEdit,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Local imports
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScriptCard(QFrame):
    """Visual card representing a Python script"""

    script_selected = Signal(str)  # Emits script name when selected

    def __init__(self, script_path: Path, metadata: dict[str, Any], parent=None):
        super().__init__(parent)
        self.script_path = script_path
        self.metadata = metadata
        self.is_running = False
        self.is_selected = False

        self.setup_ui()
        self.apply_styling()

    def setup_ui(self):
        """Set up the card UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header with icon and title
        header_layout = QHBoxLayout()

        # Script icon
        self.icon_label = QLabel()
        icon = qta.icon("fa5s.file-code", color="#61DAFB")
        self.icon_label.setPixmap(icon.pixmap(32, 32))
        header_layout.addWidget(self.icon_label)

        # Script name
        self.title_label = QLabel(self.metadata.get("name", self.script_path.stem))
        self.title_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.title_label.setWordWrap(True)
        header_layout.addWidget(self.title_label, 1)

        # Status indicator
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(12, 12)
        self.update_status_indicator("ready")
        header_layout.addWidget(self.status_indicator)

        layout.addLayout(header_layout)

        # Description
        docstring = self.metadata.get("docstring")
        if docstring is None:
            description = "No description available"
        else:
            description = str(docstring)[:100]
            if len(description) == 100:
                description += "..."

        self.description_label = QLabel(description)
        self.description_label.setFont(QFont("Arial", 9))
        self.description_label.setWordWrap(True)
        self.description_label.setMaximumHeight(60)
        layout.addWidget(self.description_label)

        # Footer with metadata
        footer_layout = QHBoxLayout()

        # Last modified
        modified = self.metadata.get("modified", datetime.now())
        if isinstance(modified, datetime):
            modified_str = modified.strftime("%m/%d %H:%M")
        else:
            modified_str = "Unknown"

        self.modified_label = QLabel(f"Modified: {modified_str}")
        self.modified_label.setFont(QFont("Arial", 8))
        footer_layout.addWidget(self.modified_label)

        footer_layout.addStretch()

        # Functions count
        func_count = len(self.metadata.get("functions", []))
        self.functions_label = QLabel(f"{func_count} functions")
        self.functions_label.setFont(QFont("Arial", 8))
        footer_layout.addWidget(self.functions_label)

        layout.addLayout(footer_layout)

    def apply_styling(self):
        """Apply visual styling to the card"""
        self.setFrameStyle(QFrame.Box)
        self.setLineWidth(1)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumSize(200, 120)
        self.setMaximumSize(250, 150)

        # Default styling
        self.setStyleSheet("""
            ScriptCard {
                background-color: #2b2b2b;
                border: 1px solid #404040;
                border-radius: 8px;
                padding: 8px;
            }
            ScriptCard:hover {
                background-color: #353535;
                border-color: #61DAFB;
            }
        """)

    def update_status_indicator(self, status: str):
        """Update the status indicator color"""
        colors = {
            "ready": "#28a745",  # Green
            "running": "#007bff",  # Blue
            "waiting": "#ffc107",  # Yellow
            "error": "#dc3545",  # Red
            "completed": "#6f42c1",  # Purple
        }

        color = colors.get(status, "#6c757d")  # Gray default
        self.status_indicator.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                border-radius: 6px;
            }}
        """)

    def set_selected(self, selected: bool):
        """Set card selection state"""
        self.is_selected = selected
        if selected:
            self.setStyleSheet("""
                ScriptCard {
                    background-color: #404040;
                    border: 2px solid #61DAFB;
                    border-radius: 8px;
                }
            """)
        else:
            self.apply_styling()

    def set_running(self, running: bool):
        """Set card running state"""
        self.is_running = running
        if running:
            self.update_status_indicator("running")
            self.icon_label.setPixmap(qta.icon("fa5s.play-circle", color="#007bff").pixmap(32, 32))
        else:
            self.update_status_indicator("ready")
            self.icon_label.setPixmap(qta.icon("fa5s.file-code", color="#61DAFB").pixmap(32, 32))

    def mousePressEvent(self, event):
        """Handle mouse click"""
        if event.button() == Qt.LeftButton:
            self.script_selected.emit(self.script_path.stem)
        super().mousePressEvent(event)


class TerminalWidget(QTextEdit):
    """Custom terminal-like text widget"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_terminal()

    def setup_terminal(self):
        """Configure terminal appearance and behavior"""
        # Set monospace font
        # Use Monaco on macOS, Courier on other systems
        font = QFont("Monaco" if sys.platform == "darwin" else "Courier", 10)
        if not font.exactMatch():
            font = QFont("Monaco", 10)  # macOS fallback
        if not font.exactMatch():
            font = QFont("DejaVu Sans Mono", 10)  # Linux fallback

        self.setFont(font)

        # Set terminal colors and styling
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 8px;
            }
        """)

        # Configure behavior
        self.setReadOnly(True)
        self.setLineWrapMode(QTextEdit.WidgetWidth)

    def append_output(self, text: str, output_type: str = "stdout"):
        """Append output with appropriate coloring"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)

        # Set color based on output type
        if output_type == "stderr":
            color = "#ff6b6b"  # Red for errors
        elif "warning" in text.lower():
            color = "#ffd93d"  # Yellow for warnings
        elif "success" in text.lower() or "completed" in text.lower():
            color = "#6bcf7f"  # Green for success
        else:
            color = "#ffffff"  # Default white

        # Insert colored text
        cursor.insertHtml(f'<span style="color: {color};">{text}</span>')

        # Auto-scroll to bottom
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_output(self):
        """Clear the terminal output"""
        self.clear()


class StatusPanel(QWidget):
    """Panel showing system status and indicators"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Set up the status panel UI"""
        layout = QVBoxLayout(self)

        # System Status Group
        system_group = QGroupBox("System Status")
        system_layout = QVBoxLayout(system_group)

        self.voice_status = QLabel("🔊 Voice: Ready")
        self.voice_status.setFont(QFont("Arial", 10))
        system_layout.addWidget(self.voice_status)

        self.onepassword_status = QLabel("🔐 1Password: Connected")
        self.onepassword_status.setFont(QFont("Arial", 10))
        system_layout.addWidget(self.onepassword_status)

        self.reminder_status = QLabel("⏰ Reminders: Active")
        self.reminder_status.setFont(QFont("Arial", 10))
        system_layout.addWidget(self.reminder_status)

        layout.addWidget(system_group)

        # Running Scripts Group
        scripts_group = QGroupBox("Active Scripts")
        scripts_layout = QVBoxLayout(scripts_group)

        self.active_scripts_list = QListWidget()
        self.active_scripts_list.setMaximumHeight(100)
        scripts_layout.addWidget(self.active_scripts_list)

        layout.addWidget(scripts_group)

        # Performance Group
        perf_group = QGroupBox("Performance")
        perf_layout = QVBoxLayout(perf_group)

        self.cpu_label = QLabel("CPU: 0%")
        self.cpu_progress = QProgressBar()
        self.cpu_progress.setRange(0, 100)
        perf_layout.addWidget(self.cpu_label)
        perf_layout.addWidget(self.cpu_progress)

        self.memory_label = QLabel("Memory: 0 MB")
        self.memory_progress = QProgressBar()
        self.memory_progress.setRange(0, 100)
        perf_layout.addWidget(self.memory_label)
        perf_layout.addWidget(self.memory_progress)

        layout.addWidget(perf_group)

        layout.addStretch()

    def update_voice_status(self, enabled: bool, connected: bool = True):
        """Update voice service status"""
        if not connected:
            self.voice_status.setText("🔊 Voice: Disconnected")
            self.voice_status.setStyleSheet("color: #dc3545;")
        elif enabled:
            self.voice_status.setText("🔊 Voice: Active")
            self.voice_status.setStyleSheet("color: #28a745;")
        else:
            self.voice_status.setText("🔊 Voice: Muted")
            self.voice_status.setStyleSheet("color: #ffc107;")

    def update_onepassword_status(self, connected: bool):
        """Update 1Password connection status"""
        if connected:
            self.onepassword_status.setText("🔐 1Password: Connected")
            self.onepassword_status.setStyleSheet("color: #28a745;")
        else:
            self.onepassword_status.setText("🔐 1Password: Disconnected")
            self.onepassword_status.setStyleSheet("color: #dc3545;")

    def update_reminder_status(self, active: bool):
        """Update reminder system status"""
        if active:
            self.reminder_status.setText("⏰ Reminders: Active")
            self.reminder_status.setStyleSheet("color: #28a745;")
        else:
            self.reminder_status.setText("⏰ Reminders: Disabled")
            self.reminder_status.setStyleSheet("color: #6c757d;")

    def add_active_script(self, script_name: str):
        """Add a script to the active scripts list"""
        self.active_scripts_list.addItem(f"▶️ {script_name}")

    def remove_active_script(self, script_name: str):
        """Remove a script from the active scripts list"""
        for i in range(self.active_scripts_list.count()):
            item = self.active_scripts_list.item(i)
            if item and script_name in item.text():
                self.active_scripts_list.takeItem(i)
                break

    def update_performance(self, cpu_percent: float, memory_mb: float, memory_percent: float):
        """Update performance indicators"""
        self.cpu_label.setText(f"CPU: {cpu_percent:.1f}%")
        self.cpu_progress.setValue(int(cpu_percent))

        self.memory_label.setText(f"Memory: {memory_mb:.0f} MB")
        self.memory_progress.setValue(int(memory_percent))


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.orchestrator = None
        self.script_cards = {}
        self.current_script = None

        self.setup_ui()
        self.setup_orchestrator()
        self.setup_system_tray()
        self.setup_timers()

        # Load and apply settings
        self.settings = QSettings("PythonOrchestrator", "MainWindow")
        self.restore_geometry()

    def setup_ui(self):
        """Set up the main UI"""
        self.setWindowTitle("Python Orchestrator")
        self.setGeometry(100, 100, 1400, 900)

        # Central widget with splitter
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # Main splitter
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Left panel: Script library
        self.setup_script_library(splitter)

        # Center panel: Terminal and controls
        self.setup_center_panel(splitter)

        # Right panel: Status
        self.setup_status_panel(splitter)

        # Set splitter proportions
        splitter.setSizes([400, 700, 300])

        # Setup menu bar and toolbar
        self.setup_menu_bar()
        self.setup_toolbar()
        self.setup_status_bar()

    def setup_script_library(self, splitter):
        """Set up the script library panel"""
        library_widget = QWidget()
        library_layout = QVBoxLayout(library_widget)

        # Library header
        header_label = QLabel("📚 Script Library")
        header_label.setFont(QFont("Arial", 14, QFont.Bold))
        library_layout.addWidget(header_label)

        # Search/filter controls
        filter_layout = QHBoxLayout()

        self.search_combo = QComboBox()
        self.search_combo.setEditable(True)
        self.search_combo.setPlaceholderText("Search scripts...")
        filter_layout.addWidget(self.search_combo)

        # View toggle button (cards vs tree)
        self.view_toggle = QPushButton()
        self.view_toggle.setIcon(qta.icon("fa5s.sitemap"))
        self.view_toggle.setToolTip("Toggle tree view")
        self.view_toggle.setCheckable(True)
        self.view_toggle.clicked.connect(self.toggle_view_mode)
        filter_layout.addWidget(self.view_toggle)

        refresh_btn = QPushButton()
        refresh_btn.setIcon(qta.icon("fa5s.sync"))
        refresh_btn.setToolTip("Refresh script library")
        refresh_btn.clicked.connect(self.refresh_scripts)
        filter_layout.addWidget(refresh_btn)

        library_layout.addLayout(filter_layout)

        # Container for both views
        self.view_container = QWidget()
        self.view_layout = QVBoxLayout(self.view_container)
        self.view_layout.setContentsMargins(0, 0, 0, 0)

        # Script cards scroll area
        self.cards_scroll_area = QScrollArea()
        self.cards_scroll_area.setWidgetResizable(True)
        self.cards_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.cards_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.script_container = QWidget()
        self.script_layout = QVBoxLayout(self.script_container)
        self.script_layout.setAlignment(Qt.AlignTop)

        self.cards_scroll_area.setWidget(self.script_container)

        # Tree view for hierarchical display
        self.tree_view = QTreeWidget()
        self.tree_view.setHeaderLabels(["Script", "Type", "Location", "Description"])
        self.tree_view.itemDoubleClicked.connect(self.on_tree_item_activated)
        self.tree_view.hide()  # Initially hidden

        # Add both to view container
        self.view_layout.addWidget(self.cards_scroll_area)
        self.view_layout.addWidget(self.tree_view)

        library_layout.addWidget(self.view_container)

        splitter.addWidget(library_widget)

    def setup_center_panel(self, splitter):
        """Set up the center panel with terminal and controls"""
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)

        # Control panel
        controls_group = QGroupBox("Controls")
        controls_layout = QHBoxLayout(controls_group)

        self.run_btn = QPushButton("Run Script")
        self.run_btn.setIcon(qta.icon("fa5s.play", color="green"))
        self.run_btn.clicked.connect(self.run_selected_script)
        self.run_btn.setEnabled(False)
        controls_layout.addWidget(self.run_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setIcon(qta.icon("fa5s.stop", color="red"))
        self.stop_btn.clicked.connect(self.stop_script)
        self.stop_btn.setEnabled(False)
        controls_layout.addWidget(self.stop_btn)

        controls_layout.addStretch()

        self.voice_toggle = QPushButton("🔊 Voice On")
        self.voice_toggle.setCheckable(True)
        self.voice_toggle.setChecked(True)
        self.voice_toggle.clicked.connect(self.toggle_voice)
        controls_layout.addWidget(self.voice_toggle)

        self.reminders_toggle = QPushButton("⏰ Reminders On")
        self.reminders_toggle.setCheckable(True)
        self.reminders_toggle.setChecked(True)
        self.reminders_toggle.clicked.connect(self.toggle_reminders)
        controls_layout.addWidget(self.reminders_toggle)

        center_layout.addWidget(controls_group)

        # Terminal output
        terminal_group = QGroupBox("Output")
        terminal_layout = QVBoxLayout(terminal_group)

        self.terminal = TerminalWidget()
        terminal_layout.addWidget(self.terminal)

        # Terminal controls
        terminal_controls = QHBoxLayout()

        clear_btn = QPushButton("Clear")
        clear_btn.setIcon(qta.icon("fa5s.eraser"))
        clear_btn.clicked.connect(self.terminal.clear_output)
        terminal_controls.addWidget(clear_btn)

        terminal_controls.addStretch()

        self.auto_scroll_toggle = QPushButton("Auto-scroll")
        self.auto_scroll_toggle.setCheckable(True)
        self.auto_scroll_toggle.setChecked(True)
        terminal_controls.addWidget(self.auto_scroll_toggle)

        terminal_layout.addLayout(terminal_controls)
        center_layout.addWidget(terminal_group)

        splitter.addWidget(center_widget)

    def setup_status_panel(self, splitter):
        """Set up the status panel"""
        self.status_panel = StatusPanel()
        splitter.addWidget(self.status_panel)

    def setup_menu_bar(self):
        """Set up the menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        refresh_action = QAction("&Refresh Scripts", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_scripts)
        file_menu.addAction(refresh_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = menubar.addMenu("&View")

        dark_theme_action = QAction("&Dark Theme", self)
        dark_theme_action.setCheckable(True)
        dark_theme_action.setChecked(True)
        view_menu.addAction(dark_theme_action)

        # Tools menu
        tools_menu = menubar.addMenu("&Tools")

        voice_settings_action = QAction("&Voice Settings", self)
        tools_menu.addAction(voice_settings_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        help_menu.addAction(about_action)

    def setup_toolbar(self):
        """Set up the toolbar"""
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        toolbar.addAction(qta.icon("fa5s.sync"), "Refresh", self.refresh_scripts)
        toolbar.addSeparator()
        toolbar.addAction(qta.icon("fa5s.play", color="green"), "Run", self.run_selected_script)
        toolbar.addAction(qta.icon("fa5s.stop", color="red"), "Stop", self.stop_script)
        toolbar.addSeparator()
        toolbar.addAction(qta.icon("fa5s.volume-up"), "Toggle Voice", self.toggle_voice)
        toolbar.addAction(qta.icon("fa5s.bell"), "Toggle Reminders", self.toggle_reminders)

    def setup_status_bar(self):
        """Set up the status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def setup_orchestrator(self):
        """Initialize the orchestrator backend"""
        from gui_orchestrator import GuiOrchestrator

        self.orchestrator = GuiOrchestrator(parent=self)

        # Connect orchestrator signals to GUI slots
        self.orchestrator.scripts_discovered.connect(self.on_scripts_discovered)
        self.orchestrator.script_output.connect(self.on_script_output)
        self.orchestrator.script_status_changed.connect(self.on_script_status_changed)
        self.orchestrator.voice_status_changed.connect(self.on_voice_status_changed)
        self.orchestrator.onepassword_status_changed.connect(self.on_onepassword_status_changed)

    def setup_system_tray(self):
        """Set up system tray integration"""
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon(self)

            # Set tray icon
            icon = qta.icon("fa5s.cogs")
            self.tray_icon.setIcon(icon)

            # Create tray menu
            tray_menu = QMenu()

            show_action = QAction("Show", self)
            show_action.triggered.connect(self.show)
            tray_menu.addAction(show_action)

            quit_action = QAction("Quit", self)
            quit_action.triggered.connect(QApplication.instance().quit)
            tray_menu.addAction(quit_action)

            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.show()

            # Handle tray activation
            self.tray_icon.activated.connect(self.tray_icon_activated)

    def setup_timers(self):
        """Set up update timers"""
        # Performance update timer
        self.perf_timer = QTimer()
        self.perf_timer.timeout.connect(self.update_performance)
        self.perf_timer.start(2000)  # Update every 2 seconds

    def refresh_scripts(self):
        """Refresh the script library"""
        self.status_bar.showMessage("Refreshing scripts...")

        # Clear existing cards
        for card in self.script_cards.values():
            card.setParent(None)
        self.script_cards.clear()

        # Use orchestrator to discover scripts
        if self.orchestrator:
            asyncio.create_task(self.orchestrator.discover_scripts())
        else:
            # Fallback to direct discovery if orchestrator not ready
            scripts_path = Path(__file__).parent / "scripts"
            if scripts_path.exists():
                scripts_data = []
                for script_file in scripts_path.glob("*.py"):
                    metadata = {
                        "name": script_file.stem,
                        "path": str(script_file),
                        "docstring": "Loading...",
                        "modified": datetime.fromtimestamp(script_file.stat().st_mtime),
                        "functions": [],
                    }
                    scripts_data.append(metadata)

                self.on_scripts_discovered(scripts_data)

    @Slot(str)
    def select_script(self, script_name: str):
        """Handle script selection"""
        # Clear previous selection
        for card in self.script_cards.values():
            card.set_selected(False)

        # Select new script
        if script_name in self.script_cards:
            self.script_cards[script_name].set_selected(True)
            self.current_script = script_name
            self.run_btn.setEnabled(True)
            self.status_bar.showMessage(f"Selected: {script_name}")

    def run_selected_script(self):
        """Run the selected script"""
        if not self.current_script or not self.orchestrator:
            return

        self.status_bar.showMessage(f"Running {self.current_script}...")
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        # Use orchestrator to run script
        self.orchestrator.run_script(self.current_script)

    def stop_script(self):
        """Stop the running script"""
        if not self.current_script or not self.orchestrator:
            return

        self.status_bar.showMessage(f"Stopping {self.current_script}...")

        # Use orchestrator to stop script
        self.orchestrator.stop_script(self.current_script)

    def toggle_voice(self):
        """Toggle voice feedback"""
        enabled = self.voice_toggle.isChecked()
        self.voice_toggle.setText("🔊 Voice On" if enabled else "🔊 Voice Off")

        # Update orchestrator
        if self.orchestrator:
            self.orchestrator.set_voice_enabled(enabled)

    def toggle_reminders(self):
        """Toggle reminder system"""
        enabled = self.reminders_toggle.isChecked()
        self.reminders_toggle.setText("⏰ Reminders On" if enabled else "⏰ Reminders Off")

        # Update orchestrator
        if self.orchestrator:
            self.orchestrator.set_reminders_enabled(enabled)

    def update_performance(self):
        """Update performance indicators"""
        try:
            import psutil

            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            memory_mb = memory.used / (1024 * 1024)
            memory_percent = memory.percent

            self.status_panel.update_performance(cpu_percent, memory_mb, memory_percent)
        except ImportError:
            pass

    def tray_icon_activated(self, reason):
        """Handle system tray icon activation"""
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.raise_()
                self.activateWindow()

    def restore_geometry(self):
        """Restore window geometry from settings"""
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

    def closeEvent(self, event):
        """Handle window close event"""
        if self.tray_icon and self.tray_icon.isVisible():
            # Minimize to tray instead of closing
            self.hide()
            event.ignore()
        else:
            # Save settings
            self.settings.setValue("geometry", self.saveGeometry())

            # Cleanup orchestrator
            if self.orchestrator:
                self.orchestrator.cleanup()

            event.accept()

    # Signal handlers for orchestrator integration
    @Slot(list)
    def on_scripts_discovered(self, scripts_data: list):
        """Handle scripts discovered by orchestrator"""
        # Clear existing cards and tree
        for card in self.script_cards.values():
            card.setParent(None)
        self.script_cards.clear()
        self.tree_view.clear()

        # Populate both views
        self.populate_cards_view(scripts_data)
        self.populate_tree_view(scripts_data)

        self.status_bar.showMessage(f"Found {len(scripts_data)} scripts", 3000)

    def populate_cards_view(self, scripts_data: list):
        """Populate the cards view with scripts"""
        for script_metadata in scripts_data:
            script_path = Path(script_metadata["path"])

            # Create and add card
            card = ScriptCard(script_path, script_metadata)
            card.script_selected.connect(self.select_script)
            self.script_cards[script_metadata["name"]] = card
            self.script_layout.addWidget(card)

    def populate_tree_view(self, scripts_data: list):
        """Populate the tree view with hierarchical script structure"""
        # Group scripts by location
        local_scripts = []
        symlinked_scripts = []

        for script_metadata in scripts_data:
            if script_metadata.get("is_symlink", False):
                symlinked_scripts.append(script_metadata)
            else:
                local_scripts.append(script_metadata)

        # Add local scripts section
        if local_scripts:
            local_root = QTreeWidgetItem(self.tree_view)
            local_root.setText(0, f"📦 Local Scripts ({len(local_scripts)})")
            local_root.setText(1, "Local")
            local_root.setText(2, str(Path(__file__).parent / "scripts"))
            local_root.setText(3, "Scripts in the orchestrator directory")
            local_root.setExpanded(True)

            for script in local_scripts:
                item = QTreeWidgetItem(local_root)
                item.setText(0, f"🐍 {script['name']}")
                item.setText(1, "Python")
                item.setText(2, script["path"])
                docstring = script.get("docstring", "No description")
                if docstring is None:
                    description = "No description"
                else:
                    description = (
                        str(docstring)[:50] + "..." if len(str(docstring)) > 50 else str(docstring)
                    )
                item.setText(3, description)
                item.setData(0, Qt.UserRole, script["name"])  # Store script name for selection

        # Add symlinked scripts section
        if symlinked_scripts:
            symlink_root = QTreeWidgetItem(self.tree_view)
            symlink_root.setText(0, f"🔗 External Scripts ({len(symlinked_scripts)})")
            symlink_root.setText(1, "External")
            symlink_root.setText(2, str(Path(__file__).parent / "symlinks"))
            symlink_root.setText(3, "Symlinked scripts from external locations")
            symlink_root.setExpanded(True)

            # Group by source directory
            source_dirs = {}
            for script in symlinked_scripts:
                target_path = script.get("target_path", "")
                if target_path:
                    source_dir = str(Path(target_path).parent)
                    if source_dir not in source_dirs:
                        source_dirs[source_dir] = []
                    source_dirs[source_dir].append(script)

            for source_dir, scripts in source_dirs.items():
                dir_item = QTreeWidgetItem(symlink_root)
                dir_item.setText(0, f"📁 {Path(source_dir).name}")
                dir_item.setText(1, "Directory")
                dir_item.setText(2, source_dir)
                dir_item.setText(3, f"{len(scripts)} script(s)")
                dir_item.setExpanded(True)

                for script in scripts:
                    item = QTreeWidgetItem(dir_item)
                    script_icon = "🐍" if script["path"].endswith(".py") else "📜"
                    item.setText(0, f"{script_icon} {script['name']}")
                    item.setText(1, "Shell" if script["path"].endswith(".sh") else "Python")
                    item.setText(2, script.get("target_path", script["path"]))
                    docstring = script.get("docstring", "No description")
                    if docstring is None:
                        description = "No description"
                    else:
                        description = (
                            str(docstring)[:50] + "..."
                            if len(str(docstring)) > 50
                            else str(docstring)
                        )
                    item.setText(3, description)
                    item.setData(0, Qt.UserRole, script["name"])  # Store script name for selection

        # Auto-resize columns
        for i in range(4):
            self.tree_view.resizeColumnToContents(i)

    def toggle_view_mode(self):
        """Toggle between cards and tree view"""
        if self.view_toggle.isChecked():
            # Switch to tree view
            self.cards_scroll_area.hide()
            self.tree_view.show()
            self.view_toggle.setToolTip("Switch to cards view")
            self.view_toggle.setIcon(qta.icon("fa5s.th-large"))
        else:
            # Switch to cards view
            self.tree_view.hide()
            self.cards_scroll_area.show()
            self.view_toggle.setToolTip("Switch to tree view")
            self.view_toggle.setIcon(qta.icon("fa5s.sitemap"))

    def on_tree_item_activated(self, item, column):
        """Handle tree item double-click"""
        script_name = item.data(0, Qt.UserRole)
        if script_name:
            self.select_script(script_name)

    @Slot(str, str)
    def on_script_output(self, output_text: str, output_type: str):
        """Handle script output from orchestrator"""
        self.terminal.append_output(output_text, output_type)

    @Slot(str, str)
    def on_script_status_changed(self, script_name: str, status: str):
        """Handle script status changes"""
        # Update card status
        if script_name in self.script_cards:
            card = self.script_cards[script_name]

            if status == "running":
                card.set_running(True)
                self.status_panel.add_active_script(script_name)
            elif status in ["completed", "failed", "error", "stopped"]:
                card.set_running(False)
                self.status_panel.remove_active_script(script_name)
                # Re-enable controls if this is the current script
                if script_name == self.current_script:
                    self.run_btn.setEnabled(True)
                    self.stop_btn.setEnabled(False)
            elif status == "waiting":
                card.update_status_indicator("waiting")

        # Update status bar
        if status == "running":
            self.status_bar.showMessage(f"{script_name} is running...")
        elif status == "completed":
            self.status_bar.showMessage(f"{script_name} completed successfully", 5000)
        elif status == "failed" or status == "error":
            self.status_bar.showMessage(f"{script_name} failed", 5000)
        elif status == "waiting":
            self.status_bar.showMessage(f"{script_name} is waiting for input", 5000)

    @Slot(bool, bool)
    def on_voice_status_changed(self, enabled: bool, connected: bool):
        """Handle voice status changes"""
        self.status_panel.update_voice_status(enabled, connected)

        # Update toggle button
        self.voice_toggle.setChecked(enabled)
        self.voice_toggle.setText("🔊 Voice On" if enabled else "🔊 Voice Off")

    @Slot(bool)
    def on_onepassword_status_changed(self, connected: bool):
        """Handle 1Password status changes"""
        self.status_panel.update_onepassword_status(connected)


def main():
    """Main entry point for the GUI application"""
    app = QApplication(sys.argv)

    # Set application properties
    app.setApplicationName("Python Orchestrator")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("Python Orchestrator")

    # Apply dark theme
    qdarktheme.setup_theme("dark", custom_colors={"primary": "#61DAFB"})

    # Create and show main window
    window = MainWindow()
    window.show()

    # Initial script refresh
    QTimer.singleShot(500, window.refresh_scripts)

    # Start event loop with asyncio integration
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    try:
        loop.run_forever()
    finally:
        loop.close()


if __name__ == "__main__":
    main()
