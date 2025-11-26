"""
Simple customer support investigator using Anthropic and query parsing.

Starts with just query parsing and will incrementally add tool calling.
"""

import asyncio
import os
import time
from typing import Any
from anthropic import AsyncAnthropic
from anthropic.types import (
    ToolParam,
    TextBlock,
    MessageParam,
    Message,
    ToolResultBlockParam,
    ToolUseBlock,
)

from seam_agent.assistant.query_parser import SupportQueryParser, ParsedQuery
from seam_agent.connectors.db import DatabaseClient
from seam_agent.connectors.seam_api import SeamAPIClient
from seam_agent.assistant.tool_registry import ToolRegistry
from seam_agent.assistant.dynamic_tool_selector import DynamicToolSelector
from seam_agent.assistant.prompt_manager import PromptManager
from seam_agent.assistant.investigation_strategy import InvestigationStrategy
from seam_agent.assistant.tool_orchestrator import ToolOrchestrator
from seam_agent.assistant.investigation_logger import InvestigationLogger, LogContext
from seam_agent.assistant.investigation_config import (
    InvestigationConfig,
    InvestigationState,
    InvestigationLimitError,
)


class SimpleInvestigator:
    anthropic: AsyncAnthropic
    db_client: DatabaseClient
    seam_client: SeamAPIClient
    query_parser: SupportQueryParser
    tool_registry: ToolRegistry
    dynamic_tool_selector: DynamicToolSelector
    prompt_manager: PromptManager
    investigation_strategy: InvestigationStrategy
    tool_orchestrator: ToolOrchestrator
    logger: InvestigationLogger
    tools: list[ToolParam]
    config: InvestigationConfig

    def __init__(
        self,
        api_key: str | None = None,
        debug_mode: bool = True,
        log_format: str = "human",
        config: InvestigationConfig | None = None,
    ):
        self.anthropic = AsyncAnthropic(
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY")
        )
        self.db_client = DatabaseClient()
        self.seam_client = SeamAPIClient()
        self.query_parser = SupportQueryParser()

        # Initialize configuration
        if config is None:
            self.config = (
                InvestigationConfig.create_debug_config()
                if debug_mode
                else InvestigationConfig.create_production_config()
            )
        else:
            self.config = config

        # Initialize logger
        self.logger = InvestigationLogger(
            debug_mode=debug_mode, output_format=log_format
        )

        # Initialize components
        self.tool_registry = ToolRegistry()
        self.dynamic_tool_selector = DynamicToolSelector()
        self.prompt_manager = PromptManager()
        self.investigation_strategy = InvestigationStrategy(
            self.tool_registry, self.prompt_manager
        )
        self.tool_orchestrator = ToolOrchestrator(
            self.db_client, self.seam_client, self.logger
        )

        # Get tool definitions from orchestrator
        self.tools = self.tool_orchestrator.get_tool_definitions()

    async def investigate(self, customer_query: str) -> dict[str, Any]:
        """
        Investigate a customer support query.

        Args:
            customer_query: Natural language customer support query

        Returns:
            Dict with parsed query info and formatted investigation note
        """
        # Initialize investigation state and tracking
        investigation_state = InvestigationState()
        investigation_state.start_time = time.time()

        # Start investigation logging
        self.logger.investigation_start(customer_query)
        self.logger.info(
            f"Investigation limits: {self.config.MAX_TOOL_ROUNDS} rounds, {self.config.MAX_TOTAL_TOOLS} total tools",
            LogContext.INVESTIGATION,
        )

        # Initialize defaults in case of early errors
        parsed_query = None
        formatted_investigation = "Investigation not completed"
        raw_analysis = "No analysis available"

        try:
            # Step 1: Parse the query to extract structured information
            parsed_query = await self.query_parser.parse(customer_query)
            self.logger.query_parsed(parsed_query.__dict__, parsed_query.confidence)

            # Step 2: Use Anthropic with tools to investigate
            raw_analysis = await self._investigate_with_tools(
                customer_query, parsed_query, investigation_state
            )

            # Step 3: Format the investigation into a structured internal note
            formatted_investigation = await self._format_investigation_note(
                raw_analysis
            )

            # Complete investigation logging
            self.logger.investigation_complete(len(formatted_investigation))
            self.logger.info(
                f"Investigation completed. {investigation_state.get_limits_summary()}",
                LogContext.INVESTIGATION,
            )

        except InvestigationLimitError as e:
            self.logger.warning(
                f"Investigation stopped due to limits: {str(e)}",
                LogContext.INVESTIGATION,
            )
            formatted_investigation = f"Investigation stopped due to resource limits: {str(e)}. Partial analysis may be available."
            raw_analysis = f"Investigation incomplete due to limits: {str(e)}"

        except Exception as e:
            self.logger.error(
                f"Investigation failed: {str(e)}", LogContext.INVESTIGATION
            )
            formatted_investigation = f"Investigation failed due to error: {str(e)}"
            raw_analysis = f"Investigation error: {str(e)}"

        result = {
            "original_query": customer_query,
            "parsed_query": parsed_query.__dict__ if parsed_query else {},
            "investigation": formatted_investigation,
            "raw_analysis": raw_analysis,  # Keep raw analysis for debugging
        }

        # Add debug information if available
        if self.logger.debug_mode:
            result["debug"] = {
                "log_summary": self.logger.get_summary(),
                "log_export": self.logger.export_json(),
            }

        return result

    def export_investigation_to_md(
        self, investigation_result: dict, filename: str | None = None
    ) -> str:
        """Export the complete investigation to a markdown file."""
        if filename is None:
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"investigation_{timestamp}.md"

        # Build the markdown content
        md_content = self._build_investigation_markdown(investigation_result)

        # Write to file
        with open(filename, "w", encoding="utf-8") as f:
            f.write(md_content)

        return filename

    def _build_investigation_markdown(self, result: dict) -> str:
        """Build the complete investigation markdown content."""
        from datetime import datetime

        md = f"""# Investigation Report
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Customer Query
```
{result['original_query'].strip()}
```

## Parsed Query Information
"""

        # Add parsed query details
        for key, value in result["parsed_query"].items():
            if value:  # Only show non-empty values
                if isinstance(value, list):
                    md += f"- **{key.replace('_', ' ').title()}**: {', '.join(map(str, value))}\n"
                else:
                    md += f"- **{key.replace('_', ' ').title()}**: {value}\n"

        md += f"""
## 🔍 Investigation Results

{result['investigation']}

## 📋 Raw Analysis
```
{result['raw_analysis']}
```

"""

        # Add debug information if available
        if "debug" in result:
            debug_info = result["debug"]

            md += "## 🔧 Debug Information\n\n"

            # Add log summary
            if "log_summary" in debug_info:
                summary = debug_info["log_summary"]
                md += f"""### Performance Summary
{summary}

"""

            # Add structured logs
            if "log_export" in debug_info:
                import json

                try:
                    logs = json.loads(debug_info["log_export"])

                    md += "### Investigation Timeline\n\n"
                    for i, log_entry in enumerate(logs, 1):
                        level = log_entry.get("level", "INFO")
                        context = log_entry.get("context", "general")
                        message = log_entry.get("message", "")
                        duration = log_entry.get("duration_ms")

                        duration_str = f" ({duration:.0f}ms)" if duration else ""

                        md += f"{i}. **[{level}]** `{context.upper()}` - {message}{duration_str}\n"

                        # Add data if it's important
                        if log_entry.get("data") and level in ["ERROR", "SUCCESS"]:
                            data = log_entry["data"]
                            if "key_findings" in data:
                                md += f"   - {data['key_findings']}\n"
                            elif "error" in data:
                                md += f"   - Error: {data['error']}\n"

                    md += "\n"
                except Exception:
                    md += "Debug log parsing failed\n\n"

        md += """---
*Generated by Seam Customer Support Investigation Assistant*
"""

        return md

    async def _investigate_with_tools(
        self,
        original_query: str,
        parsed_query: ParsedQuery,
        investigation_state: InvestigationState,
    ) -> str:
        """Use Anthropic with tools to investigate the customer query."""

        # Initialize dynamic tool selection for this investigation
        initial_tools = self.dynamic_tool_selector.select_initial_tools(
            parsed_query, original_query
        )
        self.logger.info(
            f"Dynamic tool selection recommends initial tools: {initial_tools}",
            LogContext.TOOL_EXECUTION,
        )

        prompt = self.prompt_manager.get_initial_investigation_prompt(
            original_query, parsed_query
        )

        # Add tool guidance to the prompt
        if initial_tools:
            tool_guidance = f"\n\nBased on the query analysis, consider using these tools for investigation: {', '.join(initial_tools)}"
            prompt += tool_guidance

        # Initial request to Anthropic with tools
        response = await self.anthropic.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            tools=self.tools,
            messages=[{"role": "user", "content": prompt}],
        )

        # Handle tool calls if Anthropic requests them
        if any(block.type == "tool_use" for block in response.content):
            return await self._handle_tool_calls(
                response, original_query, prompt, parsed_query, investigation_state
            )

        # If no tools called, return the direct response
        if response.content:
            for block in response.content:
                if isinstance(block, TextBlock):
                    return block.text
        return "No response generated"

    async def _format_investigation_note(self, raw_analysis: str) -> str:
        """Format the raw analysis into a structured internal support note."""
        format_prompt = self.prompt_manager.get_format_investigation_note_prompt(
            raw_analysis
        )

        response = await self.anthropic.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": format_prompt}],
        )

        if response.content:
            for block in response.content:
                if isinstance(block, TextBlock):
                    return block.text

        return raw_analysis  # Fallback to raw analysis if formatting fails

    async def _handle_tool_calls(
        self,
        response: Message,
        original_query: str,
        original_prompt: str,
        parsed_query,
        investigation_state: InvestigationState,
    ) -> str:
        """Execute tool calls and get final analysis from Anthropic."""

        # Start new tool round
        investigation_state.start_new_round()
        self.logger.info(
            f"Starting tool round {investigation_state.tool_rounds_used}",
            LogContext.TOOL_EXECUTION,
        )

        # Check if we can start this round
        if not investigation_state.can_start_new_round(self.config):
            raise InvestigationLimitError(
                f"Maximum tool rounds ({self.config.MAX_TOOL_ROUNDS}) exceeded"
            )

        # Build the conversation history
        messages: list[MessageParam] = [
            {"role": "user", "content": original_prompt},
            {"role": "assistant", "content": response.content},
        ]
        investigation_state.record_message()
        investigation_state.record_message()

        # Execute each tool call
        tool_results: list[ToolResultBlockParam] = []
        for block in response.content:
            if block.type == "tool_use":
                # Check if we can execute more tools in this round
                if not investigation_state.can_continue_round(self.config):
                    self.logger.warning(
                        f"Tool limit reached in round {investigation_state.tool_rounds_used}",
                        LogContext.TOOL_EXECUTION,
                    )
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Tool execution skipped due to limits. Max {self.config.MAX_TOOLS_PER_ROUND} tools per round, {self.config.MAX_TOTAL_TOOLS} total.",
                        }
                    )
                    continue
                self.logger.debug(
                    f"Processing tool call: {block.name}",
                    LogContext.TOOL_EXECUTION,
                    {"tool_name": block.name, "input": block.input},
                )

                try:
                    # Record tool usage
                    investigation_state.record_tool_use()

                    result = await self.tool_orchestrator.execute_tool(
                        block.name, block.input
                    )  # type: ignore
                    # Tool orchestrator already logs success/failure

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": self.tool_orchestrator.summarize_tool_result(
                                block.name, result
                            ),
                        }
                    )
                except Exception as e:
                    self.logger.error(
                        "Unexpected error in tool execution",
                        LogContext.TOOL_EXECUTION,
                        {
                            "tool_name": block.name,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        },
                    )
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Error executing tool: {str(e)}",
                        }
                    )

        # Add tool results to conversation
        messages.append({"role": "user", "content": tool_results})

        # Continue investigation using dynamic tool selection
        # Extract tool results from this round for analysis
        current_tool_results = {}
        tools_used_this_round = set()

        for block in response.content:
            if block.type == "tool_use":
                tools_used_this_round.add(block.name)
                # Find corresponding result
                for tool_result in tool_results:
                    if tool_result.get("tool_use_id") == block.id:
                        # Parse the result content to extract structured data
                        # Note: This is simplified - in a full implementation,
                        # we'd need to reverse-engineer the structured data from the summary
                        content_str = str(tool_result.get("content", ""))
                        current_tool_results[block.name] = {
                            "success": "Error" not in content_str,
                            "content": content_str,
                        }

        # Use dynamic selector to determine if we should continue
        should_continue, reasoning = (
            self.dynamic_tool_selector.should_continue_investigation(
                investigation_state, self.config
            )
        )

        self.logger.info(
            f"Dynamic tool selection: Continue={should_continue}, Reason={reasoning}",
            LogContext.TOOL_EXECUTION,
        )

        if should_continue:
            # Get recommended follow-up tools
            followup_tools = self.dynamic_tool_selector.select_followup_tools(
                current_tool_results, investigation_state, self.config, parsed_query
            )

            if followup_tools:
                continue_prompt = f"Based on the tool results above, please use these specific tools to continue the investigation: {', '.join(followup_tools)}. Focus on gathering additional data to complete the analysis."
            else:
                continue_prompt = "Based on the tool results above, please provide your analysis of the findings. No additional tools are needed."
        else:
            continue_prompt = f"Based on the tool results above, please provide your detailed analysis and recommendations. Investigation complete: {reasoning}"

        messages.append({"role": "user", "content": continue_prompt})

        # Get response - might be more tool calls or final analysis
        continue_response = await self.anthropic.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            tools=self.tools,
            messages=messages,
        )

        # If Anthropic wants to use more tools, handle them
        if any(isinstance(block, ToolUseBlock) for block in continue_response.content):
            self.logger.info("AI requested additional tools", LogContext.AI_RESPONSE)
            return await self._handle_additional_tools(
                continue_response, messages, investigation_state
            )

        # Return the final analysis
        if continue_response.content:
            for block in continue_response.content:
                if isinstance(block, TextBlock):
                    return block.text
        return "No final analysis generated"

    async def _handle_additional_tools(
        self,
        response: Message,
        messages: list[MessageParam],
        investigation_state: InvestigationState,
    ) -> str:
        """Handle additional tool calls in an iterative investigation."""

        # Check if we can continue with more rounds
        if not investigation_state.can_start_new_round(self.config):
            self.logger.warning(
                "Cannot start additional tool round - limit reached",
                LogContext.TOOL_EXECUTION,
            )
            return "Investigation stopped due to tool round limits. Analysis based on available data."

        # Start new round for additional tools
        investigation_state.start_new_round()
        self.logger.info(
            f"Starting additional tool round {investigation_state.tool_rounds_used}",
            LogContext.TOOL_EXECUTION,
        )

        # Execute the additional tool calls
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                # Check tool limits
                if not investigation_state.can_continue_round(self.config):
                    self.logger.warning(
                        f"Tool limit reached in additional round {investigation_state.tool_rounds_used}",
                        LogContext.TOOL_EXECUTION,
                    )
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": "Additional tool execution skipped due to limits.",
                        }
                    )
                    continue

                self.logger.debug(
                    f"Processing additional tool call: {block.name}",
                    LogContext.TOOL_EXECUTION,
                    {"tool_name": block.name, "input": block.input},
                )

                try:
                    # Record tool usage
                    investigation_state.record_tool_use()

                    result = await self.tool_orchestrator.execute_tool(
                        block.name, block.input
                    )
                    # Tool orchestrator already logs success/failure

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": self.tool_orchestrator.summarize_tool_result(
                                block.name, result
                            ),
                        }
                    )
                except Exception as e:
                    self.logger.error(
                        "Unexpected error in additional tool execution",
                        LogContext.TOOL_EXECUTION,
                        {
                            "tool_name": block.name,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        },
                    )
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Error executing tool: {str(e)}",
                        }
                    )

        # Add the assistant's response and tool results to conversation
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

        # Get response - might be more tool calls or final analysis
        continue_response = await self.anthropic.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            tools=self.tools,
            messages=messages,
        )

        # If Anthropic wants to use more tools, handle them recursively (with limits)
        if any(block.type == "tool_use" for block in continue_response.content):
            self.logger.info("AI requested even more tools", LogContext.AI_RESPONSE)
            return await self._handle_additional_tools(
                continue_response, messages, investigation_state
            )

        # Add explicit prompt for final analysis if no more tools needed
        analysis_prompt = "Based on all the data you've gathered from the tools above, please provide your detailed analysis and recommendations for this support issue. Include specific findings from the data and actionable next steps."
        messages.append({"role": "user", "content": analysis_prompt})

        # Get final analysis
        final_response = await self.anthropic.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=2000, messages=messages
        )

        if final_response.content:
            for block in final_response.content:
                if isinstance(block, TextBlock):
                    return block.text
        return "No final analysis generated after additional tools"


async def test_simple_investigator():
    """Test the simple investigator with a sample query."""
    # Test with debug mode enabled
    investigator = SimpleInvestigator(api_key=None, debug_mode=True, log_format="human")

    test_query = """
Dimas De la Fuente Hernández
  Today at 2:25 AM
Hello team!
We are checking an Igloohome device that does not seem to be connected to a bridge, so it only supports offline functionality. However, the device response says that it can program online access codes. Is that correct?
Workspace ID: e68eb8c9-f98c-4e23-a5d2-49bbb304d730
Device ID: 267ed8d4-3933-4e71-921a-53ce3736879a
    """

    result = await investigator.investigate(test_query)

    # Clean output showing results
    print("\n" + "=" * 60)
    print("🔍 INVESTIGATION RESULTS")
    print("=" * 60)
    print(f"Query: {result['original_query'][:100]}...")
    print("\n📋 Parsed Information:")
    for key, value in result["parsed_query"].items():
        if value:  # Only show non-empty values
            print(f"  {key}: {value}")

    print("\n📊 Investigation Analysis:")
    print(result["investigation"])

    # Export to markdown file
    md_filename = investigator.export_investigation_to_md(result)
    print(f"\n📄 Investigation exported to: {md_filename}")

    # Show debug info if available
    if "debug" in result:
        print("\n🔧 Debug Summary:")
        print(result["debug"]["log_summary"])


if __name__ == "__main__":
    asyncio.run(test_simple_investigator())
