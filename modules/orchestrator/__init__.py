"""
Fifth Symphony Orchestrator

Permission-gating system for AI agent operations with voice feedback.
Provides terminal UI for approval/denial of Claude Code actions.

All prompts stored securely in 1Password - zero hardcoded strings.
"""

from .permission_engine import PermissionEngine
from .mcp_client import MCPClient
from .prompt_manager import PromptManager
from .chat_integration import OrchestratorChatClient, OrchestratorChatContext

# TODO: Implement these modules
# from .tui_interface import TUIInterface
# from .ipc_server import IPCServer
# from .approval_store import ApprovalStore

__all__ = [
    "PermissionEngine",
    "MCPClient",
    "PromptManager",
    "OrchestratorChatClient",
    "OrchestratorChatContext",
    # "TUIInterface",
    # "IPCServer",
    # "ApprovalStore",
]
