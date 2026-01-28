"""Mock objects for Logfire unit tests.

Provides mock span objects that simulate Logfire query results
without requiring API access. These enable unit testing of internal
logic (detection, extraction, events, tree) in isolation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class MockSpan:
    """Simulates Logfire span from query results for unit testing.

    Mirrors the structure of rows returned by Logfire SQL queries
    with the columns used by the logfire source implementation.
    """

    trace_id: str = "trace-001"
    span_id: str = "span-001"
    parent_span_id: str | None = None
    span_name: str = "test-span"
    message: str = "Test span message"
    start_timestamp: datetime = field(default_factory=datetime.now)
    end_timestamp: datetime | None = None
    duration: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    is_exception: bool = False
    exception_type: str | None = None
    exception_message: str | None = None
    otel_scope_name: str = "logfire"
    otel_events: list[dict[str, Any]] | None = None
    level: str = "info"
    tags: list[str] | None = None
    service_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary matching Logfire query result format."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "span_name": self.span_name,
            "message": self.message,
            "start_timestamp": self.start_timestamp,
            "end_timestamp": self.end_timestamp,
            "duration": self.duration,
            "attributes": self.attributes,
            "is_exception": self.is_exception,
            "exception_type": self.exception_type,
            "exception_message": self.exception_message,
            "otel_scope_name": self.otel_scope_name,
            "otel_events": self.otel_events,
            "level": self.level,
            "tags": self.tags,
            "service_name": self.service_name,
        }


# =============================================================================
# Factory Functions for Pre-configured Mocks
# =============================================================================


def create_openai_llm_span(
    span_id: str = "span-openai",
    trace_id: str = "trace-001",
    parent_span_id: str | None = None,
    model: str = "gpt-4o-mini",
    input_tokens: int = 50,
    output_tokens: int = 25,
    input_messages: list[dict[str, Any]] | None = None,
    output_content: str = "Hello! How can I help you?",
) -> dict[str, Any]:
    """Create a mock span with OpenAI-style attributes.

    Args:
        span_id: Unique span identifier
        trace_id: Parent trace identifier
        parent_span_id: Parent span ID (for nested spans)
        model: OpenAI model name
        input_tokens: Input token count
        output_tokens: Output token count
        input_messages: Input messages (OpenAI format)
        output_content: Response content text

    Returns:
        Dictionary mimicking Logfire span query result
    """
    if input_messages is None:
        input_messages = [{"role": "user", "content": "Hello!"}]

    # Create span events for messages (GenAI semantic convention)
    events = []
    for msg in input_messages:
        event_name = f"gen_ai.{msg.get('role', 'user')}.message"
        events.append(
            {
                "name": event_name,
                "attributes": {"role": msg.get("role"), "content": msg.get("content")},
            }
        )

    # Add output event
    events.append(
        {
            "name": "gen_ai.assistant.message",
            "attributes": {"role": "assistant", "content": output_content},
        }
    )

    span = MockSpan(
        span_id=span_id,
        trace_id=trace_id,
        parent_span_id=parent_span_id,
        span_name=f"chat {model}",
        message=f"OpenAI chat completion with {model}",
        duration=0.5,
        otel_scope_name="opentelemetry.instrumentation.openai",
        otel_events=events,
        attributes={
            "gen_ai.operation.name": "chat",
            "gen_ai.system": "openai",
            "gen_ai.request.model": model,
            "gen_ai.response.model": model,
            "gen_ai.usage.input_tokens": input_tokens,
            "gen_ai.usage.output_tokens": output_tokens,
        },
    )

    return span.to_dict()


def create_anthropic_llm_span(
    span_id: str = "span-anthropic",
    trace_id: str = "trace-001",
    parent_span_id: str | None = None,
    model: str = "claude-3-5-haiku-latest",
    input_tokens: int = 50,
    output_tokens: int = 25,
    input_messages: list[dict[str, Any]] | None = None,
    system: str | None = None,
    output_content: str = "Hello! How can I help you?",
) -> dict[str, Any]:
    """Create a mock span with Anthropic-style attributes.

    Args:
        span_id: Unique span identifier
        trace_id: Parent trace identifier
        parent_span_id: Parent span ID (for nested spans)
        model: Anthropic model name
        input_tokens: Input token count
        output_tokens: Output token count
        input_messages: Input messages (Anthropic format)
        system: System prompt
        output_content: Response content text

    Returns:
        Dictionary mimicking Logfire span query result
    """
    if input_messages is None:
        input_messages = [{"role": "user", "content": "Hello!"}]

    # Create span events for messages
    events = []
    if system:
        events.append(
            {
                "name": "gen_ai.system.message",
                "attributes": {"role": "system", "content": system},
            }
        )
    for msg in input_messages:
        event_name = f"gen_ai.{msg.get('role', 'user')}.message"
        events.append(
            {
                "name": event_name,
                "attributes": {"role": msg.get("role"), "content": msg.get("content")},
            }
        )
    events.append(
        {
            "name": "gen_ai.assistant.message",
            "attributes": {"role": "assistant", "content": output_content},
        }
    )

    span = MockSpan(
        span_id=span_id,
        trace_id=trace_id,
        parent_span_id=parent_span_id,
        span_name=f"chat {model}",
        message=f"Anthropic chat completion with {model}",
        duration=0.6,
        otel_scope_name="opentelemetry.instrumentation.anthropic",
        otel_events=events,
        attributes={
            "gen_ai.operation.name": "chat",
            "gen_ai.system": "anthropic",
            "gen_ai.request.model": model,
            "gen_ai.response.model": model,
            "gen_ai.usage.input_tokens": input_tokens,
            "gen_ai.usage.output_tokens": output_tokens,
        },
    )

    return span.to_dict()


def create_google_llm_span(
    span_id: str = "span-google",
    trace_id: str = "trace-001",
    parent_span_id: str | None = None,
    model: str = "gemini-2.0-flash",
    input_tokens: int = 50,
    output_tokens: int = 25,
    input_messages: list[dict[str, Any]] | None = None,
    output_content: str = "Hello! How can I help you?",
) -> dict[str, Any]:
    """Create a mock span with Google GenAI-style attributes.

    Args:
        span_id: Unique span identifier
        trace_id: Parent trace identifier
        parent_span_id: Parent span ID (for nested spans)
        model: Gemini model name
        input_tokens: Input token count
        output_tokens: Output token count
        input_messages: Input messages
        output_content: Response content text

    Returns:
        Dictionary mimicking Logfire span query result
    """
    if input_messages is None:
        input_messages = [{"role": "user", "content": "Hello!"}]

    events = []
    for msg in input_messages:
        event_name = f"gen_ai.{msg.get('role', 'user')}.message"
        events.append(
            {
                "name": event_name,
                "attributes": {"role": msg.get("role"), "content": msg.get("content")},
            }
        )
    events.append(
        {
            "name": "gen_ai.assistant.message",
            "attributes": {"role": "assistant", "content": output_content},
        }
    )

    span = MockSpan(
        span_id=span_id,
        trace_id=trace_id,
        parent_span_id=parent_span_id,
        span_name=f"generate_content {model}",
        message=f"Google GenAI completion with {model}",
        duration=0.7,
        otel_scope_name="opentelemetry.instrumentation.google-genai",
        otel_events=events,
        attributes={
            "gen_ai.operation.name": "generate_content",
            "gen_ai.system": "google_genai",
            "gen_ai.request.model": model,
            "gen_ai.response.model": model,
            "gen_ai.usage.input_tokens": input_tokens,
            "gen_ai.usage.output_tokens": output_tokens,
        },
    )

    return span.to_dict()


def create_tool_span(
    span_id: str = "span-tool",
    trace_id: str = "trace-001",
    parent_span_id: str | None = None,
    tool_name: str = "get_weather",
    arguments: dict[str, Any] | None = None,
    result: str = "Sunny, 72F",
    error: str | None = None,
) -> dict[str, Any]:
    """Create a mock span for tool execution.

    Args:
        span_id: Unique span identifier
        trace_id: Parent trace identifier
        parent_span_id: Parent span ID (LLM span that invoked the tool)
        tool_name: Tool function name
        arguments: Tool input arguments
        result: Tool execution result
        error: Error message if tool failed

    Returns:
        Dictionary mimicking Logfire span query result
    """
    if arguments is None:
        arguments = {"city": "San Francisco"}

    span = MockSpan(
        span_id=span_id,
        trace_id=trace_id,
        parent_span_id=parent_span_id,
        span_name=f"execute_tool {tool_name}",
        message=f"Executing tool: {tool_name}",
        duration=0.1,
        is_exception=error is not None,
        exception_message=error,
        attributes={
            "gen_ai.operation.name": "execute_tool",
            "gen_ai.tool.name": tool_name,
            "gen_ai.tool.call.id": f"call_{span_id}",
            "gen_ai.tool.call.arguments": arguments,
            "gen_ai.tool.call.result": result if not error else None,
        },
    )

    return span.to_dict()


def create_agent_span(
    span_id: str = "span-agent",
    trace_id: str = "trace-001",
    parent_span_id: str | None = None,
    agent_name: str = "assistant",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Create a mock span for agent/orchestration.

    Args:
        span_id: Unique span identifier
        trace_id: Parent trace identifier
        parent_span_id: Parent span ID (for nested agents)
        agent_name: Agent name
        tags: Span tags

    Returns:
        Dictionary mimicking Logfire span query result
    """
    span = MockSpan(
        span_id=span_id,
        trace_id=trace_id,
        parent_span_id=parent_span_id,
        span_name=f"agent {agent_name}",
        message=f"Agent run: {agent_name}",
        duration=2.0,
        tags=tags,
        otel_scope_name="pydantic-ai",
        attributes={
            "gen_ai.operation.name": "invoke_agent",
            "agent": agent_name,
        },
    )

    return span.to_dict()


def create_pydantic_ai_span(
    span_id: str = "span-pydantic-ai",
    trace_id: str = "trace-001",
    parent_span_id: str | None = None,
    model: str = "gpt-4o-mini",
    input_tokens: int = 50,
    output_tokens: int = 25,
    input_messages: list[dict[str, Any]] | None = None,
    output_content: str = "Hello! How can I help you?",
) -> dict[str, Any]:
    """Create a mock span for Pydantic AI LLM call.

    Pydantic AI uses OpenAI-style format but has its own scope name.

    Args:
        span_id: Unique span identifier
        trace_id: Parent trace identifier
        parent_span_id: Parent span ID
        model: Model name
        input_tokens: Input token count
        output_tokens: Output token count
        input_messages: Input messages
        output_content: Response content text

    Returns:
        Dictionary mimicking Logfire span query result
    """
    if input_messages is None:
        input_messages = [{"role": "user", "content": "Hello!"}]

    events = []
    for msg in input_messages:
        event_name = f"gen_ai.{msg.get('role', 'user')}.message"
        events.append(
            {
                "name": event_name,
                "attributes": {"role": msg.get("role"), "content": msg.get("content")},
            }
        )
    events.append(
        {
            "name": "gen_ai.assistant.message",
            "attributes": {"role": "assistant", "content": output_content},
        }
    )

    span = MockSpan(
        span_id=span_id,
        trace_id=trace_id,
        parent_span_id=parent_span_id,
        span_name=f"chat {model}",
        message=f"Pydantic AI chat with {model}",
        duration=0.5,
        otel_scope_name="pydantic-ai",
        otel_events=events,
        attributes={
            "gen_ai.operation.name": "chat",
            "gen_ai.system": "openai",
            "gen_ai.request.model": model,
            "gen_ai.response.model": model,
            "gen_ai.usage.input_tokens": input_tokens,
            "gen_ai.usage.output_tokens": output_tokens,
        },
    )

    return span.to_dict()


def create_multiturn_openai_spans(
    trace_id: str = "trace-multiturn",
    model: str = "gpt-4o-mini",
) -> list[dict[str, Any]]:
    """Create a set of spans representing a multi-turn OpenAI conversation.

    Args:
        trace_id: Trace identifier
        model: Model name

    Returns:
        List of span dictionaries for a 3-turn conversation
    """
    from datetime import timedelta

    now = datetime.now()

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
    )
    span1["start_timestamp"] = now

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
    )
    span2["start_timestamp"] = now + timedelta(seconds=1)

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
    )
    span3["start_timestamp"] = now + timedelta(seconds=2)

    return [span1, span2, span3]


def create_pydantic_ai_agent_trace(
    trace_id: str = "trace-pydantic-agent",
    model: str = "gpt-4o-mini",
    agent_name: str = "assistant",
    with_tools: bool = False,
) -> list[dict[str, Any]]:
    """Create a complete Pydantic AI agent trace with agent and LLM spans.

    Args:
        trace_id: Trace identifier
        model: Model name
        agent_name: Name of the agent
        with_tools: Whether to include tool execution spans

    Returns:
        List of span dictionaries representing a complete agent trace
    """
    from datetime import timedelta

    now = datetime.now()

    spans: list[dict[str, Any]] = []

    # Agent span (root)
    agent_span = create_agent_span(
        span_id="span-agent-root",
        trace_id=trace_id,
        agent_name=agent_name,
    )
    agent_span["start_timestamp"] = now
    spans.append(agent_span)

    # LLM call span (child of agent)
    llm_span = create_pydantic_ai_span(
        span_id="span-llm-call",
        trace_id=trace_id,
        parent_span_id="span-agent-root",
        model=model,
        input_messages=[
            {"role": "system", "content": f"You are {agent_name}."},
            {"role": "user", "content": "Hello!"},
        ],
        output_content="Hello! How can I help you?",
    )
    llm_span["start_timestamp"] = now + timedelta(milliseconds=100)
    spans.append(llm_span)

    if with_tools:
        # Tool execution span
        tool_span = create_tool_span(
            span_id="span-tool-exec",
            trace_id=trace_id,
            parent_span_id="span-llm-call",
            tool_name="get_weather",
            arguments={"city": "San Francisco"},
            result="Sunny, 72F",
        )
        tool_span["start_timestamp"] = now + timedelta(milliseconds=200)
        spans.append(tool_span)

        # Second LLM call after tool
        llm_span2 = create_pydantic_ai_span(
            span_id="span-llm-call-2",
            trace_id=trace_id,
            parent_span_id="span-agent-root",
            model=model,
            input_messages=[
                {"role": "system", "content": f"You are {agent_name}."},
                {"role": "user", "content": "What's the weather?"},
                {"role": "assistant", "content": "Let me check..."},
                {"role": "tool", "content": "Sunny, 72F"},
            ],
            output_content="The weather in San Francisco is sunny with a temperature of 72F.",
        )
        llm_span2["start_timestamp"] = now + timedelta(milliseconds=300)
        spans.append(llm_span2)

    return spans


def create_openai_tool_calls() -> list[dict[str, Any]]:
    """Create sample OpenAI tool calls for testing.

    Returns:
        List of tool call dictionaries in OpenAI format
    """
    return [
        {
            "id": "call_abc123",
            "type": "function",
            "function": {
                "name": "get_weather",
                "arguments": '{"city": "San Francisco"}',
            },
        },
        {
            "id": "call_def456",
            "type": "function",
            "function": {
                "name": "get_time",
                "arguments": '{"timezone": "America/Los_Angeles"}',
            },
        },
    ]


def create_openai_tools() -> list[dict[str, Any]]:
    """Create sample OpenAI tool definitions for testing.

    Returns:
        List of tool definition dictionaries in OpenAI format
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get the current weather for a city.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "The city name to get weather for.",
                        }
                    },
                    "required": ["city"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_time",
                "description": "Get the current time in a timezone.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "timezone": {
                            "type": "string",
                            "description": "The timezone name.",
                        }
                    },
                    "required": ["timezone"],
                },
            },
        },
    ]
