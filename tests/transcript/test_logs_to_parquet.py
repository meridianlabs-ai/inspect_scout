"""Tests for importing eval logs into Parquet database and verifying query equivalence."""

import json
from pathlib import Path
from typing import Any, AsyncIterator

import pytest
import pytest_asyncio
from inspect_scout import metadata as m
from inspect_scout import transcripts_from
from inspect_scout._transcript.database.parquet import ParquetTranscriptsDB
from inspect_scout._transcript.transcripts import Transcripts
from inspect_scout._transcript.types import Transcript, TranscriptContent

# Path to test logs
TEST_LOGS_DIR = Path(__file__).parent.parent / "recorder" / "logs"


@pytest.fixture
def log_transcripts() -> Transcripts:
    """Load transcripts from test eval logs."""
    return transcripts_from(str(TEST_LOGS_DIR))


@pytest.fixture
def test_db_location(tmp_path: Path) -> Path:
    """Create temporary directory for Parquet database."""
    location = tmp_path / "transcript_db"
    location.mkdir(parents=True, exist_ok=True)
    return location


@pytest_asyncio.fixture
async def parquet_db(test_db_location: Path) -> AsyncIterator[ParquetTranscriptsDB]:
    """Create and connect to a ParquetTranscriptDB."""
    db = ParquetTranscriptsDB(str(test_db_location))
    await db.connect()
    yield db
    await db.disconnect()


@pytest_asyncio.fixture
async def populated_parquet_db(
    parquet_db: ParquetTranscriptsDB, log_transcripts: Transcripts
) -> ParquetTranscriptsDB:
    """Create a Parquet database populated with test logs."""
    # Import all transcripts from logs into the Parquet database
    await parquet_db.insert(log_transcripts)
    return parquet_db


@pytest.fixture
def parquet_transcripts(
    test_db_location: Path, populated_parquet_db: ParquetTranscriptsDB
) -> Transcripts:
    """Get Transcripts interface to the populated Parquet database."""
    return transcripts_from(str(test_db_location))


async def get_transcript_ids(transcripts: Transcripts) -> list[str]:
    """Get list of transcript IDs from a Transcripts source."""
    async with transcripts.reader() as reader:
        return [info.transcript_id async for info in reader.index()]


async def get_transcript_count(transcripts: Transcripts) -> int:
    """Get count of transcripts from a Transcripts source."""
    async with transcripts.reader() as reader:
        return await reader.count()


async def read_full_transcript(
    transcripts: Transcripts, transcript_id: str
) -> Transcript:
    """Read a full transcript with all messages and events."""
    async with transcripts.reader() as reader:
        async for info in reader.index():
            if info.transcript_id == transcript_id:
                return await reader.read(
                    info, TranscriptContent(messages="all", events="all")
                )
    raise ValueError(f"Transcript {transcript_id} not found")


def normalize_metadata_value(value: Any) -> Any:
    """Normalize metadata values for comparison.

    Converts JSON strings to their parsed equivalents for comparison.
    """
    if isinstance(value, str):
        # Try to parse as JSON
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return value
    return value


def assert_transcripts_equal(t1: Transcript, t2: Transcript) -> None:
    """Assert that two transcripts are equal in all aspects."""
    # Basic fields
    assert t1.transcript_id == t2.transcript_id
    assert t1.source_type == t2.source_type
    assert t1.source_id == t2.source_id

    # Metadata (keys and values)
    assert set(t1.metadata.keys()) == set(t2.metadata.keys())
    for key in t1.metadata:
        # Normalize both values for comparison (handles JSON string vs dict)
        v1 = normalize_metadata_value(t1.metadata[key])
        v2 = normalize_metadata_value(t2.metadata[key])
        assert v1 == v2, f"Metadata key {key} differs: {v1} != {v2}"

    # Messages
    assert len(t1.messages) == len(t2.messages)
    for i, (m1, m2) in enumerate(zip(t1.messages, t2.messages, strict=True)):
        assert type(m1) is type(m2), f"Message {i} type differs"
        assert m1.role == m2.role, f"Message {i} role differs"
        assert m1.content == m2.content, f"Message {i} content differs"

    # Events
    assert len(t1.events) == len(t2.events)
    for i, (e1, e2) in enumerate(zip(t1.events, t2.events, strict=True)):
        assert type(e1) is type(e2), f"Event {i} type differs: {type(e1)} vs {type(e2)}"
        # Compare the event objects (they should be equal if same type and data)
        assert e1 == e2, f"Event {i} differs"


@pytest.mark.asyncio
async def test_basic_import_and_count(
    log_transcripts: Transcripts, parquet_transcripts: Transcripts
) -> None:
    """Test basic import and verify transcript count matches."""
    log_count = await get_transcript_count(log_transcripts)
    parquet_count = await get_transcript_count(parquet_transcripts)

    assert log_count > 0, "Should have transcripts from test logs"
    assert log_count == parquet_count, "Parquet DB should have same count as logs"


@pytest.mark.asyncio
async def test_query_simple_equality(
    log_transcripts: Transcripts, parquet_transcripts: Transcripts
) -> None:
    """Test simple equality filter works the same on both sources."""
    # Query for specific task
    log_filtered = log_transcripts.where(m.task_name == "popularity")
    parquet_filtered = parquet_transcripts.where(m.task_name == "popularity")

    log_ids = await get_transcript_ids(log_filtered)
    parquet_ids = await get_transcript_ids(parquet_filtered)

    assert len(log_ids) > 0, "Should find some popularity transcripts"
    assert log_ids == parquet_ids, "Should return same IDs in same order"


@pytest.mark.asyncio
async def test_query_simple_inequality(
    log_transcripts: Transcripts, parquet_transcripts: Transcripts
) -> None:
    """Test inequality filter works the same on both sources."""
    log_filtered = log_transcripts.where(m.task_name != "popularity")
    parquet_filtered = parquet_transcripts.where(m.task_name != "popularity")

    log_ids = await get_transcript_ids(log_filtered)
    parquet_ids = await get_transcript_ids(parquet_filtered)

    assert len(log_ids) > 0, "Should find non-popularity transcripts"
    assert log_ids == parquet_ids, "Should return same IDs in same order"


@pytest.mark.asyncio
async def test_query_greater_equal(
    log_transcripts: Transcripts, parquet_transcripts: Transcripts
) -> None:
    """Test greater-than-or-equal filter works the same on both sources."""
    log_filtered = log_transcripts.where(m.epoch >= 0)
    parquet_filtered = parquet_transcripts.where(m.epoch >= 0)

    log_ids = await get_transcript_ids(log_filtered)
    parquet_ids = await get_transcript_ids(parquet_filtered)

    assert log_ids == parquet_ids, "Should return same IDs in same order"


@pytest.mark.asyncio
async def test_query_in_operator(
    log_transcripts: Transcripts, parquet_transcripts: Transcripts
) -> None:
    """Test IN operator works the same on both sources."""
    tasks = ["popularity", "security-guide"]
    log_filtered = log_transcripts.where(m.task_name.in_(tasks))
    parquet_filtered = parquet_transcripts.where(m.task_name.in_(tasks))

    log_ids = await get_transcript_ids(log_filtered)
    parquet_ids = await get_transcript_ids(parquet_filtered)

    assert len(log_ids) > 0, "Should find transcripts matching tasks"
    assert log_ids == parquet_ids, "Should return same IDs in same order"


@pytest.mark.asyncio
async def test_query_null_check(
    log_transcripts: Transcripts, parquet_transcripts: Transcripts
) -> None:
    """Test NULL check works the same on both sources."""
    log_filtered = log_transcripts.where(m.error.is_null())
    parquet_filtered = parquet_transcripts.where(m.error.is_null())

    log_ids = await get_transcript_ids(log_filtered)
    parquet_ids = await get_transcript_ids(parquet_filtered)

    assert log_ids == parquet_ids, "Should return same IDs in same order"


@pytest.mark.asyncio
async def test_query_and_operator(
    log_transcripts: Transcripts, parquet_transcripts: Transcripts
) -> None:
    """Test AND operator works the same on both sources."""
    condition = (m.task_name == "popularity") & (m.epoch == 0)
    log_filtered = log_transcripts.where(condition)
    parquet_filtered = parquet_transcripts.where(condition)

    log_ids = await get_transcript_ids(log_filtered)
    parquet_ids = await get_transcript_ids(parquet_filtered)

    assert log_ids == parquet_ids, "Should return same IDs in same order"


@pytest.mark.asyncio
async def test_query_or_operator(
    log_transcripts: Transcripts, parquet_transcripts: Transcripts
) -> None:
    """Test OR operator works the same on both sources."""
    condition = (m.task_name == "popularity") | (m.task_name == "security-guide")
    log_filtered = log_transcripts.where(condition)
    parquet_filtered = parquet_transcripts.where(condition)

    log_ids = await get_transcript_ids(log_filtered)
    parquet_ids = await get_transcript_ids(parquet_filtered)

    assert len(log_ids) > 0, "Should find transcripts"
    assert log_ids == parquet_ids, "Should return same IDs in same order"


@pytest.mark.asyncio
async def test_query_not_operator(
    log_transcripts: Transcripts, parquet_transcripts: Transcripts
) -> None:
    """Test NOT operator works the same on both sources."""
    condition = ~(m.task_name == "popularity")
    log_filtered = log_transcripts.where(condition)
    parquet_filtered = parquet_transcripts.where(condition)

    log_ids = await get_transcript_ids(log_filtered)
    parquet_ids = await get_transcript_ids(parquet_filtered)

    assert len(log_ids) > 0, "Should find non-popularity transcripts"
    assert log_ids == parquet_ids, "Should return same IDs in same order"


@pytest.mark.asyncio
async def test_query_limit(
    log_transcripts: Transcripts, parquet_transcripts: Transcripts
) -> None:
    """Test limit works the same on both sources."""
    log_filtered = log_transcripts.limit(2)
    parquet_filtered = parquet_transcripts.limit(2)

    log_ids = await get_transcript_ids(log_filtered)
    parquet_ids = await get_transcript_ids(parquet_filtered)

    assert len(log_ids) == 2, "Should limit to 2 transcripts"
    assert len(parquet_ids) == 2, "Should limit to 2 transcripts"
    assert log_ids == parquet_ids, "Should return same IDs in same order"


@pytest.mark.asyncio
async def test_query_shuffle_deterministic(
    log_transcripts: Transcripts, parquet_transcripts: Transcripts
) -> None:
    """Test shuffle with seed works the same on both sources."""
    log_filtered = log_transcripts.shuffle(seed=42)
    parquet_filtered = parquet_transcripts.shuffle(seed=42)

    log_ids = await get_transcript_ids(log_filtered)
    parquet_ids = await get_transcript_ids(parquet_filtered)

    # With same seed, order should be identical
    assert log_ids == parquet_ids, "Should return same IDs in same order with same seed"

    # Verify it's actually shuffled (not in original order)
    original_log_ids = await get_transcript_ids(log_transcripts)
    assert log_ids != original_log_ids, "Should be shuffled from original order"


@pytest.mark.asyncio
async def test_full_content_verification(
    log_transcripts: Transcripts, parquet_transcripts: Transcripts
) -> None:
    """Test that full transcript content (messages and events) matches."""
    # Get first few transcript IDs
    log_ids = await get_transcript_ids(log_transcripts.limit(3))

    for transcript_id in log_ids:
        log_transcript = await read_full_transcript(log_transcripts, transcript_id)
        parquet_transcript = await read_full_transcript(
            parquet_transcripts, transcript_id
        )

        assert_transcripts_equal(log_transcript, parquet_transcript)


@pytest.mark.asyncio
async def test_chained_queries(
    log_transcripts: Transcripts, parquet_transcripts: Transcripts
) -> None:
    """Test complex chained queries work the same on both sources."""
    # Chain multiple operations
    log_filtered = (
        log_transcripts.where(m.task_name != "popularity").limit(5).shuffle(seed=42)
    )
    parquet_filtered = (
        parquet_transcripts.where(m.task_name != "popularity").limit(5).shuffle(seed=42)
    )

    log_ids = await get_transcript_ids(log_filtered)
    parquet_ids = await get_transcript_ids(parquet_filtered)

    assert len(log_ids) <= 5, "Should limit to 5 transcripts"
    assert log_ids == parquet_ids, "Should return same IDs in same order"


@pytest.mark.asyncio
async def test_multiple_where_clauses(
    log_transcripts: Transcripts, parquet_transcripts: Transcripts
) -> None:
    """Test multiple sequential where clauses work the same on both sources."""
    # Multiple where calls should be ANDed together
    log_filtered = log_transcripts.where(m.epoch >= 0).where(
        m.task_name.in_(["popularity", "security-guide"])
    )
    parquet_filtered = parquet_transcripts.where(m.epoch >= 0).where(
        m.task_name.in_(["popularity", "security-guide"])
    )

    log_ids = await get_transcript_ids(log_filtered)
    parquet_ids = await get_transcript_ids(parquet_filtered)

    assert log_ids == parquet_ids, "Should return same IDs in same order"
