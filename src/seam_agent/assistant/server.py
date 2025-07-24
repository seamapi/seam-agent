import os
from typing import Any
from datetime import datetime
from fastmcp import FastMCP
from seam_agent.connectors.seam_api import SeamAPIClient
from seam_agent.connectors.quickwit import QuickwitClient
from seam_agent.connectors.db import DatabaseClient

# Check for required environment variables
SEAM_API_KEY = os.getenv("SEAM_API_KEY")
if not SEAM_API_KEY:
    raise ValueError("SEAM_API_KEY environment variable is required")

# Quickwit variables are checked when tools are called
QUICKWIT_URL = os.getenv("QUICKWIT_URL")
QUICKWIT_API_KEY = os.getenv("QUICKWIT_API_KEY")

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


@mcp.tool
async def get_action_attempt(action_attempt_id: str) -> dict[str, Any]:
    """
    Get a specific action attempt by ID.

    Args:
        action_attempt_id: The action attempt ID to retrieve

    Returns:
        Action attempt dictionary with detailed information about the attempt,
        including status, error messages, timestamps, and related device info.
    """
    async with SeamAPIClient(SEAM_API_KEY) as client:
        action_attempt = await client.get_action_attempt(action_attempt_id)
        return action_attempt


@mcp.tool
async def list_action_attempts(action_attempt_ids: list[str]) -> list[dict[str, Any]]:
    """
    List specific action attempts by their IDs.

    Args:
        action_attempt_ids: List of action attempt IDs to retrieve

    Returns:
        List of action attempt dictionaries with detailed information.
        Useful for analyzing patterns across multiple attempts.
    """
    async with SeamAPIClient(SEAM_API_KEY) as client:
        action_attempts = await client.list_action_attempts(action_attempt_ids)
        return action_attempts


@mcp.tool
async def find_device_action_attempts(device_id: str) -> list[dict[str, Any]]:
    """
    Find action attempts related to a specific device using universal search.

    This is a helper tool that uses the find_resources endpoint to locate
    action attempts associated with a device, then fetches their details.

    Args:
        device_id: The device ID to find action attempts for

    Returns:
        List of action attempt dictionaries related to the device.
        Essential for device investigation and timeline reconstruction.
    """
    async with SeamAPIClient(SEAM_API_KEY) as client:
        # First, use find_resources to search for action attempts related to the device
        search_results = await client.find_resources(device_id)

        # Extract action attempt IDs from the search results
        action_attempts = search_results.get("action_attempts", [])

        if not action_attempts:
            return []

        # Get the IDs and fetch full details
        action_attempt_ids = [
            attempt.get("action_attempt_id")
            for attempt in action_attempts
            if attempt.get("action_attempt_id")
        ]

        if action_attempt_ids:
            detailed_attempts = await client.list_action_attempts(action_attempt_ids)
            return detailed_attempts

        return action_attempts


@mcp.tool
async def search_quickwit_logs(
    device_id: str,
    index: str = "application_logs_v4",
    hours_back: int = 24,
    error_only: bool = False,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """
    Search Quickwit logs for a specific device using production indexes.

    Essential for device investigation timeline reconstruction - finds error messages,
    events, and system logs correlated with device issues.

    Args:
        device_id: The device ID to search logs for
        index: Quickwit index name (default: "application_logs_v4")
        hours_back: How many hours back to search (default: 24)
        error_only: Only return error/warning logs (default: False)
        limit: Maximum number of log entries to return

    Returns:
        List of log entries with timestamps, messages, and metadata.
        Critical for understanding device issue timeline and root causes.
    """
    # Validate Quickwit environment variables
    quickwit_url = os.getenv("QUICKWIT_URL")
    quickwit_api_key = os.getenv("QUICKWIT_API_KEY")
    if not quickwit_url or not quickwit_api_key:
        raise ValueError(
            "QUICKWIT_URL and QUICKWIT_API_KEY environment variables are required"
        )

    async with QuickwitClient(quickwit_url, quickwit_api_key) as client:
        logs = await client.search_device_logs(
            device_id=device_id,
            index=index,
            hours_back=hours_back,
            error_only=error_only,
            limit=limit,
        )
        return logs


@mcp.tool
async def search_logs_by_query(
    query: str,
    index: str = "application_logs_v4",
    start_time: str | None = None,
    end_time: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """
    Search Quickwit logs using a custom query with production indexes.

    Flexible log search for investigating patterns, errors, or specific events
    across the system. Useful for provider-wide issues or correlation analysis.

    Args:
        query: Quickwit search query string
        index: Quickwit index name (default: "application_logs_v4")
        start_time: Start time in ISO format (e.g., "2025-07-24T10:00:00Z")
        end_time: End time in ISO format (e.g., "2025-07-24T18:00:00Z")
        limit: Maximum number of log entries to return

    Returns:
        List of log entries matching the search criteria.
        Enables cross-device analysis and pattern detection.
    """
    # Validate Quickwit environment variables
    quickwit_url = os.getenv("QUICKWIT_URL")
    quickwit_api_key = os.getenv("QUICKWIT_API_KEY")
    if not quickwit_url or not quickwit_api_key:
        raise ValueError(
            "QUICKWIT_URL and QUICKWIT_API_KEY environment variables are required"
        )

    async with QuickwitClient(quickwit_url, quickwit_api_key) as client:
        # Parse datetime strings if provided
        start_dt = (
            datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            if start_time
            else None
        )
        end_dt = (
            datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            if end_time
            else None
        )

        logs = await client.search_logs(
            index=index,
            query=query,
            start_time=start_dt,
            end_time=end_dt,
            limit=limit,
        )
        return logs


@mcp.tool
async def query_devices_db(
    device_id: str | None = None,
    workspace_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """
    Query devices directly from PostgreSQL database.

    Provides access to device metadata, configuration, and state information
    that may not be available through the Seam API. Essential for deep
    device investigation and troubleshooting.

    Args:
        device_id: Specific device ID to query (optional)
        workspace_id: Filter by workspace ID (optional)
        limit: Maximum number of devices to return

    Returns:
        List of device records with full database fields including
        properties, capabilities, errors, and timestamps.
    """
    # Validate database environment variables
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")

    try:
        async with DatabaseClient() as db_client:
            devices = await db_client.query_devices(
                device_id=device_id,
                workspace_id=workspace_id,
                limit=limit,
            )
            return devices
    except ImportError as e:
        raise ValueError(f"Database functionality not available: {e}")


@mcp.tool
async def query_action_attempts_db(
    device_id: str | None = None,
    action_attempt_id: str | None = None,
    workspace_id: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """
    Query action attempts directly from PostgreSQL database.

    Provides comprehensive action attempt history with full error details,
    timing information, and status tracking. Critical for understanding
    device operation patterns and failure analysis.

    Args:
        device_id: Filter by device ID (optional)
        action_attempt_id: Specific action attempt ID (optional)
        workspace_id: Filter by workspace ID (optional)
        status: Filter by status - pending, success, error (optional)
        limit: Maximum number of action attempts to return

    Returns:
        List of action attempt records with full database fields including
        action_type, result, error details, and timestamps.
    """
    # Validate database environment variables
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")

    try:
        async with DatabaseClient() as db_client:
            action_attempts = await db_client.query_action_attempts(
                device_id=device_id,
                action_attempt_id=action_attempt_id,
                workspace_id=workspace_id,
                status=status,
                limit=limit,
            )
            return action_attempts
    except ImportError as e:
        raise ValueError(f"Database functionality not available: {e}")


@mcp.tool
async def execute_safe_db_query(
    query: str,
    params: list[Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Execute a safe, read-only SQL query against the PostgreSQL database.

    Allows for custom database queries with safety restrictions to prevent
    data modification. Only SELECT statements are permitted with parameter
    validation to prevent SQL injection.

    Args:
        query: SQL SELECT query string
        params: Query parameters for safe parameterized queries (optional)

    Returns:
        List of query results as dictionaries.

    Raises:
        ValueError: If query contains unsafe operations or keywords
    """
    # Validate database environment variables
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")

    try:
        async with DatabaseClient() as db_client:
            results = await db_client.execute_safe_query(
                query=query,
                params=params or [],
            )
            return results
    except ImportError as e:
        raise ValueError(f"Database functionality not available: {e}")


if __name__ == "__main__":
    print("🚀 Starting Seam Device Resources MCP server...")
    mcp.run()
