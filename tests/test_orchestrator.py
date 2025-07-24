import asyncio
from unittest.mock import AsyncMock, patch
from seam_agent.assistant.orchestrator import analyze_device_issue


def test_analyze_device_issue():
    """
    Tests the full flow of the device issue analysis orchestrator.
    """
    # Mock device data (JSON response from API)
    mock_device = {
        "device_id": "device_123",
        "display_name": "Test Device",
        "properties": {"online": False},
    }

    async def run_test():
        # Mock the SeamAPIClient
        with patch(
            "seam_agent.assistant.orchestrator.SeamAPIClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get_device.return_value = mock_device
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Given a device ID
            device_id = "device_123"

            # When we analyze the device issue
            result = await analyze_device_issue(device_id)

            # Then we should get a valid analysis result (JSON dict)
            assert isinstance(result, dict)
            assert result["device"]["device_id"] == device_id
            assert result["analysis_type"] == "device_issue_analysis"
            assert "offline" in result["summary"]  # Device is offline in mock
            assert result["root_cause"] == "Device is offline."
            assert isinstance(result["timeline"], list)

            # Verify the client was called correctly
            mock_client.get_device.assert_called_once_with(device_id)

    # Run the async test
    asyncio.run(run_test())
