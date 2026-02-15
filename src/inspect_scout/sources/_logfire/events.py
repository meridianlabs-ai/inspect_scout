"""Event conversion for Logfire spans.

Converts Logfire spans to Scout event types:
- LLM spans -> ModelEvent
- Tool spans -> ToolEvent
- Agent spans -> SpanBeginEvent + SpanEndEvent
"""

import json
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

from .detection import (
    detect_instrumentor,
    get_model_name,
    is_agent_span,
    is_llm_span,
    is_tool_span,
)
from .extraction import extract_input_messages, extract_output, extract_tools


def _get_timestamp(span: dict[str, Any], attr: str = "start_timestamp") -> datetime:
    """Get a timestamp from a span, with fallback to datetime.min."""
    ts = span.get(attr)
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return datetime.min
    return datetime.min


def _get_end_timestamp(span: dict[str, Any]) -> datetime:
    """Get end timestamp from span.

    Calculates from start_timestamp + duration if end_timestamp not available.
    """
    end_ts = span.get("end_timestamp")
    if end_ts:
        if isinstance(end_ts, datetime):
            return end_ts
        if isinstance(end_ts, str):
            try:
                return datetime.fromisoformat(end_ts.replace("Z", "+00:00"))
            except ValueError:
                pass

    # Calculate from start + duration
    start = _get_timestamp(span, "start_timestamp")
    duration = span.get("duration")
    if duration is not None and start != datetime.min:
        from datetime import timedelta

        return start + timedelta(seconds=float(duration))

    return datetime.min


async def to_model_event(span: dict[str, Any]) -> ModelEvent:
    """Convert Logfire LLM span to ModelEvent.

    Args:
        span: Logfire span with gen_ai.operation.name in (chat, text_completion, etc.)

    Returns:
        ModelEvent object
    """
    # Detect instrumentor for correct message extraction
    instrumentor = detect_instrumentor(span)

    # Extract input messages
    input_messages = await extract_input_messages(span, instrumentor)

    # Extract output
    output = await extract_output(span, instrumentor)

    # Extract model name
    model_name = get_model_name(span) or "unknown"

    # Build GenerateConfig from attributes
    attributes = span.get("attributes") or {}
    config = GenerateConfig(
        temperature=attributes.get("gen_ai.request.temperature"),
        max_tokens=attributes.get("gen_ai.request.max_tokens"),
        top_p=attributes.get("gen_ai.request.top_p"),
        stop_seqs=attributes.get("gen_ai.request.stop_sequences"),
    )

    return ModelEvent(
        model=model_name,
        input=input_messages,
        tools=extract_tools(span),
        tool_choice="auto",
        config=config,
        output=output,
        timestamp=_get_timestamp(span, "start_timestamp"),
        completed=_get_end_timestamp(span),
        span_id=str(span.get("parent_span_id") or ""),
    )


def to_tool_event(span: dict[str, Any]) -> ToolEvent:
    """Convert Logfire tool span to ToolEvent.

    Args:
        span: Logfire span representing tool execution

    Returns:
        ToolEvent object
    """
    attributes = span.get("attributes") or {}

    error = None
    if span.get("is_exception"):
        error = ToolCallError(
            type=span.get("exception_type", "unknown"),
            message=span.get("exception_message", "Unknown error"),
        )

    # Extract function name
    function_name = (
        attributes.get("gen_ai.tool.name")
        or span.get("span_name")
        or span.get("message")
        or "unknown_tool"
    )

    # Extract arguments
    arguments = attributes.get("gen_ai.tool.call.arguments", {})
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            arguments = {}

    # Extract result
    result = attributes.get("gen_ai.tool.call.result", "")
    if isinstance(result, dict):
        result = json.dumps(result)
    else:
        result = str(result)

    return ToolEvent(
        id=str(
            attributes.get("gen_ai.tool.call.id") or span.get("span_id") or uuid.uuid4()
        ),
        type="function",
        function=str(function_name),
        arguments=arguments if isinstance(arguments, dict) else {},
        result=result,
        timestamp=_get_timestamp(span, "start_timestamp"),
        completed=_get_end_timestamp(span),
        error=error,
        span_id=str(span.get("parent_span_id") or ""),
    )


def to_span_begin_event(
    span: dict[str, Any], *, is_agent: bool = False
) -> SpanBeginEvent:
    """Convert Logfire span to SpanBeginEvent.

    Args:
        span: Logfire span (typically agent or wrapper span)
        is_agent: Whether this span represents an agent execution

    Returns:
        SpanBeginEvent object
    """
    name = span.get("span_name") or span.get("message") or "span"

    return SpanBeginEvent(
        id=str(span.get("span_id", "")),
        name=str(name),
        parent_id=str(span.get("parent_span_id") or ""),
        type="agent" if is_agent else None,
        timestamp=_get_timestamp(span, "start_timestamp"),
        working_start=0.0,  # Required field
        metadata=_extract_span_metadata(span),
    )


def to_span_end_event(span: dict[str, Any]) -> SpanEndEvent:
    """Convert Logfire span end to SpanEndEvent.

    Args:
        span: Logfire span object

    Returns:
        SpanEndEvent object
    """
    return SpanEndEvent(
        id=str(span.get("span_id", "")),
        timestamp=_get_end_timestamp(span),
        metadata=_extract_span_metadata(span),
    )


def to_info_event(span: dict[str, Any]) -> InfoEvent:
    """Convert Logfire span to InfoEvent.

    Args:
        span: Logfire span object

    Returns:
        InfoEvent object
    """
    return InfoEvent(
        source=str(span.get("otel_scope_name") or "logfire"),
        data=span.get("attributes") or span.get("message") or "",
        timestamp=_get_timestamp(span, "start_timestamp"),
        metadata=_extract_span_metadata(span),
    )


def _extract_span_metadata(span: dict[str, Any]) -> dict[str, Any] | None:
    """Extract metadata from span for event.

    Args:
        span: Logfire span object

    Returns:
        Metadata dictionary or None
    """
    metadata: dict[str, Any] = {}

    # Add tags
    tags = span.get("tags")
    if tags:
        metadata["tags"] = tags

    # Add service info
    service_name = span.get("service_name")
    if service_name:
        metadata["service_name"] = service_name

    # Add level
    level = span.get("level")
    if level:
        metadata["level"] = level

    return metadata if metadata else None


async def spans_to_events(spans: list[dict[str, Any]]) -> list[Event]:
    """Convert Logfire spans to Scout events by type.

    Args:
        spans: List of Logfire spans

    Returns:
        List of Scout event objects sorted chronologically
    """
    events: list[Event] = []

    for span in spans:
        if is_llm_span(span):
            events.append(await to_model_event(span))
        elif is_tool_span(span):
            events.append(to_tool_event(span))
        elif is_agent_span(span):
            events.append(to_span_begin_event(span, is_agent=True))
            # Add end event if span has duration
            if span.get("duration") is not None:
                events.append(to_span_end_event(span))
        # Skip other spans for now (embeddings, etc.)

    # Sort by timestamp to maintain chronological order
    events.sort(key=lambda e: e.timestamp or datetime.min)

    return events
