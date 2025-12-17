"""Tests for index caching functionality."""

from pathlib import Path
from typing import Any
from unittest.mock import patch

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from inspect_scout._transcript.database.parquet.index import (
    init_index_table,
)
from inspect_scout._transcript.database.parquet.index_cache import (
    INDEX_CACHE_VERSION,
    _index_cache_key,
    _location_cache_dir,
    get_index_cache_path,
    load_cached_index,
    save_index_cache,
)
from inspect_scout._transcript.database.parquet.types import (
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


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    """Create a temporary cache directory."""
    cache = tmp_path / "cache"
    cache.mkdir()
    return cache


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


def create_index_file(
    storage: IndexStorage, name: str, transcript_ids: list[str]
) -> str:
    """Create an index file in the storage location."""
    index_dir = Path(storage.location) / "_index"
    index_dir.mkdir(parents=True, exist_ok=True)

    table = create_sample_index_table(
        transcript_ids=transcript_ids,
        filenames=[f"file_{i}.parquet" for i in range(len(transcript_ids))],
    )

    path = index_dir / name
    pq.write_table(table, str(path))
    return str(path)


# --- Cache Path Generation Tests ---


class TestCachePathGeneration:
    """Tests for cache path generation functions."""

    def test_location_cache_dir_creates_unique_dirs(self, tmp_path: Path) -> None:
        """Different locations get different cache directories."""
        storage1 = IndexStorage(location="s3://bucket1/path")
        storage2 = IndexStorage(location="s3://bucket2/path")

        with patch(
            "inspect_scout._transcript.database.parquet.index_cache.scout_cache_dir",
            return_value=tmp_path,
        ):
            dir1 = _location_cache_dir(storage1)
            dir2 = _location_cache_dir(storage2)

        assert dir1 != dir2
        # Both should be under tmp_path/v{VERSION}/
        version_dir = tmp_path / f"v{INDEX_CACHE_VERSION}"
        assert dir1.parent == version_dir
        assert dir2.parent == version_dir

    def test_location_cache_dir_includes_version(self, tmp_path: Path) -> None:
        """Cache path includes version directory for invalidation."""
        storage = IndexStorage(location="s3://bucket/path")

        with patch(
            "inspect_scout._transcript.database.parquet.index_cache.scout_cache_dir",
            return_value=tmp_path,
        ):
            cache_dir = _location_cache_dir(storage)

        # Path should include version: tmp_path/v1/<hash>
        assert f"v{INDEX_CACHE_VERSION}" in str(cache_dir)
        assert cache_dir.parent.name == f"v{INDEX_CACHE_VERSION}"

    def test_location_cache_dir_same_location_same_dir(self, tmp_path: Path) -> None:
        """Same location gets same cache directory."""
        storage1 = IndexStorage(location="s3://bucket/path")
        storage2 = IndexStorage(location="s3://bucket/path")

        with patch(
            "inspect_scout._transcript.database.parquet.index_cache.scout_cache_dir",
            return_value=tmp_path,
        ):
            dir1 = _location_cache_dir(storage1)
            dir2 = _location_cache_dir(storage2)

        assert dir1 == dir2

    def test_location_cache_dir_trailing_slash_normalized(self, tmp_path: Path) -> None:
        """Trailing slashes are normalized."""
        storage1 = IndexStorage(location="s3://bucket/path")
        storage2 = IndexStorage(location="s3://bucket/path/")

        with patch(
            "inspect_scout._transcript.database.parquet.index_cache.scout_cache_dir",
            return_value=tmp_path,
        ):
            dir1 = _location_cache_dir(storage1)
            dir2 = _location_cache_dir(storage2)

        assert dir1 == dir2

    def test_index_cache_key_changes_with_files(self) -> None:
        """Hash changes when file list changes."""
        files1 = ["index_20250101T100000_abc.idx"]
        files2 = ["index_20250101T100000_abc.idx", "index_20250101T110000_def.idx"]

        key1 = _index_cache_key(files1)
        key2 = _index_cache_key(files2)

        assert key1 != key2
        assert len(key1) == 16
        assert len(key2) == 16

    def test_index_cache_key_order_independent(self) -> None:
        """Hash is same regardless of file order."""
        files1 = ["a.idx", "b.idx", "c.idx"]
        files2 = ["c.idx", "a.idx", "b.idx"]

        key1 = _index_cache_key(files1)
        key2 = _index_cache_key(files2)

        assert key1 == key2

    def test_index_cache_key_uses_basename(self) -> None:
        """Hash uses only basename, not full path."""
        files1 = ["/path/to/index_abc.idx"]
        files2 = ["/other/path/index_abc.idx"]

        key1 = _index_cache_key(files1)
        key2 = _index_cache_key(files2)

        assert key1 == key2

    def test_get_index_cache_path_unencrypted(self, tmp_path: Path) -> None:
        """Unencrypted storage gets .parquet extension."""
        storage = IndexStorage(location="s3://bucket/path", is_encrypted=False)
        index_files = ["index_abc.idx"]

        with patch(
            "inspect_scout._transcript.database.parquet.index_cache.scout_cache_dir",
            return_value=tmp_path,
        ):
            path = get_index_cache_path(storage, index_files)

        assert path.suffix == ".parquet"

    def test_get_index_cache_path_encrypted(self, tmp_path: Path) -> None:
        """Encrypted storage gets .enc.parquet extension."""
        storage = IndexStorage(
            location="s3://bucket/path",
            is_encrypted=True,
            encryption_key="0" * 32,
        )
        index_files = ["index_abc.idx"]

        with patch(
            "inspect_scout._transcript.database.parquet.index_cache.scout_cache_dir",
            return_value=tmp_path,
        ):
            path = get_index_cache_path(storage, index_files)

        assert str(path).endswith(".enc.parquet")


# --- Cache Save/Load Tests ---


class TestCacheSaveLoad:
    """Tests for cache save and load operations."""

    def test_save_and_load_cached_index(
        self, conn: duckdb.DuckDBPyConnection, storage: IndexStorage, tmp_path: Path
    ) -> None:
        """Round-trip save/load works correctly."""
        # Create a table in the connection
        conn.execute("""
            CREATE TABLE test_index AS
            SELECT 'id1' AS transcript_id, 'file1.parquet' AS filename, 'task1' AS task
            UNION ALL
            SELECT 'id2', 'file2.parquet', 'task2'
        """)

        # Save to cache
        cache_path = tmp_path / "cache.parquet"
        save_index_cache(conn, cache_path, "test_index", storage)

        assert cache_path.exists()

        # Load from cache in new connection
        conn2 = duckdb.connect(":memory:")
        count = load_cached_index(conn2, cache_path, "loaded_index", storage)

        assert count == 2
        result = conn2.execute(
            "SELECT * FROM loaded_index ORDER BY transcript_id"
        ).fetchall()
        assert len(result) == 2
        assert result[0][0] == "id1"
        assert result[1][0] == "id2"

    def test_load_cached_index_returns_none_if_missing(
        self, conn: duckdb.DuckDBPyConnection, storage: IndexStorage, tmp_path: Path
    ) -> None:
        """Returns None when cache file doesn't exist."""
        cache_path = tmp_path / "nonexistent.parquet"

        result = load_cached_index(conn, cache_path, "test_index", storage)

        assert result is None

    def test_load_cached_index_deletes_corrupted_cache(
        self, conn: duckdb.DuckDBPyConnection, storage: IndexStorage, tmp_path: Path
    ) -> None:
        """Corrupted cache file is deleted and None is returned."""
        cache_path = tmp_path / "corrupted.parquet"
        cache_path.write_text("not a valid parquet file")

        result = load_cached_index(conn, cache_path, "test_index", storage)

        assert result is None
        assert not cache_path.exists()


# --- Integration Tests ---


class TestInitIndexTableCaching:
    """Tests for caching integration with init_index_table."""

    @pytest.mark.asyncio
    async def test_init_index_table_uses_cache_for_remote(self, tmp_path: Path) -> None:
        """Cache is populated on first call for remote storage."""
        # Setup storage with index file
        storage = IndexStorage(location=str(tmp_path))
        create_index_file(storage, "_manifest_20250101T100000_abc.idx", ["id1", "id2"])

        cache_base = tmp_path / "cache"
        cache_base.mkdir()

        with (
            patch.object(storage, "is_remote", return_value=True),
            patch(
                "inspect_scout._transcript.database.parquet.index_cache.scout_cache_dir",
                return_value=cache_base,
            ),
        ):
            # First call should create cache
            conn1 = duckdb.connect(":memory:")
            count1 = await init_index_table(conn1, storage)

            # Find the cache file
            cache_files = list(cache_base.rglob("*.parquet"))
            assert len(cache_files) == 1
            assert count1 == 2

    @pytest.mark.asyncio
    async def test_init_index_table_loads_from_cache(self, tmp_path: Path) -> None:
        """Second call uses cache instead of reading index files."""
        # Setup storage with index file
        storage = IndexStorage(location=str(tmp_path))
        create_index_file(storage, "_manifest_20250101T100000_abc.idx", ["id1", "id2"])

        cache_base = tmp_path / "cache"
        cache_base.mkdir()

        with (
            patch.object(storage, "is_remote", return_value=True),
            patch(
                "inspect_scout._transcript.database.parquet.index_cache.scout_cache_dir",
                return_value=cache_base,
            ),
        ):
            # First call populates cache
            conn1 = duckdb.connect(":memory:")
            await init_index_table(conn1, storage)

            # Get cache file and its modification time
            cache_files = list(cache_base.rglob("*.parquet"))
            assert len(cache_files) == 1
            cache_mtime = cache_files[0].stat().st_mtime

            # Second call should use cache (not rewrite it)
            conn2 = duckdb.connect(":memory:")
            count2 = await init_index_table(conn2, storage)

            # Cache file should not have been modified (same mtime)
            assert cache_files[0].stat().st_mtime == cache_mtime
            assert count2 == 2

    @pytest.mark.asyncio
    async def test_init_index_table_invalidates_on_file_change(
        self, tmp_path: Path
    ) -> None:
        """New index files result in new cache."""
        # Setup storage with index file
        storage = IndexStorage(location=str(tmp_path))
        create_index_file(storage, "_manifest_20250101T100000_abc.idx", ["id1", "id2"])

        cache_base = tmp_path / "cache"
        cache_base.mkdir()

        with (
            patch.object(storage, "is_remote", return_value=True),
            patch(
                "inspect_scout._transcript.database.parquet.index_cache.scout_cache_dir",
                return_value=cache_base,
            ),
        ):
            # First call creates cache
            conn1 = duckdb.connect(":memory:")
            await init_index_table(conn1, storage)

            cache_files_before = list(cache_base.rglob("*.parquet"))
            assert len(cache_files_before) == 1

            # Add a new index file (simulating new data)
            create_index_file(
                storage, "_manifest_20250102T100000_def.idx", ["id3", "id4", "id5"]
            )
            # Remove old manifest
            old_manifest = (
                Path(storage.location) / "_index" / "_manifest_20250101T100000_abc.idx"
            )
            old_manifest.unlink()

            # Second call should create new cache
            conn2 = duckdb.connect(":memory:")
            count2 = await init_index_table(conn2, storage)

            # New cache file created (different hash)
            cache_files_after = list(cache_base.rglob("*.parquet"))
            assert len(cache_files_after) == 2  # Old + new cache
            assert count2 == 3

    @pytest.mark.asyncio
    async def test_init_index_table_skips_cache_for_local(self, tmp_path: Path) -> None:
        """Local storage doesn't use caching."""
        # Setup storage with index file
        storage = IndexStorage(location=str(tmp_path))
        create_index_file(storage, "_manifest_20250101T100000_abc.idx", ["id1", "id2"])

        cache_base = tmp_path / "cache"
        cache_base.mkdir()

        with patch(
            "inspect_scout._transcript.database.parquet.index_cache.scout_cache_dir",
            return_value=cache_base,
        ):
            # Call without mocking is_remote (it returns False for local paths)
            conn = duckdb.connect(":memory:")
            count = await init_index_table(conn, storage)

            # No cache files created
            cache_files = list(cache_base.rglob("*.parquet"))
            assert len(cache_files) == 0
            assert count == 2


# --- Encryption Tests ---


class TestEncryptedCache:
    """Tests for encrypted cache functionality."""

    def test_save_encrypted_cache(
        self, conn: duckdb.DuckDBPyConnection, tmp_path: Path
    ) -> None:
        """Encrypted storage saves encrypted cache."""
        key = "0" * 32  # 32 bytes = AES-256
        storage = IndexStorage(
            location=str(tmp_path),
            is_encrypted=True,
            encryption_key=key,
        )

        # Setup encryption in connection
        conn.execute(f"PRAGMA add_parquet_key('scout_key', '{key}')")

        conn.execute("""
            CREATE TABLE test_index AS
            SELECT 'id1' AS transcript_id, 'file1.parquet' AS filename
        """)

        cache_path = tmp_path / "cache.enc.parquet"
        save_index_cache(conn, cache_path, "test_index", storage)

        assert cache_path.exists()

        # Verify file is encrypted (can't read without key)
        conn2 = duckdb.connect(":memory:")
        with pytest.raises(
            duckdb.Error
        ):  # DuckDB raises error for encrypted file without key
            conn2.execute(f"SELECT * FROM read_parquet('{cache_path}')")

    def test_load_encrypted_cache(self, tmp_path: Path) -> None:
        """Encrypted cache can be loaded with correct key."""
        key = "0" * 32
        storage = IndexStorage(
            location=str(tmp_path),
            is_encrypted=True,
            encryption_key=key,
        )

        # Save encrypted cache
        conn1 = duckdb.connect(":memory:")
        conn1.execute(f"PRAGMA add_parquet_key('scout_key', '{key}')")
        conn1.execute("""
            CREATE TABLE test_index AS
            SELECT 'id1' AS transcript_id, 'file1.parquet' AS filename
        """)

        cache_path = tmp_path / "cache.enc.parquet"
        save_index_cache(conn1, cache_path, "test_index", storage)

        # Load with key
        conn2 = duckdb.connect(":memory:")
        conn2.execute(f"PRAGMA add_parquet_key('scout_key', '{key}')")
        count = load_cached_index(conn2, cache_path, "loaded_index", storage)

        assert count == 1
        result = conn2.execute("SELECT * FROM loaded_index").fetchall()
        assert result[0][0] == "id1"
