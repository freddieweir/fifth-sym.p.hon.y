"""
Video Game-Style HUD Overlay

Displays system status in gaming-inspired heads-up display.
ADHD-optimized with visual indicators and real-time stats.
"""

import asyncio
from datetime import datetime
from typing import Optional, Dict

from textual.widget import Widget
from textual.widgets import Static
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.console import Group


class SystemHUD(Widget):
    """
    Video game-style HUD overlay.

    Displays:
    - Current LLM model and context
    - Voice configuration
    - System status
    - Resource usage
    - Active tasks
    """

    def __init__(self):
        super().__init__()

        # System state
        self.model_name = "Not loaded"
        self.model_context = "0/0"
        self.voice_name = "None"
        self.voice_status = "Idle"
        self.system_status = "Starting..."
        self.cpu_usage = 0
        self.memory_usage = 0
        self.active_tasks = []
        self.ollama_status = "Disconnected"
        self.docker_containers = 0
        self.battery_level = 100
        self.is_charging = False

        # LED status indicators (macOS/iOS-style)
        self.led_status = {
            "voice_active": False,      # 🔵 Blue - Voice speaking
            "mic_active": False,         # 🟢 Green - Microphone recording
            "processing": False,         # 🟡 Yellow - AI processing
            "error": False,             # 🔴 Red - Error state
            "screen_share": False,      # 🟣 Purple - Screen sharing / special state
        }

    def update_model(self, name: str, context_used: int, context_max: int):
        """Update LLM model information."""
        self.model_name = name
        self.model_context = f"{context_used}/{context_max}"
        self.refresh()

    def update_voice(self, name: str, status: str):
        """Update voice status."""
        self.voice_name = name
        self.voice_status = status
        self.refresh()

    def update_system_status(self, status: str):
        """Update system status."""
        self.system_status = status
        self.refresh()

    def update_resources(self, cpu: float, memory: float):
        """Update resource usage."""
        self.cpu_usage = cpu
        self.memory_usage = memory
        self.refresh()

    def update_battery(self, level: int, charging: bool):
        """Update battery status."""
        self.battery_level = level
        self.is_charging = charging
        self.refresh()

    def add_active_task(self, task: str):
        """Add active task to HUD."""
        self.active_tasks.append(task)
        if len(self.active_tasks) > 5:
            self.active_tasks.pop(0)
        self.refresh()

    def update_led_status(self, led_name: str, active: bool):
        """
        Update LED status indicator.

        Args:
            led_name: LED indicator name (voice_active, mic_active, etc.)
            active: True if LED should be on, False if off
        """
        if led_name in self.led_status:
            self.led_status[led_name] = active
            self.refresh()

    def set_voice_speaking(self, speaking: bool):
        """Set voice speaking LED (blue)."""
        self.update_led_status("voice_active", speaking)

    def set_mic_recording(self, recording: bool):
        """Set microphone recording LED (green)."""
        self.update_led_status("mic_active", recording)

    def set_processing(self, processing: bool):
        """Set AI processing LED (yellow)."""
        self.update_led_status("processing", processing)

    def set_error(self, error: bool):
        """Set error LED (red)."""
        self.update_led_status("error", error)

    def set_special_state(self, active: bool):
        """Set special state LED (purple) - screen sharing, etc."""
        self.update_led_status("screen_share", active)

    def render(self):
        """Render HUD overlay."""
        # Build HUD components

        # Model Status
        model_bar = self._create_progress_bar(
            "MODEL CONTEXT",
            self.model_context,
            self._parse_context_percentage()
        )

        # Voice Status
        voice_indicator = self._create_status_indicator("VOICE", self.voice_status)

        # System Status
        system_indicator = self._create_status_indicator("SYSTEM", self.system_status)

        # Resources
        cpu_bar = self._create_progress_bar("CPU", f"{self.cpu_usage}%", self.cpu_usage)
        mem_bar = self._create_progress_bar("MEMORY", f"{self.memory_usage}%", self.memory_usage)

        # Battery
        battery_icon = "🔌" if self.is_charging else "🔋"
        battery_bar = self._create_progress_bar(
            f"BATTERY {battery_icon}",
            f"{self.battery_level}%",
            self.battery_level
        )

        # Active Tasks
        tasks_display = self._create_tasks_list()

        # Combine into HUD layout
        hud_table = Table.grid(padding=(0, 1))
        hud_table.add_column(justify="left", width=30)
        hud_table.add_column(justify="right", width=30)

        # Row 1: Model + Voice
        hud_table.add_row(
            Text(f"🧠 {self.model_name}", style="bold cyan"),
            Text(f"🎤 {self.voice_name}", style="bold magenta")
        )

        # Row 2: Context + Status
        hud_table.add_row(model_bar, voice_indicator)

        # Row 3: Resources
        hud_table.add_row(cpu_bar, mem_bar)

        # Row 4: Battery + System
        hud_table.add_row(battery_bar, system_indicator)

        # Row 5: Active Tasks
        if self.active_tasks:
            hud_table.add_row(tasks_display, "")

        # LED Status Indicator (macOS/iOS-style)
        led_display = self._create_led_display()

        # Wrap in panel with gaming aesthetic
        return Panel(
            hud_table,
            title=f"[bold green]⚡ FIFTH SYMPHONY HUD[/bold green]  {led_display}  {datetime.now().strftime('%H:%M:%S')}",
            border_style="green",
            padding=(0, 1)
        )

    def _parse_context_percentage(self) -> float:
        """Parse context usage percentage."""
        if "/" not in self.model_context:
            return 0

        try:
            used, total = self.model_context.split("/")
            return (int(used) / int(total)) * 100 if int(total) > 0 else 0
        except:
            return 0

    def _create_progress_bar(self, label: str, value: str, percentage: float) -> Text:
        """Create progress bar visualization."""
        # Determine color based on percentage
        if percentage < 50:
            color = "green"
        elif percentage < 80:
            color = "yellow"
        else:
            color = "red"

        # Create bar
        bar_width = 20
        filled = int((percentage / 100) * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)

        return Text(f"{label}: {bar} {value}", style=color)

    def _create_status_indicator(self, label: str, status: str) -> Text:
        """Create status indicator with emoji."""
        status_emoji = {
            "Idle": "⚪",
            "Active": "🟢",
            "Processing": "🟡",
            "Error": "🔴",
            "Starting": "🔵"
        }

        emoji = status_emoji.get(status, "⚪")
        return Text(f"{label}: {emoji} {status}")

    def _create_tasks_list(self) -> Text:
        """Create active tasks list."""
        if not self.active_tasks:
            return Text("No active tasks", style="dim")

        tasks_text = Text("🎯 ACTIVE TASKS:\n", style="bold yellow")
        for i, task in enumerate(self.active_tasks[-3:], 1):
            tasks_text.append(f"  {i}. {task}\n", style="white")

        return tasks_text

    def _create_led_display(self) -> str:
        """
        Create macOS/iOS-style LED status indicator display.

        Returns:
            String with colored LED indicators
        """
        leds = []

        # Voice speaking (blue)
        if self.led_status["voice_active"]:
            leds.append("🔵")

        # Microphone recording (green)
        if self.led_status["mic_active"]:
            leds.append("🟢")

        # AI processing (yellow)
        if self.led_status["processing"]:
            leds.append("🟡")

        # Error state (red)
        if self.led_status["error"]:
            leds.append("🔴")

        # Special state (purple)
        if self.led_status["screen_share"]:
            leds.append("🟣")

        # Return LED string or empty if no active LEDs
        return " ".join(leds) if leds else ""


class CompactHUD(Widget):
    """
    Compact single-line HUD.

    For minimal screen space usage.
    """

    def __init__(self):
        super().__init__()
        self.model = "N/A"
        self.status = "Idle"
        self.voice = "Off"

    def render(self):
        """Render compact HUD."""
        return Text(
            f"🎮 Model: {self.model} | Status: {self.status} | Voice: {self.voice}",
            style="bold green on black"
        )


# Example usage
async def test_hud():
    """Test HUD rendering."""
    from textual.app import App

    class HUDTestApp(App):
        def compose(self):
            hud = SystemHUD()

            # Simulate updates
            hud.update_model("llama3.2:3b-instruct", 1024, 8192)
            hud.update_voice("Albedo", "Active")
            hud.update_system_status("Processing")
            hud.update_resources(45.2, 67.8)
            hud.update_battery(85, True)
            hud.add_active_task("Analyzing repository")
            hud.add_active_task("Generating summary")

            yield hud

    app = HUDTestApp()
    app.run()


if __name__ == "__main__":
    asyncio.run(test_hud())
