import os
from typing import Any, Optional, List, Dict
from contextlib import asynccontextmanager

try:
    import asyncpg
except ImportError:
    asyncpg = None


class DatabaseClient:
    """Async client for PostgreSQL database queries."""

    def __init__(self, database_url: str | None = None):
        if asyncpg is None:
            raise ImportError(
                "asyncpg is required for database operations. Install with: pip install asyncpg"
            )

        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")

        self.pool = None

    async def connect(self):
        """Initialize connection pool."""
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                self.database_url, min_size=1, max_size=10, command_timeout=30
            )

    async def close(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None

    @asynccontextmanager
    async def get_connection(self):
        """Get a database connection from the pool."""
        if not self.pool:
            await self.connect()

        async with self.pool.acquire() as connection:
            yield connection

    async def query_devices(
        self,
        device_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Query devices from the database.

        Args:
            device_id: Specific device ID to query
            workspace_id: Filter by workspace ID
            limit: Maximum number of results

        Returns:
            List of device records
        """
        query = """
        SELECT
            device_id,
            workspace_id,
            device_type,
            nickname,
            created_at,
            updated_at,
            properties,
            capabilities,
            errors
        FROM devices
        WHERE 1=1
        """

        params = []
        param_count = 0

        if device_id:
            param_count += 1
            query += f" AND device_id = ${param_count}"
            params.append(device_id)

        if workspace_id:
            param_count += 1
            query += f" AND workspace_id = ${param_count}"
            params.append(workspace_id)

        param_count += 1
        query += f" ORDER BY updated_at DESC LIMIT ${param_count}"
        params.append(limit)

        async with self.get_connection() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]

    async def query_action_attempts(
        self,
        device_id: Optional[str] = None,
        action_attempt_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Query action attempts from the database.

        Args:
            device_id: Filter by device ID
            action_attempt_id: Specific action attempt ID
            workspace_id: Filter by workspace ID
            status: Filter by status (pending, success, error)
            limit: Maximum number of results

        Returns:
            List of action attempt records
        """
        query = """
        SELECT
            action_attempt_id,
            device_id,
            workspace_id,
            action_type,
            status,
            created_at,
            updated_at,
            result,
            error
        FROM action_attempts
        WHERE 1=1
        """

        params = []
        param_count = 0

        if action_attempt_id:
            param_count += 1
            query += f" AND action_attempt_id = ${param_count}"
            params.append(action_attempt_id)

        if device_id:
            param_count += 1
            query += f" AND device_id = ${param_count}"
            params.append(device_id)

        if workspace_id:
            param_count += 1
            query += f" AND workspace_id = ${param_count}"
            params.append(workspace_id)

        if status:
            param_count += 1
            query += f" AND status = ${param_count}"
            params.append(status)

        param_count += 1
        query += f" ORDER BY created_at DESC LIMIT ${param_count}"
        params.append(limit)

        async with self.get_connection() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]

    async def execute_safe_query(
        self, query: str, params: List[Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a safe, read-only query with parameter validation.

        Args:
            query: SQL query string (must be SELECT only)
            params: Query parameters

        Returns:
            List of query results

        Raises:
            ValueError: If query is not a safe SELECT statement
        """
        # Basic safety check - only allow SELECT statements
        query_upper = query.strip().upper()
        if not query_upper.startswith("SELECT"):
            raise ValueError("Only SELECT queries are allowed")

        # Check for dangerous keywords
        dangerous_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE"]
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                raise ValueError(f"Query contains dangerous keyword: {keyword}")

        if params is None:
            params = []

        async with self.get_connection() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        return None
