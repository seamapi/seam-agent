"""
Tests for the InvestigationConfig and InvestigationState classes.
"""

import pytest

from seam_agent.assistant.investigation_config import (
    InvestigationConfig,
    InvestigationState,
    InvestigationLimitError,
)


class TestInvestigationConfig:
    """Test the InvestigationConfig class."""

    def test_default_config_values(self):
        """Test that default configuration has reasonable values."""
        config = InvestigationConfig()

        assert config.MAX_TOOL_ROUNDS >= 1
        assert config.MAX_TOOLS_PER_ROUND >= 1
        assert config.MAX_TOTAL_TOOLS >= config.MAX_TOOLS_PER_ROUND
        assert config.CONTEXT_BUDGET_TOKENS > 1000
        assert config.TOOL_EXECUTION_TIMEOUT > 0
        assert config.TOTAL_INVESTIGATION_TIMEOUT > config.TOOL_EXECUTION_TIMEOUT

    def test_production_config(self):
        """Test production configuration is conservative."""
        config = InvestigationConfig.create_production_config()

        assert config.MAX_TOOL_ROUNDS <= 3  # Conservative for production
        assert config.MAX_TOTAL_TOOLS <= 10  # Reasonable limit
        assert config.TOTAL_INVESTIGATION_TIMEOUT <= 120  # 2 minutes max

        # Should be more restrictive than default
        default_config = InvestigationConfig()
        assert config.MAX_TOOL_ROUNDS <= default_config.MAX_TOOL_ROUNDS
        assert config.MAX_TOTAL_TOOLS <= default_config.MAX_TOTAL_TOOLS

    def test_debug_config(self):
        """Test debug configuration is more permissive."""
        config = InvestigationConfig.create_debug_config()

        assert config.MAX_TOOL_ROUNDS >= 3  # More rounds for debugging
        assert config.MAX_TOTAL_TOOLS >= 15  # More tools for exploration
        assert config.TOTAL_INVESTIGATION_TIMEOUT >= 180  # More time for debugging

        # Should be more permissive than production
        prod_config = InvestigationConfig.create_production_config()
        assert config.MAX_TOOL_ROUNDS >= prod_config.MAX_TOOL_ROUNDS
        assert config.MAX_TOTAL_TOOLS >= prod_config.MAX_TOTAL_TOOLS

    def test_pagination_limits(self):
        """Test pagination-related configuration."""
        config = InvestigationConfig()

        assert config.DEFAULT_PAGINATION_LIMIT > 0
        assert config.MAX_PAGINATION_LIMIT > config.DEFAULT_PAGINATION_LIMIT
        assert config.AGGRESSIVE_PAGINATION_LIMIT <= config.MAX_PAGINATION_LIMIT
        assert config.AGGRESSIVE_PAGINATION_LIMIT > config.DEFAULT_PAGINATION_LIMIT


class TestInvestigationState:
    """Test the InvestigationState class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = InvestigationConfig(
            MAX_TOOL_ROUNDS=3, MAX_TOOLS_PER_ROUND=5, MAX_TOTAL_TOOLS=10
        )
        self.state = InvestigationState()

    def test_initial_state(self):
        """Test initial investigation state."""
        assert self.state.tool_rounds_used == 0
        assert self.state.tools_used_this_round == 0
        assert self.state.total_tools_used == 0
        assert self.state.conversation_messages == 0
        assert self.state.start_time is None

    def test_can_continue_round_initially(self):
        """Test that we can continue round initially."""
        assert self.state.can_continue_round(self.config) is True

    def test_can_start_new_round_initially(self):
        """Test that we can start new round initially."""
        assert self.state.can_start_new_round(self.config) is True

    def test_record_tool_use(self):
        """Test recording tool usage."""
        initial_round_tools = self.state.tools_used_this_round
        initial_total_tools = self.state.total_tools_used

        self.state.record_tool_use()

        assert self.state.tools_used_this_round == initial_round_tools + 1
        assert self.state.total_tools_used == initial_total_tools + 1

    def test_start_new_round(self):
        """Test starting a new round."""
        # Use some tools first
        self.state.record_tool_use()
        self.state.record_tool_use()

        initial_rounds = self.state.tool_rounds_used

        self.state.start_new_round()

        assert self.state.tool_rounds_used == initial_rounds + 1
        assert self.state.tools_used_this_round == 0  # Reset for new round
        assert self.state.total_tools_used == 2  # Should remain

    def test_tools_per_round_limit(self):
        """Test that tools per round limit is enforced."""
        self.state.start_new_round()

        # Use up to the limit
        for _ in range(self.config.MAX_TOOLS_PER_ROUND):
            assert self.state.can_continue_round(self.config) is True
            self.state.record_tool_use()

        # Should not be able to continue round
        assert self.state.can_continue_round(self.config) is False

    def test_total_tools_limit(self):
        """Test that total tools limit is enforced."""
        # Start a round and use tools up to total limit
        self.state.start_new_round()

        for _ in range(self.config.MAX_TOTAL_TOOLS):
            # May need to start new rounds due to per-round limits
            if not self.state.can_continue_round(self.config):
                if self.state.can_start_new_round(self.config):
                    self.state.start_new_round()
                else:
                    break

            self.state.record_tool_use()

        # Should have reached total limit
        assert self.state.total_tools_used == self.config.MAX_TOTAL_TOOLS
        assert self.state.can_continue_round(self.config) is False

    def test_round_limit(self):
        """Test that round limit is enforced."""
        # Use up all rounds
        for _ in range(self.config.MAX_TOOL_ROUNDS):
            assert self.state.can_start_new_round(self.config) is True
            self.state.start_new_round()

        # Should not be able to start new round
        assert self.state.can_start_new_round(self.config) is False

    def test_record_message(self):
        """Test recording conversation messages."""
        initial_messages = self.state.conversation_messages

        self.state.record_message()

        assert self.state.conversation_messages == initial_messages + 1

    def test_get_limits_summary(self):
        """Test generating limits summary."""
        self.state.start_new_round()
        self.state.record_tool_use()
        self.state.record_message()

        summary = self.state.get_limits_summary()

        assert "Tool rounds: 1" in summary
        assert "Tools this round: 1" in summary
        assert "Total tools: 1" in summary
        assert "Messages: 1" in summary

    def test_complex_investigation_flow(self):
        """Test a complex investigation flow with multiple rounds."""
        # Round 1: Use 3 tools
        self.state.start_new_round()
        for _ in range(3):
            self.state.record_tool_use()

        assert self.state.tool_rounds_used == 1
        assert self.state.tools_used_this_round == 3
        assert self.state.total_tools_used == 3

        # Round 2: Use 2 more tools
        self.state.start_new_round()
        for _ in range(2):
            self.state.record_tool_use()

        assert self.state.tool_rounds_used == 2
        assert self.state.tools_used_this_round == 2
        assert self.state.total_tools_used == 5

        # Should still be able to continue
        assert self.state.can_start_new_round(self.config) is True
        assert self.state.can_continue_round(self.config) is True

    def test_edge_case_zero_limits(self):
        """Test behavior with edge case configurations."""
        edge_config = InvestigationConfig(
            MAX_TOOL_ROUNDS=1, MAX_TOOLS_PER_ROUND=1, MAX_TOTAL_TOOLS=1
        )

        state = InvestigationState()

        # Should be able to start one round
        assert state.can_start_new_round(edge_config) is True
        state.start_new_round()

        # Should be able to use one tool
        assert state.can_continue_round(edge_config) is True
        state.record_tool_use()

        # Should not be able to continue or start new round
        assert state.can_continue_round(edge_config) is False
        assert state.can_start_new_round(edge_config) is False


class TestInvestigationLimitError:
    """Test the InvestigationLimitError exception."""

    def test_limit_error_creation(self):
        """Test creating InvestigationLimitError."""
        message = "Test limit exceeded"
        error = InvestigationLimitError(message)

        assert str(error) == message
        assert isinstance(error, Exception)

    def test_limit_error_in_practical_scenario(self):
        """Test that limit errors are raised in practical scenarios."""
        config = InvestigationConfig(MAX_TOOL_ROUNDS=1, MAX_TOTAL_TOOLS=1)
        state = InvestigationState()

        # Simulate exceeding limits
        state.start_new_round()
        state.record_tool_use()

        # Should raise error if we try to continue beyond limits
        with pytest.raises(InvestigationLimitError):
            if not state.can_start_new_round(config):
                raise InvestigationLimitError("Round limit exceeded")

        with pytest.raises(InvestigationLimitError):
            if not state.can_continue_round(config):
                raise InvestigationLimitError("Tool limit exceeded")


class TestConfigurationInteraction:
    """Test interactions between different configuration scenarios."""

    def test_production_vs_debug_behavior(self):
        """Test difference in behavior between production and debug configs."""
        prod_config = InvestigationConfig.create_production_config()
        debug_config = InvestigationConfig.create_debug_config()

        # Simulate investigation that would exceed production limits
        state = InvestigationState()

        # Use tools up to production limit
        rounds_used = 0
        while (
            state.can_start_new_round(prod_config) and rounds_used < 10
        ):  # Safety valve
            state.start_new_round()
            rounds_used += 1
            while state.can_continue_round(prod_config):
                state.record_tool_use()

        prod_total_tools = state.total_tools_used

        # Reset and test with debug config
        state = InvestigationState()
        rounds_used = 0
        while (
            state.can_start_new_round(debug_config) and rounds_used < 10
        ):  # Safety valve
            state.start_new_round()
            rounds_used += 1
            while state.can_continue_round(debug_config):
                state.record_tool_use()

        debug_total_tools = state.total_tools_used

        # Debug should allow more tools
        assert debug_total_tools > prod_total_tools

    def test_configuration_consistency(self):
        """Test that configurations are internally consistent."""
        configs = [
            InvestigationConfig(),
            InvestigationConfig.create_production_config(),
            InvestigationConfig.create_debug_config(),
        ]

        for config in configs:
            # Total tools should be achievable with given rounds and tools per round
            max_possible = config.MAX_TOOL_ROUNDS * config.MAX_TOOLS_PER_ROUND
            assert (
                config.MAX_TOTAL_TOOLS <= max_possible
            ), f"Config inconsistent: {config}"

            # Timeouts should be reasonable
            assert config.TOOL_EXECUTION_TIMEOUT < config.TOTAL_INVESTIGATION_TIMEOUT

            # Pagination limits should be ordered correctly
            assert config.DEFAULT_PAGINATION_LIMIT <= config.AGGRESSIVE_PAGINATION_LIMIT
            assert config.AGGRESSIVE_PAGINATION_LIMIT <= config.MAX_PAGINATION_LIMIT


if __name__ == "__main__":
    pytest.main([__file__])
