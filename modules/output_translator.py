"""
Output Translator Module
Converts technical output to conversational voice messages
"""

import logging
import re
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class OutputTranslator:
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.enabled = config.get("technical_to_voice", True)
        self.simplify_errors = config.get("simplify_errors", True)

        # Load translation templates
        self.templates = self._load_templates()

        # Patterns to detect significant events
        self.event_patterns = {
            "error": [
                r"error:",
                r"exception:",
                r"failed:",
                r"failure:",
                r"traceback",
                r"errno",
                r"fatal:",
                r"critical:",
            ],
            "warning": [r"warning:", r"warn:", r"deprecated:", r"caution:"],
            "success": [
                r"success",
                r"completed",
                r"finished",
                r"done",
                r"ready",
                r"initialized",
                r"started",
            ],
            "progress": [
                r"\d+%",
                r"step \d+",
                r"processing",
                r"downloading",
                r"installing",
                r"building",
                r"compiling",
            ],
            "waiting": [
                r"waiting",
                r"please enter",
                r"input required",
                r"press any key",
                r"continue\?",
            ],
        }

        # Technical terms to simplify
        self.technical_terms = {
            "subprocess": "process",
            "exception": "error",
            "traceback": "error details",
            "errno": "error number",
            "pid": "process ID",
            "stdin": "input",
            "stdout": "output",
            "stderr": "error output",
            "argv": "arguments",
            "kwargs": "keyword arguments",
            "regex": "pattern",
            "boolean": "true or false value",
            "integer": "number",
            "float": "decimal number",
            "dict": "dictionary",
            "tuple": "group of values",
            "lambda": "small function",
            "decorator": "function modifier",
            "async": "asynchronous",
            "await": "wait for",
            "coroutine": "async function",
            "mutex": "lock",
            "semaphore": "counter lock",
            "deadlock": "stuck processes",
            "segfault": "memory error",
            "nullptr": "missing value",
            "undefined": "not set",
            "null": "empty",
            "nan": "not a number",
            "inf": "infinity",
        }

        # Error code translations
        self.error_codes = {
            "404": "not found",
            "403": "access denied",
            "401": "authentication required",
            "500": "server error",
            "503": "service unavailable",
            "ENOENT": "file not found",
            "EACCES": "permission denied",
            "EEXIST": "already exists",
            "ETIMEDOUT": "timed out",
            "ECONNREFUSED": "connection refused",
        }

    def _load_templates(self) -> dict[str, dict]:
        """Load translation templates from config"""
        templates_file = (
            Path(__file__).parent.parent / "config" / "templates" / "output_formats.yaml"
        )

        if templates_file.exists():
            with open(templates_file, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}

        # Default templates
        return {
            "error": {
                "generic": "An error occurred: {message}",
                "file_not_found": "Could not find the file {filename}",
                "permission_denied": "Permission denied for {action}",
                "connection_failed": "Could not connect to {target}",
                "timeout": "Operation timed out after {duration} seconds",
            },
            "success": {
                "generic": "Operation completed successfully",
                "file_created": "Created {filename}",
                "download_complete": "Download finished",
                "installation_complete": "Installation complete",
            },
            "progress": {
                "percentage": "Progress: {percent} percent complete",
                "step": "Working on step {current} of {total}",
                "downloading": "Downloading {item}",
                "processing": "Processing {item}",
            },
        }

    async def translate_for_voice(self, text: str) -> str | None:
        """Translate technical output to voice-friendly message"""
        if not self.enabled or not text.strip():
            return None

        # Detect event type
        event_type = self._detect_event_type(text)

        if not event_type:
            # Check if it's significant enough to voice
            if len(text) < 10 or text.count("\n") > 3:
                return None

        # Simplify the message
        simplified = self._simplify_message(text)

        # Apply template if available
        if event_type and event_type in self.templates:
            simplified = self._apply_template(event_type, simplified)

        # Only return if message is meaningful
        if simplified and len(simplified) > 5:
            return simplified

        return None

    def _detect_event_type(self, text: str) -> str | None:
        """Detect the type of event from output text"""
        text_lower = text.lower()

        for event_type, patterns in self.event_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return event_type

        return None

    def _simplify_message(self, text: str) -> str:
        """Simplify technical jargon in message"""
        simplified = text

        # Remove file paths but keep filename
        simplified = re.sub(r"(/[\w/.-]+/)([\w.-]+)", r"\2", simplified)

        # Remove memory addresses
        simplified = re.sub(r"0x[0-9a-fA-F]+", "", simplified)

        # Remove stack trace details
        if "Traceback" in simplified:
            # Just keep the actual error message
            lines = simplified.split("\n")
            for i, line in enumerate(lines):
                if "Error:" in line or "Exception:" in line:
                    simplified = line
                    break

        # Replace technical terms
        for tech_term, simple_term in self.technical_terms.items():
            pattern = r"\b" + re.escape(tech_term) + r"\b"
            simplified = re.sub(pattern, simple_term, simplified, flags=re.IGNORECASE)

        # Replace error codes
        for code, meaning in self.error_codes.items():
            if code in simplified:
                simplified = simplified.replace(code, f"{code} ({meaning})")

        # Remove excessive whitespace
        simplified = " ".join(simplified.split())

        # Limit length for voice
        if len(simplified) > 200:
            simplified = simplified[:197] + "..."

        return simplified

    def simplify_error(self, error_message: str) -> str:
        """Simplify an error message for voice output"""
        if not self.simplify_errors:
            return error_message

        simplified = error_message

        # Common Python errors
        error_translations = {
            "FileNotFoundError": "File not found",
            "PermissionError": "Permission denied",
            "ConnectionError": "Connection failed",
            "TimeoutError": "Operation timed out",
            "ValueError": "Invalid value",
            "TypeError": "Wrong type of value",
            "KeyError": "Missing key",
            "IndexError": "Index out of range",
            "AttributeError": "Missing attribute",
            "ImportError": "Import failed",
            "ModuleNotFoundError": "Module not found",
            "SyntaxError": "Syntax error",
            "IndentationError": "Indentation error",
            "NameError": "Name not defined",
            "ZeroDivisionError": "Division by zero",
            "MemoryError": "Out of memory",
            "KeyboardInterrupt": "Interrupted by user",
            "SystemExit": "System exit",
            "OSError": "Operating system error",
        }

        for error_type, simple_desc in error_translations.items():
            if error_type in simplified:
                # Extract the actual error message
                match = re.search(f"{error_type}:\\s*(.+)", simplified)
                if match:
                    details = match.group(1)
                    simplified = f"{simple_desc}: {self._simplify_message(details)}"
                else:
                    simplified = simple_desc
                break

        return self._simplify_message(simplified)

    def _apply_template(self, event_type: str, message: str) -> str:
        """Apply a template to format the message"""
        if event_type not in self.templates:
            return message

        templates = self.templates[event_type]

        # Try to extract relevant information
        context = self._extract_context(message)

        # Find best matching template
        for template_key, template in templates.items():
            if template_key == "generic":
                continue

            # Check if this template is applicable
            if template_key in message.lower():
                try:
                    return template.format(**context, message=message)
                except KeyError:
                    pass

        # Use generic template
        if "generic" in templates:
            try:
                return templates["generic"].format(**context, message=message)
            except KeyError:
                pass

        return message

    def _extract_context(self, message: str) -> dict[str, str]:
        """Extract contextual information from message"""
        context = {}

        # Extract filename
        file_match = re.search(r"[\w.-]+\.\w+", message)
        if file_match:
            context["filename"] = file_match.group()

        # Extract percentage
        percent_match = re.search(r"(\d+)%", message)
        if percent_match:
            context["percent"] = percent_match.group(1)

        # Extract numbers for step counting
        step_match = re.search(r"step\s+(\d+)\s+of\s+(\d+)", message, re.IGNORECASE)
        if step_match:
            context["current"] = step_match.group(1)
            context["total"] = step_match.group(2)

        # Extract duration
        duration_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:seconds?|secs?|s)", message)
        if duration_match:
            context["duration"] = duration_match.group(1)

        # Extract action words
        action_words = ["downloading", "installing", "processing", "building", "compiling"]
        for action in action_words:
            if action in message.lower():
                context["action"] = action
                break

        return context

    def should_voice_output(self, output: str) -> bool:
        """Determine if output is significant enough for voice"""
        if not output.strip():
            return False

        # Don't voice single characters or very short outputs
        if len(output.strip()) < 5:
            return False

        # Don't voice outputs with too many lines (like tables or lists)
        if output.count("\n") > 5:
            return False

        # Don't voice progress bars or spinners
        if any(char in output for char in ["|", "/", "-", "\\", "█", "░", "▓"]):
            return False

        # Check for significant events
        event_type = self._detect_event_type(output)
        if event_type in ["error", "warning", "success", "waiting"]:
            return True

        # Check for completion indicators
        completion_words = ["complete", "done", "finished", "ready", "failed", "error"]
        if any(word in output.lower() for word in completion_words):
            return True

        return False

    def format_for_voice(self, data: Any, data_type: str = "generic") -> str:
        """Format various data types for voice output"""
        if data_type == "list":
            if isinstance(data, list):
                if len(data) == 0:
                    return "Empty list"
                if len(data) == 1:
                    return f"One item: {data[0]}"
                if len(data) <= 3:
                    return f"{len(data)} items: " + ", ".join(str(item) for item in data)
                return f"{len(data)} items, starting with {data[0]}"

        elif data_type == "dict":
            if isinstance(data, dict):
                if not data:
                    return "Empty dictionary"
                if len(data) == 1:
                    key, value = list(data.items())[0]
                    return f"One entry: {key} is {value}"
                return f"Dictionary with {len(data)} entries"

        elif data_type == "number":
            if isinstance(data, int | float):
                if data > 1000000:
                    return f"{data / 1000000:.1f} million"
                if data > 1000:
                    return f"{data / 1000:.1f} thousand"
                return str(data)

        elif data_type == "boolean":
            return "yes" if data else "no"

        elif data_type == "path":
            if isinstance(data, str | Path):
                path = Path(data)
                return f"File {path.name} in {path.parent.name}"

        return str(data)
