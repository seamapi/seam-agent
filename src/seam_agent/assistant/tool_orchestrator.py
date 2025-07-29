"""
Tool orchestrator for managing tool execution and result summarization.
"""

from typing import Dict, Any
from anthropic.types import ToolParam

from seam_agent.connectors.db import DatabaseClient
from seam_agent.connectors.seam_api import SeamAPIClient


class ToolOrchestrator:
    """Manages tool execution and result summarization."""

    db_client: DatabaseClient
    seam_client: SeamAPIClient

    def __init__(self, db_client, seam_client):
        self.db_client = db_client
        self.seam_client = seam_client

    def get_tool_definitions(self) -> list[ToolParam]:
        """Get the tool definitions for Anthropic API."""
        return [
            {
                "name": "get_device_info",
                "description": "Get comprehensive device information from the database including properties, status, and third-party details",
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
                "description": "Get recent action attempts for a device to see what operations were tried and their success/failure status",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "device_id": {
                            "type": "string",
                            "description": "The device ID to lookup",
                        },
                        "workspace_id": {
                            "type": "string",
                            "description": "The workspace ID for filtering",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (default 10)",
                            "default": 10,
                        },
                    },
                    "required": ["device_id", "workspace_id"],
                },
            },
            {
                "name": "get_access_codes",
                "description": "Get access codes for a device to see what codes are configured and their status",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "device_id": {
                            "type": "string",
                            "description": "The device ID to lookup",
                        },
                        "workspace_id": {
                            "type": "string",
                            "description": "The workspace ID for filtering",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (default 10)",
                            "default": 10,
                        },
                        "offset": {
                            "type": "integer",
                            "description": "Number of records to skip (default 0)",
                            "default": 0,
                        },
                    },
                    "required": ["device_id", "workspace_id"],
                },
            },
            {
                "name": "get_audit_logs",
                "description": "Get audit logs for access code operations (INSERT/DELETE) on a device to see recent changes",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "device_id": {
                            "type": "string",
                            "description": "The device ID to lookup",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (default 10)",
                            "default": 10,
                        },
                    },
                    "required": ["device_id"],
                },
            },
            {
                "name": "get_device_events",
                "description": "Get recent events for a device to see what has happened (non-internal events only)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "device_id": {
                            "type": "string",
                            "description": "The device ID to lookup",
                        },
                        "workspace_id": {
                            "type": "string",
                            "description": "The workspace ID for filtering",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (default 10)",
                            "default": 10,
                        },
                    },
                    "required": ["device_id", "workspace_id"],
                },
            },
        ]

    def summarize_tool_result(self, tool_name: str, result: Dict[str, Any]) -> str:
        """Create a concise summary of tool results to reduce context size."""

        if tool_name == "get_device_info":
            device_type = result.get("device_type", "unknown")
            workspace_id = result.get("workspace_id", "unknown")
            return f"Device Info: {device_type} in workspace {workspace_id}"

        elif tool_name == "get_access_codes":
            codes = result.get("access_codes", [])
            count = len(codes)
            if count > 0:
                # Show count and a few key details
                sample_codes = [
                    f"{code.get('name', 'unnamed')}: {code.get('code', 'N/A')}"
                    for code in codes[:3]
                ]
                summary = f"Access Codes ({count} total): {', '.join(sample_codes)}"
                if count > 3:
                    summary += f" and {count - 3} more"
                return summary
            return "Access Codes: None found"

        elif tool_name == "get_audit_logs":
            logs = result.get("audit_logs", [])
            count = len(logs)
            if count > 0:
                return f"Audit Logs: {count} entries found (access code changes, creations, deletions)"
            return "Audit Logs: No entries found"

        elif tool_name == "get_action_attempts":
            attempts = result.get("action_attempts", [])
            count = len(attempts)
            if count > 0:
                success_count = sum(1 for a in attempts if a.get("status") == "success")
                failed_count = count - success_count
                return f"Action Attempts: {count} total ({success_count} successful, {failed_count} failed)"
            return "Action Attempts: No attempts found"

        elif tool_name == "get_device_events":
            events = result.get("device_events", [])
            count = len(events)
            if count > 0:
                return (
                    f"Device Events: {count} events found (connection status, activity)"
                )
            return "Device Events: No events found"

        else:
            # Fallback for unknown tools - truncate the result
            result_str = str(result)
            if len(result_str) > 200:
                return f"{tool_name} result: {result_str[:200]}..."
            return f"{tool_name} result: {result_str}"

    async def execute_tool(self, tool_name: str, tool_input: Any) -> dict[str, Any]:
        """Execute a specific tool and return the result."""
        print(f"\n=== Executing Tool: {tool_name} ===")
        print(f"Input: {tool_input}")

        if tool_name == "get_device_info":
            device_id = tool_input["device_id"]
            print(f"Querying database for device: {device_id}")
            try:
                device_info = await self.db_client.get_device_by_id(device_id)
                if device_info:
                    print(
                        f"Found device in main table: {device_info.get('device_type', 'unknown')}"
                    )
                    return device_info
                else:
                    print("Device not found in main table")
                    return {"error": "Device not found"}
            except Exception as e:
                print(f"Error querying device: {str(e)}")
                return {"error": str(e)}

        elif tool_name == "get_access_codes":
            device_id = tool_input["device_id"]
            workspace_id = tool_input["workspace_id"]
            limit = tool_input.get("limit", 10)
            offset = tool_input.get("offset", 0)
            print(
                f"Querying access codes for device: {device_id} in workspace: {workspace_id}"
            )
            try:
                access_codes = await self.db_client.get_access_codes(
                    device_id, workspace_id, limit, offset
                )
                print(f"Found {len(access_codes)} access codes")
                return {"access_codes": access_codes}
            except Exception as e:
                print(f"Error querying access codes: {str(e)}")
                return {"error": str(e)}

        elif tool_name == "get_audit_logs":
            device_id = tool_input["device_id"]
            limit = tool_input.get("limit", 10)
            print(f"Querying audit logs for device: {device_id}")
            try:
                audit_logs = await self.db_client.get_audit_logs(device_id, limit)
                print(f"Found {len(audit_logs)} audit log entries")
                return {"audit_logs": audit_logs, "device_id": device_id}
            except Exception as e:
                print(f"Error querying audit logs: {str(e)}")
                return {"error": str(e)}

        elif tool_name == "get_action_attempts":
            device_id = tool_input["device_id"]
            workspace_id = tool_input["workspace_id"]
            limit = tool_input.get("limit", 10)
            print(
                f"Querying action attempts for device: {device_id} in workspace: {workspace_id}"
            )
            try:
                action_attempts = await self.db_client.get_action_attempts(
                    device_id, workspace_id, limit
                )
                print(f"Found {len(action_attempts)} action attempts")
                return {
                    "action_attempts": action_attempts,
                    "device_id": device_id,
                    "workspace_id": workspace_id,
                }
            except Exception as e:
                print(f"Error querying action attempts: {str(e)}")
                return {"error": str(e)}

        elif tool_name == "get_device_events":
            device_id = tool_input["device_id"]
            workspace_id = tool_input["workspace_id"]
            limit = tool_input.get("limit", 10)
            print(
                f"Querying device events for device: {device_id} in workspace: {workspace_id}"
            )
            try:
                device_events = await self.db_client.get_device_events(
                    device_id, workspace_id, limit
                )
                print(f"Found {len(device_events)} device events")
                return {
                    "device_events": device_events,
                    "device_id": device_id,
                    "workspace_id": workspace_id,
                }
            except Exception as e:
                print(f"Error querying device events: {str(e)}")
                return {"error": str(e)}

        else:
            return {"error": f"Unknown tool: {tool_name}"}
