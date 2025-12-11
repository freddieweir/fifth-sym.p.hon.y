"""
Terminal UI chat client with color-coded messages.

Attention-friendly visual design with emoji indicators and rich formatting.
"""

import asyncio
import json
import logging
from datetime import datetime

import websockets
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

logger = logging.getLogger(__name__)


class ChatClient:
    """
    Terminal UI chat client with color-coded messages.

    Color-coded usernames for easy agent identification.
    """

    # Color mappings for different agents
    COLORS = {
        "User": "cyan",
        "Fifth-Symphony": "magenta",
        "Nazarick-Agent": "blue",
        "Code-Assistant": "green",
        "VM-Claude": "yellow",
        "System": "dim white",
    }

    # Emoji indicators for different agents
    EMOJIS = {
        "User": "👤",
        "Fifth-Symphony": "🎵",
        "Nazarick-Agent": "🎭",
        "Code-Assistant": "🤖",
        "VM-Claude": "🖥️",
        "System": "⚙️",
    }

    def __init__(self, username: str = "User", server_url: str = "ws://localhost:8765"):
        """
        Initialize chat client.

        Args:
            username: Display name for this client
            server_url: WebSocket server URL
        """
        self.username = username
        self.server_url = server_url
        self.console = Console()
        self.messages = []
        self.websocket: websockets.WebSocketClientProtocol | None = None
        self.running = False

    async def connect(self):
        """Connect to chat server and start message loop."""
        self.running = True

        try:
            async with websockets.connect(self.server_url) as websocket:
                self.websocket = websocket
                self.console.print(
                    Panel(
                        f"[bold green]Connected to Fifth Symphony Chat[/bold green]\n"
                        f"Username: [bold {self.COLORS.get(self.username, 'white')}]{self.EMOJIS.get(self.username, '')} {self.username}[/bold {self.COLORS.get(self.username, 'white')}]\n"
                        f"Server: {self.server_url}",
                        title="🎵 Fifth Symphony Multi-Agent Chat",
                        border_style="magenta",
                    )
                )

                # Start receiver task
                receiver_task = asyncio.create_task(self.receive_messages())

                # Start sender task
                sender_task = asyncio.create_task(self.send_messages())

                # Wait for either task to complete
                done, pending = await asyncio.wait(
                    [receiver_task, sender_task], return_when=asyncio.FIRST_COMPLETED
                )

                # Cancel pending tasks
                for task in pending:
                    task.cancel()

        except websockets.exceptions.ConnectionRefused:
            self.console.print(
                "[bold red]❌ Connection refused. Is the chat server running?[/bold red]"
            )
            self.console.print("   Try: python -m modules.chat.chat_server")
        except Exception as e:
            self.console.print(f"[bold red]❌ Connection error: {e}[/bold red]")
        finally:
            self.running = False

    async def receive_messages(self):
        """Receive and display messages from server."""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    self.display_message(data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received: {message}")
                except Exception as e:
                    logger.error(f"Error displaying message: {e}")
        except websockets.exceptions.ConnectionClosed:
            self.console.print("[dim]Connection closed by server[/dim]")
            self.running = False
        except Exception as e:
            logger.error(f"Error receiving messages: {e}")
            self.running = False

    async def send_messages(self):
        """Send user messages to server."""
        while self.running:
            try:
                # Get user input (blocking, but in separate task)
                user_input = await asyncio.to_thread(input)

                if not user_input.strip():
                    continue

                # Handle exit commands
                if user_input.lower() in ["/quit", "/exit", "/q"]:
                    self.console.print("[dim]Disconnecting...[/dim]")
                    self.running = False
                    break

                # Send message
                message = {
                    "username": self.username,
                    "content": user_input,
                }
                await self.websocket.send(json.dumps(message))

            except EOFError:
                self.running = False
                break
            except Exception as e:
                logger.error(f"Error sending message: {e}")

    def display_message(self, data: dict):
        """
        Display color-coded message.

        Args:
            data: Message dict with username, content, timestamp
        """
        username = data.get("username", "Unknown")
        content = data.get("content", "")
        timestamp = data.get("timestamp", datetime.now().isoformat())

        # Parse timestamp
        try:
            dt = datetime.fromisoformat(timestamp)
            time_str = dt.strftime("%H:%M:%S")
        except (ValueError, AttributeError):
            time_str = "??:??:??"

        # Get color and emoji
        color = self.COLORS.get(username, "white")
        emoji = self.EMOJIS.get(username, "")

        # Create formatted message
        text = Text()
        text.append(f"[{time_str}] ", style="dim")
        text.append(f"{emoji} {username}: ", style=f"bold {color}")
        text.append(content, style="white")

        self.console.print(text)

    async def post_message(self, content: str):
        """
        Post message to chat (for programmatic use).

        Args:
            content: Message content
        """
        if self.websocket and self.running:
            message = {
                "username": self.username,
                "content": content,
            }
            await self.websocket.send(json.dumps(message))


async def main():
    """Run standalone chat client."""
    import argparse

    parser = argparse.ArgumentParser(description="Fifth Symphony Chat Client")
    parser.add_argument(
        "--username",
        default="User",
        help="Display name (User, Fifth-Symphony, Nazarick-Agent, Code-Assistant, VM-Claude)",
    )
    parser.add_argument("--server", default="ws://localhost:8765", help="WebSocket server URL")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    client = ChatClient(username=args.username, server_url=args.server)
    await client.connect()


if __name__ == "__main__":
    asyncio.run(main())
