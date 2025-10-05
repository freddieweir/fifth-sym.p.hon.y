"""
Permission Engine

Core permission logic for orchestrator approval/denial system.
Handles request evaluation, auto-approve rules, and risk assessment.
"""

import logging
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk levels for permission requests"""
    LOW = "low"           # Read operations, safe commands
    MEDIUM = "medium"     # Write operations, non-destructive changes
    HIGH = "high"         # System modifications, network operations
    CRITICAL = "critical" # Destructive operations, security-sensitive


class ApprovalResponse(Enum):
    """User approval responses"""
    YES = "yes"                    # Approve this time
    NO = "no"                      # Deny this time
    ALWAYS = "always"              # Auto-approve this pattern
    NEVER = "never"                # Auto-deny this pattern
    CUSTOM = "custom"              # Provide custom instructions


@dataclass
class PermissionRequest:
    """Represents a permission request from Claude Code"""
    action: str                    # Description of action
    command: Optional[str]         # Actual command if applicable
    risk_level: RiskLevel          # Assessed risk level
    agent: str                     # Which Nazarick agent is requesting
    context: Dict[str, Any]        # Additional context
    session_id: str                # Session identifier


class PermissionEngine:
    """
    Core permission evaluation engine.

    Responsibilities:
    - Assess risk levels for operations
    - Check auto-approve rules
    - Evaluate permission requests
    - Store approval decisions
    """

    def __init__(self, config: Dict[str, Any], approval_store):
        """
        Initialize permission engine.

        Args:
            config: Configuration dictionary
            approval_store: ApprovalStore instance for persistence
        """
        self.config = config
        self.approval_store = approval_store
        self.logger = logging.getLogger(__name__)

        # Risk assessment patterns
        self.risk_patterns = self._load_risk_patterns()

    def _load_risk_patterns(self) -> Dict[RiskLevel, list]:
        """Load risk assessment patterns from config"""
        return {
            RiskLevel.CRITICAL: [
                r"rm -rf",
                r"dd if=",
                r"mkfs\.",
                r"--force",
                r"git push.*--force",
                r"DROP DATABASE",
                r"DELETE FROM.*WHERE 1=1",
            ],
            RiskLevel.HIGH: [
                r"sudo",
                r"git push",
                r"docker rm",
                r"DELETE FROM",
                r"ALTER TABLE",
                r"chmod 777",
            ],
            RiskLevel.MEDIUM: [
                r"git commit",
                r"write file",
                r"edit file",
                r"docker restart",
                r"npm install",
            ],
            RiskLevel.LOW: [
                r"git status",
                r"read file",
                r"ls",
                r"find",
                r"grep",
            ],
        }

    async def assess_risk(self, action: str, command: Optional[str] = None) -> RiskLevel:
        """
        Assess risk level for an action.

        Args:
            action: Description of action
            command: Optional command being executed

        Returns:
            RiskLevel enum value
        """
        import re

        text_to_check = f"{action} {command or ''}".lower()

        # Check patterns from highest to lowest risk
        for risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW]:
            patterns = self.risk_patterns.get(risk_level, [])
            for pattern in patterns:
                if re.search(pattern, text_to_check, re.IGNORECASE):
                    self.logger.info(f"Risk assessment: {risk_level.value} (matched pattern: {pattern})")
                    return risk_level

        # Default to medium risk if no patterns match
        return RiskLevel.MEDIUM

    async def check_auto_approve(self, request: PermissionRequest) -> Optional[bool]:
        """
        Check if request matches auto-approve rules.

        Args:
            request: PermissionRequest to check

        Returns:
            True if auto-approved, False if auto-denied, None if needs user decision
        """
        return await self.approval_store.check_auto_approve(request)

    async def evaluate_request(self, request: PermissionRequest) -> Optional[ApprovalResponse]:
        """
        Evaluate permission request against auto-approve rules.

        Args:
            request: PermissionRequest to evaluate

        Returns:
            ApprovalResponse if auto-decided, None if user input needed
        """
        auto_decision = await self.check_auto_approve(request)

        if auto_decision is True:
            self.logger.info(f"Auto-approved: {request.action}")
            return ApprovalResponse.YES
        elif auto_decision is False:
            self.logger.info(f"Auto-denied: {request.action}")
            return ApprovalResponse.NO

        # Need user decision
        return None

    async def record_decision(
        self,
        request: PermissionRequest,
        response: ApprovalResponse,
        custom_message: Optional[str] = None
    ):
        """
        Record user decision for future reference.

        Args:
            request: Original permission request
            response: User's approval response
            custom_message: Optional custom message if response is CUSTOM
        """
        await self.approval_store.record_decision(request, response, custom_message)

        # If user said "always" or "never", create auto-approve rule
        if response in [ApprovalResponse.ALWAYS, ApprovalResponse.NEVER]:
            await self.approval_store.create_auto_rule(request, response)
