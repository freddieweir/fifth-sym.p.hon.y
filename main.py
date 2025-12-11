#!/usr/bin/env python3
"""
Neural Orchestra - Distributed Automation Conductor
AI-powered automation system orchestrating scripts across networks
with voice synthesis and modular integration
"""

import argparse
import asyncio
import sys
from pathlib import Path

import yaml
from rich.console import Console
from rich.table import Table

from modules.onepassword_manager import OnePasswordManager
from modules.output_translator import OutputTranslator
from modules.reminder_system import ReminderSystem
from modules.script_runner import ScriptRunner
from modules.symlink_manager import SymlinkManager
from modules.voice_handler import VoiceHandler
from modules.orchestrator.chat_integration import OrchestratorChatContext
from modules.yubikey_auth import YubiKeyAuth

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent))


class NeuralOrchestra:
    """
    Neural Orchestra - Distributed Automation Conductor
    AI-powered automation system orchestrating scripts across networks
    with voice synthesis and modular integration
    """

    def __init__(self, config_path: Path = None, enable_chat: bool = False):
        self.console = Console()
        self.config_path = config_path or Path(__file__).parent / "config"
        self.scripts_path = Path(__file__).parent / "scripts"
        self.symlinks_path = Path(__file__).parent / "scripts" / "symlinks"

        # Initialize configuration
        self.config = self._load_config()

        # Initialize modules
        self.op_manager = OnePasswordManager(self.config.get("onepassword", {}))
        self.voice_handler = VoiceHandler(self.config.get("voice", {}), self.op_manager)
        self.output_translator = OutputTranslator(self.config.get("translation", {}))
        self.script_runner = ScriptRunner(self.scripts_path)
        self.reminder_system = ReminderSystem(self.voice_handler, self.config.get("reminders", {}))
        self.symlink_manager = SymlinkManager(self.symlinks_path)

        # Chat integration (optional)
        self.enable_chat = enable_chat or self.config.get("chat", {}).get("enabled", False)
        self.chat_client = None

        # Track running scripts
        self.running_scripts: dict[str, asyncio.Task] = {}

    def _load_config(self) -> dict:
        """Load main configuration file"""
        config_file = self.config_path / "settings.yaml"
        if config_file.exists():
            with open(config_file, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return self._create_default_config()

    def _create_default_config(self) -> dict:
        """Create default configuration"""
        return {
            "voice": {
                "enabled": True,
                "voice_id": "Albedo",
                "api_key_item": "Eleven Labs API",
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
            "onepassword": {"vault": "Development", "signin_account": None},
            "reminders": {
                "enabled": True,
                "interval_seconds": 120,
                "escalation_levels": [
                    {"after_seconds": 120, "urgency": "gentle"},
                    {"after_seconds": 300, "urgency": "moderate"},
                    {"after_seconds": 600, "urgency": "urgent"},
                ],
            },
            "translation": {"technical_to_voice": True, "simplify_errors": True},
            "scripts": {
                "auto_discover": True,
                "excluded_patterns": ["__pycache__", "*.pyc", "test_*"],
            },
        }

    async def discover_scripts(self) -> list[Path]:
        """Discover all Python scripts in the scripts directory and symlinks"""
        scripts = []
        excluded_patterns = self.config.get("scripts", {}).get("excluded_patterns", [])

        # Discover scripts in the main scripts directory
        if self.scripts_path.exists():
            for script_file in self.scripts_path.glob("*.py"):
                # Skip excluded patterns
                if any(pattern in script_file.name for pattern in excluded_patterns):
                    continue
                scripts.append(script_file)

        # Discover scripts from symlinks directory
        if self.symlinks_path.exists():
            for item in self.symlinks_path.iterdir():
                # Skip metadata file
                if item.name.startswith("."):
                    continue

                # Check if it's a valid symlink to a script
                if item.is_symlink() and item.exists():
                    # Support both Python and shell scripts
                    if item.suffix in [".py", ".sh", ".bash"]:
                        # Skip excluded patterns
                        if any(pattern in item.name for pattern in excluded_patterns):
                            continue
                        scripts.append(item)

        # Sort scripts alphabetically
        scripts.sort(key=lambda x: x.name)
        return scripts

    def display_menu(self, scripts: list[Path]):
        """Display interactive menu of available scripts"""
        table = Table(title="Available Scripts", show_header=True, header_style="bold magenta")
        table.add_column("#", style="cyan", width=4)
        table.add_column("Script", style="green")
        table.add_column("Type", style="blue", width=10)
        table.add_column("Description", style="yellow")

        for idx, script in enumerate(scripts, 1):
            # Determine if it's a symlinked script
            is_symlink = script.is_symlink()
            script_type = "🔗 External" if is_symlink else "📦 Local"

            # Try to extract description from script docstring
            description = self._get_script_description(script)

            # Add location info for symlinked scripts
            if is_symlink:
                target = script.resolve()
                description = (
                    f"{description} [{target.parent.name}]"
                    if description
                    else f"From {target.parent.name}"
                )

            table.add_row(str(idx), script.stem, script_type, description)

        self.console.print(table)

    def _get_script_description(self, script_path: Path) -> str:
        """Extract description from script docstring"""
        try:
            with open(script_path, encoding="utf-8") as f:
                lines = f.readlines()
                in_docstring = False
                docstring_lines = []

                for line in lines[:20]:  # Check first 20 lines
                    if '"""' in line or "'''" in line:
                        if not in_docstring:
                            in_docstring = True
                            # Check if docstring starts and ends on same line
                            if line.count('"""') == 2 or line.count("'''") == 2:
                                return line.split('"""')[1].strip() or line.split("'''")[1].strip()
                        else:
                            break
                    elif in_docstring:
                        docstring_lines.append(line.strip())

                if docstring_lines:
                    return docstring_lines[0][:50] + ("..." if len(docstring_lines[0]) > 50 else "")
        except Exception:
            pass
        return "No description available"

    async def run_script(self, script_path: Path, args: list[str] = None):
        """Run a single script with voice feedback"""
        script_name = script_path.stem

        # Voice announcement
        await self.voice_handler.speak(f"Starting execution of {script_name}")

        # Chat announcement
        if self.chat_client:
            await self.chat_client.post_message(f"🎬 Starting script: {script_name}")

        # Create reminder task for this script
        reminder_task = None
        if self.config.get("reminders", {}).get("enabled"):
            reminder_task = asyncio.create_task(self.reminder_system.monitor_script(script_name))

        try:
            # Run the script
            async for output_type, output in self.script_runner.run_script_async(script_path, args):
                # Display output
                if output_type == "stdout":
                    self.console.print(output, style="green", end="")
                elif output_type == "stderr":
                    self.console.print(output, style="red", end="")

                # Translate and speak significant outputs
                if self.config.get("translation", {}).get("technical_to_voice"):
                    voice_message = await self.output_translator.translate_for_voice(output)
                    if voice_message:
                        await self.voice_handler.speak(voice_message, priority="low")

                # Check if script is waiting for input
                if self.script_runner.is_waiting_for_input(output):
                    if reminder_task:
                        reminder_task.cancel()
                    await self.voice_handler.speak(
                        f"{script_name} is waiting for your input", priority="high"
                    )
                    if self.chat_client:
                        await self.chat_client.post_message(f"⏸️ {script_name} waiting for input")
                    # Restart reminder after input is provided
                    if self.config.get("reminders", {}).get("enabled"):
                        reminder_task = asyncio.create_task(
                            self.reminder_system.monitor_script(script_name)
                        )

            # Script completed
            await self.voice_handler.speak(f"{script_name} completed successfully")
            if self.chat_client:
                await self.chat_client.post_message(f"✅ {script_name} completed successfully")

        except Exception as e:
            error_message = self.output_translator.simplify_error(str(e))
            await self.voice_handler.speak(
                f"Error in {script_name}: {error_message}", priority="high"
            )
            self.console.print(f"[red]Error: {e}[/red]")
            if self.chat_client:
                await self.chat_client.post_message(f"❌ {script_name} failed: {error_message}")
        finally:
            if reminder_task:
                reminder_task.cancel()

    async def run_orchestration_sequence(self, sequence_name: str):
        """Run a predefined sequence of scripts"""
        sequences_file = self.config_path / "sequences.yaml"
        if not sequences_file.exists():
            self.console.print("[red]No sequences file found[/red]")
            return

        with open(sequences_file, encoding="utf-8") as f:
            sequences = yaml.safe_load(f) or {}

        if sequence_name not in sequences:
            self.console.print(f"[red]Sequence '{sequence_name}' not found[/red]")
            return

        sequence = sequences[sequence_name]
        await self.voice_handler.speak(f"Starting orchestration sequence: {sequence_name}")

        for step in sequence.get("steps", []):
            script_name = step.get("script")
            args = step.get("args", [])
            wait_after = step.get("wait_after", 0)

            script_path = self.scripts_path / f"{script_name}.py"
            if script_path.exists():
                await self.run_script(script_path, args)
                if wait_after:
                    await asyncio.sleep(wait_after)
            else:
                self.console.print(f"[red]Script not found: {script_name}[/red]")
                await self.voice_handler.speak(f"Warning: Script {script_name} not found, skipping")

    async def manage_symlinks(self):
        """Interactive symlink management"""
        while True:
            self.console.clear()
            self.console.print("[bold magenta]Symlink Management[/bold magenta]\n")

            # Show existing symlinks
            symlinks = self.symlink_manager.list_symlinks()
            if symlinks:
                table = Table(title="Current Symlinks", show_header=True, header_style="bold cyan")
                table.add_column("Name", style="green")
                table.add_column("Target", style="yellow")
                table.add_column("Status", style="blue")

                for link in symlinks:
                    status = "✅ Valid" if link["valid"] else "❌ Broken"
                    table.add_row(link["name"], link.get("target", "Unknown"), status)

                self.console.print(table)
            else:
                self.console.print("[yellow]No symlinks configured[/yellow]")

            # Show options
            self.console.print("\n[bold cyan]Symlink Options:[/bold cyan]")
            self.console.print("1: Add new symlink")
            self.console.print("2: Remove symlink")
            self.console.print("3: Clean broken symlinks")
            self.console.print("4: Back to main menu")

            choice = self.console.input("\n[bold]Enter choice: [/bold]").strip()

            if choice == "1":
                # Add new symlink
                path = self.console.input("Enter full path to external script: ").strip()

                # Remove quotes if present
                path = path.strip('"').strip("'")

                # Handle spaces in path
                if path:
                    alias = self.console.input(
                        "Enter alias (or press Enter to use script name): "
                    ).strip()
                    alias = alias if alias else None

                    success, message = self.symlink_manager.add_symlink(path, alias)
                    if success:
                        self.console.print(f"[green]{message}[/green]")
                        await self.voice_handler.speak("Symlink created successfully")
                    else:
                        self.console.print(f"[red]{message}[/red]")
                        await self.voice_handler.speak("Failed to create symlink")

            elif choice == "2":
                # Remove symlink
                name = self.console.input("Enter symlink name to remove: ").strip()
                if name:
                    success, message = self.symlink_manager.remove_symlink(name)
                    if success:
                        self.console.print(f"[green]{message}[/green]")
                        await self.voice_handler.speak("Symlink removed successfully")
                    else:
                        self.console.print(f"[red]{message}[/red]")

            elif choice == "3":
                # Clean broken symlinks
                removed = self.symlink_manager.clean_broken_symlinks()
                if removed:
                    self.console.print(
                        f"[green]Removed {len(removed)} broken symlinks: {', '.join(removed)}[/green]"
                    )
                    await self.voice_handler.speak(f"Cleaned {len(removed)} broken symlinks")
                else:
                    self.console.print("[green]No broken symlinks found[/green]")

            elif choice == "4":
                break

            if choice != "4":
                self.console.input("\n[dim]Press Enter to continue...[/dim]")

    async def interactive_mode(self):
        """Run in interactive mode with menu"""
        await self.voice_handler.speak(
            "Welcome to the Neural Orchestra. Initializing automation symphony."
        )

        # Chat startup announcement
        if self.chat_client:
            await self.chat_client.post_message("🎵 Neural Orchestra started in interactive mode")

        scripts = await self.discover_scripts()

        if not scripts:
            self.console.print("[yellow]No scripts found in the scripts directory[/yellow]")
            await self.voice_handler.speak(
                "No scripts found. Please add Python scripts to the scripts directory."
            )
            return

        while True:
            self.console.clear()
            self.display_menu(scripts)

            self.console.print("\n[bold cyan]Options:[/bold cyan]")
            self.console.print("1-N: Run script by number")
            self.console.print("a: Run all scripts in sequence")
            self.console.print("s: Run a saved sequence")
            self.console.print("r: Refresh script list")
            self.console.print("l: Manage symlinks")
            self.console.print("q: Quit")

            choice = self.console.input("\n[bold]Enter choice: [/bold]").strip().lower()

            if choice == "q":
                await self.voice_handler.speak("Goodbye!")
                break
            if choice == "r":
                scripts = await self.discover_scripts()
                await self.voice_handler.speak("Script list refreshed")
            elif choice == "a":
                await self.voice_handler.speak("Running all scripts in sequence")
                for script in scripts:
                    await self.run_script(script)
            elif choice == "s":
                sequence_name = self.console.input("Enter sequence name: ").strip()
                await self.run_orchestration_sequence(sequence_name)
            elif choice == "l":
                await self.manage_symlinks()
                scripts = await self.discover_scripts()  # Refresh after managing symlinks
            else:
                try:
                    script_num = int(choice)
                    if 1 <= script_num <= len(scripts):
                        selected_script = scripts[script_num - 1]
                        await self.run_script(selected_script)
                    else:
                        self.console.print("[red]Invalid script number[/red]")
                except ValueError:
                    self.console.print("[red]Invalid choice[/red]")

            if choice != "q":
                self.console.input("\n[dim]Press Enter to continue...[/dim]")

    async def main(self):
        """Main entry point"""
        parser = argparse.ArgumentParser(
            description="Neural Orchestra - AI-Powered Distributed Automation Conductor"
        )
        parser.add_argument("script", nargs="?", help="Script name to run directly")
        parser.add_argument("-s", "--sequence", help="Run a predefined sequence")
        parser.add_argument("-a", "--args", nargs="+", help="Arguments to pass to the script")
        parser.add_argument("-q", "--quiet", action="store_true", help="Disable voice feedback")
        parser.add_argument("--no-reminders", action="store_true", help="Disable reminder system")
        parser.add_argument(
            "--with-chat", action="store_true", help="Enable multi-agent chat integration"
        )
        parser.add_argument(
            "--add-symlink", metavar="PATH", help="Add a symlink to an external script"
        )
        parser.add_argument(
            "--symlink-alias", help="Alias for the symlink (use with --add-symlink)"
        )
        parser.add_argument(
            "--list-symlinks", action="store_true", help="List all configured symlinks"
        )

        args = parser.parse_args()

        # Override config based on command line args
        if args.quiet:
            self.config["voice"]["enabled"] = False
            await self.voice_handler.set_enabled(False)

        if args.no_reminders:
            self.config["reminders"]["enabled"] = False

        if args.with_chat:
            self.enable_chat = True

        # Initialize chat connection if enabled
        chat_context = None
        if self.enable_chat:
            chat_config = self.config.get("chat", {})
            chat_context = OrchestratorChatContext(
                server_url=chat_config.get("server_url", "ws://localhost:8765"),
                username=chat_config.get("username", "Fifth-Symphony"),
            )

        try:
            # YubiKey authentication (first startup only)
            yubikey_config = self.config.get("security", {}).get("yubikey", {})
            if yubikey_config.get("enabled", False):
                yubikey_auth = YubiKeyAuth(
                    session_duration_hours=yubikey_config.get("session_duration_hours", 24)
                )
                try:
                    await yubikey_auth.require_yubikey_tap("fifth-symphony-orchestrator")
                    self.console.print("[green]🔐 YubiKey authentication successful[/green]")
                except PermissionError as e:
                    self.console.print(f"[red]🔐 YubiKey authentication failed: {e}[/red]")
                    return

            # Connect to chat if enabled
            if chat_context:
                async with chat_context as chat_client:
                    self.chat_client = chat_client

                    # Initialize 1Password session if needed
                    if self.config.get("onepassword", {}).get("vault"):
                        await self.op_manager.initialize_session()

                    await self._run_main_logic(args)
            else:
                # Initialize 1Password session if needed
                if self.config.get("onepassword", {}).get("vault"):
                    await self.op_manager.initialize_session()

                await self._run_main_logic(args)

        except KeyboardInterrupt:
            self.console.print("\n[yellow]Neural Orchestra interrupted[/yellow]")
            await self.voice_handler.speak("Neural Orchestra interrupted")
        except Exception as e:
            await self.voice_handler.speak(
                f"Fatal error: {self.output_translator.simplify_error(str(e))}", priority="high"
            )
        finally:
            # Cleanup
            await self.voice_handler.cleanup()
            for task in self.running_scripts.values():
                task.cancel()

    async def _run_main_logic(self, args):
        """Execute main orchestrator logic"""
        # Handle symlink operations
        if args.add_symlink:
            success, message = self.symlink_manager.add_symlink(
                args.add_symlink, args.symlink_alias
            )
            if success:
                self.console.print(f"[green]{message}[/green]")
            else:
                self.console.print(f"[red]{message}[/red]")
            return

        if args.list_symlinks:
            symlinks = self.symlink_manager.list_symlinks()
            if symlinks:
                table = Table(
                    title="Configured Symlinks", show_header=True, header_style="bold cyan"
                )
                table.add_column("Name", style="green")
                table.add_column("Target", style="yellow")
                table.add_column("Status", style="blue")

                for link in symlinks:
                    status = "✅ Valid" if link["valid"] else "❌ Broken"
                    table.add_row(link["name"], link.get("target", "Unknown"), status)

                self.console.print(table)
            else:
                self.console.print("[yellow]No symlinks configured[/yellow]")
            return

        if args.sequence:
            await self.run_orchestration_sequence(args.sequence)
        elif args.script:
            # Try to find script in various locations
            script_path = None

            # Check scripts directory
            for attempt in [
                self.scripts_path / f"{args.script}.py",
                self.scripts_path / args.script,
            ]:
                if attempt.exists():
                    script_path = attempt
                    break

            # If not found, check symlinks directory
            if not script_path:
                for attempt in [
                    self.symlinks_path / args.script,
                    self.symlinks_path / f"{args.script}.py",
                    self.symlinks_path / f"{args.script}.sh",
                    self.symlinks_path / f"{args.script}.bash",
                ]:
                    if attempt.exists():
                        script_path = attempt
                        break

            if script_path:
                await self.run_script(script_path, args.args)
            else:
                self.console.print(f"[red]Script not found: {args.script}[/red]")
                await self.voice_handler.speak(f"Script {args.script} not found")
        else:
            await self.interactive_mode()


if __name__ == "__main__":
    orchestra = NeuralOrchestra()
    asyncio.run(orchestra.main())
