"""
Dynamic tool selection based on investigation state and previous results.
"""

from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum

from seam_agent.assistant.query_parser import ParsedQuery
from seam_agent.assistant.investigation_config import (
    InvestigationState,
    InvestigationConfig,
)


class InvestigationPhase(Enum):
    """Current phase of the investigation."""

    INITIAL = "initial"
    GATHERING = "gathering"
    ANALYZING = "analyzing"
    DEEP_DIVE = "deep_dive"
    FINALIZING = "finalizing"


@dataclass
class ToolResult:
    """Structured representation of a tool result for decision making."""

    tool_name: str
    success: bool
    data_found: bool
    needs_followup: bool
    key_findings: List[str]
    raw_result: Dict[str, Any]

    @classmethod
    def from_raw_result(
        cls, tool_name: str, raw_result: Dict[str, Any]
    ) -> "ToolResult":
        """Create a ToolResult from raw tool output."""
        success = "error" not in raw_result
        data_found = cls._has_meaningful_data(tool_name, raw_result)
        needs_followup = cls._needs_followup(tool_name, raw_result)
        key_findings = cls._extract_key_findings(tool_name, raw_result)

        return cls(
            tool_name=tool_name,
            success=success,
            data_found=data_found,
            needs_followup=needs_followup,
            key_findings=key_findings,
            raw_result=raw_result,
        )

    @staticmethod
    def _has_meaningful_data(tool_name: str, result: Dict[str, Any]) -> bool:
        """Check if the tool result contains meaningful data."""
        if "error" in result:
            return False

        if tool_name == "get_device_info":
            return "device_type" in result and result.get("device_type") != "unknown"
        elif tool_name == "get_access_codes":
            codes = result.get("access_codes", [])
            return len(codes) > 0
        elif tool_name == "get_action_attempts":
            attempts = result.get("action_attempts", [])
            return len(attempts) > 0
        elif tool_name == "get_device_events":
            events = result.get("device_events", [])
            return len(events) > 0
        elif tool_name == "get_audit_logs":
            logs = result.get("audit_logs", [])
            return len(logs) > 0

        return True

    @staticmethod
    def _needs_followup(tool_name: str, result: Dict[str, Any]) -> bool:
        """Check if this tool result suggests more data is needed."""
        if "error" in result:
            return False

        # Check pagination
        pagination = result.get("pagination", {})
        if pagination.get("has_more", False):
            return True

        # Device info failure might need third-party lookup
        if tool_name == "get_device_info" and "error" in result:
            return True

        return False

    @staticmethod
    def _extract_key_findings(tool_name: str, result: Dict[str, Any]) -> List[str]:
        """Extract key findings from tool result."""
        findings = []

        if tool_name == "get_device_info":
            if "device_type" in result:
                findings.append(f"Device type: {result['device_type']}")
            if result.get("properties", {}).get("online") is False:
                findings.append("Device is offline")

        elif tool_name == "get_action_attempts":
            attempts = result.get("action_attempts", [])
            if attempts:
                success_count = sum(1 for a in attempts if a.get("status") == "success")
                failed_count = len(attempts) - success_count
                if failed_count > 0:
                    findings.append(f"{failed_count} failed action attempts found")

        elif tool_name == "get_access_codes":
            codes = result.get("access_codes", [])
            unmanaged_codes = [c for c in codes if c.get("is_managed") is False]
            if unmanaged_codes:
                findings.append(f"{len(unmanaged_codes)} unmanaged access codes found")

        return findings


class DynamicToolSelector:
    """Intelligent tool selection based on investigation state and findings."""

    def __init__(self):
        self.investigation_phase = InvestigationPhase.INITIAL
        self.tool_results: Dict[str, ToolResult] = {}
        self.investigation_context: Dict[str, Any] = {}

    def select_initial_tools(
        self, parsed_query: ParsedQuery, original_query: str
    ) -> List[str]:
        """Select the initial set of tools based on the query."""
        self.investigation_phase = InvestigationPhase.INITIAL
        tools = []

        # Always start with device info as foundation
        tools.append("get_device_info")

        # Select specific tools based on query analysis
        if self._is_access_code_issue(parsed_query, original_query):
            tools.extend(["get_access_codes", "get_audit_logs"])
        elif self._is_connectivity_issue(parsed_query, original_query):
            tools.extend(["get_device_events"])
        elif self._is_action_issue(parsed_query, original_query):
            tools.extend(["get_action_attempts"])
        else:
            # For unclear issues, start broad
            tools.extend(["get_action_attempts", "get_device_events"])

        return tools

    def select_followup_tools(
        self,
        previous_results: Dict[str, Dict[str, Any]],
        investigation_state: InvestigationState,
        config: InvestigationConfig,
        parsed_query: ParsedQuery,
    ) -> List[str]:
        """Select follow-up tools based on previous results and current state."""

        # Update our understanding with new results
        for tool_name, raw_result in previous_results.items():
            self.tool_results[tool_name] = ToolResult.from_raw_result(
                tool_name, raw_result
            )

        # Update investigation phase
        self._update_investigation_phase(investigation_state)

        # Check if we have budget for more tools
        if not investigation_state.can_continue_round(config):
            return []

        followup_tools = []

        # Handle pagination needs first (high priority)
        for tool_name, result in self.tool_results.items():
            if result.needs_followup and investigation_state.can_continue_round(config):
                followup_tools.append(self._get_pagination_tool_call(tool_name, result))

        # Add tools based on findings if we have budget
        if investigation_state.can_continue_round(config):
            followup_tools.extend(self._select_analytical_tools(parsed_query))

        # Always include admin links last if we haven't used it yet
        if (
            "get_admin_links" not in self.tool_results
            and investigation_state.can_continue_round(config)
        ):
            followup_tools.append("get_admin_links")

        return followup_tools[
            : config.MAX_TOOLS_PER_ROUND - investigation_state.tools_used_this_round
        ]

    def should_continue_investigation(
        self, investigation_state: InvestigationState, config: InvestigationConfig
    ) -> tuple[bool, str]:
        """Determine if investigation should continue and provide reasoning."""

        # Check hard limits first
        if not investigation_state.can_start_new_round(config):
            return False, "Investigation limits reached"

        # Check if we have sufficient data for analysis
        if self._has_sufficient_data():
            return False, "Sufficient data gathered for analysis"

        # Check if we have critical failures that need addressing
        if self._has_critical_failures():
            return True, "Critical failures detected, need more investigation"

        # Default to continuing if we have budget and incomplete data
        return True, "Investigation incomplete, continuing with additional tools"

    def get_investigation_summary(self) -> Dict[str, Any]:
        """Get a summary of the current investigation state."""
        return {
            "phase": self.investigation_phase.value,
            "tools_used": list(self.tool_results.keys()),
            "key_findings": [
                finding
                for result in self.tool_results.values()
                for finding in result.key_findings
            ],
            "needs_followup": [
                name
                for name, result in self.tool_results.items()
                if result.needs_followup
            ],
            "data_quality": self._assess_data_quality(),
        }

    def _is_access_code_issue(
        self, parsed_query: ParsedQuery, original_query: str
    ) -> bool:
        """Check if this is primarily an access code issue."""
        return (
            parsed_query.question_type == "access_code"
            or "access_code" in original_query.lower()
            or "unmanaged code" in original_query.lower()
            or len(parsed_query.access_codes) > 0
            or (
                "code" in original_query.lower()
                and any(
                    word in original_query.lower()
                    for word in ["created", "marked", "working", "failed"]
                )
            )
        )

    def _is_connectivity_issue(
        self, parsed_query: ParsedQuery, original_query: str
    ) -> bool:
        """Check if this is primarily a connectivity issue."""
        return any(
            word in original_query.lower()
            for word in [
                "offline",
                "online",
                "connection",
                "connectivity",
                "network",
                "disconnected",
            ]
        )

    def _is_action_issue(self, parsed_query: ParsedQuery, original_query: str) -> bool:
        """Check if this is primarily an action/operation issue."""
        return any(
            word in original_query.lower()
            for word in ["unlock", "lock", "failed", "error", "attempt", "operation"]
        )

    def _update_investigation_phase(
        self, investigation_state: InvestigationState
    ) -> None:
        """Update the current investigation phase based on progress."""
        if investigation_state.tool_rounds_used == 1:
            self.investigation_phase = InvestigationPhase.GATHERING
        elif investigation_state.tool_rounds_used == 2:
            self.investigation_phase = InvestigationPhase.ANALYZING
        elif investigation_state.tool_rounds_used >= 3:
            self.investigation_phase = InvestigationPhase.DEEP_DIVE

    def _get_pagination_tool_call(self, tool_name: str, result: ToolResult) -> str:
        """Get the appropriate tool call for pagination."""
        # For now, return the same tool name - the orchestrator will handle pagination logic
        return tool_name

    def _select_analytical_tools(self, parsed_query: ParsedQuery) -> List[str]:
        """Select tools for deeper analysis based on current findings."""
        analytical_tools = []

        # If device info failed, try third-party lookup
        device_result = self.tool_results.get("get_device_info")
        if device_result and not device_result.success:
            analytical_tools.append("get_third_party_device_info")

        # If we found failed actions but no audit logs, get audit logs
        action_result = self.tool_results.get("get_action_attempts")
        if (
            action_result
            and action_result.data_found
            and "get_audit_logs" not in self.tool_results
            and any("failed" in finding for finding in action_result.key_findings)
        ):
            analytical_tools.append("get_audit_logs")

        # If we have access code issues but no device events, get events
        code_result = self.tool_results.get("get_access_codes")
        if (
            code_result
            and code_result.data_found
            and "get_device_events" not in self.tool_results
        ):
            analytical_tools.append("get_device_events")

        return analytical_tools

    def _has_sufficient_data(self) -> bool:
        """Check if we have enough data for a meaningful analysis."""
        # Need at least device info and one other data source
        has_device_info = "get_device_info" in self.tool_results
        has_additional_data = (
            len([r for r in self.tool_results.values() if r.data_found]) >= 2
        )

        return has_device_info and has_additional_data

    def _has_critical_failures(self) -> bool:
        """Check if there are critical failures that need more investigation."""
        return any(
            not result.success
            and result.tool_name in ["get_device_info", "get_access_codes"]
            for result in self.tool_results.values()
        )

    def _assess_data_quality(self) -> str:
        """Assess the overall quality of data gathered."""
        if not self.tool_results:
            return "no_data"

        successful_tools = sum(1 for r in self.tool_results.values() if r.success)
        data_tools = sum(1 for r in self.tool_results.values() if r.data_found)
        total_tools = len(self.tool_results)

        if successful_tools == total_tools and data_tools >= 2:
            return "excellent"
        elif successful_tools >= total_tools * 0.8 and data_tools >= 1:
            return "good"
        elif successful_tools >= total_tools * 0.5:
            return "fair"
        else:
            return "poor"
