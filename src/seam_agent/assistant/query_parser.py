"""
LLM-based query parser for customer support queries.

Extracts structured information from natural language support queries
using an LLM with structured output.
"""

import json
import os
from typing import List, Optional
from pydantic import BaseModel, Field
from openai import AsyncOpenAI


class ParsedQuery(BaseModel):
    """Structured output from LLM query parsing"""

    # Identifiers
    device_ids: List[str] = Field(
        default_factory=list, description="Device UUIDs found in the query"
    )
    access_codes: List[str] = Field(
        default_factory=list, description="Access codes mentioned"
    )
    workspace_ids: List[str] = Field(
        default_factory=list, description="Workspace UUIDs (customer's main account)"
    )
    connected_account_ids: List[str] = Field(
        default_factory=list,
        description="Connected Account UUIDs (provider accounts like Nuki, August)",
    )
    action_attempt_ids: List[str] = Field(
        default_factory=list, description="Action attempt UUIDs"
    )

    # Context
    time_references: List[str] = Field(
        default_factory=list, description="Time expressions mentioned"
    )
    question_type: str = Field(
        description="Type of support question: device_behavior, troubleshooting, api_help, account_issue"
    )
    device_types: List[str] = Field(
        default_factory=list,
        description="Device brands/types mentioned (Nuki, August, Yale, etc.)",
    )
    operations: List[str] = Field(
        default_factory=list,
        description="Operations mentioned (unlock, lock, create_access_code, etc.)",
    )

    # Analysis
    confidence: float = Field(
        description="Confidence score 0-1 for the parsing accuracy"
    )
    summary: str = Field(description="Brief summary of what the user is asking")


class SupportQueryParser:
    """Parses customer support queries using LLM structured output"""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with OpenAI API key"""
        self.client = AsyncOpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))

    async def parse(self, query: str) -> ParsedQuery:
        """
        Parse a customer support query into structured data.

        Args:
            query: Natural language support query

        Returns:
            ParsedQuery with extracted structured information
        """
        system_prompt = """
You are a customer support query parser for Seam, a smart lock API company.
Extract structured information from customer support queries.

IMPORTANT: You must respond with valid JSON that matches this exact schema:
{
  "device_ids": ["list of UUIDs that look like device identifiers"],
  "access_codes": ["list of access codes mentioned"],
  "workspace_ids": ["list of UUIDs that are the customer's main workspace/account"],
  "connected_account_ids": ["list of UUIDs that are provider accounts (Nuki, August, etc.)"],
  "action_attempt_ids": ["list of UUIDs that look like action attempt identifiers"],
  "time_references": ["list of time expressions like '12:02 pm', 'yesterday', 'this morning'"],
  "question_type": "one of: device_behavior, troubleshooting, api_help, account_issue",
  "device_types": ["list of device brands like Nuki, August, Yale, Schlage, etc."],
  "operations": ["list of operations like unlock, lock, create_access_code, delete_access_code, etc."],
  "confidence": 0.95,
  "summary": "Brief summary of what the user is asking"
}

Guidelines:
- UUIDs are typically 36 characters with dashes (8-4-4-4-12 format)
- ID Types in Seam:
  * Device ID: The actual smart lock/device UUID
  * Workspace ID: Customer's main account (rarely mentioned explicitly)
  * Connected Account ID: Provider account (look for "Connected Account:", "Nuki Account:", "August Account:")
  * Action Attempt ID: Specific operation attempts
- Device types include: Nuki, August, Yale, Schlage, Kwikset, SmartThings, etc.
- Operations include: unlock, lock, create_access_code, delete_access_code, sync, connect, etc.
- Question types:
  - device_behavior: How does X work? What should happen?
  - troubleshooting: Something is broken/not working
  - api_help: How to use API endpoints, code examples
  - account_issue: Workspace problems, billing, access issues
- Time references: Keep original format, don't convert
- Confidence: 0.9+ if very clear, 0.7-0.9 if somewhat ambiguous, <0.7 if unclear
"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",  # Using mini for cost efficiency
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Parse this support query:\n\n{query}",
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0.1,  # Low temperature for consistent parsing
            )

            # Parse the JSON response
            parsed_data = json.loads(response.choices[0].message.content)
            return ParsedQuery(**parsed_data)

        except Exception as e:
            # Fallback with minimal parsing if LLM fails
            return ParsedQuery(
                question_type="troubleshooting",
                confidence=0.1,
                summary=f"Failed to parse query: {str(e)}",
            )


# Example usage and testing
async def test_parser():
    """Test the parser with the Nuki example"""
    parser = SupportQueryParser()

    test_query = """
    Hello team,
    Will Nuki devices auto-lock after a few minutes of being unlocked? if so, could you confirm what's the delay, please?
    for reference: 1409 Gate/Puerta Calle
    ID: 49aa8687-041e-471e-9188-8b0b13d930b3
    Connected Account: 45a2cfbc-f8cd-412d-b9b1-2595835ca854
    Unlocked at 12:02 pm
    remained unlocked until 12:14 pm.
    """

    result = await parser.parse(test_query)
    print("Parsed Query:")
    print(f"  Device IDs: {result.device_ids}")
    print(f"  Workspace IDs: {result.workspace_ids}")
    print(f"  Connected Account IDs: {result.connected_account_ids}")
    print(f"  Time References: {result.time_references}")
    print(f"  Question Type: {result.question_type}")
    print(f"  Device Types: {result.device_types}")
    print(f"  Operations: {result.operations}")
    print(f"  Confidence: {result.confidence}")
    print(f"  Summary: {result.summary}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_parser())
