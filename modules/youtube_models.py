"""
Pydantic models for YouTube Subscriptions integration.

Data structures for channels, categories, and Glance configuration.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Channel(BaseModel):
    """Represents a YouTube channel subscription."""

    id: str = Field(..., description="YouTube channel ID (UCxxxxx format)")
    title: str = Field(..., description="Channel display name")
    description: str = Field(default="", description="Channel description")
    thumbnail_url: str = Field(default="", description="Channel thumbnail URL")

    # Categorization
    topic_ids: list[str] = Field(default_factory=list, description="YouTube topic IDs")
    assigned_category: str | None = Field(default=None, description="Assigned category name")
    is_override: bool = Field(default=False, description="Category was manually overridden")

    # Metadata for filtering
    subscriber_count: int | None = Field(default=None, description="Subscriber count")
    video_count: int | None = Field(default=None, description="Total video count")
    last_video_date: datetime | None = Field(default=None, description="Date of most recent video")

    # Timestamps
    subscribed_at: datetime | None = Field(default=None, description="When user subscribed")
    fetched_at: datetime = Field(default_factory=datetime.now, description="When data was fetched")


class CategoryDefinition(BaseModel):
    """Defines a category for organizing channels."""

    name: str = Field(..., description="Category name")
    emoji: str = Field(default="📺", description="Emoji icon for category")
    topic_ids: list[str] = Field(default_factory=list, description="YouTube topic IDs that map to this category")
    priority: int = Field(default=50, description="Sort order (lower = first)")


class CategoryGroup(BaseModel):
    """A category with its assigned channels."""

    name: str = Field(..., description="Category name")
    emoji: str = Field(default="📺", description="Emoji icon")
    channels: list[Channel] = Field(default_factory=list, description="Channels in this category")
    priority: int = Field(default=50, description="Sort order")

    @property
    def count(self) -> int:
        """Number of channels in this category."""
        return len(self.channels)

    @property
    def channel_ids(self) -> list[str]:
        """List of channel IDs only."""
        return [ch.id for ch in self.channels]


class GlanceVideoWidget(BaseModel):
    """Represents a Glance videos widget configuration."""

    type: Literal["videos"] = "videos"
    title: str | None = Field(default=None, description="Widget title (e.g., '🎮 Gaming')")
    channels: list[str] = Field(default_factory=list, description="Channel IDs to display")
    limit: int = Field(default=12, description="Max videos to show")
    collapse_after: int = Field(default=4, ge=1, description="Collapse after N videos")
    grid_columns: int = Field(default=3, ge=1, le=6, description="Grid columns")

    def to_glance_dict(self) -> dict:
        """Convert to Glance YAML-compatible dictionary."""
        result = {"type": self.type}
        if self.title:
            result["title"] = self.title
        result["channels"] = self.channels
        result["limit"] = self.limit
        result["collapse-after"] = self.collapse_after
        result["grid-columns"] = self.grid_columns
        return result


class GlanceColumn(BaseModel):
    """Represents a Glance column containing widgets."""

    size: Literal["small", "full"] = "full"
    widgets: list[GlanceVideoWidget] = Field(default_factory=list)

    def to_glance_dict(self) -> dict:
        """Convert to Glance YAML-compatible dictionary."""
        return {
            "size": self.size,
            "widgets": [w.to_glance_dict() for w in self.widgets],
        }


class GlancePage(BaseModel):
    """Represents a complete Glance page configuration."""

    name: str = Field(default="YouTube", description="Page name")
    columns: list[GlanceColumn] = Field(default_factory=list)

    def to_glance_dict(self) -> dict:
        """Convert to Glance YAML-compatible dictionary."""
        return {
            "name": self.name,
            "columns": [c.to_glance_dict() for c in self.columns],
        }


class SubscriptionCache(BaseModel):
    """Cache metadata for subscription data."""

    total_subscriptions: int = 0
    categories_count: int = 0
    last_fetched: datetime | None = None
    last_generated: datetime | None = None
    channels: list[Channel] = Field(default_factory=list)


class SyncStats(BaseModel):
    """Statistics from a sync operation."""

    total_subscriptions: int = 0
    categorized_auto: int = 0
    categorized_override: int = 0
    uncategorized: int = 0
    filtered_out: int = 0
    categories_with_content: int = 0
    duration_seconds: float = 0.0
