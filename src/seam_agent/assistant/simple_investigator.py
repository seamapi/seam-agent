"""
Simple customer support investigator using Anthropic and query parsing.

Starts with just query parsing and will incrementally add tool calling.
"""

import asyncio
import os
from typing import Any
from anthropic import AsyncAnthropic
from anthropic.types import (
    ToolParam,
    TextBlock,
    MessageParam,
    Message,
    ToolResultBlockParam,
)

from seam_agent.assistant.query_parser import SupportQueryParser, ParsedQuery
from seam_agent.connectors.db import DatabaseClient
from seam_agent.connectors.seam_api import SeamAPIClient
from seam_agent.assistant.tool_registry import ToolRegistry
from seam_agent.assistant.prompt_manager import PromptManager
from seam_agent.assistant.investigation_strategy import InvestigationStrategy
from seam_agent.assistant.tool_orchestrator import ToolOrchestrator


class SimpleInvestigator:
    anthropic: AsyncAnthropic
    db_client: DatabaseClient
    seam_client: SeamAPIClient
    query_parser: SupportQueryParser
    tool_registry: ToolRegistry
    prompt_manager: PromptManager
    investigation_strategy: InvestigationStrategy
    tool_orchestrator: ToolOrchestrator
    tools: list[ToolParam]

    def __init__(self, api_key: str | None = None):
        self.anthropic = AsyncAnthropic(
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY")
        )
        self.db_client = DatabaseClient()
        self.seam_client = SeamAPIClient()
        self.query_parser = SupportQueryParser()

        # Initialize components
        self.tool_registry = ToolRegistry()
        self.prompt_manager = PromptManager()
        self.investigation_strategy = InvestigationStrategy(
            self.tool_registry, self.prompt_manager
        )
        self.tool_orchestrator = ToolOrchestrator(self.db_client, self.seam_client)

        # Get tool definitions from orchestrator
        self.tools = self.tool_orchestrator.get_tool_definitions()

    async def investigate(self, customer_query: str) -> dict[str, Any]:
        """
        Investigate a customer support query.

        Args:
            customer_query: Natural language customer support query

        Returns:
            Dict with parsed query info and initial analysis
        """
        # Step 1: Parse the query to extract structured information
        parsed_query = await self.query_parser.parse(customer_query)

        # Step 2: Use Anthropic with tools to investigate
        investigation_result = await self._investigate_with_tools(
            customer_query, parsed_query
        )

        return {
            "original_query": customer_query,
            "parsed_query": parsed_query.__dict__,
            "investigation": investigation_result,
        }

    async def _investigate_with_tools(
        self, original_query: str, parsed_query: ParsedQuery
    ) -> str:
        """Use Anthropic with tools to investigate the customer query."""

        prompt = self.prompt_manager.get_initial_investigation_prompt(
            original_query, parsed_query
        )

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
                response, original_query, prompt, parsed_query
            )

        # If no tools called, return the direct response
        if response.content:
            for block in response.content:
                if isinstance(block, TextBlock):
                    return block.text
        return "No response generated"

    async def _handle_tool_calls(
        self, response: Message, original_query: str, original_prompt: str, parsed_query
    ) -> str:
        """Execute tool calls and get final analysis from Anthropic."""

        # Build the conversation history
        messages: list[MessageParam] = [
            {"role": "user", "content": original_prompt},
            {"role": "assistant", "content": response.content},
        ]

        # Execute each tool call
        tool_results: list[ToolResultBlockParam] = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"Executing tool: {block.name} with input: {block.input}")

                try:
                    result = await self.tool_orchestrator.execute_tool(
                        block.name, block.input
                    )  # type: ignore
                    print(f"Tool '{block.name}' executed successfully")
                    print(f"Result type: {type(result)}")
                    print(
                        f"Result preview: {str(result)[:200]}..."
                        if len(str(result)) > 200
                        else f"Result: {result}"
                    )

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
                    print(f"Tool '{block.name}' failed with error: {str(e)}")
                    print(f"Error type: {type(e)}")
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Error executing tool: {str(e)}",
                        }
                    )

        # Add tool results to conversation
        messages.append({"role": "user", "content": tool_results})

        # Continue investigation - ask Anthropic if it wants to use more tools
        # Track which tools have been used by examining tool_use blocks in the conversation
        tools_used: set[str] = set()
        for msg in messages:
            if msg.get("role") == "assistant":
                # Check if this message contains tool use blocks
                content = msg.get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if (
                            hasattr(block, "type")
                            and getattr(block, "type") == "tool_use"
                        ):
                            tools_used.add(getattr(block, "name"))

        # Use investigation strategy to determine next steps
        should_continue, continue_prompt = (
            self.investigation_strategy.should_continue_investigation(
                parsed_query, original_query, tools_used
            )
        )

        messages.append({"role": "user", "content": continue_prompt})

        # Get response - might be more tool calls or final analysis
        continue_response = await self.anthropic.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            tools=self.tools,
            messages=messages,
        )

        # If Anthropic wants to use more tools, handle them
        if any(block.type == "tool_use" for block in continue_response.content):
            print("Anthropic is calling additional tools...")
            return await self._handle_additional_tools(continue_response, messages)

        # Otherwise, return the final analysis
        if continue_response.content:
            for block in continue_response.content:
                if isinstance(block, TextBlock):
                    return block.text
        return "No final analysis generated"

    async def _handle_additional_tools(self, response, messages) -> str:
        """Handle additional tool calls in an iterative investigation."""

        # Execute the additional tool calls
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(
                    f"Executing additional tool: {block.name} with input: {block.input}"
                )

                try:
                    result = await self.tool_orchestrator.execute_tool(
                        block.name, block.input
                    )
                    print(f"Additional tool '{block.name}' executed successfully")
                    print(f"Result type: {type(result)}")
                    print(
                        f"Result preview: {str(result)[:200]}..."
                        if len(str(result)) > 200
                        else f"Result: {result}"
                    )

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
                    print(f"Additional tool '{block.name}' failed with error: {str(e)}")
                    print(f"Error type: {type(e)}")
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

        # If Anthropic wants to use more tools, handle them recursively
        if any(block.type == "tool_use" for block in continue_response.content):
            print("Anthropic is calling even more tools...")
            return await self._handle_additional_tools(continue_response, messages)

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
    investigator = SimpleInvestigator(api_key=None)

    test_query = """
   Jake
  Jul 21st at 4:27 AM
Hi team,
Can you help me check if this unmanaged code on this users lock is something that we created but only marked by the system as unmanaged?
Lock name: Cabin Basement
Lock ID: 14923119-8686-4010-870f-0621cdef220a
Code name: Brian Kem5f2
Code: 7995
Access Code: aeae87ee-5f52-498f-8208-e2daf28bcfa0
Looking at the timing of when this unmanaged code was created, it lines up with when we first attempted to create the code but got rejected.
Perhaps it was actually created/added on the lock but then somehow got marked as unmanaged? (edited)
    """

    result = await investigator.investigate(test_query)

    print("=== Simple Investigator Results ===")
    print(f"Original Query: {result['original_query'][:100]}...")
    print("\nParsed Information:")
    for key, value in result["parsed_query"].items():
        if value:  # Only show non-empty values
            print(f"  {key}: {value}")

    print("\nInvestigation:")
    print(result["investigation"])


if __name__ == "__main__":
    asyncio.run(test_simple_investigator())
