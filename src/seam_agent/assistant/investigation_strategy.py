"""
Investigation strategy for managing business logic and investigation flow.
"""

from typing import Tuple, Set
from .tool_registry import ToolRegistry
from .prompt_manager import PromptManager


class InvestigationStrategy:
    """Manages the business logic for investigation flow."""

    def __init__(self, tool_registry: ToolRegistry, prompt_manager: PromptManager):
        self.tool_registry = tool_registry
        self.prompt_manager = prompt_manager

    def should_continue_investigation(
        self, parsed_query, original_query: str, tools_used: Set[str]
    ) -> Tuple[bool, str]:
        """Determine if investigation should continue and what prompt to use."""
        required_tools = self.tool_registry.get_required_tools(
            parsed_query, original_query
        )
        missing_tools = required_tools - tools_used

        if missing_tools:
            prompt = self.prompt_manager.get_missing_tools_prompt(
                required_tools, tools_used, missing_tools
            )
            return True, prompt
        else:
            prompt = self.prompt_manager.get_complete_analysis_prompt()
            return False, prompt
