"""
Fifth Symphony Multi-Agent Chat System

Real-time WebSocket-based communication hub for orchestrator, agents, and user.
Provides color-coded TUI for Attention-friendly multi-agent coordination.
"""

from .chat_client import ChatClient
from .chat_server import ChatServer

__all__ = [
    "ChatServer",
    "ChatClient",
]
