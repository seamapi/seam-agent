import httpx
import os
from typing import Any, Optional, List, Dict
from datetime import datetime


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
        start_offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Search logs in a Quickwit index with a flexible query.

        This is a powerful, generic search tool. The LLM is responsible for
        constructing the 'query' string using Quickwit's query language.

        Args:
            index: Quickwit index name (e.g., 'application_logs_v4').
            query: The search query string. Can include filters on any field
                   in the schema (e.g., 'device_id:dev_123 AND level:ERROR').
            start_time: Optional start time for the search window.
            end_time: Optional end time for the search window.
            limit: Maximum number of log entries to return.
            start_offset: Number of log entries to skip from the beginning.

        Returns:
            A list of log entries matching the search criteria.

        Query Examples:
            - To find errors for a device:
              query='device_id:dev_123 AND level:ERROR'
            - To find logs for a workspace:
              query='workspace_id:ws_abc AND "some error message"'
            - To find logs for a specific job:
              query='job_id:job_xyz'
        """
        search_params = {
            "query": query,
            "max_hits": limit,
            "start_offset": start_offset,
            "format": "json",
        }

        # Add time range filters if provided (using Quickwit's time range format)
        if start_time:
            search_params["start_timestamp"] = int(start_time.timestamp() * 1000)
        if end_time:
            search_params["end_timestamp"] = int(end_time.timestamp() * 1000)

        try:
            response = await self.client.post(
                f"/api/v1/{index}/search", json=search_params
            )
            response.raise_for_status()

            data = response.json()
            return data.get("hits", [])

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(f"Index '{index}' not found")
            elif e.response.status_code == 400:
                error_detail = e.response.json().get("detail", str(e))
                raise ValueError(
                    f"Invalid search query: {query}. Error: {error_detail}"
                )
            else:
                raise
