"""Mock objects for LangSmith unit tests.

Provides mock Run and Example objects that simulate LangSmith SDK types
without requiring API access. These enable unit testing of internal
logic (detection, extraction, events, tree) in isolation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class MockRun:
    """Simulates LangSmith run object for unit testing.

    Mirrors the structure of langsmith.schemas.Run with the fields
    used by the langsmith source implementation.
    """

    id: str = "run-001"
    trace_id: str = "trace-001"
    parent_run_id: str | None = None
    run_type: str = "llm"  # llm, tool, chain, agent, retriever, embedding
    name: str = "test-run"
    inputs: dict[str, Any] | None = None
    outputs: dict[str, Any] | None = None
    extra: dict[str, Any] | None = None
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None
    error: str | None = None
    tags: list[str] | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


@dataclass
class MockExample:
    """Simulates LangSmith dataset example for unit testing.

    Mirrors the structure of langsmith.schemas.Example with fields
    used by the langsmith source implementation.
    """

    id: str = "example-001"
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] | None = None
    created_at: datetime = field(default_factory=datetime.now)


# =============================================================================
# Factory Functions for Pre-configured Mocks
# =============================================================================


def create_openai_llm_run(
    run_id: str = "run-openai",
    trace_id: str = "trace-001",
    parent_run_id: str | None = None,
    model: str = "gpt-4o-mini",
    messages: list[dict[str, Any]] | None = None,
    tool_calls: list[dict[str, Any]] | None = None,
    content: str = "Hello! How can I help you?",
    prompt_tokens: int = 50,
    completion_tokens: int = 25,
) -> MockRun:
    """Create a MockRun with OpenAI-style inputs/outputs.

    Args:
        run_id: Unique run identifier
        trace_id: Parent trace identifier
        parent_run_id: Parent run ID (for nested runs)
        model: OpenAI model name
        messages: Input messages (OpenAI format)
        tool_calls: Tool calls in the response
        content: Response content text
        prompt_tokens: Input token count
        completion_tokens: Output token count

    Returns:
        MockRun configured with OpenAI format
    """
    if messages is None:
        messages = [{"role": "user", "content": "Hello!"}]

    inputs = {"messages": messages}

    # Build output in OpenAI format
    output_message: dict[str, Any] = {
        "role": "assistant",
        "content": content,
    }
    if tool_calls:
        output_message["tool_calls"] = tool_calls
        output_message["content"] = None

    outputs = {
        "choices": [{"message": output_message, "finish_reason": "stop"}],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }

    extra = {
        "metadata": {
            "ls_provider": "openai",
            "ls_model_name": model,
        },
        "invocation_params": {
            "model": model,
            "temperature": 0.7,
        },
    }

    return MockRun(
        id=run_id,
        trace_id=trace_id,
        parent_run_id=parent_run_id,
        run_type="llm",
        name=model,
        inputs=inputs,
        outputs=outputs,
        extra=extra,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        end_time=datetime.now(),
    )


def create_anthropic_llm_run(
    run_id: str = "run-anthropic",
    trace_id: str = "trace-001",
    parent_run_id: str | None = None,
    model: str = "claude-3-5-haiku-latest",
    messages: list[dict[str, Any]] | None = None,
    system: str | None = None,
    content_blocks: list[dict[str, Any]] | None = None,
    prompt_tokens: int = 50,
    completion_tokens: int = 25,
) -> MockRun:
    """Create a MockRun with Anthropic-style inputs/outputs.

    Args:
        run_id: Unique run identifier
        trace_id: Parent trace identifier
        parent_run_id: Parent run ID (for nested runs)
        model: Anthropic model name
        messages: Input messages (Anthropic format)
        system: System prompt
        content_blocks: Response content blocks
        prompt_tokens: Input token count
        completion_tokens: Output token count

    Returns:
        MockRun configured with Anthropic format
    """
    if messages is None:
        messages = [{"role": "user", "content": "Hello!"}]

    inputs: dict[str, Any] = {"messages": messages}
    if system:
        inputs["system"] = system

    # Build output in Anthropic format
    if content_blocks is None:
        content_blocks = [{"type": "text", "text": "Hello! How can I help you?"}]

    outputs = {
        "content": content_blocks,
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": prompt_tokens,
            "output_tokens": completion_tokens,
        },
    }

    extra = {
        "metadata": {
            "ls_provider": "anthropic",
            "ls_model_name": model,
        },
    }

    return MockRun(
        id=run_id,
        trace_id=trace_id,
        parent_run_id=parent_run_id,
        run_type="llm",
        name=model,
        inputs=inputs,
        outputs=outputs,
        extra=extra,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        end_time=datetime.now(),
    )


def create_google_llm_run(
    run_id: str = "run-google",
    trace_id: str = "trace-001",
    parent_run_id: str | None = None,
    model: str = "gemini-2.0-flash",
    contents: list[dict[str, Any]] | None = None,
    system_instruction: str | None = None,
    response_text: str = "Hello! How can I help you?",
    prompt_tokens: int = 50,
    completion_tokens: int = 25,
) -> MockRun:
    """Create a MockRun with Google/Gemini-style inputs/outputs.

    Args:
        run_id: Unique run identifier
        trace_id: Parent trace identifier
        parent_run_id: Parent run ID (for nested runs)
        model: Gemini model name
        contents: Input contents (Google format)
        system_instruction: System instruction
        response_text: Response text
        prompt_tokens: Input token count
        completion_tokens: Output token count

    Returns:
        MockRun configured with Google format
    """
    if contents is None:
        contents = [{"role": "user", "parts": [{"text": "Hello!"}]}]

    inputs: dict[str, Any] = {"contents": contents}
    if system_instruction:
        inputs["system_instruction"] = system_instruction

    # Build output in Google format
    outputs = {
        "candidates": [
            {
                "content": {"role": "model", "parts": [{"text": response_text}]},
                "finish_reason": "STOP",
            }
        ],
        "usage_metadata": {
            "prompt_token_count": prompt_tokens,
            "candidates_token_count": completion_tokens,
        },
    }

    extra = {
        "metadata": {
            "ls_provider": "google",
            "ls_model_name": model,
        },
    }

    return MockRun(
        id=run_id,
        trace_id=trace_id,
        parent_run_id=parent_run_id,
        run_type="llm",
        name=model,
        inputs=inputs,
        outputs=outputs,
        extra=extra,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        end_time=datetime.now(),
    )


def create_tool_run(
    run_id: str = "run-tool",
    trace_id: str = "trace-001",
    parent_run_id: str | None = None,
    name: str = "get_weather",
    inputs: dict[str, Any] | None = None,
    output: str | dict[str, Any] = "Sunny, 72F",
    error: str | None = None,
) -> MockRun:
    """Create a MockRun for tool execution.

    Args:
        run_id: Unique run identifier
        trace_id: Parent trace identifier
        parent_run_id: Parent run ID (LLM run that invoked the tool)
        name: Tool function name
        inputs: Tool input arguments
        output: Tool execution result
        error: Error message if tool failed

    Returns:
        MockRun configured as tool type
    """
    if inputs is None:
        inputs = {"city": "San Francisco"}

    outputs: dict[str, Any] | None = None
    if not error:
        if isinstance(output, dict):
            outputs = output
        else:
            outputs = {"output": output}

    return MockRun(
        id=run_id,
        trace_id=trace_id,
        parent_run_id=parent_run_id,
        run_type="tool",
        name=name,
        inputs=inputs,
        outputs=outputs,
        error=error,
        end_time=datetime.now(),
    )


def create_chain_run(
    run_id: str = "run-chain",
    trace_id: str = "trace-001",
    parent_run_id: str | None = None,
    name: str = "agent",
    run_type: str = "chain",
    inputs: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
    tags: list[str] | None = None,
) -> MockRun:
    """Create a MockRun for chain/agent spans.

    Args:
        run_id: Unique run identifier
        trace_id: Parent trace identifier
        parent_run_id: Parent run ID (for nested chains)
        name: Chain/agent name
        run_type: Either "chain" or "agent"
        inputs: Chain input data
        outputs: Chain output data
        tags: Run tags

    Returns:
        MockRun configured as chain/agent type
    """
    if inputs is None:
        inputs = {"messages": [{"role": "user", "content": "Hello"}]}

    if outputs is None:
        outputs = {"output": "Done"}

    return MockRun(
        id=run_id,
        trace_id=trace_id,
        parent_run_id=parent_run_id,
        run_type=run_type,
        name=name,
        inputs=inputs,
        outputs=outputs,
        tags=tags,
        end_time=datetime.now(),
    )


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


def create_anthropic_tool_use_blocks() -> list[dict[str, Any]]:
    """Create sample Anthropic tool_use content blocks for testing.

    Returns:
        List of content block dictionaries in Anthropic format
    """
    return [
        {
            "type": "tool_use",
            "id": "toolu_abc123",
            "name": "get_weather",
            "input": {"city": "San Francisco"},
        },
        {
            "type": "tool_use",
            "id": "toolu_def456",
            "name": "get_time",
            "input": {"timezone": "America/Los_Angeles"},
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
