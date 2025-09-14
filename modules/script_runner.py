"""
Script Runner Module
Manages execution and monitoring of Python scripts
"""

import asyncio
import importlib.util
import logging
import os
import re
import subprocess
import sys
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil

logger = logging.getLogger(__name__)


class ScriptRunner:
    def __init__(self, scripts_path: Path):
        self.scripts_path = scripts_path
        self.running_processes: dict[str, subprocess.Popen] = {}
        self.script_metadata: dict[str, dict] = {}

        # Patterns that indicate waiting for input
        self.input_patterns = [
            r"input\s*\(",
            r"Enter\s+",
            r"Please\s+",
            r"Type\s+",
            r"Press\s+",
            r"Waiting\s+for",
            r":\s*$",  # Ends with colon and whitespace
            r">\s*$",  # Ends with prompt
            r"Password:",
            r"Continue\?",
            r"Y/N",
            r"\[y/n\]",
            r"Select\s+",
            r"Choose\s+",
        ]

    def is_waiting_for_input(self, output: str) -> bool:
        """Detect if a script is waiting for user input"""
        if not output:
            return False

        # Check against patterns
        for pattern in self.input_patterns:
            if re.search(pattern, output, re.IGNORECASE):
                return True

        return False

    async def run_script_async(
        self, script_path: Path, args: list[str] | None = None
    ) -> AsyncIterator[tuple[str, str]]:
        """
        Run a Python or shell script asynchronously and yield output
        Yields tuples of (output_type, output_text)
        """
        script_name = script_path.stem

        # Build command based on script type
        if script_path.suffix in [".sh", ".bash"]:
            # For shell scripts, use bash or sh
            cmd = ["bash", str(script_path)]
        elif script_path.suffix == ".py":
            # For Python scripts
            cmd = [sys.executable, str(script_path)]
        else:
            # Try to execute directly (must have shebang)
            cmd = [str(script_path)]

        if args:
            cmd.extend(args)

        # Set up environment
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"  # Ensure unbuffered output

        logger.info(f"Starting script: {script_name} with args: {args}")

        try:
            # Start the process
            # Use the script's parent directory as working directory for relative paths
            working_dir = script_path.parent if script_path.is_absolute() else self.scripts_path

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE,
                env=env,
                cwd=str(working_dir),
            )

            # Track the process
            self.running_processes[script_name] = process

            # Create tasks for reading stdout and stderr
            async def read_stream(stream, stream_type):
                while True:
                    try:
                        line = await stream.readline()
                        if not line:
                            break
                        decoded = line.decode("utf-8", errors="replace")
                        yield (stream_type, decoded)
                    except Exception as e:
                        logger.error(f"Error reading {stream_type}: {e}")
                        break

            # Read both streams concurrently
            stdout_reader = read_stream(process.stdout, "stdout")
            stderr_reader = read_stream(process.stderr, "stderr")

            # Merge outputs from both streams
            async def merge_streams():
                tasks = [
                    asyncio.create_task(self._consume_stream(stdout_reader)),
                    asyncio.create_task(self._consume_stream(stderr_reader)),
                ]

                for task in asyncio.as_completed(tasks):
                    items = await task
                    for item in items:
                        yield item

            async for output_type, output in merge_streams():
                yield (output_type, output)

            # Wait for process to complete
            await process.wait()

            if process.returncode != 0:
                logger.warning(f"Script {script_name} exited with code {process.returncode}")
            else:
                logger.info(f"Script {script_name} completed successfully")

        except Exception as e:
            logger.error(f"Error running script {script_name}: {e}")
            yield ("stderr", f"Error: {e}\n")
        finally:
            # Remove from tracking
            if script_name in self.running_processes:
                del self.running_processes[script_name]

    async def _consume_stream(self, stream_generator):
        """Consume all items from a stream generator"""
        items = []
        async for item in stream_generator:
            items.append(item)
        return items

    def run_script_sync(
        self, script_path: Path, args: list[str] | None = None, timeout: int | None = None
    ) -> tuple[int, str, str]:
        """
        Run a Python or shell script synchronously
        Returns (return_code, stdout, stderr)
        """
        script_name = script_path.stem

        # Build command based on script type
        if script_path.suffix in [".sh", ".bash"]:
            # For shell scripts, use bash or sh
            cmd = ["bash", str(script_path)]
        elif script_path.suffix == ".py":
            # For Python scripts
            cmd = [sys.executable, str(script_path)]
        else:
            # Try to execute directly (must have shebang)
            cmd = [str(script_path)]

        if args:
            cmd.extend(args)

        logger.info(f"Running script synchronously: {script_name}")

        try:
            # Use the script's parent directory as working directory for relative paths
            working_dir = script_path.parent if script_path.is_absolute() else self.scripts_path

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=os.environ,
                cwd=str(working_dir),
            )

            return (result.returncode, result.stdout, result.stderr)

        except subprocess.TimeoutExpired:
            logger.error(f"Script {script_name} timed out after {timeout} seconds")
            return (-1, "", f"Script timed out after {timeout} seconds")
        except Exception as e:
            logger.error(f"Error running script {script_name}: {e}")
            return (-1, "", str(e))

    def import_script_as_module(self, script_path: Path) -> Any | None:
        """Import a Python script as a module"""
        try:
            spec = importlib.util.spec_from_file_location(script_path.stem, script_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[script_path.stem] = module
                spec.loader.exec_module(module)
                return module
            return None
        except Exception as e:
            logger.error(f"Failed to import {script_path}: {e}")
            return None

    def analyze_script(self, script_path: Path) -> dict[str, Any]:
        """Analyze a script to extract metadata"""
        metadata = {
            "name": script_path.stem,
            "path": str(script_path),
            "size": script_path.stat().st_size,
            "modified": datetime.fromtimestamp(script_path.stat().st_mtime),
            "has_main": False,
            "imports": [],
            "functions": [],
            "classes": [],
            "docstring": None,
            "requirements": [],
        }

        try:
            with open(script_path, encoding="utf-8") as f:
                content = f.read()

                # Check for main block
                if "__main__" in content:
                    metadata["has_main"] = True

                # Extract imports
                import_pattern = r"^(?:from\s+(\S+)\s+)?import\s+(.+)$"
                for match in re.finditer(import_pattern, content, re.MULTILINE):
                    if match.group(1):
                        metadata["imports"].append(match.group(1))
                    else:
                        imports = match.group(2).split(",")
                        metadata["imports"].extend([imp.strip() for imp in imports])

                # Extract function definitions
                func_pattern = r"^def\s+(\w+)\s*\("
                metadata["functions"] = re.findall(func_pattern, content, re.MULTILINE)

                # Extract class definitions
                class_pattern = r"^class\s+(\w+)\s*[\(:]"
                metadata["classes"] = re.findall(class_pattern, content, re.MULTILINE)

                # Extract docstring
                docstring_match = re.search(r'^"""(.+?)"""', content, re.DOTALL)
                if docstring_match:
                    metadata["docstring"] = docstring_match.group(1).strip()
                else:
                    docstring_match = re.search(r"^'''(.+?)'''", content, re.DOTALL)
                    if docstring_match:
                        metadata["docstring"] = docstring_match.group(1).strip()

                # Cache metadata
                self.script_metadata[script_path.stem] = metadata

        except Exception as e:
            logger.error(f"Failed to analyze script {script_path}: {e}")

        return metadata

    async def stop_script(self, script_name: str) -> bool:
        """Stop a running script"""
        if script_name in self.running_processes:
            process = self.running_processes[script_name]
            try:
                # Try graceful termination first
                process.terminate()
                await asyncio.sleep(2)

                # Force kill if still running
                if process.returncode is None:
                    process.kill()
                    await process.wait()

                logger.info(f"Stopped script: {script_name}")
                return True

            except Exception as e:
                logger.error(f"Error stopping script {script_name}: {e}")

        return False

    async def stop_all_scripts(self):
        """Stop all running scripts"""
        tasks = []
        for script_name in list(self.running_processes.keys()):
            tasks.append(self.stop_script(script_name))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def get_running_scripts(self) -> list[str]:
        """Get list of currently running scripts"""
        return list(self.running_processes.keys())

    def is_script_running(self, script_name: str) -> bool:
        """Check if a script is currently running"""
        return script_name in self.running_processes

    async def send_input_to_script(self, script_name: str, input_text: str) -> bool:
        """Send input to a running script"""
        if script_name in self.running_processes:
            process = self.running_processes[script_name]
            try:
                if process.stdin:
                    process.stdin.write((input_text + "\n").encode())
                    await process.stdin.drain()
                    return True
            except Exception as e:
                logger.error(f"Error sending input to {script_name}: {e}")

        return False

    def validate_script(self, script_path: Path) -> tuple[bool, str | None]:
        """Validate a Python script for basic syntax errors"""
        try:
            with open(script_path, encoding="utf-8") as f:
                code = f.read()

            # Try to compile the code
            compile(code, str(script_path), "exec")
            return (True, None)

        except SyntaxError as e:
            return (False, f"Syntax error at line {e.lineno}: {e.msg}")
        except Exception as e:
            return (False, str(e))

    async def run_script_with_monitoring(
        self, script_path: Path, args: list[str] | None = None, callback=None
    ) -> dict[str, Any]:
        """
        Run a script with detailed monitoring
        Calls callback function with updates
        """
        script_name = script_path.stem
        start_time = datetime.now()

        result = {
            "script": script_name,
            "start_time": start_time,
            "end_time": None,
            "duration": None,
            "return_code": None,
            "output": [],
            "errors": [],
            "memory_peak": 0,
            "cpu_percent": [],
        }

        # Start monitoring task
        monitor_task = asyncio.create_task(self._monitor_process(script_name, result))

        try:
            async for output_type, output in self.run_script_async(script_path, args):
                if output_type == "stdout":
                    result["output"].append(output)
                else:
                    result["errors"].append(output)

                if callback:
                    await callback(script_name, output_type, output)

        finally:
            monitor_task.cancel()
            result["end_time"] = datetime.now()
            result["duration"] = (result["end_time"] - start_time).total_seconds()

        return result

    async def _monitor_process(self, script_name: str, result: dict):
        """Monitor a running process for resource usage"""
        while script_name in self.running_processes:
            process = self.running_processes[script_name]
            try:
                # Get process info using psutil
                if hasattr(process, "pid"):
                    proc = psutil.Process(process.pid)

                    # Memory usage
                    memory_info = proc.memory_info()
                    if memory_info.rss > result["memory_peak"]:
                        result["memory_peak"] = memory_info.rss

                    # CPU usage
                    cpu = proc.cpu_percent(interval=1)
                    result["cpu_percent"].append(cpu)

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            await asyncio.sleep(1)
