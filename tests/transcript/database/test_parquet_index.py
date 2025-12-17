"""Tests for parquet_index module."""

import time
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa
import pytest
from inspect_scout._transcript.database.parquet.encryption import (
    _check_data_encryption_status,
    _check_index_encryption_status,
)
from inspect_scout._transcript.database.parquet.index import (
    _discover_data_files,
    _discover_index_files,
    _extract_timestamp,
    _find_orphaned_data_files,
    _generate_manifest_filename,
    append_index,
    compact_index,
    create_index,
    init_index_table,
)
from inspect_scout._transcript.database.parquet.types import (
    ENCRYPTED_INDEX_EXTENSION,
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

    def test_generate_manifest_filename_encrypted(self) -> None:
        """Test generating encrypted manifest filename."""
        filename = _generate_manifest_filename(encrypted=True)
        assert filename.startswith(MANIFEST_PREFIX)
        assert filename.endswith(ENCRYPTED_INDEX_EXTENSION)

    def test_extract_timestamp_encrypted_incremental(self) -> None:
        """Test extracting timestamp from encrypted incremental filename."""
        ts = _extract_timestamp("index_20250101T120000_abc12345.enc.idx")
        assert ts == "20250101T120000"

    def test_extract_timestamp_encrypted_manifest(self) -> None:
        """Test extracting timestamp from encrypted manifest filename."""
        ts = _extract_timestamp("_manifest_20250103T100000_abc12345.enc.idx")
        assert ts == "20250103T100000"


# --- Encryption Status Tests ---


class TestEncryptionStatus:
    """Tests for encryption status detection and validation."""

    def test_check_index_encryption_status_all_encrypted(self) -> None:
        """All encrypted files returns True."""
        files = [
            "index_20250101T100000_abc.enc.idx",
            "index_20250101T110000_def.enc.idx",
        ]
        assert _check_index_encryption_status(files) is True

    def test_check_index_encryption_status_all_unencrypted(self) -> None:
        """All unencrypted files returns False."""
        files = [
            "index_20250101T100000_abc.idx",
            "index_20250101T110000_def.idx",
        ]
        assert _check_index_encryption_status(files) is False

    def test_check_index_encryption_status_empty(self) -> None:
        """Empty list returns None."""
        assert _check_index_encryption_status([]) is None

    def test_check_index_encryption_status_mixed_raises(self) -> None:
        """Mixed encrypted and unencrypted raises ValueError."""
        files = [
            "index_20250101T100000_abc.idx",
            "index_20250101T110000_def.enc.idx",
        ]
        with pytest.raises(ValueError, match="mixed encrypted"):
            _check_index_encryption_status(files)

    def test_check_data_encryption_status_all_encrypted(self) -> None:
        """All encrypted data files returns True."""
        files = [
            "data1.enc.parquet",
            "data2.enc.parquet",
        ]
        assert _check_data_encryption_status(files) is True

    def test_check_data_encryption_status_all_unencrypted(self) -> None:
        """All unencrypted data files returns False."""
        files = [
            "data1.parquet",
            "data2.parquet",
        ]
        assert _check_data_encryption_status(files) is False

    def test_check_data_encryption_status_empty(self) -> None:
        """Empty list returns None."""
        assert _check_data_encryption_status([]) is None

    def test_check_data_encryption_status_mixed_raises(self) -> None:
        """Mixed encrypted and unencrypted raises ValueError."""
        files = [
            "data1.parquet",
            "data2.enc.parquet",
        ]
        with pytest.raises(ValueError, match="mixed encrypted"):
            _check_data_encryption_status(files)

    @pytest.mark.asyncio
    async def test_create_detects_encryption_from_index_files(
        self, tmp_path: Path
    ) -> None:
        """IndexStorage.create() detects encryption from existing files."""
        # Create encrypted index files
        index_dir = tmp_path / INDEX_DIR
        index_dir.mkdir(parents=True)
        (index_dir / "index_20250101T100000_abc.enc.idx").touch()
        (index_dir / "index_20250101T110000_def.enc.idx").touch()

        # Set encryption key in environment for the test
        import os

        os.environ["SCOUT_DB_ENCRYPTION_KEY"] = "0123456789abcdef"
        try:
            # create() should detect encryption
            storage = await IndexStorage.create(location=str(tmp_path))
            assert storage.is_encrypted is True
        finally:
            del os.environ["SCOUT_DB_ENCRYPTION_KEY"]

    @pytest.mark.asyncio
    async def test_create_raises_without_encryption_key(self, tmp_path: Path) -> None:
        """IndexStorage.create() raises if encrypted files but no key."""
        # Create encrypted index files
        index_dir = tmp_path / INDEX_DIR
        index_dir.mkdir(parents=True)
        (index_dir / "index_20250101T100000_abc.enc.idx").touch()

        # Ensure no encryption key in environment
        import os

        os.environ.pop("SCOUT_DB_ENCRYPTION_KEY", None)

        with pytest.raises(ValueError, match="no encryption key"):
            await IndexStorage.create(location=str(tmp_path))

    @pytest.mark.asyncio
    async def test_discover_index_files_mixed_raises(
        self, storage: IndexStorage
    ) -> None:
        """discover_index_files raises ValueError for mixed encryption."""
        index_dir = Path(storage.location) / INDEX_DIR
        index_dir.mkdir(parents=True)

        # Create mixed index files
        (index_dir / "index_20250101T100000_abc.idx").touch()
        (index_dir / "index_20250101T110000_def.enc.idx").touch()

        with pytest.raises(ValueError, match="mixed encrypted"):
            await _discover_index_files(storage)

    @pytest.fixture
    def storage(self, tmp_path: Path) -> IndexStorage:
        """Create IndexStorage for a temporary directory."""
        return IndexStorage(location=str(tmp_path))


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
    async def test_discover_index_files_manifest_priority(
        self, storage: IndexStorage
    ) -> None:
        """Uses _manifest_*.idx over old index_*.idx files."""
        index_dir = Path(storage.location) / INDEX_DIR
        index_dir.mkdir(parents=True)

        # Create old incremental files
        (index_dir / "index_20250101T100000_abc12345.idx").touch()
        (index_dir / "index_20250101T110000_def67890.idx").touch()

        # Create newer manifest
        (index_dir / "_manifest_20250102T100000_abc12345.idx").touch()

        result = await _discover_index_files(storage)

        # Should only return the manifest (incremental files are older)
        assert len(result) == 1
        assert "_manifest_" in str(result[0])

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
    async def test_discover_index_files_includes_newer_incrementals(
        self, storage: IndexStorage
    ) -> None:
        """Includes index_*.idx files newer than manifest."""
        index_dir = Path(storage.location) / INDEX_DIR
        index_dir.mkdir(parents=True)

        # Create manifest at T=100
        (index_dir / "_manifest_20250101T100000_abc12345.idx").touch()

        # Create older incremental (should be ignored)
        (index_dir / "index_20250101T090000_old12345.idx").touch()

        # Create newer incremental (should be included)
        (index_dir / "index_20250101T110000_new12345.idx").touch()

        result = await _discover_index_files(storage)

        # Should return manifest + newer incremental
        assert len(result) == 2
        filenames = [Path(f).name for f in result]
        assert "_manifest_20250101T100000_abc12345.idx" in filenames
        assert "index_20250101T110000_new12345.idx" in filenames
        # Older incremental should NOT be included
        assert "index_20250101T090000_old12345.idx" not in filenames


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


# --- Maintenance Tests ---


class TestFindOrphanedDataFiles:
    """Tests for find_orphaned_data_files function."""

    def test_find_orphaned_data_files(self) -> None:
        """Identifies unreferenced files."""
        data_files = [
            "/path/data1.parquet",
            "/path/data2.parquet",
            "/path/data3.parquet",
        ]
        manifest = pa.table(
            {
                "transcript_id": ["t1", "t2"],
                "filename": ["/path/data1.parquet", "/path/data2.parquet"],
            }
        )

        orphaned = _find_orphaned_data_files(data_files, manifest)

        assert len(orphaned) == 1
        assert "/path/data3.parquet" in orphaned

    def test_find_orphaned_data_files_none(self) -> None:
        """Returns empty when all files are referenced."""
        data_files = ["/path/data1.parquet", "/path/data2.parquet"]
        manifest = pa.table(
            {
                "transcript_id": ["t1", "t2"],
                "filename": ["/path/data1.parquet", "/path/data2.parquet"],
            }
        )

        orphaned = _find_orphaned_data_files(data_files, manifest)

        assert len(orphaned) == 0


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

        result = await compact_index(conn, storage, delete_orphaned_data=False)

        assert isinstance(result, CompactionResult)
        assert result.index_files_merged == 2
        assert "_manifest_" in result.new_index_path

        # Verify new manifest exists and contains all data
        import pyarrow.parquet as pq

        table = pq.read_table(result.new_index_path)
        assert table.num_rows == 2

    @pytest.mark.asyncio
    async def test_compact_index_deletes_orphans(
        self, storage: IndexStorage, conn: duckdb.DuckDBPyConnection
    ) -> None:
        """Removes orphaned data files during compaction."""
        location = Path(storage.location)

        # Create data files
        create_sample_data_file(location / "data1.parquet", ["t1"])
        create_sample_data_file(location / "orphan.parquet", ["t_orphan"])

        # Create index that only references data1.parquet
        table = create_sample_index_table(["t1"], [str(location / "data1.parquet")])
        await append_index(table, storage, "index_20250101T100000_a.idx")

        result = await compact_index(conn, storage, delete_orphaned_data=True)

        assert result.orphaned_files_deleted == 1
        assert not (location / "orphan.parquet").exists()
        assert (location / "data1.parquet").exists()

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

        result = await compact_index(conn, storage, delete_orphaned_data=False)

        # Read compacted manifest
        import pyarrow.parquet as pq

        table = pq.read_table(result.new_index_path)

        # Both rows preserved
        assert table.num_rows == 2

        # Schema merged (union_by_name)
        assert "task" in table.column_names
        assert "new_field" in table.column_names

    @pytest.mark.asyncio
    async def test_compact_index_cleans_up_all_old_index_files(
        self, storage: IndexStorage, conn: duckdb.DuckDBPyConnection
    ) -> None:
        """Cleans up ALL old index files, including orphaned ones."""
        location = Path(storage.location)
        index_dir = location / INDEX_DIR
        index_dir.mkdir(parents=True)

        # Create a valid manifest (newest - will be discovered)
        table1 = create_sample_index_table(["t1"], ["data1.parquet"])
        await append_index(table1, storage, "_manifest_20250101T100000_abc12345.idx")

        # Create a valid incremental newer than manifest (will be discovered)
        table2 = create_sample_index_table(["t2"], ["data2.parquet"])
        await append_index(table2, storage, "index_20250101T110000_b.idx")

        # Create orphaned files (older than newest manifest, won't be discovered)
        # These are empty files - they would cause errors if read, proving they're skipped
        (index_dir / "_manifest_20250101T050000_def67890.idx").touch()  # Old manifest
        (index_dir / "index_20250101T060000_old.idx").touch()  # Old incremental

        # Verify we have 4 index files before
        idx_files_before = list(index_dir.glob("*.idx"))
        assert len(idx_files_before) == 4

        # Run compact_index - should succeed (only reads valid files)
        result = await compact_index(conn, storage, delete_orphaned_data=False)

        # Verify only the new manifest remains
        idx_files_after = list(index_dir.glob("*.idx"))
        assert len(idx_files_after) == 1
        assert idx_files_after[0].name.startswith("_manifest_")
        assert str(idx_files_after[0]) == result.new_index_path

        # All 4 old files should have been deleted
        assert result.index_files_deleted == 4
