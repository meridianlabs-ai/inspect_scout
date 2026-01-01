"""Event to string conversion for grep_scanner pattern matching."""

import json
from logging import getLogger

from inspect_ai._util.logger import warn_once
from inspect_ai.event import Event

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
    # ModelEvent has output.completion
    if hasattr(event, "output") and event.output is not None:
        completion = getattr(event.output, "completion", None)
        if completion:
            return f"MODEL:\n{completion}\n"
    return None


def _tool_event_as_str(event: Event) -> str | None:
    """Format ToolEvent with function, arguments, and result."""
    # ToolEvent has function, arguments, result, error
    function = getattr(event, "function", "unknown")
    arguments = getattr(event, "arguments", {})
    result = getattr(event, "result", None)
    error = getattr(event, "error", None)

    parts = [f"TOOL ({function}):"]

    if arguments:
        if isinstance(arguments, dict):
            args_text = "\n".join(f"  {k}: {v}" for k, v in arguments.items())
            parts.append(f"Arguments:\n{args_text}")
        else:
            parts.append(f"Arguments: {arguments}")

    if result is not None:
        result_str = str(result) if not isinstance(result, str) else result
        parts.append(f"Result: {result_str}")

    if error is not None:
        error_msg = getattr(error, "message", str(error))
        parts.append(f"Error: {error_msg}")

    return "\n".join(parts) + "\n"


def _error_event_as_str(event: Event) -> str | None:
    """Extract error message from ErrorEvent."""
    # ErrorEvent has error (EvalError with message)
    error = getattr(event, "error", None)
    if error is not None:
        message = getattr(error, "message", str(error))
        return f"ERROR:\n{message}\n"
    return None


def _info_event_as_str(event: Event) -> str | None:
    """Format InfoEvent data as string or JSON."""
    # InfoEvent has source, data
    source = getattr(event, "source", None)
    data = getattr(event, "data", None)

    if data is None:
        return None

    # Convert data to string - JSON dump if not already a string
    if isinstance(data, str):
        data_str = data
    else:
        data_str = json.dumps(data, default=str)

    source_part = f" ({source})" if source else ""
    return f"INFO{source_part}:\n{data_str}\n"


def _logger_event_as_str(event: Event) -> str | None:
    """Extract log message from LoggerEvent."""
    # LoggerEvent has message (LoggingMessage with message, level)
    msg = getattr(event, "message", None)
    if msg is not None:
        level = getattr(msg, "level", "info")
        message = getattr(msg, "message", str(msg))
        return f"LOG ({level}):\n{message}\n"
    return None


def _approval_event_as_str(event: Event) -> str | None:
    """Format ApprovalEvent with message, tool call, and decision."""
    # ApprovalEvent has message, call (ToolCall), decision, explanation
    message = getattr(event, "message", "")
    call = getattr(event, "call", None)
    decision = getattr(event, "decision", "unknown")
    explanation = getattr(event, "explanation", None)

    parts = [f"APPROVAL ({decision}):"]

    if message:
        parts.append(f"Message: {message}")

    if call is not None:
        function = getattr(call, "function", "unknown")
        arguments = getattr(call, "arguments", {})
        parts.append(f"Tool: {function}")
        if arguments:
            if isinstance(arguments, dict):
                args_text = ", ".join(f"{k}={v}" for k, v in arguments.items())
                parts.append(f"Args: {args_text}")
            else:
                parts.append(f"Args: {arguments}")

    if explanation:
        parts.append(f"Explanation: {explanation}")

    return "\n".join(parts) + "\n"
