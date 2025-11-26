"""
Tests for the DynamicToolSelector and related components.
"""

import pytest

from seam_agent.assistant.dynamic_tool_selector import (
    DynamicToolSelector,
    ToolResult,
    InvestigationPhase,
)
from seam_agent.assistant.investigation_config import (
    InvestigationConfig,
    InvestigationState,
)


class MockParsedQuery:
    """Mock ParsedQuery for testing."""

    def __init__(
        self, question_type="device_issue", access_codes=None, device_ids=None
    ):
        self.question_type = question_type
        self.access_codes = access_codes or []
        self.device_ids = device_ids or []


class TestToolResult:
    """Test the ToolResult class functionality."""

    def test_create_tool_result_from_device_info_success(self):
        """Test creating ToolResult from successful device info."""
        raw_result = {
            "device_type": "schlage_lock",
            "workspace_id": "test-workspace",
            "properties": {"online": True},
        }

        result = ToolResult.from_raw_result("get_device_info", raw_result)

        assert result.tool_name == "get_device_info"
        assert result.success is True
        assert result.data_found is True
        assert result.needs_followup is False
        assert "Device type: schlage_lock" in result.key_findings

    def test_create_tool_result_from_device_info_offline(self):
        """Test creating ToolResult from offline device."""
        raw_result = {"device_type": "august_lock", "properties": {"online": False}}

        result = ToolResult.from_raw_result("get_device_info", raw_result)

        assert result.success is True
        assert result.data_found is True
        assert "Device is offline" in result.key_findings

    def test_create_tool_result_from_access_codes_with_unmanaged(self):
        """Test creating ToolResult from access codes with unmanaged codes."""
        raw_result = {
            "access_codes": [
                {"name": "managed_code", "is_managed": True},
                {"name": "unmanaged_code_1", "is_managed": False},
                {"name": "unmanaged_code_2", "is_managed": False},
            ]
        }

        result = ToolResult.from_raw_result("get_access_codes", raw_result)

        assert result.success is True
        assert result.data_found is True
        assert "2 unmanaged access codes found" in result.key_findings

    def test_create_tool_result_from_action_attempts_with_failures(self):
        """Test creating ToolResult from action attempts with failures."""
        raw_result = {
            "action_attempts": [
                {"status": "success"},
                {"status": "failed"},
                {"status": "failed"},
                {"status": "success"},
            ]
        }

        result = ToolResult.from_raw_result("get_action_attempts", raw_result)

        assert result.success is True
        assert result.data_found is True
        assert "2 failed action attempts found" in result.key_findings

    def test_create_tool_result_with_pagination(self):
        """Test creating ToolResult that needs followup due to pagination."""
        raw_result = {
            "access_codes": [{"name": "code1"}],
            "pagination": {"has_more": True, "suggested_next_limit": 20},
        }

        result = ToolResult.from_raw_result("get_access_codes", raw_result)

        assert result.needs_followup is True
        assert result.data_found is True

    def test_create_tool_result_with_error(self):
        """Test creating ToolResult from failed tool execution."""
        raw_result = {"error": "Device not found"}

        result = ToolResult.from_raw_result("get_device_info", raw_result)

        assert result.success is False
        assert result.data_found is False
        assert result.needs_followup is False


class TestDynamicToolSelector:
    """Test the DynamicToolSelector class functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.selector = DynamicToolSelector()
        self.config = InvestigationConfig.create_production_config()

    def test_select_initial_tools_for_access_code_issue(self):
        """Test initial tool selection for access code issues."""
        parsed_query = MockParsedQuery(
            question_type="access_code", access_codes=["test-code"]
        )
        query = "Hi team, can you help me check if this unmanaged code is something we created?"

        tools = self.selector.select_initial_tools(parsed_query, query)

        assert "get_device_info" in tools
        assert "get_access_codes" in tools
        assert "get_audit_logs" in tools
        assert len(tools) >= 3

    def test_select_initial_tools_for_connectivity_issue(self):
        """Test initial tool selection for connectivity issues."""
        parsed_query = MockParsedQuery()
        query = "The device appears to be offline and not responding to commands"

        tools = self.selector.select_initial_tools(parsed_query, query)

        assert "get_device_info" in tools
        assert "get_device_events" in tools

    def test_select_initial_tools_for_action_issue(self):
        """Test initial tool selection for action/operation issues."""
        parsed_query = MockParsedQuery()
        query = "The unlock operation failed with an error"

        tools = self.selector.select_initial_tools(parsed_query, query)

        assert "get_device_info" in tools
        assert "get_action_attempts" in tools

    def test_select_initial_tools_for_general_issue(self):
        """Test initial tool selection for unclear/general issues."""
        parsed_query = MockParsedQuery()
        query = "Something is wrong with my device"

        tools = self.selector.select_initial_tools(parsed_query, query)

        assert "get_device_info" in tools
        assert "get_action_attempts" in tools
        assert "get_device_events" in tools

    def test_should_continue_investigation_with_sufficient_data(self):
        """Test investigation continuation decision with sufficient data."""
        # Set up selector with sufficient data
        self.selector.tool_results = {
            "get_device_info": ToolResult(
                tool_name="get_device_info",
                success=True,
                data_found=True,
                needs_followup=False,
                key_findings=["Device type: schlage_lock"],
                raw_result={},
            ),
            "get_access_codes": ToolResult(
                tool_name="get_access_codes",
                success=True,
                data_found=True,
                needs_followup=False,
                key_findings=["2 access codes found"],
                raw_result={},
            ),
        }

        state = InvestigationState()
        should_continue, reason = self.selector.should_continue_investigation(
            state, self.config
        )

        assert should_continue is False
        assert "sufficient data" in reason.lower()

    def test_should_continue_investigation_with_limits_reached(self):
        """Test investigation stops when limits are reached."""
        state = InvestigationState()
        # Simulate reaching round limits
        for _ in range(self.config.MAX_TOOL_ROUNDS):
            state.start_new_round()

        should_continue, reason = self.selector.should_continue_investigation(
            state, self.config
        )

        assert should_continue is False
        assert "limits reached" in reason.lower()

    def test_should_continue_investigation_with_critical_failures(self):
        """Test investigation continues with critical failures."""
        # Set up selector with critical failure
        self.selector.tool_results = {
            "get_device_info": ToolResult(
                tool_name="get_device_info",
                success=False,
                data_found=False,
                needs_followup=True,
                key_findings=[],
                raw_result={"error": "Device not found"},
            )
        }

        state = InvestigationState()
        should_continue, reason = self.selector.should_continue_investigation(
            state, self.config
        )

        assert should_continue is True
        assert "critical failures" in reason.lower()

    def test_select_followup_tools_with_pagination_needs(self):
        """Test follow-up tool selection when pagination is needed."""
        # Set up previous results with pagination
        previous_results = {
            "get_access_codes": {
                "access_codes": [{"name": "code1"}],
                "pagination": {"has_more": True},
            }
        }

        state = InvestigationState()
        state.start_new_round()
        parsed_query = MockParsedQuery()

        followup_tools = self.selector.select_followup_tools(
            previous_results, state, self.config, parsed_query
        )

        assert "get_access_codes" in followup_tools

    def test_select_followup_tools_analytical(self):
        """Test follow-up tool selection for deeper analysis."""
        # Set up results that suggest need for analysis
        previous_results = {
            "get_device_info": {"error": "Device not found"},
            "get_action_attempts": {
                "action_attempts": [{"status": "failed"}, {"status": "failed"}]
            },
        }

        state = InvestigationState()
        state.start_new_round()
        parsed_query = MockParsedQuery()

        followup_tools = self.selector.select_followup_tools(
            previous_results, state, self.config, parsed_query
        )

        # Should suggest third-party device lookup and audit logs
        assert "get_third_party_device_info" in followup_tools
        assert "get_audit_logs" in followup_tools

    def test_investigation_phase_progression(self):
        """Test that investigation phases progress correctly."""
        assert self.selector.investigation_phase == InvestigationPhase.INITIAL

        state = InvestigationState()
        state.start_new_round()
        self.selector._update_investigation_phase(state)
        assert self.selector.investigation_phase == InvestigationPhase.GATHERING

        state.start_new_round()
        self.selector._update_investigation_phase(state)
        assert self.selector.investigation_phase == InvestigationPhase.ANALYZING

        state.start_new_round()
        self.selector._update_investigation_phase(state)
        assert self.selector.investigation_phase == InvestigationPhase.DEEP_DIVE

    def test_get_investigation_summary(self):
        """Test investigation summary generation."""
        # Set up some tool results
        self.selector.tool_results = {
            "get_device_info": ToolResult(
                tool_name="get_device_info",
                success=True,
                data_found=True,
                needs_followup=False,
                key_findings=["Device type: schlage_lock"],
                raw_result={},
            ),
            "get_access_codes": ToolResult(
                tool_name="get_access_codes",
                success=True,
                data_found=True,
                needs_followup=True,
                key_findings=["5 access codes found"],
                raw_result={},
            ),
        }

        summary = self.selector.get_investigation_summary()

        assert summary["phase"] == "initial"
        assert "get_device_info" in summary["tools_used"]
        assert "get_access_codes" in summary["tools_used"]
        assert "Device type: schlage_lock" in summary["key_findings"]
        assert "5 access codes found" in summary["key_findings"]
        assert "get_access_codes" in summary["needs_followup"]
        assert summary["data_quality"] in ["excellent", "good", "fair", "poor"]

    def test_data_quality_assessment(self):
        """Test data quality assessment logic."""
        # Test excellent quality
        self.selector.tool_results = {
            "tool1": ToolResult("tool1", True, True, False, [], {}),
            "tool2": ToolResult("tool2", True, True, False, [], {}),
            "tool3": ToolResult("tool3", True, False, False, [], {}),
        }
        assert self.selector._assess_data_quality() == "excellent"

        # Test poor quality
        self.selector.tool_results = {
            "tool1": ToolResult("tool1", False, False, False, [], {}),
            "tool2": ToolResult("tool2", False, False, False, [], {}),
        }
        assert self.selector._assess_data_quality() == "poor"

    def test_issue_type_detection(self):
        """Test the issue type detection methods."""
        # Test access code issue detection
        parsed_query = MockParsedQuery(
            question_type="access_code", access_codes=["test"]
        )
        query = "unmanaged code issue"
        assert self.selector._is_access_code_issue(parsed_query, query) is True

        # Test connectivity issue detection
        query = "device is offline and disconnected"
        assert self.selector._is_connectivity_issue(parsed_query, query) is True

        # Test action issue detection
        query = "unlock failed with error"
        assert self.selector._is_action_issue(parsed_query, query) is True


class TestIntegrationWithInvestigationConfig:
    """Test integration between DynamicToolSelector and InvestigationConfig."""

    def test_respects_tool_limits_in_followup_selection(self):
        """Test that follow-up tool selection respects configuration limits."""
        selector = DynamicToolSelector()
        config = InvestigationConfig(MAX_TOOLS_PER_ROUND=2, MAX_TOTAL_TOOLS=4)

        state = InvestigationState()
        state.start_new_round()
        state.record_tool_use()  # 1 tool used

        # Mock results that would suggest many follow-up tools
        previous_results = {
            "get_device_info": {"error": "Device not found"},
            "get_access_codes": {"access_codes": [], "pagination": {"has_more": True}},
        }

        followup_tools = selector.select_followup_tools(
            previous_results, state, config, MockParsedQuery()
        )

        # Should respect the MAX_TOOLS_PER_ROUND limit (2 total - 1 used = 1 remaining)
        assert len(followup_tools) <= 1

    def test_stops_when_tool_budget_exhausted(self):
        """Test that selector stops when tool budget is exhausted."""
        selector = DynamicToolSelector()
        config = InvestigationConfig(MAX_TOOLS_PER_ROUND=1, MAX_TOTAL_TOOLS=1)

        state = InvestigationState()
        state.start_new_round()
        state.record_tool_use()  # Budget exhausted

        followup_tools = selector.select_followup_tools(
            {}, state, config, MockParsedQuery()
        )

        assert len(followup_tools) == 0


if __name__ == "__main__":
    pytest.main([__file__])
