"""Tests for ParquetTranscriptDB implementation."""

from pathlib import Path
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from inspect_ai.event._event import Event
from inspect_ai.model._chat_message import ChatMessage, ChatMessageUser
from inspect_scout._transcript.database.parquet import ParquetTranscriptDB
from inspect_scout._transcript.database.reader import TranscriptsDBReader
from inspect_scout._transcript.metadata import metadata as m
from inspect_scout._transcript.parquet_transcripts import transcripts_from_parquet
from inspect_scout._transcript.types import (
    Transcript,
    TranscriptContent,
    TranscriptInfo,
)


# Test data helpers
def create_sample_transcript(
    id: str = "test-001",
    source_id: str = "source-001",
    source_uri: str = "test://uri",
    metadata: dict[str, Any] | None = None,
    messages: list[ChatMessage] | None = None,
    events: list[Event] | None = None,
) -> Transcript:
    """Create a test transcript with customizable fields."""
    return Transcript(
        id=id,
        source_id=source_id,
        source_uri=source_uri,
        metadata=metadata or {},
        messages=messages or [ChatMessageUser(content="Test message")],
        events=events or [],
    )


def create_test_transcripts(count: int = 10) -> list[Transcript]:
    """Create multiple test transcripts with varied metadata."""
    transcripts = []
    models = ["gpt-4", "gpt-3.5-turbo", "claude-3-opus"]
    tasks = ["math", "coding", "qa"]

    for i in range(count):
        transcripts.append(
            create_sample_transcript(
                id=f"sample-{i:03d}",
                source_id=f"eval-{i // 5:02d}",  # Group into evals
                source_uri=f"test://log-{i:03d}.json",
                metadata={
                    "model": models[i % 3],
                    "task": tasks[i % 3],
                    "temperature": 0.5 + (i % 5) * 0.1,
                    "index": i,
                    "score": 0.5 + (i % 10) * 0.05,  # Moved to metadata
                    "accuracy": 0.8,  # Moved to metadata
                    "completeness": 0.9,  # Moved to metadata
                    "var_a": i,  # Moved to metadata
                    "var_b": f"value_{i}",  # Moved to metadata
                },
                messages=[
                    ChatMessageUser(content=f"Question {i}"),
                ],
                events=[],
            )
        )

    return transcripts


async def async_transcript_generator(count: int) -> AsyncIterator[Transcript]:
    """Generate transcripts asynchronously for streaming tests."""
    for i in range(count):
        yield create_sample_transcript(
            id=f"async-{i:03d}",
            source_id=f"async-source-{i}",
            metadata={"index": i, "async": True},
        )


# Fixtures
@pytest.fixture
def test_location(tmp_path: Path) -> Path:
    """Create temporary directory for Parquet files."""
    location = tmp_path / "transcript_db"
    location.mkdir(parents=True, exist_ok=True)
    return location


@pytest.fixture
def sample_transcripts() -> list[Transcript]:
    """Create sample transcripts for testing."""
    return create_test_transcripts(20)


@pytest_asyncio.fixture
async def parquet_db(test_location: Path) -> AsyncIterator[ParquetTranscriptDB]:
    """Create and connect to a ParquetTranscriptDB."""
    db = ParquetTranscriptDB(str(test_location))
    await db.connect()
    yield db
    await db.disconnect()


@pytest_asyncio.fixture
async def populated_db(
    parquet_db: ParquetTranscriptDB, sample_transcripts: list[Transcript]
) -> ParquetTranscriptDB:
    """Create a database with pre-inserted test data."""
    await parquet_db.insert(sample_transcripts)
    return parquet_db


# Basic Operations Tests
@pytest.mark.asyncio
async def test_connect_disconnect(test_location: Path) -> None:
    """Test database connection lifecycle."""
    db = ParquetTranscriptDB(str(test_location))

    # Initially not connected
    assert db._conn is None

    # Connect
    await db.connect()
    assert db._conn is not None

    # Disconnect
    await db.disconnect()
    assert db._conn is None


@pytest.mark.asyncio
async def test_insert_single_batch(
    parquet_db: ParquetTranscriptDB, test_location: Path
) -> None:
    """Test inserting a small batch of transcripts."""
    transcripts = create_test_transcripts(5)
    await parquet_db.insert(transcripts)

    # Verify Parquet file was created
    parquet_files = list(test_location.glob("transcripts_*.parquet"))
    assert len(parquet_files) == 1

    # Verify count
    count = await parquet_db.count([], None)
    assert count == 5


@pytest.mark.asyncio
async def test_insert_multiple_batches(
    parquet_db: ParquetTranscriptDB, test_location: Path
) -> None:
    """Test inserting large batch that spans multiple Parquet files."""
    # Insert 2500 transcripts (> 2 * BATCH_SIZE of 1000)
    transcripts = create_test_transcripts(2500)
    await parquet_db.insert(transcripts)

    # Verify multiple Parquet files were created
    parquet_files = list(test_location.glob("transcripts_*.parquet"))
    assert len(parquet_files) == 3  # 1000 + 1000 + 500

    # Verify count
    count = await parquet_db.count([], None)
    assert count == 2500


@pytest.mark.asyncio
async def test_insert_async_iterator(
    parquet_db: ParquetTranscriptDB, test_location: Path
) -> None:
    """Test inserting from async iterator."""
    await parquet_db.insert(async_transcript_generator(15))

    # Verify data was inserted
    count = await parquet_db.count([], None)
    assert count == 15


@pytest.mark.asyncio
async def test_count_all(populated_db: ParquetTranscriptDB) -> None:
    """Test counting all transcripts."""
    count = await populated_db.count([], None)
    assert count == 20


@pytest.mark.asyncio
async def test_count_with_limit(populated_db: ParquetTranscriptDB) -> None:
    """Test counting with limit parameter."""
    count = await populated_db.count([], limit=5)
    assert count == 5


# Query & Filtering Tests
@pytest.mark.asyncio
async def test_select_all(populated_db: ParquetTranscriptDB) -> None:
    """Test selecting all transcripts."""
    results = [info async for info in populated_db.select([], None, False)]
    assert len(results) == 20

    # Verify TranscriptInfo structure
    first = results[0]
    assert isinstance(first, TranscriptInfo)
    assert first.id is not None
    assert first.source_id is not None
    assert first.source_uri is not None


@pytest.mark.asyncio
async def test_select_with_where(populated_db: ParquetTranscriptDB) -> None:
    """Test filtering by metadata conditions."""
    # Filter by model (now a direct column, not nested in metadata JSON)
    condition = m.model == "gpt-4"
    results = [info async for info in populated_db.select([condition], None, False)]

    # Should have ~7 results (20 total / 3 models)
    assert 6 <= len(results) <= 7

    # Verify all results match condition
    for info in results:
        assert info.metadata.get("model") == "gpt-4"


@pytest.mark.asyncio
async def test_select_with_limit(populated_db: ParquetTranscriptDB) -> None:
    """Test limiting results."""
    results = [info async for info in populated_db.select([], limit=5, shuffle=False)]
    assert len(results) == 5


@pytest.mark.asyncio
async def test_select_with_shuffle(populated_db: ParquetTranscriptDB) -> None:
    """Test shuffle with deterministic seed."""
    # Get results with same seed twice
    results1 = [info.id async for info in populated_db.select([], None, shuffle=42)]
    results2 = [info.id async for info in populated_db.select([], None, shuffle=42)]

    # Should be same order
    assert results1 == results2

    # Get results with different seed
    results3 = [info.id async for info in populated_db.select([], None, shuffle=123)]

    # Should be different order (very likely)
    assert results1 != results3


@pytest.mark.asyncio
async def test_metadata_dsl_queries(populated_db: ParquetTranscriptDB) -> None:
    """Test various Condition operators."""
    # Greater than
    results = [
        info
        async for info in populated_db.select([m.index > 15], None, False)
    ]
    assert len(results) == 4  # indices 16, 17, 18, 19

    # Less than or equal
    results = [
        info
        async for info in populated_db.select([m.index <= 5], None, False)
    ]
    assert len(results) == 6  # indices 0-5

    # IN operator
    results = [
        info
        async for info in populated_db.select(
            [m.task.in_(["math", "coding"])], None, False
        )
    ]
    assert len(results) >= 10  # At least 2/3 of results


@pytest.mark.asyncio
async def test_json_path_queries(populated_db: ParquetTranscriptDB) -> None:
    """Test querying metadata fields."""
    # Query by temperature value
    results = [
        info
        async for info in populated_db.select(
            [m.temperature > 0.7], None, False
        )
    ]
    assert len(results) > 0

    # Verify results
    for info in results:
        temp = info.metadata.get("temperature", 0.0)
        assert isinstance(temp, (int, float)) and temp > 0.7


@pytest.mark.asyncio
async def test_complex_conditions(populated_db: ParquetTranscriptDB) -> None:
    """Test combining conditions with & and |."""
    # AND condition
    condition = (m.model == "gpt-4") & (m.index < 10)
    results = [info async for info in populated_db.select([condition], None, False)]

    for info in results:
        assert info.metadata.get("model") == "gpt-4"
        index = info.metadata.get("index", 100)
        assert isinstance(index, int) and index < 10

    # OR condition
    condition = (m.index == 0) | (m.index == 19)
    results = [info async for info in populated_db.select([condition], None, False)]
    assert len(results) == 2


# Content Loading Tests
@pytest.mark.asyncio
async def test_read_full_content(populated_db: ParquetTranscriptDB) -> None:
    """Test loading full transcript content."""
    # Get a transcript info
    infos = [info async for info in populated_db.select([], limit=1, shuffle=False)]
    assert len(infos) == 1

    # Read full content
    content = TranscriptContent(messages="all", events="all")
    transcript = await populated_db.read(infos[0], content)

    # Verify structure
    assert isinstance(transcript, Transcript)
    assert len(transcript.messages) > 0
    # Events are empty in our test data
    assert len(transcript.events) == 0


@pytest.mark.asyncio
async def test_read_filtered_messages(populated_db: ParquetTranscriptDB) -> None:
    """Test filtering messages by type."""
    infos = [info async for info in populated_db.select([], limit=1, shuffle=False)]

    # Read only user messages
    content = TranscriptContent(messages=["user"], events=None)
    transcript = await populated_db.read(infos[0], content)

    # Should have messages
    assert len(transcript.messages) > 0

    # Should not have events
    assert len(transcript.events) == 0


@pytest.mark.asyncio
async def test_read_no_content(populated_db: ParquetTranscriptDB) -> None:
    """Test loading metadata only (no content)."""
    infos = [info async for info in populated_db.select([], limit=1, shuffle=False)]

    # Read with no messages or events
    content = TranscriptContent(messages=None, events=None)
    transcript = await populated_db.read(infos[0], content)

    # Should have no content
    assert len(transcript.messages) == 0
    assert len(transcript.events) == 0

    # Should still have metadata
    assert transcript.id == infos[0].id


# Update & Delete Tests
@pytest.mark.asyncio
async def test_update_single(populated_db: ParquetTranscriptDB) -> None:
    """Test updating a single transcript."""
    # Get original
    infos = [info async for info in populated_db.select([], limit=1, shuffle=False)]
    original_id = infos[0].id

    # Create updated version
    updated = create_sample_transcript(
        id=original_id,
        source_id="updated-source",
        metadata={"updated": True, "new_field": "new_value"},
    )

    # Update
    await populated_db.update([(original_id, updated)])

    # Verify update
    results = [
        info async for info in populated_db.select([m.id == original_id], None, False)
    ]
    assert len(results) == 1
    assert results[0].source_id == "updated-source"
    assert results[0].metadata.get("updated") is True


@pytest.mark.asyncio
async def test_delete_single(populated_db: ParquetTranscriptDB) -> None:
    """Test deleting a single transcript."""
    # Get original count
    original_count = await populated_db.count([], None)

    # Get a transcript to delete
    infos = [info async for info in populated_db.select([], limit=1, shuffle=False)]
    delete_id = infos[0].id

    # Delete
    await populated_db.delete([delete_id])

    # Verify deletion
    new_count = await populated_db.count([], None)
    assert new_count == original_count - 1

    # Verify specific transcript is gone
    results = [
        info async for info in populated_db.select([m.id == delete_id], None, False)
    ]
    assert len(results) == 0


@pytest.mark.asyncio
async def test_delete_multiple(populated_db: ParquetTranscriptDB) -> None:
    """Test deleting multiple transcripts."""
    original_count = await populated_db.count([], None)

    # Get 3 transcripts to delete
    infos = [info async for info in populated_db.select([], limit=3, shuffle=False)]
    delete_ids = [info.id for info in infos]

    # Delete
    await populated_db.delete(delete_ids)

    # Verify deletion
    new_count = await populated_db.count([], None)
    assert new_count == original_count - 3


# Schema & File Management Tests
@pytest.mark.asyncio
async def test_empty_database(parquet_db: ParquetTranscriptDB) -> None:
    """Test querying empty database."""
    count = await parquet_db.count([], None)
    assert count == 0

    results = [info async for info in parquet_db.select([], None, False)]
    assert len(results) == 0


@pytest.mark.asyncio
async def test_arbitrary_metadata(parquet_db: ParquetTranscriptDB) -> None:
    """Test with various metadata structures."""
    transcripts = [
        create_sample_transcript(
            id="complex-1",
            metadata={
                "nested": {"deep": {"value": 42}},
                "array": [1, 2, 3],
                "string": "test",
                "number": 3.14,
                "boolean": True,
                "null": None,
            },
        ),
        create_sample_transcript(
            id="minimal-1",
            metadata={},
        ),
    ]

    await parquet_db.insert(transcripts)

    # Query with nested metadata (use JSON path for nested dicts)
    results = [
        info
        async for info in parquet_db.select(
            [m["nested.deep.value"] == 42], None, False
        )
    ]
    assert len(results) == 1
    assert results[0].id == "complex-1"


@pytest.mark.asyncio
async def test_null_handling(parquet_db: ParquetTranscriptDB) -> None:
    """Test nullable metadata fields."""
    transcripts = [
        create_sample_transcript(
            id="with-data",
            metadata={"key": "value", "score": 0.95, "a": 1.0, "x": "y"},
        ),
        create_sample_transcript(
            id="without-data",
            metadata={},
        ),
    ]

    await parquet_db.insert(transcripts)

    count = await parquet_db.count([], None)
    assert count == 2


# Integration Tests - ParquetTranscripts
@pytest.mark.asyncio
async def test_factory_function(test_location: Path) -> None:
    """Test transcripts_from_parquet factory function."""
    transcripts = transcripts_from_parquet(str(test_location))
    assert transcripts is not None

    # Insert some data
    sample_data = create_test_transcripts(5)
    async with transcripts.reader() as reader:
        # Access underlying DB to insert data
        if hasattr(reader, "_db"):
            await reader._db.insert(sample_data)

        count = await reader.count()
        assert count == 5


@pytest.mark.asyncio
async def test_where_filtering(test_location: Path) -> None:
    """Test .where() method on ParquetTranscripts."""
    # Create and populate
    transcripts_obj = transcripts_from_parquet(str(test_location))
    async with transcripts_obj.reader() as reader:
        if isinstance(reader, TranscriptsDBReader):
            await reader._db.insert(create_test_transcripts(20))

    # Filter
    filtered = transcripts_obj.where(m.model == "gpt-4")

    async with filtered.reader() as reader:
        count = await reader.count()
        # Should have fewer than 20
        assert count < 20


@pytest.mark.asyncio
async def test_limit_method(test_location: Path) -> None:
    """Test .limit() method."""
    transcripts_obj = transcripts_from_parquet(str(test_location))
    async with transcripts_obj.reader() as reader:
        if isinstance(reader, TranscriptsDBReader):
            await reader._db.insert(create_test_transcripts(20))

    # Limit
    limited = transcripts_obj.limit(5)

    async with limited.reader() as reader:
        count = await reader.count()
        assert count == 5


@pytest.mark.asyncio
async def test_shuffle_method(test_location: Path) -> None:
    """Test .shuffle() method."""
    transcripts_obj = transcripts_from_parquet(str(test_location))
    async with transcripts_obj.reader() as reader:
        if isinstance(reader, TranscriptsDBReader):
            await reader._db.insert(create_test_transcripts(10))

    # Shuffle with seed
    shuffled = transcripts_obj.shuffle(seed=42)

    async with shuffled.reader() as reader:
        results1 = [info.id async for info in reader.index()]

    # Shuffle again with same seed
    async with shuffled.reader() as reader:
        results2 = [info.id async for info in reader.index()]

    # Should be same order
    assert results1 == results2


# Edge Cases & Error Handling
@pytest.mark.asyncio
async def test_insert_empty_list(parquet_db: ParquetTranscriptDB) -> None:
    """Test inserting empty iterable."""
    await parquet_db.insert([])

    count = await parquet_db.count([], None)
    assert count == 0


@pytest.mark.asyncio
async def test_query_no_matches(populated_db: ParquetTranscriptDB) -> None:
    """Test query with no matching results."""
    # Query for non-existent value
    results = [
        info
        async for info in populated_db.select(
            [m.model == "non-existent-model"], None, False
        )
    ]
    assert len(results) == 0


@pytest.mark.asyncio
async def test_read_nonexistent_transcript(populated_db: ParquetTranscriptDB) -> None:
    """Test reading missing transcript."""
    # Create a non-existent TranscriptInfo
    fake_info = TranscriptInfo(
        id="non-existent-id",
        source_id="fake",
        source_uri="fake://uri",
    )

    # Read should return transcript with no content
    content = TranscriptContent(messages="all", events="all")
    transcript = await populated_db.read(fake_info, content)

    # Should not raise error, just return empty
    assert transcript.id == "non-existent-id"
    assert len(transcript.messages) == 0


# New tests for flattened metadata implementation
@pytest.mark.asyncio
async def test_nested_metadata_stored_as_json(parquet_db: ParquetTranscriptDB) -> None:
    """Test that nested dicts/arrays are stored as JSON and queryable."""
    transcripts = [
        create_sample_transcript(
            id="nested-1",
            metadata={
                "model": "gpt-4",
                "config": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                },
                "tags": ["math", "reasoning"],
            },
        ),
        create_sample_transcript(
            id="nested-2",
            metadata={
                "model": "claude",
                "config": {
                    "temperature": 0.5,
                },
            },
        ),
    ]

    await parquet_db.insert(transcripts)

    # Query by direct field
    results = [info async for info in parquet_db.select([m.model == "gpt-4"], None, False)]
    assert len(results) == 1

    # Query by nested field (JSON path into config column)
    results = [
        info async for info in parquet_db.select(
            [m["config.temperature"] > 0.6], None, False
        )
    ]
    assert len(results) == 1
    assert results[0].id == "nested-1"

    # Verify nested structures are preserved
    assert results[0].metadata["config"] == {"temperature": 0.7, "top_p": 0.9}
    assert results[0].metadata["tags"] == ["math", "reasoning"]


@pytest.mark.asyncio
async def test_reserved_column_validation(parquet_db: ParquetTranscriptDB) -> None:
    """Test that reserved column names in metadata raise error."""
    from inspect_scout._transcript.database.parquet import _validate_metadata_keys

    # Should raise error for reserved keys
    with pytest.raises(ValueError, match="reserved"):
        _validate_metadata_keys({"id": "bad"})

    with pytest.raises(ValueError, match="reserved"):
        _validate_metadata_keys({"content": "bad"})

    with pytest.raises(ValueError, match="reserved"):
        _validate_metadata_keys({"messages": "bad"})

    # Should be fine for non-reserved keys
    _validate_metadata_keys({"model": "gpt-4", "task": "math"})  # No error


@pytest.mark.asyncio
async def test_schema_evolution(parquet_db: ParquetTranscriptDB, test_location: Path) -> None:
    """Test that different metadata fields across batches work correctly."""
    # First batch: model, task
    batch1 = [
        create_sample_transcript(
            id=f"batch1-{i}",
            metadata={"model": "gpt-4", "task": "math"},
        )
        for i in range(5)
    ]
    await parquet_db.insert(batch1)

    # Second batch: model, temperature (different fields!)
    batch2 = [
        create_sample_transcript(
            id=f"batch2-{i}",
            metadata={"model": "claude", "temperature": 0.7},
        )
        for i in range(5)
    ]
    await parquet_db.insert(batch2)

    # Should have 2 Parquet files
    parquet_files = list(test_location.glob("transcripts_*.parquet"))
    assert len(parquet_files) == 2

    # Query should work across both schemas
    all_results = [info async for info in parquet_db.select([], None, False)]
    assert len(all_results) == 10

    # First batch has NULL temperature
    batch1_results = [
        info async for info in parquet_db.select([m.task == "math"], None, False)
    ]
    assert len(batch1_results) == 5
    for info in batch1_results:
        assert info.metadata.get("temperature") is None
        assert info.metadata.get("task") == "math"

    # Second batch has NULL task
    batch2_results = [
        info async for info in parquet_db.select([m.model == "claude"], None, False)
    ]
    assert len(batch2_results) == 5
    for info in batch2_results:
        assert info.metadata.get("task") is None
        assert info.metadata.get("temperature") == 0.7
