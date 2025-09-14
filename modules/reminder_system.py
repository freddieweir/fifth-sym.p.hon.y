"""
Reminder System Module
Provides proactive reminders and attention-getting alerts
"""

import asyncio
import logging
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ReminderLevel:
    after_seconds: int
    urgency: str
    message_variations: list[str]
    voice_overrides: dict[str, Any]


class ReminderSystem:
    def __init__(self, voice_handler, config: dict[str, Any]):
        self.voice_handler = voice_handler
        self.config = config
        self.enabled = config.get("enabled", True)
        self.base_interval = config.get("interval_seconds", 120)

        # Parse escalation levels
        self.escalation_levels = self._parse_escalation_levels(config.get("escalation_levels", []))

        # Track active reminders
        self.active_reminders: dict[str, asyncio.Task] = {}
        self.script_start_times: dict[str, datetime] = {}
        self.last_reminder_times: dict[str, datetime] = {}

        # Load reminder messages
        self.reminder_messages = self._load_reminder_messages()

    def _parse_escalation_levels(self, levels_config: list[dict]) -> list[ReminderLevel]:
        """Parse escalation levels from config"""
        levels = []

        default_levels = [
            {
                "after_seconds": 120,
                "urgency": "gentle",
                "message_variations": [
                    "Hey there, {script} is still running. Just checking in!",
                    "Quick update: {script} is still working away.",
                    "{script} is still processing. Everything's going smoothly.",
                ],
                "voice_overrides": {"style": 0.2, "stability": 0.7},
            },
            {
                "after_seconds": 300,
                "urgency": "moderate",
                "message_variations": [
                    "Heads up! {script} has been running for {duration}.",
                    "Attention: {script} is still active. Might want to check on it.",
                    "Just so you know, {script} is taking a while. {duration} so far.",
                ],
                "voice_overrides": {"style": 0.5, "stability": 0.5, "similarity_boost": 0.8},
            },
            {
                "after_seconds": 600,
                "urgency": "urgent",
                "message_variations": [
                    "Important! {script} has been running for {duration}. Please check on it!",
                    "Alert! {script} needs your attention. It's been {duration}.",
                    "Warning! {script} is still running after {duration}. Action may be needed!",
                ],
                "voice_overrides": {"style": 0.8, "stability": 0.3, "similarity_boost": 0.9},
            },
        ]

        # Use provided config or defaults
        config_to_use = levels_config if levels_config else default_levels

        for level_config in config_to_use:
            level = ReminderLevel(
                after_seconds=level_config.get("after_seconds", 120),
                urgency=level_config.get("urgency", "gentle"),
                message_variations=level_config.get("message_variations", []),
                voice_overrides=level_config.get("voice_overrides", {}),
            )
            levels.append(level)

        # Sort by time
        levels.sort(key=lambda x: x.after_seconds)
        return levels

    def _load_reminder_messages(self) -> dict[str, list[str]]:
        """Load reminder message variations"""
        return {
            "gentle": [
                "Just a gentle reminder: {script} is still running.",
                "Quick check-in: {script} is still active.",
                "FYI, {script} is still going.",
                "Friendly update: {script} continues to run.",
                "Hey, {script} is still processing.",
            ],
            "moderate": [
                "Important: {script} has been running for a while.",
                "Please note: {script} is taking longer than usual.",
                "Attention needed: {script} is still active.",
                "Check this out: {script} has been running for {duration}.",
                "Time check: {script} started {duration} ago.",
            ],
            "urgent": [
                "Urgent! {script} requires your attention!",
                "Action needed! {script} has been running for {duration}!",
                "Critical: Please check on {script} immediately!",
                "Alert! {script} may be stuck or waiting for input!",
                "Warning! {script} has exceeded normal runtime!",
            ],
            "stuck": [
                "{script} appears to be stuck. It might need your help.",
                "{script} hasn't produced output recently. Check if it needs input.",
                "Looks like {script} might be waiting for something.",
                "{script} seems frozen. You might want to investigate.",
                "No activity from {script}. It could be waiting for you.",
            ],
            "long_running": [
                "Marathon alert! {script} has been running for {duration}.",
                "Endurance test: {script} is still going after {duration}.",
                "Long runner: {script} started {duration} ago.",
                "Still here: {script} continues after {duration}.",
                "Persistence award goes to {script}: {duration} and counting.",
            ],
        }

    async def monitor_script(self, script_name: str):
        """Monitor a script and send reminders"""
        if not self.enabled:
            return

        logger.info(f"Starting reminder monitoring for {script_name}")

        # Record start time
        self.script_start_times[script_name] = datetime.now()

        try:
            # Stop any existing reminder for this script
            await self.stop_monitoring(script_name)

            # Create new monitoring task
            task = asyncio.create_task(self._reminder_loop(script_name))
            self.active_reminders[script_name] = task

            await task

        except asyncio.CancelledError:
            logger.info(f"Reminder monitoring cancelled for {script_name}")
        except Exception as e:
            logger.error(f"Error in reminder monitoring for {script_name}: {e}")
        finally:
            # Clean up
            if script_name in self.active_reminders:
                del self.active_reminders[script_name]
            if script_name in self.script_start_times:
                del self.script_start_times[script_name]
            if script_name in self.last_reminder_times:
                del self.last_reminder_times[script_name]

    async def _reminder_loop(self, script_name: str):
        """Main reminder loop for a script"""
        start_time = self.script_start_times[script_name]

        while True:
            # Calculate elapsed time
            elapsed = datetime.now() - start_time
            elapsed_seconds = elapsed.total_seconds()

            # Find appropriate escalation level
            appropriate_level = None
            for i, level in enumerate(self.escalation_levels):
                if elapsed_seconds >= level.after_seconds:
                    appropriate_level = level

            if appropriate_level:
                # Check if we should send a reminder
                should_remind = False

                if script_name not in self.last_reminder_times:
                    should_remind = True
                else:
                    time_since_last = datetime.now() - self.last_reminder_times[script_name]
                    if time_since_last.total_seconds() >= self.base_interval:
                        should_remind = True

                if should_remind:
                    await self._send_reminder(script_name, appropriate_level, elapsed)
                    self.last_reminder_times[script_name] = datetime.now()

            # Wait before next check
            await asyncio.sleep(30)  # Check every 30 seconds

    async def _send_reminder(self, script_name: str, level: ReminderLevel, elapsed: timedelta):
        """Send a reminder message"""
        # Format duration
        duration = self._format_duration(elapsed)

        # Select message
        message = self._select_reminder_message(script_name, level, duration)

        # Send via voice handler with appropriate priority
        priority = (
            "normal"
            if level.urgency == "gentle"
            else "high"
            if level.urgency == "moderate"
            else "critical"
        )

        logger.info(f"Sending {level.urgency} reminder for {script_name}")

        await self.voice_handler.speak(message, priority=priority, **level.voice_overrides)

        # Add visual notification if urgent
        if level.urgency == "urgent":
            await self._trigger_visual_alert(script_name, message)

    def _select_reminder_message(
        self, script_name: str, level: ReminderLevel, duration: str
    ) -> str:
        """Select an appropriate reminder message"""
        # Use level's specific messages if available
        if level.message_variations:
            messages = level.message_variations
        else:
            # Fall back to category messages
            messages = self.reminder_messages.get(level.urgency, [])

        if not messages:
            # Ultimate fallback
            return f"{script_name} is still running after {duration}"

        # Select random message for variety
        message_template = random.choice(messages)

        # Format the message
        return message_template.format(script=script_name, duration=duration)

    def _format_duration(self, duration: timedelta) -> str:
        """Format duration in human-readable form"""
        total_seconds = int(duration.total_seconds())

        if total_seconds < 60:
            return f"{total_seconds} seconds"
        if total_seconds < 3600:
            minutes = total_seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''}"
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        if minutes > 0:
            return f"{hours} hour{'s' if hours != 1 else ''} and {minutes} minute{'s' if minutes != 1 else ''}"
        return f"{hours} hour{'s' if hours != 1 else ''}"

    async def _trigger_visual_alert(self, script_name: str, message: str):
        """Trigger a visual alert (platform-specific)"""
        try:
            import platform

            system = platform.system()

            if system == "Darwin":  # macOS
                # Use osascript for notification
                import subprocess

                subprocess.run(
                    [
                        "osascript",
                        "-e",
                        f'display notification "{message}" with title "Python Orchestrator" sound name "Glass"',
                    ]
                )
            elif system == "Linux":
                # Use notify-send if available
                import subprocess

                subprocess.run(
                    ["notify-send", "Python Orchestrator", message, "--urgency=critical"]
                )
            elif system == "Windows":
                # Use Windows toast notification
                try:
                    from win10toast import ToastNotifier

                    toaster = ToastNotifier()
                    toaster.show_toast("Python Orchestrator", message, duration=10, threaded=True)
                except ImportError:
                    pass

        except Exception as e:
            logger.debug(f"Could not show visual alert: {e}")

    async def stop_monitoring(self, script_name: str):
        """Stop monitoring a specific script"""
        if script_name in self.active_reminders:
            task = self.active_reminders[script_name]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.active_reminders[script_name]
            logger.info(f"Stopped monitoring {script_name}")

    async def stop_all_monitoring(self):
        """Stop all active monitoring"""
        tasks = list(self.active_reminders.keys())
        for script_name in tasks:
            await self.stop_monitoring(script_name)

    def get_monitoring_status(self) -> dict[str, dict[str, Any]]:
        """Get status of all monitored scripts"""
        status = {}

        for script_name in self.active_reminders:
            if script_name in self.script_start_times:
                elapsed = datetime.now() - self.script_start_times[script_name]
                last_reminder = None
                if script_name in self.last_reminder_times:
                    last_reminder = datetime.now() - self.last_reminder_times[script_name]

                status[script_name] = {
                    "running_for": self._format_duration(elapsed),
                    "last_reminder": self._format_duration(last_reminder)
                    if last_reminder
                    else "Never",
                    "start_time": self.script_start_times[script_name].isoformat(),
                }

        return status

    async def send_custom_reminder(self, script_name: str, message: str, urgency: str = "moderate"):
        """Send a custom reminder message"""
        priority = (
            "normal" if urgency == "gentle" else "high" if urgency == "moderate" else "critical"
        )

        await self.voice_handler.speak(message, priority=priority)

        if urgency == "urgent":
            await self._trigger_visual_alert(script_name, message)

    def set_enabled(self, enabled: bool):
        """Enable or disable the reminder system"""
        self.enabled = enabled
        if not enabled:
            # Cancel all active monitoring
            asyncio.create_task(self.stop_all_monitoring())
