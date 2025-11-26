"""
Integration tests for SimpleInvestigator with dynamic tool selection.

These tests use mocked connectors to avoid requiring database/API access.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import os

from seam_agent.assistant.simple_investigator import SimpleInvestigator
from seam_agent.assistant.investigation_config import InvestigationConfig
from seam_agent.assistant.query_parser import ParsedQuery

# Set environment variables for testing
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")


class TestSimpleInvestigatorIntegration:
    """Test SimpleInvestigator with mocked dependencies."""

    @pytest.fixture
    def mock_investigator(self):
        """Create a SimpleInvestigator with mocked dependencies."""

        # Mock all the external dependencies
        with (
            patch("seam_agent.assistant.simple_investigator.DatabaseClient") as mock_db,
            patch(
                "seam_agent.assistant.simple_investigator.SeamAPIClient"
            ) as mock_seam,
            patch(
                "seam_agent.assistant.simple_investigator.AsyncAnthropic"
            ) as mock_anthropic,
        ):
            # Configure the mocks
            mock_anthropic_instance = AsyncMock()
            mock_anthropic.return_value = mock_anthropic_instance

            # Create investigator with test config
            config = InvestigationConfig(
                MAX_TOOL_ROUNDS=2, MAX_TOOLS_PER_ROUND=3, MAX_TOTAL_TOOLS=5
            )

            investigator = SimpleInvestigator(
                api_key="test-key", debug_mode=True, config=config
            )

            # Store references for test assertions
            investigator._mock_anthropic = mock_anthropic_instance
            investigator._mock_db = mock_db.return_value
            investigator._mock_seam = mock_seam.return_value

            return investigator

    @pytest.fixture
    def mock_parsed_query(self):
        """Create a mock parsed query for access code issue."""
        query = Mock(spec=ParsedQuery)
        query.question_type = "access_code"
        query.device_ids = ["test-device-123"]
        query.access_codes = ["test-code-456"]
        query.confidence = 0.9
        query.__dict__ = {
            "question_type": "access_code",
            "device_ids": ["test-device-123"],
            "access_codes": ["test-code-456"],
            "confidence": 0.9,
        }
        return query

    @pytest.mark.asyncio
    async def test_investigator_dynamic_tool_selection_flow(
        self, mock_investigator, mock_parsed_query
    ):
        """Test that the investigator uses dynamic tool selection correctly."""

        # Mock the query parser
        with patch.object(
            mock_investigator.query_parser, "parse", return_value=mock_parsed_query
        ):
            # Mock Anthropic responses
            mock_response = Mock()
            mock_response.content = [
                Mock(
                    type="text",
                    text="I'll investigate this access code issue using the recommended tools.",
                )
            ]

            mock_investigator._mock_anthropic.messages.create.return_value = (
                mock_response
            )

            # Test query
            test_query = "Hi team, can you help me check if this unmanaged code is something we created?"

            # Run the investigation
            result = await mock_investigator.investigate(test_query)

            # Verify results
            assert result["original_query"] == test_query
            assert result["parsed_query"]["question_type"] == "access_code"
            assert "investigation" in result
            assert "raw_analysis" in result

            # Verify dynamic tool selection was used
            # The initial tool selection should have recommended access code related tools
            calls = mock_investigator._mock_anthropic.messages.create.call_args_list
            assert len(calls) >= 1

            # Check that the prompt included tool guidance
            initial_call = calls[0]
            prompt_content = initial_call[1]["messages"][0]["content"]
            assert "get_device_info" in prompt_content
            assert "get_access_codes" in prompt_content

    @pytest.mark.asyncio
    async def test_investigator_handles_tool_calling_with_limits(
        self, mock_investigator, mock_parsed_query
    ):
        """Test that investigator respects tool calling limits."""

        with patch.object(
            mock_investigator.query_parser, "parse", return_value=mock_parsed_query
        ):
            # Mock a response that requests tools
            mock_tool_response = Mock()
            mock_tool_response.content = [
                Mock(
                    type="tool_use",
                    id="tool_call_1",
                    name="get_device_info",
                    input={"device_id": "test-device-123"},
                )
            ]

            # Mock tool orchestrator response
            mock_investigator.tool_orchestrator.execute_tool = AsyncMock(
                return_value={
                    "device_type": "schlage_lock",
                    "properties": {"online": True},
                }
            )

            mock_investigator.tool_orchestrator.summarize_tool_result = Mock(
                return_value="Device found: schlage_lock"
            )

            # Mock follow-up response (no more tools)
            mock_final_response = Mock()
            mock_final_response.content = [
                Mock(
                    type="text",
                    text="Based on the device information, this appears to be a standard Schlage lock configuration issue.",
                )
            ]

            mock_investigator._mock_anthropic.messages.create.side_effect = [
                mock_tool_response,  # Initial response with tool call
                mock_final_response,  # Final analysis
            ]

            # Run investigation
            result = await mock_investigator.investigate("Device access code issue")

            # Verify the investigation completed
            assert result["original_query"] == "Device access code issue"
            assert "investigation" in result

            # Verify tool was executed
            mock_investigator.tool_orchestrator.execute_tool.assert_called_once_with(
                "get_device_info", {"device_id": "test-device-123"}
            )

            # Verify dynamic tool selection logic was invoked
            # Should have at least initial call + follow-up call
            assert (
                len(mock_investigator._mock_anthropic.messages.create.call_args_list)
                >= 2
            )

    @pytest.mark.asyncio
    async def test_investigator_respects_investigation_limits(
        self, mock_investigator, mock_parsed_query
    ):
        """Test that investigator stops when limits are reached."""

        # Use very restrictive config
        restrictive_config = InvestigationConfig(
            MAX_TOOL_ROUNDS=1, MAX_TOOLS_PER_ROUND=1, MAX_TOTAL_TOOLS=1
        )
        mock_investigator.config = restrictive_config

        with patch.object(
            mock_investigator.query_parser, "parse", return_value=mock_parsed_query
        ):
            # Mock responses that would normally trigger many tool calls
            mock_tool_response = Mock()
            mock_tool_response.content = [
                Mock(
                    type="tool_use",
                    id="tool1",
                    name="get_device_info",
                    input={"device_id": "test"},
                ),
                Mock(
                    type="tool_use",
                    id="tool2",
                    name="get_access_codes",
                    input={"device_id": "test"},
                ),  # This should be limited
            ]

            mock_investigator.tool_orchestrator.execute_tool = AsyncMock(
                return_value={"result": "test"}
            )
            mock_investigator.tool_orchestrator.summarize_tool_result = Mock(
                return_value="Tool result"
            )

            mock_final_response = Mock()
            mock_final_response.content = [Mock(type="text", text="Analysis complete")]

            mock_investigator._mock_anthropic.messages.create.side_effect = [
                mock_tool_response,
                mock_final_response,
            ]

            # Run investigation
            result = await mock_investigator.investigate("Test query")

            # Should complete without error
            assert "investigation" in result

            # Should have executed only 1 tool due to limits
            assert mock_investigator.tool_orchestrator.execute_tool.call_count == 1

    def test_dynamic_tool_selector_initialization(self, mock_investigator):
        """Test that dynamic tool selector is properly initialized."""

        # Check that dynamic tool selector exists
        assert hasattr(mock_investigator, "dynamic_tool_selector")
        assert mock_investigator.dynamic_tool_selector is not None

        # Check that it can select initial tools
        from seam_agent.assistant.query_parser import ParsedQuery

        mock_query = Mock(spec=ParsedQuery)
        mock_query.question_type = "access_code"
        mock_query.access_codes = ["test"]

        initial_tools = mock_investigator.dynamic_tool_selector.select_initial_tools(
            mock_query, "access code issue"
        )

        assert len(initial_tools) > 0
        assert "get_device_info" in initial_tools
        assert "get_access_codes" in initial_tools

    def test_configuration_integration(self, mock_investigator):
        """Test that configuration is properly integrated."""

        # Check config is set
        assert mock_investigator.config is not None
        assert mock_investigator.config.MAX_TOOL_ROUNDS == 2
        assert mock_investigator.config.MAX_TOOLS_PER_ROUND == 3
        assert mock_investigator.config.MAX_TOTAL_TOOLS == 5

        # Check debug mode affects config
        debug_investigator = SimpleInvestigator(debug_mode=True)
        prod_investigator = SimpleInvestigator(debug_mode=False)

        # Debug should allow more tools (though both will fail due to missing DB)
        try:
            debug_config = debug_investigator.config
            prod_config = prod_investigator.config
            assert debug_config.MAX_TOTAL_TOOLS >= prod_config.MAX_TOTAL_TOOLS
        except ValueError:
            # Expected due to missing DATABASE_URL, but config creation should work
            pass


def test_investigator_can_be_imported():
    """Test that SimpleInvestigator can be imported and basic functionality works."""

    # This should work without database connection
    assert SimpleInvestigator is not None

    # Test configuration creation
    config = InvestigationConfig.create_production_config()
    assert config.MAX_TOOL_ROUNDS > 0

    config = InvestigationConfig.create_debug_config()
    assert config.MAX_TOOL_ROUNDS > 0


@pytest.mark.asyncio
async def test_mock_investigation_realistic_flow():
    """Test a realistic investigation flow with mocked components."""

    # Mock all external dependencies
    with (
        patch("seam_agent.assistant.simple_investigator.DatabaseClient"),
        patch("seam_agent.assistant.simple_investigator.SeamAPIClient"),
        patch(
            "seam_agent.assistant.simple_investigator.AsyncAnthropic"
        ) as mock_anthropic_class,
    ):
        # Set up anthropic mock
        mock_anthropic = AsyncMock()
        mock_anthropic_class.return_value = mock_anthropic

        # Create investigator
        investigator = SimpleInvestigator(
            api_key="test",
            debug_mode=True,
            config=InvestigationConfig(MAX_TOOL_ROUNDS=2, MAX_TOTAL_TOOLS=3),
        )

        # Mock query parser
        mock_parsed_query = Mock()
        mock_parsed_query.question_type = "device_issue"
        mock_parsed_query.device_ids = ["device-123"]
        mock_parsed_query.access_codes = []
        mock_parsed_query.confidence = 0.8
        mock_parsed_query.__dict__ = {
            "question_type": "device_issue",
            "device_ids": ["device-123"],
            "access_codes": [],
            "confidence": 0.8,
        }

        with patch.object(
            investigator.query_parser, "parse", return_value=mock_parsed_query
        ):
            # Mock simple text response (no tools)
            mock_response = Mock()
            mock_response.content = [
                Mock(
                    type="text",
                    text="Based on the query, this appears to be a general device connectivity issue. I recommend checking the device status and recent events.",
                )
            ]

            mock_anthropic.messages.create.return_value = mock_response

            # Run investigation
            result = await investigator.investigate(
                "My device seems to be having connectivity issues"
            )

            # Verify basic structure
            assert isinstance(result, dict)
            assert "original_query" in result
            assert "parsed_query" in result
            assert "investigation" in result
            assert "raw_analysis" in result

            # Verify query was processed
            assert (
                result["original_query"]
                == "My device seems to be having connectivity issues"
            )
            assert result["parsed_query"]["question_type"] == "device_issue"

            # Verify Anthropic was called with tool guidance
            calls = mock_anthropic.messages.create.call_args_list
            assert len(calls) >= 1

            # Check that dynamic tool selection added guidance to the prompt
            first_call = calls[0]
            messages = first_call[1]["messages"]
            prompt = messages[0]["content"]

            # Should contain tool recommendations for device issues
            assert "tool" in prompt.lower() or "investigate" in prompt.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
