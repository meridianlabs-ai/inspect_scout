# type: ignore
"""Full round-trip pipeline tests for Phoenix source.

Tests the full pipeline: fetch transcripts from Phoenix project,
insert into ParquetTranscriptsDB, and verify round-trip preserves all data.

These tests require:
- PHOENIX_RUN_TESTS=1
- PHOENIX_API_KEY set
- PHOENIX_COLLECTOR_ENDPOINT set
- Test traces created via bootstrap.py
"""

from pathlib import Path
from typing import Any

import pytest
from inspect_ai.event import ModelEvent
from inspect_scout._query import Query
from inspect_scout._transcript.database.parquet import ParquetTranscriptsDB
from inspect_scout._transcript.types import TranscriptContent

from .conftest import skip_if_no_phoenix


@skip_if_no_phoenix
@pytest.mark.asyncio
async def test_phoenix_to_db_roundtrip(phoenix_project: str, tmp_path: Path) -> None:
    """Test full pipeline: Phoenix -> Transcript -> DB."""
    from inspect_scout.sources._phoenix import phoenix

    # Fetch transcripts
    transcripts: list[Any] = []
    async for transcript in phoenix(project=phoenix_project, limit=5):
        transcripts.append(transcript)

    assert len(transcripts) > 0, (
        "No transcripts found. Run bootstrap first: "
        "python -m tests.sources.phoenix_source.bootstrap"
    )

    # Insert into DB
    db_path = tmp_path / "phoenix_roundtrip_db"
    db_path.mkdir(parents=True, exist_ok=True)

    db = ParquetTranscriptsDB(str(db_path))
    await db.connect()

    try:
        await db.insert(transcripts)

        # Verify all transcripts present
        db_results = [info async for info in db.select(Query())]
        assert len(db_results) == len(transcripts), (
            f"Expected {len(transcripts)} transcripts in DB, got {len(db_results)}"
        )

        # Verify each transcript has expected structure
        db_by_id = {r.transcript_id: r for r in db_results}
        for original in transcripts:
            assert original.transcript_id in db_by_id

            db_record = db_by_id[original.transcript_id]
            assert db_record.source_type == "phoenix"
            assert db_record.task_id == original.task_id

            if original.model:
                assert db_record.model == original.model

            assert db_record.message_count == original.message_count

        # Verify content round-trip
        for original in transcripts:
            db_record = db_by_id[original.transcript_id]
            content_spec = TranscriptContent(messages="all", events="all")
            full_record = await db.read(db_record, content_spec)

            # Message count
            assert len(full_record.messages) == len(original.messages), (
                f"Message count mismatch for {original.transcript_id}"
            )

            # Message roles
            original_roles = [m.role for m in original.messages]
            db_roles = [m.role for m in full_record.messages]
            assert original_roles == db_roles, (
                f"Message roles mismatch for {original.transcript_id}"
            )

            # Event count
            assert len(full_record.events) == len(original.events), (
                f"Event count mismatch for {original.transcript_id}"
            )

            # Event types
            original_event_types = [type(e).__name__ for e in original.events]
            db_event_types = [type(e).__name__ for e in full_record.events]
            assert original_event_types == db_event_types, (
                f"Event types mismatch for {original.transcript_id}"
            )

    finally:
        await db.disconnect()


@skip_if_no_phoenix
@pytest.mark.asyncio
async def test_phoenix_transcript_fields_in_db(
    phoenix_project: str, tmp_path: Path
) -> None:
    """Test that transcript fields survive DB round-trip."""
    from inspect_scout.sources._phoenix import phoenix

    # Fetch one transcript
    transcript = None
    async for t in phoenix(project=phoenix_project, limit=1):
        transcript = t
        break

    if transcript is None:
        pytest.skip("No transcripts found - run bootstrap first")

    # Insert into DB
    db_path = tmp_path / "phoenix_fields_db"
    db_path.mkdir(parents=True, exist_ok=True)

    db = ParquetTranscriptsDB(str(db_path))
    await db.connect()

    try:
        await db.insert([transcript])

        db_results = [info async for info in db.select(Query())]
        assert len(db_results) == 1

        db_record = db_results[0]

        # Verify key fields
        assert db_record.source_type == "phoenix"
        assert db_record.source_id == transcript.source_id
        assert db_record.model is not None

        # Verify events include ModelEvent
        content_spec = TranscriptContent(messages=None, events="all")
        full_record = await db.read(db_record, content_spec)
        model_events = [e for e in full_record.events if isinstance(e, ModelEvent)]
        assert len(model_events) >= 1, "Expected at least one ModelEvent"

    finally:
        await db.disconnect()
