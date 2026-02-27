"""Mock objects for W&B Weave tests.

Provides realistic mock objects for unit testing without API access.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4


@dataclass
class MockWeaveCall:
    """Mock Weave call object for testing."""

    id: str = field(default_factory=lambda: str(uuid4()))
    trace_id: str | None = None
    parent_id: str | None = None
    op_name: str = "test_op"
    display_name: str | None = None
    inputs: dict[str, Any] = field(default_factory=dict)
    output: Any = None
    started_at: datetime = field(default_factory=datetime.now)
    ended_at: datetime | None = None
    exception: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.trace_id is None and self.parent_id is None:
            # Root call - trace_id is the call's own id
            self.trace_id = self.id
        if self.ended_at is None:
            self.ended_at = self.started_at + timedelta(seconds=1)


def create_openai_llm_call(
    call_id: str | None = None,
    trace_id: str | None = None,
    parent_id: str | None = None,
) -> MockWeaveCall:
    """Create a mock OpenAI LLM call.

    Args:
        call_id: Call ID (generated if not provided)
        trace_id: Trace ID (uses call_id if root call)
        parent_id: Parent call ID

    Returns:
        MockWeaveCall configured as OpenAI LLM call
    """
    call_id = call_id or str(uuid4())
    return MockWeaveCall(
        id=call_id,
        trace_id=trace_id or (call_id if not parent_id else None),
        parent_id=parent_id,
        op_name="openai.chat.completions.create",
        display_name="ChatCompletion",
        inputs={
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello!"},
            ],
        },
        output={
            "id": "chatcmpl-123",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Hello! How can I help?",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 20,
                "completion_tokens": 10,
                "total_tokens": 30,
            },
        },
        attributes={"model": "gpt-4o-mini", "provider": "openai"},
        summary={
            "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30}
        },
    )


def create_anthropic_llm_call(
    call_id: str | None = None,
    trace_id: str | None = None,
    parent_id: str | None = None,
) -> MockWeaveCall:
    """Create a mock Anthropic LLM call.

    Args:
        call_id: Call ID (generated if not provided)
        trace_id: Trace ID (uses call_id if root call)
        parent_id: Parent call ID

    Returns:
        MockWeaveCall configured as Anthropic LLM call
    """
    call_id = call_id or str(uuid4())
    return MockWeaveCall(
        id=call_id,
        trace_id=trace_id or (call_id if not parent_id else None),
        parent_id=parent_id,
        op_name="anthropic.messages.create",
        display_name="Messages",
        inputs={
            "model": "claude-3-haiku-20240307",
            "system": "You are a helpful assistant.",
            "messages": [{"role": "user", "content": "Hello!"}],
            "max_tokens": 1024,
        },
        output={
            "id": "msg_123",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Hello! How can I help you today?"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 15, "output_tokens": 12},
        },
        attributes={"model": "claude-3-haiku-20240307", "provider": "anthropic"},
        summary={
            "usage": {"input_tokens": 15, "output_tokens": 12, "total_tokens": 27}
        },
    )


def create_openai_llm_call_with_tools(
    call_id: str | None = None,
    trace_id: str | None = None,
    parent_id: str | None = None,
) -> MockWeaveCall:
    """Create a mock OpenAI LLM call with tool calls.

    Args:
        call_id: Call ID (generated if not provided)
        trace_id: Trace ID (uses call_id if root call)
        parent_id: Parent call ID

    Returns:
        MockWeaveCall configured as OpenAI LLM call with tools
    """
    call_id = call_id or str(uuid4())
    return MockWeaveCall(
        id=call_id,
        trace_id=trace_id or (call_id if not parent_id else None),
        parent_id=parent_id,
        op_name="openai.chat.completions.create",
        display_name="ChatCompletion",
        inputs={
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What's the weather in San Francisco?"},
            ],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get weather for a city",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "city": {"type": "string", "description": "City name"}
                            },
                            "required": ["city"],
                        },
                    },
                }
            ],
        },
        output={
            "id": "chatcmpl-456",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_abc123",
                                "type": "function",
                                "function": {
                                    "name": "get_weather",
                                    "arguments": '{"city": "San Francisco"}',
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70},
        },
        attributes={"model": "gpt-4o-mini", "provider": "openai"},
    )


def create_tool_call(
    call_id: str | None = None,
    trace_id: str | None = None,
    parent_id: str | None = None,
    tool_name: str = "get_weather",
) -> MockWeaveCall:
    """Create a mock tool call.

    Args:
        call_id: Call ID (generated if not provided)
        trace_id: Trace ID
        parent_id: Parent call ID
        tool_name: Name of the tool

    Returns:
        MockWeaveCall configured as tool call
    """
    call_id = call_id or str(uuid4())
    return MockWeaveCall(
        id=call_id,
        trace_id=trace_id,
        parent_id=parent_id,
        op_name=f"tool.{tool_name}",
        display_name=tool_name,
        inputs={"city": "San Francisco"},
        output={"result": "Foggy, 58F"},
        attributes={"tool_name": tool_name},
    )


def create_span_call(
    call_id: str | None = None,
    trace_id: str | None = None,
    parent_id: str | None = None,
    name: str = "agent_run",
) -> MockWeaveCall:
    """Create a mock span/chain call.

    Args:
        call_id: Call ID (generated if not provided)
        trace_id: Trace ID (uses call_id if root call)
        parent_id: Parent call ID
        name: Span name

    Returns:
        MockWeaveCall configured as span call
    """
    call_id = call_id or str(uuid4())
    return MockWeaveCall(
        id=call_id,
        trace_id=trace_id or (call_id if not parent_id else None),
        parent_id=parent_id,
        op_name=name,
        display_name=name,
        inputs={"query": "What's the weather?"},
        output={"response": "It's foggy in San Francisco."},
        attributes={"span_type": "agent"},
    )


def create_trace_with_tool_calls() -> list[MockWeaveCall]:
    """Create a complete trace with tool calls.

    Returns:
        List of MockWeaveCall objects representing a trace with:
        - Root span (agent_run)
        - First LLM call (requests tool)
        - Tool call execution
        - Second LLM call (final response)
    """
    root_id = str(uuid4())
    llm1_id = str(uuid4())
    tool_id = str(uuid4())
    llm2_id = str(uuid4())

    base_time = datetime.now()

    root = create_span_call(call_id=root_id, name="agent_run")
    root.started_at = base_time
    root.ended_at = base_time + timedelta(seconds=5)

    llm1 = create_openai_llm_call_with_tools(
        call_id=llm1_id, trace_id=root_id, parent_id=root_id
    )
    llm1.started_at = base_time + timedelta(milliseconds=100)
    llm1.ended_at = base_time + timedelta(seconds=1)

    tool = create_tool_call(call_id=tool_id, trace_id=root_id, parent_id=root_id)
    tool.started_at = base_time + timedelta(seconds=1, milliseconds=100)
    tool.ended_at = base_time + timedelta(seconds=2)

    llm2 = create_openai_llm_call(call_id=llm2_id, trace_id=root_id, parent_id=root_id)
    llm2.started_at = base_time + timedelta(seconds=2, milliseconds=100)
    llm2.ended_at = base_time + timedelta(seconds=3)
    llm2.inputs = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What's the weather in San Francisco?"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_abc123",
                        "type": "function",
                        "function": {
                            "name": "get_weather",
                            "arguments": '{"city": "San Francisco"}',
                        },
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "call_abc123", "content": "Foggy, 58F"},
        ],
    }
    llm2.output = {
        "id": "chatcmpl-789",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "The weather in San Francisco is foggy and 58F.",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 15, "total_tokens": 115},
    }

    return [root, llm1, tool, llm2]


def create_multiturn_trace() -> list[MockWeaveCall]:
    """Create a multi-turn conversation trace.

    Returns:
        List of MockWeaveCall objects representing a 3-turn conversation
    """
    root_id = str(uuid4())
    base_time = datetime.now()

    calls = []

    # Root span
    root = create_span_call(call_id=root_id, name="conversation")
    root.started_at = base_time
    root.ended_at = base_time + timedelta(seconds=10)
    calls.append(root)

    # Turn 1
    llm1 = create_openai_llm_call(
        call_id=str(uuid4()), trace_id=root_id, parent_id=root_id
    )
    llm1.started_at = base_time + timedelta(milliseconds=100)
    llm1.ended_at = base_time + timedelta(seconds=1)
    llm1.inputs = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
        ],
    }
    llm1.output = {
        "id": "chatcmpl-1",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hi! How can I help?"},
                "finish_reason": "stop",
            }
        ],
    }
    calls.append(llm1)

    # Turn 2
    llm2 = create_openai_llm_call(
        call_id=str(uuid4()), trace_id=root_id, parent_id=root_id
    )
    llm2.started_at = base_time + timedelta(seconds=2)
    llm2.ended_at = base_time + timedelta(seconds=3)
    llm2.inputs = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi! How can I help?"},
            {"role": "user", "content": "Tell me a joke."},
        ],
    }
    llm2.output = {
        "id": "chatcmpl-2",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Why did the programmer quit? Because he didn't get arrays!",
                },
                "finish_reason": "stop",
            }
        ],
    }
    calls.append(llm2)

    # Turn 3
    llm3 = create_openai_llm_call(
        call_id=str(uuid4()), trace_id=root_id, parent_id=root_id
    )
    llm3.started_at = base_time + timedelta(seconds=4)
    llm3.ended_at = base_time + timedelta(seconds=5)
    llm3.inputs = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi! How can I help?"},
            {"role": "user", "content": "Tell me a joke."},
            {
                "role": "assistant",
                "content": "Why did the programmer quit? Because he didn't get arrays!",
            },
            {"role": "user", "content": "That's funny!"},
        ],
    }
    llm3.output = {
        "id": "chatcmpl-3",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "I'm glad you enjoyed it! Would you like to hear another?",
                },
                "finish_reason": "stop",
            }
        ],
    }
    calls.append(llm3)

    return calls
