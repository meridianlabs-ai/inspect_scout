import io
import json
import re
from collections.abc import AsyncIterable
from dataclasses import dataclass
from typing import IO, Any, Callable

import ijson  # type: ignore
from pydantic import JsonValue

from inspect_scout._util.async_bytes_reader import AsyncBytesReader, adapt_to_reader

from ..types import (
    EventFilter,
    MessageFilter,
    Transcript,
    TranscriptContent,
    TranscriptInfo,
)
from ..util import filter_transcript
from .reducer import (
    ATTACHMENT_PREFIX,
    ATTACHMENTS_PREFIX,
    EVENTS_ITEM_PREFIX,
    MESSAGES_ITEM_PREFIX,
    METADATA_PREFIX,
    ListProcessingConfig,
    ParseState,
    attachments_coroutine,
    event_item_coroutine,
    message_item_coroutine,
    metadata_coroutine,
)

# Pre-compiled regex patterns for performance
ATTACHMENT_PATTERN = re.compile(r"attachment://([a-f0-9]{32})")

# Section constants for prefix classification
_SECTION_OTHER = 0
_SECTION_MESSAGES = 1
_SECTION_EVENTS = 2
_SECTION_ATTACHMENTS = 3
_SECTION_METADATA = 4

_MESSAGES_ITEM_PREFIX_LEN = len(MESSAGES_ITEM_PREFIX)
_EVENTS_ITEM_PREFIX_LEN = len(EVENTS_ITEM_PREFIX)
_ATTACHMENTS_PREFIX_LEN = len(ATTACHMENTS_PREFIX)
_METADATA_PREFIX_LEN = len(METADATA_PREFIX)
_MIN_SECTION_PREFIX_LEN = min(
    _MESSAGES_ITEM_PREFIX_LEN,
    _EVENTS_ITEM_PREFIX_LEN,
    _ATTACHMENTS_PREFIX_LEN,
    _METADATA_PREFIX_LEN,
)


@dataclass(slots=True)
class RawTranscript:
    """Temporary structure for transcript data before validation."""

    id: str
    source_type: str | None
    source_id: str | None
    source_uri: str | None
    date: str | None
    task_set: str | None
    task_id: str | None
    task_repeat: int | None
    agent: str | None
    agent_args: dict[str, Any] | None
    model: str | None
    model_options: dict[str, Any] | None
    score: JsonValue
    success: bool | None
    total_time: float | None
    total_tokens: int | None
    error: str | None
    limit: str | None
    metadata: dict[str, Any]
    messages: list[dict[str, Any]]
    events: list[dict[str, Any]]


async def load_filtered_transcript(
    sample_bytes: IO[bytes] | AsyncIterable[bytes],
    t: TranscriptInfo,
    messages: MessageFilter,
    events: EventFilter,
) -> Transcript:
    """
    Transform and filter JSON sample data into a Transcript.

    Uses a two-phase approach:
    1. Stream parse and filter messages/events while collecting attachment references
    2. Resolve attachment references with actual values

    Falls back to non-streaming json5 parser if streaming fails (e.g., NaN/Inf values).

    Args:
        sample_bytes: Byte stream of JSON sample data
        t: TranscriptInfo representing the transcript to load
        messages: Filter for message roles (None=exclude all, "all"=include all,
            list=include matching)
        events: Filter for event types (None=exclude all, "all"=include all,
            list=include matching)

    Returns:
        Transcript object with filtered messages and events, resolved attachments
    """
    try:
        # Phase 1: Parse, filter, and collect attachment references
        transcript, attachment_refs = await _parse_and_filter(
            adapt_to_reader(sample_bytes), t, messages, events
        )
        # Phase 2: Resolve attachment references
        return _resolve_attachments(transcript, attachment_refs)
    except ijson.JSONError:
        # Fallback to json5 for JSON5 features (NaN, Inf, etc.)
        return await _load_with_json5_fallback(sample_bytes, t, messages, events)


async def _load_with_json5_fallback(
    sample_bytes: IO[bytes] | AsyncIterable[bytes],
    t: TranscriptInfo,
    messages: MessageFilter,
    events: EventFilter,
) -> Transcript:
    """Fallback parser using json5 for JSON5 features (NaN, Inf, etc.)."""
    if hasattr(sample_bytes, "__aiter__"):
        io_source: IO[bytes] = io.BytesIO()
        async for chunk in sample_bytes:
            io_source.write(chunk)
    else:
        io_source = sample_bytes
    io_source.seek(0)
    data = json.load(io.TextIOWrapper(io_source, encoding="utf-8"))

    return filter_transcript(
        _resolve_attachments(
            RawTranscript(
                id=t.transcript_id,
                source_type=t.source_type,
                source_id=t.source_id,
                source_uri=t.source_uri,
                date=t.date,
                task_set=t.task_set,
                task_id=t.task_id,
                task_repeat=t.task_repeat,
                agent=t.agent,
                agent_args=t.agent_args,
                model=t.model,
                model_options=t.model_options,
                score=t.score,
                success=t.success,
                total_time=t.total_time,
                total_tokens=t.total_tokens,
                error=t.error,
                limit=t.limit,
                metadata=(
                    t.metadata.copy() | {"sample_metadata": data.get("metadata", {})}
                    if data.get("metadata")
                    else t.metadata
                ),
                messages=data.get("messages", []),
                events=data.get("events", []),
            ),
            data.get("attachments", {}),
        ),
        TranscriptContent(messages, events),
    )


async def _parse_and_filter(
    sample_json: AsyncBytesReader,
    t: TranscriptInfo,
    messages_filter: MessageFilter,
    events_filter: EventFilter,
) -> tuple[RawTranscript, dict[str, str]]:
    """
    Phase 1: Single-pass stream parse, filter, and collect attachment references.

    Returns:
        Tuple of (partial transcript, attachment references dict)
    """
    # Create processing configurations
    messages_config = (
        ListProcessingConfig(
            array_item_prefix="messages.item",
            filter_field="role",
            filter_list=messages_filter,  # type:ignore
        )
        if messages_filter is not None
        else None
    )

    events_config = (
        ListProcessingConfig(
            array_item_prefix="events.item",
            filter_field="event",
            filter_list=events_filter,  # type:ignore
        )
        if events_filter is not None
        else None
    )

    state = ParseState()

    # Initialize coroutine processors
    messages_coro = (
        message_item_coroutine(state, messages_config) if messages_config else None
    )
    events_coro = event_item_coroutine(state, events_config) if events_config else None
    attachments_coro = attachments_coroutine(state)
    metadata_coro = metadata_coroutine(state)

    last_prefix = ""
    current_section = _SECTION_OTHER

    async for prefix, event, value in ijson.parse_async(sample_json, use_float=True):
        # Inline prefix classification for performance (56M+ calls in hot path)
        if prefix != last_prefix:
            last_prefix = prefix
            p_len = len(prefix)
            if p_len == 0 or prefix[0] not in ("m", "e", "a"):
                current_section = _SECTION_OTHER
            elif p_len < _MIN_SECTION_PREFIX_LEN:
                # Special case: "metadata" is 8 chars, less than min (9), but valid
                if prefix == "metadata":
                    current_section = _SECTION_METADATA
                else:
                    current_section = _SECTION_OTHER
            elif prefix[0] == "m":
                # Both "messages" and "metadata" start with "me", check 3rd char
                # (safe because we already checked p_len >= _MIN_SECTION_PREFIX_LEN)
                if (
                    p_len >= _MESSAGES_ITEM_PREFIX_LEN
                    and prefix[2] == "s"
                    and prefix[:_MESSAGES_ITEM_PREFIX_LEN] == MESSAGES_ITEM_PREFIX
                ):
                    current_section = _SECTION_MESSAGES
                elif prefix[2] == "t" and (
                    prefix == "metadata" or prefix.startswith(METADATA_PREFIX)
                ):
                    current_section = _SECTION_METADATA
                else:
                    current_section = _SECTION_OTHER
            elif (
                prefix[0] == "e"
                and p_len >= _EVENTS_ITEM_PREFIX_LEN
                and prefix[:_EVENTS_ITEM_PREFIX_LEN] == EVENTS_ITEM_PREFIX
            ):
                current_section = _SECTION_EVENTS
            elif (
                prefix[0] == "a"
                and p_len >= _ATTACHMENTS_PREFIX_LEN
                and prefix[:_ATTACHMENTS_PREFIX_LEN] == ATTACHMENTS_PREFIX
            ):
                current_section = _SECTION_ATTACHMENTS
            else:
                current_section = _SECTION_OTHER

        # Dispatch to coroutines (optimized to avoid redundant None checks)
        if current_section == _SECTION_MESSAGES and messages_coro:
            messages_coro.send((prefix, event, value))
        elif current_section == _SECTION_EVENTS and events_coro:
            events_coro.send((prefix, event, value))
        elif current_section == _SECTION_ATTACHMENTS:
            attachments_coro.send((prefix, event, value))
        elif current_section == _SECTION_METADATA:
            metadata_coro.send((prefix, event, value))

    return (
        RawTranscript(
            id=t.transcript_id,
            source_type=t.source_type,
            source_id=t.source_id,
            source_uri=t.source_uri,
            date=t.date,
            task_set=t.task_set,
            task_id=t.task_id,
            task_repeat=t.task_repeat,
            agent=t.agent,
            agent_args=t.agent_args,
            model=t.model,
            model_options=t.model_options,
            score=t.score,
            success=t.success,
            total_time=t.total_time,
            total_tokens=t.total_tokens,
            error=t.error,
            limit=t.limit,
            # t.metadata's sample_metadata is potentially thinned, so swap in the full one
            metadata=(
                t.metadata.copy() | {"sample_metadata": state.metadata}
                if state.metadata
                else t.metadata
            ),
            messages=state.messages,
            events=state.events,
        ),
        state.attachments,
    )


def _resolve_attachments(
    transcript: RawTranscript, attachments: dict[str, str]
) -> Transcript:
    """
    Phase 2: Replace attachment references with actual values.

    Args:
        transcript: Transcript with attachment references
        attachments: Dict mapping attachment IDs to their values

    Returns:
        Transcript with resolved attachment references
    """

    def resolve_string(text: str) -> str:
        """Replace attachment references in a string."""
        # Fast path: skip regex if no attachment prefix found
        if ATTACHMENT_PREFIX not in text:
            return text

        def replace_ref(match: re.Match[str]) -> str:
            attachment_id = match.group(1)
            return attachments.get(
                attachment_id, match.group(0)
            )  # Return original if not found

        return ATTACHMENT_PATTERN.sub(replace_ref, text)

    # Resolve references in messages (already raw dicts, no need to model_dump)
    resolved_messages = []
    for message_dict in transcript.messages:
        resolved_dict = _resolve_dict_attachments(message_dict, resolve_string)
        resolved_messages.append(resolved_dict)

    # Resolve references in events (already raw dicts, no need to model_dump)
    resolved_events = []
    for event_dict in transcript.events:
        resolved_dict = _resolve_dict_attachments(event_dict, resolve_string)
        resolved_events.append(resolved_dict)

    # Create new transcript with resolved data
    # Use model_validate to validate messages/events into proper types,
    # but pass metadata separately via __pydantic_private__ to preserve LazyJSONDict
    validated = Transcript.model_validate(
        {
            "transcript_id": transcript.id,
            "source_type": transcript.source_type,
            "source_id": transcript.source_id,
            "source_uri": transcript.source_uri,
            "date": transcript.date,
            "task_set": transcript.task_set,
            "task_id": transcript.task_id,
            "task_repeat": transcript.task_repeat,
            "agent": transcript.agent,
            "agent_args": transcript.agent_args,
            "model": transcript.model,
            "model_options": transcript.model_options,
            "score": transcript.score,
            "success": transcript.success,
            "total_time": transcript.total_time,
            "total_tokens": transcript.total_tokens,
            "error": transcript.error,
            "limit": transcript.limit,
            "metadata": {},  # Placeholder to avoid validation
            "messages": resolved_messages,
            "events": resolved_events,
        }
    )
    # Directly assign metadata to preserve LazyJSONDict
    validated.metadata = transcript.metadata
    return validated


def _resolve_dict_attachments(obj: Any, resolve_func: Callable[[str], str]) -> Any:
    if isinstance(obj, str):
        return resolve_func(obj)
    if isinstance(obj, dict):
        return {k: _resolve_dict_attachments(v, resolve_func) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_dict_attachments(item, resolve_func) for item in obj]

    return obj
