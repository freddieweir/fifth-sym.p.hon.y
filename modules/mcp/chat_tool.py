"""
MCP server for Fifth Symphony chat integration.

Allows Claude Code agents to post messages to the shared chat hub.
"""

import asyncio
import json
import logging
from typing import Optional
import websockets
from mcp.server import Server
from mcp.types import Tool, TextContent

logger = logging.getLogger(__name__)

# Initialize MCP server
server = Server("fifth-symphony-chat")

# Global WebSocket connection
_chat_connection: Optional[websockets.WebSocketClientProtocol] = None
_chat_server_url = "ws://localhost:8765"


async def _connect_to_chat():
    """Connect to chat server if not already connected."""
    global _chat_connection

    if _chat_connection and not _chat_connection.closed:
        return _chat_connection

    try:
        _chat_connection = await websockets.connect(_chat_server_url)
        logger.info("Connected to Fifth Symphony chat server")
        return _chat_connection
    except Exception as e:
        logger.error(f"Failed to connect to chat server: {e}")
        raise


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="post_to_chat",
            description="Post a message to the Fifth Symphony multi-agent chat",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The message to post to chat"
                    },
                    "username": {
                        "type": "string",
                        "description": "Display name (Nazarick-Agent, Code-Assistant, VM-Claude)",
                        "default": "Nazarick-Agent"
                    }
                },
                "required": ["message"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    if name == "post_to_chat":
        message = arguments.get("message", "")
        username = arguments.get("username", "Nazarick-Agent")

        if not message:
            return [TextContent(type="text", text="Error: message cannot be empty")]

        try:
            # Connect to chat server
            ws = await _connect_to_chat()

            # Send message
            chat_message = {
                "username": username,
                "content": message
            }
            await ws.send(json.dumps(chat_message))

            return [TextContent(
                type="text",
                text=f"Message posted to Fifth Symphony chat as {username}"
            )]

        except Exception as e:
            logger.error(f"Error posting to chat: {e}")
            return [TextContent(
                type="text",
                text=f"Error posting to chat: {str(e)}"
            )]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    """Run MCP server."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
