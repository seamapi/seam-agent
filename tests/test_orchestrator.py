from seam_agent.assistant.orchestrator import analyze_device_issue
from seam_agent.assistant.models import AnalysisResult


def test_analyze_device_issue():
    """
    Tests the full flow of the device issue analysis orchestrator.
    """
    # Given a device ID
    device_id = "device_123"

    # When we analyze the device issue
    result = analyze_device_issue(device_id)

    # Then we should get a valid analysis result
    assert isinstance(result, AnalysisResult)
    assert result.device.device_id == device_id
    assert len(result.action_attempts) == 2
    assert "online" in result.summary
    assert result.root_cause == "Device is offline."
    assert len(result.timeline) == 2
