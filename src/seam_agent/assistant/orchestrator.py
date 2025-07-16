import asyncio
from seam_agent.assistant.models import AnalysisResult
from seam_agent.connectors import seam_api
from fastmcp import Client
from fastmcp.client.transports import StdioTransport


def analyze_device_issue(device_id: str) -> AnalysisResult:
    """
    Analyzes a device issue by fetching device data and action attempts.

    This is a mock implementation that does not call an LLM.
    """
    device = seam_api.get_device(device_id)
    action_attempts = seam_api.list_action_attempts(device_id)

    # In a real implementation, an LLM would generate this summary.
    summary = (
        f"The device '{device.display_name}' is currently "
        f"{'online' if device.is_online else 'offline'}. "
        "There are recent action attempts with both success and failure statuses."
    )

    timeline = [
        f"14:41:11 - Action '{a.action_type}' resulted in '{a.status}'"
        for a in action_attempts
    ]

    return AnalysisResult(
        device=device,
        action_attempts=action_attempts,
        summary=summary,
        timeline=timeline,
        root_cause="Device is offline.",  # Mock root cause
    )


transport = StdioTransport(command="python", args=["seam_agent/assistant/server.py"])
client = Client(transport)


async def call_tool(name: str):
    async with client:
        result = await client.call_tool("get_device", {"device_id": name})
        print(result)


asyncio.run(call_tool("my_device_id"))
