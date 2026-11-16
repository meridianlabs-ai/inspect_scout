"""Deterministic regressions for concurrent local Parquet writers."""

from pathlib import Path

import duckdb
import pyarrow as pa
import pytest
from inspect_scout import transcripts_db
from inspect_scout._transcript.database.parquet import index
from inspect_scout._transcript.database.parquet.transcripts import ParquetTranscriptsDB
from inspect_scout._transcript.database.parquet.types import IndexStorage
from inspect_scout._transcript.types import Transcript
from inspect_scout._util.duckdb import parquet_view


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["read", "compact"])
async def test_index_disappears_after_discovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    """Rediscovery recovers data when another compactor replaces a listed file."""
    storage = IndexStorage(location=str(tmp_path))
    table = pa.table({"transcript_id": ["t1"], "filename": ["data.parquet"]})
    old_path = await index.append_index(table, storage, "index_20250101T100000_aaa.idx")
    discover = index._discover_index_files
    replaced = False

    async def discover_and_replace(storage: IndexStorage) -> list[str]:
        nonlocal replaced
        paths = await discover(storage)
        if not replaced:
            replaced = True
            await index.append_index(
                table, storage, "_manifest_20250101T100001_bbb.idx"
            )
            Path(old_path).unlink()
        return paths

    monkeypatch.setattr(index, "_discover_index_files", discover_and_replace)
    with duckdb.connect(":memory:") as conn:
        if operation == "read":
            assert await index.init_index_table(conn, storage) == 1
            assert conn.sql(
                "SELECT transcript_id FROM transcript_index"
            ).fetchall() == [("t1",)]
        else:
            result = await index.compact_index(conn, storage)
            assert conn.read_parquet(result.new_index_path).fetchall() == [
                ("t1", "data.parquet")
            ]


@pytest.mark.asyncio
@pytest.mark.parametrize("fail", [False, True])
async def test_local_fragment_only_visible_after_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fail: bool
) -> None:
    """Readers cannot discover incomplete fragments, including failed writes."""
    write = ParquetTranscriptsDB._write_parquet_file
    visible_during_write: list[Path] = []

    def interrupted_write(
        self: ParquetTranscriptsDB, table: pa.Table, path: str
    ) -> None:
        Path(path).write_bytes(b"PAR1")
        visible_during_write.extend(tmp_path.rglob("*.parquet"))
        if fail:
            raise OSError("interrupted fragment write")
        write(self, table, path)

    monkeypatch.setattr(ParquetTranscriptsDB, "_write_parquet_file", interrupted_write)
    transcript = Transcript(
        transcript_id="t1",
        source_type="test",
        source_id="test",
        source_uri="test://local",
    )
    async with transcripts_db(str(tmp_path)) as db:
        if fail:
            with pytest.raises(OSError, match="interrupted fragment write"):
                await db.insert([transcript])
        else:
            await db.insert([transcript])
            assert await db.count() == 1
    assert visible_during_write == []
    assert len(list(tmp_path.rglob("*.parquet"))) == (0 if fail else 1)
    assert list(tmp_path.rglob(".tmp_*")) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["read", "compact"])
@pytest.mark.parametrize(
    "error, retry",
    [
        (
            duckdb.HTTPException(
                'HTTP Error: Unable to connect to URL "https://example.test/index.idx": 404 (Not Found)'
            ),
            True,
        ),
        (
            duckdb.HTTPException(
                'HTTP Error: Unable to connect to URL "https://example.test/index.idx": 404 (File not found)'
            ),
            True,
        ),
        (
            duckdb.HTTPException(
                'HTTP Error: Unable to connect to URL "https://example.test/404.idx": 403 (Forbidden)'
            ),
            False,
        ),
        (
            duckdb.HTTPException(
                'HTTP Error: Unable to connect to URL "https://example.test:404/index.idx": 403 (Forbidden)'
            ),
            False,
        ),
        (duckdb.IOException("IO Error: 404 unrelated failure"), False),
    ],
)
async def test_index_read_io_classification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    error: duckdb.IOException,
    retry: bool,
) -> None:
    """Retry missing HTTP objects while propagating unrelated I/O failures."""
    from contextlib import contextmanager
    from typing import Iterator

    storage = IndexStorage(location=str(tmp_path))
    await index.append_index(
        pa.table({"transcript_id": ["t1"], "filename": ["data.parquet"]}),
        storage,
        "index_20250101T100000_aaa.idx",
    )
    attempts = 0

    @contextmanager
    def disappearing_view(
        conn: duckdb.DuckDBPyConnection, paths: str | list[str], **kwargs: bool
    ) -> Iterator[str]:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise error
        with parquet_view(conn, paths, **kwargs) as view:
            yield view

    monkeypatch.setattr(index, "parquet_view", disappearing_view)
    with duckdb.connect(":memory:") as conn:
        if not retry:
            with pytest.raises(type(error)) as raised:
                if operation == "read":
                    await index.init_index_table(conn, storage)
                else:
                    await index.compact_index(conn, storage)
            assert raised.value is error
        elif operation == "read":
            assert await index.init_index_table(conn, storage) == 1
        else:
            result = await index.compact_index(conn, storage)
            assert conn.read_parquet(result.new_index_path).fetchall() == [
                ("t1", "data.parquet")
            ]
    assert attempts == (2 if retry else 1)


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["read", "compact"])
async def test_missing_index_retry_is_bounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    """Repeated missing-file failures stop after the existing three retries."""
    storage = IndexStorage(location=str(tmp_path))
    discoveries = 0

    async def discover_missing(storage: IndexStorage) -> list[str]:
        nonlocal discoveries
        discoveries += 1
        return [str(tmp_path / "missing.idx")]

    monkeypatch.setattr(index, "_discover_index_files", discover_missing)
    with duckdb.connect(":memory:") as conn:
        with pytest.raises(
            duckdb.IOException, match="No files found that match the pattern"
        ):
            if operation == "read":
                await index.init_index_table(conn, storage)
            else:
                await index.compact_index(conn, storage)
    assert discoveries == 4
