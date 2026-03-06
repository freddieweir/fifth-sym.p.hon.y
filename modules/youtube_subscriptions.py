"""
YouTube Subscriptions → Glance Integration

Fetches YouTube subscriptions, auto-categorizes by topic, and generates
native Glance videos widget configuration.

Usage:
    youtube-subs auth      # One-time OAuth flow
    youtube-subs fetch     # Fetch subscriptions
    youtube-subs generate  # Generate Glance config
    youtube-subs sync      # Full pipeline
"""

import json
import logging
import os
import sqlite3
import subprocess
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests
import typer
import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .youtube_models import (
    CategoryDefinition,
    CategoryGroup,
    Channel,
    GlanceColumn,
    GlancePage,
    GlanceVideoWidget,
    InvidiousSyncResult,
    SyncStats,
)

logger = logging.getLogger(__name__)
console = Console()

# Typer app for CLI
app = typer.Typer(
    name="youtube-subs",
    help="YouTube Subscriptions → Glance Dashboard Integration",
    add_completion=False,
)


def get_config_path() -> Path:
    """Get path to YouTube config directory."""
    # Check if we're in fifth-symphony or a parent repo
    current = Path.cwd()
    for _ in range(5):  # Look up to 5 levels
        config_path = current / "config" / "youtube"
        if config_path.exists():
            return config_path
        # Check if this is fifth-symphony itself
        if (current / "modules" / "youtube_subscriptions.py").exists():
            return current / "config" / "youtube"
        current = current.parent

    # Fallback to fifth-symphony location
    return Path(__file__).parent.parent / "config" / "youtube"


def load_settings() -> dict[str, Any]:
    """Load settings from config/youtube/settings.yaml."""
    config_path = get_config_path() / "settings.yaml"
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def load_overrides() -> dict[str, Any]:
    """Load overrides from config/youtube/overrides.yaml."""
    config_path = get_config_path() / "overrides.yaml"
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


class YouTubeAuth:
    """
    OAuth 2.0 authentication for YouTube Data API.

    Handles:
    - Loading credentials from 1Password
    - Running OAuth flow (opens browser)
    - Storing/refreshing tokens
    """

    SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

    def __init__(self, settings: dict[str, Any] | None = None):
        self.settings = settings or load_settings().get("youtube", {})
        self.credentials_item = os.environ.get(
            "YOUTUBE_OP_ITEM", self.settings.get("credentials_item", "YouTube API Credentials")
        )
        self.credentials_vault = os.environ.get(
            "YOUTUBE_OP_VAULT", self.settings.get("credentials_vault", "API")
        )
        self.token_path = Path(
            os.path.expanduser(self.settings.get("token_path", "~/.config/youtube-glance/token.json"))
        )
        self._credentials = None

    def _get_credentials_json(self) -> dict[str, Any] | None:
        """Retrieve OAuth credentials JSON from 1Password.

        Tries in order:
        1. File attachment on the item (via op item get --format json to find file ID,
           then op read to fetch it)
        2. Document type item (op document get)
        3. Field named 'credential' containing JSON
        """
        try:
            # Try to find a file attachment containing the OAuth JSON
            result = subprocess.run(
                [
                    "op", "item", "get", self.credentials_item,
                    "--vault", self.credentials_vault,
                    "--format", "json",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0 and result.stdout.strip():
                item_data = json.loads(result.stdout.strip())
                files = item_data.get("files", [])
                for f in files:
                    if f.get("name", "").endswith(".json"):
                        file_ref = f"op://{self.credentials_vault}/{self.credentials_item}/{f['id']}"
                        file_result = subprocess.run(
                            ["op", "read", file_ref],
                            capture_output=True,
                            text=True,
                            check=False,
                        )
                        if file_result.returncode == 0 and file_result.stdout.strip():
                            return json.loads(file_result.stdout.strip())

            # Fallback: try as a document type item
            result = subprocess.run(
                [
                    "op", "document", "get", self.credentials_item,
                    "--vault", self.credentials_vault,
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout.strip())

            logger.error(f"Failed to get credentials from 1Password: {result.stderr}")
            return None

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in credentials: {e}")
            return None
        except FileNotFoundError:
            logger.error("1Password CLI not found. Install: brew install --cask 1password-cli")
            return None

    def _load_cached_token(self) -> dict[str, Any] | None:
        """Load cached OAuth token from disk."""
        if self.token_path.exists():
            try:
                with open(self.token_path, encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return None

    def _save_token(self, token: dict[str, Any]) -> None:
        """Save OAuth token to disk."""
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.token_path, "w", encoding="utf-8") as f:
            json.dump(token, f, indent=2)

    def get_credentials(self):
        """
        Get valid OAuth credentials.

        Returns google.oauth2.credentials.Credentials or None.
        """
        if self._credentials and self._credentials.valid:
            return self._credentials

        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
        except ImportError:
            console.print("[red]Missing google-auth. Run: uv sync[/red]")
            return None

        # Try to load cached token
        token_data = self._load_cached_token()
        if token_data:
            self._credentials = Credentials(
                token=token_data.get("token"),
                refresh_token=token_data.get("refresh_token"),
                token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
                client_id=token_data.get("client_id"),
                client_secret=token_data.get("client_secret"),
                scopes=self.SCOPES,
            )

            # Refresh if expired
            if self._credentials.expired and self._credentials.refresh_token:
                try:
                    self._credentials.refresh(Request())
                    self._save_token({
                        "token": self._credentials.token,
                        "refresh_token": self._credentials.refresh_token,
                        "token_uri": self._credentials.token_uri,
                        "client_id": self._credentials.client_id,
                        "client_secret": self._credentials.client_secret,
                    })
                except Exception as e:
                    logger.warning(f"Token refresh failed: {e}")
                    self._credentials = None

        return self._credentials

    def run_oauth_flow(self) -> bool:
        """
        Run OAuth 2.0 flow (opens browser for user consent).

        Returns True if successful.
        """
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
        except ImportError:
            console.print("[red]Missing google-auth-oauthlib. Run: uv sync[/red]")
            return False

        # Get credentials JSON from 1Password
        creds_json = self._get_credentials_json()
        if not creds_json:
            console.print("[red]Could not retrieve credentials from 1Password.[/red]")
            console.print(f"Expected item: '{self.credentials_item}' in vault '{self.credentials_vault}'")
            return False

        # Write to temp file for the flow (google library requires file)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(creds_json, f)
            temp_creds_path = f.name

        try:
            console.print("[cyan]Opening browser for Google authentication...[/cyan]")
            console.print("[dim]Sign in with the Google account that has your YouTube subscriptions.[/dim]")

            flow = InstalledAppFlow.from_client_secrets_file(temp_creds_path, self.SCOPES)

            # Run local server for OAuth callback
            self._credentials = flow.run_local_server(port=8888)

            # Save token
            self._save_token({
                "token": self._credentials.token,
                "refresh_token": self._credentials.refresh_token,
                "token_uri": self._credentials.token_uri,
                "client_id": self._credentials.client_id,
                "client_secret": self._credentials.client_secret,
            })

            console.print("[green]✓ Authentication successful![/green]")
            return True

        except Exception as e:
            logger.error(f"OAuth flow failed: {e}")
            console.print(f"[red]OAuth flow failed: {e}[/red]")
            return False

        finally:
            # Clean up temp file
            Path(temp_creds_path).unlink(missing_ok=True)

    def is_authenticated(self) -> bool:
        """Check if we have valid credentials."""
        return self.get_credentials() is not None


class SubscriptionFetcher:
    """
    Fetches YouTube subscriptions using the Data API.

    Features:
    - Pagination for large subscription lists
    - Channel metadata (topics, subscriber count)
    - SQLite caching
    """

    def __init__(self, auth: YouTubeAuth, settings: dict[str, Any] | None = None):
        self.auth = auth
        self.settings = settings or load_settings().get("youtube", {})
        self.cache_path = Path(
            os.path.expanduser(self.settings.get("cache_path", "~/.config/youtube-glance/cache.db"))
        )
        self._service = None

    def _get_service(self):
        """Get YouTube API service."""
        if self._service:
            return self._service

        try:
            from googleapiclient.discovery import build
        except ImportError:
            console.print("[red]Missing google-api-python-client. Run: uv sync[/red]")
            return None

        credentials = self.auth.get_credentials()
        if not credentials:
            return None

        self._service = build("youtube", "v3", credentials=credentials)
        return self._service

    def _init_cache(self) -> sqlite3.Connection:
        """Initialize SQLite cache."""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.cache_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                channel_id TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                thumbnail_url TEXT,
                topic_ids TEXT,
                subscriber_count INTEGER,
                video_count INTEGER,
                last_video_date TEXT,
                subscribed_at TEXT,
                fetched_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()
        return conn

    def fetch_subscriptions(self, use_cache: bool = True) -> list[Channel]:
        """
        Fetch all subscriptions.

        Args:
            use_cache: If True, return cached data if fresh

        Returns:
            List of Channel objects
        """
        conn = self._init_cache()

        # Check cache freshness
        if use_cache:
            cursor = conn.execute("SELECT value FROM metadata WHERE key = 'last_fetched'")
            row = cursor.fetchone()
            if row:
                last_fetched = datetime.fromisoformat(row[0])
                cache_hours = self.settings.get("cache_duration_hours", 24)
                if datetime.now() - last_fetched < timedelta(hours=cache_hours):
                    console.print("[dim]Using cached subscriptions[/dim]")
                    return self._load_from_cache(conn)

        service = self._get_service()
        if not service:
            console.print("[red]Not authenticated. Run: youtube-subs auth[/red]")
            return []

        channels = []
        next_page_token = None

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Fetching subscriptions...", total=None)

            while True:
                try:
                    request = service.subscriptions().list(
                        part="snippet,contentDetails",
                        mine=True,
                        maxResults=50,
                        pageToken=next_page_token,
                    )
                    response = request.execute()

                    for item in response.get("items", []):
                        snippet = item.get("snippet", {})
                        resource_id = snippet.get("resourceId", {})

                        channel = Channel(
                            id=resource_id.get("channelId", ""),
                            title=snippet.get("title", ""),
                            description=snippet.get("description", ""),
                            thumbnail_url=snippet.get("thumbnails", {}).get("default", {}).get("url", ""),
                            subscribed_at=datetime.fromisoformat(
                                snippet.get("publishedAt", "").replace("Z", "+00:00")
                            ) if snippet.get("publishedAt") else None,
                        )
                        channels.append(channel)

                    progress.update(task, description=f"Fetched {len(channels)} subscriptions...")

                    next_page_token = response.get("nextPageToken")
                    if not next_page_token:
                        break

                except Exception as e:
                    logger.error(f"API error: {e}")
                    console.print(f"[red]API error: {e}[/red]")
                    break

        # Fetch channel details (topics, subscriber counts)
        if channels:
            channels = self._enrich_channel_data(service, channels, progress)

        # Save to cache
        self._save_to_cache(conn, channels)
        conn.close()

        console.print(f"[green]✓ Fetched {len(channels)} subscriptions[/green]")
        return channels

    def _enrich_channel_data(self, service, channels: list[Channel], progress) -> list[Channel]:
        """Fetch additional channel data (topics, stats)."""
        task = progress.add_task("Fetching channel details...", total=len(channels))

        # Batch requests (50 channels per request)
        for i in range(0, len(channels), 50):
            batch = channels[i:i + 50]
            channel_ids = [ch.id for ch in batch]

            try:
                request = service.channels().list(
                    part="snippet,statistics,topicDetails",
                    id=",".join(channel_ids),
                )
                response = request.execute()

                # Map response to channels
                channel_map = {ch.id: ch for ch in batch}
                for item in response.get("items", []):
                    ch = channel_map.get(item["id"])
                    if ch:
                        # Topic IDs
                        topic_details = item.get("topicDetails", {})
                        ch.topic_ids = topic_details.get("topicIds", [])

                        # Statistics
                        stats = item.get("statistics", {})
                        ch.subscriber_count = int(stats.get("subscriberCount", 0))
                        ch.video_count = int(stats.get("videoCount", 0))

                progress.update(task, advance=len(batch))

            except Exception as e:
                logger.warning(f"Failed to fetch channel details: {e}")

        return channels

    def _save_to_cache(self, conn: sqlite3.Connection, channels: list[Channel]) -> None:
        """Save channels to SQLite cache."""
        now = datetime.now().isoformat()

        conn.execute("DELETE FROM subscriptions")
        for ch in channels:
            conn.execute(
                """INSERT INTO subscriptions
                   (channel_id, title, description, thumbnail_url, topic_ids,
                    subscriber_count, video_count, last_video_date, subscribed_at, fetched_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    ch.id, ch.title, ch.description, ch.thumbnail_url,
                    json.dumps(ch.topic_ids), ch.subscriber_count, ch.video_count,
                    ch.last_video_date.isoformat() if ch.last_video_date else None,
                    ch.subscribed_at.isoformat() if ch.subscribed_at else None,
                    now,
                ),
            )

        conn.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES ('last_fetched', ?)",
            (now,),
        )
        conn.commit()

    def _load_from_cache(self, conn: sqlite3.Connection) -> list[Channel]:
        """Load channels from SQLite cache."""
        cursor = conn.execute("SELECT * FROM subscriptions")
        channels = []

        for row in cursor.fetchall():
            channels.append(Channel(
                id=row[0],
                title=row[1],
                description=row[2],
                thumbnail_url=row[3],
                topic_ids=json.loads(row[4]) if row[4] else [],
                subscriber_count=row[5],
                video_count=row[6],
                last_video_date=datetime.fromisoformat(row[7]) if row[7] else None,
                subscribed_at=datetime.fromisoformat(row[8]) if row[8] else None,
                fetched_at=datetime.fromisoformat(row[9]) if row[9] else datetime.now(),
            ))

        return channels


class CategoryMapper:
    """
    Maps channels to categories using hybrid approach.

    Priority:
    1. Manual overrides (from overrides.yaml)
    2. Auto-detection via YouTube topic IDs
    3. "Other" catch-all category
    """

    def __init__(self, settings: dict[str, Any] | None = None, overrides: dict[str, Any] | None = None):
        self.settings = settings or load_settings()
        self.overrides = overrides or load_overrides()

        # Build category definitions
        self.categories: dict[str, CategoryDefinition] = {}
        for name, cfg in self.settings.get("categories", {}).items():
            self.categories[name] = CategoryDefinition(
                name=name,
                emoji=cfg.get("emoji", "📺"),
                topic_ids=cfg.get("topic_ids", []),
                priority=cfg.get("priority", 50),
            )

        # Add custom categories from overrides
        for name, cfg in self.overrides.get("custom_categories", {}).items():
            self.categories[name] = CategoryDefinition(
                name=name,
                emoji=cfg.get("emoji", "📺"),
                topic_ids=cfg.get("topic_ids", []),
                priority=cfg.get("priority", 50),
            )

        # Build topic → category mapping
        self.topic_to_category: dict[str, str] = {}
        for cat_name, cat_def in self.categories.items():
            for topic_id in cat_def.topic_ids:
                self.topic_to_category[topic_id] = cat_name

        # Manual overrides
        self.channel_overrides: dict[str, str] = self.overrides.get("channel_overrides", {})
        self.excluded_channels: set[str] = set(self.overrides.get("excluded_channels", []))
        self.priority_channels: set[str] = set(self.overrides.get("priority_channels", []))

    def categorize(self, channel: Channel) -> str:
        """
        Determine category for a channel.

        Returns category name.
        """
        # Check manual override first
        if channel.id in self.channel_overrides:
            channel.is_override = True
            return self.channel_overrides[channel.id]

        # Auto-detect from topic IDs
        for topic_id in channel.topic_ids:
            if topic_id in self.topic_to_category:
                return self.topic_to_category[topic_id]

        # Fallback to "Other"
        return "Other"

    def categorize_all(self, channels: list[Channel]) -> list[CategoryGroup]:
        """
        Categorize all channels and return grouped results.

        Returns list of CategoryGroup sorted by priority.
        """
        # Filter excluded channels
        channels = [ch for ch in channels if ch.id not in self.excluded_channels]

        # Group by category
        groups: dict[str, list[Channel]] = {}
        for ch in channels:
            category = self.categorize(ch)
            ch.assigned_category = category

            if category not in groups:
                groups[category] = []
            groups[category].append(ch)

        # Build CategoryGroup objects
        result = []
        for cat_name, cat_channels in groups.items():
            cat_def = self.categories.get(cat_name, CategoryDefinition(name=cat_name))
            result.append(CategoryGroup(
                name=cat_name,
                emoji=cat_def.emoji,
                channels=cat_channels,
                priority=cat_def.priority,
            ))

        # Sort by priority
        result.sort(key=lambda g: g.priority)

        return result

    def apply_filtering(self, groups: list[CategoryGroup]) -> list[CategoryGroup]:
        """
        Apply filtering rules to category groups.

        - Max channels per category
        - Minimum subscriber count
        - Inactive channel filtering
        """
        filtering = self.settings.get("filtering", {})
        max_per_category = filtering.get("max_channels_per_category", 25)
        min_subscribers = filtering.get("min_subscriber_count", 1000)
        include_inactive = filtering.get("include_inactive_channels", False)
        inactive_days = filtering.get("inactive_threshold_days", 90)

        cutoff_date = datetime.now() - timedelta(days=inactive_days)

        for group in groups:
            filtered = []
            for ch in group.channels:
                # Priority channels always included
                if ch.id in self.priority_channels:
                    filtered.append(ch)
                    continue

                # Check subscriber count
                if ch.subscriber_count and ch.subscriber_count < min_subscribers:
                    continue

                # Check activity (if we have the data)
                if not include_inactive and ch.last_video_date:
                    if ch.last_video_date < cutoff_date:
                        continue

                filtered.append(ch)

            # Sort by subscriber count (highest first) and limit
            filtered.sort(key=lambda c: c.subscriber_count or 0, reverse=True)
            group.channels = filtered[:max_per_category]

        # Remove empty groups
        groups = [g for g in groups if g.channels]

        return groups


class GlanceConfigGenerator:
    """
    Generates native Glance YAML configuration.

    Outputs a page with videos widgets organized by category.
    """

    def __init__(self, settings: dict[str, Any] | None = None):
        self.settings = settings or load_settings()
        self.display = self.settings.get("display", {})
        self.output = self.settings.get("output", {})

    def generate(self, groups: list[CategoryGroup]) -> GlancePage:
        """
        Generate Glance page configuration.

        Args:
            groups: Categorized channel groups

        Returns:
            GlancePage object
        """
        videos_per_category = self.display.get("videos_per_category", 12)
        collapse_after = self.display.get("collapse_after", 4)
        grid_columns = self.display.get("grid_columns", 3)
        layout = self.display.get("layout", "two_column")

        page = GlancePage(name="YouTube")

        if layout == "two_column":
            # Split groups between two columns
            col1 = GlanceColumn(size="full")
            col2 = GlanceColumn(size="full")

            for i, group in enumerate(groups):
                widget = GlanceVideoWidget(
                    title=f"{group.emoji} {group.name}",
                    channels=group.channel_ids,
                    limit=videos_per_category,
                    collapse_after=collapse_after,
                    grid_columns=grid_columns,
                )

                if i % 2 == 0:
                    col1.widgets.append(widget)
                else:
                    col2.widgets.append(widget)

            page.columns = [col1, col2]

        else:  # single_column
            col = GlanceColumn(size="full")
            for group in groups:
                widget = GlanceVideoWidget(
                    title=f"{group.emoji} {group.name}",
                    channels=group.channel_ids,
                    limit=videos_per_category,
                    collapse_after=collapse_after,
                    grid_columns=grid_columns,
                )
                col.widgets.append(widget)

            page.columns = [col]

        return page

    def to_yaml(self, page: GlancePage, include_header: bool = True) -> str:
        """
        Convert GlancePage to YAML string.

        Args:
            page: GlancePage object
            include_header: Add generation metadata header

        Returns:
            YAML string ready for Glance
        """
        output = ""

        if include_header and self.output.get("include_timestamp", True):
            output += "# Auto-generated by youtube-subs - DO NOT EDIT MANUALLY\n"
            output += f"# Last updated: {datetime.now().isoformat()}\n"

            if self.output.get("include_summary", True):
                total_channels = sum(len(col.widgets) for col in page.columns for w in col.widgets for _ in w.channels)
                total_channels = sum(
                    len(w.channels)
                    for col in page.columns
                    for w in col.widgets
                )
                total_categories = sum(len(col.widgets) for col in page.columns)
                output += f"# Total channels: {total_channels} | Categories: {total_categories}\n"

            output += "\n"

        # Convert to YAML (as a single-item list for Glance pages array)
        page_dict = page.to_glance_dict()
        output += yaml.dump([page_dict], default_flow_style=False, allow_unicode=True, sort_keys=False)

        return output

    def save(self, page: GlancePage) -> Path:
        """
        Save generated config to file.

        Returns path to saved file.
        """
        output_path = self.output.get("glance_yaml_path", "generated/glance_youtube.yaml")

        # Resolve relative to config directory's parent
        if not os.path.isabs(output_path):
            base_path = get_config_path().parent
            output_path = base_path / output_path

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        yaml_content = self.to_yaml(page)
        output_path.write_text(yaml_content, encoding="utf-8")

        return output_path


class InvidiousClient:
    """
    Client for Invidious API subscription management.

    Handles:
    - Token retrieval from 1Password
    - Fetching current Invidious subscriptions
    - Subscribing to channels
    - Diff-based sync from YouTube subscriptions
    """

    def __init__(self, settings: dict[str, Any] | None = None):
        all_settings = settings or load_settings()
        self.settings = all_settings.get("invidious", {})
        self.base_url = os.environ.get(
            "INVIDIOUS_BASE_URL", self.settings.get("base_url", "")
        ).rstrip("/")
        self.token_op_item = os.environ.get(
            "INVIDIOUS_OP_ITEM", self.settings.get("token_op_item", "Invidious API Token")
        )
        self.token_op_vault = os.environ.get(
            "INVIDIOUS_OP_VAULT", self.settings.get("token_op_vault", "API")
        )
        self.token_op_field = os.environ.get(
            "INVIDIOUS_OP_FIELD", self.settings.get("token_op_field", "credential")
        )
        self.request_delay = self.settings.get("request_delay_seconds", 0.5)
        self.batch_size = self.settings.get("batch_size", 10)
        self.batch_pause = self.settings.get("batch_pause_seconds", 2)
        self._token: str | None = None

        # SSL verification: True, False, or path to CA cert
        verify_ssl = self.settings.get("verify_ssl", True)
        if isinstance(verify_ssl, str) and verify_ssl.lower() not in ("true", "false"):
            self.verify_ssl: bool | str = os.path.expanduser(verify_ssl)
        elif isinstance(verify_ssl, str):
            self.verify_ssl = verify_ssl.lower() == "true"
        else:
            self.verify_ssl = verify_ssl

        if not self.base_url:
            raise ValueError("invidious.base_url not configured in settings.yaml")

        # Suppress InsecureRequestWarning when verify_ssl is explicitly disabled
        if self.verify_ssl is False:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def _get_token(self) -> str:
        """Retrieve Invidious API token from 1Password."""
        if self._token:
            return self._token

        try:
            result = subprocess.run(
                [
                    "op", "item", "get", self.token_op_item,
                    "--vault", self.token_op_vault,
                    "--fields", self.token_op_field,
                    "--reveal",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"Failed to get Invidious token from 1Password: {result.stderr.strip()}"
                )

            token = result.stdout.strip()
            # 1Password returns JSON fields with CSV-style escaping:
            # outer wrapping quotes and doubled inner quotes ("" → ")
            if token.startswith('"') and token.endswith('"'):
                token = token[1:-1].replace('""', '"')
            self._token = token
            return self._token

        except FileNotFoundError as err:
            raise RuntimeError("1Password CLI not found. Install: brew install --cask 1password-cli") from err

    def _headers(self) -> dict[str, str]:
        """Build request headers with auth token."""
        return {"Authorization": f"Bearer {self._get_token()}"}

    def get_subscriptions(self) -> list[str]:
        """Fetch current Invidious subscription channel IDs.

        Returns:
            List of channel IDs (UCxxxx format).
        """
        url = f"{self.base_url}/api/v1/auth/subscriptions"
        resp = requests.get(url, headers=self._headers(), timeout=30, verify=self.verify_ssl)

        if resp.status_code == 403:
            raise RuntimeError(
                "Invidious API returned 403 Forbidden. "
                "Check that your API token is valid and not expired. "
                "Generate a new one at: "
                f"{self.base_url}/authorize_token"
            )
        resp.raise_for_status()

        data = resp.json()
        return [item.get("authorId", "") for item in data if item.get("authorId")]

    def subscribe(self, channel_id: str) -> bool:
        """Subscribe to a channel on Invidious.

        Args:
            channel_id: YouTube channel ID (UCxxxx format).

        Returns:
            True if successful.
        """
        url = f"{self.base_url}/api/v1/auth/subscriptions/{channel_id}"
        resp = requests.post(url, headers=self._headers(), timeout=30, verify=self.verify_ssl)

        if resp.status_code in (200, 204):
            return True

        logger.warning(f"Failed to subscribe to {channel_id}: {resp.status_code} {resp.text}")
        return False

    def unsubscribe(self, channel_id: str) -> bool:
        """Unsubscribe from a channel on Invidious.

        Args:
            channel_id: YouTube channel ID (UCxxxx format).

        Returns:
            True if successful.
        """
        url = f"{self.base_url}/api/v1/auth/subscriptions/{channel_id}"
        resp = requests.delete(url, headers=self._headers(), timeout=30, verify=self.verify_ssl)

        if resp.status_code in (200, 204):
            return True

        logger.warning(f"Failed to unsubscribe from {channel_id}: {resp.status_code} {resp.text}")
        return False

    def sync_from_youtube(
        self,
        channel_ids: list[str],
        dry_run: bool = False,
        remove_stale: bool = False,
    ) -> InvidiousSyncResult:
        """Sync YouTube subscriptions to Invidious.

        Args:
            channel_ids: YouTube channel IDs to sync.
            dry_run: If True, compute diff but don't make changes.
            remove_stale: If True, unsubscribe from Invidious channels not in YouTube.

        Returns:
            InvidiousSyncResult with sync details.
        """
        start = time.monotonic()

        # Get current Invidious subscriptions
        console.print("[dim]Fetching current Invidious subscriptions...[/dim]")
        existing = set(self.get_subscriptions())
        invidious_before = len(existing)

        # Compute diffs
        youtube_set = set(channel_ids)
        missing = youtube_set - existing
        already_present = youtube_set & existing
        stale = existing - youtube_set if remove_stale else set()

        status_parts = [
            f"YouTube: {len(youtube_set)}",
            f"Invidious: {invidious_before}",
            f"To add: {len(missing)}",
        ]
        if remove_stale:
            status_parts.append(f"To remove: {len(stale)}")
        console.print(" | ".join(status_parts))

        if dry_run:
            duration = time.monotonic() - start
            return InvidiousSyncResult(
                youtube_count=len(youtube_set),
                invidious_count_before=invidious_before,
                invidious_count_after=invidious_before,
                added=[],
                removed=list(stale),
                already_present=list(already_present),
                failed=[],
                dry_run=True,
                duration_seconds=duration,
            )

        added = []
        failed = []

        if missing:
            sorted_missing = sorted(missing)
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(
                    f"Subscribing to {len(sorted_missing)} channels...", total=len(sorted_missing)
                )

                for i, channel_id in enumerate(sorted_missing):
                    if self.subscribe(channel_id):
                        added.append(channel_id)
                    else:
                        failed.append(channel_id)

                    progress.update(task, advance=1)
                    time.sleep(self.request_delay)

                    # Batch pause
                    if (i + 1) % self.batch_size == 0 and (i + 1) < len(sorted_missing):
                        progress.update(
                            task,
                            description=f"Batch pause ({i + 1}/{len(sorted_missing)})...",
                        )
                        time.sleep(self.batch_pause)
                        progress.update(
                            task,
                            description=f"Subscribing to {len(sorted_missing)} channels...",
                        )

        # Remove stale subscriptions
        removed = []
        if stale:
            sorted_stale = sorted(stale)
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(
                    f"Removing {len(sorted_stale)} stale subscriptions...", total=len(sorted_stale)
                )

                for i, channel_id in enumerate(sorted_stale):
                    if self.unsubscribe(channel_id):
                        removed.append(channel_id)

                    progress.update(task, advance=1)
                    time.sleep(self.request_delay)

                    if (i + 1) % self.batch_size == 0 and (i + 1) < len(sorted_stale):
                        time.sleep(self.batch_pause)

        duration = time.monotonic() - start
        return InvidiousSyncResult(
            youtube_count=len(youtube_set),
            invidious_count_before=invidious_before,
            invidious_count_after=invidious_before + len(added) - len(removed),
            added=added,
            removed=removed,
            already_present=list(already_present),
            failed=failed,
            dry_run=False,
            duration_seconds=duration,
        )


# ============================================================================
# CLI Commands
# ============================================================================

@app.command()
def auth():
    """Run OAuth 2.0 flow to authenticate with YouTube."""
    console.print("[bold]YouTube Authentication[/bold]")
    console.print()

    auth_handler = YouTubeAuth()

    if auth_handler.is_authenticated():
        console.print("[green]✓ Already authenticated[/green]")
        if typer.confirm("Re-authenticate?", default=False):
            auth_handler.run_oauth_flow()
    else:
        console.print("Starting OAuth flow...")
        console.print()
        auth_handler.run_oauth_flow()


@app.command()
def fetch(
    no_cache: bool = typer.Option(False, "--no-cache", help="Force fresh fetch from API"),
):
    """Fetch subscriptions from YouTube."""
    console.print("[bold]Fetching YouTube Subscriptions[/bold]")
    console.print()

    auth_handler = YouTubeAuth()
    if not auth_handler.is_authenticated():
        console.print("[red]Not authenticated. Run: youtube-subs auth[/red]")
        raise typer.Exit(1)

    fetcher = SubscriptionFetcher(auth_handler)
    channels = fetcher.fetch_subscriptions(use_cache=not no_cache)

    console.print()
    console.print(f"[green]Total subscriptions: {len(channels)}[/green]")


@app.command()
def categories():
    """Show categories with channel counts."""
    console.print("[bold]YouTube Subscription Categories[/bold]")
    console.print()

    auth_handler = YouTubeAuth()
    fetcher = SubscriptionFetcher(auth_handler)

    # Try to load from cache
    channels = fetcher.fetch_subscriptions(use_cache=True)
    if not channels:
        console.print("[red]No subscriptions found. Run: youtube-subs fetch[/red]")
        raise typer.Exit(1)

    mapper = CategoryMapper()
    groups = mapper.categorize_all(channels)
    groups = mapper.apply_filtering(groups)

    # Display table
    table = Table(title="Categories")
    table.add_column("Category", style="cyan")
    table.add_column("Channels", justify="right")
    table.add_column("Top Channels", style="dim")

    for group in groups:
        top_channels = ", ".join(ch.title[:20] for ch in group.channels[:3])
        if len(group.channels) > 3:
            top_channels += "..."
        table.add_row(f"{group.emoji} {group.name}", str(group.count), top_channels)

    console.print(table)


@app.command()
def generate(
    output: str = typer.Option(None, "--output", "-o", help="Output file path"),
):
    """Generate Glance configuration from subscriptions."""
    console.print("[bold]Generating Glance Configuration[/bold]")
    console.print()

    auth_handler = YouTubeAuth()
    fetcher = SubscriptionFetcher(auth_handler)

    # Load subscriptions
    channels = fetcher.fetch_subscriptions(use_cache=True)
    if not channels:
        console.print("[red]No subscriptions found. Run: youtube-subs fetch[/red]")
        raise typer.Exit(1)

    # Categorize
    mapper = CategoryMapper()
    groups = mapper.categorize_all(channels)
    groups = mapper.apply_filtering(groups)

    # Generate config
    generator = GlanceConfigGenerator()

    if output:
        generator.output["glance_yaml_path"] = output

    page = generator.generate(groups)
    output_path = generator.save(page)

    console.print()
    console.print(f"[green]✓ Generated: {output_path}[/green]")
    console.print()
    console.print("[dim]Copy this to your Glance config or include it via YAML merge.[/dim]")


@app.command()
def sync(
    no_cache: bool = typer.Option(False, "--no-cache", help="Force fresh fetch from API"),
):
    """Full pipeline: fetch subscriptions and generate Glance config."""
    console.print("[bold]YouTube → Glance Sync[/bold]")
    console.print()

    # Check auth
    auth_handler = YouTubeAuth()
    if not auth_handler.is_authenticated():
        console.print("[yellow]Not authenticated. Starting OAuth flow...[/yellow]")
        if not auth_handler.run_oauth_flow():
            raise typer.Exit(1)

    # Fetch
    fetcher = SubscriptionFetcher(auth_handler)
    channels = fetcher.fetch_subscriptions(use_cache=not no_cache)

    if not channels:
        console.print("[red]No subscriptions found.[/red]")
        raise typer.Exit(1)

    # Categorize
    mapper = CategoryMapper()
    groups = mapper.categorize_all(channels)
    groups = mapper.apply_filtering(groups)

    # Stats
    stats = SyncStats(
        total_subscriptions=len(channels),
        categorized_auto=sum(1 for ch in channels if not ch.is_override and ch.assigned_category != "Other"),
        categorized_override=sum(1 for ch in channels if ch.is_override),
        uncategorized=sum(1 for ch in channels if ch.assigned_category == "Other"),
        categories_with_content=len(groups),
    )

    # Generate
    generator = GlanceConfigGenerator()
    page = generator.generate(groups)
    output_path = generator.save(page)

    # Summary
    console.print()
    console.print("[green]✓ Sync complete![/green]")
    console.print()

    table = Table(title="Sync Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row("Total Subscriptions", str(stats.total_subscriptions))
    table.add_row("Auto-categorized", str(stats.categorized_auto))
    table.add_row("Manual Overrides", str(stats.categorized_override))
    table.add_row("Uncategorized (Other)", str(stats.uncategorized))
    table.add_row("Categories with Content", str(stats.categories_with_content))

    console.print(table)
    console.print()
    console.print(f"[dim]Output: {output_path}[/dim]")


@app.command("list")
def list_channels(
    category: str = typer.Option(None, "--category", "-c", help="Filter by category"),
):
    """List subscribed channels."""
    auth_handler = YouTubeAuth()
    fetcher = SubscriptionFetcher(auth_handler)

    channels = fetcher.fetch_subscriptions(use_cache=True)
    if not channels:
        console.print("[red]No subscriptions found. Run: youtube-subs fetch[/red]")
        raise typer.Exit(1)

    mapper = CategoryMapper()
    groups = mapper.categorize_all(channels)

    if category:
        groups = [g for g in groups if g.name.lower() == category.lower()]
        if not groups:
            console.print(f"[red]Category '{category}' not found[/red]")
            raise typer.Exit(1)

    for group in groups:
        console.print(f"\n[bold]{group.emoji} {group.name}[/bold] ({group.count} channels)")
        for ch in group.channels[:20]:  # Limit display
            subs = f"{ch.subscriber_count:,}" if ch.subscriber_count else "?"
            console.print(f"  • {ch.title} ({subs} subs) - {ch.id}")
        if group.count > 20:
            console.print(f"  [dim]... and {group.count - 20} more[/dim]")


@app.command()
def move(
    channel_id: str = typer.Argument(..., help="Channel ID to move"),
    to: str = typer.Option(..., "--to", help="Target category"),
):
    """Move a channel to a different category (updates overrides.yaml)."""
    overrides = load_overrides()
    overrides.setdefault("channel_overrides", {})
    overrides["channel_overrides"][channel_id] = to

    overrides_path = get_config_path() / "overrides.yaml"
    with open(overrides_path, "w", encoding="utf-8") as f:
        yaml.dump(overrides, f, default_flow_style=False, allow_unicode=True)

    console.print(f"[green]✓ Moved {channel_id} to {to}[/green]")
    console.print("[dim]Run 'youtube-subs generate' to update Glance config.[/dim]")


@app.command("invidious-sync")
def invidious_sync(
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without subscribing"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Force fresh fetch from YouTube API"),
    remove_stale: bool = typer.Option(
        False, "--remove-stale", help="Remove Invidious subs not in YouTube"
    ),
):
    """Sync YouTube subscriptions to Invidious."""
    console.print("[bold]YouTube → Invidious Sync[/bold]")
    console.print()

    # Fetch YouTube subscriptions
    auth_handler = YouTubeAuth()
    if not auth_handler.is_authenticated():
        console.print("[red]Not authenticated with YouTube. Run: youtube-subs auth[/red]")
        raise typer.Exit(1)

    fetcher = SubscriptionFetcher(auth_handler)
    channels = fetcher.fetch_subscriptions(use_cache=not no_cache)

    if not channels:
        console.print("[red]No YouTube subscriptions found.[/red]")
        raise typer.Exit(1)

    channel_ids = [ch.id for ch in channels]

    # Sync to Invidious
    try:
        client = InvidiousClient()
    except (ValueError, RuntimeError) as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    result = client.sync_from_youtube(channel_ids, dry_run=dry_run, remove_stale=remove_stale)

    # Display results
    console.print()
    if dry_run:
        console.print("[yellow]DRY RUN — no changes made[/yellow]")

    table = Table(title="Invidious Sync Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row("YouTube subscriptions", str(result.youtube_count))
    table.add_row("Invidious before", str(result.invidious_count_before))
    table.add_row("Already present", str(len(result.already_present)))
    table.add_row("Added", str(len(result.added)))
    if remove_stale:
        table.add_row("Removed", str(len(result.removed)))
    table.add_row("Failed", str(len(result.failed)))
    table.add_row("Invidious after", str(result.invidious_count_after))
    table.add_row("Duration", f"{result.duration_seconds:.1f}s")

    console.print(table)

    if result.failed:
        console.print()
        console.print("[red]Failed channels:[/red]")
        for cid in result.failed:
            console.print(f"  - {cid}")

    if not dry_run and result.added:
        console.print()
        console.print(f"[green]Successfully added {len(result.added)} channels to Invidious[/green]")

    if not dry_run and result.removed:
        console.print(f"[yellow]Removed {len(result.removed)} stale subscriptions from Invidious[/yellow]")


@app.command("invidious-status")
def invidious_status():
    """Show Invidious subscription count and connection status."""
    console.print("[bold]Invidious Status[/bold]")
    console.print()

    try:
        client = InvidiousClient()
    except (ValueError, RuntimeError) as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    try:
        subs = client.get_subscriptions()
        console.print(f"[green]Connected to {client.base_url}[/green]")
        console.print(f"Subscriptions: {len(subs)}")
    except requests.RequestException as e:
        console.print(f"[red]Connection failed: {e}[/red]")
        raise typer.Exit(1) from None


if __name__ == "__main__":
    app()
