"""
AppleScript bridge for macOS automation.

Provides Python interface to Calendar, Reminders, Notes, and other macOS apps.
"""

import asyncio
import logging
import subprocess
from datetime import datetime, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class AppleScriptBridge:
    """
    Bridge to macOS automation via AppleScript.

    Provides access to:
    - Calendar (events)
    - Reminders (tasks)
    - Notes
    - Notifications
    - Other macOS apps
    """

    @staticmethod
    async def run_applescript(script: str) -> str:
        """
        Execute AppleScript and return output.

        Args:
            script: AppleScript code to execute

        Returns:
            Script output as string
        """
        try:
            result = await asyncio.create_subprocess_exec(
                "osascript",
                "-e",
                script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                error = stderr.decode()
                logger.error(f"AppleScript error: {error}")
                raise RuntimeError(f"AppleScript failed: {error}")

            return stdout.decode().strip()

        except Exception as e:
            logger.error(f"AppleScript execution error: {e}")
            raise

    # Calendar Methods

    async def get_today_events(self) -> List[Dict]:
        """
        Get today's calendar events.

        Returns:
            List of event dicts with 'title', 'start', 'end'
        """
        script = '''
        tell application "Calendar"
            set todayStart to (current date)
            set time of todayStart to 0
            set todayEnd to todayStart + (24 * hours)

            set eventList to {}
            repeat with cal in calendars
                repeat with evt in (events of cal whose start date ≥ todayStart and start date < todayEnd)
                    set end of eventList to {title:(summary of evt), startDate:(start date of evt as string), endDate:(end date of evt as string)}
                end repeat
            end repeat

            return eventList
        end tell
        '''

        try:
            await self.run_applescript(script)
            # Parse AppleScript output (simplified)
            # Real implementation would parse the returned data structure
            return [{"title": "Event parsing TODO", "start": "", "end": ""}]

        except Exception as e:
            logger.error(f"Failed to get calendar events: {e}")
            return []

    async def create_calendar_event(
        self,
        title: str,
        start_time: datetime,
        duration_minutes: int = 60,
        notes: str = ""
    ) -> bool:
        """
        Create calendar event.

        Args:
            title: Event title
            start_time: Start datetime
            duration_minutes: Event duration
            notes: Event notes (optional)

        Returns:
            True if successful
        """
        end_time = start_time + timedelta(minutes=duration_minutes)

        start_str = start_time.strftime("%m/%d/%Y %I:%M:%S %p")
        end_str = end_time.strftime("%m/%d/%Y %I:%M:%S %p")

        script = f'''
        tell application "Calendar"
            tell calendar "Fifth Symphony"
                make new event with properties {{summary:"{title}", start date:date "{start_str}", end date:date "{end_str}", description:"{notes}"}}
            end tell
        end tell
        '''

        try:
            await self.run_applescript(script)
            logger.info(f"Created calendar event: {title}")
            return True

        except Exception as e:
            logger.error(f"Failed to create event: {e}")
            return False

    # Reminders Methods

    async def get_reminders(self, list_name: str = "Fifth Symphony") -> List[Dict]:
        """
        Get reminders from list.

        Args:
            list_name: Reminders list name

        Returns:
            List of reminder dicts
        """
        script = f'''
        tell application "Reminders"
            set reminderList to list "{list_name}"
            set output to ""

            repeat with r in reminders of reminderList
                set output to output & (name of r) & "|" & (completed of r as string) & "\\n"
            end repeat

            return output
        end tell
        '''

        try:
            output = await self.run_applescript(script)
            reminders = []

            for line in output.split('\n'):
                if '|' in line:
                    name, completed = line.split('|')
                    reminders.append({
                        "name": name,
                        "completed": completed == "true"
                    })

            return reminders

        except Exception as e:
            logger.error(f"Failed to get reminders: {e}")
            return []

    async def create_reminder(
        self,
        title: str,
        list_name: str = "Fifth Symphony",
        due_date: Optional[datetime] = None,
        notes: str = ""
    ) -> bool:
        """
        Create reminder.

        Args:
            title: Reminder title
            list_name: List to add to
            due_date: Due date (optional)
            notes: Reminder notes

        Returns:
            True if successful
        """
        script_parts = [
            'tell application "Reminders"',
            f'    tell list "{list_name}"',
            f'        set newReminder to make new reminder with properties {{name:"{title}"}}'
        ]

        if due_date:
            due_str = due_date.strftime("%m/%d/%Y %I:%M:%S %p")
            script_parts.append(f'        set due date of newReminder to date "{due_str}"')

        if notes:
            script_parts.append(f'        set body of newReminder to "{notes}"')

        script_parts.extend([
            '    end tell',
            'end tell'
        ])

        script = '\n'.join(script_parts)

        try:
            await self.run_applescript(script)
            logger.info(f"Created reminder: {title}")
            return True

        except Exception as e:
            logger.error(f"Failed to create reminder: {e}")
            return False

    # Notifications

    async def send_notification(
        self,
        title: str,
        message: str,
        subtitle: str = ""
    ):
        """
        Send macOS notification.

        Args:
            title: Notification title
            message: Notification message
            subtitle: Subtitle (optional)
        """
        script = f'''
        display notification "{message}" with title "{title}" subtitle "{subtitle}"
        '''

        try:
            await self.run_applescript(script)
            logger.info(f"Sent notification: {title}")

        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

    # Notes

    async def create_note(self, title: str, body: str) -> bool:
        """
        Create note in Notes app.

        Args:
            title: Note title
            body: Note content

        Returns:
            True if successful
        """
        script = f'''
        tell application "Notes"
            make new note with properties {{name:"{title}", body:"{body}"}}
        end tell
        '''

        try:
            await self.run_applescript(script)
            logger.info(f"Created note: {title}")
            return True

        except Exception as e:
            logger.error(f"Failed to create note: {e}")
            return False

    # Utility Methods

    async def speak_text(self, text: str, voice: str = "Samantha"):
        """
        Use macOS text-to-speech (alternative to ElevenLabs).

        Args:
            text: Text to speak
            voice: macOS voice name
        """
        script = f'''
        say "{text}" using "{voice}"
        '''

        try:
            await self.run_applescript(script)

        except Exception as e:
            logger.error(f"Failed to speak text: {e}")

    async def get_battery_level(self) -> int:
        """
        Get current battery level.

        Returns:
            Battery percentage (0-100)
        """
        script = '''
        do shell script "pmset -g batt | grep -Eo '\\d+%' | cut -d% -f1"
        '''

        try:
            output = await self.run_applescript(script)
            return int(output)

        except Exception as e:
            logger.error(f"Failed to get battery level: {e}")
            return 0


# Example usage
async def main():
    """Test AppleScript bridge."""
    bridge = AppleScriptBridge()

    # Send notification
    await bridge.send_notification(
        "Fifth Symphony",
        "AppleScript bridge is working!",
        "System Integration"
    )

    # Get reminders
    reminders = await bridge.get_reminders()
    print(f"Reminders: {reminders}")

    # Get battery
    battery = await bridge.get_battery_level()
    print(f"Battery: {battery}%")


if __name__ == "__main__":
    asyncio.run(main())
