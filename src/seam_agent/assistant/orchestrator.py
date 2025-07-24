from typing import Any
from seam_agent.connectors.seam_api import SeamAPIClient
from fastmcp import Client
from fastmcp.client.transports import StdioTransport


async def analyze_device_issue(device_id: str) -> dict[str, Any]:
    """
    Analyzes a device issue by fetching device data and action attempts.

    This is a mock implementation that does not call an LLM.
    Returns raw JSON suitable for LLM processing.
    """
    async with SeamAPIClient() as client:
        device = await client.get_device(device_id)
        # Note: list_action_attempts doesn't exist yet in our client
        # This would need to be implemented or mocked
        action_attempts = []  # Mock data for now

    # Extract key info from device JSON
    display_name = device.get("display_name", "Unknown Device")
    is_online = device.get("properties", {}).get("online", False)

    # In a real implementation, an LLM would generate this summary.
    summary = (
        f"The device '{display_name}' is currently "
        f"{'online' if is_online else 'offline'}. "
        "There are recent action attempts with both success and failure statuses."
    )

    timeline = [
        f"14:41:11 - Action '{a.get('action_type', 'unknown')}' resulted in '{a.get('status', 'unknown')}'"
        for a in action_attempts
    ]

    # Return JSON structure for LLM processing
    return {
        "device": device,  # Full device JSON
        "action_attempts": action_attempts,
        "summary": summary,
        "timeline": timeline,
        "root_cause": "Device is offline.",  # Mock root cause
        "analysis_type": "device_issue_analysis",
    }


# Helper functions for MCP client integration (for future use)
def create_mcp_client():
    """Creates an MCP client for tool integration."""
    transport = StdioTransport(command="python", args=["assistant/server.py"])
    return Client(transport)


async def call_tool(name: str, device_id: str):
    """Example function for calling MCP tools (for future integration)."""
    client = create_mcp_client()
    async with client:
        result = await client.call_tool("get_device", {"device_id": device_id})
        return result
