"""Tests to verify LazyJSONDict survives through the entire transcript pipeline."""

import json
from pathlib import Path

import pytest
import pytest_asyncio
from inspect_scout._transcript.database.parquet import ParquetTranscriptsDB
from inspect_scout._transcript.eval_log import EvalLogTranscriptsDB
from inspect_scout._transcript.types import Transcript, TranscriptContent
from inspect_scout._transcript.util import LazyJSONDict, filter_transcript


@pytest.mark.asyncio
async def test_lazy_dict_survives_parquet_select(
    parquet_db_with_nested_metadata: ParquetTranscriptsDB,
) -> None:
    """Test that LazyJSONDict survives through parquet select()."""
    # Query transcripts
    results = [
        info async for info in parquet_db_with_nested_metadata.select([], None, False)
    ]
    assert len(results) > 0

    # Verify metadata is still a LazyJSONDict
    info = results[0]
    assert isinstance(info.metadata, LazyJSONDict)

    # Verify JSON is NOT parsed yet (should be string)
    # Use dict.__getitem__ to bypass LazyJSONDict's __getitem__ override
    config_raw = dict.__getitem__(info.metadata, "config")
    assert isinstance(config_raw, str)  # Still a JSON string

    # Now access it normally - should trigger parsing
    config = info.metadata["config"]
    assert isinstance(config, dict)  # Now parsed


@pytest.mark.asyncio
async def test_lazy_dict_survives_parquet_read_no_content(
    parquet_db_with_nested_metadata: ParquetTranscriptsDB,
) -> None:
    """Test that LazyJSONDict survives through parquet read() with no content."""
    # Get transcript info
    infos = [
        info async for info in parquet_db_with_nested_metadata.select([], None, False)
    ]
    info = infos[0]

    # Read with no content
    transcript = await parquet_db_with_nested_metadata.read(
        info, TranscriptContent(messages=None, events=None)
    )

    # Verify metadata is still a LazyJSONDict
    assert isinstance(transcript.metadata, LazyJSONDict)

    # Verify JSON is NOT parsed yet
    config_raw = dict.__getitem__(transcript.metadata, "config")
    assert isinstance(config_raw, str)

    # Access should trigger parsing
    config = transcript.metadata["config"]
    assert isinstance(config, dict)


@pytest.mark.asyncio
async def test_lazy_dict_survives_parquet_read_with_content(
    parquet_db_with_nested_metadata: ParquetTranscriptsDB,
) -> None:
    """Test that LazyJSONDict survives through parquet read() with content."""
    # Get transcript info
    infos = [
        info async for info in parquet_db_with_nested_metadata.select([], None, False)
    ]
    info = infos[0]

    # Read with full content
    transcript = await parquet_db_with_nested_metadata.read(
        info, TranscriptContent(messages="all", events="all")
    )

    # Verify metadata is still a LazyJSONDict
    assert isinstance(transcript.metadata, LazyJSONDict)

    # Verify JSON is NOT parsed yet
    config_raw = dict.__getitem__(transcript.metadata, "config")
    assert isinstance(config_raw, str)

    # Access should trigger parsing
    config = transcript.metadata["config"]
    assert isinstance(config, dict)


@pytest.mark.asyncio
async def test_lazy_dict_survives_filter_transcript(
    parquet_db_with_nested_metadata: ParquetTranscriptsDB,
) -> None:
    """Test that LazyJSONDict survives through filter_transcript()."""
    # Get full transcript
    infos = [
        info async for info in parquet_db_with_nested_metadata.select([], None, False)
    ]
    transcript = await parquet_db_with_nested_metadata.read(
        infos[0], TranscriptContent(messages="all", events="all")
    )

    # Verify it starts as LazyJSONDict
    assert isinstance(transcript.metadata, LazyJSONDict)

    # Filter it
    filtered = filter_transcript(
        transcript, TranscriptContent(messages=["user"], events=None)
    )

    # Verify metadata is STILL a LazyJSONDict after filtering
    assert isinstance(filtered.metadata, LazyJSONDict)

    # Verify JSON is NOT parsed yet
    config_raw = dict.__getitem__(filtered.metadata, "config")
    assert isinstance(config_raw, str)

    # Access should trigger parsing
    config = filtered.metadata["config"]
    assert isinstance(config, dict)


@pytest.mark.asyncio
async def test_lazy_dict_survives_eval_log_query(
    eval_log_db_with_json_metadata: EvalLogTranscriptsDB,
) -> None:
    """Test that LazyJSONDict survives through eval log query()."""
    # Query transcripts
    results = [
        info async for info in eval_log_db_with_json_metadata.query([], None, False)
    ]
    assert len(results) > 0

    # Verify metadata is a LazyJSONDict
    info = results[0]
    assert isinstance(info.metadata, LazyJSONDict)

    # Verify known JSON columns are NOT parsed yet
    if "eval_metadata" in info.metadata:
        metadata_raw = dict.__getitem__(info.metadata, "eval_metadata")
        assert isinstance(metadata_raw, str)  # Still a JSON string

        # Access should trigger parsing
        metadata = info.metadata["eval_metadata"]
        assert isinstance(metadata, dict)  # Now parsed


@pytest.mark.asyncio
async def test_lazy_dict_only_parses_accessed_fields(
    parquet_db_with_nested_metadata: ParquetTranscriptsDB,
) -> None:
    """Test that only accessed fields are parsed, not all JSON fields."""
    # Get transcript info
    infos = [
        info async for info in parquet_db_with_nested_metadata.select([], None, False)
    ]
    info = infos[0]

    # Access one field
    config = info.metadata["config"]
    assert isinstance(config, dict)

    # Verify other JSON fields are still strings
    tags_raw = dict.__getitem__(info.metadata, "tags")
    assert isinstance(tags_raw, str)  # Should still be unparsed

    # Now access tags
    tags = info.metadata["tags"]
    assert isinstance(tags, list)  # Now parsed


@pytest.mark.asyncio
async def test_lazy_dict_to_json_string_without_materialization() -> None:
    """Test that to_json_string() doesn't materialize unparsed fields."""
    # Create LazyJSONDict with JSON fields
    data = LazyJSONDict(
        {
            "model": "gpt-4",
            "config": '{"temperature": 0.7, "top_p": 0.9}',
            "tags": '["math", "reasoning"]',
        }
    )

    # Access one field to parse it
    _ = data["model"]  # This is a plain string, won't trigger JSON parsing

    # Serialize to JSON string
    json_str = data.to_json_string()

    # Verify we got valid JSON
    result = json.loads(json_str)
    assert result["model"] == "gpt-4"
    assert result["config"] == {"temperature": 0.7, "top_p": 0.9}
    assert result["tags"] == ["math", "reasoning"]

    # Verify "config" and "tags" were NOT parsed in the original dict
    config_raw = dict.__getitem__(data, "config")
    assert isinstance(config_raw, str)  # Still unparsed!
    tags_raw = dict.__getitem__(data, "tags")
    assert isinstance(tags_raw, str)  # Still unparsed!


@pytest.mark.asyncio
async def test_lazy_dict_to_json_string_with_mixed_state() -> None:
    """Test to_json_string() with mix of parsed and unparsed fields."""
    # Create LazyJSONDict
    data = LazyJSONDict(
        {
            "simple": "text",
            "number": 42,
            "config": '{"key": "value"}',
            "list": "[1, 2, 3]",
        }
    )

    # Parse one of the JSON fields
    config = data["config"]
    assert isinstance(config, dict)

    # Now serialize
    json_str = data.to_json_string()
    result = json.loads(json_str)

    # Verify all fields are correct
    assert result["simple"] == "text"
    assert result["number"] == 42
    assert result["config"] == {"key": "value"}
    assert result["list"] == [1, 2, 3]

    # Verify "list" is still unparsed
    list_raw = dict.__getitem__(data, "list")
    assert isinstance(list_raw, str)


@pytest.mark.asyncio
async def test_recorder_buffer_doesnt_materialize_metadata() -> None:
    """Test that RecorderBuffer.record() doesn't materialize LazyJSONDict metadata."""
    from inspect_scout._recorder.buffer import _normalize_scalar

    # Create LazyJSONDict with nested metadata
    metadata = LazyJSONDict(
        {
            "model": "gpt-4",
            "config": '{"temperature": 0.7}',
            "tags": '["test"]',
        }
    )

    # Normalize it (this is what buffer.py does)
    result = _normalize_scalar(metadata)

    # Should be a JSON string
    assert isinstance(result, str)

    # Should be valid JSON
    parsed = json.loads(result)
    assert parsed["model"] == "gpt-4"
    assert parsed["config"] == {"temperature": 0.7}

    # Original metadata should NOT have materialized the JSON fields
    config_raw = dict.__getitem__(metadata, "config")
    assert isinstance(config_raw, str)  # Still unparsed!
    tags_raw = dict.__getitem__(metadata, "tags")
    assert isinstance(tags_raw, str)  # Still unparsed!


# Fixtures


@pytest_asyncio.fixture
async def parquet_db_with_nested_metadata(
    tmp_path: Path,
) -> ParquetTranscriptsDB:
    """Create a parquet DB with nested metadata for testing."""
    from inspect_ai.model import ChatMessageUser

    db_path = str(tmp_path / "test_db")
    db = ParquetTranscriptsDB(db_path)
    await db.connect()

    # Insert test transcript with nested metadata
    transcript = Transcript(
        transcript_id="test-1",
        source_type="test",
        source_id="source-1",
        source_uri="file:///test",
        metadata={
            "model": "gpt-4",
            "config": {"temperature": 0.7, "top_p": 0.9},
            "tags": ["math", "reasoning"],
        },
        messages=[ChatMessageUser(content="test")],
        events=[],
    )

    await db.insert([transcript])
    return db


@pytest_asyncio.fixture
async def eval_log_db_with_json_metadata() -> EvalLogTranscriptsDB:
    """Create an eval log DB with JSON metadata for testing."""
    import pandas as pd

    # Create a minimal dataframe with JSON columns
    df = pd.DataFrame(
        {
            "sample_id": ["sample-1"],
            "eval_id": ["eval-1"],
            "log": ["file:///test.log"],
            "id": ["id-1"],
            "epoch": [1],
            "eval_metadata": ['{"key": "value"}'],
            "task_args": ['{"arg1": "val1"}'],
        }
    )

    db = EvalLogTranscriptsDB(df)
    await db.connect()
    return db
