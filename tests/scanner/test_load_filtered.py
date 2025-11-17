"""Tests for load_filtered_transcript function."""

import io
import json
import time
from typing import Any, Counter, cast

import pytest
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
    data = {
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

    stream = create_json_stream(data)
    info = TranscriptInfo(
        id="test-001",
        source_type="test",
        source_id="source-001",
        source_uri="/test.json",
        metadata={"test": True},
    )

    result = await load_filtered_transcript(stream, info, "all", "all")

    assert isinstance(result, Transcript)
    assert result.id == "test-001"
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
    data = {
        "id": "test",
        "messages": [
            {"role": "user", "content": "User message"},
            {"role": "assistant", "content": "Assistant message"},
            {"role": "system", "content": "System message"},
        ],
        "events": [],
        "attachments": {},
    }

    stream = create_json_stream(data)
    info = TranscriptInfo(
        id="test", source_type="test", source_id="42", source_uri="/test.json"
    )

    result = await load_filtered_transcript(stream, info, message_filter, "all")

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
    data = {
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
            {"span_id": "s3", "timestamp": 3.0, "event": "span_end", "id": "s1"},
        ],
        "attachments": {},
    }

    stream = create_json_stream(data)
    info = TranscriptInfo(
        id="test", source_type="test", source_id="42", source_uri="/test.json"
    )

    result = await load_filtered_transcript(stream, info, "all", event_filter)

    assert len(result.events) == expected_count
    actual_types = [evt.event for evt in result.events]
    assert set(actual_types) == set(expected_types)


@pytest.mark.asyncio
async def test_combined_filtering() -> None:
    """Test filtering both messages and events simultaneously."""
    data = {
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
            {"span_id": "s2", "timestamp": 2.0, "event": "error", "error": "Test"},
        ],
        "attachments": {},
    }

    stream = create_json_stream(data)
    info = TranscriptInfo(
        id="test", source_type="test", source_id="42", source_uri="/test.json"
    )

    result = await load_filtered_transcript(stream, info, ["user"], ["score"])

    assert len(result.messages) == 1
    assert result.messages[0].role == "user"
    assert len(result.events) == 1
    assert result.events[0].event == "score"


@pytest.mark.asyncio
async def test_attachment_resolution() -> None:
    """Test resolution of attachment references."""
    data = {
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

    stream = create_json_stream(data)
    info = TranscriptInfo(
        id="test", source_type="test", source_id="42", source_uri="/test.json"
    )

    result = await load_filtered_transcript(stream, info, "all", "all")

    assert result.messages[0].content == "Content A"
    assert result.messages[1].text == "Content B"
    assert isinstance(result.events[0], ToolEvent)
    assert result.events[0].result == "Content C"


@pytest.mark.asyncio
async def test_missing_attachments() -> None:
    """Test handling of missing attachment references."""
    data = {
        "id": "test",
        "messages": [
            {"role": "user", "content": "attachment://missingabcdef1234567890123456"}
        ],
        "events": [],
        "attachments": {},
    }

    stream = create_json_stream(data)
    info = TranscriptInfo(
        id="test", source_type="test", source_id="42", source_uri="/test.json"
    )

    result = await load_filtered_transcript(stream, info, "all", "all")

    # Missing attachment should remain as reference
    assert "attachment://missingabcdef1234567890123456" in result.messages[0].content


@pytest.mark.asyncio
async def test_malformed_attachments() -> None:
    """Test handling of malformed attachment references."""
    data = {
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

    stream = create_json_stream(data)
    info = TranscriptInfo(
        id="test", source_type="test", source_id="42", source_uri="/test.json"
    )

    result = await load_filtered_transcript(stream, info, "all", "all")

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
    data = {
        "id": "test",
        "messages": [
            {"role": "user", "content": "attachment://a1b2c3d4e5f678901234567890123456"}
        ],
        "events": [],
        "attachments": {
            "a1b2c3d4e5f678901234567890123456": "Unicode: éñ中文🌟\nSpecial: @#$%"
        },
    }

    stream = create_json_stream(data)
    info = TranscriptInfo(
        id="test", source_type="test", source_id="42", source_uri="/test.json"
    )

    result = await load_filtered_transcript(stream, info, "all", "all")

    assert result.messages[0].content == "Unicode: éñ中文🌟\nSpecial: @#$%"


@pytest.mark.asyncio
async def test_empty_transcript() -> None:
    """Test handling of empty transcript."""
    data = {"id": "empty", "messages": [], "events": [], "attachments": {}}

    stream = create_json_stream(data)
    info = TranscriptInfo(
        id="empty", source_type="test", source_id="42", source_uri="/test.json"
    )

    result = await load_filtered_transcript(stream, info, "all", "all")

    assert len(result.messages) == 0
    assert len(result.events) == 0


@pytest.mark.asyncio
async def test_parse_and_filter() -> None:
    """Test filtering of messages and events."""
    data = {
        "id": "test",
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "system", "content": "System"},
        ],
        "events": [
            {
                "span_id": "s1",
                "timestamp": 1.0,
                "event": "score",
                "score": {"value": 0.9},
            },
            {"span_id": "s2", "timestamp": 2.0, "event": "error", "error": "Error"},
        ],
        "attachments": {},
    }

    stream = create_json_stream(data)
    info = TranscriptInfo(
        id="test",
        source_type="test",
        source_id="42",
        source_uri="/test.json",
        metadata={"key": "value"},
    )

    transcript = await load_filtered_transcript(stream, info, ["user"], ["score"])

    assert isinstance(transcript, Transcript)
    assert transcript.id == "test"
    assert transcript.metadata == {"key": "value"}
    assert len(transcript.messages) == 1
    assert transcript.messages[0].role == "user"
    assert len(transcript.events) == 1
    assert transcript.events[0].event == "score"


@pytest.mark.asyncio
async def test_attachment_resolution_in_nested_structures() -> None:
    """Test attachment resolution in deeply nested structures (lists and dicts)."""
    data = {
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
                        {"nested_key": "attachment://c3d4e5f6789012345678901234567890"},
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

    stream = create_json_stream(data)
    info = TranscriptInfo(
        id="test", source_type="test", source_id="42", source_uri="/test.json"
    )

    result = await load_filtered_transcript(stream, info, "all", "all")

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


@pytest.mark.slow
@pytest.mark.asyncio
async def test_s3_eval_assistant_tool_filter() -> None:
    s3_path = "s3://slow-tests/swe_bench.eval"
    member_name = "samples/astropy__astropy-14309_epoch_1.json"

    info = TranscriptInfo(
        id="what id?",
        source_type="test",
        source_id="vend_fat_eval",
        source_uri=s3_path,
        metadata={"test": True},
    )

    async with AsyncFilesystem() as fs:
        start = time.time()
        async with AsyncZipReader(fs, s3_path).open_member(member_name) as stream:
            result = await load_filtered_transcript(
                stream,
                info,
                ["assistant", "tool"],  # Filter for assistant and tool messages
                None,
            )
        duration = time.time() - start
        print(f"Parse took {duration:.3f}s")

    assert isinstance(result, Transcript)
    assert result.id == "what id?"
    assert result.source_uri == s3_path
    # Check that we got what we asked for and only what we asked for
    role_counts = Counter(msg.role for msg in result.messages)
    assert len(role_counts) == 2
    assert role_counts["assistant"] == 40
    assert role_counts["tool"] == 38
    assert not result.events
