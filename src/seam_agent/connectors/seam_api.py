import httpx
import os
from typing import Any


class SeamAPIClient:
    """Async client for interacting with Seam device endpoints."""

    def __init__(
        self, api_key: str | None = None, base_url: str = "https://connect.getseam.com"
    ):
        self.api_key = api_key or os.getenv("SEAM_API_KEY")
        if not self.api_key:
            raise ValueError(
                "SEAM_API_KEY must be provided or set as environment variable"
            )

        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def list_devices(
        self,
        device_type: str | None = None,
        manufacturer: str | None = None,
        connected_account_id: str | None = None,
        device_ids: list[str] | None = None,
        limit: int | None = None,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        List devices from Seam API.

        Args:
            device_type: Filter by device type (e.g., "smart_lock", "thermostat")
            manufacturer: Filter by manufacturer (e.g., "august", "yale")
            connected_account_id: Filter by connected account ID
            device_ids: Array of specific device IDs to retrieve
            limit: Maximum number of devices to return (default 500)
            search: Search string for device name/ID

        Returns:
            List of device dictionaries with raw API data
        """
        params = {}
        if device_type:
            params["device_type"] = device_type
        if manufacturer:
            params["manufacturer"] = manufacturer
        if connected_account_id:
            params["connected_account_id"] = connected_account_id
        if device_ids:
            params["device_ids"] = device_ids
        if limit:
            params["limit"] = limit
        if search:
            params["search"] = search

        response = await self.client.get("/devices/list", params=params)
        response.raise_for_status()

        data = response.json()
        return data.get("devices", [])

    async def get_device(
        self, device_id: str | None = None, name: str | None = None
    ) -> dict[str, Any]:
        """
        Get a specific device by ID or name.

        Args:
            device_id: The device ID to retrieve
            name: The device name to retrieve (alternative to device_id)

        Returns:
            Device dictionary with raw API data

        Note: You must specify either device_id or name
        """
        if not device_id and not name:
            raise ValueError("Must specify either device_id or name")

        params = {}
        if device_id:
            params["device_id"] = device_id
        if name:
            params["name"] = name

        response = await self.client.get("/devices/get", params=params)
        response.raise_for_status()

        data = response.json()
        return data["device"]

    async def find_resources(self, search: str) -> dict[str, Any]:
        """
        Search for resources inside a workspace using the universal find endpoint.

        Args:
            search: Search term (UUID format) to find resources by

        Returns:
            Batch dictionary containing various resource types (devices, users, spaces, etc.)
        """
        params = {"search": search}

        response = await self.client.post("/workspaces/find_resources", params=params)
        response.raise_for_status()

        data = response.json()
        return data.get("batch", {})

    async def get_action_attempt(self, action_attempt_id: str) -> dict[str, Any]:
        """
        Get a specific action attempt by ID.

        Args:
            action_attempt_id: The action attempt ID to retrieve

        Returns:
            Action attempt dictionary with raw API data
        """
        params = {"action_attempt_id": action_attempt_id}

        response = await self.client.get("/action_attempts/get", params=params)
        response.raise_for_status()

        data = response.json()
        return data["action_attempt"]

    async def list_action_attempts(
        self, action_attempt_ids: list[str]
    ) -> list[dict[str, Any]]:
        """
        List specific action attempts by their IDs.

        Args:
            action_attempt_ids: List of action attempt IDs to retrieve

        Returns:
            List of action attempt dictionaries with raw API data
        """
        params = {"action_attempt_ids": action_attempt_ids}

        response = await self.client.get("/action_attempts/list", params=params)
        response.raise_for_status()

        data = response.json()
        return data.get("action_attempts", [])
