"""Event conversion for LangFuse observations."""

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

from .detection import detect_provider_format
from .extraction import extract_input_messages, extract_output, extract_tools


async def to_model_event(gen: Any) -> ModelEvent:
    """Convert LangFuse generation to ModelEvent.

    Args:
        gen: LangFuse generation observation

    Returns:
        ModelEvent object
    """
    # Detect provider format
    format_type = detect_provider_format(gen)

    # Extract input messages based on detected format
    input_messages = await extract_input_messages(gen.input, format_type)

    # Extract output based on detected format
    output = await extract_output(gen.output, gen, format_type)

    # Build GenerateConfig from model_parameters
    params = gen.model_parameters or {}
    config = GenerateConfig(
        temperature=params.get("temperature"),
        max_tokens=params.get("max_tokens"),
        top_p=params.get("top_p"),
        stop_seqs=params.get("stop"),
    )

    return ModelEvent(
        model=gen.model or "unknown",
        input=input_messages,
        tools=extract_tools(gen),
        tool_choice="auto",
        config=config,
        output=output,
        timestamp=gen.start_time,
        completed=gen.end_time,
        span_id=getattr(gen, "parent_observation_id", None),
    )


def to_tool_event(obs: Any) -> ToolEvent:
    """Convert LangFuse TOOL observation to ToolEvent.

    Args:
        obs: LangFuse observation

    Returns:
        ToolEvent object
    """
    error = None
    if getattr(obs, "level", None) == "ERROR":
        error = ToolCallError(
            type="unknown", message=getattr(obs, "status_message", "Unknown error")
        )

    # Convert result to string if needed
    result = obs.output
    if result is not None and not isinstance(result, str):
        result = str(result)

    return ToolEvent(
        id=obs.id or str(uuid.uuid4()),
        type="function",
        function=obs.name or "unknown_tool",
        arguments=obs.input if isinstance(obs.input, dict) else {},
        result=result or "",
        timestamp=obs.start_time,
        completed=obs.end_time,
        error=error,
        span_id=getattr(obs, "parent_observation_id", None),
    )


def to_span_begin_event(obs: Any) -> SpanBeginEvent:
    """Convert LangFuse SPAN/AGENT/CHAIN observation to SpanBeginEvent.

    Args:
        obs: LangFuse observation

    Returns:
        SpanBeginEvent object
    """
    return SpanBeginEvent(
        id=obs.id,
        name=obs.name or obs.type.lower(),
        parent_id=getattr(obs, "parent_observation_id", None),
        timestamp=obs.start_time,
        working_start=0.0,  # Required field
        metadata=getattr(obs, "metadata", None),
    )


def to_span_end_event(obs: Any) -> SpanEndEvent:
    """Convert LangFuse observation end to SpanEndEvent.

    Args:
        obs: LangFuse observation

    Returns:
        SpanEndEvent object
    """
    return SpanEndEvent(
        id=obs.id,
        timestamp=obs.end_time,
        metadata=getattr(obs, "metadata", None),
    )


def to_info_event(obs: Any) -> InfoEvent:
    """Convert LangFuse EVENT observation to InfoEvent.

    Args:
        obs: LangFuse observation

    Returns:
        InfoEvent object
    """
    return InfoEvent(
        source=obs.name or "langfuse",
        data=obs.input or obs.output or obs.name or "event",
        timestamp=obs.start_time,
        metadata=getattr(obs, "metadata", None),
    )


async def observations_to_events(observations: list[Any]) -> list[Any]:
    """Convert LangFuse observations to Scout events by type.

    Args:
        observations: List of LangFuse observations

    Returns:
        List of Scout event objects
    """
    events: list[Event] = []
    for obs in observations:
        obs_type = getattr(obs, "type", "")
        match obs_type:
            case "GENERATION":
                events.append(await to_model_event(obs))
            case "TOOL":
                events.append(to_tool_event(obs))
            case "SPAN" | "AGENT" | "CHAIN":
                events.append(to_span_begin_event(obs))
                if obs.end_time:
                    events.append(to_span_end_event(obs))
            case "EVENT":
                events.append(to_info_event(obs))
            # Skip: RETRIEVER, EMBEDDING, GUARDRAIL

    # Sort by timestamp to maintain chronological order (handle None timestamps safely)
    events.sort(key=lambda e: e.timestamp or datetime.min)
    return events
