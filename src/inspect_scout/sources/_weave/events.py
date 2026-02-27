"""Event conversion for W&B Weave calls.

Converts Weave calls to Scout event types:
- LLM calls -> ModelEvent
- Tool calls -> ToolEvent
- Span/chain calls -> SpanBeginEvent + SpanEndEvent
"""

import uuid
from datetime import datetime
from typing import Any

from inspect_ai.event import (
    Event,
    InfoEvent,
    ModelEvent,
    SpanBeginEvent,
    SpanEndEvent,
    ToolEvent,
)
from inspect_ai.model._generate_config import GenerateConfig
from inspect_ai.tool._tool_call import ToolCallError

from .detection import detect_provider_format, get_model_name


def _to_float(value: Any) -> float | None:
    """Coerce a value to float, returning None for non-numeric types."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    """Coerce a value to int, returning None for non-numeric types."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
from .extraction import extract_input_messages, extract_output, extract_tools


def _get_timestamp(call: Any, attr: str = "started_at") -> datetime:
    """Get a timestamp from a call, with fallback to datetime.min."""
    ts = getattr(call, attr, None)
    return ts if isinstance(ts, datetime) else datetime.min


def _is_llm_call(call: Any) -> bool:
    """Check if a call is an LLM call.

    Uses Weave's ``kind`` attribute when available, falling back to
    op_name pattern matching for API-level call signatures.

    Args:
        call: Weave call object

    Returns:
        True if this is an LLM call
    """
    # Prefer the structured kind attribute set by Weave's integrations
    attrs = getattr(call, "attributes", None)
    if isinstance(attrs, dict):
        weave_meta = attrs.get("weave")
        if isinstance(weave_meta, dict) and weave_meta.get("kind") == "llm":
            return True

    # Fall back to op_name, but only match API-level call patterns
    # (not broad provider names which may appear in user function names)
    op_name = str(getattr(call, "op_name", "")).lower()
    llm_patterns = [
        "chat.completions",
        "messages.create",
        "generate_content",
        "completion",
    ]
    return any(pattern in op_name for pattern in llm_patterns)


def _is_tool_call(call: Any) -> bool:
    """Check if a call is a tool call.

    Args:
        call: Weave call object

    Returns:
        True if this is a tool call
    """
    op_name = str(getattr(call, "op_name", "")).lower()
    return "tool" in op_name or "function" in op_name


async def to_model_event(call: Any) -> ModelEvent:
    """Convert Weave LLM call to ModelEvent.

    Args:
        call: Weave call that is an LLM call

    Returns:
        ModelEvent object
    """
    # Detect provider format for correct message extraction
    format_type = detect_provider_format(call)

    # Extract input messages
    inputs = getattr(call, "inputs", None) or {}
    input_messages = await extract_input_messages(inputs, format_type)

    # Extract output
    output_data = getattr(call, "output", None)
    output = await extract_output(output_data, call, format_type)

    # Extract model name
    model_name = get_model_name(call)

    # Build GenerateConfig from inputs, coercing values to expected types.
    # Provider SDKs may use sentinel objects (e.g. anthropic.Omit) for unset
    # fields which are not valid floats/ints.
    config = GenerateConfig(
        temperature=_to_float(inputs.get("temperature")) if isinstance(inputs, dict) else None,
        max_tokens=_to_int(inputs.get("max_tokens")) if isinstance(inputs, dict) else None,
        top_p=_to_float(inputs.get("top_p")) if isinstance(inputs, dict) else None,
        stop_seqs=inputs.get("stop") if isinstance(inputs, dict) else None,
    )

    return ModelEvent(
        model=model_name,
        input=input_messages,
        tools=extract_tools(call),
        tool_choice="auto",
        config=config,
        output=output,
        timestamp=_get_timestamp(call, "started_at"),
        completed=_get_timestamp(call, "ended_at"),
        span_id=str(getattr(call, "parent_id", None) or ""),
    )


def to_tool_event(call: Any) -> ToolEvent:
    """Convert Weave tool call to ToolEvent.

    Args:
        call: Weave call that is a tool call

    Returns:
        ToolEvent object
    """
    error = None
    call_exception = getattr(call, "exception", None)
    if call_exception:
        error = ToolCallError(
            type="unknown",
            message=str(call_exception),
        )

    # Extract function arguments
    inputs = getattr(call, "inputs", None) or {}
    arguments = inputs if isinstance(inputs, dict) else {}

    # Extract result
    output = getattr(call, "output", None)
    result = ""
    if output:
        if isinstance(output, dict):
            result = str(
                output.get(
                    "output", output.get("result", output.get("content", output))
                )
            )
        else:
            result = str(output)

    # Get function name from op_name
    op_name = str(getattr(call, "op_name", "unknown_tool"))
    # Clean up op_name to get just the function name
    if "." in op_name:
        op_name = op_name.split(".")[-1]

    return ToolEvent(
        id=str(getattr(call, "id", uuid.uuid4())),
        type="function",
        function=op_name,
        arguments=arguments,
        result=result,
        timestamp=_get_timestamp(call, "started_at"),
        completed=_get_timestamp(call, "ended_at"),
        error=error,
        span_id=str(getattr(call, "parent_id", None) or ""),
    )


def to_span_begin_event(call: Any) -> SpanBeginEvent:
    """Convert Weave span call to SpanBeginEvent.

    Args:
        call: Weave call object

    Returns:
        SpanBeginEvent object
    """
    op_name = getattr(call, "op_name", None) or "span"
    display_name = getattr(call, "display_name", None) or op_name

    return SpanBeginEvent(
        id=str(getattr(call, "id", "")),
        name=str(display_name),
        parent_id=str(getattr(call, "parent_id", None) or ""),
        timestamp=_get_timestamp(call, "started_at"),
        working_start=0.0,  # Required field
        metadata=_extract_call_metadata(call),
    )


def to_span_end_event(call: Any) -> SpanEndEvent:
    """Convert Weave call end to SpanEndEvent.

    Args:
        call: Weave call object

    Returns:
        SpanEndEvent object
    """
    return SpanEndEvent(
        id=str(getattr(call, "id", "")),
        timestamp=_get_timestamp(call, "ended_at"),
        metadata=_extract_call_metadata(call),
    )


def to_info_event(call: Any) -> InfoEvent:
    """Convert Weave call to InfoEvent.

    Args:
        call: Weave call object

    Returns:
        InfoEvent object
    """
    op_name = str(getattr(call, "op_name", "weave"))
    return InfoEvent(
        source=op_name,
        data=getattr(call, "inputs", None) or getattr(call, "output", None) or op_name,
        timestamp=_get_timestamp(call, "started_at"),
        metadata=_extract_call_metadata(call),
    )


def _extract_call_metadata(call: Any) -> dict[str, Any] | None:
    """Extract metadata from call for event.

    Args:
        call: Weave call object

    Returns:
        Metadata dictionary or None
    """
    metadata: dict[str, Any] = {}

    # Add attributes
    attrs = getattr(call, "attributes", None)
    if isinstance(attrs, dict):
        metadata.update(attrs)

    return metadata if metadata else None


async def calls_to_events(calls: list[Any]) -> list[Event]:
    """Convert Weave calls to Scout events by type.

    Args:
        calls: List of Weave calls

    Returns:
        List of Scout event objects sorted chronologically
    """
    events: list[Event] = []

    for call in calls:
        if _is_llm_call(call):
            events.append(await to_model_event(call))
        elif _is_tool_call(call):
            events.append(to_tool_event(call))
        else:
            # Treat as span
            events.append(to_span_begin_event(call))
            if getattr(call, "ended_at", None):
                events.append(to_span_end_event(call))

    # Sort by timestamp to maintain chronological order
    events.sort(key=lambda e: e.timestamp or datetime.min)

    return events
