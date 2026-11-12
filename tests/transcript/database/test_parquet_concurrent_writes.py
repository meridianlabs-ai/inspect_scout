"""Deterministic regressions for concurrent local Parquet writers."""

from pathlib import Path

import duckdb
import pyarrow as pa
import pytest
from inspect_scout import transcripts_db
from inspect_scout._transcript.database.parquet import index
from inspect_scout._transcript.database.parquet.transcripts import (
    ParquetTranscriptInfo,
    ParquetTranscriptsDB,
)
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


def _transcript(transcript_id: str) -> Transcript:
    return Transcript(
        transcript_id=transcript_id,
        source_type="test",
        source_id="test",
        source_uri="test://local",
    )


async def _delete_denied(storage: IndexStorage, path: str) -> None:
    raise PermissionError("delete denied")


@pytest.mark.asyncio
async def test_overtaken_compaction_keeps_every_transcript(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A compaction that read the index before another finished cannot hide rows."""
    location = str(tmp_path)
    append = index.append_index
    # The slow compaction's manifest gets the later name, so it sorts newest.
    names = iter(
        ["_manifest_20990101T000001_slow.idx", "_manifest_20990101T000000_fast.idx"]
    )

    async def append_after_other_writer(
        table: pa.Table, storage: IndexStorage, filename: str
    ) -> str:
        monkeypatch.setattr(index, "append_index", append)
        async with transcripts_db(location) as other:
            await other.insert([_transcript("t3")])
        return await append(table, storage, filename)

    async with transcripts_db(location) as db:
        await db.insert([_transcript("t1")])
        await db.insert([_transcript("t2")], commit=False)
        # This commit reads the index, then another writer inserts t3 and
        # compacts before this commit writes its own manifest.
        monkeypatch.setattr(index, "append_index", append_after_other_writer)
        monkeypatch.setattr(index, "_generate_manifest_filename", lambda: next(names))
        await db.commit()

    async with transcripts_db(location) as db:
        assert sorted(await db.transcript_ids()) == ["t1", "t2", "t3"]


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["read", "compact"])
@pytest.mark.parametrize(
    "stale, current",
    [
        pytest.param(
            "transcripts_s_20250101T100000_aaaaaaaa.parquet",
            "transcripts_20250101T100005_bbbbbbbb.parquet",
            id="session-file-compacted-later",
        ),
        pytest.param(
            "transcripts_s_20250101T100000_ffffffff.parquet",
            "transcripts_20250101T100000_00000000.parquet",
            id="session-file-compacted-in-the-same-second",
        ),
        pytest.param(
            "transcripts_20250101T100000_ffffffff.parquet",
            "transcripts_20250101T100005_00000000.parquet",
            id="insert-retried-later",
        ),
    ],
)
async def test_late_manifest_does_not_restore_stale_row(
    tmp_path: Path, operation: str, stale: str, current: str
) -> None:
    """A row is ranked by its data file, not by the manifest that carries it."""
    storage = IndexStorage(location=str(tmp_path))
    await index.append_index(
        pa.table({"transcript_id": ["t1"], "filename": [current]}),
        storage,
        "_manifest_20250101T100006_fast.idx",
    )
    await index.append_index(
        pa.table({"transcript_id": ["t1"], "filename": [stale]}),
        storage,
        "_manifest_20250101T100007_slow.idx",
    )
    with duckdb.connect(":memory:") as conn:
        if operation == "read":
            assert await index.init_index_table(conn, storage) == 1
            assert conn.sql("SELECT filename FROM transcript_index").fetchall() == [
                (current,)
            ]
        else:
            result = await index.compact_index(conn, storage)
            assert conn.read_parquet(result.new_index_path).fetchall() == [
                ("t1", current)
            ]


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["read", "compact"])
@pytest.mark.parametrize(
    "replacement_discovered, discoveries",
    [(True, 1), (False, 2)],
    ids=["replacement-discovered", "replacement-written-after-discovery"],
)
async def test_manifest_deleted_after_discovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    replacement_discovered: bool,
    discoveries: int,
) -> None:
    """A deleted manifest needs a rediscovery only if its replacement was not listed."""
    storage = IndexStorage(location=str(tmp_path))
    t1 = pa.table({"transcript_id": ["t1"], "filename": ["data1.parquet"]})
    deleted = await index.append_index(t1, storage, "_manifest_20250101T100000_z.idx")
    await index.append_index(
        pa.table({"transcript_id": ["t2"], "filename": ["data2.parquet"]}),
        storage,
        "index_20250101T100001_b.idx",
    )
    replacement = index._recording_replaced_files(t1, [deleted])
    if replacement_discovered:
        await index.append_index(
            replacement, storage, "_manifest_20250101T100000_a.idx"
        )
    discover = index._discover_index_files
    calls = 0

    async def discover_then_delete(storage: IndexStorage) -> list[str]:
        nonlocal calls
        calls += 1
        paths = await discover(storage)
        if calls == 1:
            if not replacement_discovered:
                await index.append_index(
                    replacement, storage, "_manifest_20250101T100002_c.idx"
                )
            Path(deleted).unlink()
        return paths

    monkeypatch.setattr(index, "_discover_index_files", discover_then_delete)
    with duckdb.connect(":memory:") as conn:
        if operation == "read":
            assert await index.init_index_table(conn, storage) == 2
        else:
            result = await index.compact_index(conn, storage)
            assert conn.read_parquet(result.new_index_path).order(
                "transcript_id"
            ).fetchall() == [("t1", "data1.parquet"), ("t2", "data2.parquet")]
    assert calls == discoveries


@pytest.mark.asyncio
async def test_undeleted_index_files_do_not_duplicate_transcripts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Merged index files that could not be deleted are not read as extra rows."""
    monkeypatch.setattr(index, "_delete_file", _delete_denied)
    for transcript_id in ["t1", "t2"]:
        async with transcripts_db(str(tmp_path)) as db:
            await db.insert([_transcript(transcript_id)])
    async with transcripts_db(str(tmp_path)) as db:
        assert await db.count() == 2
        assert sorted(await db.transcript_ids()) == ["t1", "t2"]


@pytest.mark.asyncio
async def test_replaced_index_files_are_not_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An index file a live manifest replaced is skipped, even when it is damaged."""
    monkeypatch.setattr(index, "_delete_file", _delete_denied)
    for transcript_id in ["t1", "t2"]:
        async with transcripts_db(str(tmp_path)) as db:
            await db.insert([_transcript(transcript_id)])
    # The first commit's incremental file, replaced by both later manifests.
    replaced = sorted((tmp_path / "_index").glob("index_*.idx"))[0]
    replaced.write_bytes(b"")
    async with transcripts_db(str(tmp_path)) as db:
        assert sorted(await db.transcript_ids()) == ["t1", "t2"]
        await db.insert([_transcript("t3")])
    async with transcripts_db(str(tmp_path)) as db:
        assert sorted(await db.transcript_ids()) == ["t1", "t2", "t3"]


@pytest.mark.asyncio
async def test_unreadable_index_file_names_the_rebuild_command(tmp_path: Path) -> None:
    """A damaged index file that nothing replaced fails the open with a fix."""
    async with transcripts_db(str(tmp_path)) as db:
        await db.insert([_transcript("t1")])
    (tmp_path / "_index" / "_manifest_20000101T000000_old.idx").write_bytes(b"")
    with pytest.raises(duckdb.InvalidInputException, match="Run `scout db index "):
        async with transcripts_db(str(tmp_path)) as db:
            await db.count()
    with duckdb.connect(":memory:") as conn:
        await index.create_index(conn, IndexStorage(location=str(tmp_path)))
    async with transcripts_db(str(tmp_path)) as db:
        assert sorted(await db.transcript_ids()) == ["t1"]


@pytest.mark.asyncio
async def test_rebuild_replaces_index_files_it_cannot_delete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A rebuild decides the index even when an old manifest stays on disk."""
    location = str(tmp_path)
    async with transcripts_db(location) as db:
        await db.insert([_transcript("t1")])
        await db.insert([_transcript("t2")])
        data_files = {
            info.transcript_id: info.filename
            async for info in db.select()
            if isinstance(info, ParquetTranscriptInfo)
        }
    (tmp_path / data_files["t2"]).unlink()
    old_manifests = {str(path) for path in (tmp_path / "_index").glob("*.idx")}
    delete = index._delete_file

    async def delete_except_old_manifests(storage: IndexStorage, path: str) -> None:
        if path in old_manifests:
            raise PermissionError("delete denied")
        await delete(storage, path)

    monkeypatch.setattr(index, "_delete_file", delete_except_old_manifests)
    with monkeypatch.context() as rebuild, duckdb.connect(":memory:") as conn:
        # The rebuilt manifest need not sort newest: names carry a one-second
        # timestamp and a random suffix.
        rebuild.setattr(
            index,
            "_generate_manifest_filename",
            lambda: "_manifest_20000101T000000_r.idx",
        )
        await index.create_index(conn, IndexStorage(location=location))
    assert all(Path(path).exists() for path in old_manifests)
    async with transcripts_db(location) as db:
        assert sorted(await db.transcript_ids()) == ["t1"]

    # A later commit keeps the rebuild's decision and replaces the old manifest too.
    async with transcripts_db(location) as db:
        await db.insert([_transcript("t3")])
    async with transcripts_db(location) as db:
        assert sorted(await db.transcript_ids()) == ["t1", "t3"]

    monkeypatch.setattr(index, "_delete_file", delete)
    async with transcripts_db(location) as db:
        await db.insert([_transcript("t4")])
        assert sorted(await db.transcript_ids()) == ["t1", "t3", "t4"]
    assert len(list((tmp_path / "_index").glob("*.idx"))) == 1
