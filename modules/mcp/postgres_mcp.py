"""
PostgreSQL MCP Server for Fifth Symphony

Provides database access tools for Claude Code agents.
Allows querying memories, anime preferences, voice IDs, and chat logs.
"""

import asyncio
import logging
import os
from typing import Any, List

import asyncpg
from mcp.server import Server
from mcp.types import Tool, TextContent

logger = logging.getLogger(__name__)

# Initialize MCP server
server = Server("fifth-symphony-postgres")

# Global connection pool
_db_pool: asyncpg.Pool = None


async def get_db_pool() -> asyncpg.Pool:
    """Get or create database connection pool."""
    global _db_pool

    if _db_pool is None:
        database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://symphony:changeme@localhost:5432/fifth_symphony"
        )
        _db_pool = await asyncpg.create_pool(database_url, min_size=2, max_size=10)
        logger.info("Created database connection pool")

    return _db_pool


@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available database tools."""
    return [
        Tool(
            name="search_memories",
            description="Search the knowledge base for relevant memories",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (supports full-text search)"
                    },
                    "category": {
                        "type": "string",
                        "description": "Filter by category (optional)",
                        "enum": ["personal", "technical", "project", "anime", None]
                    },
                    "min_importance": {
                        "type": "integer",
                        "description": "Minimum importance level (1-10, optional)",
                        "minimum": 1,
                        "maximum": 10
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_anime_preferences",
            description="Get anime preferences and watch status",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter by watch status",
                        "enum": ["WATCHING", "COMPLETED", "PLANNING", "PAUSED", "DROPPED", None]
                    },
                    "min_score": {
                        "type": "integer",
                        "description": "Minimum score (0-100, optional)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 20
                    }
                }
            }
        ),
        Tool(
            name="get_voice_ids",
            description="Get available ElevenLabs voice IDs and configurations",
            inputSchema={
                "type": "object",
                "properties": {
                    "use_case": {
                        "type": "string",
                        "description": "Filter by use case (optional)",
                        "enum": ["orchestrator", "narrator", "assistant", None]
                    }
                }
            }
        ),
        Tool(
            name="search_chat_logs",
            description="Search processed chat export logs",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for chat content"
                    },
                    "role": {
                        "type": "string",
                        "description": "Filter by message role",
                        "enum": ["user", "assistant", "system", None]
                    },
                    "has_thinking": {
                        "type": "boolean",
                        "description": "Filter messages with thinking content"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 20
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_ai_personalities",
            description="Get AI personality configurations from forge",
            inputSchema={
                "type": "object",
                "properties": {
                    "active_only": {
                        "type": "boolean",
                        "description": "Only return active personalities",
                        "default": True
                    }
                }
            }
        ),
        Tool(
            name="add_memory",
            description="Add a new memory to the knowledge base",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Memory content"
                    },
                    "category": {
                        "type": "string",
                        "description": "Memory category",
                        "enum": ["personal", "technical", "project", "anime"]
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for categorization"
                    },
                    "importance": {
                        "type": "integer",
                        "description": "Importance level (1-10)",
                        "minimum": 1,
                        "maximum": 10,
                        "default": 5
                    },
                    "source": {
                        "type": "string",
                        "description": "Source of the memory",
                        "default": "manual"
                    }
                },
                "required": ["content", "category"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> List[TextContent]:
    """Handle tool calls."""
    pool = await get_db_pool()

    try:
        if name == "search_memories":
            query = arguments["query"]
            category = arguments.get("category")
            min_importance = arguments.get("min_importance", 1)
            limit = arguments.get("limit", 10)

            sql = """
                SELECT id, content, category, tags, importance, created_at
                FROM memories
                WHERE to_tsvector('english', content) @@ plainto_tsquery('english', $1)
                AND importance >= $2
            """
            params = [query, min_importance]

            if category:
                sql += " AND category = $3"
                params.append(category)

            sql += f" ORDER BY importance DESC, created_at DESC LIMIT ${len(params) + 1}"
            params.append(limit)

            async with pool.acquire() as conn:
                rows = await conn.fetch(sql, *params)

            if not rows:
                return [TextContent(type="text", text="No memories found matching the query.")]

            result = "## Memories Found\n\n"
            for row in rows:
                result += f"**{row['category'].upper()}** (Importance: {row['importance']}/10)\n"
                result += f"{row['content']}\n"
                if row['tags']:
                    result += f"*Tags: {', '.join(row['tags'])}*\n"
                result += f"*Created: {row['created_at'].strftime('%Y-%m-%d')}*\n\n"

            return [TextContent(type="text", text=result)]

        elif name == "get_anime_preferences":
            status = arguments.get("status")
            min_score = arguments.get("min_score", 0)
            limit = arguments.get("limit", 20)

            sql = """
                SELECT title, title_english, status, score, progress, episodes, genres
                FROM anime_preferences
                WHERE score >= $1
            """
            params = [min_score]

            if status:
                sql += " AND status = $2"
                params.append(status)

            sql += f" ORDER BY score DESC NULLS LAST LIMIT ${len(params) + 1}"
            params.append(limit)

            async with pool.acquire() as conn:
                rows = await conn.fetch(sql, *params)

            if not rows:
                return [TextContent(type="text", text="No anime found matching criteria.")]

            result = "## Anime Preferences\n\n"
            for row in rows:
                title = row['title_english'] or row['title']
                result += f"**{title}** ({row['status']})\n"
                if row['score']:
                    result += f"Score: {row['score']}/100 | "
                result += f"Progress: {row['progress']}/{row['episodes'] or '?'}\n"
                if row['genres']:
                    result += f"*Genres: {', '.join(row['genres'])}*\n"
                result += "\n"

            return [TextContent(type="text", text=result)]

        elif name == "get_voice_ids":
            use_case = arguments.get("use_case")

            sql = "SELECT name, elevenlabs_voice_id, description, use_case, personality_traits FROM voice_ids"
            params = []

            if use_case:
                sql += " WHERE use_case = $1"
                params.append(use_case)

            sql += " ORDER BY name"

            async with pool.acquire() as conn:
                rows = await conn.fetch(sql, *params)

            if not rows:
                return [TextContent(type="text", text="No voice IDs configured.")]

            result = "## Available Voice IDs\n\n"
            for row in rows:
                result += f"**{row['name']}** ({row['use_case']})\n"
                result += f"ID: `{row['elevenlabs_voice_id']}`\n"
                if row['description']:
                    result += f"{row['description']}\n"
                if row['personality_traits']:
                    result += f"*Traits: {', '.join(row['personality_traits'])}*\n"
                result += "\n"

            return [TextContent(type="text", text=result)]

        elif name == "search_chat_logs":
            query = arguments["query"]
            role = arguments.get("role")
            has_thinking = arguments.get("has_thinking")
            limit = arguments.get("limit", 20)

            sql = """
                SELECT message_number, role, content, timestamp, has_thinking
                FROM chat_messages
                WHERE to_tsvector('english', content) @@ plainto_tsquery('english', $1)
            """
            params = [query]

            if role:
                sql += f" AND role = ${len(params) + 1}"
                params.append(role)

            if has_thinking is not None:
                sql += f" AND has_thinking = ${len(params) + 1}"
                params.append(has_thinking)

            sql += f" ORDER BY timestamp DESC LIMIT ${len(params) + 1}"
            params.append(limit)

            async with pool.acquire() as conn:
                rows = await conn.fetch(sql, *params)

            if not rows:
                return [TextContent(type="text", text="No chat messages found.")]

            result = "## Chat Log Search Results\n\n"
            for row in rows:
                result += f"**{row['role'].upper()} #{row['message_number']}**\n"
                if row['timestamp']:
                    result += f"*{row['timestamp'].strftime('%Y-%m-%d %H:%M')}*\n"
                result += f"{row['content'][:500]}{'...' if len(row['content']) > 500 else ''}\n\n"

            return [TextContent(type="text", text=result)]

        elif name == "get_ai_personalities":
            active_only = arguments.get("active_only", True)

            sql = """
                SELECT name, description, voice_name, personality_traits, anime_influences
                FROM active_personalities
            """
            if active_only:
                sql += " WHERE is_active = TRUE"

            async with pool.acquire() as conn:
                rows = await conn.fetch(sql)

            if not rows:
                return [TextContent(type="text", text="No AI personalities configured.")]

            result = "## AI Personalities\n\n"
            for row in rows:
                result += f"**{row['name']}**\n"
                if row['description']:
                    result += f"{row['description']}\n"
                if row['voice_name']:
                    result += f"Voice: {row['voice_name']}\n"
                if row['anime_influences']:
                    result += f"*Anime influences: {', '.join(row['anime_influences'])}*\n"
                result += "\n"

            return [TextContent(type="text", text=result)]

        elif name == "add_memory":
            content = arguments["content"]
            category = arguments["category"]
            tags = arguments.get("tags", [])
            importance = arguments.get("importance", 5)
            source = arguments.get("source", "manual")

            sql = """
                INSERT INTO memories (content, category, tags, importance, source)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            """

            async with pool.acquire() as conn:
                row = await conn.fetchrow(sql, content, category, tags, importance, source)

            return [TextContent(
                type="text",
                text=f"Memory added successfully with ID: {row['id']}"
            )]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        logger.error(f"Error in tool {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run MCP server."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
