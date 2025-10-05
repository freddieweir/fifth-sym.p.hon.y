"""
Secure Prompt Manager

Stores orchestrator prompts in 1Password for runtime injection.
Zero plaintext prompts in code or config files.
"""

import logging
import subprocess
from typing import Dict, Any, Optional
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class PromptTemplate:
    """Represents a prompt template from 1Password"""
    name: str
    category: str  # permission_request, risk_warning, approval_response, etc.
    template: str
    voice_enabled: bool = True


class PromptManager:
    """
    Manages secure prompt storage and retrieval via 1Password CLI.

    All prompts are stored in 1Password vault and injected at runtime.
    No prompts are hardcoded in source code or config files.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize prompt manager.

        Args:
            config: Configuration with 1Password settings
        """
        self.config = config
        self.vault = config.get("onepassword_vault", "Development")
        self.cache: Dict[str, str] = {}
        self.logger = logging.getLogger(__name__)

        # 1Password item names for different prompt categories
        self.prompt_items = {
            "permission_request": "Fifth Symphony Prompts - Permission Requests",
            "risk_warning": "Fifth Symphony Prompts - Risk Warnings",
            "approval_response": "Fifth Symphony Prompts - Approval Responses",
            "error_handling": "Fifth Symphony Prompts - Error Handling",
            "system_status": "Fifth Symphony Prompts - System Status",
        }

    async def get_prompt(
        self,
        category: str,
        prompt_key: str,
        **format_args
    ) -> str:
        """
        Retrieve and format a prompt from 1Password.

        Args:
            category: Prompt category (permission_request, risk_warning, etc.)
            prompt_key: Specific prompt key within category
            **format_args: Variables to format into the prompt template

        Returns:
            Formatted prompt string

        Example:
            >>> prompt = await manager.get_prompt(
            ...     "permission_request",
            ...     "file_deletion",
            ...     path="/etc/passwd",
            ...     risk_level="CRITICAL"
            ... )
        """
        try:
            # Get prompt template from 1Password
            template = await self._fetch_prompt_template(category, prompt_key)

            # Format with provided arguments
            formatted_prompt = template.format(**format_args)

            self.logger.debug(f"Retrieved prompt: {category}/{prompt_key}")
            return formatted_prompt

        except Exception as e:
            self.logger.error(f"Failed to get prompt {category}/{prompt_key}: {e}")
            # Fallback to generic prompt
            return self._get_fallback_prompt(category, prompt_key, **format_args)

    async def _fetch_prompt_template(self, category: str, prompt_key: str) -> str:
        """
        Fetch prompt template from 1Password.

        Args:
            category: Prompt category
            prompt_key: Specific prompt key

        Returns:
            Template string
        """
        cache_key = f"{category}/{prompt_key}"

        # Check cache first
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Get 1Password item name
        item_name = self.prompt_items.get(category)
        if not item_name:
            raise ValueError(f"Unknown prompt category: {category}")

        try:
            # Retrieve from 1Password
            # Prompts are stored as JSON in a single secure note per category
            result = subprocess.run(
                [
                    "op", "item", "get",
                    item_name,
                    "--vault", self.vault,
                    "--format", "json"
                ],
                capture_output=True,
                text=True,
                check=True
            )

            item_data = json.loads(result.stdout)

            # Extract prompts from secure note
            # Structure: {"fields": [{"label": "notesPlain", "value": "{...}"}]}
            notes = None
            for field in item_data.get("fields", []):
                if field.get("label") == "notesPlain":
                    notes = field.get("value")
                    break

            if not notes:
                raise ValueError(f"No notes found in 1Password item: {item_name}")

            # Parse JSON from notes
            prompts = json.loads(notes)

            # Get specific prompt
            template = prompts.get(prompt_key)
            if not template:
                raise KeyError(f"Prompt key not found: {prompt_key}")

            # Cache for future use
            self.cache[cache_key] = template

            return template

        except subprocess.CalledProcessError as e:
            self.logger.error(f"1Password CLI error: {e.stderr}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse 1Password JSON: {e}")
            raise

    def _get_fallback_prompt(self, category: str, prompt_key: str, **format_args) -> str:
        """
        Get fallback prompt when 1Password retrieval fails.

        Args:
            category: Prompt category
            prompt_key: Prompt key
            **format_args: Format arguments

        Returns:
            Generic fallback prompt
        """
        fallbacks = {
            "permission_request": "Permission requested: {action}. Risk level: {risk_level}. Approve?",
            "risk_warning": "WARNING: {action} is a {risk_level} risk operation.",
            "approval_response": "Request {status}.",
            "error_handling": "Error: {error_message}",
            "system_status": "System status: {status}",
        }

        template = fallbacks.get(category, "Unknown prompt: {category}/{prompt_key}")
        return template.format(category=category, prompt_key=prompt_key, **format_args)

    async def list_available_prompts(self, category: Optional[str] = None) -> Dict[str, list]:
        """
        List all available prompts from 1Password.

        Args:
            category: Optional category filter

        Returns:
            Dictionary of category -> list of prompt keys
        """
        categories = [category] if category else self.prompt_items.keys()
        result = {}

        for cat in categories:
            try:
                item_name = self.prompt_items[cat]
                prompts = await self._fetch_all_prompts_in_category(item_name)
                result[cat] = list(prompts.keys())
            except Exception as e:
                self.logger.error(f"Failed to list prompts for {cat}: {e}")
                result[cat] = []

        return result

    async def _fetch_all_prompts_in_category(self, item_name: str) -> Dict[str, str]:
        """
        Fetch all prompts in a category from 1Password.

        Args:
            item_name: 1Password item name

        Returns:
            Dictionary of prompt_key -> template
        """
        result = subprocess.run(
            ["op", "item", "get", item_name, "--vault", self.vault, "--format", "json"],
            capture_output=True,
            text=True,
            check=True
        )

        item_data = json.loads(result.stdout)

        for field in item_data.get("fields", []):
            if field.get("label") == "notesPlain":
                return json.loads(field.get("value", "{}"))

        return {}


# Example 1Password Secure Note Structure
"""
1Password Item: "Fifth Symphony Prompts - Permission Requests"
Type: Secure Note
Vault: Development

Notes (JSON):
{
  "file_deletion": "Permission requested: Delete {path}. This is a {risk_level} risk operation. The file contains {file_type} data. Approve deletion?",

  "git_push_force": "CRITICAL: Force push to {branch} on {remote}. This will rewrite history and may cause data loss. Are you absolutely sure?",

  "system_modification": "{agent} requests permission to modify system files in {directory}. Risk level: {risk_level}. This could affect system stability. Approve?",

  "network_operation": "Network operation requested: {action} to {destination}. This will expose data over the network. Risk level: {risk_level}. Proceed?",

  "generic": "{agent} requests permission: {action}. Risk level: {risk_level}. Approve?"
}
"""

# Example Usage:
"""
# In orchestrator code:
prompt_manager = PromptManager(config)

# Get specific permission prompt
prompt = await prompt_manager.get_prompt(
    "permission_request",
    "file_deletion",
    path="/etc/passwd",
    risk_level="CRITICAL",
    file_type="system credentials"
)
# Returns: "Permission requested: Delete /etc/passwd. This is a CRITICAL risk
#           operation. The file contains system credentials data. Approve deletion?"

# Speak the prompt via ElevenLabs MCP
await mcp_client.speak(prompt)

# Show in TUI
await tui.display_permission_request(prompt)
"""
