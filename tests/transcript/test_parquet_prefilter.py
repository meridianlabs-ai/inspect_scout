"""Tests for ParquetTranscriptsDB pre-filter optimization.

Tests the query parameter that enables Parquet filter pushdown by applying
WHERE/SHUFFLE/LIMIT during table creation rather than at query time.
"""

from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from inspect_ai.model._chat_message import ChatMessage, ChatMessageUser
from inspect_scout import columns as c
from inspect_scout._transcript.database.parquet import ParquetTranscriptsDB
from inspect_scout._transcript.transcripts import TranscriptsQuery
from inspect_scout._transcript.types import Transcript, TranscriptContent
from pydantic import JsonValue


# Test data helpers
def create_sample_transcript(
    id: str = "test-001",
    source_id: str = "source-001",
    source_uri: str = "test://uri",
    model: str | None = None,
    score: JsonValue | None = None,
    metadata: dict[str, Any] | None = None,
    messages: list[ChatMessage] | None = None,
) -> Transcript:
    """Create a test transcript with customizable fields."""
    return Transcript(
        transcript_id=id,
        source_type="test",
        source_id=source_id,
        source_uri=source_uri,
        model=model,
        score=score,
        metadata=metadata or {},
        messages=messages or [ChatMessageUser(content="Test message")],
        events=[],
    )


def create_test_transcripts(count: int = 100) -> list[Transcript]:
    """Create test transcripts with varied metadata for filter testing."""
    transcripts = []
    models = ["gpt-4", "gpt-3.5-turbo", "claude-3-opus"]
    datasets = ["gsm8k", "humaneval", "mmlu"]

    for i in range(count):
        transcripts.append(
            create_sample_transcript(
                id=f"sample-{i:03d}",
                source_id=f"eval-{i // 10:02d}",
                source_uri=f"test://log-{i:03d}.json",
                model=models[i % 3],
                score=i * 0.01,
                metadata={
                    "dataset": datasets[i % 3],
                    "index": i,
                    "temperature": 0.5 + (i % 5) * 0.1,
                },
                messages=[ChatMessageUser(content=f"Question {i}")],
            )
        )

    return transcripts


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
    return create_test_transcripts(100)


@pytest_asyncio.fixture
async def populated_db(
    test_location: Path, sample_transcripts: list[Transcript]
) -> ParquetTranscriptsDB:
    """Create and populate a database for testing."""
    db = ParquetTranscriptsDB(str(test_location))
    await db.connect()
    await db.insert(sample_transcripts)
    await db.disconnect()
    return db


# Tests
@pytest.mark.asyncio
async def test_prefilter_where_reduces_table_size(
    test_location: Path, populated_db: ParquetTranscriptsDB
) -> None:
    """Test that pre-filter WHERE reduces table size."""
    # Without pre-filter: all 100 transcripts
    db_no_filter = ParquetTranscriptsDB(str(test_location))
    await db_no_filter.connect()
    transcript_ids = await db_no_filter.transcript_ids([], None)
    assert len(transcript_ids) == 100
    await db_no_filter.disconnect()

    # With pre-filter: only gpt-4 transcripts (33 out of 100)
    query = TranscriptsQuery(where=[c.model == "gpt-4"])
    db_filtered = ParquetTranscriptsDB(str(test_location), query=query)
    await db_filtered.connect()
    transcript_ids_filtered = await db_filtered.transcript_ids([], None)
    assert len(transcript_ids_filtered) == 34  # 34 transcripts with model=gpt-4
    await db_filtered.disconnect()


@pytest.mark.asyncio
async def test_prefilter_limit_creates_smaller_table(
    test_location: Path, populated_db: ParquetTranscriptsDB
) -> None:
    """Test that pre-filter LIMIT creates a smaller table."""
    query = TranscriptsQuery(limit=25)
    db = ParquetTranscriptsDB(str(test_location), query=query)
    await db.connect()

    transcript_ids = await db.transcript_ids([], None)
    assert len(transcript_ids) == 25

    # Verify we can iterate through all 25
    results = []
    async for info in db.select([], None, False):
        results.append(info)
    assert len(results) == 25

    await db.disconnect()


@pytest.mark.asyncio
async def test_prefilter_shuffle_deterministic(
    test_location: Path, populated_db: ParquetTranscriptsDB
) -> None:
    """Test that pre-filter SHUFFLE creates deterministic ordering."""
    # Create two DBs with same shuffle seed
    query1 = TranscriptsQuery(shuffle=42, limit=20)
    db1 = ParquetTranscriptsDB(str(test_location), query=query1)
    await db1.connect()

    ids1 = []
    async for info in db1.select([], None, False):
        ids1.append(info.transcript_id)
    await db1.disconnect()

    query2 = TranscriptsQuery(shuffle=42, limit=20)
    db2 = ParquetTranscriptsDB(str(test_location), query=query2)
    await db2.connect()

    ids2 = []
    async for info in db2.select([], None, False):
        ids2.append(info.transcript_id)
    await db2.disconnect()

    # Same seed should produce same order
    assert ids1 == ids2

    # Different seed should produce different order
    query3 = TranscriptsQuery(shuffle=99, limit=20)
    db3 = ParquetTranscriptsDB(str(test_location), query=query3)
    await db3.connect()

    ids3 = []
    async for info in db3.select([], None, False):
        ids3.append(info.transcript_id)
    await db3.disconnect()

    # Different seed should give different order
    assert ids3 != ids1


@pytest.mark.asyncio
async def test_additive_where_filtering(
    test_location: Path, populated_db: ParquetTranscriptsDB
) -> None:
    """Test that query-time WHERE combines with pre-filter WHERE (AND)."""
    # Pre-filter: only gpt-4 (34 transcripts)
    query = TranscriptsQuery(where=[c.model == "gpt-4"])
    db = ParquetTranscriptsDB(str(test_location), query=query)
    await db.connect()

    # Base count
    transcript_ids_base = await db.transcript_ids([], None)
    assert len(transcript_ids_base) == 34

    # Additional filter: index < 30
    # Should get gpt-4 AND index < 30
    transcript_ids_filtered = await db.transcript_ids([c.index < 30], None)
    assert (
        len(transcript_ids_filtered) == 10
    )  # Only 10 gpt-4 transcripts with index < 30

    # Verify the results
    results = []
    async for info in db.select([c.index < 30], None, False):
        results.append(info)
        assert info.model == "gpt-4"
        assert info.metadata["index"] < 30

    assert len(results) == 10

    await db.disconnect()


@pytest.mark.asyncio
async def test_querytime_shuffle_reorders_prefiltered_table(
    test_location: Path, populated_db: ParquetTranscriptsDB
) -> None:
    """Test that query-time shuffle can re-order pre-filtered table."""
    # Pre-filter with shuffle seed 42
    query = TranscriptsQuery(shuffle=42, limit=30)
    db = ParquetTranscriptsDB(str(test_location), query=query)
    await db.connect()

    # Get order with no query-time shuffle (uses pre-filter shuffle)
    ids_preshuffle = []
    async for info in db.select([], None, False):
        ids_preshuffle.append(info.transcript_id)

    # Get order with query-time shuffle (different seed)
    ids_reshuffle = []
    async for info in db.select([], None, shuffle=99):
        ids_reshuffle.append(info.transcript_id)

    # Should have same transcripts but different order
    assert set(ids_preshuffle) == set(ids_reshuffle)
    assert ids_preshuffle != ids_reshuffle

    await db.disconnect()


@pytest.mark.asyncio
async def test_querytime_limit_on_prefiltered_table(
    test_location: Path, populated_db: ParquetTranscriptsDB
) -> None:
    """Test that query-time limit works on pre-filtered table."""
    # Pre-filter to 50 transcripts
    query = TranscriptsQuery(limit=50)
    db = ParquetTranscriptsDB(str(test_location), query=query)
    await db.connect()

    # Table has 50 transcripts
    transcript_ids_all = await db.transcript_ids([], None)
    assert len(transcript_ids_all) == 50

    # Query-time limit to 10
    transcript_ids_limited = await db.transcript_ids([], limit=10)
    assert len(transcript_ids_limited) == 10

    # Verify select honors limit
    results = []
    async for info in db.select([], limit=10, shuffle=False):
        results.append(info)
    assert len(results) == 10

    await db.disconnect()


@pytest.mark.asyncio
async def test_combined_prefilter_where_shuffle_limit(
    test_location: Path, populated_db: ParquetTranscriptsDB
) -> None:
    """Test combined WHERE + SHUFFLE + LIMIT pre-filter."""
    # Pre-filter: only gpt-4, shuffled, limit to 15
    query = TranscriptsQuery(
        where=[c.model == "gpt-4"],
        shuffle=42,
        limit=15,
    )
    db = ParquetTranscriptsDB(str(test_location), query=query)
    await db.connect()

    # Table should have exactly 15 gpt-4 transcripts in shuffled order
    transcript_ids = await db.transcript_ids([], None)
    assert len(transcript_ids) == 15

    # Verify all are gpt-4
    results = []
    async for info in db.select([], None, False):
        results.append(info)
        assert info.model == "gpt-4"

    assert len(results) == 15

    # Verify order is deterministic (same shuffle seed)
    db2 = ParquetTranscriptsDB(str(test_location), query=query)
    await db2.connect()

    ids2 = []
    async for info in db2.select([], None, False):
        ids2.append(info.transcript_id)

    assert [r.transcript_id for r in results] == ids2

    await db.disconnect()
    await db2.disconnect()


@pytest.mark.asyncio
async def test_prefilter_empty_results(
    test_location: Path, populated_db: ParquetTranscriptsDB
) -> None:
    """Test pre-filter that matches no transcripts."""
    # Filter that matches nothing
    query = TranscriptsQuery(where=[c.model == "nonexistent-model"])
    db = ParquetTranscriptsDB(str(test_location), query=query)
    await db.connect()

    transcript_ids = await db.transcript_ids([], None)
    assert len(transcript_ids) == 0

    results = []
    async for info in db.select([], None, False):
        results.append(info)
    assert len(results) == 0

    await db.disconnect()


@pytest.mark.asyncio
async def test_no_prefilter_backward_compatibility(
    test_location: Path, populated_db: ParquetTranscriptsDB
) -> None:
    """Test that no pre-filter (query=None) maintains backward compatibility."""
    # No pre-filter (old behavior)
    db = ParquetTranscriptsDB(str(test_location))
    await db.connect()

    # Should have all transcripts
    transcript_ids_all = await db.transcript_ids([], None)
    assert len(transcript_ids_all) == 100

    # Query-time filtering should work
    transcript_ids_gpt4 = await db.transcript_ids([c.model == "gpt-4"], None)
    assert len(transcript_ids_gpt4) == 34

    # Query-time limit should work
    results = []
    async for info in db.select([], limit=10, shuffle=False):
        results.append(info)
    assert len(results) == 10

    # Query-time shuffle should work
    ids_shuffled = []
    async for info in db.select([], limit=10, shuffle=42):
        ids_shuffled.append(info.transcript_id)
    assert len(ids_shuffled) == 10

    await db.disconnect()


@pytest.mark.asyncio
async def test_read_works_with_prefiltered_db(
    test_location: Path, populated_db: ParquetTranscriptsDB
) -> None:
    """Test that read() still works correctly with pre-filtered DB."""
    # Pre-filter to gpt-4 only
    query = TranscriptsQuery(where=[c.model == "gpt-4"])
    db = ParquetTranscriptsDB(str(test_location), query=query)
    await db.connect()

    # Get a transcript info
    info = None
    async for t in db.select([], limit=1, shuffle=False):
        info = t
        break

    assert info is not None

    # Read full content
    transcript = await db.read(info, TranscriptContent(messages="all", events="all"))

    assert transcript.transcript_id == info.transcript_id
    assert transcript.model == "gpt-4"
    assert len(transcript.messages) > 0
    # Verify message content (handle both string and list types)
    content = transcript.messages[0].content
    if isinstance(content, str):
        assert content.startswith("Question")
    else:
        assert len(content) > 0

    await db.disconnect()


@pytest.mark.asyncio
async def test_multiple_where_conditions_in_prefilter(
    test_location: Path, populated_db: ParquetTranscriptsDB
) -> None:
    """Test pre-filter with multiple WHERE conditions."""
    # Pre-filter: gpt-4 AND gsm8k dataset
    query = TranscriptsQuery(where=[c.model == "gpt-4", c.dataset == "gsm8k"])
    db = ParquetTranscriptsDB(str(test_location), query=query)
    await db.connect()

    # Count should reflect both conditions (AND)
    transcript_ids = await db.transcript_ids([], None)

    # Verify results match both conditions
    results = []
    async for info in db.select([], None, False):
        results.append(info)
        assert info.model == "gpt-4"
        assert info.metadata["dataset"] == "gsm8k"

    assert len(results) == len(transcript_ids)

    await db.disconnect()


@pytest.mark.asyncio
async def test_prefilter_with_complex_conditions(
    test_location: Path, populated_db: ParquetTranscriptsDB
) -> None:
    """Test pre-filter with complex query conditions."""
    # Pre-filter: (gpt-4 OR claude) AND index >= 50
    query = TranscriptsQuery(
        where=[
            (c.model == "gpt-4") | (c.model == "claude-3-opus"),
            c.index >= 50,
        ]
    )
    db = ParquetTranscriptsDB(str(test_location), query=query)
    await db.connect()

    # Verify conditions are applied
    results = []
    async for info in db.select([], None, False):
        results.append(info)
        assert info.model in ["gpt-4", "claude-3-opus"]
        assert info.metadata["index"] >= 50

    assert len(results) > 0

    await db.disconnect()
