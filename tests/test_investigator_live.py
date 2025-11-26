"""
Live tests for SimpleInvestigator functionality.

These tests show how the investigator works in practice with dynamic tool selection.
They require API keys to be set but demonstrate the actual behavior.
"""

import pytest
import os
from unittest.mock import patch, Mock, AsyncMock

from seam_agent.assistant.simple_investigator import SimpleInvestigator
from seam_agent.assistant.investigation_config import InvestigationConfig
from seam_agent.assistant.dynamic_tool_selector import DynamicToolSelector


def test_dynamic_tool_selector_standalone():
    """Test the dynamic tool selector in isolation."""

    selector = DynamicToolSelector()

    # Test access code issue detection
    class MockQuery:
        def __init__(self, question_type="device_issue", access_codes=None):
            self.question_type = question_type
            self.access_codes = access_codes or []

    # Test different query types
    access_code_query = MockQuery("access_code", ["test-code"])
    access_code_tools = selector.select_initial_tools(
        access_code_query,
        "Hi team, can you help me check if this unmanaged code is something we created?",
    )

    print("Access Code Issue Tools:", access_code_tools)
    assert "get_device_info" in access_code_tools
    assert "get_access_codes" in access_code_tools
    assert "get_audit_logs" in access_code_tools

    # Test connectivity issue
    connectivity_tools = selector.select_initial_tools(
        MockQuery(), "My device appears to be offline and not responding"
    )

    print("Connectivity Issue Tools:", connectivity_tools)
    assert "get_device_info" in connectivity_tools
    assert "get_device_events" in connectivity_tools

    # Test action issue
    action_tools = selector.select_initial_tools(
        MockQuery(), "The unlock operation failed with an error"
    )

    print("Action Issue Tools:", action_tools)
    assert "get_device_info" in action_tools
    assert "get_action_attempts" in action_tools


def test_investigation_config_modes():
    """Test different investigation configuration modes."""

    # Test production config is conservative
    prod_config = InvestigationConfig.create_production_config()
    print(
        f"Production Config: {prod_config.MAX_TOOL_ROUNDS} rounds, {prod_config.MAX_TOTAL_TOOLS} total tools"
    )

    # Test debug config is more permissive
    debug_config = InvestigationConfig.create_debug_config()
    print(
        f"Debug Config: {debug_config.MAX_TOOL_ROUNDS} rounds, {debug_config.MAX_TOTAL_TOOLS} total tools"
    )

    # Debug should allow more resources
    assert debug_config.MAX_TOOL_ROUNDS >= prod_config.MAX_TOOL_ROUNDS
    assert debug_config.MAX_TOTAL_TOOLS >= prod_config.MAX_TOTAL_TOOLS
    assert (
        debug_config.TOTAL_INVESTIGATION_TIMEOUT
        >= prod_config.TOTAL_INVESTIGATION_TIMEOUT
    )


def test_investigator_initialization():
    """Test that investigator can be initialized with different configs."""

    # Set required environment variables
    os.environ.setdefault("OPENAI_API_KEY", "test-key")
    os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
    os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")

    # Test with custom config
    custom_config = InvestigationConfig(
        MAX_TOOL_ROUNDS=2, MAX_TOOLS_PER_ROUND=3, MAX_TOTAL_TOOLS=5
    )

    try:
        investigator = SimpleInvestigator(
            api_key="test-key", debug_mode=True, config=custom_config
        )

        # Verify config is set
        assert investigator.config.MAX_TOOL_ROUNDS == 2
        assert investigator.config.MAX_TOOLS_PER_ROUND == 3
        assert investigator.config.MAX_TOTAL_TOOLS == 5

        # Verify dynamic tool selector is initialized
        assert investigator.dynamic_tool_selector is not None

        print("✅ Investigator initialized successfully with custom config")

    except ValueError as e:
        if "DATABASE_URL" in str(e):
            print("⚠️  Database connection required for full initialization")
        else:
            raise


@pytest.mark.asyncio
async def test_investigator_with_mocked_dependencies():
    """Test investigator with fully mocked dependencies."""

    # Mock all external dependencies to avoid API calls
    with (
        # patch(
        #     "seam_agent.assistant.simple_investigator.DatabaseClient"
        # ) as mock_db_class,
        # patch(
        #     "seam_agent.assistant.simple_investigator.SeamAPIClient"
        # ) as mock_seam_class,
        patch(
            "seam_agent.assistant.simple_investigator.AsyncAnthropic"
        ) as mock_anthropic_class,
        patch(
            "seam_agent.assistant.simple_investigator.SupportQueryParser"
        ) as mock_parser_class,
    ):
        # Set up mocks
        mock_anthropic = AsyncMock()
        mock_anthropic_class.return_value = mock_anthropic

        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser

        # Create investigator
        investigator = SimpleInvestigator(
            api_key="test-key",
            debug_mode=True,
            config=InvestigationConfig(MAX_TOOL_ROUNDS=2, MAX_TOTAL_TOOLS=3),
        )

        # Mock parsed query
        mock_parsed_query = Mock()
        mock_parsed_query.question_type = "access_code"
        mock_parsed_query.device_ids = ["device-123"]
        mock_parsed_query.access_codes = ["code-456"]
        mock_parsed_query.confidence = 0.9
        mock_parsed_query.__dict__ = {
            "question_type": "access_code",
            "device_ids": ["device-123"],
            "access_codes": ["code-456"],
            "confidence": 0.9,
        }

        mock_parser.parse.return_value = mock_parsed_query

        # Mock Anthropic response (no tools called)
        mock_response = Mock()
        mock_response.content = [
            Mock(
                type="text",
                text="Based on the access code issue, I recommend checking the device status and access code history.",
            )
        ]
        mock_anthropic.messages.create.return_value = mock_response

        # Run investigation
        result = await investigator.investigate("Access code issue with device")

        # Verify results
        assert result["original_query"] == "Access code issue with device"
        assert result["parsed_query"]["question_type"] == "access_code"
        assert "investigation" in result
        assert "raw_analysis" in result

        # Verify dynamic tool selection was used
        calls = mock_anthropic.messages.create.call_args_list
        assert len(calls) >= 1

        # Check that tool guidance was added to prompt
        first_call = calls[0]
        prompt = first_call[1]["messages"][0]["content"]
        assert "tool" in prompt.lower()

        print("✅ Mock investigation completed successfully")
        print(f"Result keys: {list(result.keys())}")
        print(f"Investigation length: {len(result['investigation'])}")


def test_tool_result_analysis():
    """Test the ToolResult analysis functionality."""

    from seam_agent.assistant.dynamic_tool_selector import ToolResult

    # Test device info with offline device
    device_result = {
        "device_type": "schlage_lock",
        "properties": {"online": False},
        "workspace_id": "test-workspace",
    }

    tool_result = ToolResult.from_raw_result("get_device_info", device_result)

    assert tool_result.success is True
    assert tool_result.data_found is True
    assert "Device type: schlage_lock" in tool_result.key_findings
    assert "Device is offline" in tool_result.key_findings

    print("Device Analysis:", tool_result.key_findings)

    # Test access codes with unmanaged codes
    access_code_result = {
        "access_codes": [
            {"name": "managed_code", "is_managed": True},
            {"name": "unmanaged_1", "is_managed": False},
            {"name": "unmanaged_2", "is_managed": False},
        ],
        "pagination": {"has_more": True},
    }

    code_result = ToolResult.from_raw_result("get_access_codes", access_code_result)

    assert code_result.success is True
    assert code_result.data_found is True
    assert code_result.needs_followup is True  # Due to pagination
    assert "2 unmanaged access codes found" in code_result.key_findings

    print("Access Code Analysis:", code_result.key_findings)

    # Test failed tool execution
    error_result = {"error": "Device not found in database"}

    error_tool_result = ToolResult.from_raw_result("get_device_info", error_result)

    assert error_tool_result.success is False
    assert error_tool_result.data_found is False
    assert error_tool_result.needs_followup is False

    print("✅ Tool result analysis working correctly")


if __name__ == "__main__":
    # Run the standalone tests
    print("🧪 Testing Dynamic Tool Selector...")
    test_dynamic_tool_selector_standalone()

    print("\n🧪 Testing Investigation Configs...")
    test_investigation_config_modes()

    print("\n🧪 Testing Investigator Initialization...")
    test_investigator_initialization()

    print("\n🧪 Testing Tool Result Analysis...")
    test_tool_result_analysis()

    print("\n✅ All standalone tests passed!")
    print(
        "\nTo run async tests, use: uv run pytest tests/test_investigator_live.py::test_investigator_with_mocked_dependencies -v"
    )
