#!/usr/bin/env python3
"""
Fifth Symphony Multi-Pane Dashboard

Attention-friendly TUI with multiple synchronized views:
- Live chat feed
- Directory tree
- Ollama model output
- Status/logs
- Script execution
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

import websockets
import yaml
from rich.panel import Panel
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import DataTable, Footer, Header, Input, RichLog, Static, Tree

from modules.docker_monitor import DockerMonitor


class ChatPane(Static):
    """Live chat feed with color-coded messages"""

    # Color mappings for agents
    COLORS = {
        "User": "cyan",
        "Fifth-Symphony": "magenta",
        "Nazarick-Agent": "blue",
        "Code-Assistant": "green",
        "VM-Claude": "yellow",
        "System": "dim white",
    }

    EMOJIS = {
        "User": "👤",
        "Fifth-Symphony": "🎵",
        "Nazarick-Agent": "🎭",
        "Code-Assistant": "🤖",
        "VM-Claude": "🖥️",
        "System": "⚙️",
    }

    def __init__(self, server_url: str = "ws://localhost:8765"):
        super().__init__()
        self.server_url = server_url
        self.websocket: websockets.WebSocketClientProtocol | None = None
        self.messages = []

    async def on_mount(self):
        """Connect to chat server on mount"""
        self.log = RichLog(highlight=True, markup=True)
        await self.mount(self.log)
        asyncio.create_task(self.connect_chat())

    async def connect_chat(self):
        """Connect to chat server and receive messages"""
        try:
            async with websockets.connect(self.server_url) as websocket:
                self.websocket = websocket
                self.log.write("[bold green]Connected to Fifth Symphony Chat[/bold green]")

                async for message in websocket:
                    try:
                        data = json.loads(message)
                        self.display_message(data)
                    except json.JSONDecodeError:
                        pass
        except websockets.exceptions.ConnectionRefused:
            self.log.write("[bold red]❌ Chat server not running[/bold red]")
            self.log.write("   Start with: ./start_chat_server.sh")
        except Exception as e:
            self.log.write(f"[bold red]Chat error: {e}[/bold red]")

    def display_message(self, data: dict):
        """Display color-coded chat message"""
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

        # Format message
        text = Text()
        text.append(f"[{time_str}] ", style="dim")
        text.append(f"{emoji} {username}: ", style=f"bold {color}")
        text.append(content, style="white")

        self.log.write(text)


class DirectoryTreePane(Static):
    """Live directory tree view"""

    def __init__(self, root_path: Path):
        super().__init__()
        self.root_path = root_path

    def compose(self) -> ComposeResult:
        """Create directory tree widget"""
        tree = Tree(str(self.root_path), id="directory-tree")
        tree.root.expand()
        yield tree

    async def on_mount(self):
        """Populate tree on mount"""
        tree = self.query_one("#directory-tree", Tree)
        await self.populate_tree(tree.root, self.root_path)

    async def populate_tree(self, node, path: Path, max_depth: int = 3, current_depth: int = 0):
        """Recursively populate directory tree"""
        if current_depth >= max_depth:
            return

        try:
            items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))

            for item in items:
                # Skip hidden files and common ignored directories
                if item.name.startswith("."):
                    continue
                if item.name in ["__pycache__", "node_modules", ".venv", "venv"]:
                    continue

                # Determine icon
                if item.is_dir():
                    label = f"📁 {item.name}"
                elif item.suffix == ".py":
                    label = f"🐍 {item.name}"
                elif item.suffix in [".sh", ".bash"]:
                    label = f"📜 {item.name}"
                elif item.suffix in [".md", ".txt"]:
                    label = f"📄 {item.name}"
                elif item.suffix in [".yaml", ".yml", ".json"]:
                    label = f"⚙️ {item.name}"
                else:
                    label = f"📄 {item.name}"

                child = node.add(label, allow_expand=item.is_dir())

                # Recursively populate directories
                if item.is_dir():
                    await self.populate_tree(child, item, max_depth, current_depth + 1)

        except PermissionError:
            pass


class DockerPane(Static):
    """Docker container status and logs"""

    def __init__(self, docker_config: dict):
        super().__init__()
        self.docker_config = docker_config
        self.monitor = DockerMonitor(watched_containers=docker_config.get("watched_containers", []))
        self.current_log_container = docker_config.get("default_log_container")

    def compose(self) -> ComposeResult:
        """Create Docker pane widgets"""
        yield Static("[bold blue]🐳 Docker Containers[/bold blue]", id="docker-header")
        yield DataTable(id="docker-table")
        yield Static("[bold blue]📜 Container Logs[/bold blue]", id="logs-header")
        yield RichLog(highlight=True, markup=True, id="docker-logs")

    async def on_mount(self):
        """Initialize Docker pane"""
        table = self.query_one("#docker-table", DataTable)
        table.add_columns("Status", "Name", "Health", "ID")

        # Start status refresh task
        asyncio.create_task(self.refresh_status_loop())

        # Start log streaming task
        if self.current_log_container:
            asyncio.create_task(self.stream_logs_loop())

    async def refresh_status_loop(self):
        """Periodically refresh container status"""
        table = self.query_one("#docker-table", DataTable)
        interval = self.docker_config.get("refresh", {}).get("status_interval", 5)

        status_emoji = self.docker_config.get("display", {}).get("status_emoji", {})
        health_emoji = self.docker_config.get("display", {}).get("health_emoji", {})

        while True:
            try:
                statuses = self.monitor.get_container_status()

                # Clear and repopulate table
                table.clear()

                for container in statuses:
                    status = container["status"]
                    health = container["health"]

                    # Get emoji
                    status_icon = status_emoji.get(status, "⚪")
                    health_icon = (
                        health_emoji.get(health.lower(), "➖") if health != "N/A" else "➖"
                    )

                    table.add_row(
                        f"{status_icon} {status}",
                        container["name"],
                        f"{health_icon} {health}",
                        container["id"],
                    )

                await asyncio.sleep(interval)

            except Exception as e:
                logs = self.query_one("#docker-logs", RichLog)
                logs.write(f"[red]Status refresh error: {e}[/red]")
                await asyncio.sleep(interval)

    async def stream_logs_loop(self):
        """Stream logs from selected container"""
        logs = self.query_one("#docker-logs", RichLog)

        log_settings = self.docker_config.get("log_settings", {})
        tail_lines = log_settings.get("tail_lines", 100)
        follow = log_settings.get("follow", True)

        logs.write(f"[bold cyan]Streaming logs from: {self.current_log_container}[/bold cyan]")

        try:
            async for log_line in self.monitor.stream_logs(
                self.current_log_container, lines=tail_lines, follow=follow
            ):
                logs.write(log_line)

        except Exception as e:
            logs.write(f"[red]Log streaming error: {e}[/red]")


class OllamaPane(Static):
    """Ollama model output and interaction"""

    def compose(self) -> ComposeResult:
        """Create Ollama output log"""
        yield RichLog(highlight=True, markup=True, id="ollama-log")

    def on_mount(self):
        """Initialize Ollama pane"""
        log = self.query_one("#ollama-log", RichLog)
        log.write("[bold magenta]🧠 Ollama Model Output[/bold magenta]")
        log.write("[dim]Waiting for model activity...[/dim]")

    def write_model_output(self, model: str, prompt: str, response: str):
        """Write model output to log"""
        log = self.query_one("#ollama-log", RichLog)

        log.write(
            Panel(
                f"[bold cyan]Prompt:[/bold cyan] {prompt}\n\n"
                f"[bold green]Response:[/bold green] {response}",
                title=f"🧠 {model}",
                border_style="magenta",
            )
        )


class StatusPane(Static):
    """Status and log messages"""

    def compose(self) -> ComposeResult:
        """Create status log"""
        yield RichLog(highlight=True, markup=True, id="status-log")

    def on_mount(self):
        """Initialize status pane"""
        log = self.query_one("#status-log", RichLog)
        log.write("[bold green]🎵 Fifth Symphony Dashboard[/bold green]")
        log.write(f"[dim]Started at {datetime.now().strftime('%H:%M:%S')}[/dim]")

    def write_status(self, message: str, style: str = "white"):
        """Write status message"""
        log = self.query_one("#status-log", RichLog)
        timestamp = datetime.now().strftime("%H:%M:%S")
        log.write(f"[dim][{timestamp}][/dim] [{style}]{message}[/{style}]")


class ChatInput(Static):
    """Chat input widget"""

    def compose(self) -> ComposeResult:
        """Create input field"""
        yield Input(placeholder="Type message... (Ctrl+S to send)", id="chat-input")

    def on_mount(self):
        """Focus input on mount"""
        self.query_one("#chat-input", Input).focus()


class FifthSymphonyDashboard(App):
    """
    Fifth Symphony Multi-Pane Dashboard

    Keyboard shortcuts:
    - Ctrl+C: Quit
    - Ctrl+S: Send chat message
    - Ctrl+R: Refresh directory tree
    """

    chat_websocket: websockets.WebSocketClientProtocol | None = None

    CSS = """
    Screen {
        layout: grid;
        grid-size: 3 3;
        grid-rows: 1fr 1fr 3;
    }

    #chat-pane {
        column-span: 1;
        row-span: 2;
        border: solid magenta;
    }

    #directory-pane {
        column-span: 1;
        row-span: 1;
        border: solid cyan;
    }

    #docker-pane {
        column-span: 1;
        row-span: 2;
        border: solid blue;
    }

    #ollama-pane {
        column-span: 1;
        row-span: 1;
        border: solid green;
    }

    #status-pane {
        column-span: 3;
        row-span: 1;
        border: solid yellow;
    }

    #chat-input-container {
        height: 3;
        dock: bottom;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True),
        Binding("ctrl+s", "send_message", "Send", show=True),
        Binding("ctrl+r", "refresh_tree", "Refresh", show=True),
    ]

    def __init__(self, config_path: Path = None):
        super().__init__()
        self.config_path = config_path or Path.cwd() / "config"
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """Load configuration"""
        config_file = self.config_path / "settings.yaml"
        docker_config_file = self.config_path / "docker_monitor.yaml"

        config = {}
        if config_file.exists():
            with open(config_file, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}

        # Load Docker monitoring config
        if docker_config_file.exists():
            with open(docker_config_file, encoding="utf-8") as f:
                config["docker"] = yaml.safe_load(f) or {}
        else:
            config["docker"] = {}

        return config

    def compose(self) -> ComposeResult:
        """Compose dashboard layout"""
        yield Header(show_clock=True)

        # Chat pane (left, full height)
        with Container(id="chat-pane"):
            yield Static("[bold magenta]🎵 Multi-Agent Chat[/bold magenta]")
            yield ChatPane(self.config.get("chat", {}).get("server_url", "ws://localhost:8765"))

        # Directory tree (top middle)
        with Container(id="directory-pane"):
            yield Static("[bold cyan]📁 Project Directory[/bold cyan]")
            yield DirectoryTreePane(Path.cwd())

        # Docker pane (right, full height)
        with Container(id="docker-pane"):
            yield DockerPane(self.config.get("docker", {}))

        # Ollama output (middle middle)
        with Container(id="ollama-pane"):
            yield OllamaPane()

        # Status/logs (bottom, full width)
        with Container(id="status-pane"):
            yield Static("[bold yellow]📊 Status & Logs[/bold yellow]")
            yield StatusPane()

        # Chat input (bottom)
        with Container(id="chat-input-container"):
            yield ChatInput()

        yield Footer()

    async def on_mount(self):
        """Connect to chat server on mount"""
        chat_config = self.config.get("chat", {})
        server_url = chat_config.get("server_url", "ws://localhost:8765")

        try:
            self.chat_websocket = await websockets.connect(server_url)
            status_pane = self.query_one(StatusPane)
            status_pane.write_status("Connected to chat server", "green")
        except Exception as e:
            status_pane = self.query_one(StatusPane)
            status_pane.write_status(f"Chat connection failed: {e}", "red")

    async def action_send_message(self):
        """Send chat message"""
        input_widget = self.query_one("#chat-input", Input)
        message = input_widget.value.strip()

        if not message:
            return

        status_pane = self.query_one(StatusPane)

        if not self.chat_websocket:
            status_pane.write_status("Not connected to chat server", "red")
            return

        try:
            # Send message to chat server
            chat_message = {"username": "User", "content": message}
            await self.chat_websocket.send(json.dumps(chat_message))
            input_widget.value = ""
            status_pane.write_status(f"Sent: {message}", "green")
        except Exception as e:
            status_pane.write_status(f"Send failed: {e}", "red")

    async def action_refresh_tree(self):
        """Refresh directory tree"""
        status_pane = self.query_one(StatusPane)
        status_pane.write_status("Refreshing directory tree...", "cyan")

        # TODO: Implement tree refresh
        tree_pane = self.query_one(DirectoryTreePane)
        tree = tree_pane.query_one("#directory-tree", Tree)
        tree.clear()
        await tree_pane.populate_tree(tree.root, tree_pane.root_path)

        status_pane.write_status("Tree refreshed", "green")


async def main():
    """Run dashboard"""
    app = FifthSymphonyDashboard()
    await app.run_async()


if __name__ == "__main__":
    asyncio.run(main())
