"""Event conversion for Phoenix spans.

Converts Phoenix spans to Scout event types:
- LLM spans (span_kind="LLM") -> ModelEvent
- Tool spans (span_kind="TOOL") -> ToolEvent
- Chain spans (span_kind="CHAIN"/"AGENT") -> SpanBeginEvent + SpanEndEvent
"""

import json
import uuid
from datetime import datetime
from typing import Any

from inspect_ai.event import (
    Event,
    ModelEvent,
    SpanBeginEvent,
    SpanEndEvent,
    ToolEvent,
)
from inspect_ai.model._generate_config import GenerateConfig
from inspect_ai.tool._tool_call import ToolCallError

from .detection import (
    detect_provider,
    get_model_name,
    is_chain_span,
    is_llm_span,
    is_tool_span,
)
from .extraction import extract_input_messages, extract_output, extract_tools


def _get_timestamp(span: dict[str, Any], attr: str = "start_time") -> datetime:
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


def _get_span_id(span: dict[str, Any]) -> str:
    """Get span_id from Phoenix span context."""
    context = span.get("context") or {}
    return str(context.get("span_id", ""))


def _get_parent_id(span: dict[str, Any]) -> str:
    """Get parent_id from Phoenix span."""
    parent = span.get("parent_id")
    return str(parent) if parent else ""


async def to_model_event(span: dict[str, Any]) -> ModelEvent:
    """Convert Phoenix LLM span to ModelEvent.

    Args:
        span: Phoenix span with span_kind="LLM"

    Returns:
        ModelEvent object
    """
    provider = detect_provider(span)

    # Extract input messages
    input_messages = await extract_input_messages(span, provider)

    # Extract output
    output = await extract_output(span, provider)

    # Extract model name
    model_name = get_model_name(span) or "unknown"

    # Build GenerateConfig from attributes
    attributes = span.get("attributes") or {}
    config = GenerateConfig(
        temperature=attributes.get("llm.invocation_parameters.temperature"),
        max_tokens=attributes.get("llm.invocation_parameters.max_tokens"),
        top_p=attributes.get("llm.invocation_parameters.top_p"),
    )

    return ModelEvent(
        model=model_name,
        input=input_messages,
        tools=extract_tools(span),
        tool_choice="auto",
        config=config,
        output=output,
        timestamp=_get_timestamp(span, "start_time"),
        completed=_get_timestamp(span, "end_time"),
        span_id=_get_parent_id(span),
    )


def to_tool_event(span: dict[str, Any]) -> ToolEvent:
    """Convert Phoenix tool span to ToolEvent.

    Args:
        span: Phoenix span representing tool execution

    Returns:
        ToolEvent object
    """
    attributes = span.get("attributes") or {}

    error = None
    status_code = str(span.get("status_code", "")).upper()
    if status_code == "ERROR":
        error = ToolCallError(
            type="unknown",
            message=span.get("status_message") or "Unknown error",
        )

    # Extract function name
    function_name = attributes.get("tool.name") or span.get("name") or "unknown_tool"

    # Extract arguments from input.value
    arguments: dict[str, Any] = {}
    input_value = attributes.get("input.value")
    if input_value:
        if isinstance(input_value, str):
            try:
                parsed = json.loads(input_value)
                if isinstance(parsed, dict):
                    arguments = parsed
            except json.JSONDecodeError:
                pass
        elif isinstance(input_value, dict):
            arguments = input_value

    # Extract result from output.value
    result = ""
    output_value = attributes.get("output.value")
    if output_value:
        if isinstance(output_value, dict):
            result = json.dumps(output_value)
        else:
            result = str(output_value)

    return ToolEvent(
        id=str(attributes.get("tool.call.id") or _get_span_id(span) or uuid.uuid4()),
        type="function",
        function=str(function_name),
        arguments=arguments,
        result=result,
        timestamp=_get_timestamp(span, "start_time"),
        completed=_get_timestamp(span, "end_time"),
        error=error,
        span_id=_get_parent_id(span),
    )


def to_span_begin_event(span: dict[str, Any]) -> SpanBeginEvent:
    """Convert Phoenix span to SpanBeginEvent.

    Args:
        span: Phoenix span (typically chain or agent span)

    Returns:
        SpanBeginEvent object
    """
    name = span.get("name") or "span"

    return SpanBeginEvent(
        id=_get_span_id(span),
        name=str(name),
        parent_id=_get_parent_id(span),
        timestamp=_get_timestamp(span, "start_time"),
        working_start=0.0,
    )


def to_span_end_event(span: dict[str, Any]) -> SpanEndEvent:
    """Convert Phoenix span end to SpanEndEvent.

    Args:
        span: Phoenix span object

    Returns:
        SpanEndEvent object
    """
    return SpanEndEvent(
        id=_get_span_id(span),
        timestamp=_get_timestamp(span, "end_time"),
    )


async def spans_to_events(spans: list[dict[str, Any]]) -> list[Event]:
    """Convert Phoenix spans to Scout events by type.

    Dispatches based on span_kind field.

    Args:
        spans: List of Phoenix spans

    Returns:
        List of Scout event objects sorted chronologically
    """
    events: list[Event] = []

    for span in spans:
        if is_llm_span(span):
            events.append(await to_model_event(span))
        elif is_tool_span(span):
            events.append(to_tool_event(span))
        elif is_chain_span(span):
            events.append(to_span_begin_event(span))
            # Add end event if span has end_time
            if span.get("end_time"):
                events.append(to_span_end_event(span))

    # Sort by timestamp to maintain chronological order
    events.sort(key=lambda e: e.timestamp or datetime.min)

    return events
