"""
Tool Result Processor for intelligent data extraction and context preservation.

This module processes raw tool results to extract key insights while maintaining
full structured data for cross-tool correlation and investigation analysis.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class ProcessedToolResult:
    """Structured representation of processed tool result with key insights."""

    tool_name: str
    raw_data: Dict[str, Any]
    key_insights: List[str]
    structured_findings: Dict[str, Any]
    investigation_context: Dict[str, Any]
    follow_up_suggestions: List[str]
    admin_links_context: Dict[str, Any]

    def get_summary(self) -> str:
        """Get a concise summary for LLM context."""
        insights_str = "; ".join(self.key_insights[:3])  # Top 3 insights
        return f"{self.tool_name}: {insights_str}"

    def get_detailed_context(self) -> str:
        """Get detailed context for investigation analysis."""
        context_parts = []

        if self.key_insights:
            context_parts.append(f"Key Insights: {'; '.join(self.key_insights)}")

        if self.structured_findings:
            context_parts.append(f"Findings: {self.structured_findings}")

        if self.follow_up_suggestions:
            context_parts.append(
                f"Suggestions: {'; '.join(self.follow_up_suggestions)}"
            )

        return " | ".join(context_parts)


class ToolResultProcessor:
    """Processes tool results to extract key insights and maintain context."""

    def __init__(self):
        self.investigation_context = {}
        self.processed_results: Dict[str, ProcessedToolResult] = {}

    def process_tool_result(
        self,
        tool_name: str,
        raw_result: Dict[str, Any],
        investigation_context: Optional[Dict[str, Any]] = None,
    ) -> ProcessedToolResult:
        """Process a tool result and extract key insights."""

        # Defensive programming - ensure raw_result is a dictionary
        if not isinstance(raw_result, dict):
            return ProcessedToolResult(
                tool_name=tool_name,
                raw_data={
                    "error": f"Invalid result type: {type(raw_result)}, value: {raw_result}"
                },
                key_insights=[
                    f"Tool {tool_name} returned invalid data type: {type(raw_result)}"
                ],
                structured_findings={},
                investigation_context={},
                follow_up_suggestions=[
                    "Check database connection and query implementation"
                ],
                admin_links_context={},
            )

        # Update investigation context
        if investigation_context:
            self.investigation_context.update(investigation_context)

        # Process based on tool type
        if tool_name == "get_device_info":
            processed = self._process_device_info(raw_result)
        elif tool_name == "get_access_codes":
            processed = self._process_access_codes(raw_result)
        elif tool_name == "get_audit_logs":
            processed = self._process_audit_logs(raw_result)
        elif tool_name == "get_action_attempts":
            processed = self._process_action_attempts(raw_result)
        elif tool_name == "get_device_events":
            processed = self._process_device_events(raw_result)
        elif tool_name == "get_admin_links":
            processed = self._process_admin_links(raw_result)
        else:
            processed = self._process_generic_result(tool_name, raw_result)

        # Store for cross-tool correlation
        self.processed_results[tool_name] = processed

        return processed

    def _process_device_info(self, raw_result: Dict[str, Any]) -> ProcessedToolResult:
        """Process device info with focus on key device characteristics."""

        key_insights = []
        structured_findings = {}
        follow_up_suggestions = []
        admin_context = {}

        if "error" in raw_result:
            key_insights.append(f"Device lookup failed: {raw_result['error']}")
            follow_up_suggestions.append("Try get_third_party_device_info")
            return ProcessedToolResult(
                tool_name="get_device_info",
                raw_data=raw_result,
                key_insights=key_insights,
                structured_findings=structured_findings,
                investigation_context={},
                follow_up_suggestions=follow_up_suggestions,
                admin_links_context=admin_context,
            )

        # Extract key device characteristics
        device_type = raw_result.get("device_type", "unknown")
        display_name = raw_result.get("display_name", "unnamed")
        workspace_id = raw_result.get("workspace_id")

        key_insights.append(f"Device: {display_name} ({device_type})")

        # Analyze device status
        properties = raw_result.get("properties", {})
        if "online" in properties:
            status = "online" if properties["online"] else "offline"
            key_insights.append(f"Status: {status}")
            if not properties["online"]:
                follow_up_suggestions.append(
                    "Check device events for connectivity issues"
                )

        # Check for capabilities that might affect access code management
        capabilities = raw_result.get("capabilities_supported", [])
        if capabilities:
            access_code_caps = [cap for cap in capabilities if "access_code" in cap]
            if access_code_caps:
                structured_findings["access_code_capabilities"] = access_code_caps

        # Store context for other tools
        investigation_context = {
            "device_type": device_type,
            "display_name": display_name,
            "workspace_id": workspace_id,
            "device_online": properties.get("online"),
        }

        # Admin context
        admin_context = {
            "device_id": raw_result.get("device_id"),
            "workspace_id": workspace_id,
            "device_type": device_type,
        }

        return ProcessedToolResult(
            tool_name="get_device_info",
            raw_data=raw_result,
            key_insights=key_insights,
            structured_findings=structured_findings,
            investigation_context=investigation_context,
            follow_up_suggestions=follow_up_suggestions,
            admin_links_context=admin_context,
        )

    def _process_access_codes(self, raw_result: Dict[str, Any]) -> ProcessedToolResult:
        """Process access codes with focus on managed/unmanaged status and query relevance."""

        key_insights = []
        structured_findings = {}
        follow_up_suggestions = []
        admin_context = {}

        if "error" in raw_result:
            key_insights.append(f"Access codes lookup failed: {raw_result['error']}")
            return ProcessedToolResult(
                tool_name="get_access_codes",
                raw_data=raw_result,
                key_insights=key_insights,
                structured_findings=structured_findings,
                investigation_context={},
                follow_up_suggestions=follow_up_suggestions,
                admin_links_context=admin_context,
            )

        access_codes = raw_result.get("access_codes", [])
        total_codes = len(access_codes)

        if total_codes == 0:
            key_insights.append("No access codes found")
            return ProcessedToolResult(
                tool_name="get_access_codes",
                raw_data=raw_result,
                key_insights=key_insights,
                structured_findings=structured_findings,
                investigation_context={},
                follow_up_suggestions=follow_up_suggestions,
                admin_links_context=admin_context,
            )

        # Analyze managed vs unmanaged
        managed_codes = [code for code in access_codes if code.get("is_managed", True)]
        unmanaged_codes = [
            code for code in access_codes if not code.get("is_managed", True)
        ]

        key_insights.append(
            f"Found {total_codes} access codes ({len(managed_codes)} managed, {len(unmanaged_codes)} unmanaged)"
        )

        # Look for codes mentioned in investigation context
        query_codes = self.investigation_context.get("access_codes", [])
        mentioned_codes = []

        for query_code in query_codes:
            # Look for exact matches or partial matches
            for code in access_codes:
                code_value = str(code.get("code", ""))
                code_name = code.get("name", "")
                code_id = code.get("access_code_id", "")

                if (
                    query_code == code_value
                    or query_code == code_id
                    or query_code in code_name
                ):
                    mentioned_codes.append(
                        {
                            "query_reference": query_code,
                            "found_code": code,
                            "match_type": "exact"
                            if query_code == code_value
                            else "id"
                            if query_code == code_id
                            else "name",
                        }
                    )

        if mentioned_codes:
            for match in mentioned_codes:
                code = match["found_code"]
                managed_status = (
                    "managed" if code.get("is_managed", True) else "unmanaged"
                )
                key_insights.append(
                    f"Query code '{match['query_reference']}' found: {code.get('name', 'unnamed')} ({managed_status})"
                )

                # If unmanaged code matches query, this is significant
                if not code.get("is_managed", True):
                    follow_up_suggestions.append(
                        "Check audit logs for this code's management history"
                    )

        # Check for unusual patterns
        if len(unmanaged_codes) > len(managed_codes):
            key_insights.append(
                f"Unusual: More unmanaged ({len(unmanaged_codes)}) than managed codes ({len(managed_codes)})"
            )
            follow_up_suggestions.append("Investigate device sync issues")

        # Pagination handling
        pagination = raw_result.get("pagination", {})
        if pagination.get("has_more"):
            follow_up_suggestions.append(
                f"More codes available (use limit={pagination.get('suggested_next_limit', 50)})"
            )

        structured_findings = {
            "total_codes": total_codes,
            "managed_count": len(managed_codes),
            "unmanaged_count": len(unmanaged_codes),
            "mentioned_codes": mentioned_codes,
            "has_more_data": pagination.get("has_more", False),
        }

        # Admin context for specific codes
        admin_context = {
            "device_id": raw_result.get("device_id"),
            "workspace_id": raw_result.get("workspace_id"),
            "mentioned_code_ids": [
                match["found_code"].get("access_code_id")
                for match in mentioned_codes
                if match["found_code"].get("access_code_id")
            ],
            "unmanaged_code_ids": [
                code.get("access_code_id")
                for code in unmanaged_codes
                if code.get("access_code_id")
            ],
        }

        return ProcessedToolResult(
            tool_name="get_access_codes",
            raw_data=raw_result,
            key_insights=key_insights,
            structured_findings=structured_findings,
            investigation_context={"access_codes_analysis": structured_findings},
            follow_up_suggestions=follow_up_suggestions,
            admin_links_context=admin_context,
        )

    def _process_audit_logs(self, raw_result: Dict[str, Any]) -> ProcessedToolResult:
        """Process audit logs with focus on timeline and access code changes."""

        key_insights = []
        structured_findings = {}
        follow_up_suggestions = []
        admin_context = {}

        if "error" in raw_result:
            key_insights.append(f"Audit logs lookup failed: {raw_result['error']}")
            return ProcessedToolResult(
                tool_name="get_audit_logs",
                raw_data=raw_result,
                key_insights=key_insights,
                structured_findings=structured_findings,
                investigation_context={},
                follow_up_suggestions=follow_up_suggestions,
                admin_links_context=admin_context,
            )

        audit_logs = raw_result.get("audit_logs", [])
        total_logs = len(audit_logs)

        if total_logs == 0:
            key_insights.append("No audit log entries found")
            return ProcessedToolResult(
                tool_name="get_audit_logs",
                raw_data=raw_result,
                key_insights=key_insights,
                structured_findings=structured_findings,
                investigation_context={},
                follow_up_suggestions=follow_up_suggestions,
                admin_links_context=admin_context,
            )

        key_insights.append(f"Found {total_logs} audit log entries")

        # Analyze log types
        log_actions = {}
        access_code_changes = []

        for log in audit_logs:
            action = log.get("action", "unknown")
            log_actions[action] = log_actions.get(action, 0) + 1

            # Look for access code related changes
            table = log.get("table", "")
            if "access_code" in table.lower():
                access_code_changes.append(log)

        if log_actions:
            action_summary = ", ".join(
                [f"{count} {action}" for action, count in log_actions.items()]
            )
            key_insights.append(f"Actions: {action_summary}")

        # Analyze access code changes specifically
        if access_code_changes:
            key_insights.append(f"Found {len(access_code_changes)} access code changes")

            # Look for management status changes
            management_changes = []
            for change in access_code_changes:
                old_values = change.get("old_values", {})
                new_values = change.get("new_values", {})

                if "is_managed" in old_values or "is_managed" in new_values:
                    management_changes.append(
                        {
                            "timestamp": change.get("timestamp"),
                            "action": change.get("action"),
                            "old_managed": old_values.get("is_managed"),
                            "new_managed": new_values.get("is_managed"),
                            "code_name": new_values.get("name")
                            or old_values.get("name"),
                        }
                    )

            if management_changes:
                key_insights.append(
                    f"Found {len(management_changes)} management status changes"
                )
                structured_findings["management_changes"] = management_changes

                # Look for codes that went from managed to unmanaged
                unmanaged_transitions = [
                    change
                    for change in management_changes
                    if change["old_managed"] is True and change["new_managed"] is False
                ]

                if unmanaged_transitions:
                    key_insights.append(
                        f"Alert: {len(unmanaged_transitions)} codes changed from managed to unmanaged"
                    )
                    follow_up_suggestions.append(
                        "Investigate sync issues causing managed->unmanaged transitions"
                    )

        # Check for timeline correlation with query
        query_time_refs = self.investigation_context.get("time_references", [])
        if query_time_refs and audit_logs:
            # Simple time correlation (could be enhanced with actual date parsing)
            recent_logs = audit_logs[:5]  # Most recent logs
            key_insights.append(
                f"Recent activity: {len(recent_logs)} recent audit entries"
            )

        # Pagination handling
        pagination = raw_result.get("pagination", {})
        if pagination.get("has_more"):
            follow_up_suggestions.append(
                f"More audit data available (use limit={pagination.get('suggested_next_limit', 50)})"
            )

        structured_findings.update(
            {
                "total_entries": total_logs,
                "action_breakdown": log_actions,
                "access_code_changes_count": len(access_code_changes),
                "has_management_changes": len(management_changes) > 0
                if access_code_changes
                else False,
                "has_more_data": pagination.get("has_more", False),
            }
        )

        admin_context = {
            "device_id": raw_result.get("device_id"),
            "audit_timeframe": "recent" if total_logs > 0 else None,
            "has_access_code_changes": len(access_code_changes) > 0,
        }

        return ProcessedToolResult(
            tool_name="get_audit_logs",
            raw_data=raw_result,
            key_insights=key_insights,
            structured_findings=structured_findings,
            investigation_context={"audit_analysis": structured_findings},
            follow_up_suggestions=follow_up_suggestions,
            admin_links_context=admin_context,
        )

    def _process_action_attempts(
        self, raw_result: Dict[str, Any]
    ) -> ProcessedToolResult:
        """Process action attempts with focus on failures and timing patterns."""

        key_insights = []
        structured_findings = {}
        follow_up_suggestions = []
        admin_context = {}

        if "error" in raw_result:
            key_insights.append(f"Action attempts lookup failed: {raw_result['error']}")
            return ProcessedToolResult(
                tool_name="get_action_attempts",
                raw_data=raw_result,
                key_insights=key_insights,
                structured_findings=structured_findings,
                investigation_context={},
                follow_up_suggestions=follow_up_suggestions,
                admin_links_context=admin_context,
            )

        action_attempts = raw_result.get("action_attempts", [])
        total_attempts = len(action_attempts)

        if total_attempts == 0:
            key_insights.append("No action attempts found")
            return ProcessedToolResult(
                tool_name="get_action_attempts",
                raw_data=raw_result,
                key_insights=key_insights,
                structured_findings=structured_findings,
                investigation_context={},
                follow_up_suggestions=follow_up_suggestions,
                admin_links_context=admin_context,
            )

        # Analyze success/failure patterns
        successful = [
            attempt for attempt in action_attempts if attempt.get("status") == "success"
        ]
        failed = [
            attempt for attempt in action_attempts if attempt.get("status") != "success"
        ]

        success_rate = len(successful) / total_attempts if total_attempts > 0 else 0

        key_insights.append(
            f"Found {total_attempts} action attempts ({len(successful)} success, {len(failed)} failed)"
        )

        if success_rate < 0.9 and len(failed) > 0:  # Less than 90% success rate
            key_insights.append(f"Low success rate: {success_rate:.1%}")
            follow_up_suggestions.append(
                "Investigate failure patterns and error messages"
            )

        # Analyze action types
        action_types = {}
        failed_by_type = {}

        for attempt in action_attempts:
            action_type = attempt.get("action_type", "unknown")
            action_types[action_type] = action_types.get(action_type, 0) + 1

            if attempt.get("status") != "success":
                failed_by_type[action_type] = failed_by_type.get(action_type, 0) + 1

        if action_types:
            type_summary = ", ".join(
                [
                    f"{count} {action_type}"
                    for action_type, count in action_types.items()
                ]
            )
            key_insights.append(f"Action types: {type_summary}")

        # Focus on access code related failures
        access_code_failures = [
            attempt
            for attempt in failed
            if "access_code" in attempt.get("action_type", "").lower()
        ]

        if access_code_failures:
            key_insights.append(
                f"Found {len(access_code_failures)} access code failures"
            )

            # Extract error patterns
            error_patterns = {}
            for failure in access_code_failures:
                error = failure.get("error", {})
                error_type = error.get("type", "unknown_error")
                error_patterns[error_type] = error_patterns.get(error_type, 0) + 1

            if error_patterns:
                structured_findings["access_code_error_patterns"] = error_patterns
                follow_up_suggestions.append(
                    "Correlate access code failures with audit log timing"
                )

        # Pagination handling
        pagination = raw_result.get("pagination", {})
        if pagination.get("has_more"):
            follow_up_suggestions.append(
                f"More attempts available (use limit={pagination.get('suggested_next_limit', 50)})"
            )

        structured_findings.update(
            {
                "total_attempts": total_attempts,
                "success_count": len(successful),
                "failure_count": len(failed),
                "success_rate": success_rate,
                "action_type_breakdown": action_types,
                "has_access_code_failures": len(access_code_failures) > 0,
                "has_more_data": pagination.get("has_more", False),
            }
        )

        admin_context = {
            "device_id": raw_result.get("device_id"),
            "workspace_id": raw_result.get("workspace_id"),
            "has_failures": len(failed) > 0,
            "failure_types": list(failed_by_type.keys()) if failed_by_type else [],
        }

        return ProcessedToolResult(
            tool_name="get_action_attempts",
            raw_data=raw_result,
            key_insights=key_insights,
            structured_findings=structured_findings,
            investigation_context={"action_attempts_analysis": structured_findings},
            follow_up_suggestions=follow_up_suggestions,
            admin_links_context=admin_context,
        )

    def _process_device_events(self, raw_result: Dict[str, Any]) -> ProcessedToolResult:
        """Process device events with focus on connectivity and status changes."""

        key_insights = []
        structured_findings = {}
        follow_up_suggestions = []
        admin_context = {}

        if "error" in raw_result:
            key_insights.append(f"Device events lookup failed: {raw_result['error']}")
            return ProcessedToolResult(
                tool_name="get_device_events",
                raw_data=raw_result,
                key_insights=key_insights,
                structured_findings=structured_findings,
                investigation_context={},
                follow_up_suggestions=follow_up_suggestions,
                admin_links_context=admin_context,
            )

        device_events = raw_result.get("device_events", [])
        total_events = len(device_events)

        if total_events == 0:
            key_insights.append("No device events found")
            return ProcessedToolResult(
                tool_name="get_device_events",
                raw_data=raw_result,
                key_insights=key_insights,
                structured_findings=structured_findings,
                investigation_context={},
                follow_up_suggestions=follow_up_suggestions,
                admin_links_context=admin_context,
            )

        key_insights.append(f"Found {total_events} device events")

        # Analyze event types
        event_types = {}
        connectivity_events = []

        for event in device_events:
            event_type = event.get("event_type", "unknown")
            event_types[event_type] = event_types.get(event_type, 0) + 1

            # Look for connectivity related events
            if any(
                keyword in event_type.lower()
                for keyword in ["connect", "disconnect", "online", "offline"]
            ):
                connectivity_events.append(event)

        if event_types:
            type_summary = ", ".join(
                [f"{count} {event_type}" for event_type, count in event_types.items()]
            )
            key_insights.append(f"Event types: {type_summary}")

        if connectivity_events:
            key_insights.append(f"Found {len(connectivity_events)} connectivity events")
            follow_up_suggestions.append(
                "Correlate connectivity events with access code issues"
            )

        structured_findings = {
            "total_events": total_events,
            "event_type_breakdown": event_types,
            "connectivity_events_count": len(connectivity_events),
            "has_more_data": raw_result.get("pagination", {}).get("has_more", False),
        }

        admin_context = {
            "device_id": raw_result.get("device_id"),
            "workspace_id": raw_result.get("workspace_id"),
            "has_connectivity_events": len(connectivity_events) > 0,
        }

        return ProcessedToolResult(
            tool_name="get_device_events",
            raw_data=raw_result,
            key_insights=key_insights,
            structured_findings=structured_findings,
            investigation_context={"device_events_analysis": structured_findings},
            follow_up_suggestions=follow_up_suggestions,
            admin_links_context=admin_context,
        )

    def _process_admin_links(self, raw_result: Dict[str, Any]) -> ProcessedToolResult:
        """Process admin links result."""

        key_insights = []
        structured_findings = {}

        admin_links = raw_result.get("admin_links", [])
        if admin_links:
            key_insights.append(f"Generated {len(admin_links)} admin links")
            structured_findings["links_generated"] = len(admin_links)

        return ProcessedToolResult(
            tool_name="get_admin_links",
            raw_data=raw_result,
            key_insights=key_insights,
            structured_findings=structured_findings,
            investigation_context={},
            follow_up_suggestions=[],
            admin_links_context={},
        )

    def _process_generic_result(
        self, tool_name: str, raw_result: Dict[str, Any]
    ) -> ProcessedToolResult:
        """Process unknown tool results with basic analysis."""

        key_insights = []
        structured_findings = {}

        if "error" in raw_result:
            key_insights.append(f"{tool_name} failed: {raw_result['error']}")
        else:
            # Basic analysis of result structure
            data_keys = [
                k for k in raw_result.keys() if k not in ["pagination", "metadata"]
            ]
            if data_keys:
                key_insights.append(
                    f"{tool_name} returned data: {', '.join(data_keys)}"
                )

        return ProcessedToolResult(
            tool_name=tool_name,
            raw_data=raw_result,
            key_insights=key_insights,
            structured_findings=structured_findings,
            investigation_context={},
            follow_up_suggestions=[],
            admin_links_context={},
        )

    def get_cross_tool_insights(self) -> List[str]:
        """Generate insights by correlating data across multiple tool results."""

        insights = []

        # Check for access code sync issues
        if (
            "get_access_codes" in self.processed_results
            and "get_audit_logs" in self.processed_results
        ):
            access_codes_result = self.processed_results["get_access_codes"]
            audit_logs_result = self.processed_results["get_audit_logs"]

            unmanaged_count = access_codes_result.structured_findings.get(
                "unmanaged_count", 0
            )
            has_management_changes = audit_logs_result.structured_findings.get(
                "has_management_changes", False
            )

            if unmanaged_count > 0 and has_management_changes:
                insights.append(
                    f"Pattern detected: {unmanaged_count} unmanaged codes with audit trail of management changes"
                )

        # Check for action attempt failures correlating with access code issues
        if (
            "get_action_attempts" in self.processed_results
            and "get_access_codes" in self.processed_results
        ):
            attempts_result = self.processed_results["get_action_attempts"]
            access_codes_result = self.processed_results["get_access_codes"]

            has_access_code_failures = attempts_result.structured_findings.get(
                "has_access_code_failures", False
            )
            unmanaged_count = access_codes_result.structured_findings.get(
                "unmanaged_count", 0
            )

            if has_access_code_failures and unmanaged_count > 0:
                insights.append(
                    "Correlation: Access code failures may have resulted in unmanaged codes"
                )

        return insights

    def get_comprehensive_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of all processed results with cross-correlations."""

        summary = {
            "tools_processed": list(self.processed_results.keys()),
            "key_insights": [],
            "cross_tool_insights": self.get_cross_tool_insights(),
            "follow_up_suggestions": [],
            "admin_context": {},
        }

        # Collect insights from all tools
        for result in self.processed_results.values():
            summary["key_insights"].extend(result.key_insights)
            summary["follow_up_suggestions"].extend(result.follow_up_suggestions)
            summary["admin_context"].update(result.admin_links_context)

        return summary
