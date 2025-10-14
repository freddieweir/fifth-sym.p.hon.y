"""
1Password CLI Integration Module
Manages secure credential retrieval via 1Password CLI
"""

import json
import logging
import os
import subprocess
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)


class OnePasswordManager:
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.vault = config.get("vault", "Private")
        self.signin_account = config.get("signin_account")
        self.session_token = None
        self.session_expiry = None

        # Cache for retrieved items
        self._cache = {}
        self._cache_ttl = timedelta(minutes=5)

    def _run_op_command(self, args: list, capture_output: bool = True) -> str | None:
        """Run a 1Password CLI command"""
        try:
            env = os.environ.copy()

            # Try to use service account token first (for restricted vaults like "Prompts")
            if not self.session_token and "OP_SERVICE_ACCOUNT_TOKEN" not in env:
                # Attempt to retrieve service account token from 1Password
                try:
                    sa_token_result = subprocess.run(
                        ["op", "item", "get", "Service Account Auth Token: albedo",
                         "--vault", "API", "--fields", "credential", "--reveal"],
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=5
                    )
                    if sa_token_result.returncode == 0 and sa_token_result.stdout.strip():
                        env["OP_SERVICE_ACCOUNT_TOKEN"] = sa_token_result.stdout.strip()
                        logger.debug("Using service account token for 1Password access")
                except Exception as e:
                    logger.debug(f"Could not retrieve service account token: {e}")

            if self.session_token:
                env["OP_SESSION"] = self.session_token

            result = subprocess.run(
                ["op"] + args, capture_output=capture_output, text=True, env=env, check=True
            )

            if capture_output:
                return result.stdout.strip()
            return None

        except subprocess.CalledProcessError as e:
            logger.error(f"1Password CLI error: {e.stderr}")
            if "session expired" in e.stderr.lower():
                self.session_token = None
                self.session_expiry = None
            return None
        except FileNotFoundError:
            logger.error(
                "1Password CLI not found. Please install: brew install --cask 1password-cli"
            )
            return None

    async def initialize_session(self) -> bool:
        """Initialize or refresh 1Password session"""
        if self.session_token and self.session_expiry and datetime.now() < self.session_expiry:
            return True

        # Try to sign in
        args = ["signin"]
        if self.signin_account:
            args.extend(["--account", self.signin_account])
        args.append("--raw")

        # First check if already signed in
        whoami_result = self._run_op_command(["whoami"])
        if whoami_result:
            logger.info("Already signed in to 1Password")
            return True

        # Sign in if needed
        logger.info("Signing in to 1Password...")
        result = self._run_op_command(args)

        if result:
            self.session_token = result
            self.session_expiry = datetime.now() + timedelta(hours=1)
            return True

        # Try biometric unlock if available
        logger.info("Attempting biometric unlock...")
        result = self._run_op_command(["signin", "--raw"])
        if result:
            self.session_token = result
            self.session_expiry = datetime.now() + timedelta(hours=1)
            return True

        return False

    @lru_cache(maxsize=128)
    def get_item(
        self, item_name: str, field: str = "credential", vault: str | None = None
    ) -> str | None:
        """Get a specific field from a 1Password item"""
        vault_name = vault or self.vault
        cache_key = f"{vault_name}:{item_name}:{field}"

        # Check cache
        if cache_key in self._cache:
            cached_time, cached_value = self._cache[cache_key]
            if datetime.now() - cached_time < self._cache_ttl:
                return cached_value

        # Retrieve from 1Password
        args = ["item", "get", item_name]
        if vault_name:
            args.extend(["--vault", vault_name])
        args.extend(["--field", field, "--reveal"])

        result = self._run_op_command(args)

        if result:
            # Cache the result
            self._cache[cache_key] = (datetime.now(), result)
            return result

        return None

    def get_api_key(self, service_name: str) -> str | None:
        """Get an API key from 1Password"""
        # First check environment variable as fallback
        env_var = f"{service_name.upper().replace(' ', '_')}_API_KEY"
        if env_var in os.environ:
            return os.environ[env_var]

        # Try to get from 1Password
        return self.get_item(f"{service_name} API", "credential")

    def get_certificate(self, cert_name: str) -> dict[str, str] | None:
        """Get a certificate from 1Password"""
        cert_data = {}

        # Get certificate content
        cert_content = self.get_item(cert_name, "certificate")
        if cert_content:
            cert_data["certificate"] = cert_content

        # Get private key if available
        key_content = self.get_item(cert_name, "private_key")
        if key_content:
            cert_data["private_key"] = key_content

        return cert_data if cert_data else None

    def get_voice_config(self, voice_service: str = "Eleven Labs") -> dict[str, Any] | None:
        """Get voice service configuration from 1Password"""
        config = {}

        # Get API key
        api_key = self.get_api_key(voice_service)
        if api_key:
            config["api_key"] = api_key

        # Get voice ID if stored
        voice_id = self.get_item(f"{voice_service} Config", "voice_id")
        if voice_id:
            config["voice_id"] = voice_id

        # Get additional settings
        settings = self.get_item(f"{voice_service} Config", "settings")
        if settings:
            try:
                config["settings"] = json.loads(settings)
            except json.JSONDecodeError:
                pass

        return config if config else None

    def get_project_secrets(self, project_name: str) -> dict[str, str]:
        """Get all secrets for a specific project"""
        secrets = {}

        # Try to get a document with all project secrets
        project_doc = self._run_op_command(
            ["item", "get", f"{project_name} Secrets", "--vault", self.vault, "--format", "json"]
        )

        if project_doc:
            try:
                doc_data = json.loads(project_doc)
                # Extract all fields
                for field in doc_data.get("fields", []):
                    if field.get("value"):
                        secrets[field.get("label", field.get("id"))] = field["value"]
            except json.JSONDecodeError:
                pass

        return secrets

    def create_item(
        self, item_type: str, title: str, fields: dict[str, str], vault: str | None = None
    ) -> bool:
        """Create a new item in 1Password"""
        vault_name = vault or self.vault

        # Build field arguments
        field_args = []
        for key, value in fields.items():
            field_args.extend([f"{key}={value}"])

        args = ["item", "create", "--category", item_type, "--title", title, "--vault", vault_name]

        # Add fields
        for field_arg in field_args:
            args.extend(["--field", field_arg])

        result = self._run_op_command(args, capture_output=False)
        return result is not None

    def update_item_field(
        self, item_name: str, field: str, value: str, vault: str | None = None
    ) -> bool:
        """Update a specific field in a 1Password item"""
        vault_name = vault or self.vault

        args = ["item", "edit", item_name, "--vault", vault_name, f"{field}={value}"]

        result = self._run_op_command(args, capture_output=False)

        # Clear cache for this item
        cache_key = f"{vault_name}:{item_name}:{field}"
        if cache_key in self._cache:
            del self._cache[cache_key]

        return result is not None

    def list_items(self, category: str | None = None, vault: str | None = None) -> list:
        """List items in a vault"""
        vault_name = vault or self.vault

        args = ["item", "list", "--vault", vault_name, "--format", "json"]
        if category:
            args.extend(["--categories", category])

        result = self._run_op_command(args)

        if result:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return []

        return []

    def clear_cache(self):
        """Clear the credential cache"""
        self._cache.clear()
        self.get_item.cache_clear()

    async def cleanup(self):
        """Clean up session and cache"""
        self.clear_cache()
        if self.session_token:
            # Sign out if needed
            self._run_op_command(["signout"])
            self.session_token = None
            self.session_expiry = None
