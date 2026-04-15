"""Codex transcript import functionality."""

from __future__ import annotations

import json
from datetime import datetime
from logging import getLogger
from os import PathLike
from pathlib import Path
from typing import TYPE_CHECKING, Any, AsyncIterator

from inspect_ai.event import Event, ModelEvent
from inspect_ai.model import stable_message_ids
from inspect_swe._codex_cli._events import process_parsed_events
from inspect_swe._codex_cli._events.models import (
    SessionMetaRecord,
    TurnContextRecord,
    extract_session_metadata,
    is_subagent_session,
    parse_event,
)
from inspect_swe._codex_cli._events.util import parse_timestamp
from pydantic import ValidationError

from .client import (
    CODEX_SOURCE_TYPE,
    discover_rollout_files,
    get_source_uri,
    peek_session_id,
    read_jsonl_records,
)

if TYPE_CHECKING:
    from inspect_scout import Transcript

logger = getLogger(__name__)


async def codex(
    path: str | PathLike[str] | None = None,
    session_id: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    limit: int | None = None,
) -> AsyncIterator["Transcript"]:
    """Read transcripts from Codex rollout files.

    Args:
        path: Path to a rollout file or directory containing rollout files. If
            ``None``, scans ``~/.codex/sessions/`` recursively.
        session_id: Specific Codex session ID to import.
        from_time: Only fetch rollout files modified on or after this time.
        to_time: Only fetch rollout files modified before this time.
        limit: Maximum number of transcripts to yield.

    Yields:
        Transcript objects ready for insertion into the Scout transcript database.
    """
    rollout_files = discover_rollout_files(path, session_id, from_time, to_time)
    if not rollout_files:
        logger.info("No Codex rollout files found")
        return

    count = 0
    for rollout_file in rollout_files:
        if limit is not None and count >= limit:
            return

        raw_events = read_jsonl_records(rollout_file)
        if not raw_events:
            continue

        parsed_events = _parse_events_safely(raw_events)
        if not parsed_events or is_subagent_session(parsed_events):
            continue

        transcript = await _create_transcript(
            rollout_file,
            raw_events=raw_events,
            parsed_events=parsed_events,
        )
        if transcript is None:
            continue

        yield transcript
        count += 1


async def _create_transcript(
    rollout_file: Path,
    *,
    raw_events: list[dict[str, Any]],
    parsed_events: list[Any],
) -> "Transcript" | None:
    """Create a Scout transcript from a Codex rollout file."""
    from inspect_ai.event import timeline_build

    from inspect_scout import Transcript
    from inspect_scout._transcript.messages import span_messages

    scout_events: list[Event] = []
    async for event in process_parsed_events(
        parsed_events, session_file=rollout_file
    ):
        scout_events.append(event)

    if not scout_events:
        return None

    timeline = timeline_build(scout_events)
    messages = span_messages(timeline.root, compaction="all")
    if not messages:
        return None

    apply_ids = stable_message_ids()
    for event in scout_events:
        if isinstance(event, ModelEvent):
            apply_ids(event)
    apply_ids(messages)

    session_metadata = _extract_session_metadata(
        raw_events, parsed_events, rollout_file
    )
    model_name = _extract_model_name(scout_events, parsed_events)
    session_id = _session_id(session_metadata, rollout_file)
    total_tokens = _sum_total_tokens(scout_events)
    total_time = _total_time_seconds(timeline.root, scout_events)

    return Transcript(
        transcript_id=session_id,
        source_type=CODEX_SOURCE_TYPE,
        source_id=session_id,
        source_uri=get_source_uri(rollout_file),
        date=session_metadata.get("session_timestamp"),
        task_set=session_metadata.get("cwd"),
        task_id=session_id,
        task_repeat=1,
        agent="codex",
        agent_args=None,
        model=model_name,
        model_options=None,
        score=None,
        success=None,
        message_count=len(messages),
        total_tokens=total_tokens if total_tokens > 0 else None,
        total_time=total_time if total_time > 0 else None,
        error=None,
        limit=None,
        messages=messages,
        events=scout_events,
        metadata=session_metadata,
    )


def _extract_session_metadata(
    raw_events: list[dict[str, Any]],
    parsed_events: list[Any],
    rollout_file: Path,
) -> dict[str, Any]:
    """Extract selected session metadata from a rollout file."""
    metadata: dict[str, Any] = {
        "rollout_path": str(rollout_file.resolve()),
    }

    raw_session_meta = _raw_session_meta(raw_events)
    if raw_session_meta is not None:
        raw_payload = raw_session_meta.get("payload")
        if isinstance(raw_payload, dict):
            source = raw_payload.get("source")
            if isinstance(source, dict):
                source = json.dumps(source, sort_keys=True)
            session_timestamp = parse_timestamp(
                _as_optional_str(raw_payload.get("timestamp"))
            )
            metadata.update(
                {
                    "session_id": _as_optional_str(raw_payload.get("id")),
                    "session_timestamp": (
                        session_timestamp.isoformat()
                        if session_timestamp is not None
                        else _as_optional_str(raw_session_meta.get("timestamp"))
                    ),
                    "cwd": _as_optional_str(raw_payload.get("cwd")),
                    "originator": _as_optional_str(raw_payload.get("originator")),
                    "cli_version": _as_optional_str(raw_payload.get("cli_version")),
                    "source": source if isinstance(source, str) else None,
                }
            )

    metadata.update(extract_session_metadata(parsed_events))

    if "session_id" not in metadata:
        metadata["session_id"] = peek_session_id(rollout_file) or rollout_file.stem
    if "session_timestamp" not in metadata:
        metadata["session_timestamp"] = _first_timestamp(parsed_events)

    return {key: value for key, value in metadata.items() if value is not None}


def _extract_model_name(
    scout_events: list[Event],
    parsed_events: list[Any],
) -> str | None:
    """Extract the primary model name from processed events."""
    for event in scout_events:
        if isinstance(event, ModelEvent) and event.model:
            return event.model

    model_provider: str | None = None
    model_name: str | None = None
    for event in parsed_events:
        if isinstance(event, SessionMetaRecord):
            model_provider = event.payload.model_provider
        elif isinstance(event, TurnContextRecord):
            model_name = event.payload.model or model_name

    if model_name is None:
        return None
    if model_provider is None:
        return model_name
    return f"{model_provider}/{model_name}"


def _sum_total_tokens(events: list[Event]) -> int:
    """Sum token usage across model events."""
    total_tokens = 0
    for event in events:
        if not isinstance(event, ModelEvent):
            continue
        if event.output is None or event.output.usage is None:
            continue
        total_tokens += event.output.usage.total_tokens or 0
    return total_tokens


def _total_time_seconds(root: Any, events: list[Event]) -> float:
    """Compute total active wall-clock time for a transcript."""
    if getattr(root, "content", None):
        wall_clock = (root.end_time() - root.start_time()).total_seconds()
        return float(wall_clock - float(root.idle_time()))

    timestamps = [
        event.timestamp for event in events if getattr(event, "timestamp", None)
    ]
    if len(timestamps) < 2:
        return 0.0
    return (max(timestamps) - min(timestamps)).total_seconds()


def _first_timestamp(parsed_events: list[Any]) -> str | None:
    """Return the first timestamp found in parsed events."""
    for event in parsed_events:
        timestamp = parse_timestamp(getattr(event, "timestamp", None))
        if timestamp is not None:
            return timestamp.isoformat()
    return None


def _raw_session_meta(raw_events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the first raw session_meta record from a rollout file."""
    for event in raw_events:
        if event.get("type") == "session_meta":
            return event
    return None


def _as_optional_str(value: Any) -> str | None:
    """Return a string value when present and non-empty."""
    if isinstance(value, str) and value:
        return value
    return None


def _session_id(session_metadata: dict[str, Any], rollout_file: Path) -> str:
    """Resolve the transcript session ID."""
    session_id = session_metadata.get("session_id")
    if isinstance(session_id, str) and session_id:
        return session_id
    return peek_session_id(rollout_file) or rollout_file.stem


def _parse_events_safely(raw_events: list[dict[str, Any]]) -> list[Any]:
    """Parse rollout records, skipping unsupported record variants."""
    parsed_events: list[Any] = []

    for raw_event in raw_events:
        normalized = _normalize_raw_event(raw_event)
        try:
            event = parse_event(normalized)
        except ValidationError:
            payload = normalized.get("payload")
            payload_type = payload.get("type") if isinstance(payload, dict) else None
            logger.debug(
                "Skipping unsupported Codex record type=%s payload_type=%s",
                normalized.get("type"),
                payload_type,
            )
            continue
        if event is not None:
            parsed_events.append(event)

    return parsed_events


def _normalize_raw_event(raw_event: dict[str, Any]) -> dict[str, Any]:
    """Normalize newer Codex rollout records into the shared parser shape."""
    if raw_event.get("type") != "response_item":
        return raw_event

    payload = raw_event.get("payload")
    if not isinstance(payload, dict):
        return raw_event

    payload_type = payload.get("type")
    if payload_type == "custom_tool_call":
        return raw_event | {
            "payload": {
                "type": "function_call",
                "name": payload.get("name"),
                "call_id": payload.get("call_id"),
                "arguments": _normalize_custom_tool_arguments(payload.get("input")),
            }
        }
    if payload_type == "custom_tool_call_output":
        return raw_event | {
            "payload": {
                "type": "function_call_output",
                "call_id": payload.get("call_id"),
                "output": _normalize_custom_tool_output(payload.get("output")),
            }
        }

    return raw_event


def _normalize_custom_tool_arguments(value: Any) -> dict[str, Any]:
    """Normalize a custom tool input payload into tool arguments."""
    if isinstance(value, dict):
        return value
    if value is None:
        return {}
    return {"input": value}


def _normalize_custom_tool_output(value: Any) -> Any:
    """Extract the user-facing result from a custom tool output payload."""
    if not isinstance(value, str):
        return value

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return value

    if isinstance(parsed, dict) and "output" in parsed:
        return parsed["output"]
    return value
