"""
Tool registry for mapping issue types to required investigation tools.
"""

from typing import Set


class ToolRegistry:
    """Manages mapping of issue types to required tools."""

    @staticmethod
    def get_required_tools(parsed_query, original_query: str) -> Set[str]:
        """Determine required tools based on issue type and content."""
        required_tools = set()

        # Check for access code related issues
        if (
            parsed_query.question_type == "access_code"
            or "access_code" in original_query.lower()
            or "unmanaged code" in original_query.lower()
            or "code" in original_query.lower()
            and (
                "created" in original_query.lower()
                or "marked" in original_query.lower()
            )
            or len(parsed_query.access_codes) > 0
        ):
            required_tools = {"get_access_codes", "get_audit_logs"}
        elif (
            "connection" in original_query.lower()
            or "offline" in original_query.lower()
        ):
            required_tools = {"get_device_events"}
        elif "unlock" in original_query.lower() or "lock" in original_query.lower():
            required_tools = {"get_action_attempts"}

        # Always include device info as baseline
        required_tools.add("get_device_info")
        return required_tools
