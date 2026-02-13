"""Mock objects for Phoenix unit tests.

Provides mock span objects that simulate Phoenix API results
without requiring API access. These enable unit testing of internal
logic (detection, extraction, events, tree) in isolation.
"""

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MockPhoenixSpan:
    """Simulates Phoenix v1.Span TypedDict for unit testing.

    Mirrors the structure returned by phoenix.client.AsyncClient.spans.get_spans().
    """

    name: str = "test-span"
    trace_id: str = "trace-001"
    span_id: str = "span-001"
    parent_id: str | None = None
    span_kind: str = "LLM"
    start_time: str = "2025-01-01T00:00:00Z"
    end_time: str = "2025-01-01T00:00:01Z"
    status_code: str = "OK"
    status_message: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary matching Phoenix span format."""
        result: dict[str, Any] = {
            "name": self.name,
            "context": {
                "trace_id": self.trace_id,
                "span_id": self.span_id,
            },
            "span_kind": self.span_kind,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status_code": self.status_code,
            "status_message": self.status_message,
            "attributes": self.attributes,
        }
        if self.parent_id:
            result["parent_id"] = self.parent_id
        if self.events:
            result["events"] = self.events
        return result


# =============================================================================
# Factory Functions for Pre-configured Mocks
# =============================================================================


def create_openai_llm_span(
    span_id: str = "span-openai",
    trace_id: str = "trace-001",
    parent_id: str | None = None,
    model: str = "gpt-4o-mini",
    input_tokens: int = 50,
    output_tokens: int = 25,
    input_messages: list[dict[str, Any]] | None = None,
    output_content: str = "Hello! How can I help you?",
    start_time: str = "2025-01-01T00:00:00Z",
    end_time: str = "2025-01-01T00:00:01Z",
) -> dict[str, Any]:
    """Create a mock span with OpenAI-style attributes.

    Populates both raw input.value/output.value payloads AND
    OpenInference flattened attributes.

    Args:
        span_id: Unique span identifier
        trace_id: Parent trace identifier
        parent_id: Parent span ID (for nested spans)
        model: OpenAI model name
        input_tokens: Input token count
        output_tokens: Output token count
        input_messages: Input messages (OpenAI format)
        output_content: Response content text
        start_time: Start time ISO string
        end_time: End time ISO string

    Returns:
        Dictionary mimicking Phoenix span
    """
    if input_messages is None:
        input_messages = [{"role": "user", "content": "Hello!"}]

    # Build raw input/output payloads (OpenAI format)
    raw_input = json.dumps({"messages": input_messages, "model": model})
    raw_output = json.dumps(
        {
            "choices": [
                {
                    "message": {"role": "assistant", "content": output_content},
                    "finish_reason": "stop",
                }
            ],
            "model": model,
            "usage": {
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
            },
        }
    )

    # Build OpenInference flattened attributes
    attributes: dict[str, Any] = {
        "llm.system": "openai",
        "llm.model_name": model,
        "llm.token_count.prompt": input_tokens,
        "llm.token_count.completion": output_tokens,
        "input.value": raw_input,
        "output.value": raw_output,
    }

    # Add flattened input messages
    for i, msg in enumerate(input_messages):
        attributes[f"llm.input_messages.{i}.message.role"] = msg.get("role")
        attributes[f"llm.input_messages.{i}.message.content"] = msg.get("content", "")
        if msg.get("tool_call_id"):
            attributes[f"llm.input_messages.{i}.message.tool_call_id"] = msg[
                "tool_call_id"
            ]

    # Add flattened output message
    attributes["llm.output_messages.0.message.role"] = "assistant"
    attributes["llm.output_messages.0.message.content"] = output_content

    span = MockPhoenixSpan(
        span_id=span_id,
        trace_id=trace_id,
        parent_id=parent_id,
        name=f"chat {model}",
        span_kind="LLM",
        start_time=start_time,
        end_time=end_time,
        attributes=attributes,
    )

    return span.to_dict()


def create_anthropic_llm_span(
    span_id: str = "span-anthropic",
    trace_id: str = "trace-001",
    parent_id: str | None = None,
    model: str = "claude-3-5-haiku-latest",
    input_tokens: int = 50,
    output_tokens: int = 25,
    input_messages: list[dict[str, Any]] | None = None,
    system: str | None = None,
    output_content: str = "Hello! How can I help you?",
    start_time: str = "2025-01-01T00:00:00Z",
    end_time: str = "2025-01-01T00:00:01Z",
) -> dict[str, Any]:
    """Create a mock span with Anthropic-style attributes.

    Args:
        span_id: Unique span identifier
        trace_id: Parent trace identifier
        parent_id: Parent span ID
        model: Anthropic model name
        input_tokens: Input token count
        output_tokens: Output token count
        input_messages: Input messages (Anthropic format)
        system: System prompt
        output_content: Response content text
        start_time: Start time ISO string
        end_time: End time ISO string

    Returns:
        Dictionary mimicking Phoenix span
    """
    if input_messages is None:
        input_messages = [{"role": "user", "content": "Hello!"}]

    # Build raw input payload (Anthropic format)
    raw_input_data: dict[str, Any] = {"messages": input_messages, "model": model}
    if system:
        raw_input_data["system"] = system
    raw_input = json.dumps(raw_input_data)

    # Build raw output payload (Anthropic format)
    raw_output = json.dumps(
        {
            "content": [{"type": "text", "text": output_content}],
            "model": model,
            "role": "assistant",
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            },
        }
    )

    # Build OpenInference flattened attributes
    all_messages = []
    if system:
        all_messages.append({"role": "system", "content": system})
    all_messages.extend(input_messages)

    attributes: dict[str, Any] = {
        "llm.system": "anthropic",
        "llm.model_name": model,
        "llm.token_count.prompt": input_tokens,
        "llm.token_count.completion": output_tokens,
        "input.value": raw_input,
        "output.value": raw_output,
    }

    for i, msg in enumerate(all_messages):
        attributes[f"llm.input_messages.{i}.message.role"] = msg.get("role")
        attributes[f"llm.input_messages.{i}.message.content"] = msg.get("content", "")

    attributes["llm.output_messages.0.message.role"] = "assistant"
    attributes["llm.output_messages.0.message.content"] = output_content

    span = MockPhoenixSpan(
        span_id=span_id,
        trace_id=trace_id,
        parent_id=parent_id,
        name=f"chat {model}",
        span_kind="LLM",
        start_time=start_time,
        end_time=end_time,
        attributes=attributes,
    )

    return span.to_dict()


def create_tool_span(
    span_id: str = "span-tool",
    trace_id: str = "trace-001",
    parent_id: str | None = None,
    tool_name: str = "get_weather",
    arguments: dict[str, Any] | None = None,
    result: str = "Sunny, 72F",
    error: str | None = None,
    start_time: str = "2025-01-01T00:00:01Z",
    end_time: str = "2025-01-01T00:00:02Z",
) -> dict[str, Any]:
    """Create a mock span for tool execution.

    Args:
        span_id: Unique span identifier
        trace_id: Parent trace identifier
        parent_id: Parent span ID
        tool_name: Tool function name
        arguments: Tool input arguments
        result: Tool execution result
        error: Error message if tool failed
        start_time: Start time ISO string
        end_time: End time ISO string

    Returns:
        Dictionary mimicking Phoenix span
    """
    if arguments is None:
        arguments = {"city": "San Francisco"}

    attributes: dict[str, Any] = {
        "tool.name": tool_name,
        "tool.call.id": f"call_{span_id}",
        "input.value": json.dumps(arguments),
        "output.value": result if not error else "",
    }

    span = MockPhoenixSpan(
        span_id=span_id,
        trace_id=trace_id,
        parent_id=parent_id,
        name=f"tool: {tool_name}",
        span_kind="TOOL",
        start_time=start_time,
        end_time=end_time,
        status_code="ERROR" if error else "OK",
        status_message=error or "",
        attributes=attributes,
    )

    return span.to_dict()


def create_chain_span(
    span_id: str = "span-chain",
    trace_id: str = "trace-001",
    parent_id: str | None = None,
    name: str = "agent-run",
    start_time: str = "2025-01-01T00:00:00Z",
    end_time: str = "2025-01-01T00:00:05Z",
) -> dict[str, Any]:
    """Create a mock span for chain/agent orchestration.

    Args:
        span_id: Unique span identifier
        trace_id: Parent trace identifier
        parent_id: Parent span ID
        name: Span name
        start_time: Start time ISO string
        end_time: End time ISO string

    Returns:
        Dictionary mimicking Phoenix span
    """
    span = MockPhoenixSpan(
        span_id=span_id,
        trace_id=trace_id,
        parent_id=parent_id,
        name=name,
        span_kind="CHAIN",
        start_time=start_time,
        end_time=end_time,
        attributes={},
    )

    return span.to_dict()


def create_multiturn_openai_spans(
    trace_id: str = "trace-multiturn",
    model: str = "gpt-4o-mini",
) -> list[dict[str, Any]]:
    """Create spans representing a multi-turn OpenAI conversation.

    Args:
        trace_id: Trace identifier
        model: Model name

    Returns:
        List of span dictionaries for a 3-turn conversation
    """
    # First turn
    span1 = create_openai_llm_span(
        span_id="span-turn-1",
        trace_id=trace_id,
        model=model,
        input_messages=[
            {"role": "system", "content": "You are a helpful math tutor."},
            {"role": "user", "content": "What is 2 + 2?"},
        ],
        output_content="2 + 2 equals 4.",
        input_tokens=30,
        output_tokens=10,
        start_time="2025-01-01T00:00:00Z",
        end_time="2025-01-01T00:00:01Z",
    )

    # Second turn
    span2 = create_openai_llm_span(
        span_id="span-turn-2",
        trace_id=trace_id,
        model=model,
        input_messages=[
            {"role": "system", "content": "You are a helpful math tutor."},
            {"role": "user", "content": "What is 2 + 2?"},
            {"role": "assistant", "content": "2 + 2 equals 4."},
            {"role": "user", "content": "What about 3 + 3?"},
        ],
        output_content="3 + 3 equals 6.",
        input_tokens=50,
        output_tokens=10,
        start_time="2025-01-01T00:00:01Z",
        end_time="2025-01-01T00:00:02Z",
    )

    # Third turn
    span3 = create_openai_llm_span(
        span_id="span-turn-3",
        trace_id=trace_id,
        model=model,
        input_messages=[
            {"role": "system", "content": "You are a helpful math tutor."},
            {"role": "user", "content": "What is 2 + 2?"},
            {"role": "assistant", "content": "2 + 2 equals 4."},
            {"role": "user", "content": "What about 3 + 3?"},
            {"role": "assistant", "content": "3 + 3 equals 6."},
            {"role": "user", "content": "And 5 + 5?"},
        ],
        output_content="5 + 5 equals 10.",
        input_tokens=70,
        output_tokens=10,
        start_time="2025-01-01T00:00:02Z",
        end_time="2025-01-01T00:00:03Z",
    )

    return [span1, span2, span3]


def create_tool_call_trace(
    trace_id: str = "trace-tools",
    model: str = "gpt-4o-mini",
) -> list[dict[str, Any]]:
    """Create a complete trace with tool calls.

    Args:
        trace_id: Trace identifier
        model: Model name

    Returns:
        List of span dictionaries representing a trace with tool use
    """
    # Chain span (root)
    chain_span = create_chain_span(
        span_id="span-chain-root",
        trace_id=trace_id,
        name="agent-run",
        start_time="2025-01-01T00:00:00Z",
        end_time="2025-01-01T00:00:05Z",
    )

    # First LLM call - requests tool use
    tool_call_output = json.dumps(
        {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "",
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
            "model": model,
        }
    )

    llm_span1 = create_openai_llm_span(
        span_id="span-llm-1",
        trace_id=trace_id,
        parent_id="span-chain-root",
        model=model,
        input_messages=[
            {"role": "user", "content": "What's the weather in San Francisco?"},
        ],
        output_content="",
        start_time="2025-01-01T00:00:00.100Z",
        end_time="2025-01-01T00:00:01Z",
    )
    # Override output to include tool calls
    llm_span1["attributes"]["output.value"] = tool_call_output
    llm_span1["attributes"]["llm.output_messages.0.message.content"] = ""
    llm_span1["attributes"][
        "llm.output_messages.0.message.tool_calls.0.tool_call.function.name"
    ] = "get_weather"
    llm_span1["attributes"][
        "llm.output_messages.0.message.tool_calls.0.tool_call.function.arguments"
    ] = '{"city": "San Francisco"}'
    llm_span1["attributes"][
        "llm.output_messages.0.message.tool_calls.0.tool_call.id"
    ] = "call_abc123"

    # Tool execution
    tool_span = create_tool_span(
        span_id="span-tool-exec",
        trace_id=trace_id,
        parent_id="span-chain-root",
        tool_name="get_weather",
        arguments={"city": "San Francisco"},
        result="Sunny, 72F",
        start_time="2025-01-01T00:00:01Z",
        end_time="2025-01-01T00:00:02Z",
    )

    # Second LLM call - after tool response
    llm_span2 = create_openai_llm_span(
        span_id="span-llm-2",
        trace_id=trace_id,
        parent_id="span-chain-root",
        model=model,
        input_messages=[
            {"role": "user", "content": "What's the weather in San Francisco?"},
            {"role": "assistant", "content": ""},
            {"role": "tool", "content": "Sunny, 72F", "tool_call_id": "call_abc123"},
        ],
        output_content="The weather in San Francisco is sunny with a temperature of 72F.",
        start_time="2025-01-01T00:00:02Z",
        end_time="2025-01-01T00:00:03Z",
    )

    return [chain_span, llm_span1, tool_span, llm_span2]
