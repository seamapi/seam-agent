"""
Configuration for investigation limits and budgets.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class InvestigationConfig:
    """Configuration for investigation limits and resource management."""

    # Tool calling limits
    MAX_TOOL_ROUNDS: int = 3
    MAX_TOOLS_PER_ROUND: int = 5
    MAX_TOTAL_TOOLS: int = 10

    # Context management
    CONTEXT_BUDGET_TOKENS: int = 8000
    MAX_CONVERSATION_LENGTH: int = 20

    # Timeout limits (seconds)
    TOOL_EXECUTION_TIMEOUT: int = 30
    TOTAL_INVESTIGATION_TIMEOUT: int = 120

    # Pagination limits
    DEFAULT_PAGINATION_LIMIT: int = 10
    MAX_PAGINATION_LIMIT: int = 100
    AGGRESSIVE_PAGINATION_LIMIT: int = 50

    @classmethod
    def create_production_config(cls) -> "InvestigationConfig":
        """Create a conservative configuration for production use."""
        return cls(
            MAX_TOOL_ROUNDS=2,
            MAX_TOOLS_PER_ROUND=3,
            MAX_TOTAL_TOOLS=6,
            CONTEXT_BUDGET_TOKENS=6000,
            TOTAL_INVESTIGATION_TIMEOUT=90,
        )

    @classmethod
    def create_debug_config(cls) -> "InvestigationConfig":
        """Create a more permissive configuration for debugging."""
        return cls(
            MAX_TOOL_ROUNDS=5,
            MAX_TOOLS_PER_ROUND=8,
            MAX_TOTAL_TOOLS=20,
            CONTEXT_BUDGET_TOKENS=12000,
            TOTAL_INVESTIGATION_TIMEOUT=300,
        )


@dataclass
class InvestigationState:
    """Tracks the current state of an investigation for limit enforcement."""

    tool_rounds_used: int = 0
    tools_used_this_round: int = 0
    total_tools_used: int = 0
    start_time: Optional[float] = None
    conversation_messages: int = 0

    def can_continue_round(self, config: InvestigationConfig) -> bool:
        """Check if we can continue with more tools in this round."""
        return (
            self.tools_used_this_round < config.MAX_TOOLS_PER_ROUND
            and self.total_tools_used < config.MAX_TOTAL_TOOLS
        )

    def can_start_new_round(self, config: InvestigationConfig) -> bool:
        """Check if we can start a new tool calling round."""
        return (
            self.tool_rounds_used < config.MAX_TOOL_ROUNDS
            and self.total_tools_used < config.MAX_TOTAL_TOOLS
        )

    def record_tool_use(self) -> None:
        """Record that a tool was used."""
        self.tools_used_this_round += 1
        self.total_tools_used += 1

    def start_new_round(self) -> None:
        """Start a new tool calling round."""
        self.tool_rounds_used += 1
        self.tools_used_this_round = 0

    def record_message(self) -> None:
        """Record a conversation message."""
        self.conversation_messages += 1

    def get_limits_summary(self) -> str:
        """Get a summary of current limits usage."""
        return (
            f"Tool rounds: {self.tool_rounds_used}, "
            f"Tools this round: {self.tools_used_this_round}, "
            f"Total tools: {self.total_tools_used}, "
            f"Messages: {self.conversation_messages}"
        )


class InvestigationLimitError(Exception):
    """Raised when investigation limits are exceeded."""

    pass
