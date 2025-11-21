import json
from functools import reduce
from typing import Any, Iterable, TypeVar

from inspect_ai.event._event import Event
from inspect_ai.model._chat_message import ChatMessage, ChatMessageBase

from .types import (
    EventFilter,
    MessageFilter,
    Transcript,
    TranscriptContent,
)


class LazyJSONDict(dict[str, Any]):
    """Dictionary that lazily parses JSON strings on first access.

    Stores raw string values from the database and only attempts JSON
    deserialization when a key is accessed via __getitem__ or get().
    Parsed results are cached in-place to avoid re-parsing.

    Two modes of operation:
    1. Automatic detection (default): Parses any string starting with '{' or '['
    2. Selective parsing: When json_keys is provided, only parses specified keys

    Note: Iteration methods like .items() and .values() return raw values
    without triggering parsing. Only direct key access triggers parsing.

    Examples:
        Automatic JSON detection:
        >>> data = LazyJSONDict({"config": '{"key": "value"}', "name": "test"})
        >>> data["config"]  # Triggers parsing, returns dict
        {'key': 'value'}
        >>> data["name"]  # Returns string as-is
        'test'

        Selective parsing (more efficient when you know which keys are JSON):
        >>> data = LazyJSONDict(
        ...     {"config": '{"key": "value"}', "data": '[1,2,3]', "name": "test"},
        ...     json_keys=["config", "data"]
        ... )
        >>> data["config"]  # Triggers parsing, returns dict
        {'key': 'value'}
        >>> data["name"]  # Returns string as-is (not in json_keys)
        'test'
    """

    def __init__(
        self,
        data: dict[str, Any] | None = None,
        json_keys: set[str] | list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize lazy JSON dictionary.

        Args:
            data: Initial dictionary data. Can also pass dict data as first
                positional arg for compatibility with dict() constructor.
            json_keys: Optional set or list of keys that should be parsed as JSON.
                If None (default), automatically detects JSON by checking if strings
                start with '{' or '['. If provided, only parses specified keys.
            **kwargs: Additional key-value pairs to include in the dict.
        """
        if data is not None:
            super().__init__(data, **kwargs)
        else:
            super().__init__(**kwargs)

        # Track which keys have been parsed to avoid re-checking
        self._parsed: set[str] = set()

        # Store JSON keys as a set for O(1) lookup (None means use auto-detection)
        self._json_keys: set[str] | None = (
            set(json_keys) if json_keys is not None else None
        )

    def __getitem__(self, key: str) -> Any:
        """Get value, lazily parsing JSON strings on first access."""
        # If already parsed, return the (possibly modified) value
        if key in self._parsed:
            return super().__getitem__(key)

        # Mark as parsed to avoid re-checking
        self._parsed.add(key)

        # Get raw value
        value = super().__getitem__(key)

        # Determine if we should try to parse this value
        should_parse = self._should_parse_value(key, value)

        if should_parse:
            try:
                parsed = json.loads(value)
                # Update the dict with parsed value in-place
                super().__setitem__(key, parsed)
                return parsed
            except (json.JSONDecodeError, ValueError):
                # Not valid JSON, return as-is
                return value

        # Not a candidate for parsing, return as-is
        return value

    def _should_parse_value(self, key: str, value: Any) -> bool:
        """Determine if a value should be parsed as JSON.

        Args:
            key: The dictionary key being accessed.
            value: The raw value to potentially parse.

        Returns:
            True if the value should be parsed as JSON, False otherwise.
        """
        if not isinstance(value, str):
            return False

        if self._json_keys is None:
            # Auto-detection mode: check if string looks like JSON
            return bool(value and value[0] in ("{", "["))
        else:
            # Selective mode: only parse specified keys
            return key in self._json_keys

    def get(self, key: str, default: Any = None) -> Any:
        """Get with default value, applying lazy parsing."""
        try:
            return self[key]
        except KeyError:
            return default

    def to_json_string(self) -> str:
        """Serialize to JSON string without parsing unparsed JSON values.

        Creates a JSON string representation efficiently by:
        - For parsed keys: serializing the current value with json.dumps
        - For unparsed keys with raw JSON strings: inserting them directly
        - For unparsed keys with non-JSON values: serializing with json.dumps

        This avoids unnecessary parse→serialize round-trips for JSON strings
        that are going to end up as JSON strings in the output anyway.

        Returns:
            JSON string representation of the dictionary.
        """
        if not self:
            return "{}"

        parts = []
        for key in self.keys():
            # Safely encode the key
            encoded_key = json.dumps(key, ensure_ascii=False)

            if key in self._parsed:
                # Already parsed - serialize the current value
                value = super().__getitem__(key)
                encoded_value = json.dumps(
                    value, ensure_ascii=False, separators=(",", ":")
                )
            else:
                # Not yet parsed - use raw value directly
                raw_value = super().__getitem__(key)

                # If raw value is a JSON string, insert it directly (no parse/serialize round-trip)
                # These strings come from json.dumps originally, so they're valid JSON
                if (
                    isinstance(raw_value, str)
                    and raw_value
                    and raw_value[0] in ("{", "[")
                ):
                    encoded_value = raw_value
                else:
                    # Not a JSON string - encode it normally
                    encoded_value = json.dumps(
                        raw_value, ensure_ascii=False, separators=(",", ":")
                    )

            parts.append(f"{encoded_key}:{encoded_value}")

        return "{" + ",".join(parts) + "}"


def union_transcript_contents(
    contents: Iterable[TranscriptContent],
) -> TranscriptContent:
    """Create the narrowest TranscriptContent that satisfies all passed TranscriptContent's.

    Each scanner has its own TranscriptContent filter describing what data it needs
    from the transcript. This function combines these individual scanner requirements
    into a single filter that represents the union of all needs. The goal is to
    create the narrowest possible filter that still satisfies every scanner's
    requirements, minimizing the amount of data loaded from large transcripts.

    Args:
        contents: Iterable of TranscriptContent objects, each representing a
            scanner's data requirements.

    Returns:
        A new TranscriptContent containing the union of all scanner filters.
    """
    return reduce(
        _union_contents,
        contents,
        TranscriptContent(None, None),
    )


def filter_transcript(transcript: Transcript, content: TranscriptContent) -> Transcript:
    """Filter a transcript based on specified content filters.

    Args:
        transcript: The original transcript to filter.
        content: Content filters specifying which messages and events to include.

    Returns:
        A new Transcript with filtered messages and events based on the content specification.
    """
    # Use model_construct to avoid materializing LazyJSONDict metadata
    return Transcript.model_construct(
        transcript_id=transcript.transcript_id,
        source_type=transcript.source_type,
        source_id=transcript.source_id,
        source_uri=transcript.source_uri,
        metadata=transcript.metadata,
        messages=filter_list(transcript.messages, content.messages),
        events=filter_list(transcript.events, content.events),
    )


def _union_contents(a: TranscriptContent, b: TranscriptContent) -> TranscriptContent:
    return TranscriptContent(
        _union_filters(a.messages, b.messages), _union_filters(a.events, b.events)
    )


T = TypeVar("T", MessageFilter, EventFilter)


def _union_filters(a: T, b: T) -> T:
    if a == "all" or b == "all":
        return "all"
    if a is None:
        return b
    if b is None:
        return a
    # At this point, both a and b are non-None and non-"all".
    return list(set(a) | set(b))


TMessageOrEvent = TypeVar("TMessageOrEvent", ChatMessage, Event)


def filter_list(
    items: list[TMessageOrEvent],
    filter_value: MessageFilter | EventFilter,
) -> list[TMessageOrEvent]:
    return (
        []
        if filter_value is None
        else (
            items
            if filter_value == "all"
            else [item for item in items if _matches_filter(item, filter_value)]
        )
    )


def _matches_filter(
    obj: ChatMessage | Event, filter: MessageFilter | EventFilter
) -> bool:
    if filter is None:
        return False
    if filter == "all":
        return True

    attr = (
        getattr(obj, "role", None)
        if isinstance(obj, ChatMessageBase)
        else getattr(obj, "event", None)
    )
    assert isinstance(attr, str)
    return attr in filter
