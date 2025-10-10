"""
WebSocket chat server for multi-agent communication.

Runs on localhost:8765 for security. Broadcasts messages to all connected
clients with timestamp and message history for new connections.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Set, Optional
import websockets
from websockets.server import WebSocketServerProtocol

logger = logging.getLogger(__name__)


class ChatServer:
    """
    WebSocket server for multi-agent communication.

    Runs on localhost:8765 for security. No external network exposure.
    """

    def __init__(self, host: str = "localhost", port: int = 8765, max_history: int = 1000):
        """
        Initialize chat server.

        Args:
            host: Bind address (default: localhost for security)
            port: WebSocket port (default: 8765)
            max_history: Maximum messages to keep in history
        """
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.message_history = []
        self.max_history = max_history
        self.server = None

    async def register(self, websocket: WebSocketServerProtocol):
        """
        Register new client connection.

        Sends last 50 messages from history to new client for context.
        """
        self.clients.add(websocket)
        client_addr = websocket.remote_address
        logger.info(f"Client connected from {client_addr}. Total clients: {len(self.clients)}")

        # Send system message about client connection
        await self.broadcast(
            {
                "username": "System",
                "content": f"Agent connected from {client_addr[0]}",
            }
        )

        # Send recent history to new client
        for msg in self.message_history[-50:]:
            try:
                await websocket.send(json.dumps(msg))
            except websockets.exceptions.ConnectionClosed:
                logger.warning(f"Client {client_addr} disconnected during history send")
                break

    async def unregister(self, websocket: WebSocketServerProtocol):
        """Unregister client connection."""
        if websocket in self.clients:
            self.clients.remove(websocket)
            client_addr = websocket.remote_address
            logger.info(
                f"Client disconnected from {client_addr}. Total clients: {len(self.clients)}"
            )

            # Announce disconnection
            await self.broadcast(
                {
                    "username": "System",
                    "content": f"Agent disconnected from {client_addr[0]}",
                }
            )

    async def broadcast(self, message: dict):
        """
        Broadcast message to all connected clients.

        Args:
            message: Message dict with 'username' and 'content' keys
        """
        # Add timestamp
        message["timestamp"] = datetime.now().isoformat()

        # Store in history
        self.message_history.append(message)
        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)

        # Broadcast to all clients
        if self.clients:
            failed_clients = []
            for client in self.clients:
                try:
                    await client.send(json.dumps(message))
                except websockets.exceptions.ConnectionClosed:
                    failed_clients.append(client)
                except Exception as e:
                    logger.error(f"Error broadcasting to client: {e}")
                    failed_clients.append(client)

            # Remove failed clients
            for client in failed_clients:
                await self.unregister(client)

    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """
        Handle individual client connection.

        Args:
            websocket: WebSocket connection
            path: Connection path (unused)
        """
        await self.register(websocket)
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)

                    # Validate message structure
                    if (
                        not isinstance(data, dict)
                        or "username" not in data
                        or "content" not in data
                    ):
                        logger.warning(f"Invalid message format: {data}")
                        continue

                    # Broadcast to all clients
                    await self.broadcast(data)

                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received: {message}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
        except websockets.exceptions.ConnectionClosed:
            logger.info("Client connection closed normally")
        finally:
            await self.unregister(websocket)

    async def start(self):
        """Start WebSocket server."""
        logger.info(f"🎵 Starting chat server on {self.host}:{self.port}")

        async with websockets.serve(self.handle_client, self.host, self.port):
            print(f"🎵 Chat server started on {self.host}:{self.port}")
            print(f"   Clients can connect to: ws://{self.host}:{self.port}")
            await asyncio.Future()  # Run forever

    async def stop(self):
        """Stop WebSocket server gracefully."""
        logger.info("Stopping chat server...")

        # Notify all clients
        await self.broadcast(
            {
                "username": "System",
                "content": "Chat server shutting down",
            }
        )

        # Close all client connections
        for client in list(self.clients):
            await client.close()

        self.clients.clear()
        logger.info("Chat server stopped")


async def main():
    """Run standalone chat server."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    server = ChatServer()
    try:
        await server.start()
    except KeyboardInterrupt:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
