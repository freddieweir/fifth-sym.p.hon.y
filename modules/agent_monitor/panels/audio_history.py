"""Audio History panel for playing back previous audio summaries."""

import os
from pathlib import Path
from datetime import datetime
from textual.widgets import Static, DataTable
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual import events
import subprocess

# Dynamic path resolution for ai-bedo repository
ALBEDO_ROOT = Path(os.getenv("ALBEDO_ROOT", Path.home() / "git" / "internal" / "repos" / "ai-bedo"))


class AudioHistoryPanel(Static):
    """Display audio message history with playback capability."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.audio_dir = self._detect_audio_directory()
        self.audio_files = []

    def _detect_audio_directory(self) -> Path:
        """Detect the correct audio directory based on environment.

        Returns directory with most audio files, or creates unified location.
        """
        # Check all possible locations and count files
        locations = [
            ALBEDO_ROOT / "communications" / "audio" / ".processed",
            ALBEDO_ROOT / "communications" / "vm-audio" / ".processed",
            ALBEDO_ROOT / "communications" / "main-audio" / ".processed",
            ALBEDO_ROOT / "communications" / "audio" / "Audio" / ".processed",
        ]

        best_location = None
        max_files = 0

        for location in locations:
            if location.exists():
                # Count .txt files
                file_count = len(list(location.glob("*.txt")))
                if file_count > max_files:
                    max_files = file_count
                    best_location = location

        # If we found files, use that location
        if best_location:
            return best_location

        # Otherwise create and use unified location
        unified = ALBEDO_ROOT / "communications" / "audio" / ".processed"
        unified.mkdir(parents=True, exist_ok=True)
        return unified

    def compose(self) -> ComposeResult:
        """Create the audio history panel."""
        yield Static("Audio History", classes="panel-title")
        table = DataTable(id="audio-history-table")
        table.add_columns("Time", "Source", "Message")
        table.cursor_type = "row"
        yield table

    def on_mount(self) -> None:
        """Populate audio history table on mount."""
        self.load_audio_files()
        self.populate_table()

    def load_audio_files(self):
        """Load audio files from the audio directory."""
        self.audio_files = []

        if not self.audio_dir.exists():
            return

        # Find all .txt files (audio summaries)
        txt_files = sorted(self.audio_dir.glob("*.txt"), reverse=True)

        # Limit to last 20 files for performance (prevent rendering issues)
        for txt_file in txt_files[:20]:
            try:
                # Parse filename: YYYYMMDD-HHMMSS-project-environment.txt
                filename = txt_file.stem
                parts = filename.split('-')

                if len(parts) >= 2:
                    # Extract timestamp
                    date_str = parts[0]
                    time_str = parts[1]
                    timestamp = f"{date_str}-{time_str}"

                    # Extract project and environment
                    if len(parts) >= 4:
                        project = '-'.join(parts[2:-1])
                        environment = parts[-1]
                        source = f"{project} ({environment})"
                    elif len(parts) >= 3:
                        project = parts[2]
                        source = project
                    else:
                        source = "unknown"

                    # Read message content (first 60 chars)
                    with open(txt_file, 'r') as f:
                        content = f.read().strip()
                        message = content[:60] + "..." if len(content) > 60 else content

                    # Check if mp3 exists
                    mp3_file = txt_file.with_suffix('.mp3')

                    self.audio_files.append({
                        'timestamp': timestamp,
                        'source': source,
                        'message': message,
                        'txt_path': txt_file,
                        'mp3_path': mp3_file if mp3_file.exists() else None,
                        'full_content': content
                    })
            except Exception as e:
                # Skip files that don't match expected format
                continue

    def populate_table(self):
        """Populate the DataTable with audio history."""
        table = self.query_one("#audio-history-table", DataTable)
        table.clear()

        if not self.audio_files:
            # Empty state - no error message needed
            return

        for idx, audio in enumerate(self.audio_files):
            # Format timestamp as HH:MM
            try:
                date_str, time_str = audio['timestamp'].split('-')
                hour = time_str[:2]
                minute = time_str[2:4]
                display_time = f"{hour}:{minute}"
            except:
                display_time = audio['timestamp']

            # Add indicator if mp3 is available
            source_display = audio['source']
            if audio['mp3_path']:
                source_display = f"🔊 {source_display}"

            table.add_row(
                display_time,
                source_display,
                audio['message'],
                key=str(idx)
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection - show full message and play audio."""
        try:
            row_key = event.row_key.value
            idx = int(row_key)
            audio = self.audio_files[idx]

            # Log to activity log
            try:
                log = self.app.query_one("#activity-log")
                timestamp = datetime.now().strftime('%H:%M:%S')
                log.write_line(f"[dim][{timestamp}][/dim] Playing: {audio['source']}")
                log.write_line(f"[cyan]{audio['full_content']}[/cyan]")
            except Exception:
                pass  # Activity log not available

            # Play mp3 if available
            if audio['mp3_path'] and audio['mp3_path'].exists():
                try:
                    # Use afplay to play audio (non-blocking)
                    subprocess.Popen(
                        ["afplay", str(audio['mp3_path'])],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    try:
                        log = self.app.query_one("#activity-log")
                        log.write_line(f"[green]✓[/green] Audio playing: {audio['mp3_path'].name}")
                    except Exception:
                        pass
                except Exception as e:
                    try:
                        log = self.app.query_one("#activity-log")
                        log.write_line(f"[red]✗[/red] Could not play audio: {e}")
                    except Exception:
                        pass
            else:
                try:
                    log = self.app.query_one("#activity-log")
                    log.write_line(f"[yellow]⊗[/yellow] No audio file available")
                except Exception:
                    pass

        except Exception as e:
            try:
                log = self.app.query_one("#activity-log")
                log.write_line(f"[red]✗[/red] Error playing audio: {e}")
            except Exception:
                pass  # Can't log error

    def refresh_data(self):
        """Refresh audio history data."""
        self.load_audio_files()
        self.populate_table()
