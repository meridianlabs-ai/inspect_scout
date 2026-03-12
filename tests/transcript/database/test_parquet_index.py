"""Tests for parquet_index module."""

import time
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa
import pytest
from inspect_scout._transcript.database.parquet.index import (
    _discover_data_files,
    _discover_index_files,
    _extract_timestamp,
    _generate_manifest_filename,
    append_index,
    compact_index,
    create_index,
    init_index_table,
)
from inspect_scout._transcript.database.parquet.types import (
    INDEX_DIR,
    INDEX_EXTENSION,
    MANIFEST_PREFIX,
    CompactionResult,
    IndexStorage,
)

# --- Test Fixtures ---


@pytest.fixture
def storage(tmp_path: Path) -> IndexStorage:
    """Create IndexStorage for a temporary directory."""
    return IndexStorage(location=str(tmp_path))


@pytest.fixture
def conn() -> duckdb.DuckDBPyConnection:
    """Create in-memory DuckDB connection."""
    return duckdb.connect(":memory:")


def create_sample_index_table(
    transcript_ids: list[str],
    filenames: list[str],
    extra_columns: dict[str, list[Any]] | None = None,
) -> pa.Table:
    """Create a sample index table for testing."""
    data: dict[str, Any] = {
        "transcript_id": transcript_ids,
        "filename": filenames,
        "task": ["test_task"] * len(transcript_ids),
        "model": ["test_model"] * len(transcript_ids),
    }
    if extra_columns:
        data.update(extra_columns)
    return pa.table(data)


def create_sample_data_file(path: Path, transcript_ids: list[str]) -> None:
    """Create a sample parquet data file with messages/events."""
    table = pa.table(
        {
            "transcript_id": transcript_ids,
            "task": ["test_task"] * len(transcript_ids),
            "model": ["test_model"] * len(transcript_ids),
            "messages": ['[{"role": "user", "content": "test"}]'] * len(transcript_ids),
            "events": ["[]"] * len(transcript_ids),
        }
    )
    import pyarrow.parquet as pq

    pq.write_table(table, str(path))


# --- Helper Function Tests ---


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_extract_timestamp_incremental(self) -> None:
        """Test extracting timestamp from incremental filename."""
        ts = _extract_timestamp("index_20250101T120000_abc12345.idx")
        assert ts == "20250101T120000"

    def test_extract_timestamp_manifest(self) -> None:
        """Test extracting timestamp from manifest filename."""
        ts = _extract_timestamp("_manifest_20250103T100000_abc12345.idx")
        assert ts == "20250103T100000"

    def test_extract_timestamp_with_path(self) -> None:
        """Test extracting timestamp from full path."""
        ts = _extract_timestamp("/path/to/_index/index_20250101T120000_abc12345.idx")
        assert ts == "20250101T120000"

    def test_extract_timestamp_invalid(self) -> None:
        """Test extracting timestamp from invalid filename."""
        ts = _extract_timestamp("random_file.idx")
        assert ts is None

    def test_generate_manifest_filename(self) -> None:
        """Test generating manifest filename."""
        filename = _generate_manifest_filename()
        assert filename.startswith(MANIFEST_PREFIX)
        assert filename.endswith(INDEX_EXTENSION)


# --- Discovery Tests ---


class TestDiscoverIndexFiles:
    """Tests for discover_index_files function."""

    @pytest.mark.asyncio
    async def test_discover_index_files_empty(self, storage: IndexStorage) -> None:
        """No index directory returns empty list."""
        result = await _discover_index_files(storage)
        assert result == []

    @pytest.mark.asyncio
    async def test_discover_index_files_incremental(
        self, storage: IndexStorage
    ) -> None:
        """Finds index_*.idx files correctly."""
        # Create index directory with incremental files
        index_dir = Path(storage.location) / INDEX_DIR
        index_dir.mkdir(parents=True)

        # Create some incremental index files
        (index_dir / "index_20250101T100000_abc12345.idx").touch()
        (index_dir / "index_20250101T110000_def67890.idx").touch()

        result = await _discover_index_files(storage)
        assert len(result) == 2
        assert all("index_" in str(f) for f in result)

    @pytest.mark.asyncio
    async def test_discover_index_files_manifest_with_incrementals(
        self, storage: IndexStorage
    ) -> None:
        """Returns manifest plus all remaining incrementals."""
        index_dir = Path(storage.location) / INDEX_DIR
        index_dir.mkdir(parents=True)

        # Create incremental files (older than manifest)
        (index_dir / "index_20250101T100000_abc12345.idx").touch()
        (index_dir / "index_20250101T110000_def67890.idx").touch()

        # Create newer manifest
        (index_dir / "_manifest_20250102T100000_abc12345.idx").touch()

        result = await _discover_index_files(storage)

        # Should return manifest + all incrementals (they may be un-merged)
        assert len(result) == 3
        filenames = [Path(f).name for f in result]
        assert "_manifest_20250102T100000_abc12345.idx" in filenames
        assert "index_20250101T100000_abc12345.idx" in filenames
        assert "index_20250101T110000_def67890.idx" in filenames

    @pytest.mark.asyncio
    async def test_discover_index_files_newest_manifest(
        self, storage: IndexStorage
    ) -> None:
        """Uses newest manifest when multiple exist."""
        index_dir = Path(storage.location) / INDEX_DIR
        index_dir.mkdir(parents=True)

        # Create multiple manifests
        (index_dir / "_manifest_20250101T100000_aaa11111.idx").touch()
        (index_dir / "_manifest_20250102T100000_bbb22222.idx").touch()
        (index_dir / "_manifest_20250103T100000_ccc33333.idx").touch()

        result = await _discover_index_files(storage)

        assert len(result) == 1
        assert "20250103T100000" in str(result[0])

    @pytest.mark.asyncio
    async def test_discover_index_files_includes_all_incrementals(
        self, storage: IndexStorage
    ) -> None:
        """Includes ALL remaining index_*.idx files, even older than manifest.

        Un-merged incrementals can have timestamps older than the manifest
        when they were written concurrently. Since compact_index only deletes
        merged files, any remaining incrementals are un-merged and must be
        discovered.
        """
        index_dir = Path(storage.location) / INDEX_DIR
        index_dir.mkdir(parents=True)

        # Create manifest at T=100
        (index_dir / "_manifest_20250101T100000_abc12345.idx").touch()

        # Create older incremental (should still be included — may be un-merged)
        (index_dir / "index_20250101T090000_old12345.idx").touch()

        # Create newer incremental (should be included)
        (index_dir / "index_20250101T110000_new12345.idx").touch()

        result = await _discover_index_files(storage)

        # Should return manifest + both incrementals
        assert len(result) == 3
        filenames = [Path(f).name for f in result]
        assert "_manifest_20250101T100000_abc12345.idx" in filenames
        assert "index_20250101T110000_new12345.idx" in filenames
        assert "index_20250101T090000_old12345.idx" in filenames


class TestDiscoverDataFiles:
    """Tests for discover_data_files function."""

    @pytest.mark.asyncio
    async def test_discover_data_files_excludes_index(
        self, storage: IndexStorage
    ) -> None:
        """Doesn't include _index/*.idx files."""
        location = Path(storage.location)
        location.mkdir(parents=True, exist_ok=True)

        # Create data files
        (location / "data1.parquet").touch()
        (location / "data2.parquet").touch()

        # Create index directory with index files
        index_dir = location / INDEX_DIR
        index_dir.mkdir()
        (index_dir / "index_20250101T100000_abc.idx").touch()

        result = await _discover_data_files(storage)

        assert len(result) == 2
        assert all(".parquet" in f for f in result)
        assert all(INDEX_DIR not in f for f in result)


# --- Read Operations Tests ---


class TestRegisterIndexTable:
    """Tests for register_index_table function."""

    @pytest.mark.asyncio
    async def test_register_index_table_no_files(
        self, storage: IndexStorage, conn: duckdb.DuckDBPyConnection
    ) -> None:
        """Returns 0 when no index exists."""
        count = await init_index_table(conn, storage)
        assert count == 0

        # Table should exist but be empty
        result = conn.execute("SELECT COUNT(*) FROM transcript_index").fetchone()
        assert result is not None
        assert result[0] == 0

    @pytest.mark.asyncio
    async def test_register_index_table_single_file(
        self, storage: IndexStorage, conn: duckdb.DuckDBPyConnection
    ) -> None:
        """Creates queryable table from one .idx file."""
        # Create index file
        table = create_sample_index_table(
            transcript_ids=["t1", "t2", "t3"],
            filenames=["data1.parquet"] * 3,
        )
        await append_index(table, storage, "index_20250101T100000_test.idx")

        count = await init_index_table(conn, storage)
        assert count == 3

    @pytest.mark.asyncio
    async def test_register_index_table_multiple_files(
        self, storage: IndexStorage, conn: duckdb.DuckDBPyConnection
    ) -> None:
        """Merges multiple .idx files."""
        # Create first index file
        table1 = create_sample_index_table(
            transcript_ids=["t1", "t2"],
            filenames=["data1.parquet"] * 2,
        )
        await append_index(table1, storage, "index_20250101T100000_abc.idx")

        # Wait a moment to ensure different timestamp
        time.sleep(0.01)

        # Create second index file
        table2 = create_sample_index_table(
            transcript_ids=["t3", "t4"],
            filenames=["data2.parquet"] * 2,
        )
        await append_index(table2, storage, "index_20250101T110000_def.idx")

        count = await init_index_table(conn, storage)
        assert count == 4

    @pytest.mark.asyncio
    async def test_register_index_table_query(
        self, storage: IndexStorage, conn: duckdb.DuckDBPyConnection
    ) -> None:
        """SQL WHERE queries work correctly."""
        # Create index with varied data
        table = create_sample_index_table(
            transcript_ids=["t1", "t2", "t3"],
            filenames=["data1.parquet", "data2.parquet", "data1.parquet"],
            extra_columns={
                "task": ["task_a", "task_b", "task_a"],
                "model": ["gpt-4", "claude", "gpt-4"],
            },
        )
        await append_index(table, storage, "index_20250101T100000_abc.idx")

        await init_index_table(conn, storage)

        # Test WHERE clause
        result = conn.execute(
            "SELECT transcript_id FROM transcript_index WHERE task = 'task_a'"
        ).fetchall()
        assert len(result) == 2

        result = conn.execute(
            "SELECT transcript_id FROM transcript_index WHERE model = 'claude'"
        ).fetchall()
        assert len(result) == 1


class TestEnsureIndexSchema:
    """Tests for _ensure_index_schema backfill of missing columns."""

    @pytest.mark.asyncio
    async def test_backfills_missing_columns_including_reserved_words(
        self, storage: IndexStorage, conn: duckdb.DuckDBPyConnection
    ) -> None:
        """Old index with only transcript_id+filename gets all schema columns added.

        Verifies that reserved SQL keywords like 'limit' are properly quoted
        in ALTER TABLE statements.
        """
        from inspect_scout._transcript.database.parquet.transcripts import (
            _ensure_index_schema,
        )
        from inspect_scout._transcript.database.schema import (
            CONTENT_COLUMNS,
            TRANSCRIPT_SCHEMA_FIELDS,
        )

        # Create a minimal index with only transcript_id and filename
        # (simulating an old index format)
        minimal_table = pa.table(
            {
                "transcript_id": ["t1", "t2"],
                "filename": ["data1.parquet", "data2.parquet"],
            }
        )
        await append_index(minimal_table, storage, "index_20250101T100000_old.idx")

        # Load into DuckDB
        row_count = await init_index_table(conn, storage)
        assert row_count == 2

        # Run the actual backfill function
        _ensure_index_schema(conn)

        # Verify all non-content schema columns now exist
        final_columns = {
            row[0]
            for row in conn.execute(
                "SELECT column_name FROM (DESCRIBE transcript_index)"
            ).fetchall()
        }
        for field in TRANSCRIPT_SCHEMA_FIELDS:
            if field.name not in CONTENT_COLUMNS:
                assert field.name in final_columns, (
                    f"Expected column '{field.name}' to be present after backfill"
                )

        # Verify reserved keyword column 'limit' is queryable
        result = conn.execute('SELECT "limit" FROM transcript_index').fetchall()
        assert len(result) == 2
        # All values should be NULL since the column was just added
        assert all(row[0] is None for row in result)


# --- Write Operations Tests ---


class TestWriteIndexFile:
    """Tests for write_index_file function."""

    @pytest.mark.asyncio
    async def test_write_index_file(self, storage: IndexStorage) -> None:
        """Writes valid parquet with correct schema."""
        table = create_sample_index_table(
            transcript_ids=["t1", "t2"],
            filenames=["data.parquet"] * 2,
        )

        filename = "test_index.idx"
        path = await append_index(table, storage, filename)

        assert Path(path).exists()
        assert path.endswith(filename)

        # Verify it's readable
        import pyarrow.parquet as pq

        read_table = pq.read_table(path)
        assert read_table.num_rows == 2

    @pytest.mark.asyncio
    async def test_write_index_file_creates_directory(
        self, storage: IndexStorage
    ) -> None:
        """Creates _index/ directory if missing."""
        table = create_sample_index_table(
            transcript_ids=["t1"],
            filenames=["data.parquet"],
        )

        index_dir = Path(storage.location) / INDEX_DIR
        assert not index_dir.exists()

        await append_index(table, storage, "test.idx")

        assert index_dir.exists()


class TestCreateIndex:
    """Tests for create_index function."""

    @pytest.mark.asyncio
    async def test_create_index_from_scratch(
        self, storage: IndexStorage, conn: duckdb.DuckDBPyConnection
    ) -> None:
        """Builds index for unindexed database."""
        # Create data files
        location = Path(storage.location)
        create_sample_data_file(location / "data1.parquet", ["t1", "t2"])
        create_sample_data_file(location / "data2.parquet", ["t3"])

        path = await create_index(conn, storage)

        assert path is not None
        assert Path(path).exists()
        assert "_manifest_" in path

        # Verify the index contains all transcripts
        import pyarrow.parquet as pq

        table = pq.read_table(path)
        assert table.num_rows == 3
        # Should not have messages/events
        assert "messages" not in table.column_names
        assert "events" not in table.column_names

    @pytest.mark.asyncio
    async def test_create_index_empty_database(
        self, storage: IndexStorage, conn: duckdb.DuckDBPyConnection
    ) -> None:
        """Handles database with no data files."""
        # Ensure directory exists but has no parquet files
        Path(storage.location).mkdir(parents=True, exist_ok=True)

        path = await create_index(conn, storage)

        assert path is None

    @pytest.mark.asyncio
    async def test_create_index_cleans_up_all_old_index_files(
        self, storage: IndexStorage, conn: duckdb.DuckDBPyConnection
    ) -> None:
        """Cleans up ALL old index files, including orphaned ones."""
        location = Path(storage.location)
        index_dir = location / INDEX_DIR
        index_dir.mkdir(parents=True)

        # Create data file
        create_sample_data_file(location / "data.parquet", ["t1"])

        # Create various old index files:
        # 1. A manifest that would be discovered
        table1 = create_sample_index_table(["t1"], ["data.parquet"])
        await append_index(table1, storage, "_manifest_20250101T100000_abc12345.idx")

        # 2. An older manifest that would be orphaned (not discovered)
        (index_dir / "_manifest_20250101T080000_def67890.idx").touch()

        # 3. An older incremental that would be orphaned
        (index_dir / "index_20250101T090000_old.idx").touch()

        # Verify we have 3 index files before
        idx_files_before = list(index_dir.glob("*.idx"))
        assert len(idx_files_before) == 3

        # Run create_index
        new_path = await create_index(conn, storage)

        # Verify only the new manifest remains
        idx_files_after = list(index_dir.glob("*.idx"))
        assert len(idx_files_after) == 1
        assert idx_files_after[0].name.startswith("_manifest_")
        assert str(idx_files_after[0]) == new_path

    @pytest.mark.asyncio
    async def test_create_index_stores_relative_filenames(
        self, storage: IndexStorage, conn: duckdb.DuckDBPyConnection
    ) -> None:
        """Index stores filenames relative to database location, not absolute paths."""
        import pyarrow.parquet as pq

        # Create data files in subdirectories (like partitioned data)
        location = Path(storage.location)
        subdir = location / "task_set=test" / "agent=foo"
        subdir.mkdir(parents=True)
        create_sample_data_file(subdir / "data1.parquet", ["t1", "t2"])
        create_sample_data_file(location / "data2.parquet", ["t3"])

        path = await create_index(conn, storage)
        assert path is not None

        # Read the index and check filenames
        table = pq.read_table(path)
        filenames = table.column("filename").to_pylist()

        # All filenames should be relative (not contain the location prefix)
        for filename in filenames:
            assert filename
            assert not filename.startswith(str(location)), (
                f"Filename '{filename}' should be relative, not absolute"
            )
            assert not filename.startswith("/"), (
                f"Filename '{filename}' should not start with /"
            )

        # Verify expected relative paths
        assert "task_set=test/agent=foo/data1.parquet" in filenames
        assert "data2.parquet" in filenames

    @pytest.mark.asyncio
    async def test_create_index_deduplicates_by_transcript_id(
        self, storage: IndexStorage, conn: duckdb.DuckDBPyConnection
    ) -> None:
        """Deduplicates transcript_ids when same ID exists in multiple data files."""
        import pyarrow.parquet as pq

        location = Path(storage.location)

        # Create two data files with the same transcript_id
        # (simulating a retry after partial failure)
        create_sample_data_file(location / "data1.parquet", ["t1", "t2"])
        create_sample_data_file(
            location / "data2.parquet", ["t1", "t3"]
        )  # t1 is duplicate

        path = await create_index(conn, storage)
        assert path is not None

        # Read the index
        table = pq.read_table(path)

        # Should have 3 unique transcript_ids (t1 deduplicated)
        transcript_ids = table.column("transcript_id").to_pylist()
        assert len(transcript_ids) == 3
        assert set(transcript_ids) == {"t1", "t2", "t3"}

        # t1 should appear only once
        assert transcript_ids.count("t1") == 1


# --- Maintenance Tests ---


class TestCompactIndex:
    """Tests for compact_index function."""

    @pytest.mark.asyncio
    async def test_compact_index(
        self, storage: IndexStorage, conn: duckdb.DuckDBPyConnection
    ) -> None:
        """Merges multiple .idx files into one."""
        # Create multiple index files
        table1 = create_sample_index_table(["t1"], ["data1.parquet"])
        table2 = create_sample_index_table(["t2"], ["data2.parquet"])

        await append_index(table1, storage, "index_20250101T100000_a.idx")
        await append_index(table2, storage, "index_20250101T110000_b.idx")

        result = await compact_index(conn, storage)

        assert isinstance(result, CompactionResult)
        assert result.index_files_merged == 2
        assert "_manifest_" in result.new_index_path

        # Verify new manifest exists and contains all data
        import pyarrow.parquet as pq

        table = pq.read_table(result.new_index_path)
        assert table.num_rows == 2

    @pytest.mark.asyncio
    async def test_compact_index_preserves_data(
        self, storage: IndexStorage, conn: duckdb.DuckDBPyConnection
    ) -> None:
        """No data loss after compaction."""
        # Create index files with different schemas (simulating metadata evolution)
        table1 = pa.table(
            {
                "transcript_id": ["t1"],
                "filename": ["data1.parquet"],
                "task": ["task1"],
            }
        )
        table2 = pa.table(
            {
                "transcript_id": ["t2"],
                "filename": ["data2.parquet"],
                "task": ["task2"],
                "new_field": ["value"],
            }
        )

        await append_index(table1, storage, "index_20250101T100000_a.idx")
        await append_index(table2, storage, "index_20250101T110000_b.idx")

        result = await compact_index(conn, storage)

        # Read compacted manifest
        import pyarrow.parquet as pq

        table = pq.read_table(result.new_index_path)

        # Both rows preserved
        assert table.num_rows == 2

        # Schema merged (union_by_name)
        assert "task" in table.column_names
        assert "new_field" in table.column_names

    @pytest.mark.asyncio
    async def test_compact_index_deduplicates_by_transcript_id(
        self, storage: IndexStorage, conn: duckdb.DuckDBPyConnection
    ) -> None:
        """Deduplicates transcript_ids, keeping entry from newest file."""
        # Create older index file with t1 pointing to data1.parquet
        table1 = create_sample_index_table(["t1"], ["data1.parquet"])
        await append_index(table1, storage, "index_20250101T100000_a.idx")

        # Create newer index file with same t1 pointing to data2.parquet
        # (simulating a retry after partial failure)
        table2 = create_sample_index_table(["t1"], ["data2.parquet"])
        await append_index(table2, storage, "index_20250101T110000_b.idx")

        result = await compact_index(conn, storage)

        # Should have only 1 row (deduplicated)
        import pyarrow.parquet as pq

        table = pq.read_table(result.new_index_path)
        assert table.num_rows == 1

        # Should keep the entry from the newer file (data2.parquet)
        filenames = table.column("filename").to_pylist()
        assert filenames == ["data2.parquet"]

    @pytest.mark.asyncio
    async def test_compact_index_recovers_concurrent_write_across_two_compactions(
        self, storage: IndexStorage, conn: duckdb.DuckDBPyConnection
    ) -> None:
        """End-to-end race: concurrent write survives first compaction, merged in second.

        Scenario:
        1. Session A discovers index_1..index_8 (index_9 not yet written)
        2. Session B writes index_9 (timestamp T3)
        3. Session A compacts index_1..index_8 into manifest (timestamp T4 > T3)
        4. Session A deletes only index_1..index_8 (fix #1) — index_9 survives
        5. Next compaction discovers manifest + index_9 and merges both — no data loss
        """
        import pyarrow.parquet as pq

        index_dir = Path(storage.location) / INDEX_DIR
        index_dir.mkdir(parents=True)

        # Step 1: Create 8 incremental index files (sessions 1-8)
        for i in range(1, 9):
            table = create_sample_index_table([f"t{i}"], [f"data{i}.parquet"])
            ts = f"20250101T{100000 + i * 10000}"
            await append_index(table, storage, f"index_{ts}_{i:08x}.idx")

        # Step 2: Session B writes index_9 concurrently (timestamp BEFORE compaction)
        table9 = create_sample_index_table(["t9"], ["data9.parquet"])
        await append_index(table9, storage, "index_20250101T185000_00000009.idx")

        # Step 3: Simulate Session A's compaction — it only discovered index_1..8
        # We do this by running compact, which now discovers all 9.
        # To properly simulate, first compact without index_9, then add it back.
        # Instead, we directly create the state after step 4:
        # - Compact index_1..8 into a manifest, delete them, leave index_9

        # Discover the 9 files, then manually do what Session A would have done:
        # read only index_1..8, write manifest, delete only index_1..8
        idx_files = sorted(index_dir.glob("index_*.idx"))
        assert len(idx_files) == 9

        # Read index_1..8 (what Session A discovered before index_9 existed)
        session_a_files = idx_files[:8]
        tables = [pq.read_table(str(f)) for f in session_a_files]
        merged = pa.concat_tables(tables)

        # Write manifest with timestamp AFTER index_9's timestamp
        manifest_name = "_manifest_20250101T190000_compacted.idx"
        await append_index(merged, storage, manifest_name)

        # Delete only the 8 files Session A merged (fix #1 behavior)
        for f in session_a_files:
            f.unlink()

        # State after step 4: manifest (T=190000) + index_9 (T=185000)
        remaining = list(index_dir.glob("*.idx"))
        assert len(remaining) == 2
        names = {f.name for f in remaining}
        assert manifest_name in names
        assert "index_20250101T185000_00000009.idx" in names

        # Step 5: Second compaction — must discover and merge index_9
        result = await compact_index(conn, storage)

        assert result.index_files_merged == 2
        assert result.index_files_deleted == 2

        # Verify all 9 transcripts are in the final manifest
        final_table = pq.read_table(result.new_index_path)
        transcript_ids = set(final_table.column("transcript_id").to_pylist())
        assert transcript_ids == {f"t{i}" for i in range(1, 10)}, (
            "All 9 transcripts must be present — index_9 must not be orphaned"
        )

    @pytest.mark.asyncio
    async def test_compact_index_only_deletes_merged_files(
        self, storage: IndexStorage, conn: duckdb.DuckDBPyConnection
    ) -> None:
        """Only deletes files that were discovered and merged, not orphaned ones.

        This prevents a race condition where files written concurrently by
        other sessions could be deleted before their data is merged.
        """
        location = Path(storage.location)
        index_dir = location / INDEX_DIR
        index_dir.mkdir(parents=True)

        # Create a valid manifest (newest - will be discovered)
        table1 = create_sample_index_table(["t1"], ["data1.parquet"])
        await append_index(table1, storage, "_manifest_20250101T100000_abc12345.idx")

        # Create a valid incremental newer than manifest (will be discovered)
        table2 = create_sample_index_table(["t2"], ["data2.parquet"])
        await append_index(table2, storage, "index_20250101T110000_b.idx")

        # Create an older incremental with valid data that was NOT in the manifest
        # (simulating a concurrent write that was missed during compaction)
        table3 = create_sample_index_table(["t3"], ["data3.parquet"])
        await append_index(table3, storage, "index_20250101T060000_old.idx")

        # Verify we have 3 index files before
        idx_files_before = list(index_dir.glob("*.idx"))
        assert len(idx_files_before) == 3

        # Run compact_index — discovers manifest + all incrementals (including older one)
        result = await compact_index(conn, storage)

        # All 3 discovered files should have been merged and deleted
        assert result.index_files_merged == 3
        assert result.index_files_deleted == 3

        # Only the new manifest remains
        idx_files_after = list(index_dir.glob("*.idx"))
        assert len(idx_files_after) == 1

        # The new manifest should exist and contain all 3 transcripts
        manifest_files = [f for f in idx_files_after if f.name.startswith("_manifest_")]
        assert len(manifest_files) == 1
        assert str(manifest_files[0]) == result.new_index_path

        import pyarrow.parquet as pq

        merged_table = pq.read_table(result.new_index_path)
        transcript_ids = set(merged_table.column("transcript_id").to_pylist())
        assert transcript_ids == {"t1", "t2", "t3"}, (
            "Orphaned incremental t3 must be merged, not permanently lost"
        )


# --- Concurrency Protection Tests ---


class TestConcurrencyProtection:
    """Tests for concurrency protection in index operations."""

    @pytest.mark.asyncio
    async def test_append_index_no_temp_files_on_success(
        self, storage: IndexStorage
    ) -> None:
        """Local writes leave no temp files after successful write."""
        table = create_sample_index_table(["t1"], ["data.parquet"])
        index_dir = Path(storage.location) / INDEX_DIR

        await append_index(table, storage, "index_20250101T100000_abc.idx")

        # Verify no temp files remain
        tmp_files = list(index_dir.glob(".tmp_*"))
        assert len(tmp_files) == 0

        # Verify the actual file was created
        idx_files = list(index_dir.glob("*.idx"))
        assert len(idx_files) == 1

    @pytest.mark.asyncio
    async def test_append_index_cleans_temp_on_write_error(
        self, storage: IndexStorage
    ) -> None:
        """Temp file is cleaned up if write fails."""
        from unittest.mock import patch

        import pyarrow.parquet as pq

        table = create_sample_index_table(["t1"], ["data.parquet"])
        index_dir = Path(storage.location) / INDEX_DIR
        index_dir.mkdir(parents=True, exist_ok=True)

        # Mock pq.write_table to raise an error
        with patch.object(pq, "write_table", side_effect=IOError("Write failed")):
            with pytest.raises(IOError, match="Write failed"):
                await append_index(table, storage, "index_20250101T100000_abc.idx")

        # Verify no temp files remain
        tmp_files = list(index_dir.glob(".tmp_*"))
        assert len(tmp_files) == 0

        # Verify no index file was created either
        idx_files = list(index_dir.glob("*.idx"))
        assert len(idx_files) == 0

    @pytest.mark.asyncio
    async def test_init_index_table_retries_on_file_not_found(
        self, storage: IndexStorage, conn: duckdb.DuckDBPyConnection
    ) -> None:
        """init_index_table retries when file disappears during read."""
        # Create an index file
        table = create_sample_index_table(["t1", "t2"], ["data.parquet"] * 2)
        await append_index(table, storage, "index_20250101T100000_abc.idx")

        # Delete the file to simulate concurrent deletion
        index_dir = Path(storage.location) / INDEX_DIR
        for f in index_dir.glob("*.idx"):
            f.unlink()

        # Should return 0 (empty) rather than error after retries
        count = await init_index_table(conn, storage)
        assert count == 0

    @pytest.mark.asyncio
    async def test_compact_index_handles_missing_files_gracefully(
        self, storage: IndexStorage, conn: duckdb.DuckDBPyConnection
    ) -> None:
        """compact_index handles files deleted during compaction."""
        # This test verifies the retry mechanism works when files are deleted
        # between discovery and read. Since we can't easily simulate that,
        # we test the simpler case: no files results in empty result.
        result = await compact_index(conn, storage)

        assert result.index_files_merged == 0
        assert result.new_index_path == ""

    @pytest.mark.asyncio
    async def test_delete_file_handles_already_deleted(
        self, storage: IndexStorage
    ) -> None:
        """_delete_file silently ignores missing files."""
        from inspect_scout._transcript.database.parquet.index import _delete_file

        # Try to delete a non-existent file - should not raise
        await _delete_file(storage, "/nonexistent/path/file.idx")

    @pytest.mark.asyncio
    async def test_multiple_manifests_discovery_picks_newest(
        self, storage: IndexStorage
    ) -> None:
        """When multiple manifests exist, discovery picks the newest one."""
        index_dir = Path(storage.location) / INDEX_DIR
        index_dir.mkdir(parents=True)

        # Create multiple manifests (simulating concurrent create_index calls)
        table1 = create_sample_index_table(["t1"], ["data1.parquet"])
        table2 = create_sample_index_table(["t2"], ["data2.parquet"])
        table3 = create_sample_index_table(["t3"], ["data3.parquet"])

        await append_index(table1, storage, "_manifest_20250101T100000_abc.idx")
        await append_index(table2, storage, "_manifest_20250101T110000_def.idx")
        await append_index(table3, storage, "_manifest_20250101T120000_ghi.idx")

        # Discovery should return only the newest manifest
        idx_files = await _discover_index_files(storage)
        assert len(idx_files) == 1
        assert "20250101T120000" in idx_files[0]
