"""Event to string conversion for grep_scanner pattern matching."""

import json
from logging import getLogger

from inspect_ai._util.logger import warn_once
from inspect_ai.event import (
    ApprovalEvent,
    ErrorEvent,
    Event,
    InfoEvent,
    LoggerEvent,
    ModelEvent,
    ToolEvent,
)

logger = getLogger(__name__)


def event_as_str(event: Event) -> str | None:
    """Convert an Event to a searchable string representation.

    Args:
        event: The Event to convert.

    Returns:
        A formatted string representation, or None if the event type
        is not supported or has no text content.
    """
    match event.event:
        case "model":
            return _model_event_as_str(event)
        case "tool":
            return _tool_event_as_str(event)
        case "error":
            return _error_event_as_str(event)
        case "info":
            return _info_event_as_str(event)
        case "logger":
            return _logger_event_as_str(event)
        case "approval":
            return _approval_event_as_str(event)
        case _:
            warn_once(
                logger,
                f"event_as_str: unsupported event type '{event.event}' - skipping",
            )
            return None


def _model_event_as_str(event: Event) -> str | None:
    """Extract completion text from ModelEvent."""
    if not isinstance(event, ModelEvent):
        return None
    completion = event.output.completion
    if completion:
        return f"MODEL:\n{completion}\n"
    return None


def _tool_event_as_str(event: Event) -> str | None:
    """Format ToolEvent with function, arguments, and result."""
    if not isinstance(event, ToolEvent):
        return None

    parts = [f"TOOL ({event.function}):"]

    if event.arguments:
        if isinstance(event.arguments, dict):
            args_text = "\n".join(f"  {k}: {v}" for k, v in event.arguments.items())
            parts.append(f"Arguments:\n{args_text}")
        else:
            parts.append(f"Arguments: {event.arguments}")

    if event.result is not None:
        result_str = (
            str(event.result) if not isinstance(event.result, str) else event.result
        )
        parts.append(f"Result: {result_str}")

    if event.error is not None:
        parts.append(f"Error: {event.error.message}")

    return "\n".join(parts) + "\n"


def _error_event_as_str(event: Event) -> str | None:
    """Extract error message from ErrorEvent."""
    if not isinstance(event, ErrorEvent):
        return None
    return f"ERROR:\n{event.error.message}\n"


def _info_event_as_str(event: Event) -> str | None:
    """Format InfoEvent data as string or JSON."""
    if not isinstance(event, InfoEvent):
        return None

    if event.data is None:
        return None

    # Convert data to string - JSON dump if not already a string
    if isinstance(event.data, str):
        data_str = event.data
    else:
        data_str = json.dumps(event.data, default=str)

    source_part = f" ({event.source})" if event.source else ""
    return f"INFO{source_part}:\n{data_str}\n"


def _logger_event_as_str(event: Event) -> str | None:
    """Extract log message from LoggerEvent."""
    if not isinstance(event, LoggerEvent):
        return None
    return f"LOG ({event.message.level}):\n{event.message.message}\n"


def _approval_event_as_str(event: Event) -> str | None:
    """Format ApprovalEvent with message, tool call, and decision."""
    if not isinstance(event, ApprovalEvent):
        return None

    parts = [f"APPROVAL ({event.decision}):"]

    if event.message:
        parts.append(f"Message: {event.message}")

    call = event.call
    parts.append(f"Tool: {call.function}")
    if call.arguments:
        if isinstance(call.arguments, dict):
            args_text = ", ".join(f"{k}={v}" for k, v in call.arguments.items())
            parts.append(f"Args: {args_text}")
        else:
            parts.append(f"Args: {call.arguments}")

    if event.explanation:
        parts.append(f"Explanation: {event.explanation}")

    return "\n".join(parts) + "\n"
