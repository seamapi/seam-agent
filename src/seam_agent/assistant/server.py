import os
import logging
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


@mcp.tool(enabled=False)
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
async def search_logs(
    query: str,
    index: str = "application_logs_v4",
    start_time: str | None = None,
    end_time: str | None = None,
    limit: int = 10,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """
    Search logs in a Quickwit index with a flexible query.

    This is the primary tool for searching logs. The LLM is responsible for
    constructing the 'query' string using Quickwit's query language.

    Available Indexes and Queryable Fields:

    1. `application_logs_v4` (Default):
       - `log_type`: Type of log (e.g., 'http_request').
       - `job_id`: Associated job ID.
       - `log_id`: Unique log identifier.
       - `app`: Application source (e.g., 'seam-connect').
       - `host`: Hostname where the log was generated.
       - `level`: Log level (e.g., 'INFO', 'ERROR').
       - `message`: The log message content.
       - `task_identifier`: Specific task identifier.
       - `workspace_id`: The workspace ID.
       - `device_id`: The device ID.
       - `third_party_account_id`: The third-party account ID.
       - `connect_webview_id`: The connect webview ID.
       - `phone_sdk_installation_id`: Phone SDK installation ID.
       - `custom_sdk_installation_id`: Custom SDK installation ID.
       - `phone_registration_id`: Phone registration ID.
       - `user_identity_id`: The user identity ID.
       - `client_session_id`: The client session ID.
       - `access_code_ids`: Array of access code IDs.
       - `response_time`: Response time in seconds.

    2. `application_logs_v5_beta_2`:
       - `message`: The log message content.
       - `app`: Application source.
       - `workspace_id`: The workspace ID.
       - `response_json`: JSON response data.
       - `response_time`: Response time in seconds.
       - `device_id`: The device ID.
       - `third_party_account_id`: The third-party account ID.
       - `connect_webview_id`: The connect webview ID.
       - `phone_sdk_installation_id`: Phone SDK installation ID.
       - `custom_sdk_installation_id`: Custom SDK installation ID.
       - `phone_registration_id`: Phone registration ID.
       - `user_identity_id`: The user identity ID.
       - `client_session_id`: The client session ID.
       - `access_code_ids`: Array of access code IDs.

    Args:
        query: The search query string. Can include filters on any field
               in the schema (e.g., 'device_id:dev_123 AND level:ERROR').
        index: Quickwit index name (e.g., 'application_logs_v4', 'application_logs_v5_beta_2').
        start_time: Optional start time in ISO 8601 format (e.g., '2023-01-01T00:00:00Z').
        end_time: Optional end time in ISO 8601 format (e.g., '2023-01-01T23:59:59Z').
        limit: Maximum number of log entries to return.
        offset: Number of log entries to skip from the beginning.

    Returns:
        A list of log entries matching the search criteria.
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
            start_offset=offset,
        )
        return logs


# Simplified database access using our existing DatabaseClient
# This gives us the flexibility you want with minimal tool exposure


@mcp.tool
async def query_database(sql: str) -> list[dict[str, Any]]:
    """
    Execute read-only SQL queries against the Seam database.

    The LLM can query any table for device investigation with full flexibility.
    All queries are automatically restricted to SELECT operations only with
    built-in safety validation.

    Essential for device investigation - allows flexible queries across:
    - devices table (device metadata, properties, capabilities, errors)
    - action_attempts table (operation history, errors, timing, status)
    - Any other tables needed for comprehensive analysis

    Always use the schema prefix for table names (e.g., "seam.devices").

    Args:
        sql: SQL SELECT query string for investigation

    Returns:
        List of query results as dictionaries with full database fields.

    Examples:
        - "SELECT * FROM seam.device WHERE device_id = 'c00718ad-4e66-45c4-a517-28fb3394c28d'"
        - "SELECT * FROM seam.action_attempt WHERE device_id = 'c00718ad-4e66-45c4-a517-28fb3394c28d' ORDER BY created_at DESC LIMIT 10"
        - "SELECT d.device_type, d.nickname, aa.action_type, aa.status, aa.error FROM seam.device d JOIN seam.action_attempt aa ON d.device_id = aa.device_id WHERE d.device_id = 'c00718ad-4e66-45c4-a517-28fb3394c28d'"
    """
    # Validate database environment variables
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")

    try:
        async with DatabaseClient() as db_client:
            results = await db_client.execute_safe_query(sql, [])
            return results
    except ImportError as e:
        raise ValueError(
            f"Database functionality not available: {e}. Install with: pip install asyncpg"
        )
    except Exception as e:
        raise ValueError(f"Database query failed: {e}")


@mcp.tool
async def get_database_schema() -> str:
    """
    Get live database schema information by introspecting the actual database.

    Queries the PostgreSQL information_schema to provide real-time schema info:
    - All table names and structures
    - Column names, types, and constraints
    - Primary keys and relationships
    - Indexes and constraints

    This enables the LLM to craft intelligent queries based on the actual
    database structure, not assumptions.
    """
    # Validate database environment variables
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")

    try:
        async with DatabaseClient() as db_client:
            # Get all tables in the seam and diagnostics schemas (focus on Seam application and diagnostics tables)
            # Filter out the massive public_log_entry_* tables that cause token explosion
            tables_query = """
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_schema IN ('seam', 'diagnostics')
            AND table_type = 'BASE TABLE'
            AND table_name NOT LIKE 'public_log_entry_%'  -- Filter out massive log tables
            AND table_name NOT LIKE 'job_log_%'          -- Filter out job log tables too
            ORDER BY
                CASE WHEN table_schema = 'seam' THEN 1
                     WHEN table_schema = 'diagnostics' THEN 2
                     ELSE 3 END,
                table_name;
            """
            tables = await db_client.execute_safe_query(tables_query, [])

            schema_info = "# Live Database Schema\n\n"

            for table in tables:
                table_schema = table["table_schema"]
                table_name = table["table_name"]
                full_table_name = f"{table_schema}.{table_name}"
                schema_info += f"## {full_table_name}\n"

                # Use parameterized query for safety
                columns = await db_client.execute_safe_query(
                    f"SELECT column_name, data_type, is_nullable, column_default, character_maximum_length FROM information_schema.columns WHERE table_schema = '{table_schema}' AND table_name = '{table_name}' ORDER BY ordinal_position",
                    [],
                )

                for col in columns:
                    nullable = "NULL" if col["is_nullable"] == "YES" else "NOT NULL"
                    data_type = col["data_type"]
                    if col["character_maximum_length"]:
                        data_type += f"({col['character_maximum_length']})"

                    schema_info += f"- {col['column_name']} ({data_type}, {nullable})"
                    if col["column_default"]:
                        schema_info += f" DEFAULT {col['column_default']}"
                    schema_info += "\n"

                # Get primary key information
                pk_query = f"""
                SELECT column_name
                FROM information_schema.key_column_usage
                WHERE table_schema = '{table_schema}'
                  AND table_name = '{table_name}'
                  AND constraint_name = (SELECT constraint_name
                                         FROM information_schema.table_constraints
                                         WHERE table_schema = '{table_schema}'
                                           AND table_name = '{table_name}'
                                           AND constraint_type = 'PRIMARY KEY');
                """

                try:
                    pk_cols = await db_client.execute_safe_query(pk_query, [])
                    if pk_cols:
                        pk_names = [col["column_name"] for col in pk_cols]
                        schema_info += f"**Primary Key:** {', '.join(pk_names)}\n"
                except Exception as e:
                    logging.warning(
                        f"Could not retrieve primary key for {full_table_name}: {e}"
                    )

                schema_info += "\n"

            # Add some helpful query examples
            schema_info += """
## Common Query Patterns

```sql
-- List all tables
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';

-- Get row counts
SELECT schemaname,tablename,n_tup_ins,n_tup_upd,n_tup_del,n_live_tup,n_dead_tup
FROM pg_stat_user_tables;

-- Find tables with specific columns
SELECT table_name FROM information_schema.columns
WHERE column_name = 'device_id' AND table_schema = 'public';
```
"""

            return schema_info

    except ImportError as e:
        return f"Database functionality not available: {e}. Install with: pip install asyncpg"
    except Exception as e:
        return f"Error introspecting database schema: {e}"


if __name__ == "__main__":
    print("🚀 Starting Seam MCP server...")
    mcp.run()
