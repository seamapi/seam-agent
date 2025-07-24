import os
from typing import Any
from fastmcp import FastMCP
from seam_agent.connectors.seam_api import SeamAPIClient

# Check for API key
SEAM_API_KEY = os.getenv("SEAM_API_KEY")
if not SEAM_API_KEY:
    raise ValueError("SEAM_API_KEY environment variable is required")

print("🔧 Initializing Seam Device Resources...")

# Create MCP server
mcp = FastMCP("Seam Device Resources")


@mcp.resource("seam://devices")
async def list_all_devices() -> list[dict[str, Any]]:
    """
    List all devices from Seam API.
    Returns raw JSON device data suitable for LLM processing.
    """
    async with SeamAPIClient(SEAM_API_KEY) as client:
        devices = await client.list_devices()
        return devices


@mcp.resource("seam://devices/{device_id}")
async def get_device_by_id(device_id: str) -> dict[str, Any]:
    """
    Get a specific device by its ID.
    Returns raw JSON device data suitable for LLM processing.
    """
    async with SeamAPIClient(SEAM_API_KEY) as client:
        device = await client.get_device(device_id=device_id)
        return device


# For filtered searches, let's use a tool instead since FastMCP resources
# with parameters don't work well for complex filtering
@mcp.tool
async def search_devices(
    device_type: str | None = None,
    manufacturer: str | None = None,
    connected_account_id: str | None = None,
    device_ids: list[str] | None = None,
    limit: int | None = None,
    search: str | None = None,
) -> list[dict[str, Any]]:
    """
    Search/filter devices from Seam API with optional parameters.
    Returns raw JSON device data suitable for LLM processing.

    Args:
        device_type: Filter by device type (e.g., "smart_lock", "thermostat")
        manufacturer: Filter by manufacturer (e.g., "august", "yale")
        connected_account_id: Filter by connected account ID
        device_ids: Array of specific device IDs to retrieve
        limit: Maximum number of devices to return (default 500)
        search: Search string for device name/ID
    """
    async with SeamAPIClient(SEAM_API_KEY) as client:
        devices = await client.list_devices(
            device_type=device_type,
            manufacturer=manufacturer,
            connected_account_id=connected_account_id,
            device_ids=device_ids,
            limit=limit,
            search=search,
        )
        return devices


@mcp.tool
async def find_resources(search: str) -> dict[str, Any]:
    """
    Search for resources inside a workspace using the universal find endpoint.
    This can find any type of resource (devices, users, spaces, action_attempts, etc.) by ID or search term.

    Args:
        search: Search term (UUID format) to find resources by. Can be a device ID, user ID, space ID, etc.

    Returns:
        Batch dictionary containing various resource types that match the search term.
        The response includes arrays for: devices, users, spaces, action_attempts, client_sessions,
        acs_entrances, acs_systems, acs_users, and other resource types.
    """
    async with SeamAPIClient(SEAM_API_KEY) as client:
        batch = await client.find_resources(search=search)
        return batch


if __name__ == "__main__":
    print("🚀 Starting Seam Device Resources MCP server...")
    mcp.run()
