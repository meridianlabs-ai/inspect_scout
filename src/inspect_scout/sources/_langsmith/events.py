"""Event conversion for LangSmith runs.

Converts LangSmith runs to Scout event types:
- LLM runs -> ModelEvent
- Tool runs -> ToolEvent
- Chain/Agent runs -> SpanBeginEvent + SpanEndEvent
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
from .extraction import extract_input_messages, extract_output, extract_tools


def _get_timestamp(run: Any, attr: str = "start_time") -> datetime:
    """Get a timestamp from a run, with fallback to datetime.min."""
    ts = getattr(run, attr, None)
    return ts if isinstance(ts, datetime) else datetime.min


async def to_model_event(run: Any) -> ModelEvent:
    """Convert LangSmith LLM run to ModelEvent.

    Args:
        run: LangSmith run with run_type == "llm"

    Returns:
        ModelEvent object
    """
    # Detect provider format for correct message extraction
    format_type = detect_provider_format(run)

    # Extract input messages
    inputs = getattr(run, "inputs", None) or {}
    input_messages = await extract_input_messages(inputs, format_type)

    # Extract output
    outputs = getattr(run, "outputs", None) or {}
    output = await extract_output(outputs, run, format_type)

    # Extract model name
    model_name = get_model_name(run)

    # Build GenerateConfig from invocation_params
    extra = getattr(run, "extra", None) or {}
    params = extra.get("invocation_params", {}) if isinstance(extra, dict) else {}
    config = GenerateConfig(
        temperature=params.get("temperature"),
        max_tokens=params.get("max_tokens") or params.get("max_output_tokens"),
        top_p=params.get("top_p"),
        stop_seqs=params.get("stop"),
    )

    return ModelEvent(
        model=model_name,
        input=input_messages,
        tools=extract_tools(run),
        tool_choice="auto",
        config=config,
        output=output,
        timestamp=_get_timestamp(run, "start_time"),
        completed=_get_timestamp(run, "end_time"),
        span_id=str(getattr(run, "parent_run_id", None) or ""),
    )


def to_tool_event(run: Any) -> ToolEvent:
    """Convert LangSmith tool run to ToolEvent.

    Args:
        run: LangSmith run with run_type == "tool"

    Returns:
        ToolEvent object
    """
    error = None
    run_error = getattr(run, "error", None)
    if run_error:
        error = ToolCallError(
            type="unknown",
            message=str(run_error),
        )

    # Extract function arguments
    inputs = getattr(run, "inputs", None) or {}
    arguments = inputs if isinstance(inputs, dict) else {}

    # Extract result
    outputs = getattr(run, "outputs", None)
    result = ""
    if outputs:
        if isinstance(outputs, dict):
            # Try to get output text
            result = str(
                outputs.get(
                    "output", outputs.get("result", outputs.get("content", outputs))
                )
            )
        else:
            result = str(outputs)

    return ToolEvent(
        id=str(getattr(run, "id", uuid.uuid4())),
        type="function",
        function=str(getattr(run, "name", "unknown_tool")),
        arguments=arguments,
        result=result,
        timestamp=_get_timestamp(run, "start_time"),
        completed=_get_timestamp(run, "end_time"),
        error=error,
        span_id=str(getattr(run, "parent_run_id", None) or ""),
    )


def to_span_begin_event(run: Any) -> SpanBeginEvent:
    """Convert LangSmith chain/agent run to SpanBeginEvent.

    Args:
        run: LangSmith run with run_type in ("chain", "agent")

    Returns:
        SpanBeginEvent object
    """
    run_type = str(getattr(run, "run_type", "span")).lower()
    name = getattr(run, "name", None) or run_type

    return SpanBeginEvent(
        id=str(getattr(run, "id", "")),
        name=str(name),
        parent_id=str(getattr(run, "parent_run_id", None) or ""),
        type="agent",  # Mark chain/agent runs as agent spans for TranscriptNodes detection
        timestamp=_get_timestamp(run, "start_time"),
        working_start=0.0,  # Required field
        metadata=_extract_run_metadata(run),
    )


def to_span_end_event(run: Any) -> SpanEndEvent:
    """Convert LangSmith run end to SpanEndEvent.

    Args:
        run: LangSmith run object

    Returns:
        SpanEndEvent object
    """
    return SpanEndEvent(
        id=str(getattr(run, "id", "")),
        timestamp=_get_timestamp(run, "end_time"),
        metadata=_extract_run_metadata(run),
    )


def to_info_event(run: Any) -> InfoEvent:
    """Convert LangSmith retriever/embedding run to InfoEvent.

    Args:
        run: LangSmith run object

    Returns:
        InfoEvent object
    """
    return InfoEvent(
        source=str(getattr(run, "name", "langsmith")),
        data=getattr(run, "inputs", None)
        or getattr(run, "outputs", None)
        or str(run.name),
        timestamp=_get_timestamp(run, "start_time"),
        metadata=_extract_run_metadata(run),
    )


def _extract_run_metadata(run: Any) -> dict[str, Any] | None:
    """Extract metadata from run for event.

    Args:
        run: LangSmith run object

    Returns:
        Metadata dictionary or None
    """
    metadata: dict[str, Any] = {}

    # Add tags
    tags = getattr(run, "tags", None)
    if tags:
        metadata["tags"] = tags

    # Add extra metadata
    extra = getattr(run, "extra", None) or {}
    if isinstance(extra, dict):
        run_metadata = extra.get("metadata", {})
        if isinstance(run_metadata, dict):
            metadata.update(run_metadata)

    return metadata if metadata else None


async def runs_to_events(runs: list[Any]) -> list[Event]:
    """Convert LangSmith runs to Scout events by type.

    Args:
        runs: List of LangSmith runs

    Returns:
        List of Scout event objects sorted chronologically
    """
    events: list[Event] = []

    for run in runs:
        run_type = str(getattr(run, "run_type", "")).lower()

        match run_type:
            case "llm":
                events.append(await to_model_event(run))
            case "tool":
                events.append(to_tool_event(run))
            case "chain" | "agent":
                events.append(to_span_begin_event(run))
                if getattr(run, "end_time", None):
                    events.append(to_span_end_event(run))
            case "retriever" | "embedding":
                events.append(to_info_event(run))
            # Skip: parser, prompt, other

    # Sort by timestamp to maintain chronological order
    events.sort(key=lambda e: e.timestamp or datetime.min)

    return events
