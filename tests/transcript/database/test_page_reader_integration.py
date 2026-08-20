"""Byte-equivalence of the page-reader and DuckDB paths through Scout's API."""

import json
from pathlib import Path
from typing import Any, AsyncIterator

import inspect_scout._transcript.database.parquet.transcripts as transcripts_module
import pyarrow as pa
import pytest
import pytest_asyncio
from inspect_ai.model._chat_message import ChatMessageUser
from inspect_scout._transcript.database.parquet import ParquetTranscriptsDB
from inspect_scout._transcript.types import Transcript, TranscriptInfo


def make_transcript(id: str, content_size: int) -> Transcript:
    return Transcript(
        transcript_id=id,
        source_type="test",
        source_id="src-1",
        source_uri=f"test://{id}",
        metadata={},
        messages=[ChatMessageUser(content=f"héllo→世界😀 {id} " + "x" * content_size)],
        events=[],
    )


def adversarial_batch() -> pa.RecordBatchReader:
    """Rows with hand-authored content cells: NULLs, empties, all columns."""
    batch = pa.RecordBatch.from_pydict(
        {
            "transcript_id": pa.array(
                ["rb-000", "rb-001", "rb-002"], pa.large_string()
            ),
            "source_type": pa.array(["test"] * 3, pa.large_string()),
            "messages": pa.array(
                ['[{"role":"user","content":"hi"}]', None, ""],
                pa.large_string(),
            ),
            "events": pa.array(
                ['[{"event":"x","data":"' + "y" * 2_000_000 + '"}]', None, "[]"],
                pa.large_string(),
            ),
            "events_data": pa.array(
                ['{"messages":[],"calls":[]}', None, None], pa.large_string()
            ),
            "timelines": pa.array(['[{"id":"tl-1"}]', None, ""], pa.large_string()),
        }
    )
    return pa.RecordBatchReader.from_batches(batch.schema, [batch])


@pytest_asyncio.fixture
async def db(tmp_path: Path) -> AsyncIterator[ParquetTranscriptsDB]:
    location = tmp_path / "store"
    location.mkdir()
    database = ParquetTranscriptsDB(str(location))
    await database.connect()
    await database.insert(
        [make_transcript(f"t-{i:03d}", 2_000_000 if i == 1 else 200) for i in range(4)]
    )
    await database.insert(adversarial_batch())
    await database.commit()
    yield database
    await database.disconnect()


def break_page_reader(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force every integration site onto the DuckDB fallback."""

    def boom(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("page reader disabled for test")

    monkeypatch.setattr(transcripts_module, "ParquetContentReader", boom)


async def collect_messages_events(
    db: ParquetTranscriptsDB, info: TranscriptInfo
) -> bytes:
    result = await db.read_messages_events(info)
    chunks: list[bytes] = []
    async with result.data as data:
        async for chunk in data:
            chunks.append(chunk)
    return b"".join(chunks)


@pytest.mark.asyncio
async def test_stream_chunks_byte_identical_to_duckdb(
    db: ParquetTranscriptsDB, monkeypatch: pytest.MonkeyPatch
) -> None:
    infos = [info async for info in db.select()]
    assert len(infos) == 7
    via_reader = {
        info.transcript_id: await collect_messages_events(db, info) for info in infos
    }
    # every envelope must be well-formed JSON with the standard keys
    for payload in via_reader.values():
        parsed = json.loads(payload)
        assert set(parsed) == {"messages", "events", "events_data", "timelines"}
    break_page_reader(monkeypatch)
    for info in infos:
        assert (
            await collect_messages_events(db, info) == via_reader[info.transcript_id]
        ), info.transcript_id


def rewrite_store_file(store: Path, **write_kwargs: Any) -> None:
    """Rewrite every store parquet file in place with different flags.

    Simulates files from older writers (the index keeps working because
    filenames and transcript ids are unchanged). The store is multi-file
    (one file per insert batch), so all files are rewritten.
    """
    import pyarrow.parquet as pq

    files = sorted(store.glob("transcripts_*.parquet"))
    assert files, "no store parquet files found"
    drop = write_kwargs.pop("drop_columns", None)
    for path in files:
        table = pq.read_table(str(path))
        if drop is not None:
            table = table.drop_columns(
                [column for column in drop if column in table.column_names]
            )
        pq.write_table(table, str(path), **write_kwargs)


@pytest.mark.asyncio
async def test_unsupported_file_falls_back_byte_identically(
    db: ParquetTranscriptsDB, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A SNAPPY store triggers organic fallback and matches DuckDB byte-for-byte.

    The reader raises PageReaderUnsupported internally — proven at unit
    level in test_page_reader.py — and the output is byte-identical to a
    forced DuckDB-only run.
    """
    rewrite_store_file(tmp_path / "store", compression="snappy", row_group_size=25)
    infos = [info async for info in db.select()]
    organic = {
        info.transcript_id: await collect_messages_events(db, info) for info in infos
    }
    break_page_reader(monkeypatch)
    for info in infos:
        assert await collect_messages_events(db, info) == organic[info.transcript_id], (
            info.transcript_id
        )


@pytest.mark.asyncio
async def test_file_missing_columns_reads_with_defaults(
    db: ParquetTranscriptsDB, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Schema evolution: a file missing columns reads with default values.

    A file without events_data/timelines produces the default envelope
    values, identically on both paths (reader via column_names(), DuckDB
    via its BinderException retry).
    """
    rewrite_store_file(
        tmp_path / "store",
        drop_columns=["events_data", "timelines"],
        compression="zstd",
        use_dictionary=True,
        row_group_size=25,
        write_statistics=True,
    )
    infos = [info async for info in db.select()]
    via_reader = {
        info.transcript_id: await collect_messages_events(db, info) for info in infos
    }
    for payload in via_reader.values():
        parsed = json.loads(payload)
        assert parsed["events_data"] is None
        assert parsed["timelines"] == []
    break_page_reader(monkeypatch)
    for info in infos:
        assert (
            await collect_messages_events(db, info) == via_reader[info.transcript_id]
        ), info.transcript_id
