"""
Visual Novel Widget

Static image display with state-based swapping for Attention-friendly visual feedback.
Features LED status indicators and emotion-based image selection.

States:
- Idle: Default resting state
- Talking: Voice output active
- Listening: Voice input active
- Processing: AI thinking
- Error: Error state

Future: Emotion-based dynamic selection (happy, sad, surprised, etc.)
"""

import logging
from enum import Enum
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class AvatarState(Enum):
    """Avatar display states."""

    IDLE = "idle"
    TALKING = "talking"
    LISTENING = "listening"
    PROCESSING = "processing"
    ERROR = "error"


class LEDColor(Enum):
    """LED indicator colors (matches HUD)."""

    BLUE = "#0066FF"  # Voice speaking
    GREEN = "#00FF66"  # Microphone recording
    YELLOW = "#FFCC00"  # AI processing
    RED = "#FF3333"  # Error state
    PURPLE = "#9933FF"  # Special state
    OFF = "#333333"  # LED off


class LEDIndicator(QWidget):
    """
    LED status indicator widget.

    Displays circular LED with color and optional pulsing animation.
    """

    def __init__(self, size: int = 20, parent=None):
        super().__init__(parent)
        self.size = size
        self.color = LEDColor.OFF
        self.pulsing = False
        self.pulse_opacity = 1.0
        self.pulse_direction = -1  # -1 = dimming, 1 = brightening

        self.setFixedSize(size, size)

        # Pulse timer
        self.pulse_timer = QTimer(self)
        self.pulse_timer.timeout.connect(self._update_pulse)
        self.pulse_timer.setInterval(50)  # 20 FPS

    def set_color(self, color: LEDColor, pulsing: bool = False):
        """
        Set LED color and pulsing state.

        Args:
            color: LED color
            pulsing: Whether LED should pulse
        """
        self.color = color
        self.pulsing = pulsing

        if pulsing:
            self.pulse_timer.start()
        else:
            self.pulse_timer.stop()
            self.pulse_opacity = 1.0

        self.update()

    def _update_pulse(self):
        """Update pulse animation."""
        # Pulse between 0.3 and 1.0 opacity
        self.pulse_opacity += 0.05 * self.pulse_direction

        if self.pulse_opacity <= 0.3:
            self.pulse_direction = 1
        elif self.pulse_opacity >= 1.0:
            self.pulse_direction = -1

        self.update()

    def paintEvent(self, event):
        """Paint LED indicator."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw outer circle (border)
        pen = QPen(QColor("#666666"))
        pen.setWidth(2)
        painter.setPen(pen)

        color = QColor(self.color.value)
        color.setAlphaF(self.pulse_opacity if self.pulsing else 1.0)
        painter.setBrush(color)

        # Draw circle
        painter.drawEllipse(2, 2, self.size - 4, self.size - 4)


class VisualNovelWidget(QWidget):
    """
    Visual Novel display widget.

    Features:
    - Static image display with state-based swapping
    - LED status indicators
    - Emotion-based image selection (future)
    - Always-on-top window option
    - Resizable with aspect ratio preservation
    """

    # Signals
    state_changed = Signal(AvatarState)
    led_changed = Signal(LEDColor)

    def __init__(
        self, assets_path: Path | None = None, always_on_top: bool = False, parent=None
    ):
        super().__init__(parent)

        # Configuration
        self.assets_path = assets_path or Path(__file__).parent.parent / "assets" / "visualization"
        self.always_on_top = always_on_top

        # State
        self.current_state = AvatarState.IDLE
        self.current_emotion = "neutral"  # Future: emotion system
        self.current_led = LEDColor.OFF

        # Image cache
        self.images: dict[str, QPixmap] = {}

        # Setup UI
        self._setup_ui()
        self._load_images()
        self._update_display()

        # Window flags
        if always_on_top:
            self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)

    def _setup_ui(self):
        """Setup user interface."""
        self.setWindowTitle("Fifth Symphony Avatar")
        self.setMinimumSize(400, 500)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # LED indicator bar
        led_bar = self._create_led_bar()
        layout.addWidget(led_bar)

        # Image display
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setScaledContents(False)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.image_label)

        # Status bar
        status_bar = self._create_status_bar()
        layout.addWidget(status_bar)

        # Style
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
        """)

    def _create_led_bar(self) -> QWidget:
        """Create LED indicator bar."""
        led_bar = QFrame()
        led_bar.setFrameShape(QFrame.StyledPanel)
        led_bar.setStyleSheet("background-color: #2d2d2d; padding: 5px;")

        layout = QHBoxLayout(led_bar)

        # Title
        title = QLabel("Fifth Symphony")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        layout.addStretch()

        # LED indicators (all 5 types)
        self.leds = {}

        led_labels = {
            "voice": ("🎤", LEDColor.BLUE),
            "mic": ("🎙️", LEDColor.GREEN),
            "processing": ("🧠", LEDColor.YELLOW),
            "error": ("⚠️", LEDColor.RED),
            "special": ("⭐", LEDColor.PURPLE),
        }

        for name, (emoji, color) in led_labels.items():
            # Emoji label
            emoji_label = QLabel(emoji)
            layout.addWidget(emoji_label)

            # LED indicator
            led = LEDIndicator(size=16)
            led.set_color(LEDColor.OFF)
            self.leds[name] = led
            layout.addWidget(led)

        return led_bar

    def _create_status_bar(self) -> QWidget:
        """Create status text bar."""
        status_bar = QFrame()
        status_bar.setFrameShape(QFrame.StyledPanel)
        status_bar.setStyleSheet("background-color: #2d2d2d; padding: 5px;")

        layout = QHBoxLayout(status_bar)

        # Status text
        self.status_label = QLabel("Idle")
        self.status_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(self.status_label)

        layout.addStretch()

        # Close button (if frameless)
        if self.always_on_top:
            close_btn = QPushButton("×")
            close_btn.setFixedSize(30, 30)
            close_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ff4444;
                    color: white;
                    border: none;
                    font-size: 20px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #ff6666;
                }
            """)
            close_btn.clicked.connect(self.close)
            layout.addWidget(close_btn)

        return status_bar

    def _load_images(self):
        """Load avatar images from assets directory."""
        # Default image paths
        image_files = {
            "idle": "idle.png",
            "talking": "talking.png",
            "listening": "listening.png",
            "processing": "processing.png",
            "error": "error.png",
        }

        for state, filename in image_files.items():
            image_path = self.assets_path / filename

            if image_path.exists():
                pixmap = QPixmap(str(image_path))
                self.images[state] = pixmap
                logger.info(f"Loaded image: {state} from {image_path}")
            else:
                # Create placeholder if image doesn't exist
                pixmap = self._create_placeholder(state)
                self.images[state] = pixmap
                logger.warning(f"Image not found: {image_path}, using placeholder")

    def _create_placeholder(self, state: str) -> QPixmap:
        """
        Create placeholder image for missing assets.

        Args:
            state: Avatar state name

        Returns:
            Placeholder QPixmap
        """
        pixmap = QPixmap(400, 500)
        pixmap.fill(QColor("#3d3d3d"))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw text
        painter.setPen(QColor("#ffffff"))
        painter.drawText(
            pixmap.rect(),
            Qt.AlignCenter,
            f"{state.upper()}\n\nPlace image at:\nassets/visualization/{state}.png",
        )

        painter.end()
        return pixmap

    def set_state(self, state: AvatarState):
        """
        Set avatar state and update display.

        Args:
            state: New avatar state
        """
        if self.current_state != state:
            self.current_state = state
            self._update_display()
            self.state_changed.emit(state)

            logger.info(f"Avatar state changed: {state.value}")

    def _update_display(self):
        """Update image display based on current state."""
        state_key = self.current_state.value

        if state_key in self.images:
            pixmap = self.images[state_key]

            # Scale to fit while preserving aspect ratio
            scaled_pixmap = pixmap.scaled(
                self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )

            self.image_label.setPixmap(scaled_pixmap)

        # Update status text
        status_texts = {
            AvatarState.IDLE: "Idle - Ready",
            AvatarState.TALKING: "Speaking...",
            AvatarState.LISTENING: "Listening...",
            AvatarState.PROCESSING: "Thinking...",
            AvatarState.ERROR: "Error occurred",
        }

        self.status_label.setText(status_texts.get(self.current_state, "Unknown"))

    def set_led(self, led_name: str, active: bool, pulsing: bool = False):
        """
        Set LED indicator state.

        Args:
            led_name: LED name (voice, mic, processing, error, special)
            active: True to turn on, False to turn off
            pulsing: Whether LED should pulse
        """
        if led_name in self.leds:
            led = self.leds[led_name]

            if active:
                # Determine color
                colors = {
                    "voice": LEDColor.BLUE,
                    "mic": LEDColor.GREEN,
                    "processing": LEDColor.YELLOW,
                    "error": LEDColor.RED,
                    "special": LEDColor.PURPLE,
                }
                color = colors.get(led_name, LEDColor.OFF)
                led.set_color(color, pulsing=pulsing)
            else:
                led.set_color(LEDColor.OFF, pulsing=False)

    def set_voice_speaking(self, speaking: bool):
        """Convenience method for voice speaking state."""
        self.set_led("voice", speaking, pulsing=speaking)
        if speaking:
            self.set_state(AvatarState.TALKING)
        else:
            self.set_state(AvatarState.IDLE)

    def set_mic_recording(self, recording: bool):
        """Convenience method for mic recording state."""
        self.set_led("mic", recording, pulsing=recording)
        if recording:
            self.set_state(AvatarState.LISTENING)
        else:
            self.set_state(AvatarState.IDLE)

    def set_processing(self, processing: bool):
        """Convenience method for AI processing state."""
        self.set_led("processing", processing, pulsing=processing)
        if processing:
            self.set_state(AvatarState.PROCESSING)
        else:
            self.set_state(AvatarState.IDLE)

    def set_error(self, error: bool):
        """Convenience method for error state."""
        self.set_led("error", error, pulsing=error)
        if error:
            self.set_state(AvatarState.ERROR)
        else:
            self.set_state(AvatarState.IDLE)

    def resizeEvent(self, event):
        """Handle window resize."""
        super().resizeEvent(event)
        self._update_display()


# Example standalone application
def main():
    """Run visual novel widget as standalone app."""
    import sys

    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # Create widget
    widget = VisualNovelWidget(always_on_top=True)
    widget.resize(400, 500)
    widget.show()

    # Demo state changes
    def demo_states():
        """Demonstrate state transitions."""

        states = [
            (AvatarState.IDLE, "Idle", False, False, False),
            (AvatarState.TALKING, "Talking", True, False, False),
            (AvatarState.LISTENING, "Listening", False, True, False),
            (AvatarState.PROCESSING, "Processing", False, False, True),
            (AvatarState.ERROR, "Error", False, False, False),
        ]

        for state, name, voice, mic, processing in states:
            widget.set_state(state)
            widget.set_voice_speaking(voice)
            widget.set_mic_recording(mic)
            widget.set_processing(processing)

            QTimer.singleShot(3000, lambda: None)  # Wait 3 seconds

    # Start demo
    QTimer.singleShot(1000, demo_states)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
