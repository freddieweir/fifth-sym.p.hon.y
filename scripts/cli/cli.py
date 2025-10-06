#!/usr/bin/env python3
"""
Fifth Symphony CLI

Unified Python CLI for all Fifth Symphony commands.
Replaces bash scripts with Python-only interface.
"""

import asyncio
import sys
from pathlib import Path

import click
from rich.console import Console

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent))

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="Fifth Symphony")
def cli():
    """
    🎵 Fifth Symphony - AI-Powered Distributed Automation Conductor

    Orchestrates Python, Bash, and AppleScript scripts across networks
    with voice synthesis, multi-agent chat, and Attention-friendly interfaces.
    """
    pass


@cli.command()
@click.option("--with-chat", is_flag=True, help="Enable multi-agent chat integration")
@click.option("--quiet", "-q", is_flag=True, help="Disable voice feedback")
@click.option("--no-reminders", is_flag=True, help="Disable reminder system")
@click.argument("script", required=False)
def orchestrator(with_chat, quiet, no_reminders, script):
    """
    Start the orchestrator for script execution.

    Run without arguments for interactive mode,
    or specify a script name to run directly.
    """
    from main import NeuralOrchestra

    console.print("[bold magenta]🎵 Fifth Symphony Orchestrator[/bold magenta]")

    # Build args for main.py
    args = []
    if script:
        args.append(script)
    if with_chat:
        args.append("--with-chat")
    if quiet:
        args.append("--quiet")
    if no_reminders:
        args.append("--no-reminders")

    # Run orchestrator
    orchestra = NeuralOrchestra()
    asyncio.run(orchestra.main())


@cli.command()
def dashboard():
    """
    Launch the multi-pane dashboard TUI.

    Features:
    - Live chat feed
    - Directory tree view
    - Docker container monitoring
    - Ollama model output
    - Status logs
    """
    from dashboard import main as dashboard_main

    console.print("[bold magenta]🎵 Fifth Symphony Dashboard[/bold magenta]")
    console.print("   Multi-pane TUI with synchronized views")
    console.print()

    asyncio.run(dashboard_main())


@cli.command()
def chat_server():
    """
    Start the WebSocket chat server.

    Runs on localhost:8765 for multi-agent communication.
    """
    from modules.chat.chat_server import main as server_main

    console.print("[bold magenta]🎵 Fifth Symphony Chat Server[/bold magenta]")
    console.print("   WebSocket server on ws://localhost:8765")
    console.print("   Press Ctrl+C to stop")
    console.print()

    asyncio.run(server_main())


@cli.command()
@click.option("--username", "-u", default="User", help="Display name for chat")
@click.option("--server", "-s", default="ws://localhost:8765", help="WebSocket server URL")
def chat_client(username, server):
    """
    Connect to the chat server as a client.

    Available usernames:
    - User (👤 Cyan)
    - Fifth-Symphony (🎵 Magenta)
    - Nazarick-Agent (🎭 Blue)
    - Code-Assistant (🤖 Green)
    - VM-Claude (🖥️ Yellow)
    """
    from modules.chat.chat_client import main as client_main

    console.print("[bold magenta]🎵 Fifth Symphony Chat Client[/bold magenta]")
    console.print(f"   Connecting to {server}")
    console.print(f"   Username: {username}")
    console.print()

    # Override sys.argv for client main
    sys.argv = ["chat_client", "--username", username, "--server", server]

    asyncio.run(client_main())


@cli.command()
@click.option("--port", "-p", default=8000, help="Port for MCP server")
def mcp_chat():
    """
    Start the MCP chat tool server.

    Allows Claude Code agents to post messages to the chat.
    """
    from modules.mcp.chat_tool import main as mcp_main

    console.print("[bold magenta]🎵 Fifth Symphony MCP Chat Tool[/bold magenta]")
    console.print("   Starting MCP server for Claude Code integration")
    console.print()

    asyncio.run(mcp_main())


@cli.command()
def status():
    """
    Show status of all Fifth Symphony services.

    Checks:
    - Chat server (port 8765)
    - Docker containers
    - YubiKey session
    - 1Password session
    """
    import socket
    import subprocess

    console.print("[bold magenta]🎵 Fifth Symphony Status[/bold magenta]")
    console.print()

    # Check chat server
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("localhost", 8765))
        sock.close()

        if result == 0:
            console.print("✅ Chat server: [green]Running[/green] on port 8765")
        else:
            console.print("❌ Chat server: [red]Not running[/red]")
    except Exception as e:
        console.print(f"⚠️ Chat server: [yellow]Error checking: {e}[/yellow]")

    # Check Docker
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            container_count = len([line for line in result.stdout.strip().split("\n") if line])
            console.print(f"✅ Docker: [green]{container_count} containers running[/green]")
        else:
            console.print("❌ Docker: [red]Not available[/red]")
    except Exception:
        console.print("❌ Docker: [red]Not installed or not running[/red]")

    # Check YubiKey session
    session_file = Path.home() / ".fifth-symphony-yubikey-session"
    if session_file.exists():
        console.print("✅ YubiKey: [green]Session active[/green]")
    else:
        console.print("⚪ YubiKey: [dim]No active session[/dim]")

    # Check 1Password
    try:
        result = subprocess.run(["op", "whoami"], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            console.print("✅ 1Password: [green]Signed in[/green]")
        else:
            console.print("⚪ 1Password: [dim]Not signed in[/dim]")
    except Exception:
        console.print("⚪ 1Password CLI: [dim]Not installed[/dim]")


if __name__ == "__main__":
    cli()
