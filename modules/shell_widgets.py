"""
Interactive shell widgets for Textual dashboard.

Provides embedded ZSH shells using ptyprocess for real terminal emulation.
"""

import asyncio
import os
import pty
import select
import termios
import tty
from typing import Optional

from textual.widget import Widget
from textual.widgets import Static
from rich.text import Text
from rich.console import RenderableType


class ShellWidget(Widget):
    """
    Embedded interactive shell widget.

    Creates a real PTY (pseudo-terminal) running ZSH.
    Supports full terminal interaction including colors, cursor movement, etc.
    """

    def __init__(
        self, shell_cmd: str = "/bin/zsh", name: str = "shell", title: str = "Shell", **kwargs
    ):
        """
        Initialize shell widget.

        Args:
            shell_cmd: Shell command to run (default: /bin/zsh)
            name: Widget name
            title: Display title
        """
        super().__init__(**kwargs)
        self.shell_cmd = shell_cmd
        self.widget_name = name
        self.title = title

        # PTY file descriptors
        self.master_fd: Optional[int] = None
        self.pid: Optional[int] = None

        # Output buffer
        self.output_lines = []
        self.max_lines = 1000

    async def on_mount(self):
        """Start shell when widget mounts."""
        await self.start_shell()

        # Start output reader task
        asyncio.create_task(self.read_output_loop())

    async def start_shell(self):
        """Start shell process with PTY."""
        try:
            # Fork process with PTY
            self.pid, self.master_fd = pty.fork()

            if self.pid == 0:
                # Child process - exec shell
                os.execvp(self.shell_cmd, [self.shell_cmd])
            else:
                # Parent process - set up terminal
                # Make stdin non-blocking
                tty.setraw(self.master_fd)
                attrs = termios.tcgetattr(self.master_fd)
                attrs[3] = attrs[3] & ~termios.ECHO  # Disable echo
                termios.tcsetattr(self.master_fd, termios.TCSANOW, attrs)

        except Exception as e:
            self.output_lines.append(f"Error starting shell: {e}")

    async def read_output_loop(self):
        """Continuously read shell output."""
        while self.master_fd:
            try:
                # Check if data available
                readable, _, _ = select.select([self.master_fd], [], [], 0.1)

                if readable:
                    # Read available data
                    try:
                        data = os.read(self.master_fd, 1024)
                        if data:
                            # Decode and add to output
                            text = data.decode("utf-8", errors="ignore")
                            self.add_output(text)
                            self.refresh()
                    except OSError:
                        # Shell closed
                        break

                # Small delay to prevent CPU spinning
                await asyncio.sleep(0.05)

            except Exception as e:
                self.output_lines.append(f"Read error: {e}")
                break

    def add_output(self, text: str):
        """Add output text to buffer."""
        # Split into lines
        lines = text.split("\n")

        # Add to buffer
        self.output_lines.extend(lines)

        # Trim if too long
        if len(self.output_lines) > self.max_lines:
            self.output_lines = self.output_lines[-self.max_lines :]

    async def send_command(self, command: str):
        """
        Send command to shell.

        Args:
            command: Command string to send
        """
        if self.master_fd:
            try:
                # Add newline if not present
                if not command.endswith("\n"):
                    command += "\n"

                # Write to shell
                os.write(self.master_fd, command.encode("utf-8"))
            except Exception as e:
                self.output_lines.append(f"Send error: {e}")

    def render(self) -> RenderableType:
        """Render shell output."""
        # Join last N lines for display
        display_lines = self.output_lines[-50:]  # Show last 50 lines
        output = "\n".join(display_lines)

        return Text(output, style="white on black")

    async def on_unmount(self):
        """Clean up when widget unmounts."""
        if self.master_fd:
            try:
                os.close(self.master_fd)
            except OSError:
                pass

        if self.pid:
            try:
                os.kill(self.pid, 15)  # SIGTERM
            except (OSError, ProcessLookupError):
                pass


class OllamaShellWidget(ShellWidget):
    """
    Specialized shell widget for Ollama repo analysis.

    Pre-configured with helpful environment and startup commands.
    """

    def __init__(self, **kwargs):
        super().__init__(title="🧠 Ollama Analysis Shell", name="ollama-shell", **kwargs)

    async def on_mount(self):
        """Start shell and set up environment."""
        await super().on_mount()

        # Wait for shell to be ready
        await asyncio.sleep(0.5)

        # Send initialization commands
        await self.send_command("# Ollama Repo Analysis Shell")
        await self.send_command("# Use 'ollama run' to analyze code")
        await self.send_command("echo 'Ready for repo analysis...'")


class UserShellWidget(ShellWidget):
    """
    Standard user ZSH shell.

    Your personal interactive shell for manual commands.
    """

    def __init__(self, **kwargs):
        super().__init__(title="💻 Your ZSH Shell", name="user-shell", **kwargs)

    async def on_mount(self):
        """Start user shell."""
        await super().on_mount()

        # Wait for shell to be ready
        await asyncio.sleep(0.5)

        # Send welcome message
        await self.send_command("# Your Interactive Shell")
        await self.send_command("echo 'Fifth Symphony User Shell Ready'")
