"""Byte-equivalence of the page-reader and DuckDB paths through Scout's API."""

import contextlib
import json
from pathlib import Path
from typing import Any, AsyncIterator, Iterator

import duckdb
import inspect_scout._transcript.database.parquet.transcripts as transcripts_module
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import pytest_asyncio
from inspect_ai.event import Timeline, TimelineSpan
from inspect_ai.model._chat_message import ChatMessageUser
from inspect_scout._transcript.database.parquet import ParquetTranscriptsDB
from inspect_scout._transcript.database.parquet.page_reader import (
    ParquetContentReader,
)
from inspect_scout._transcript.types import (
    Transcript,
    TranscriptContent,
    TranscriptInfo,
    TranscriptTooLargeError,
)


def make_transcript(
    id: str, content_size: int, *, timelines: list[Timeline] | None = None
) -> Transcript:
    return Transcript(
        transcript_id=id,
        source_type="test",
        source_id="src-1",
        source_uri=f"test://{id}",
        metadata={},
        messages=[ChatMessageUser(content=f"héllo→世界😀 {id} " + "x" * content_size)],
        events=[],
        timelines=timelines or [],
    )


def make_timeline(id: str) -> Timeline:
    return Timeline(
        name=f"tl-{id}",
        description="héllo→世界😀",
        root=TimelineSpan(
            id=f"root-{id}",
            name="root",
            branches=[TimelineSpan(id=f"child-{id}", name="child")],
        ),
    )


@contextlib.contextmanager
def assert_no_fallback(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Fail if anything falls back to DuckDB inside the block.

    Without this the equivalence tests would still pass if the reader
    regressed to always falling back: they would compare DuckDB with itself.
    """
    fallbacks: list[str] = []
    original = transcripts_module._log_page_reader_fallback

    def record(path: str, ex: Exception) -> None:
        fallbacks.append(f"{path}: {ex}")
        original(path, ex)

    monkeypatch.setattr(transcripts_module, "_log_page_reader_fallback", record)
    yield
    assert not fallbacks, f"unexpected DuckDB fallback(s): {fallbacks}"


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
                [
                    '[{"event":"x","data":"héllo→世界😀 ' + "y" * 2_000_000 + '"}]',
                    None,
                    "[]",
                ],
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
        [
            make_transcript(
                f"t-{i:03d}",
                2_000_000 if i == 1 else 200,
                # one row carries a stored timeline, the rest have none
                timelines=[make_timeline(f"t-{i:03d}")] if i == 2 else None,
            )
            for i in range(4)
        ]
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
    with assert_no_fallback(monkeypatch):
        via_reader = {
            info.transcript_id: await collect_messages_events(db, info)
            for info in infos
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

    The reader raises PageReaderUnsupportedError internally — proven at unit
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


@pytest.mark.asyncio
async def test_stream_abandonment_closes_reader(
    db: ParquetTranscriptsDB, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Abandoning the stream mid-way must close the page reader promptly.

    The reader is closed via aclose/__aexit__, not left to GC finalization.
    """
    closed: list[bool] = []
    original_close = ParquetContentReader.close

    def tracking_close(self: ParquetContentReader) -> None:
        closed.append(True)
        original_close(self)

    monkeypatch.setattr(ParquetContentReader, "close", tracking_close)
    infos = [info async for info in db.select()]
    result = await db.read_messages_events(infos[0])
    async with result.data as data:
        async for _chunk in data:
            break  # abandon mid-stream with bytes already emitted
    assert closed, "ParquetContentReader.close never ran on abandonment"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content",
    [
        TranscriptContent(messages="all", events="all"),
        TranscriptContent(messages=["user"], events=None),
        TranscriptContent(messages=None, events="all"),
        TranscriptContent(messages=None, events=None),
        TranscriptContent(messages="all", events="all", timeline="all"),
        TranscriptContent(messages=None, events=None, timeline="all"),
    ],
    ids=[
        "all-all",
        "user-none",
        "none-events",
        "none-none",
        "all-all-timeline",
        "timeline-only",
    ],
)
async def test_read_matches_duckdb(
    db: ParquetTranscriptsDB,
    monkeypatch: pytest.MonkeyPatch,
    content: TranscriptContent,
) -> None:
    infos = [info async for info in db.select()]
    real = [
        info for info in infos if info.transcript_id.startswith("t-")
    ]  # Transcript-inserted rows parse as full transcripts
    with assert_no_fallback(monkeypatch):
        via_reader = {
            info.transcript_id: (await db.read(info, content)).model_dump()
            for info in real
        }
    if content.timeline is not None:
        # t-002 stores a timeline: keeps the timeline cases from going vacuous
        assert any(dump["timelines"] for dump in via_reader.values())
    break_page_reader(monkeypatch)
    for info in real:
        assert (await db.read(info, content)).model_dump() == via_reader[
            info.transcript_id
        ], info.transcript_id


@pytest.mark.asyncio
async def test_read_uses_page_reader(
    db: ParquetTranscriptsDB, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    original = transcripts_module.ParquetContentReader  # type: ignore[attr-defined]

    def counting(path: str, **kwargs: Any) -> ParquetContentReader:
        calls.append(path)
        return original(path, **kwargs)

    monkeypatch.setattr(transcripts_module, "ParquetContentReader", counting)
    infos = [info async for info in db.select()]
    await db.read(infos[0], TranscriptContent(messages="all", events="all"))
    assert calls, "read() did not construct a ParquetContentReader"


@pytest.mark.asyncio
async def test_multi_row_group_store_matches_duckdb(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rows spread over many row groups read identically on both paths.

    row_group_size=3 over 10 mixed-size rows puts every row at a different
    offset within its group, which is where a cross-row-group off-by-one in
    the locate/page-walk arithmetic would show up.
    """
    location = tmp_path / "store"
    location.mkdir()
    database = ParquetTranscriptsDB(str(location), row_group_size=3)
    await database.connect()
    await database.insert(
        [
            make_transcript(
                f"g-{i:03d}",
                2_000_000 if i == 5 else 100 * i,
                timelines=[make_timeline(f"g-{i:03d}")] if i % 4 == 0 else None,
            )
            for i in range(10)
        ]
    )
    await database.commit()
    try:
        store_file = next(location.glob("transcripts_*.parquet"))
        assert pq.ParquetFile(str(store_file)).metadata.num_row_groups >= 4

        infos = [info async for info in database.select()]
        assert len(infos) == 10
        content = TranscriptContent(messages="all", events="all", timeline="all")
        with assert_no_fallback(monkeypatch):
            via_reader = {
                info.transcript_id: (
                    await collect_messages_events(database, info),
                    (await database.read(info, content)).model_dump(),
                )
                for info in infos
            }
        assert any(dump["timelines"] for _, dump in via_reader.values())
        break_page_reader(monkeypatch)
        for info in infos:
            duckdb_bytes = await collect_messages_events(database, info)
            duckdb_read = (await database.read(info, content)).model_dump()
            assert (duckdb_bytes, duckdb_read) == via_reader[info.transcript_id], (
                info.transcript_id
            )
    finally:
        await database.disconnect()


def stored_content_sizes(store: Path, transcript_id: str) -> tuple[int, int]:
    """(byte, character) size of messages+events+events_data as stored on disk."""
    store_files = [str(f) for f in sorted(store.glob("transcripts_*.parquet"))]
    conn = duckdb.connect()
    row = conn.execute(
        """
        SELECT COALESCE(strlen(messages), 0) + COALESCE(strlen(events), 0)
                 + COALESCE(strlen(events_data), 0),
               COALESCE(LENGTH(messages), 0) + COALESCE(LENGTH(events), 0)
                 + COALESCE(LENGTH(events_data), 0)
        FROM read_parquet(?) WHERE transcript_id = ?
        """,
        [store_files, transcript_id],
    ).fetchone()
    conn.close()
    assert row is not None
    return row[0], row[1]


@pytest.mark.asyncio
@pytest.mark.parametrize("use_fallback", [False, True], ids=["reader", "duckdb"])
async def test_max_bytes_gate_is_byte_accurate(
    db: ParquetTranscriptsDB,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    use_fallback: bool,
) -> None:
    """Pins the max_bytes gate's boundary semantics on both paths.

    t-000's stored messages are ASCII-escaped by json.dumps
    (_transcript_to_row), so byte and character counts coincide here; the
    bytes-vs-characters distinction itself is proven by
    test_content_size_counts_bytes_not_characters.
    """
    if use_fallback:
        break_page_reader(monkeypatch)
    infos = [info async for info in db.select()]
    info = next(i for i in infos if i.transcript_id == "t-000")
    content = TranscriptContent(messages="all", events="all")

    byte_size, _ = stored_content_sizes(tmp_path / "store", "t-000")
    assert byte_size > 0

    # one byte below the true size must raise; at the true size must succeed
    with contextlib.nullcontext() if use_fallback else assert_no_fallback(monkeypatch):
        with pytest.raises(TranscriptTooLargeError):
            await db.read(info, content, max_bytes=byte_size - 1)
        transcript = await db.read(info, content, max_bytes=byte_size)
        assert transcript.messages


@pytest.mark.asyncio
@pytest.mark.parametrize("use_fallback", [False, True], ids=["reader", "duckdb"])
async def test_content_size_counts_bytes_not_characters(
    db: ParquetTranscriptsDB,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    use_fallback: bool,
) -> None:
    """uncompressed_size must be UTF-8 bytes, not characters.

    Proven on a cell whose stored bytes contain unescaped non-ASCII
    (RecordBatch rows bypass json.dumps' ASCII escaping).
    """
    if use_fallback:
        break_page_reader(monkeypatch)
    infos = [info async for info in db.select()]
    info = next(i for i in infos if i.transcript_id == "rb-000")

    byte_size, char_size = stored_content_sizes(tmp_path / "store", "rb-000")
    assert byte_size > char_size, "fixture no longer distinguishes bytes from chars"
    with contextlib.nullcontext() if use_fallback else assert_no_fallback(monkeypatch):
        result = await db.read_messages_events(info)
        assert result.uncompressed_size == byte_size
