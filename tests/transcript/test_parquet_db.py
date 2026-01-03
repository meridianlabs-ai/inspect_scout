"""Tests for ParquetTranscriptDB implementation."""

from pathlib import Path
from typing import Any, AsyncIterator, Literal

import pyarrow as pa
import pytest
import pytest_asyncio
from inspect_ai.event._event import Event
from inspect_ai.model._chat_message import ChatMessage, ChatMessageUser
from inspect_scout import columns as c
from inspect_scout import transcripts_db, transcripts_from
from inspect_scout._query import OrderBy
from inspect_scout._transcript.database.parquet import (
    PARQUET_TRANSCRIPTS_GLOB,
    ParquetTranscriptsDB,
)
from inspect_scout._transcript.database.reader import TranscriptsViewReader
from inspect_scout._transcript.types import (
    Transcript,
    TranscriptContent,
    TranscriptInfo,
)
from pydantic import JsonValue


# Test data helpers
def create_sample_transcript(
    id: str = "test-001",
    source_id: str = "source-001",
    source_uri: str = "test://uri",
    model: str | None = None,
    task: str | None = None,
    score: JsonValue | None = None,
    metadata: dict[str, Any] | None = None,
    messages: list[ChatMessage] | None = None,
    events: list[Event] | None = None,
) -> Transcript:
    """Create a test transcript with customizable fields."""
    return Transcript(
        transcript_id=id,
        source_type="test",
        source_id=source_id,
        source_uri=source_uri,
        task_set=task,
        model=model,
        score=score,
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
                model=models[i % 3],
                task=tasks[i % 3],
                score=0.5 + (i % 10) * 0.05,
                metadata={
                    "temperature": 0.5 + (i % 5) * 0.1,
                    "index": i,
                    "mean": 0.8,  # Moved to metadata
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
async def parquet_db(test_location: Path) -> AsyncIterator[ParquetTranscriptsDB]:
    """Create and connect to a ParquetTranscriptDB."""
    db = ParquetTranscriptsDB(str(test_location))
    await db.connect()
    yield db
    await db.disconnect()


@pytest_asyncio.fixture
async def populated_db(
    parquet_db: ParquetTranscriptsDB, sample_transcripts: list[Transcript]
) -> ParquetTranscriptsDB:
    """Create a database with pre-inserted test data."""
    await parquet_db.insert(sample_transcripts)
    return parquet_db


# Basic Operations Tests
@pytest.mark.asyncio
async def test_connect_disconnect(test_location: Path) -> None:
    """Test database connection lifecycle."""
    db = ParquetTranscriptsDB(str(test_location))

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
    parquet_db: ParquetTranscriptsDB, test_location: Path
) -> None:
    """Test inserting a small batch of transcripts."""
    transcripts = create_test_transcripts(5)
    await parquet_db.insert(transcripts)

    # Verify Parquet file was created
    parquet_files = list(test_location.glob(PARQUET_TRANSCRIPTS_GLOB))
    assert len(parquet_files) == 1


@pytest.mark.asyncio
async def test_insert_multiple_batches(test_location: Path) -> None:
    """Test inserting large batch with size-based splitting.

    Transcripts are processed sequentially and split into batches
    based on target file size, regardless of source_id.
    """
    # Create database with very small target_file_size_mb to force batching
    # Use 0.01 MB (10KB) to ensure multiple batches with small test transcripts
    parquet_db = ParquetTranscriptsDB(str(test_location), target_file_size_mb=0.01)
    await parquet_db.connect()

    try:
        # Create 500 transcripts with source_id groups of 250
        # This will create 2 source_ids: eval-00 (transcripts 0-249), eval-01 (transcripts 250-499)
        transcripts = []
        for i in range(500):
            transcripts.append(
                create_sample_transcript(
                    id=f"sample-{i:03d}",
                    source_id=f"eval-{i // 250:02d}",  # Groups of 250 to test batch splitting
                    source_uri=f"test://log-{i:03d}.json",
                    model=["gpt-4", "gpt-3.5-turbo", "claude-3-opus"][i % 3],
                    task=["math", "coding", "qa"][i % 3],
                    score=0.5 + (i % 10) * 0.05,
                    metadata={
                        "temperature": 0.5 + (i % 5) * 0.1,
                        "index": i,
                        "mean": 0.8,
                        "completeness": 0.9,
                        "var_a": i,
                        "var_b": f"value_{i}",
                    },
                )
            )

        await parquet_db.insert(transcripts)

        # Expected file count:
        # - 500 transcripts total with target_file_size_mb=0.01
        # - Small test transcripts result in multiple files based on accumulated size
        # - Should create multiple parquet files (exact count depends on serialized size)
        parquet_files = list(test_location.glob(PARQUET_TRANSCRIPTS_GLOB))
        assert len(parquet_files) >= 2, (
            f"Expected multiple files, got {len(parquet_files)}"
        )
        assert len(parquet_files) <= 20, (
            f"Expected reasonable number of files, got {len(parquet_files)}"
        )

    finally:
        await parquet_db.disconnect()


@pytest.mark.asyncio
async def test_insert_async_iterator(
    parquet_db: ParquetTranscriptsDB, test_location: Path
) -> None:
    """Test inserting from async iterator."""
    await parquet_db.insert(async_transcript_generator(15))

    # Verify data was inserted
    transcript_ids = await parquet_db.transcript_ids([], None)
    assert len(transcript_ids) == 15


@pytest.mark.asyncio
async def test_count_all(populated_db: ParquetTranscriptsDB) -> None:
    """Test counting all transcripts."""
    transcript_ids = await populated_db.transcript_ids([], None)
    assert len(transcript_ids) == 20


@pytest.mark.asyncio
async def test_count_with_limit(populated_db: ParquetTranscriptsDB) -> None:
    """Test counting with limit parameter."""
    transcript_ids = await populated_db.transcript_ids([], limit=5)
    assert len(transcript_ids) == 5


# Query & Filtering Tests
@pytest.mark.asyncio
async def test_select_all(populated_db: ParquetTranscriptsDB) -> None:
    """Test selecting all transcripts."""
    results = [info async for info in populated_db.select([], None, False)]
    assert len(results) == 20

    # Verify TranscriptInfo structure
    first = results[0]
    assert isinstance(first, TranscriptInfo)
    assert first.transcript_id is not None
    assert first.source_id is not None
    assert first.source_uri is not None


@pytest.mark.asyncio
async def test_select_with_where(populated_db: ParquetTranscriptsDB) -> None:
    """Test filtering by metadata conditions."""
    # Filter by model (now a direct column, not nested in metadata JSON)
    condition = c.model == "gpt-4"
    results = [info async for info in populated_db.select([condition], None, False)]

    # Should have ~7 results (20 total / 3 models)
    assert 6 <= len(results) <= 7

    # Verify all results match condition
    for info in results:
        assert info.model == "gpt-4"


@pytest.mark.asyncio
async def test_select_with_limit(populated_db: ParquetTranscriptsDB) -> None:
    """Test limiting results."""
    results = [info async for info in populated_db.select([], limit=5, shuffle=False)]
    assert len(results) == 5


@pytest.mark.asyncio
async def test_count_method_all(populated_db: ParquetTranscriptsDB) -> None:
    """Test count() method with no filter."""
    count = await populated_db.count()
    assert count == 20


@pytest.mark.asyncio
async def test_count_method_with_where(populated_db: ParquetTranscriptsDB) -> None:
    """Test count() method with filter condition."""
    count = await populated_db.count([c.model == "gpt-4"])
    assert 6 <= count <= 7


@pytest.mark.asyncio
async def test_select_with_shuffle(populated_db: ParquetTranscriptsDB) -> None:
    """Test shuffle with deterministic seed."""
    # Get results with same seed twice
    results1 = [
        info.transcript_id async for info in populated_db.select([], None, shuffle=42)
    ]
    results2 = [
        info.transcript_id async for info in populated_db.select([], None, shuffle=42)
    ]

    # Should be same order
    assert results1 == results2

    # Get results with different seed
    results3 = [
        info.transcript_id async for info in populated_db.select([], None, shuffle=123)
    ]

    # Should be different order (very likely)
    assert results1 != results3


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "column,direction,extractor,reverse",
    [
        (c.index.name, "ASC", lambda info: info.metadata.get("index"), False),
        (c.index.name, "DESC", lambda info: info.metadata.get("index"), True),
        (c.task_set.name, "ASC", lambda info: info.task_set, False),
        (c.task_set.name, "DESC", lambda info: info.task_set, True),
    ],
)
async def test_select_with_order_by_single_column(
    populated_db: ParquetTranscriptsDB,
    column: str,
    direction: Literal["ASC", "DESC"],
    extractor: Any,
    reverse: bool,
) -> None:
    """Test ordering by single column with various directions."""
    results = [
        info
        async for info in populated_db.select(
            [], None, False, order_by=[OrderBy(column, direction)]
        )
    ]
    values = [extractor(info) for info in results if extractor(info) is not None]
    assert values == sorted(values, reverse=reverse)


@pytest.mark.asyncio
async def test_select_with_order_by_chaining(
    populated_db: ParquetTranscriptsDB,
) -> None:
    """Test ordering with multiple columns (tie-breaking)."""
    # Order by task_set ASC, then index DESC
    results = [
        info
        async for info in populated_db.select(
            [],
            None,
            False,
            order_by=[OrderBy(c.task_set.name, "ASC"), OrderBy(c.index.name, "DESC")],
        )
    ]

    # Group by task_set and verify indices are descending within each task_set
    from itertools import groupby
    from typing import cast

    for _task_set, group in groupby(results, key=lambda r: r.task_set):
        indices = [
            cast(int, r.metadata.get("index"))
            for r in group
            if r.metadata.get("index") is not None
        ]
        assert indices == sorted(indices, reverse=True)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "where_clause,limit,expected_results",
    [
        (
            [c.task_set == "math"],
            None,
            lambda results: all(r.task_set == "math" for r in results),
        ),
        ([], 5, lambda results: len(results) == 5),
    ],
)
async def test_order_by_with_where_and_limit(
    populated_db: ParquetTranscriptsDB,
    where_clause: list[Any],
    limit: int | None,
    expected_results: Any,
) -> None:
    """Test combining where clause and limit with order_by."""
    results = [
        info
        async for info in populated_db.select(
            where_clause, limit, False, order_by=[OrderBy(c.index.name, "ASC")]
        )
    ]

    # Verify results match expectations
    assert expected_results(results)

    # Verify ordering
    from typing import cast

    indices = [
        cast(int, result.metadata.get("index"))
        for result in results
        if result.metadata.get("index") is not None
    ]
    assert indices == sorted(indices)


@pytest.mark.asyncio
async def test_order_by_with_shuffle(populated_db: ParquetTranscriptsDB) -> None:
    """Test that shuffle takes precedence over order_by."""
    # Get results with shuffle and order_by (shuffle should win)
    results1 = [
        info.transcript_id
        async for info in populated_db.select(
            [], limit=10, shuffle=42, order_by=[OrderBy(c.index.name, "ASC")]
        )
    ]

    # Get results with same shuffle seed - should be same order
    results2 = [
        info.transcript_id
        async for info in populated_db.select(
            [], limit=10, shuffle=42, order_by=[OrderBy(c.index.name, "ASC")]
        )
    ]
    assert results1 == results2

    # Get results without shuffle - should be different
    results3 = [
        info.transcript_id
        async for info in populated_db.select(
            [], limit=10, shuffle=False, order_by=[OrderBy(c.index.name, "ASC")]
        )
    ]
    assert results1 != results3  # Shuffled vs ordered should differ


@pytest.mark.asyncio
async def test_order_by_empty_results(populated_db: ParquetTranscriptsDB) -> None:
    """Test order_by on empty result set."""
    results = [
        info
        async for info in populated_db.select(
            [c.task_set == "nonexistent"],
            None,
            False,
            order_by=[OrderBy(c.index.name, "ASC")],
        )
    ]
    assert len(results) == 0


@pytest.mark.asyncio
async def test_metadata_dsl_queries(populated_db: ParquetTranscriptsDB) -> None:
    """Test various Condition operators."""
    # Greater than
    results = [info async for info in populated_db.select([c.index > 15], None, False)]
    assert len(results) == 4  # indices 16, 17, 18, 19

    # Less than or equal
    results = [info async for info in populated_db.select([c.index <= 5], None, False)]
    assert len(results) == 6  # indices 0-5

    # IN operator
    results = [
        info
        async for info in populated_db.select(
            [c.task_set.in_(["math", "coding"])], None, False
        )
    ]
    assert len(results) >= 10  # At least 2/3 of results


@pytest.mark.asyncio
async def test_json_path_queries(populated_db: ParquetTranscriptsDB) -> None:
    """Test querying metadata fields."""
    # Query by temperature value
    results = [
        info async for info in populated_db.select([c.temperature > 0.7], None, False)
    ]
    assert len(results) > 0

    # Verify results
    for info in results:
        temp = info.metadata.get("temperature", 0.0)
        assert isinstance(temp, (int, float)) and temp > 0.7


@pytest.mark.asyncio
async def test_complex_conditions(populated_db: ParquetTranscriptsDB) -> None:
    """Test combining conditions with & and |."""
    # AND condition
    condition = (c.model == "gpt-4") & (c.index < 10)
    results = [info async for info in populated_db.select([condition], None, False)]

    for info in results:
        assert info.model == "gpt-4"
        index = info.metadata.get("index", 100)
        assert isinstance(index, int) and index < 10

    # OR condition
    condition = (c.index == 0) | (c.index == 19)
    results = [info async for info in populated_db.select([condition], None, False)]
    assert len(results) == 2


# Content Loading Tests
@pytest.mark.asyncio
async def test_read_full_content(populated_db: ParquetTranscriptsDB) -> None:
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
async def test_read_filtered_messages(populated_db: ParquetTranscriptsDB) -> None:
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
async def test_read_no_content(populated_db: ParquetTranscriptsDB) -> None:
    """Test loading metadata only (no content)."""
    infos = [info async for info in populated_db.select([], limit=1, shuffle=False)]

    # Read with no messages or events
    content = TranscriptContent(messages=None, events=None)
    transcript = await populated_db.read(infos[0], content)

    # Should have no content
    assert len(transcript.messages) == 0
    assert len(transcript.events) == 0

    # Should still have metadata
    assert transcript.transcript_id == infos[0].transcript_id


# Schema & File Management Tests
@pytest.mark.asyncio
async def test_empty_database(parquet_db: ParquetTranscriptsDB) -> None:
    results = [info async for info in parquet_db.select([], None, False)]
    assert len(results) == 0


@pytest.mark.asyncio
async def test_arbitrary_metadata(parquet_db: ParquetTranscriptsDB) -> None:
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
        async for info in parquet_db.select([c["nested.deep.value"] == 42], None, False)
    ]
    assert len(results) == 1
    assert results[0].transcript_id == "complex-1"


@pytest.mark.asyncio
async def test_null_handling(parquet_db: ParquetTranscriptsDB) -> None:
    """Test nullable metadata fields."""
    transcripts = [
        create_sample_transcript(
            id="with-data",
            score=0.95,
            metadata={"key": "value", "a": 1.0, "x": "y"},
        ),
        create_sample_transcript(
            id="without-data",
            metadata={},
        ),
    ]

    await parquet_db.insert(transcripts)

    transcript_ids = await parquet_db.transcript_ids([], None)
    assert len(transcript_ids) == 2


# Integration Tests - ParquetTranscripts
@pytest.mark.asyncio
async def test_factory_function(test_location: Path) -> None:
    """Test transcripts_from_parquet factory function."""
    transcripts = transcripts_from(str(test_location))
    assert transcripts is not None

    # Insert some data
    sample_data = create_test_transcripts(5)
    async with transcripts_db(str(test_location)) as db:
        await db.insert(sample_data)


@pytest.mark.asyncio
async def test_where_filtering(test_location: Path) -> None:
    """Test .where() method on ParquetTranscripts."""
    # Create and populate
    transcripts_obj = transcripts_from(str(test_location))
    async with transcripts_db(str(test_location)) as db:
        await db.insert(create_test_transcripts(20))

    # Filter
    filtered = transcripts_obj.where(c.model == "gpt-4")

    async with filtered.reader() as reader:
        index = [info async for info in reader.index()]
        # Should have fewer than 20
        assert len(index) < 20


@pytest.mark.asyncio
async def test_limit_method(test_location: Path) -> None:
    """Test .limit() method."""
    transcripts_obj = transcripts_from(str(test_location))
    async with transcripts_db(str(test_location)) as db:
        await db.insert(create_test_transcripts(20))

    # Limit
    limited = transcripts_obj.limit(5)

    async with limited.reader() as reader:
        index = [info async for info in reader.index()]
        assert len(index) == 5


@pytest.mark.asyncio
async def test_shuffle_method(test_location: Path) -> None:
    """Test .shuffle() method."""
    transcripts_obj = transcripts_from(str(test_location))
    async with transcripts_db(str(test_location)) as db:
        await db.insert(create_test_transcripts(10))

    # Shuffle with seed
    shuffled = transcripts_obj.shuffle(seed=42)

    async with shuffled.reader() as reader:
        results1 = [info.transcript_id async for info in reader.index()]

    # Shuffle again with same seed
    async with shuffled.reader() as reader:
        results2 = [info.transcript_id async for info in reader.index()]

    # Should be same order
    assert results1 == results2


# Edge Cases & Error Handling
@pytest.mark.asyncio
async def test_insert_empty_list(parquet_db: ParquetTranscriptsDB) -> None:
    """Test inserting empty iterable."""
    await parquet_db.insert([])

    transcript_ids = await parquet_db.transcript_ids([], None)
    assert len(transcript_ids) == 0


@pytest.mark.asyncio
async def test_query_no_matches(populated_db: ParquetTranscriptsDB) -> None:
    """Test query with no matching results."""
    # Query for non-existent value
    results = [
        info
        async for info in populated_db.select(
            [c.model == "non-existent-model"], None, False
        )
    ]
    assert len(results) == 0


@pytest.mark.asyncio
async def test_read_nonexistent_transcript(populated_db: ParquetTranscriptsDB) -> None:
    """Test reading missing transcript."""
    # Create a non-existent TranscriptInfo
    fake_info = TranscriptInfo(
        transcript_id="non-existent-id",
        source_type="test",
        source_id="fake",
        source_uri="fake://uri",
    )

    # Read should return transcript with no content
    content = TranscriptContent(messages="all", events="all")
    transcript = await populated_db.read(fake_info, content)

    # Should not raise error, just return empty
    assert transcript.transcript_id == "non-existent-id"
    assert len(transcript.messages) == 0


# New tests for flattened metadata implementation
@pytest.mark.asyncio
async def test_nested_metadata_stored_as_json(parquet_db: ParquetTranscriptsDB) -> None:
    """Test that nested dicts/arrays are stored as JSON and queryable."""
    transcripts = [
        create_sample_transcript(
            id="nested-1",
            model="gpt-4",
            metadata={
                "config": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                },
                "tags": ["math", "reasoning"],
            },
        ),
        create_sample_transcript(
            id="nested-2",
            model="claude",
            metadata={
                "config": {
                    "temperature": 0.5,
                },
            },
        ),
    ]

    await parquet_db.insert(transcripts)

    # Query by direct field
    results = [
        info async for info in parquet_db.select([c.model == "gpt-4"], None, False)
    ]
    assert len(results) == 1

    # Query by nested field (JSON path into config column)
    results = [
        info
        async for info in parquet_db.select(
            [c["config.temperature"] > 0.6], None, False
        )
    ]
    assert len(results) == 1
    assert results[0].transcript_id == "nested-1"

    # Verify nested structures are preserved
    assert results[0].metadata["config"] == {"temperature": 0.7, "top_p": 0.9}
    assert results[0].metadata["tags"] == ["math", "reasoning"]


@pytest.mark.asyncio
async def test_reserved_column_validation(parquet_db: ParquetTranscriptsDB) -> None:
    """Test that reserved column names in metadata raise error."""
    from inspect_scout._transcript.database.parquet.transcripts import (
        _validate_metadata_keys,
    )

    # Should raise error for reserved keys (actual Parquet columns)
    with pytest.raises(ValueError, match="reserved"):
        _validate_metadata_keys({"transcript_id": "bad"})

    with pytest.raises(ValueError, match="reserved"):
        _validate_metadata_keys({"source_id": "bad"})

    with pytest.raises(ValueError, match="reserved"):
        _validate_metadata_keys({"messages": "bad"})

    with pytest.raises(ValueError, match="reserved"):
        _validate_metadata_keys({"events": "bad"})

    # Should be fine for non-reserved keys
    _validate_metadata_keys({"foo": "gpt-4", "bar": "math"})  # No error
    _validate_metadata_keys({"content": "custom"})  # "content" is no longer reserved


@pytest.mark.asyncio
async def test_schema_evolution(
    parquet_db: ParquetTranscriptsDB, test_location: Path
) -> None:
    """Test that different metadata fields across batches work correctly."""
    # First batch: category, difficulty metadata
    batch1 = [
        create_sample_transcript(
            id=f"batch1-{i}",
            metadata={"category": "science", "difficulty": "hard"},
        )
        for i in range(5)
    ]
    await parquet_db.insert(batch1)

    # Second batch: category, temperature (different fields!)
    batch2 = [
        create_sample_transcript(
            id=f"batch2-{i}",
            metadata={"category": "math", "temperature": 0.7},
        )
        for i in range(5)
    ]
    await parquet_db.insert(batch2)

    # Query should work across both schemas (files may be compacted)
    all_results = [info async for info in parquet_db.select([], None, False)]
    assert len(all_results) == 10

    # First batch has NULL temperature
    batch1_results = [
        info async for info in parquet_db.select([c.category == "science"], None, False)
    ]
    assert len(batch1_results) == 5
    for info in batch1_results:
        assert info.metadata.get("temperature") is None
        assert info.metadata.get("difficulty") == "hard"

    # Second batch has NULL difficulty
    batch2_results = [
        info async for info in parquet_db.select([c.category == "math"], None, False)
    ]
    assert len(batch2_results) == 5
    for info in batch2_results:
        assert info.metadata.get("difficulty") is None
        assert info.metadata.get("temperature") == 0.7


@pytest.mark.asyncio
async def test_partitioning_file_and_row_group_levels(test_location: Path) -> None:
    """Test that transcripts are partitioned correctly at both file and row group levels."""
    import pyarrow.parquet as pq

    # Create database with specific size targets for predictable partitioning
    # Use very small sizes to ensure multiple files and row groups
    # (sizes account for compression-aware estimation in ParquetTranscriptsDB)
    target_file_size_mb = 0.002  # 2KB per file
    row_group_size_mb = 0.001  # 1KB per row group
    parquet_db = ParquetTranscriptsDB(
        str(test_location),
        target_file_size_mb=target_file_size_mb,
        row_group_size_mb=row_group_size_mb,
    )
    await parquet_db.connect()

    try:
        # Create 100 transcripts with substantial content to trigger partitioning
        transcripts = []
        for i in range(100):
            # Create messages with enough content to make transcripts ~2-3KB each
            messages: list[ChatMessage] = [
                ChatMessageUser(content=f"Question {i}: " + "x" * 1000),
                ChatMessageUser(content=f"Follow-up {i}: " + "y" * 500),
            ]
            transcripts.append(
                create_sample_transcript(
                    id=f"sample-{i:03d}",
                    source_id=f"eval-{i // 10:02d}",
                    source_uri=f"test://log-{i:03d}.json",
                    model="gpt-4",
                    metadata={
                        "index": i,
                        "description": "z" * 200,  # Add more bulk to metadata
                    },
                    messages=messages,
                )
            )

        await parquet_db.insert(transcripts)

        # Verify file-level partitioning
        parquet_files = sorted(test_location.glob(PARQUET_TRANSCRIPTS_GLOB))
        assert len(parquet_files) >= 3, (
            f"Expected at least 3 files with {target_file_size_mb}MB target, "
            f"got {len(parquet_files)}"
        )

        # Verify row group level partitioning by inspecting Parquet metadata
        total_row_groups = 0
        for parquet_file in parquet_files:
            metadata = pq.read_metadata(parquet_file)
            num_row_groups = metadata.num_row_groups

            # Each file should have multiple row groups given our small row_group_size
            assert num_row_groups >= 1, f"File {parquet_file.name} has no row groups"
            total_row_groups += num_row_groups

            # Verify row group sizes are approximately as configured
            for rg_idx in range(num_row_groups):
                rg = metadata.row_group(rg_idx)
                rg_size_bytes = rg.total_byte_size
                rg_size_mb = rg_size_bytes / (1024 * 1024)

                # Row groups should be roughly the configured size
                # (allow some overhead/variation, but should be in the ballpark)
                # Last row group in file may be smaller
                is_last_rg_in_file = rg_idx == num_row_groups - 1
                if not is_last_rg_in_file:
                    assert rg_size_mb <= row_group_size_mb * 2, (
                        f"Row group {rg_idx} in {parquet_file.name} is {rg_size_mb:.3f}MB, "
                        f"expected ~{row_group_size_mb}MB (allowing 2x for overhead)"
                    )

        # Should have multiple row groups across all files
        assert total_row_groups >= len(parquet_files), (
            f"Expected at least {len(parquet_files)} row groups total, "
            f"got {total_row_groups}"
        )

        # Verify data integrity - all transcripts should be queryable
        transcript_ids = await parquet_db.transcript_ids([], None)
        assert len(transcript_ids) == 100, (
            f"Expected 100 transcripts, got {len(transcript_ids)}"
        )

    finally:
        await parquet_db.disconnect()


@pytest.mark.asyncio
async def test_indexed_database_isolation(test_location: Path) -> None:
    """Test that indexed databases are isolated - each database only sees its own index.

    When multiple databases exist in a directory hierarchy, each with its own index,
    opening a database from a specific location only sees that database's transcripts.
    """
    # Create subdirectories for separate databases
    subdir1 = test_location / "batch1"
    subdir2 = test_location / "batch2" / "nested"
    subdir1.mkdir(parents=True)
    subdir2.mkdir(parents=True)

    # Create database and insert transcripts to root
    db = ParquetTranscriptsDB(str(test_location))
    await db.connect()
    root_transcripts = [
        create_sample_transcript(
            id=f"root-{i}", source_id="root-eval", metadata={"location": "root"}
        )
        for i in range(3)
    ]
    await db.insert(root_transcripts)
    await db.disconnect()

    # Create separate database in subdir1
    db1 = ParquetTranscriptsDB(str(subdir1))
    await db1.connect()
    subdir1_transcripts = [
        create_sample_transcript(
            id=f"sub1-{i}", source_id="sub1-eval", metadata={"location": "subdir1"}
        )
        for i in range(3)
    ]
    await db1.insert(subdir1_transcripts)
    await db1.disconnect()

    # Create separate database in subdir2
    db2 = ParquetTranscriptsDB(str(subdir2))
    await db2.connect()
    subdir2_transcripts = [
        create_sample_transcript(
            id=f"sub2-{i}", source_id="sub2-eval", metadata={"location": "subdir2"}
        )
        for i in range(3)
    ]
    await db2.insert(subdir2_transcripts)
    await db2.disconnect()

    # Open from root - should only see root's 3 transcripts (uses root's index)
    db_root = ParquetTranscriptsDB(str(test_location))
    await db_root.connect()
    root_ids = await db_root.transcript_ids([], None)
    assert len(root_ids) == 3
    root_results = [info async for info in db_root.select([], None, False)]
    assert all(info.metadata.get("location") == "root" for info in root_results)
    await db_root.disconnect()

    # Open from subdir1 - should only see subdir1's 3 transcripts
    db_sub1 = ParquetTranscriptsDB(str(subdir1))
    await db_sub1.connect()
    sub1_ids = await db_sub1.transcript_ids([], None)
    assert len(sub1_ids) == 3
    sub1_results = [info async for info in db_sub1.select([], None, False)]
    assert all(info.metadata.get("location") == "subdir1" for info in sub1_results)
    await db_sub1.disconnect()

    # Open from subdir2 - should only see subdir2's 3 transcripts
    db_sub2 = ParquetTranscriptsDB(str(subdir2))
    await db_sub2.connect()
    sub2_ids = await db_sub2.transcript_ids([], None)
    assert len(sub2_ids) == 3
    sub2_results = [info async for info in db_sub2.select([], None, False)]
    assert all(info.metadata.get("location") == "subdir2" for info in sub2_results)
    await db_sub2.disconnect()


@pytest.mark.asyncio
async def test_file_uri_discovery(test_location: Path) -> None:
    """Test that parquet files are discovered when location is a file: URI."""
    # Create and populate database using regular path
    db = ParquetTranscriptsDB(str(test_location))
    await db.connect()
    transcripts = [
        create_sample_transcript(id=f"uri-{i}", metadata={"index": i}) for i in range(3)
    ]
    await db.insert(transcripts)
    await db.disconnect()

    # Now create a new database using file: URI
    file_uri = test_location.as_uri()  # Converts to file:///path/to/dir
    db_uri = ParquetTranscriptsDB(file_uri)
    await db_uri.connect()

    try:
        # Should discover and read all transcripts
        transcript_ids = await db_uri.transcript_ids([], None)
        assert len(transcript_ids) == 3
    finally:
        await db_uri.disconnect()


# RecordBatchReader Tests
def create_record_batch_reader(
    transcript_ids: list[str],
    include_source_fields: bool = True,
    include_content_fields: bool = True,
    metadata: dict[str, list[Any]] | None = None,
) -> pa.RecordBatchReader:
    """Create a RecordBatchReader for testing.

    Args:
        transcript_ids: List of transcript IDs.
        include_source_fields: Include source_type, source_id, source_uri.
        include_content_fields: Include messages and events columns.
        metadata: Additional metadata columns as {name: [values]}.

    Returns:
        PyArrow RecordBatchReader.
    """
    data: dict[str, list[Any] | pa.Array[Any]] = {"transcript_id": transcript_ids}

    if include_source_fields:
        data["source_type"] = ["test"] * len(transcript_ids)
        data["source_id"] = [f"source-{i}" for i in range(len(transcript_ids))]
        data["source_uri"] = [f"test://uri/{i}" for i in range(len(transcript_ids))]

    if include_content_fields:
        data["messages"] = ["[]"] * len(transcript_ids)
        data["events"] = ["[]"] * len(transcript_ids)

    if metadata:
        data.update(metadata)

    table = pa.table(data)
    return table.to_reader()


@pytest.mark.asyncio
async def test_insert_record_batch_reader_all_columns(test_location: Path) -> None:
    """Test inserting via RecordBatchReader with all columns."""
    db = ParquetTranscriptsDB(str(test_location))
    await db.connect()

    try:
        # Create RecordBatchReader with all columns
        reader = create_record_batch_reader(
            transcript_ids=["rb-001", "rb-002", "rb-003"],
            include_source_fields=True,
            include_content_fields=True,
            metadata={"model": ["gpt-4", "gpt-4", "gpt-4"]},
        )

        # Insert
        await db.insert(reader)

        # Verify count
        transcript_ids = await db.transcript_ids([], None)
        assert len(transcript_ids) == 3

        # Verify data is queryable
        results = [info async for info in db.select([], None, False)]
        assert len(results) == 3

        # Verify fields are populated
        info = results[0]
        assert info.transcript_id.startswith("rb-")
        assert info.source_type == "test"
        assert info.source_id is not None
        assert info.source_uri is not None
    finally:
        await db.disconnect()


@pytest.mark.asyncio
async def test_insert_record_batch_reader_minimal_schema(test_location: Path) -> None:
    """Test inserting via RecordBatchReader with only transcript_id."""
    db = ParquetTranscriptsDB(str(test_location))
    await db.connect()

    try:
        # Create RecordBatchReader with minimal schema
        reader = create_record_batch_reader(
            transcript_ids=["min-001", "min-002"],
            include_source_fields=False,
            include_content_fields=False,
        )

        # Insert
        await db.insert(reader)

        # Verify select() returns None for optional fields
        results = [info async for info in db.select([], None, False)]
        assert len(results) == 2

        info = results[0]
        assert info.transcript_id.startswith("min-")
        assert info.source_type is None
        assert info.source_id is None
        assert info.source_uri is None
    finally:
        await db.disconnect()


@pytest.mark.asyncio
async def test_insert_record_batch_reader_duplicate_filtering(
    test_location: Path,
) -> None:
    """Test that duplicate transcript_ids are filtered during RecordBatchReader insert."""
    db = ParquetTranscriptsDB(str(test_location))
    await db.connect()

    try:
        # First insert some transcripts
        transcripts = [
            create_sample_transcript(id="dup-001"),
            create_sample_transcript(id="dup-002"),
        ]
        await db.insert(transcripts)

        # Create RecordBatchReader with mix of new and duplicate IDs
        reader = create_record_batch_reader(
            transcript_ids=["dup-001", "dup-002", "dup-003", "dup-004"],
            include_source_fields=True,
            include_content_fields=True,
        )

        # Insert - duplicates should be filtered
        await db.insert(reader)

    finally:
        await db.disconnect()


@pytest.mark.asyncio
async def test_insert_record_batch_reader_batch_size_splitting(
    test_location: Path,
) -> None:
    """Test that large RecordBatchReader data is split into multiple files."""
    # Use very small target file size to force splitting
    db = ParquetTranscriptsDB(str(test_location), target_file_size_mb=0.001)
    await db.connect()

    try:
        # Create many transcripts with content to exceed file size
        transcript_ids = [f"split-{i:04d}" for i in range(100)]
        messages = ['[{"role": "user", "content": "' + "x" * 1000 + '"}]'] * 100
        events = ["[]"] * 100

        table = pa.table(
            {
                "transcript_id": transcript_ids,
                "source_type": ["test"] * 100,
                "source_id": [f"src-{i}" for i in range(100)],
                "source_uri": [f"uri-{i}" for i in range(100)],
                "messages": messages,
                "events": events,
            }
        )
        # Use small chunk size to create multiple batches for realistic testing
        batches = table.to_batches(max_chunksize=10)
        reader = pa.RecordBatchReader.from_batches(table.schema, batches)

        # Insert
        await db.insert(reader)

        # Verify multiple files were created
        parquet_files = list(test_location.glob(PARQUET_TRANSCRIPTS_GLOB))
        assert len(parquet_files) > 1

        # Verify all data is queryable
        assert len(await db.transcript_ids([], None)) == 100
    finally:
        await db.disconnect()


# Schema Validation Tests
@pytest.mark.asyncio
async def test_insert_record_batch_reader_missing_transcript_id(
    test_location: Path,
) -> None:
    """Test that missing transcript_id raises ValueError."""
    db = ParquetTranscriptsDB(str(test_location))
    await db.connect()

    try:
        # Create table without transcript_id
        table = pa.table({"source_type": ["test", "test"]})
        reader = table.to_reader()

        # Verify ValueError is raised
        with pytest.raises(ValueError, match="transcript_id"):
            await db.insert(reader)
    finally:
        await db.disconnect()


@pytest.mark.asyncio
async def test_insert_record_batch_reader_invalid_transcript_id_type(
    test_location: Path,
) -> None:
    """Test that non-string transcript_id raises ValueError."""
    db = ParquetTranscriptsDB(str(test_location))
    await db.connect()

    try:
        # Create table with int64 transcript_id
        table = pa.table({"transcript_id": [1, 2, 3]})
        reader = table.to_reader()

        # Verify ValueError is raised
        with pytest.raises(ValueError, match="string type"):
            await db.insert(reader)
    finally:
        await db.disconnect()


@pytest.mark.asyncio
async def test_insert_record_batch_reader_invalid_optional_column_type(
    test_location: Path,
) -> None:
    """Test that non-string optional columns raise ValueError."""
    db = ParquetTranscriptsDB(str(test_location))
    await db.connect()

    try:
        # Create table with int64 source_type
        table = pa.table({"transcript_id": ["t1", "t2"], "source_type": [1, 2]})
        reader = table.to_reader()

        # Verify ValueError is raised
        with pytest.raises(ValueError, match="string type"):
            await db.insert(reader)
    finally:
        await db.disconnect()


# Select with Missing Columns Tests
@pytest.mark.asyncio
async def test_select_missing_optional_columns(test_location: Path) -> None:
    """Test that select() returns None for missing optional columns."""
    db = ParquetTranscriptsDB(str(test_location))
    await db.connect()

    try:
        # Insert via RecordBatchReader with minimal schema
        reader = create_record_batch_reader(
            transcript_ids=["sel-001", "sel-002"],
            include_source_fields=False,
            include_content_fields=False,
        )
        await db.insert(reader)

        # Verify select() returns TranscriptInfo with None for optional fields
        results = [info async for info in db.select([], None, False)]
        assert len(results) == 2

        for info in results:
            assert info.transcript_id.startswith("sel-")
            assert info.source_type is None
            assert info.source_id is None
            assert info.source_uri is None
    finally:
        await db.disconnect()


# Read with Missing Content Columns Tests
@pytest.mark.asyncio
async def test_read_missing_messages_column(test_location: Path) -> None:
    """Test that read() handles missing messages column gracefully."""
    db = ParquetTranscriptsDB(str(test_location))
    await db.connect()

    try:
        # Insert via RecordBatchReader without messages column (but with events)
        table = pa.table(
            {
                "transcript_id": ["rm-001", "rm-002"],
                "source_type": ["test", "test"],
                "source_id": ["src-1", "src-2"],
                "source_uri": ["uri-1", "uri-2"],
                "events": ["[]", "[]"],
            }
        )
        reader = table.to_reader()
        await db.insert(reader)

        # Get transcript info
        results = [info async for info in db.select([], None, False)]
        assert len(results) == 2

        # Read with messages requested - should return empty
        content = TranscriptContent(messages="all", events=None)
        transcript = await db.read(results[0], content)
        assert transcript.messages == []
    finally:
        await db.disconnect()


@pytest.mark.asyncio
async def test_read_missing_events_column(test_location: Path) -> None:
    """Test that read() handles missing events column gracefully."""
    db = ParquetTranscriptsDB(str(test_location))
    await db.connect()

    try:
        # Insert via RecordBatchReader without events column (but with messages)
        table = pa.table(
            {
                "transcript_id": ["re-001", "re-002"],
                "source_type": ["test", "test"],
                "source_id": ["src-1", "src-2"],
                "source_uri": ["uri-1", "uri-2"],
                "messages": ["[]", "[]"],
            }
        )
        reader = table.to_reader()
        await db.insert(reader)

        # Get transcript info
        results = [info async for info in db.select([], None, False)]
        assert len(results) == 2

        # Read with events requested - should return empty
        content = TranscriptContent(messages=None, events="all")
        transcript = await db.read(results[0], content)
        assert transcript.events == []
    finally:
        await db.disconnect()


@pytest.mark.asyncio
async def test_read_missing_both_content_columns(test_location: Path) -> None:
    """Test that read() handles missing messages and events columns."""
    db = ParquetTranscriptsDB(str(test_location))
    await db.connect()

    try:
        # Insert via RecordBatchReader with only transcript_id
        reader = create_record_batch_reader(
            transcript_ids=["rb-001", "rb-002"],
            include_source_fields=False,
            include_content_fields=False,
        )
        await db.insert(reader)

        # Get transcript info
        results = [info async for info in db.select([], None, False)]
        assert len(results) == 2

        # Read with both messages and events requested - should return empty
        content = TranscriptContent(messages="all", events="all")
        transcript = await db.read(results[0], content)
        assert transcript.messages == []
        assert transcript.events == []
    finally:
        await db.disconnect()


# File Columns Cache Tests
@pytest.mark.asyncio
async def test_file_columns_cache_populated(test_location: Path) -> None:
    """Test that _file_columns_cache is populated after read() with missing columns."""
    import pyarrow.parquet as pq

    # Write a parquet file directly (simulating external data lake without messages)
    table = pa.table(
        {
            "transcript_id": ["cache-001", "cache-002"],
            "source_type": ["test", "test"],
            "source_id": ["src-1", "src-2"],
            "source_uri": ["uri-1", "uri-2"],
            "events": ["[]", "[]"],
        }
    )
    parquet_path = test_location / "transcripts_external_001.parquet"
    pq.write_table(table, str(parquet_path))

    db = ParquetTranscriptsDB(str(test_location))
    await db.connect()

    try:
        # Cache should be empty initially
        assert len(db._file_columns_cache) == 0

        # Get transcript info
        results = [info async for info in db.select([], None, False)]
        assert len(results) == 2

        # Read a transcript (triggers cache population on BinderException)
        content = TranscriptContent(messages="all", events="all")
        await db.read(results[0], content)

        # Verify _file_columns_cache is now populated
        assert len(db._file_columns_cache) == 1

        # Verify the cached columns include expected columns
        cached_columns = list(db._file_columns_cache.values())[0]
        assert "transcript_id" in cached_columns
        assert "events" in cached_columns
        assert "messages" not in cached_columns  # This was missing
    finally:
        await db.disconnect()


@pytest.mark.asyncio
async def test_file_columns_cache_reused(test_location: Path) -> None:
    """Test that cached column info is reused on subsequent reads."""
    import pyarrow.parquet as pq

    # Write a parquet file directly (simulating external data lake without messages)
    table = pa.table(
        {
            "transcript_id": ["reuse-001", "reuse-002", "reuse-003"],
            "source_type": ["test", "test", "test"],
            "source_id": ["src-1", "src-2", "src-3"],
            "source_uri": ["uri-1", "uri-2", "uri-3"],
            "events": ["[]", "[]", "[]"],
        }
    )
    parquet_path = test_location / "transcripts_external_002.parquet"
    pq.write_table(table, str(parquet_path))

    db = ParquetTranscriptsDB(str(test_location))
    await db.connect()

    try:
        # Get transcript info
        results = [info async for info in db.select([], None, False)]
        assert len(results) == 3

        # Read first transcript (populates cache)
        content = TranscriptContent(messages="all", events="all")
        await db.read(results[0], content)

        # Verify cache has one entry
        assert len(db._file_columns_cache) == 1

        # Read second and third transcripts from same file
        await db.read(results[1], content)
        await db.read(results[2], content)

        # Cache should still have just one entry (reused, not re-populated)
        assert len(db._file_columns_cache) == 1
    finally:
        await db.disconnect()


# Schema Inference Fallback Tests
@pytest.mark.asyncio
async def test_exclude_clause_fallback_mixed_schemas(test_location: Path) -> None:
    """Test fallback when first file has different content columns than others.

    The schema inference optimization reads schema from the first file only.
    If that schema differs from other files (e.g., first file lacks messages/events
    but later files have them), the fallback should scan all file schemas.
    """
    import pyarrow.parquet as pq

    # First file: NO messages/events columns (sorted first alphabetically)
    table1 = pa.table(
        {
            "transcript_id": ["a-001", "a-002"],
            "source_type": ["test", "test"],
            "custom_field": ["val1", "val2"],
        }
    )
    pq.write_table(table1, str(test_location / "transcripts_aaa_first.parquet"))

    # Second file: HAS messages/events columns (sorted second alphabetically)
    table2 = pa.table(
        {
            "transcript_id": ["b-001", "b-002"],
            "source_type": ["test", "test"],
            "messages": ['[{"role": "user", "content": "hello"}]', "[]"],
            "events": ["[]", "[]"],
        }
    )
    pq.write_table(table2, str(test_location / "transcripts_bbb_second.parquet"))

    # Connect - should handle mixed schemas via fallback
    db = ParquetTranscriptsDB(str(test_location))
    await db.connect()

    try:
        # Should be able to query all transcripts
        results = [info async for info in db.select()]
        assert len(results) == 4

        # Verify we got transcripts from both files
        ids = {r.transcript_id for r in results}
        assert "a-001" in ids
        assert "b-001" in ids

        # Read from second file should return messages
        b_info = next(r for r in results if r.transcript_id == "b-001")
        content = TranscriptContent(messages="all", events=None)
        transcript = await db.read(b_info, content)
        assert len(transcript.messages) == 1
        assert transcript.messages[0].content == "hello"
    finally:
        await db.disconnect()


# Snapshot Tests
@pytest.mark.asyncio
async def test_snapshot_returns_transcript_ids(test_location: Path) -> None:
    """Test that snapshot() returns correct ScanTranscripts with transcript IDs."""
    from inspect_scout._util.constants import TRANSCRIPT_SOURCE_DATABASE

    db = ParquetTranscriptsDB(str(test_location))
    await db.connect()

    try:
        # Insert test transcripts
        transcripts = [
            create_sample_transcript(id=f"snap-{i:03d}", metadata={"index": i})
            for i in range(5)
        ]
        await db.insert(transcripts)

        # Create reader and get snapshot
        reader = TranscriptsViewReader(db, str(test_location), None)
        scan_transcripts = await reader.snapshot()

        # Verify ScanTranscripts structure
        assert scan_transcripts.type == TRANSCRIPT_SOURCE_DATABASE
        assert scan_transcripts.location == str(test_location)

        assert len(scan_transcripts.transcript_ids) == 5
        assert set(scan_transcripts.transcript_ids.keys()) == {
            f"snap-{i:03d}" for i in range(5)
        }

    finally:
        await db.disconnect()


@pytest.mark.asyncio
async def test_snapshot_empty_database(test_location: Path) -> None:
    """Test that snapshot() works correctly with empty database."""
    from inspect_scout._util.constants import TRANSCRIPT_SOURCE_DATABASE

    db = ParquetTranscriptsDB(str(test_location))
    await db.connect()

    try:
        reader = TranscriptsViewReader(db, str(test_location), None)
        scan_transcripts = await reader.snapshot()

        # Verify empty results
        assert scan_transcripts.type == TRANSCRIPT_SOURCE_DATABASE
        assert len(scan_transcripts.transcript_ids) == 0
    finally:
        await db.disconnect()


@pytest.mark.asyncio
async def test_snapshot_legacy_format_restoration(test_location: Path) -> None:
    """Test that legacy snapshot format (with CSV data) is correctly restored."""
    from inspect_scout._scanspec import ScanTranscripts
    from inspect_scout._transcript.database.factory import transcripts_from_db_snapshot
    from inspect_scout._util.constants import TRANSCRIPT_SOURCE_DATABASE

    db = ParquetTranscriptsDB(str(test_location))
    await db.connect()

    try:
        # Insert test transcripts
        transcripts = [
            create_sample_transcript(id=f"legacy-{i:03d}", metadata={"index": i})
            for i in range(3)
        ]
        await db.insert(transcripts)

        # Create a legacy-format snapshot (simulating old saved snapshot)
        legacy_snapshot = ScanTranscripts(
            type=TRANSCRIPT_SOURCE_DATABASE,
            location=str(test_location),
            count=3,
            fields=[{"name": "transcript_id", "type": "string"}],
            data="transcript_id\nlegacy-000\nlegacy-001\nlegacy-002\n",
        )

        # Restore transcripts from legacy snapshot
        restored = transcripts_from_db_snapshot(legacy_snapshot)

        # Verify restoration works - should get exactly those 3 transcripts
        async with restored.reader() as reader:
            restored_ids = [info.transcript_id async for info in reader.index()]

        assert set(restored_ids) == {"legacy-000", "legacy-001", "legacy-002"}
    finally:
        await db.disconnect()


@pytest.mark.asyncio
async def test_snapshot_based_index_creation(test_location: Path) -> None:
    """Test that snapshot can be used to create index without parquet crawl."""
    from inspect_scout._scanspec import ScanTranscripts
    from inspect_scout._util.constants import TRANSCRIPT_SOURCE_DATABASE

    # First, create a database with some transcripts
    db = ParquetTranscriptsDB(str(test_location))
    await db.connect()

    try:
        transcripts = [
            create_sample_transcript(id=f"snap-{i:03d}", metadata={"index": i})
            for i in range(3)
        ]
        await db.insert(transcripts)

        # Get transcript_ids with filenames
        transcript_ids = await db.transcript_ids()
        assert len(transcript_ids) == 3

        # All should have filenames
        for filename in transcript_ids.values():
            assert filename is not None
            assert filename.endswith(".parquet")
    finally:
        await db.disconnect()

    # Now create a new DB instance with the snapshot - this should use the fast path
    snapshot = ScanTranscripts(
        type=TRANSCRIPT_SOURCE_DATABASE,
        location=str(test_location),
        transcript_ids=transcript_ids,
    )

    db2 = ParquetTranscriptsDB(str(test_location), snapshot=snapshot)
    await db2.connect()

    try:
        # Should be able to read transcripts using snapshot-based index
        for tid in transcript_ids:
            info = TranscriptInfo(
                transcript_id=tid,
                source_type="test",
                source_id="source-001",
                source_uri="test://uri",
                metadata={},
            )
            content = TranscriptContent(messages="all", events=None)
            transcript = await db2.read(info, content)
            assert transcript.transcript_id == tid
            assert len(transcript.messages) > 0
    finally:
        await db2.disconnect()


@pytest.mark.asyncio
async def test_exclude_clause_first_file_has_content(test_location: Path) -> None:
    """Test that exclude clause works when first file HAS content columns.

    This is the fast path - schema from first file matches all files.
    """
    import pyarrow.parquet as pq

    # First file: HAS messages/events (sorted first)
    table1 = pa.table(
        {
            "transcript_id": ["a-001"],
            "source_type": ["test"],
            "messages": ['[{"role": "user", "content": "first"}]'],
            "events": ["[]"],
        }
    )
    pq.write_table(table1, str(test_location / "transcripts_aaa.parquet"))

    # Second file: also HAS messages/events (sorted second)
    table2 = pa.table(
        {
            "transcript_id": ["b-001"],
            "source_type": ["test"],
            "messages": ['[{"role": "user", "content": "second"}]'],
            "events": ["[]"],
        }
    )
    pq.write_table(table2, str(test_location / "transcripts_bbb.parquet"))

    db = ParquetTranscriptsDB(str(test_location))
    await db.connect()

    try:
        # Both transcripts should be queryable
        results = [info async for info in db.select()]
        assert len(results) == 2

        # Messages should NOT appear in metadata (excluded from VIEW)
        for info in results:
            assert "messages" not in info.metadata
            assert "events" not in info.metadata

        # But reading content should work
        content = TranscriptContent(messages="all", events=None)
        for info in results:
            transcript = await db.read(info, content)
            assert len(transcript.messages) == 1
    finally:
        await db.disconnect()
