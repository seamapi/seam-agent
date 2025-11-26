"""
Tool orchestrator for managing tool execution and result summarization.
"""

from typing import Dict, Any, Optional, List
from anthropic.types import ToolParam

from seam_agent.connectors.db import DatabaseClient
from seam_agent.connectors.seam_api import SeamAPIClient
from seam_agent.connectors.admin_links import AdminLinksConnector
from seam_agent.assistant.investigation_logger import InvestigationLogger, LogContext
from seam_agent.assistant.tool_result_processor import (
    ToolResultProcessor,
    ProcessedToolResult,
)


class ToolOrchestrator:
    """Manages tool execution and result summarization with intelligent data processing."""

    db_client: DatabaseClient
    seam_client: SeamAPIClient
    admin_links_client: AdminLinksConnector
    logger: InvestigationLogger
    result_processor: ToolResultProcessor

    def __init__(
        self,
        db_client,
        seam_client,
        logger: Optional[InvestigationLogger] = None,
        admin_base_url: Optional[str] = None,
    ):
        self.db_client = db_client
        self.seam_client = seam_client
        self.admin_links_client = AdminLinksConnector(
            admin_base_url or "https://connect.getseam.com/admin"
        )
        self.logger = logger or InvestigationLogger()
        self.result_processor = ToolResultProcessor()
        self._executed_tools_cache = {}  # Cache tool results to prevent hallucinations

    def get_tool_definitions(self) -> list[ToolParam]:
        """Get the tool definitions for Anthropic API."""
        return [
            {
                "name": "get_device_info",
                "description": "Get comprehensive device information from the database including properties, status, and third-party details. IMPORTANT: The result includes workspace_id which you MUST use for subsequent tools that require workspace_id parameter.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "device_id": {
                            "type": "string",
                            "description": "The device ID to lookup",
                        }
                    },
                    "required": ["device_id"],
                },
            },
            {
                "name": "get_third_party_device_info",
                "description": "Get third-party device information when main device query fails or additional details needed",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "third_party_device_id": {
                            "type": "string",
                            "description": "The third-party device ID to lookup",
                        }
                    },
                    "required": ["third_party_device_id"],
                },
            },
            {
                "name": "get_action_attempts",
                "description": "Get action attempts for a device to see what operations were tried and their success/failure status. Returns pagination info - if 'has_more': true, call again with suggested_next_limit to see the complete history. For troubleshooting failed operations or timeline analysis, you typically need more than the default 10 attempts to understand patterns and root causes. IMPORTANT: Use the workspace_id from get_device_info result, never use placeholders.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "device_id": {
                            "type": "string",
                            "description": "The device ID to lookup",
                        },
                        "workspace_id": {
                            "type": "string",
                            "description": "The workspace ID for filtering - get this from get_device_info result, not a placeholder",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (default 10, range 1-100). Increase for comprehensive troubleshooting.",
                            "default": 10,
                        },
                    },
                    "required": ["device_id", "workspace_id"],
                },
            },
            {
                "name": "get_access_codes",
                "description": "Get access codes for a device. Returns pagination info to help you determine if more data is needed. If the response shows 'has_more': true, call this tool again with a higher limit (suggested_next_limit) to get complete data for thorough analysis. For troubleshooting unmanaged codes or missing codes, you often need to see ALL access codes, not just the first 10. IMPORTANT: Use the workspace_id from get_device_info result, never use placeholders.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "device_id": {
                            "type": "string",
                            "description": "The device ID to lookup",
                        },
                        "workspace_id": {
                            "type": "string",
                            "description": "The workspace ID for filtering - get this from get_device_info result, not a placeholder",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (default 10, range 1-100). Increase for comprehensive analysis.",
                            "default": 10,
                        },
                        "offset": {
                            "type": "integer",
                            "description": "Number of records to skip for pagination (default 0)",
                            "default": 0,
                        },
                    },
                    "required": ["device_id", "workspace_id"],
                },
            },
            {
                "name": "get_audit_logs",
                "description": "Get audit logs for access code operations (INSERT/DELETE) on a device. Returns pagination info - if 'has_more': true, you should call again with suggested_next_limit to get the complete audit history. For investigating access code issues, timeline analysis, or finding when specific codes were created/deleted, you often need more than 10 entries to understand the full history.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "device_id": {
                            "type": "string",
                            "description": "The device ID to lookup",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (default 10, range 1-100). Increase for comprehensive audit history.",
                            "default": 10,
                        },
                    },
                    "required": ["device_id"],
                },
            },
            {
                "name": "get_device_events",
                "description": "Get events for a device to see what has happened (non-internal events only). Returns pagination info - if 'has_more': true, call again with suggested_next_limit to get complete event history. For troubleshooting connectivity issues, investigating device behavior patterns, or timeline analysis, you typically need more than 10 events to understand what's happening. IMPORTANT: Use the workspace_id from get_device_info result, never use placeholders.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "device_id": {
                            "type": "string",
                            "description": "The device ID to lookup",
                        },
                        "workspace_id": {
                            "type": "string",
                            "description": "The workspace ID for filtering - get this from get_device_info result, not a placeholder",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (default 10, range 1-100). Increase for comprehensive event history.",
                            "default": 10,
                        },
                    },
                    "required": ["device_id", "workspace_id"],
                },
            },
            {
                "name": "get_admin_links",
                "description": "Generate relevant admin page links for deeper investigation. Call this when you want to provide direct admin links for the support agent to continue investigation in the admin interface. Pass the investigation context including device_id, workspace_id, access_codes, etc.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "investigation_context": {
                            "type": "object",
                            "description": "Investigation context with device_id, workspace_id, access_codes, action_attempts, third_party_account_id, etc.",
                            "properties": {
                                "device_id": {"type": "string"},
                                "workspace_id": {"type": "string"},
                                "access_codes": {"type": "array"},
                                "action_attempts": {"type": "array"},
                                "third_party_account_id": {"type": "string"},
                            },
                        }
                    },
                    "required": ["investigation_context"],
                },
            },
        ]

    def summarize_tool_result(self, tool_name: str, result: Dict[str, Any]) -> str:
        """Create an intelligent summary that preserves critical debugging information."""

        if tool_name == "get_device_info":
            if "error" in result:
                return f"Device Info: {result['error']}"

            # Return the full device data as JSON for comprehensive context
            import json

            return (
                f"Device Info (Full Data):\n{json.dumps(result, indent=2, default=str)}"
            )

        elif tool_name == "get_access_codes":
            if "error" in result:
                return f"Access Codes: {result['error']}"

            codes = result.get("access_codes", [])
            pagination = result.get("pagination", {})
            count = len(codes)

            if count == 0:
                return "Access Codes: None found"

            # Critical debugging info: managed vs unmanaged status
            unmanaged_codes = [
                code for code in codes if not code.get("is_managed", True)
            ]

            status_info = []
            status_info.append(f"{count} total")

            if unmanaged_codes:
                status_info.append(f"{len(unmanaged_codes)} unmanaged")
                # Show unmanaged code names - critical for debugging
                unmanaged_names = [
                    code.get("name", "unnamed") for code in unmanaged_codes[:2]
                ]
                if unmanaged_names:
                    status_info.append(f"unmanaged: {', '.join(unmanaged_names)}")

            # Show sample codes with critical info
            sample_codes = []
            for code in codes[:3]:
                name = code.get("name", "unnamed")
                code_value = code.get("code", "N/A")
                managed_status = (
                    "managed" if code.get("is_managed", True) else "UNMANAGED"
                )
                sample_codes.append(f"{name}({code_value})-{managed_status}")

            summary = (
                f"Access Codes ({', '.join(status_info)}): {', '.join(sample_codes)}"
            )

            if count > 3:
                summary += f" and {count - 3} more"

            if pagination.get("has_more"):
                summary += f" - MORE DATA AVAILABLE (use limit={pagination.get('suggested_next_limit', 20)})"

            return summary

        elif tool_name == "get_audit_logs":
            if "error" in result:
                return f"Audit Logs: {result['error']}"

            logs = result.get("audit_logs", [])
            pagination = result.get("pagination", {})
            count = len(logs)

            if count == 0:
                return "Audit Logs: No entries found"

            # Critical debugging info: operation types and recent activity
            operations = {}
            recent_operations = []

            for log in logs:
                if isinstance(log, dict):
                    operation = log.get("operation", "unknown")
                    operations[operation] = operations.get(operation, 0) + 1

                    # Track recent operations for timeline
                    if len(recent_operations) < 3:
                        timestamp = log.get("created_at", "unknown")
                        recent_operations.append(f"{operation}@{timestamp}")

            # Build summary with operation breakdown
            op_summary = ", ".join(
                [f"{count} {op}" for op, count in operations.items()]
            )
            summary = f"Audit Logs: {count} entries ({op_summary})"

            # Add recent activity for timeline context
            if recent_operations:
                summary += f" | Recent: {', '.join(recent_operations)}"

            if pagination.get("has_more"):
                summary += f" - MORE DATA AVAILABLE (use limit={pagination.get('suggested_next_limit', 20)})"

            return summary

        elif tool_name == "get_action_attempts":
            if "error" in result:
                return f"Action Attempts: {result['error']}"

            attempts = result.get("action_attempts", [])
            pagination = result.get("pagination", {})
            count = len(attempts)

            if count == 0:
                return "Action Attempts: No attempts found"

            # Critical debugging info: success/failure patterns and error types
            success_count = sum(1 for a in attempts if a.get("status") == "success")
            failed_count = count - success_count

            # Analyze failure patterns - critical for debugging
            action_types = {}
            recent_failures = []

            for attempt in attempts:
                if isinstance(attempt, dict):
                    action_type = attempt.get("action_type", "unknown")
                    action_types[action_type] = action_types.get(action_type, 0) + 1

                    # Track recent failures for timeline
                    if attempt.get("status") != "success" and len(recent_failures) < 2:
                        timestamp = attempt.get("created_at", "unknown")
                        error = attempt.get("error", {})
                        error_type = (
                            error.get("type", "unknown")
                            if isinstance(error, dict)
                            else "unknown"
                        )
                        recent_failures.append(
                            f"{action_type}:{error_type}@{timestamp}"
                        )

            # Build comprehensive summary
            summary = f"Action Attempts: {count} total ({success_count} successful, {failed_count} failed)"

            # Add action type breakdown - helpful for understanding patterns
            if action_types:
                top_actions = sorted(
                    action_types.items(), key=lambda x: x[1], reverse=True
                )[:2]
                action_summary = ", ".join(
                    [f"{count} {action}" for action, count in top_actions]
                )
                summary += f" | Types: {action_summary}"

            # Add recent failure details - critical for debugging
            if recent_failures:
                summary += f" | Recent failures: {', '.join(recent_failures)}"

            if pagination.get("has_more"):
                summary += f" - MORE DATA AVAILABLE (use limit={pagination.get('suggested_next_limit', 20)})"

            return summary

        elif tool_name == "get_device_events":
            if "error" in result:
                return f"Device Events: {result['error']}"

            events = result.get("device_events", [])
            pagination = result.get("pagination", {})
            count = len(events)

            if count == 0:
                return "Device Events: No events found"

            # Critical debugging info: event types and connectivity patterns
            event_types = {}
            connectivity_events = []
            recent_events = []

            for event in events:
                if isinstance(event, dict):
                    event_type = event.get("event_type", "unknown")
                    event_types[event_type] = event_types.get(event_type, 0) + 1

                    # Track connectivity-related events - critical for diagnosis
                    if any(
                        keyword in event_type.lower()
                        for keyword in ["connect", "disconnect", "online", "offline"]
                    ):
                        if len(connectivity_events) < 2:
                            timestamp = event.get("occurred_at", "unknown")
                            connectivity_events.append(f"{event_type}@{timestamp}")

                    # Track recent events for timeline
                    if len(recent_events) < 3:
                        timestamp = event.get("occurred_at", "unknown")
                        recent_events.append(f"{event_type}@{timestamp}")

            # Build comprehensive summary
            summary = f"Device Events: {count} events"

            # Add event type breakdown
            if event_types:
                top_events = sorted(
                    event_types.items(), key=lambda x: x[1], reverse=True
                )[:2]
                event_summary = ", ".join(
                    [f"{count} {event}" for event, count in top_events]
                )
                summary += f" ({event_summary})"

            # Highlight connectivity events - critical for debugging connectivity issues
            if connectivity_events:
                summary += f" | Connectivity: {', '.join(connectivity_events)}"

            if pagination.get("has_more"):
                summary += f" - MORE DATA AVAILABLE (use limit={pagination.get('suggested_next_limit', 20)})"

            return summary

        elif tool_name == "get_admin_links":
            links = result.get("admin_links", [])
            count = len(links)
            if count > 0:
                # Include the actual URLs so the LLM can use them in analysis
                formatted_links = []
                for link in links:
                    title = link.get("title", "Unknown")
                    url = link.get("url", "")
                    description = link.get("description", "")
                    formatted_links.append(f"- [{title}]({url}) - {description}")

                summary = f"Admin Links ({count} generated):\n" + "\n".join(
                    formatted_links
                )
                return summary
            return "Admin Links: No relevant pages found"

        else:
            # Fallback for unknown tools - truncate the result
            result_str = str(result)
            if len(result_str) > 200:
                return f"{tool_name} result: {result_str[:200]}..."
            return f"{tool_name} result: {result_str}"

    async def execute_tool(self, tool_name: str, tool_input: Any) -> dict[str, Any]:
        """Execute a specific tool and return the result."""
        self.logger.tool_start(tool_name, tool_input)

        if tool_name == "get_device_info":
            device_id = tool_input["device_id"]
            self.logger.debug(
                f"Querying database for device: {device_id}", LogContext.DATABASE
            )
            try:
                device_info = await self.db_client.get_device_by_id(device_id)

                # Handle null/None response properly
                if device_info is None:
                    self.logger.warning(
                        "Device not found in main table", LogContext.DATABASE
                    )
                    return {"error": "Device not found"}

                # Ensure device_info is a dictionary (should always be from db.py but safety check)
                if not isinstance(device_info, dict):
                    self.logger.warning(
                        f"Database returned unexpected type {type(device_info)}: {device_info}",
                        LogContext.DATABASE,
                    )
                    return {
                        "error": f"Database returned unexpected format: {type(device_info)}"
                    }

                # Extract key findings for logging
                device_type = device_info.get("device_type", "unknown")
                is_online = (
                    device_info.get("properties", {}).get("online")
                    if isinstance(device_info.get("properties"), dict)
                    else None
                )
                key_findings = f"Device type: {device_type}" + (
                    f", online: {is_online}" if is_online is not None else ""
                )

                self.logger.tool_success(tool_name, len(str(device_info)), key_findings)
                # Cache result to prevent hallucinations in admin links
                self._executed_tools_cache[tool_name] = device_info
                return device_info

            except Exception as e:
                self.logger.tool_error(tool_name, str(e))
                return {"error": str(e)}

        elif tool_name == "get_access_codes":
            device_id = tool_input["device_id"]
            workspace_id = tool_input["workspace_id"]
            limit = tool_input.get("limit", 10)
            offset = tool_input.get("offset", 0)
            self.logger.debug(
                f"Querying access codes for device: {device_id} in workspace: {workspace_id}",
                LogContext.DATABASE,
            )
            try:
                access_codes = await self.db_client.get_access_codes(
                    device_id, workspace_id, limit, offset
                )

                # Check if there are more results by querying with limit + 1
                check_more = await self.db_client.get_access_codes(
                    device_id, workspace_id, limit + 1, offset
                )
                has_more = len(check_more) > limit

                key_findings = f"{len(access_codes)} access codes found"
                if has_more:
                    key_findings += " (more available)"

                self.logger.tool_success(
                    tool_name, len(str(access_codes)), key_findings
                )
                result = {
                    "access_codes": access_codes,
                    "pagination": {
                        "current_count": len(access_codes),
                        "has_more": has_more,
                        "next_offset": offset + len(access_codes) if has_more else None,
                        "suggested_next_limit": limit,
                    },
                }
                # Cache result to prevent hallucinations in admin links
                self._executed_tools_cache[tool_name] = result
                return result
            except Exception as e:
                self.logger.tool_error(tool_name, str(e))
                return {"error": str(e)}

        elif tool_name == "get_audit_logs":
            device_id = tool_input["device_id"]
            limit = tool_input.get("limit", 10)
            self.logger.debug(
                f"Querying audit logs for device: {device_id}", LogContext.DATABASE
            )
            try:
                audit_logs = await self.db_client.get_audit_logs(device_id, limit)

                # Check if there are more results by querying with limit + 1
                check_more = await self.db_client.get_audit_logs(device_id, limit + 1)
                has_more = len(check_more) > limit

                key_findings = f"{len(audit_logs)} audit log entries found"
                if has_more:
                    key_findings += " (more available)"

                self.logger.tool_success(tool_name, len(str(audit_logs)), key_findings)
                return {
                    "audit_logs": audit_logs,
                    "device_id": device_id,
                    "pagination": {
                        "current_count": len(audit_logs),
                        "has_more": has_more,
                        "suggested_next_limit": limit * 2 if has_more else limit,
                    },
                }
            except Exception as e:
                self.logger.tool_error(tool_name, str(e))
                return {"error": str(e)}

        elif tool_name == "get_action_attempts":
            device_id = tool_input["device_id"]
            workspace_id = tool_input["workspace_id"]
            limit = tool_input.get("limit", 10)
            self.logger.debug(
                f"Querying action attempts for device: {device_id} in workspace: {workspace_id}",
                LogContext.DATABASE,
            )
            try:
                action_attempts = await self.db_client.get_action_attempts(
                    device_id, workspace_id, limit
                )

                # Check if there are more results by querying with limit + 1
                check_more = await self.db_client.get_action_attempts(
                    device_id, workspace_id, limit + 1
                )
                has_more = len(check_more) > limit

                successful = sum(
                    1 for a in action_attempts if a.get("status") == "success"
                )
                key_findings = (
                    f"{len(action_attempts)} attempts ({successful} successful)"
                )
                if has_more:
                    key_findings += " (more available)"

                self.logger.tool_success(
                    tool_name, len(str(action_attempts)), key_findings
                )
                result = {
                    "action_attempts": action_attempts,
                    "device_id": device_id,
                    "workspace_id": workspace_id,
                    "pagination": {
                        "current_count": len(action_attempts),
                        "has_more": has_more,
                        "suggested_next_limit": limit * 2 if has_more else limit,
                    },
                }
                # Cache result to prevent hallucinations in admin links
                self._executed_tools_cache[tool_name] = result
                return result
            except Exception as e:
                self.logger.tool_error(tool_name, str(e))
                return {"error": str(e)}

        elif tool_name == "get_device_events":
            device_id = tool_input["device_id"]
            workspace_id = tool_input["workspace_id"]
            limit = tool_input.get("limit", 10)
            self.logger.debug(
                f"Querying device events for device: {device_id} in workspace: {workspace_id}",
                LogContext.DATABASE,
            )
            try:
                device_events = await self.db_client.get_device_events(
                    device_id, workspace_id, limit
                )

                # Check if there are more results by querying with limit + 1
                check_more = await self.db_client.get_device_events(
                    device_id, workspace_id, limit + 1
                )
                has_more = len(check_more) > limit

                key_findings = f"{len(device_events)} device events found"
                if has_more:
                    key_findings += " (more available)"

                self.logger.tool_success(
                    tool_name, len(str(device_events)), key_findings
                )
                return {
                    "device_events": device_events,
                    "device_id": device_id,
                    "workspace_id": workspace_id,
                    "pagination": {
                        "current_count": len(device_events),
                        "has_more": has_more,
                        "suggested_next_limit": limit * 2 if has_more else limit,
                    },
                }
            except Exception as e:
                self.logger.tool_error(tool_name, str(e))
                return {"error": str(e)}

        elif tool_name == "get_admin_links":
            investigation_context = tool_input["investigation_context"]
            self.logger.debug(
                "Generating admin links for investigation context",
                LogContext.TOOL_EXECUTION,
            )
            try:
                # AUTO-BUILD CONTEXT: Enhance context with data from previous tool executions
                enhanced_context = self._build_enhanced_investigation_context(
                    investigation_context
                )

                admin_links = self.admin_links_client.get_relevant_admin_links(
                    enhanced_context
                )
                key_findings = f"{len(admin_links)} relevant admin pages found"
                self.logger.tool_success(tool_name, len(str(admin_links)), key_findings)
                return {
                    "admin_links": admin_links,
                    "context_processed": enhanced_context,
                }
            except Exception as e:
                self.logger.tool_error(tool_name, str(e))
                return {"error": str(e)}

        else:
            self.logger.error(f"Unknown tool: {tool_name}", LogContext.TOOL_EXECUTION)
            return {"error": f"Unknown tool: {tool_name}"}

    async def process_and_execute_tool(
        self,
        tool_name: str,
        tool_input: Any,
        investigation_context: Optional[Dict[str, Any]] = None,
    ) -> ProcessedToolResult:
        """Execute a tool and return processed results with structured insights."""

        try:
            # Execute the tool normally
            raw_result = await self.execute_tool(tool_name, tool_input)

            # Debug logging
            self.logger.debug(
                f"Raw result type for {tool_name}: {type(raw_result)}",
                LogContext.TOOL_EXECUTION,
            )

            # Process with context
            processed_result = self.result_processor.process_tool_result(
                tool_name, raw_result, investigation_context
            )

            return processed_result

        except Exception as e:
            self.logger.error(
                f"Error in process_and_execute_tool for {tool_name}: {str(e)}",
                LogContext.TOOL_EXECUTION,
            )
            # Return a safe fallback result
            return self.result_processor.process_tool_result(
                tool_name,
                {"error": f"Processing failed: {str(e)}"},
                investigation_context,
            )

    def get_processed_summary(
        self, tool_name: str, processed_result: ProcessedToolResult
    ) -> str:
        """Get an intelligent summary that preserves key context for LLM."""

        # Use the processed insights instead of generic summarization
        summary_parts = []

        # Always include key insights
        if processed_result.key_insights:
            insights_summary = "; ".join(
                processed_result.key_insights[:3]
            )  # Top 3 insights
            summary_parts.append(f"Key insights: {insights_summary}")

        # Add structured findings if they exist
        findings = processed_result.structured_findings
        if findings:
            # Highlight the most important findings
            important_findings = []

            if "mentioned_codes" in findings and findings["mentioned_codes"]:
                important_findings.append(
                    f"Query-relevant codes found: {len(findings['mentioned_codes'])}"
                )

            if "unmanaged_count" in findings and findings["unmanaged_count"] > 0:
                important_findings.append(
                    f"Unmanaged codes: {findings['unmanaged_count']}"
                )

            if (
                "has_management_changes" in findings
                and findings["has_management_changes"]
            ):
                important_findings.append("Management status changes detected")

            if (
                "has_access_code_failures" in findings
                and findings["has_access_code_failures"]
            ):
                important_findings.append("Access code failures found")

            if important_findings:
                summary_parts.append(
                    f"Critical findings: {'; '.join(important_findings)}"
                )

        # Add follow-up suggestions if they exist
        if processed_result.follow_up_suggestions:
            # Include only the most important suggestion
            priority_suggestion = processed_result.follow_up_suggestions[0]
            summary_parts.append(f"Next: {priority_suggestion}")

        if not summary_parts:
            # Fallback to basic summary if no insights
            return f"{tool_name}: Data retrieved successfully"

        return f"{tool_name}: {' | '.join(summary_parts)}"

    def get_cross_tool_insights(self) -> List[str]:
        """Get insights from cross-tool correlation."""
        return self.result_processor.get_cross_tool_insights()

    def get_comprehensive_investigation_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary with all structured insights."""
        return self.result_processor.get_comprehensive_summary()

    def get_investigation_context_for_admin_links(self) -> Dict[str, Any]:
        """Get structured context specifically for generating admin links."""

        admin_context = {}

        # Collect admin context from all processed results
        for (
            tool_name,
            processed_result,
        ) in self.result_processor.processed_results.items():
            admin_context.update(processed_result.admin_links_context)

        # Add cross-tool correlations
        comprehensive_summary = self.result_processor.get_comprehensive_summary()
        if comprehensive_summary.get("cross_tool_insights"):
            admin_context["cross_tool_insights"] = comprehensive_summary[
                "cross_tool_insights"
            ]

        return admin_context

    def set_investigation_context(self, context: Dict[str, Any]) -> None:
        """Set investigation context for the result processor."""
        self.result_processor.investigation_context.update(context)

    def _build_enhanced_investigation_context(
        self, llm_provided_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build enhanced investigation context by combining LLM input with actual tool results.
        This prevents hallucinations by using real data from previous tool executions.
        """
        enhanced_context = llm_provided_context.copy()

        # Get actual data from executed tools to prevent hallucinations
        if hasattr(self, "_executed_tools_cache"):
            # Extract real device info if we executed get_device_info
            if "get_device_info" in self._executed_tools_cache:
                device_result = self._executed_tools_cache["get_device_info"]
                if isinstance(device_result, dict) and "error" not in device_result:
                    # Override with actual data
                    if "device_id" in device_result:
                        enhanced_context["device_id"] = device_result["device_id"]
                    if "workspace_id" in device_result:
                        enhanced_context["workspace_id"] = device_result["workspace_id"]
                    if "device_type" in device_result:
                        enhanced_context["device_type"] = device_result["device_type"]

            # Extract real access codes if we executed get_access_codes
            if "get_access_codes" in self._executed_tools_cache:
                codes_result = self._executed_tools_cache["get_access_codes"]
                if isinstance(codes_result, dict) and "access_codes" in codes_result:
                    enhanced_context["access_codes"] = codes_result["access_codes"]

            # Extract real action attempts if we executed get_action_attempts
            if "get_action_attempts" in self._executed_tools_cache:
                attempts_result = self._executed_tools_cache["get_action_attempts"]
                if (
                    isinstance(attempts_result, dict)
                    and "action_attempts" in attempts_result
                ):
                    enhanced_context["action_attempts"] = attempts_result[
                        "action_attempts"
                    ]

        return enhanced_context
