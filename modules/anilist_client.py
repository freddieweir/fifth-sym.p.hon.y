"""
AniList API Client

Integrates with AniList GraphQL API for anime/manga tracking.
Uses 1Password for secure API token storage.
"""

import subprocess
import logging
import aiohttp
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AnimeEntry:
    """Represents an anime entry"""
    id: int
    title: str
    status: str  # CURRENT, PLANNING, COMPLETED, DROPPED, PAUSED
    progress: int
    score: Optional[float] = None
    episodes: Optional[int] = None


@dataclass
class MangaEntry:
    """Represents a manga entry"""
    id: int
    title: str
    status: str
    progress: int
    score: Optional[float] = None
    chapters: Optional[int] = None


class AniListClient:
    """
    Client for AniList GraphQL API.

    Features:
    - Retrieve anime/manga lists
    - Update progress and scores
    - Search for anime/manga
    - Get user statistics
    """

    API_URL = "https://graphql.anilist.co"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize AniList client.

        Args:
            config: Optional configuration (vault name, etc.)
        """
        self.config = config or {}
        self.vault = self.config.get("onepassword_vault", "API")
        self.api_token_item = self.config.get("api_token_item", "AniList API")
        self.logger = logging.getLogger(__name__)
        self._token: Optional[str] = None

    async def _get_api_token(self) -> str:
        """
        Retrieve AniList API token from 1Password.

        Returns:
            API token string
        """
        if self._token:
            return self._token

        try:
            result = subprocess.run(
                [
                    "op", "item", "get",
                    self.api_token_item,
                    "--vault", self.vault,
                    "--fields", "credential"
                ],
                capture_output=True,
                text=True,
                check=True
            )

            self._token = result.stdout.strip()
            self.logger.info(f"Retrieved AniList API token from 1Password")
            return self._token

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to retrieve API token: {e.stderr}")
            raise RuntimeError(f"Cannot access AniList API token: {e.stderr}")

    async def _query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute GraphQL query against AniList API.

        Args:
            query: GraphQL query string
            variables: Optional query variables

        Returns:
            Response data dictionary
        """
        token = await self._get_api_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload = {
            "query": query,
            "variables": variables or {}
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.API_URL,
                json=payload,
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    self.logger.error(f"AniList API error: {error_text}")
                    raise RuntimeError(f"AniList API returned {response.status}: {error_text}")

                data = await response.json()
                return data

    async def get_user_anime_list(
        self,
        username: str,
        status: Optional[str] = None
    ) -> List[AnimeEntry]:
        """
        Get user's anime list.

        Args:
            username: AniList username
            status: Optional filter (CURRENT, PLANNING, COMPLETED, etc.)

        Returns:
            List of AnimeEntry objects
        """
        query = """
        query ($username: String, $status: MediaListStatus) {
          MediaListCollection(userName: $username, type: ANIME, status: $status) {
            lists {
              entries {
                id
                status
                progress
                score
                media {
                  id
                  title {
                    romaji
                    english
                  }
                  episodes
                }
              }
            }
          }
        }
        """

        variables = {"username": username}
        if status:
            variables["status"] = status

        data = await self._query(query, variables)

        # Parse response
        entries = []
        lists = data.get("data", {}).get("MediaListCollection", {}).get("lists", [])

        for lst in lists:
            for entry in lst.get("entries", []):
                media = entry.get("media", {})
                title_data = media.get("title", {})
                title = title_data.get("english") or title_data.get("romaji")

                entries.append(AnimeEntry(
                    id=entry.get("id"),
                    title=title,
                    status=entry.get("status"),
                    progress=entry.get("progress", 0),
                    score=entry.get("score"),
                    episodes=media.get("episodes")
                ))

        return entries

    async def get_currently_watching(self, username: str) -> List[AnimeEntry]:
        """
        Get anime currently being watched.

        Args:
            username: AniList username

        Returns:
            List of AnimeEntry objects with CURRENT status
        """
        return await self.get_user_anime_list(username, status="CURRENT")

    async def update_anime_progress(
        self,
        media_id: int,
        progress: int,
        score: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Update anime progress.

        Args:
            media_id: AniList media ID
            progress: Episode progress
            score: Optional score (0-10)

        Returns:
            Updated entry data
        """
        mutation = """
        mutation ($mediaId: Int, $progress: Int, $score: Float) {
          SaveMediaListEntry(mediaId: $mediaId, progress: $progress, scoreRaw: $score) {
            id
            status
            progress
            score
          }
        }
        """

        variables = {
            "mediaId": media_id,
            "progress": progress
        }

        if score is not None:
            variables["score"] = score * 10  # AniList uses 0-100 scale

        data = await self._query(mutation, variables)
        return data.get("data", {}).get("SaveMediaListEntry", {})

    async def search_anime(self, search: str) -> List[Dict[str, Any]]:
        """
        Search for anime.

        Args:
            search: Search query

        Returns:
            List of anime results
        """
        query = """
        query ($search: String) {
          Page(page: 1, perPage: 10) {
            media(search: $search, type: ANIME) {
              id
              title {
                romaji
                english
              }
              episodes
              status
              description
            }
          }
        }
        """

        variables = {"search": search}
        data = await self._query(query, variables)

        media = data.get("data", {}).get("Page", {}).get("media", [])
        return media

    async def get_user_stats(self, username: str) -> Dict[str, Any]:
        """
        Get user statistics.

        Args:
            username: AniList username

        Returns:
            User statistics
        """
        query = """
        query ($username: String) {
          User(name: $username) {
            statistics {
              anime {
                count
                episodesWatched
                minutesWatched
                meanScore
              }
            }
          }
        }
        """

        variables = {"username": username}
        data = await self._query(query, variables)

        stats = data.get("data", {}).get("User", {}).get("statistics", {}).get("anime", {})
        return stats


# Example usage
async def example_usage():
    """Example AniList integration"""
    import asyncio

    client = AniListClient()

    # Get currently watching anime
    watching = await client.get_currently_watching("YourUsername")

    print("Currently Watching:")
    for anime in watching:
        print(f"  - {anime.title}: {anime.progress}/{anime.episodes or '?'} episodes")

    # Search for anime
    results = await client.search_anime("Frieren")
    print("\nSearch Results:")
    for result in results[:3]:
        title = result["title"]["english"] or result["title"]["romaji"]
        print(f"  - {title}")

    # Get stats
    stats = await client.get_user_stats("YourUsername")
    print(f"\nStats:")
    print(f"  Total Anime: {stats.get('count')}")
    print(f"  Episodes Watched: {stats.get('episodesWatched')}")
    print(f"  Mean Score: {stats.get('meanScore')}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())
