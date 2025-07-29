"""
Unified AI model client for different providers.

Provides a consistent interface for OpenAI and Anthropic models.
"""

import json
from typing import Any, Optional, List
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic


class Function(BaseModel):
    """Function call information"""

    name: str
    arguments: str


class ToolCall(BaseModel):
    """Tool call information"""

    id: str
    function: Function
    type: str = "function"


class Message(BaseModel):
    """Message with content and optional tool calls"""

    content: str
    tool_calls: Optional[List[ToolCall]] = None


class Choice(BaseModel):
    """Choice containing a message"""

    message: Message


class UnifiedResponse(BaseModel):
    """Unified response object that works with both OpenAI and Anthropic"""

    provider: str
    raw_response: Any = Field(
        exclude=True
    )  # Store raw response but exclude from serialization
    _choices: Optional[List[Choice]] = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, provider: str, response: Any, **data):
        super().__init__(provider=provider, raw_response=response, **data)

    @property
    def choices(self) -> List[Choice]:
        """Unified choices interface"""
        if self._choices is None:
            if self.provider == "openai":
                # Convert OpenAI response to our Pydantic models
                choices = []
                for choice in self.raw_response.choices:
                    tool_calls = []
                    if (
                        hasattr(choice.message, "tool_calls")
                        and choice.message.tool_calls
                    ):
                        for tc in choice.message.tool_calls:
                            tool_calls.append(
                                ToolCall(
                                    id=tc.id,
                                    function=Function(
                                        name=tc.function.name,
                                        arguments=tc.function.arguments,
                                    ),
                                )
                            )

                    message = Message(
                        content=choice.message.content or "",
                        tool_calls=tool_calls if tool_calls else None,
                    )
                    choices.append(Choice(message=message))

                self._choices = choices

            elif self.provider == "anthropic":
                # Extract content and tool calls from Anthropic response
                content = ""
                tool_calls = []

                if hasattr(self.raw_response, "content"):
                    for content_block in self.raw_response.content:
                        if hasattr(content_block, "text"):
                            content += content_block.text
                        elif hasattr(content_block, "name"):  # Tool use
                            # Convert Anthropic tool use to our format
                            tool_calls.append(
                                ToolCall(
                                    id=getattr(
                                        content_block, "id", f"call_{len(tool_calls)}"
                                    ),
                                    function=Function(
                                        name=content_block.name,
                                        arguments=json.dumps(
                                            getattr(content_block, "input", {})
                                        ),
                                    ),
                                )
                            )

                message = Message(
                    content=content, tool_calls=tool_calls if tool_calls else None
                )
                self._choices = [Choice(message=message)]

        return self._choices or []


class ModelClient:
    """Unified interface for different AI model providers"""

    def __init__(self, provider: str, api_key: Optional[str] = None):
        self.provider = provider
        if provider == "openai":
            self.client = AsyncOpenAI(api_key=api_key)
        elif provider == "anthropic":
            try:
                self.client = AsyncAnthropic(api_key=api_key)
            except ImportError:
                raise ImportError(
                    "anthropic package not installed. Run: pip install anthropic"
                )
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    async def chat_completion(
        self, messages, tools=None, model=None, **kwargs
    ) -> UnifiedResponse:
        """Unified chat completion interface"""
        if self.provider == "openai":
            # Filter out None tools for OpenAI
            openai_kwargs = kwargs.copy()
            if tools is not None:
                openai_kwargs["tools"] = tools

            response = await self.client.chat.completions.create(
                model=model or "gpt-4o-mini", messages=messages, **openai_kwargs
            )
            return UnifiedResponse("openai", response)

        elif self.provider == "anthropic":
            # Convert OpenAI format to Anthropic format
            anthropic_messages = self._convert_messages_to_anthropic(messages)
            anthropic_kwargs = {
                k: v for k, v in kwargs.items() if k not in ["tool_choice"]
            }

            # Handle tools properly for Anthropic
            anthropic_tools = self._convert_tools_to_anthropic(tools) if tools else None
            create_kwargs = {
                "model": model or "claude-3-5-sonnet-20241022",
                "messages": anthropic_messages,
                "max_tokens": 4096,
                **anthropic_kwargs,
            }
            if anthropic_tools is not None:
                create_kwargs["tools"] = anthropic_tools

            response = await self.client.messages.create(**create_kwargs)
            return UnifiedResponse("anthropic", response)

        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _convert_messages_to_anthropic(self, messages):
        """Convert OpenAI message format to Anthropic format"""
        anthropic_messages = []
        system_content = None

        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            elif msg["role"] in ["user", "assistant"]:
                anthropic_messages.append(
                    {"role": msg["role"], "content": msg["content"]}
                )
            elif msg["role"] == "tool":
                # Handle tool responses for Anthropic
                anthropic_messages.append(
                    {"role": "user", "content": f"Tool result: {msg['content']}"}
                )

        # Add system message as first user message if present
        if system_content and anthropic_messages:
            anthropic_messages[0]["content"] = (
                f"System: {system_content}\n\nUser: {anthropic_messages[0]['content']}"
            )

        return anthropic_messages

    def _convert_tools_to_anthropic(self, tools):
        """Convert OpenAI tool format to Anthropic format"""
        if not tools:
            return None

        anthropic_tools = []
        for tool in tools:
            if tool["type"] == "function":
                anthropic_tools.append(
                    {
                        "name": tool["function"]["name"],
                        "description": tool["function"]["description"],
                        "input_schema": tool["function"]["parameters"],
                    }
                )

        return anthropic_tools
