"""Tests for load_filtered_transcript function."""

from __future__ import annotations

import io
import json
import math
import time
from collections import Counter
from collections.abc import AsyncIterable, AsyncIterator
from typing import TYPE_CHECKING, Any, Literal, cast

import pytest

if TYPE_CHECKING:
    from conftest import CallTracker

from inspect_ai._util.asyncfiles import AsyncFilesystem
from inspect_ai.event import ToolEvent
from inspect_scout import Transcript, TranscriptInfo
from inspect_scout._transcript.json.load_filtered import load_filtered_transcript
from inspect_scout._transcript.types import EventFilter, MessageFilter
from inspect_scout._util.async_zip import AsyncZipReader


def create_json_stream(data: dict[str, Any]) -> io.BytesIO:
    """Create an async-compatible BytesIO stream from dictionary data."""
    return io.BytesIO(json.dumps(data).encode())


@pytest.mark.asyncio
async def test_basic_loading() -> None:
    """Test basic transcript loading."""
    result = await load_filtered_transcript(
        create_json_stream(
            {
                "id": "test-001",
                "metadata": {
                    "eval_name": "diffecient",
                    "eval_file_path": "some_path",
                    "variant_name": "hard",
                    "first_solve_time": 454,
                    "category": "cryptography",
                    "competition": "Sekai-2022",
                    "some_object": {"hi": "there"},
                },
                "messages": [
                    {"id": "m1", "role": "user", "content": "Hello"},
                    {"id": "m2", "role": "assistant", "content": "Hi"},
                ],
                "events": [
                    {
                        "span_id": "s1",
                        "timestamp": 1640995200.123,
                        "event": "score",
                        "score": {"value": 0.85},
                    }
                ],
                "attachments": {},
            }
        ),
        TranscriptInfo(
            transcript_id="test-001",
            source_type="test",
            source_id="source-001",
            source_uri="/test.json",
            metadata={"test": True},
        ),
        "all",
        "all",
    )

    assert isinstance(result, Transcript)
    assert result.transcript_id == "test-001"
    assert result.source_uri == "/test.json"
    assert result.metadata == {
        "test": True,
        "sample_metadata": {
            "eval_name": "diffecient",
            "eval_file_path": "some_path",
            "variant_name": "hard",
            "first_solve_time": 454,
            "category": "cryptography",
            "competition": "Sekai-2022",
            "some_object": {"hi": "there"},
        },
    }
    assert len(result.messages) == 2
    assert len(result.events) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message_filter,expected_count,expected_roles",
    [
        (None, 0, []),
        (["user"], 1, ["user"]),
        (["user", "assistant"], 2, ["user", "assistant"]),
        ("all", 3, ["user", "assistant", "system"]),
    ],
)
async def test_message_filtering(
    message_filter: MessageFilter, expected_count: int, expected_roles: list[str]
) -> None:
    """Test message filtering with different filter configurations."""
    result = await load_filtered_transcript(
        create_json_stream(
            {
                "id": "test",
                "messages": [
                    {"role": "user", "content": "User message"},
                    {"role": "assistant", "content": "Assistant message"},
                    {"role": "system", "content": "System message"},
                ],
                "events": [],
                "attachments": {},
            }
        ),
        TranscriptInfo(
            transcript_id="test",
            source_type="test",
            source_id="42",
            source_uri="/test.json",
        ),
        message_filter,
        "all",
    )

    assert len(result.messages) == expected_count
    actual_roles = [msg.role for msg in result.messages]
    assert set(actual_roles) == set(expected_roles)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "event_filter,expected_count,expected_types",
    [
        (None, 0, []),
        (["score"], 1, ["score"]),
        (["span_begin", "score"], 2, ["span_begin", "score"]),
        ("all", 3, ["span_begin", "score", "span_end"]),
    ],
)
async def test_event_filtering(
    event_filter: EventFilter, expected_count: int, expected_types: list[str]
) -> None:
    """Test event filtering with different filter configurations."""
    result = await load_filtered_transcript(
        create_json_stream(
            {
                "id": "test",
                "messages": [],
                "events": [
                    {
                        "span_id": "s1",
                        "timestamp": 1.0,
                        "event": "span_begin",
                        "id": "s1",
                        "name": "test_span",
                    },
                    {
                        "span_id": "s2",
                        "timestamp": 2.0,
                        "event": "score",
                        "score": {"value": 0.85},
                    },
                    {
                        "span_id": "s3",
                        "timestamp": 3.0,
                        "event": "span_end",
                        "id": "s1",
                    },
                ],
                "attachments": {},
            }
        ),
        TranscriptInfo(
            transcript_id="test",
            source_type="test",
            source_id="42",
            source_uri="/test.json",
        ),
        "all",
        event_filter,
    )

    assert len(result.events) == expected_count
    actual_types = [evt.event for evt in result.events]
    assert set(actual_types) == set(expected_types)


@pytest.mark.asyncio
async def test_combined_filtering() -> None:
    """Test filtering both messages and events simultaneously."""
    result = await load_filtered_transcript(
        create_json_stream(
            {
                "id": "test",
                "messages": [
                    {"role": "user", "content": "Q"},
                    {"role": "assistant", "content": "A"},
                    {"role": "system", "content": "S"},
                ],
                "events": [
                    {
                        "span_id": "s1",
                        "timestamp": 1.0,
                        "event": "score",
                        "score": {"value": 0.9},
                    },
                    {
                        "span_id": "s2",
                        "timestamp": 2.0,
                        "event": "error",
                        "error": "Test",
                    },
                ],
                "attachments": {},
            }
        ),
        TranscriptInfo(
            transcript_id="test",
            source_type="test",
            source_id="42",
            source_uri="/test.json",
        ),
        ["user"],
        ["score"],
    )

    assert len(result.messages) == 1
    assert result.messages[0].role == "user"
    assert len(result.events) == 1
    assert result.events[0].event == "score"


@pytest.mark.asyncio
async def test_attachment_resolution() -> None:
    """Test resolution of attachment references."""
    result = await load_filtered_transcript(
        create_json_stream(
            {
                "id": "test",
                "messages": [
                    {
                        "role": "user",
                        "content": "attachment://a1b2c3d4e5f678901234567890123456",
                    },
                    {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "text",
                                "text": "attachment://b2c3d4e5f67890123456789012345678",
                            }
                        ],
                    },
                ],
                "events": [
                    {
                        "span_id": "s1",
                        "timestamp": 1.0,
                        "event": "tool",
                        "id": "tool1",
                        "function": "test_function",
                        "arguments": {},
                        "result": "attachment://c3d4e5f6789012345678901234567890",
                    }
                ],
                "attachments": {
                    "a1b2c3d4e5f678901234567890123456": "Content A",
                    "b2c3d4e5f67890123456789012345678": "Content B",
                    "c3d4e5f6789012345678901234567890": "Content C",
                },
            }
        ),
        TranscriptInfo(
            transcript_id="test",
            source_type="test",
            source_id="42",
            source_uri="/test.json",
        ),
        "all",
        "all",
    )

    assert result.messages[0].content == "Content A"
    assert result.messages[1].text == "Content B"
    assert isinstance(result.events[0], ToolEvent)
    assert result.events[0].result == "Content C"


@pytest.mark.asyncio
async def test_missing_attachments() -> None:
    """Test handling of missing attachment references."""
    result = await load_filtered_transcript(
        create_json_stream(
            {
                "id": "test",
                "messages": [
                    {
                        "role": "user",
                        "content": "attachment://missingabcdef1234567890123456",
                    }
                ],
                "events": [],
                "attachments": {},
            }
        ),
        TranscriptInfo(
            transcript_id="test",
            source_type="test",
            source_id="42",
            source_uri="/test.json",
        ),
        "all",
        "all",
    )

    # Missing attachment should remain as reference
    assert "attachment://missingabcdef1234567890123456" in result.messages[0].content


@pytest.mark.asyncio
async def test_malformed_attachments() -> None:
    """Test handling of malformed attachment references."""
    result = await load_filtered_transcript(
        create_json_stream(
            {
                "id": "test",
                "messages": [
                    {"role": "user", "content": "attachment://short"},
                    {
                        "role": "user",
                        "content": "attachment://toolong123456789012345678901234567890",
                    },
                    {"role": "user", "content": "Regular text without attachments"},
                ],
                "events": [],
                "attachments": {},
            }
        ),
        TranscriptInfo(
            transcript_id="test",
            source_type="test",
            source_id="42",
            source_uri="/test.json",
        ),
        "all",
        "all",
    )

    # Malformed references should remain unchanged
    assert result.messages[0].content == "attachment://short"
    assert (
        result.messages[1].content
        == "attachment://toolong123456789012345678901234567890"
    )
    assert result.messages[2].content == "Regular text without attachments"


@pytest.mark.asyncio
async def test_unicode_and_special_chars() -> None:
    """Test handling of unicode and special characters in attachments."""
    result = await load_filtered_transcript(
        create_json_stream(
            {
                "id": "test",
                "messages": [
                    {
                        "role": "user",
                        "content": "attachment://a1b2c3d4e5f678901234567890123456",
                    }
                ],
                "events": [],
                "attachments": {
                    "a1b2c3d4e5f678901234567890123456": "Unicode: éñ中文🌟\nSpecial: @#$%"
                },
            }
        ),
        TranscriptInfo(
            transcript_id="test",
            source_type="test",
            source_id="42",
            source_uri="/test.json",
        ),
        "all",
        "all",
    )

    assert result.messages[0].content == "Unicode: éñ中文🌟\nSpecial: @#$%"


@pytest.mark.asyncio
async def test_empty_transcript() -> None:
    """Test handling of empty transcript."""
    result = await load_filtered_transcript(
        create_json_stream(
            {"id": "empty", "messages": [], "events": [], "attachments": {}}
        ),
        TranscriptInfo(
            transcript_id="empty",
            source_type="test",
            source_id="42",
            source_uri="/test.json",
        ),
        "all",
        "all",
    )

    assert len(result.messages) == 0
    assert len(result.events) == 0


class _AsyncChunkedBytes:
    """AsyncIterable that yields data in chunks, can be iterated multiple times."""

    def __init__(self, data: bytes, chunk_size: int = 64) -> None:
        self._data = data
        self._chunk_size = chunk_size

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for i in range(0, len(self._data), self._chunk_size):
            yield self._data[i : i + self._chunk_size]


@pytest.mark.asyncio
@pytest.mark.parametrize("data_type", ["io", "iterable"])
async def test_json5_nan_inf_fallback(data_type: Literal["io", "iterable"]) -> None:
    """Test fallback to json5 parser for NaN and Infinity values."""
    # JSON5 with NaN and Infinity - ijson can't parse this, so fallback triggers
    json5_content = b"""{
        "id": "json5-test",
        "metadata": {"score": NaN, "limit": Infinity, "negative": -Infinity},
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"}
        ],
        "events": [
            {"span_id": "s1", "timestamp": 1.0, "event": "score", "score": {"value": NaN}}
        ],
        "attachments": {}
    }"""

    source: io.BytesIO | AsyncIterable[bytes] = (
        _AsyncChunkedBytes(json5_content)
        if data_type == "iterable"
        else io.BytesIO(json5_content)
    )

    result = await load_filtered_transcript(
        source,
        TranscriptInfo(
            transcript_id="json5-test",
            source_type="test",
            source_id="42",
            source_uri="/test.json",
            metadata={"original": "metadata"},
        ),
        "all",
        "all",
    )

    assert result.transcript_id == "json5-test"
    assert len(result.messages) == 2
    assert len(result.events) == 1
    # Verify NaN/Inf values are parsed (they become Python float nan/inf)
    sample_meta = result.metadata["sample_metadata"]
    assert math.isnan(sample_meta["score"])
    assert math.isinf(sample_meta["limit"]) and sample_meta["limit"] > 0
    assert math.isinf(sample_meta["negative"]) and sample_meta["negative"] < 0


@pytest.mark.asyncio
async def test_json5_fallback_with_filtering() -> None:
    """Test that json5 fallback applies filtering correctly."""
    result = await load_filtered_transcript(
        io.BytesIO(
            b"""{
        "id": "filter-test",
        "metadata": {},
        "messages": [
            {"role": "user", "content": "User msg"},
            {"role": "assistant", "content": "Assistant msg"},
            {"role": "system", "content": "System msg"}
        ],
        "events": [
            {"span_id": "s1", "timestamp": 1.0, "event": "score", "score": {"value": NaN}},
            {"span_id": "s2", "timestamp": 2.0, "event": "info", "data": {"key": "value"}}
        ],
        "attachments": {}
    }"""
        ),
        TranscriptInfo(
            transcript_id="filter-test",
            source_type="test",
            source_id="42",
            source_uri="/test.json",
        ),
        ["user"],
        ["score"],
    )

    assert len(result.messages) == 1
    assert result.messages[0].role == "user"
    assert len(result.events) == 1
    assert result.events[0].event == "score"


@pytest.mark.asyncio
async def test_attachment_resolution_in_nested_structures() -> None:
    """Test attachment resolution in deeply nested structures (lists and dicts)."""
    result = await load_filtered_transcript(
        create_json_stream(
            {
                "id": "test",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "attachment://a1b2c3d4e5f678901234567890123456",
                            },
                        ],
                    }
                ],
                "events": [
                    {
                        "span_id": "s1",
                        "timestamp": 1.0,
                        "event": "tool",
                        "id": "tool1",
                        "function": "test_function",
                        "arguments": {
                            "list_input": [
                                "attachment://b2c3d4e5f67890123456789012345678",
                                {
                                    "nested_key": "attachment://c3d4e5f6789012345678901234567890"
                                },
                            ],
                            "dict_input": {
                                "key1": "attachment://d4e5f67890123456789012345678901a",
                                "nested": {
                                    "key2": "attachment://e5f67890123456789012345678901ab2"
                                },
                            },
                        },
                        "result": "test result",
                    }
                ],
                "attachments": {
                    "a1b2c3d4e5f678901234567890123456": "Resolved A",
                    "b2c3d4e5f67890123456789012345678": "Resolved B",
                    "c3d4e5f6789012345678901234567890": "Resolved C",
                    "d4e5f67890123456789012345678901a": "Resolved D",
                    "e5f67890123456789012345678901ab2": "Resolved E",
                },
            }
        ),
        TranscriptInfo(
            transcript_id="test",
            source_type="test",
            source_id="42",
            source_uri="/test.json",
        ),
        "all",
        "all",
    )

    # Check message content array resolution
    assert result.messages[0].text == "Resolved A"

    # Check event arguments resolution with lists
    assert isinstance(result.events[0], ToolEvent)
    assert cast(list[Any], result.events[0].arguments["list_input"])[0] == "Resolved B"
    assert (
        cast(
            dict[str, Any], cast(list[Any], result.events[0].arguments["list_input"])[1]
        )["nested_key"]
        == "Resolved C"
    )

    # Check event arguments resolution with nested dicts
    assert (
        cast(dict[str, Any], result.events[0].arguments["dict_input"])["key1"]
        == "Resolved D"
    )
    assert (
        cast(
            dict[str, Any],
            cast(dict[str, Any], result.events[0].arguments["dict_input"])["nested"],
        )["key2"]
        == "Resolved E"
    )


@pytest.mark.asyncio
async def test_early_exit_when_no_events_no_attachment_refs(
    call_tracker: CallTracker,
) -> None:
    """Early exit fires when events=None and messages have no attachment refs."""
    result = await load_filtered_transcript(
        create_json_stream(
            {
                "id": "test",
                "target": "the answer",
                "messages": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi"},
                ],
                "output": {},
                "scores": {"accuracy": {"value": "C", "answer": "C"}},
                "metadata": {"key": "value"},
                "events": [
                    {"span_id": "s1", "timestamp": 1.0, "event": "info", "data": {}},
                ],
                "attachments": {},
            }
        ),
        TranscriptInfo(
            transcript_id="test",
            source_type="test",
            source_id="42",
            source_uri="/test.json",
        ),
        "all",
        None,
        on_early_exit=call_tracker,
    )

    assert call_tracker.called
    assert len(result.messages) == 2
    assert not result.events
    assert result.metadata["scores"] == {"accuracy": {"value": "C", "answer": "C"}}


@pytest.mark.asyncio
async def test_early_exit_suppressed_by_attachment_refs(
    call_tracker: CallTracker,
) -> None:
    """Early exit does NOT fire when messages contain attachment refs."""
    attachment_id = "a1b2c3d4e5f678901234567890123456"

    result = await load_filtered_transcript(
        create_json_stream(
            {
                "id": "test",
                "target": "the answer",
                "messages": [
                    {"role": "user", "content": f"attachment://{attachment_id}"},
                    {"role": "assistant", "content": "Hi"},
                ],
                "output": {},
                "scores": {"accuracy": {"value": "C", "answer": "C"}},
                "metadata": {"key": "value"},
                "events": [],
                "attachments": {attachment_id: "Resolved content"},
            }
        ),
        TranscriptInfo(
            transcript_id="test",
            source_type="test",
            source_id="42",
            source_uri="/test.json",
        ),
        "all",
        None,
        on_early_exit=call_tracker,
    )

    assert not call_tracker.called
    assert len(result.messages) == 2
    assert result.messages[0].content == "Resolved content"
    assert result.metadata["scores"] == {"accuracy": {"value": "C", "answer": "C"}}


@pytest.mark.asyncio
async def test_early_exit_preserves_sample_metadata(
    call_tracker: CallTracker,
) -> None:
    """sample_metadata must be unthinned even when early exit fires (events=None)."""
    result = await load_filtered_transcript(
        create_json_stream(
            {
                "id": "test",
                "target": "the answer",
                "messages": [
                    {"role": "user", "content": "Hello"},
                ],
                "output": {},
                "scores": {"accuracy": {"value": "C", "answer": "C"}},
                "metadata": {"full_key": "full_value", "nested": {"a": 1}},
                "events": [],
                "attachments": {},
            }
        ),
        TranscriptInfo(
            transcript_id="test",
            source_type="test",
            source_id="42",
            source_uri="/test.json",
            metadata={"existing": "kept"},
        ),
        "all",
        None,
        on_early_exit=call_tracker,
    )

    assert call_tracker.called
    assert result.metadata["existing"] == "kept"
    assert result.metadata["sample_metadata"] == {
        "full_key": "full_value",
        "nested": {"a": 1},
    }
    assert result.metadata["scores"] == {"accuracy": {"value": "C", "answer": "C"}}


@pytest.mark.asyncio
async def test_target_unthinned_string() -> None:
    """`target` (string) from sample JSON replaces thinned index value in metadata."""
    result = await load_filtered_transcript(
        create_json_stream(
            {
                "id": "test",
                "target": "the full answer",
                "messages": [{"role": "user", "content": "Hello"}],
                "output": {},
                "scores": {"accuracy": {"value": "C", "answer": "C"}},
                "metadata": {},
                "events": [],
                "attachments": {},
            }
        ),
        TranscriptInfo(
            transcript_id="test",
            source_type="test",
            source_id="42",
            source_uri="/test.json",
            metadata={"target": "thinned"},
        ),
        "all",
        None,
    )

    assert result.metadata["target"] == "the full answer"
    assert result.metadata["scores"] == {"accuracy": {"value": "C", "answer": "C"}}


@pytest.mark.asyncio
async def test_target_unthinned_list() -> None:
    """`target` (list) from sample JSON replaces thinned index value in metadata."""
    result = await load_filtered_transcript(
        create_json_stream(
            {
                "id": "test",
                "target": ["answer A", "answer B"],
                "messages": [{"role": "user", "content": "Hello"}],
                "output": {},
                "scores": {"accuracy": {"value": "C", "answer": "C"}},
                "metadata": {},
                "events": [],
                "attachments": {},
            }
        ),
        TranscriptInfo(
            transcript_id="test",
            source_type="test",
            source_id="42",
            source_uri="/test.json",
            metadata={"target": "thinned"},
        ),
        "all",
        None,
    )

    assert result.metadata["target"] == ["answer A", "answer B"]
    assert result.metadata["scores"] == {"accuracy": {"value": "C", "answer": "C"}}


@pytest.mark.asyncio
async def test_scores_unthinned() -> None:
    """`scores` from sample JSON available in metadata after loading."""
    scores = {
        "accuracy": {"value": "C", "answer": "C", "explanation": "Correct"},
        "relevance": {"value": "I", "answer": "B"},
    }
    result = await load_filtered_transcript(
        create_json_stream(
            {
                "id": "test",
                "target": "the answer",
                "messages": [{"role": "user", "content": "Hello"}],
                "output": {},
                "scores": scores,
                "metadata": {},
                "events": [],
                "attachments": {},
            }
        ),
        TranscriptInfo(
            transcript_id="test",
            source_type="test",
            source_id="42",
            source_uri="/test.json",
        ),
        "all",
        None,
    )

    assert result.metadata["scores"] == scores


@pytest.mark.slow
@pytest.mark.asyncio
async def test_s3_eval_assistant_tool_filter() -> None:
    s3_path = "s3://slow-tests/swe_bench.eval"
    member_name = "samples/astropy__astropy-14309_epoch_1.json"

    info = TranscriptInfo(
        transcript_id="what id?",
        source_type="test",
        source_id="vend_fat_eval",
        source_uri=s3_path,
        metadata={"test": True},
    )

    async with AsyncFilesystem() as fs:
        async with await AsyncZipReader(fs, s3_path).open_member(member_name) as stream:
            result = await load_filtered_transcript(
                stream,
                info,
                ["assistant", "tool"],  # Filter for assistant and tool messages
                None,
            )

    assert (
        result.metadata["sample_metadata"]["hints_text"] == "cc @nstarman from #14274"
    )
    assert isinstance(result, Transcript)
    assert result.transcript_id == "what id?"
    assert result.source_uri == s3_path
    # Check that we got what we asked for and only what we asked for
    role_counts = Counter(msg.role for msg in result.messages)
    assert len(role_counts) == 2
    assert role_counts["assistant"] == 40
    assert role_counts["tool"] == 38
    assert not result.events
