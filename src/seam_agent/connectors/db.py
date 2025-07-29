import os
from typing import Any, Optional, List, Dict
from contextlib import asynccontextmanager

import asyncpg


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

        self.pool: asyncpg.pool.Pool | None = None

    async def connect(self):
        """Initialize connection pool."""
        if not self.pool:
            if not self.database_url:
                raise ValueError("DATABASE_URL environment variable is required")
            database_url = self._fix_ssl_config(self.database_url)

            self.pool = await asyncpg.create_pool(
                database_url, min_size=1, max_size=10, command_timeout=30
            )

    def _fix_ssl_config(self, url: str) -> str:
        """Fix SSL configuration to be compatible with asyncpg."""
        # Map common SSL modes to asyncpg-compatible ones
        ssl_fixes = {
            "sslmode=no-verify": "sslmode=require",
            "sslmode=required": "sslmode=require",
            "sslmode=preferred": "sslmode=prefer",
            "sslmode=disabled": "sslmode=disable",
            "sslmode=true": "sslmode=require",
            "sslmode=false": "sslmode=disable",
        }

        # Apply SSL fixes
        for old, new in ssl_fixes.items():
            url = url.replace(old, new)

        return url

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

        if not self.pool:
            raise ValueError("Database connection pool is not initialized")

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
        FROM device
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
        FROM action_attempt
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

    async def get_device_by_id(self, device_id: str) -> Optional[Dict[str, Any]]:
        """
        Get device information by device ID or third party device ID.

        Args:
            device_id: The device ID or third party device ID to lookup

        Returns:
            Device information dict or None if not found
        """
        query = """
        SELECT seam.device.*, seam.phone_sdk_installation.phone_sdk_installation_id
        FROM seam.device
        LEFT JOIN seam.phone_sdk_installation ON seam.phone_sdk_installation.device_id = seam.device.device_id
        WHERE (seam.device.device_id = $1 OR seam.device.third_party_device_id = $1)
        LIMIT 1;
        """

        async with self.get_connection() as conn:
            result = await conn.fetchrow(query, device_id)
            if result:
                device_info = dict(result)
                # Convert UUID and datetime objects to strings for JSON serialization
                for key, value in device_info.items():
                    if hasattr(value, "hex"):  # UUID objects have a hex attribute
                        device_info[key] = str(value)
                    elif hasattr(
                        value, "isoformat"
                    ):  # datetime objects have isoformat method
                        device_info[key] = value.isoformat()
                return device_info
            return None

    async def get_third_party_device_by_id(
        self, third_party_device_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get third party device information by third party device ID.

        Args:
            third_party_device_id: The third party device ID to lookup

        Returns:
            Third party device information dict or None if not found
        """
        query = """
        SELECT *, seam.third_party_device.workspace_id as third_party_device_workspace_id
        FROM seam.third_party_device
        WHERE third_party_device_id = $1
        LIMIT 1;
        """

        async with self.get_connection() as conn:
            result = await conn.fetchrow(query, third_party_device_id)
            if result:
                tpd_info = dict(result)
                # Convert UUID and datetime objects to strings for JSON serialization
                for key, value in tpd_info.items():
                    if hasattr(value, "hex"):  # UUID objects have a hex attribute
                        tpd_info[key] = str(value)
                    elif hasattr(
                        value, "isoformat"
                    ):  # datetime objects have isoformat method
                        tpd_info[key] = value.isoformat()
                return tpd_info
            return None

    async def get_action_attempts(
        self, device_id: str, workspace_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent action attempts for a device.

        Args:
            device_id: The device ID to lookup
            workspace_id: The workspace ID for filtering
            limit: Maximum number of results (default 10)

        Returns:
            List of action attempt records
        """
        query = """
        SELECT action_attempt_id, action_type, status, created_at, success_details
        FROM seam.action_attempt
        WHERE device_id = $1 AND workspace_id = $2
        ORDER BY created_at DESC
        LIMIT $3;
        """

        async with self.get_connection() as conn:
            results = await conn.fetch(query, device_id, workspace_id, limit)
            action_attempts = []
            for result in results:
                attempt_info = dict(result)
                # Convert UUID and datetime objects to strings for JSON serialization
                for key, value in attempt_info.items():
                    if hasattr(value, "hex"):  # UUID objects have a hex attribute
                        attempt_info[key] = str(value)
                    elif hasattr(
                        value, "isoformat"
                    ):  # datetime objects have isoformat method
                        attempt_info[key] = value.isoformat()
                action_attempts.append(attempt_info)
            return action_attempts

    async def get_access_codes(
        self, device_id: str, workspace_id: str, limit: int = 10, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get access codes for a device.

        Args:
            device_id: The device ID to lookup
            workspace_id: The workspace ID for filtering
            limit: Maximum number of results (default 10)
            offset: Number of records to skip (default 0)

        Returns:
            List of access code records
        """
        query = """
        SELECT *
        FROM seam.access_code
        WHERE device_id = $1 AND workspace_id = $2
        ORDER BY created_at DESC
        LIMIT $3 OFFSET $4;
        """

        async with self.get_connection() as conn:
            results = await conn.fetch(query, device_id, workspace_id, limit, offset)
            access_codes = []
            for result in results:
                code_info = dict(result)
                # Convert UUID and datetime objects to strings for JSON serialization
                for key, value in code_info.items():
                    if hasattr(value, "hex"):  # UUID objects have a hex attribute
                        code_info[key] = str(value)
                    elif hasattr(
                        value, "isoformat"
                    ):  # datetime objects have isoformat method
                        code_info[key] = value.isoformat()
                access_codes.append(code_info)
            return access_codes

    async def get_audit_logs(
        self, device_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get audit logs for access code operations on a device.

        Args:
            device_id: The device ID to lookup
            limit: Maximum number of results (default 10)

        Returns:
            List of audit log records
        """
        query = """
        SELECT *
        FROM diagnostics.access_code_audit
        WHERE device_id = $1 AND (operation = 'INSERT' OR operation = 'DELETE')
        ORDER BY created_at DESC
        LIMIT $2;
        """

        async with self.get_connection() as conn:
            results = await conn.fetch(query, device_id, limit)
            audit_logs = []
            for result in results:
                log_info = dict(result)
                # Convert UUID and datetime objects to strings for JSON serialization
                for key, value in log_info.items():
                    if hasattr(value, "hex"):  # UUID objects have a hex attribute
                        log_info[key] = str(value)
                    elif hasattr(
                        value, "isoformat"
                    ):  # datetime objects have isoformat method
                        log_info[key] = value.isoformat()
                audit_logs.append(log_info)
            return audit_logs

    async def get_device_events(
        self, device_id: str, workspace_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent events for a device.

        Args:
            device_id: The device ID to lookup
            workspace_id: The workspace ID for filtering
            limit: Maximum number of results (default 10)

        Returns:
            List of device event records
        """
        query = """
        SELECT *
        FROM seam.event
        WHERE device_id = $1 AND workspace_id = $2 AND is_internal = false
        ORDER BY occurred_at DESC
        LIMIT $3;
        """

        async with self.get_connection() as conn:
            results = await conn.fetch(query, device_id, workspace_id, limit)
            events = []
            for result in results:
                event_info = dict(result)
                # Convert UUID and datetime objects to strings for JSON serialization
                for key, value in event_info.items():
                    if hasattr(value, "hex"):  # UUID objects have a hex attribute
                        event_info[key] = str(value)
                    elif hasattr(
                        value, "isoformat"
                    ):  # datetime objects have isoformat method
                        event_info[key] = value.isoformat()
                events.append(event_info)
            return events

    async def execute_safe_query(
        self, query: str, params: List[Any] = []
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

        async with self.get_connection() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        return None
