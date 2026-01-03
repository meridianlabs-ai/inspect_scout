"""Parquet index management for efficient transcript queries.

This module provides standalone functions for managing index files that
enable fast metadata queries without scanning all data files. Index files
are stored in an `_index/` directory with two types:

- Incremental index files: `index_<timestamp>_<uuid>.idx` (or `.enc.idx` if encrypted)
  Written during insert operations, one per batch.

- Compacted manifests: `_manifest_<timestamp>_<uuid>.idx` (or `.enc.idx` if encrypted)
  Written during compaction, consolidates multiple index files.

The discovery priority ensures concurrent operations work correctly:
1. If any `_manifest_*.idx` exists, use the newest one
2. Also include any `index_*.idx` files newer than that manifest
3. If no manifest exists, use all `index_*.idx` files

Encryption status is determined by file extensions (`.enc.idx` vs `.idx`),
mirroring the `.enc.parquet` vs `.parquet` pattern for data files.
"""

import glob
import os
import re
import tempfile
from datetime import datetime, timezone
from logging import getLogger
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from inspect_ai._util.file import filesystem
from inspect_ai.util import trace_message
from shortuuid import uuid

from .encryption import (
    ENCRYPTION_KEY_NAME,
    _check_data_encryption_status,
    _check_index_encryption_status,
    setup_encryption,
)
from .index_cache import get_index_cache_path, load_cached_index, save_index_cache
from .migration import migrate_table
from .types import (
    ENCRYPTED_INDEX_EXTENSION,
    INCREMENTAL_PREFIX,
    INDEX_DIR,
    INDEX_EXTENSION,
    MANIFEST_PREFIX,
    TIMESTAMP_FORMAT,
    CompactionResult,
    IndexStorage,
)

logger = getLogger(__name__)

# Regex patterns for extracting timestamps from filenames
# UUID part allows any alphanumeric (actual UUIDs are hex, but be permissive for testing)
# These patterns match both encrypted (.enc.idx) and unencrypted (.idx) files
INCREMENTAL_PATTERN = re.compile(r"index_(\d{8}T\d{6})_[a-zA-Z0-9]+(?:\.enc)?\.idx$")
MANIFEST_PATTERN = re.compile(r"_manifest_(\d{8}T\d{6})_[a-zA-Z0-9]+(?:\.enc)?\.idx$")


async def append_index(
    table: pa.Table,
    storage: IndexStorage,
    filename: str,
) -> str:
    """Write index file to _index/ directory.

    Args:
        table: PyArrow table containing index data.
        storage: Storage configuration.
        filename: Name for the index file (without directory prefix).

    Returns:
        Full path to the written file.
    """
    index_dir = storage.index_dir_path()
    full_path = f"{index_dir}/{filename}"

    if storage.is_remote():
        # Remote storage: write to temp file then upload
        with tempfile.NamedTemporaryFile(
            suffix=storage.index_extension(), delete=False
        ) as tmp_file:
            tmp_path = tmp_file.name

        try:
            _write_parquet_table(table, tmp_path, storage)

            # Upload to remote
            assert storage.fs is not None, "AsyncFilesystem required for remote storage"
            await storage.fs.write_file(full_path, Path(tmp_path).read_bytes())
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    else:
        # Local storage: use atomic write pattern to prevent partial files
        output_path = Path(full_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to temp file in same directory (ensures same filesystem for rename)
        tmp_filename = f".tmp_{uuid()[:8]}{storage.index_extension()}"
        local_tmp_path = output_path.parent / tmp_filename

        try:
            _write_parquet_table(table, str(local_tmp_path), storage)
            # Atomic rename on POSIX - prevents partial files from being visible
            os.rename(local_tmp_path, output_path)
        except Exception:
            # Clean up temp file on any error
            local_tmp_path.unlink(missing_ok=True)
            raise

    return full_path


async def compact_index(
    conn: duckdb.DuckDBPyConnection,
    storage: IndexStorage,
    _retry_count: int = 0,
) -> CompactionResult:
    """Compact multiple index files into one.

    Steps:
    1. Read all index files into merged manifest
    2. Write single compacted manifest file
    3. (Only after success) Delete ALL old index files

    Args:
        conn: DuckDB connection.
        storage: Storage configuration.
        _retry_count: Internal retry counter (do not set manually).

    Returns:
        CompactionResult with stats about files merged/deleted.
    """
    MAX_RETRIES = 3
    # Use discovery for reading (gets the right files to merge)
    idx_files = await _discover_index_files(storage)
    # List ALL files for cleanup (includes orphaned older files)
    all_idx_files = await _list_all_index_files(storage)

    if not idx_files:
        # No index files at all
        return CompactionResult(
            index_files_merged=0,
            index_files_deleted=0,
            new_index_path="",
        )
    # Setup encryption if needed (discover_index_files sets storage.is_encrypted)
    enc_config = setup_encryption(conn, storage)

    # Load all index files into a single table with deduplication.
    # If the same transcript_id appears in multiple index files (from retried
    # inserts after partial failures), keep the entry from the newest file.
    # Index files have timestamps in their names, so newer files sort later.
    # We tag each file with its position in the sorted list (_file_order).
    try:
        merged_table = _read_and_deduplicate_index_files(conn, idx_files, enc_config)
    except duckdb.IOException as e:
        error_msg = str(e).lower()
        if (
            "could not open file" in error_msg or "no such file" in error_msg
        ) and _retry_count < MAX_RETRIES:
            # Files changed during operation - retry with fresh discovery
            logger.warning(
                f"Index file access failed during compaction (attempt {_retry_count + 1}), retrying"
            )
            return await compact_index(conn, storage, _retry_count + 1)
        raise

    # Write compacted manifest (even if only 1 file - converts incremental to manifest)
    new_filename = _generate_manifest_filename(encrypted=storage.is_encrypted)
    new_path = await append_index(merged_table, storage, new_filename)

    # Delete ALL old index files (only after successful write)
    deleted_idx_count = 0
    for old_file in all_idx_files:
        try:
            await _delete_file(storage, old_file)
            deleted_idx_count += 1
        except Exception as e:
            logger.warning(f"Failed to delete old index file {old_file}: {e}")

    return CompactionResult(
        index_files_merged=len(idx_files),
        index_files_deleted=deleted_idx_count,
        new_index_path=new_path,
    )


async def create_index(
    conn: duckdb.DuckDBPyConnection,
    storage: IndexStorage,
) -> str | None:
    """Create or rebuild index from existing parquet files.

    Scans all .parquet data files, extracts metadata (excluding
    messages/events), and writes a complete manifest file. Handles both:
    - Databases with no index (full build)
    - Databases with partial index (rebuild)

    After successfully writing the new index, any existing index files
    are deleted. This ensures corrupted or partial indexes are cleaned up.

    The index will be encrypted if the data files are encrypted.

    Args:
        conn: DuckDB connection.
        storage: Storage configuration.

    Returns:
        Path to created index file, or None if no data files exist.
    """
    # List ALL existing index files before creating new one (for cleanup)
    existing_idx_files = await _list_all_index_files(storage)

    data_files = await _discover_data_files(storage)

    if not data_files:
        # Empty database - nothing to index
        return None

    # Build file list for read_parquet
    if len(data_files) == 1:
        file_pattern = f"'{data_files[0]}'"
    else:
        file_pattern = "[" + ", ".join(f"'{p}'" for p in data_files) + "]"

    # Setup encryption if needed (discover_data_files sets storage.is_encrypted)
    enc_config = setup_encryption(conn, storage)

    # Read all metadata from data files, excluding messages/events
    # First, get the schema to know which columns exist
    schema_result = conn.execute(
        f"SELECT column_name FROM (DESCRIBE SELECT * FROM read_parquet({file_pattern}, union_by_name=true{enc_config}))"
    ).fetchall()
    all_columns = {row[0] for row in schema_result}

    # Build exclude clause for messages/events if they exist
    exclude_columns = [c for c in ["messages", "events"] if c in all_columns]
    exclude_clause = (
        f" EXCLUDE ({', '.join(exclude_columns)})" if exclude_columns else ""
    )

    # Read metadata into Arrow table with deduplication.
    # If the same transcript_id exists in multiple data files (e.g., from
    # retried inserts after partial failures), keep only one entry.
    # We use ROW_NUMBER() to pick one arbitrarily per transcript_id.
    result = conn.execute(f"""
        SELECT * EXCLUDE (_rn) FROM (
            SELECT *{exclude_clause},
                   ROW_NUMBER() OVER (PARTITION BY transcript_id) as _rn
            FROM read_parquet({file_pattern}, union_by_name=true, filename=true{enc_config})
        )
        WHERE _rn = 1
    """).fetch_arrow_table()

    # Convert absolute filenames to relative paths (relative to database location)
    result = _make_filenames_relative(result, storage.location)

    # Write as manifest file (this is a full rebuild, so use manifest naming)
    filename = _generate_manifest_filename(encrypted=storage.is_encrypted)
    new_path = await append_index(result, storage, filename)

    # Delete old index files (only after successful write)
    for old_file in existing_idx_files:
        try:
            await _delete_file(storage, old_file)
        except Exception as e:
            logger.warning(f"Failed to delete old index file {old_file}: {e}")

    return new_path


async def init_index_table(
    conn: duckdb.DuckDBPyConnection,
    storage: IndexStorage,
    table_name: str = "transcript_index",
    _retry_count: int = 0,
) -> int:
    """Register index files as a DuckDB table for querying.

    Creates a TABLE from index files using union_by_name.
    This is the primary entry point for read operations.

    For remote storage, uses local caching to avoid repeated downloads.
    The cache is invalidated when index files change (based on filename hash).

    After calling, SQL queries work directly:
        SELECT * FROM transcript_index WHERE task = 'gaia'
        SELECT COUNT(*) FROM transcript_index WHERE model LIKE '%claude%'

    Args:
        conn: DuckDB connection.
        storage: Storage configuration.
        table_name: Name for the created table.
        _retry_count: Internal retry counter (do not set manually).

    Returns:
        Row count (0 if no index files found).

    Raises:
        duckdb.Error: If index files are corrupted or unreadable.
        ValueError: If encrypted but no encryption key available.
    """
    MAX_RETRIES = 3
    idx_files = await _discover_index_files(storage)

    if not idx_files:
        # No index files - create empty table
        conn.execute(f"""
            CREATE TABLE {table_name} AS
            SELECT ''::VARCHAR AS transcript_id, ''::VARCHAR AS filename
            WHERE FALSE
        """)
        return 0

    # For remote storage, try to use local cache
    cache_path: Path | None = None
    if storage.is_remote():
        cache_path = get_index_cache_path(storage, idx_files)

        # Try loading from cache
        cached_count = load_cached_index(conn, cache_path, table_name, storage)
        if cached_count is not None:
            trace_message(
                logger, "Scout Index Cache", f"Loaded from cache: {cache_path}"
            )
            # migrate fields for backwards compatiblity with databases created from eval_log
            migrate_table(conn, table_name)
            return cached_count

    # Build file list for read_parquet
    if len(idx_files) == 1:
        file_pattern = f"'{idx_files[0]}'"
    else:
        file_pattern = "[" + ", ".join(f"'{p}'" for p in idx_files) + "]"

    # Setup encryption if needed (discover_index_files sets storage.is_encrypted)
    enc_config = setup_encryption(conn, storage)

    # Create table from index files
    # Handle file-not-found errors from concurrent operations with retry
    try:
        conn.execute(f"""
            CREATE TABLE {table_name} AS
            SELECT * FROM read_parquet({file_pattern}, union_by_name=true{enc_config})
        """)
    except duckdb.IOException as e:
        error_msg = str(e).lower()
        if (
            "could not open file" in error_msg or "no such file" in error_msg
        ) and _retry_count < MAX_RETRIES:
            # File was deleted by concurrent operation - rediscover and retry
            logger.warning(
                f"Index file access failed (attempt {_retry_count + 1}), retrying"
            )
            return await init_index_table(conn, storage, table_name, _retry_count + 1)
        raise

    # Return row count
    result = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
    row_count = result[0] if result else 0

    # For remote storage, save to cache
    if storage.is_remote() and cache_path is not None:
        try:
            save_index_cache(conn, cache_path, table_name, storage)
            trace_message(logger, "Scout Index Cache", f"Saved to cache: {cache_path}")
        except Exception as e:
            logger.warning(f"Failed to save index cache: {e}")

    # migrate fields for backwards compatiblity with databases created from eval_log
    migrate_table(conn, table_name)

    return row_count


async def _discover_index_files(storage: IndexStorage) -> list[str]:
    """Find index files in _index/ directory.

    Implements discovery priority for handling concurrent operations:
    1. If any _manifest_*.idx exists, use the newest one
    2. Also include any index_*.idx files NEWER than that manifest
    3. If no manifest exists, use all index_*.idx files

    Args:
        storage: Storage configuration.

    Returns:
        List of index file paths to use.

    Raises:
        ValueError: If index contains mixed encrypted and unencrypted files.
    """
    index_dir = storage.index_dir_path()

    if storage.is_remote():
        # Remote storage: use filesystem listing
        fs = filesystem(storage.location)
        try:
            all_files = fs.ls(index_dir, recursive=False)
        except FileNotFoundError:
            # Index directory doesn't exist yet
            return []
        all_idx_files = [f.name for f in all_files if _is_index_file(f.name)]
    else:
        # Local storage: use glob for both extensions
        index_path = Path(index_dir)
        if not index_path.exists():
            return []
        all_idx_files = [str(p) for p in index_path.glob("*" + INDEX_EXTENSION)]

    if not all_idx_files:
        return []

    # Validate encryption status consistency (raises if mixed)
    _check_index_encryption_status(all_idx_files)

    # Separate manifests from incremental files
    manifest_files = [
        f for f in all_idx_files if Path(f).name.startswith(MANIFEST_PREFIX)
    ]
    incremental_files = [
        f for f in all_idx_files if Path(f).name.startswith(INCREMENTAL_PREFIX)
    ]

    if not manifest_files:
        # No manifest - use all incremental files
        return sorted(incremental_files)

    # Use newest manifest (sorted by filename = sorted by timestamp)
    newest_manifest = sorted(manifest_files)[-1]
    manifest_ts = _extract_timestamp(newest_manifest)

    if manifest_ts is None:
        # Shouldn't happen, but fall back to just using manifest
        return [newest_manifest]

    # Include incremental files at or after the manifest timestamp
    # Using >= handles the case where insert happens in the same second as compaction
    newer_incrementals = []
    for f in incremental_files:
        inc_ts = _extract_timestamp(f)
        if inc_ts and inc_ts >= manifest_ts:
            newer_incrementals.append(f)

    return [newest_manifest] + sorted(newer_incrementals)


async def _list_all_index_files(storage: IndexStorage) -> list[str]:
    """List ALL index files in _index/ directory (no priority filtering).

    Unlike _discover_index_files(), this returns every .idx file,
    used for cleanup operations like create_index().

    Args:
        storage: Storage configuration.

    Returns:
        List of all index file paths.
    """
    index_dir = storage.index_dir_path()

    if storage.is_remote():
        fs = filesystem(storage.location)
        try:
            all_files = fs.ls(index_dir, recursive=False)
        except FileNotFoundError:
            return []
        return [f.name for f in all_files if _is_index_file(f.name)]
    else:
        index_path = Path(index_dir)
        if not index_path.exists():
            return []
        return [str(p) for p in index_path.glob("*" + INDEX_EXTENSION)]


async def _discover_data_files(storage: IndexStorage) -> list[str]:
    """Find all .parquet data files (excluding _index/).

    Args:
        storage: Storage configuration.

    Returns:
        List of data file paths.

    Raises:
        ValueError: If database contains mixed encrypted and unencrypted files.
    """
    data_files = await _discover_data_files_internal(storage)

    # Validate encryption status consistency (raises if mixed)
    if data_files:
        _check_data_encryption_status(data_files)

    return data_files


async def _discover_data_files_internal(storage: IndexStorage) -> list[str]:
    """Internal helper to discover data files without encryption detection."""
    if storage.is_remote():
        fs = filesystem(storage.location)
        all_files = fs.ls(storage.location, recursive=True)
        return [
            f.name
            for f in all_files
            if f.name.endswith(".parquet") and f"/{INDEX_DIR}/" not in f.name
        ]
    else:
        location_path = Path(storage.location)
        if not location_path.exists():
            return []

        all_parquet = glob.glob(str(location_path / "**" / "*.parquet"), recursive=True)
        return [
            p
            for p in all_parquet
            if f"/{INDEX_DIR}/" not in p and f"\\{INDEX_DIR}\\" not in p
        ]


def _write_parquet_table(
    table: pa.Table,
    path: str,
    storage: IndexStorage,
) -> None:
    """Write PyArrow table to Parquet with standard settings.

    Uses DuckDB to write encrypted parquet when encryption is enabled.

    Args:
        table: PyArrow table to write.
        path: Destination file path.
        storage: Storage configuration with is_encrypted flag.
    """
    if storage.is_encrypted:
        conn = duckdb.connect()
        try:
            conn.execute(
                f"PRAGMA add_parquet_key('{ENCRYPTION_KEY_NAME}', '{storage.encryption_key}')"
            )
            # Register the PyArrow table and write with encryption
            conn.register("source_table", table)
            conn.execute(
                f"COPY source_table TO '{path}' "
                f"(FORMAT PARQUET, COMPRESSION 'zstd', "
                f"ENCRYPTION_CONFIG {{footer_key: '{ENCRYPTION_KEY_NAME}'}})"
            )
        finally:
            conn.close()
    else:
        # Write unencrypted using PyArrow
        pq.write_table(
            table,
            path,
            compression="zstd",
            use_dictionary=True,
            write_statistics=True,
        )


async def _delete_file(storage: IndexStorage, path: str) -> None:
    """Delete a file from storage.

    Silently ignores missing files (already deleted by another process).

    Args:
        storage: Storage configuration.
        path: Path to the file to delete.
    """
    if storage.is_remote():
        fs = filesystem(storage.location)
        try:
            fs.rm(path)
        except FileNotFoundError:
            pass  # Already deleted by another process - that's fine
    else:
        Path(path).unlink(missing_ok=True)


def _is_index_file(filename: str) -> bool:
    """Check if a file is an index file (encrypted or not)."""
    return filename.endswith(INDEX_EXTENSION)  # Matches both .idx and .enc.idx


def _extract_timestamp(filename: str) -> str | None:
    """Extract timestamp from an index filename.

    Args:
        filename: Index filename (path or just filename).

    Returns:
        Timestamp string (e.g., "20250101T120000") or None if not matched.
    """
    basename = Path(filename).name

    # Try incremental pattern first
    match = INCREMENTAL_PATTERN.search(basename)
    if match:
        return match.group(1)

    # Try manifest pattern
    match = MANIFEST_PATTERN.search(basename)
    if match:
        return match.group(1)

    return None


def _generate_timestamp() -> str:
    """Generate current UTC timestamp for filenames."""
    return datetime.now(timezone.utc).strftime(TIMESTAMP_FORMAT)


def _generate_manifest_filename(encrypted: bool = False) -> str:
    """Generate filename for a compacted manifest file.

    Includes short UUID to ensure uniqueness when multiple compactions
    happen in the same second.
    """
    timestamp = _generate_timestamp()
    unique_id = uuid()[:8]
    ext = ENCRYPTED_INDEX_EXTENSION if encrypted else INDEX_EXTENSION
    return f"{MANIFEST_PREFIX}{timestamp}_{unique_id}{ext}"


def _make_filenames_relative(table: pa.Table, location: str) -> pa.Table:
    """Convert absolute filenames in a table to paths relative to location.

    The index stores filenames relative to the database root so they work
    correctly when the database is accessed from different locations
    (e.g., local vs S3 vs HuggingFace).

    Args:
        table: PyArrow table with a 'filename' column containing absolute paths.
        location: Database location to strip from filenames.

    Returns:
        Table with filename column containing relative paths.
    """
    if "filename" not in table.column_names:
        return table

    # Normalize location to ensure consistent trailing slash handling
    location_prefix = location.rstrip("/") + "/"

    # Get current filename column
    filenames = table.column("filename")

    # Strip the location prefix from each filename
    # PyArrow's replace_substring works well for this
    relative_filenames = pc.replace_substring(
        filenames,
        pattern=location_prefix,
        replacement="",
        max_replacements=1,  # Only replace the prefix once
    )

    # Replace the filename column with relative paths
    col_idx = table.column_names.index("filename")
    return table.set_column(col_idx, "filename", relative_filenames)


def _read_and_deduplicate_index_files(
    conn: duckdb.DuckDBPyConnection,
    idx_files: list[str],
    enc_config: str,
) -> pa.Table:
    """Read index files and deduplicate by transcript_id.

    If the same transcript_id appears in multiple index files (e.g., from
    retried inserts after partial failures), keeps the entry from the
    newest file. Index files have timestamps in their names, so we can
    determine which is newest by sorting.

    Args:
        conn: DuckDB connection.
        idx_files: List of index file paths (should be sorted by timestamp).
        enc_config: DuckDB encryption config string.

    Returns:
        PyArrow table with deduplicated entries.
    """
    if len(idx_files) == 1:
        # Single file - no deduplication needed
        return conn.execute(
            f"SELECT * FROM read_parquet('{idx_files[0]}'{enc_config})"
        ).fetch_arrow_table()

    # Read each file with an order tag. Higher order = newer file.
    # The idx_files list is sorted with older files first, so we use
    # the list index as the order (newer files have higher indices).
    subqueries = []
    for i, f in enumerate(sorted(idx_files)):
        subqueries.append(
            f"SELECT *, {i} as _file_order FROM read_parquet('{f}'{enc_config})"
        )

    union_query = " UNION ALL BY NAME ".join(subqueries)

    # Deduplicate: keep entry from newest file (highest _file_order)
    return conn.execute(f"""
        SELECT * EXCLUDE (_file_order, _rn) FROM (
            SELECT *,
                   ROW_NUMBER() OVER (
                       PARTITION BY transcript_id
                       ORDER BY _file_order DESC
                   ) as _rn
            FROM ({union_query})
        )
        WHERE _rn = 1
    """).fetch_arrow_table()
