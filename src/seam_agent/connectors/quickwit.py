import httpx
import os
from typing import Any, Optional, List, Dict
from datetime import datetime, timedelta


class QuickwitClient:
    """Async client for searching Quickwit logs."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = base_url or os.getenv("QUICKWIT_URL", "http://localhost:7280")
        self.api_key = api_key or os.getenv("QUICKWIT_API_KEY")

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        self.client = httpx.AsyncClient(
            base_url=self.base_url.rstrip("/"),
            headers=headers,
            timeout=30.0,
        )

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def search_logs(
        self,
        index: str,
        query: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        device_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search logs in Quickwit index.

        Args:
            index: Quickwit index name to search
            query: Search query string
            start_time: Start time for log search
            end_time: End time for log search
            limit: Maximum number of results to return
            device_id: Optional device ID to filter logs

        Returns:
            List of log entries matching the search criteria
        """
        # Build the search query - keep it simple for Quickwit
        search_params = {
            "query": query,
            "max_hits": limit,
        }

        # Add time range filters if provided (using Quickwit's time range format)
        if start_time:
            search_params["start_timestamp"] = int(start_time.timestamp())
        if end_time:
            search_params["end_timestamp"] = int(end_time.timestamp())

        try:
            response = await self.client.post(
                f"/api/v1/{index}/search", json=search_params
            )
            response.raise_for_status()

            data = response.json()
            return data.get("hits", [])

        except httpx.HTTPStatusError as e:
            # Handle common Quickwit errors gracefully
            if e.response.status_code == 404:
                raise ValueError(f"Index '{index}' not found")
            elif e.response.status_code == 400:
                raise ValueError(f"Invalid search query: {query}")
            else:
                raise

    async def search_device_logs(
        self,
        device_id: str,
        index: str = "application_logs_v4",
        hours_back: int = 24,
        error_only: bool = False,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Search logs for a specific device.

        Args:
            device_id: Device ID to search for
            index: Quickwit index to search (default: application_logs_v4)
            hours_back: Number of hours back to search
            error_only: If True, only return error/warning logs
            limit: Maximum number of results

        Returns:
            List of log entries for the device
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours_back)

        # Build simple query for Quickwit
        if error_only:
            query = f"device_id:{device_id} AND (level:ERROR OR level:WARN OR level:WARNING)"
        else:
            query = f"device_id:{device_id}"

        return await self.search_logs(
            index=index,
            query=query,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

    async def search_application_logs(
        self,
        query: str,
        workspace_id: str | None = None,
        hours_back: int = 24,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Search application logs with workspace filtering.

        Uses application_logs_v4 index which has device_id, workspace_id,
        and other metadata fields optimized for device investigation.

        Args:
            query: Search query string
            workspace_id: Optional workspace ID to filter results
            hours_back: How many hours back to search
            limit: Maximum number of results

        Returns:
            List of application log entries
        """
        from datetime import timedelta

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours_back)

        # Add workspace filter if provided
        if workspace_id:
            query = f"({query}) AND workspace_id:{workspace_id}"

        return await self.search_logs(
            index="application_logs_v4",
            query=query,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

    async def search_beta_logs(
        self,
        query: str,
        workspace_id: str | None = None,
        hours_back: int = 24,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Search beta application logs.

        Uses application_logs_v5_beta_2 index for newer log format.

        Args:
            query: Search query string
            workspace_id: Optional workspace ID to filter results
            hours_back: How many hours back to search
            limit: Maximum number of results

        Returns:
            List of beta log entries
        """
        from datetime import timedelta

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours_back)

        # Add workspace filter if provided
        if workspace_id:
            query = f"({query}) AND workspace_id:{workspace_id}"

        return await self.search_logs(
            index="application_logs_v5_beta_2",
            query=query,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )
