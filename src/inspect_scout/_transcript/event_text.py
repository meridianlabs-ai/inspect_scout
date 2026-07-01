"""Event-to-string rendering shared by the grep and llm scanners."""

import json
from logging import getLogger

from inspect_ai._util.logger import warn_once
from inspect_ai.event import (
    ApprovalEvent,
    ErrorEvent,
    Event,
    InfoEvent,
    InputEvent,
    LoggerEvent,
    ModelEvent,
    SampleLimitEvent,
    SandboxEvent,
    ScoreEvent,
    ToolEvent,
)

logger = getLogger(__name__)


def event_as_str(event: Event) -> str | None:
    """Convert an Event to a text representation, or None if unsupported."""
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
        case "score":
            return _score_event_as_str(event)
        case "sample_limit":
            return _sample_limit_event_as_str(event)
        case "input":
            return _input_event_as_str(event)
        case "sandbox":
            return _sandbox_event_as_str(event)
        case _:
            warn_once(
                logger,
                f"event_as_str: unsupported event type '{event.event}' - skipping",
            )
            return None


def _model_event_as_str(event: Event) -> str | None:
    if not isinstance(event, ModelEvent):
        return None
    completion = event.output.completion
    if completion:
        return f"MODEL:\n{completion}\n"
    return None


def _tool_event_as_str(event: Event) -> str | None:
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
    if not isinstance(event, ErrorEvent):
        return None
    return f"ERROR:\n{event.error.message}\n"


def _info_event_as_str(event: Event) -> str | None:
    if not isinstance(event, InfoEvent):
        return None
    if event.data is None:
        return None
    if isinstance(event.data, str):
        data_str = event.data
    else:
        data_str = json.dumps(event.data, default=str)
    source_part = f" ({event.source})" if event.source else ""
    return f"INFO{source_part}:\n{data_str}\n"


def _logger_event_as_str(event: Event) -> str | None:
    if not isinstance(event, LoggerEvent):
        return None
    return f"LOG ({event.message.level}):\n{event.message.message}\n"


def _approval_event_as_str(event: Event) -> str | None:
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


def _score_event_as_str(event: Event) -> str | None:
    if not isinstance(event, ScoreEvent):
        return None
    score = event.score
    header = [f"value={score.value}"]
    if event.target is not None:
        target = (
            ", ".join(event.target) if isinstance(event.target, list) else event.target
        )
        header.append(f"target={target}")
    if event.intermediate:
        header.append("intermediate")
    if score.answer:
        header.append(f"answer={score.answer}")
    result = f"SCORE ({event.scorer or 'unknown'}): {' '.join(header)}"
    if score.explanation:
        result += f"\n  explanation: {score.explanation}"
    return result + "\n"


def _sample_limit_event_as_str(event: Event) -> str | None:
    if not isinstance(event, SampleLimitEvent):
        return None
    return f"LIMIT ({event.type}): {event.message}\n"


def _input_event_as_str(event: Event) -> str | None:
    if not isinstance(event, InputEvent):
        return None
    return f"INPUT:\n{event.input}\n"


def _sandbox_event_as_str(event: Event) -> str | None:
    if not isinstance(event, SandboxEvent):
        return None
    detail = event.cmd if event.cmd is not None else event.file
    suffix = f": {detail}" if detail else ""
    return f"SANDBOX ({event.action}){suffix}\n"
