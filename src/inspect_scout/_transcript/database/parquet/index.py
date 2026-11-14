"""Parquet index management for efficient transcript queries.

This module provides standalone functions for managing index files that
enable fast metadata queries without scanning all data files. Index files
are stored in an `_index/` directory with two types:

- Incremental index files: `index_<timestamp>_<uuid>.idx`
  Written during insert operations, one per batch.

- Compacted manifests: `_manifest_<timestamp>_<uuid>.idx`
  Written during compaction, consolidates multiple index files.

Every manifest and every incremental file is read, with two exceptions: a
file that a manifest still present says it replaced, and manifests that carry
no such record, of which only the latest is read. Earlier versions wrote no
record and read only the latest manifest, and their compactions deleted only
the files they had read, so older ones can remain on disk; a manifest that
cannot be read as Parquet also counts as carrying no record.

A compaction deletes only files it listed, after writing a manifest that
holds the entries of every file it read, so an entry is never lost to another
compaction, whichever of them wrote last. The files it lists but does not
read, as above, are deleted with the rest. When several files list one
transcript_id, one row is kept, ranked first by the data file the row points
at.
"""

import json
import os
import re
import shlex
import tempfile
from datetime import datetime, timezone
from logging import getLogger
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from inspect_ai._util.asyncfiles import AsyncFilesystem
from inspect_ai._util.file import filesystem
from inspect_ai._util.path import pretty_path
from inspect_ai.util import trace_message
from shortuuid import uuid

from ...._query.sql import quote_identifier
from ...._util.duckdb import (
    escape_duckdb_glob,
    generated_identifier,
    parquet_view,
    relation_columns,
)
from ..schema import CONTENT_COLUMNS
from .index_cache import get_index_cache_path, load_cached_index, save_index_cache
from .migration import migrate_table
from .types import (
    INCREMENTAL_PREFIX,
    INDEX_DIR,
    INDEX_EXTENSION,
    MANIFEST_PREFIX,
    TIMESTAMP_FORMAT,
    CompactionResult,
    IndexStorage,
)

logger = getLogger(__name__)

# Parquet key-value metadata of a manifest: JSON list of the index file names
# it replaces (the files its writer listed before writing it).
_REPLACES_KEY = "inspect_scout.replaces"

# Rank of an index row among rows for the same transcript_id, taken from the
# data file the row points at so that it is the same whichever index file
# carries the row. A data file written without a session id comes first:
# session compaction writes one in place of the session's own files and then
# deletes those. Then the newest `<timestamp>_<uuid>.parquet` name, so a
# retried insert written in a later second outranks the attempt it retried;
# rows still tied are settled as described in `_one_row_per_transcript`.
_DATA_FILE_RANK = (
    r"regexp_matches(coalesce(filename, ''), "
    r"'(^|[/\\])transcripts_\d{8}T\d{6}_[0-9a-zA-Z]+\.parquet$') DESC, "
    r"coalesce(regexp_extract(filename, "
    r"'(\d{8}T\d{6})_[0-9a-zA-Z]+\.parquet$', 1), '') DESC"
)


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
            suffix=INDEX_EXTENSION, delete=False
        ) as tmp_file:
            tmp_path = tmp_file.name

        try:
            _write_parquet_table(table, tmp_path)

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
        tmp_filename = f".tmp_{uuid()[:8]}{INDEX_EXTENSION}"
        local_tmp_path = output_path.parent / tmp_filename

        try:
            _write_parquet_table(table, str(local_tmp_path))
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
    1. Read the discovered index files into merged manifest, skipping the
       files `_without_replaced_files` drops: those a discovered manifest
       already replaced, and all but the latest manifest without a record
    2. Write single compacted manifest file, recording every discovered file
       as replaced
    3. (Only after success) Delete the discovered index files, skipped ones
       included

    Only files discovered at the start of compaction are deleted. Files
    written concurrently by other sessions survive for the next compaction,
    preventing a race condition where parallel writers' index entries could
    be permanently lost.

    Args:
        conn: DuckDB connection.
        storage: Storage configuration.
        _retry_count: Internal retry counter (do not set manually).

    Returns:
        CompactionResult with stats about files merged/deleted.
    """
    MAX_RETRIES = 3
    # Only the files discovered here will be deleted after compaction — files
    # written concurrently by other sessions will survive for the next compaction.
    idx_files = await _discover_index_files(storage)

    if not idx_files:
        # No index files at all
        return CompactionResult(
            index_files_merged=0,
            index_files_deleted=0,
            new_index_path="",
        )

    try:
        merged_table = _read_and_deduplicate_index_files(
            conn, _without_replaced_files(conn, idx_files)
        )
    except duckdb.IOException as e:
        if _is_missing_index_file(e) and _retry_count < MAX_RETRIES:
            # Files changed during operation - retry with fresh discovery
            logger.warning(
                f"Index file access failed during compaction (attempt {_retry_count + 1}), retrying"
            )
            return await compact_index(conn, storage, _retry_count + 1)
        raise
    except duckdb.Error as e:
        if not _is_unreadable_parquet(e):
            raise
        # An index file cannot be read as Parquet, or a manifest holds an
        # invalid record of the files it replaces.
        raise _unreadable_index_error(storage, e) from e

    # Write compacted manifest (even if only 1 file - converts incremental to manifest)
    new_filename = _generate_manifest_filename()
    new_path = await append_index(
        _recording_replaced_files(merged_table, idx_files), storage, new_filename
    )

    # Delete merged index files (only after successful write)
    deleted_idx_count = 0
    for old_file in idx_files:
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

    with parquet_view(
        conn,
        data_files,
        union_by_name=True,
        filename=True,
    ) as source_view:
        all_columns = relation_columns(conn, source_view)

        # Build exclude clause for large content columns if they exist
        exclude_columns = [c for c in CONTENT_COLUMNS if c in all_columns]
        exclude_clause = (
            " EXCLUDE ("
            + ", ".join(quote_identifier(column) for column in exclude_columns)
            + ")"
            if exclude_columns
            else ""
        )

        # Read metadata into Arrow table with deduplication.
        # If the same transcript_id exists in multiple data files (e.g., from
        # retried inserts after partial failures, or a session being
        # compacted), keep only one entry.
        result = conn.execute(
            _one_row_per_transcript(
                f"(SELECT *{exclude_clause} FROM {quote_identifier(source_view)})"
            )
        ).fetch_arrow_table()

    # Convert absolute filenames to relative paths (relative to database location)
    result = _make_filenames_relative(result, storage.location)

    # Write as manifest file (this is a full rebuild, so use manifest naming).
    # It replaces every index file listed above, including any that cannot be
    # deleted below.
    filename = _generate_manifest_filename()
    new_path = await append_index(
        _recording_replaced_files(result, existing_idx_files), storage, filename
    )

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
    """
    MAX_RETRIES = 3
    idx_files = await _discover_index_files(storage)

    if not idx_files:
        # No index files - create empty table
        conn.execute(f"""
            CREATE TABLE {quote_identifier(table_name)} AS
            SELECT ''::VARCHAR AS transcript_id, ''::VARCHAR AS filename
            WHERE FALSE
        """)
        return 0

    # For remote storage, try to use local cache
    cache_path: Path | None = None
    if storage.is_remote():
        cache_path = get_index_cache_path(storage, idx_files)

        # Try loading from cache
        cached_count = load_cached_index(conn, cache_path, table_name)
        if cached_count is not None:
            trace_message(
                logger, "Scout Index Cache", f"Loaded from cache: {cache_path}"
            )
            # migrate fields for backwards compatiblity with databases created from eval_log
            migrate_table(conn, table_name)
            return cached_count

    # Create table from index files
    # Handle file-not-found errors from concurrent operations with retry
    try:
        live_files = _without_replaced_files(conn, idx_files)
        with parquet_view(conn, live_files, union_by_name=True) as source_view:
            conn.execute(
                f"CREATE TABLE {quote_identifier(table_name)} AS "
                f"SELECT * FROM {quote_identifier(source_view)}"
            )
    except duckdb.IOException as e:
        if _is_missing_index_file(e) and _retry_count < MAX_RETRIES:
            # File was deleted by concurrent operation - rediscover and retry
            logger.warning(
                f"Index file access failed (attempt {_retry_count + 1}), retrying"
            )
            return await init_index_table(conn, storage, table_name, _retry_count + 1)
        raise
    except duckdb.Error as e:
        if not _is_unreadable_parquet(e):
            raise
        # An index file cannot be read as Parquet, or a manifest holds an
        # invalid record of the files it replaces.
        raise _unreadable_index_error(storage, e) from e

    if len(live_files) > 1:
        # Several files can list one transcript, such as the manifests of two
        # concurrent compactions.
        _delete_repeated_rows(conn, table_name)

    # Return row count
    result = conn.execute(
        f"SELECT COUNT(*) FROM {quote_identifier(table_name)}"
    ).fetchone()
    row_count = result[0] if result else 0

    # For remote storage, save to cache
    if storage.is_remote() and cache_path is not None:
        try:
            save_index_cache(conn, cache_path, table_name)
            trace_message(logger, "Scout Index Cache", f"Saved to cache: {cache_path}")
        except Exception as e:
            logger.warning(f"Failed to save index cache: {e}")

    # migrate fields for backwards compatiblity with databases created from eval_log
    migrate_table(conn, table_name)

    return row_count


def _is_missing_index_file(error: duckdb.IOException) -> bool:
    """Recognize DuckDB's local and HTTP missing-file errors."""
    message = str(error).lower()
    return (
        "could not open file" in message
        or "no such file" in message
        or "no files found that match the pattern" in message
        or (
            isinstance(error, duckdb.HTTPException)
            and re.search(r"[\"']\s*:\s*404\b", message) is not None
        )
    )


def _is_unreadable_parquet(error: duckdb.Error) -> bool:
    """Recognize DuckDB's errors for a file whose content is not valid Parquet.

    A file that is too small, lacks the Parquet magic bytes or states an
    impossible footer length raises InvalidInputException. One whose footer
    or pages cannot be decoded raises the base `duckdb.Error` itself.
    """
    return (
        isinstance(error, duckdb.InvalidInputException) or type(error) is duckdb.Error
    )


def _unreadable_index_error(
    storage: IndexStorage, error: duckdb.Error
) -> duckdb.InvalidInputException:
    """Name the rebuild command in the error for an index file that cannot be used."""
    return duckdb.InvalidInputException(
        f"{error}\nRun `scout db index "
        f"{shlex.quote(pretty_path(storage.location))}` to rebuild the index "
        "from the data files."
    )


async def _discover_index_files(storage: IndexStorage) -> list[str]:
    """Find index files in _index/ directory.

    Returns every manifest and every incremental file. With concurrent
    compactions the newest manifest is not a superset of the others: a
    compaction that listed the index earlier can write its manifest later.
    Every entry a reader could see is still in some file, because a
    compaction deletes only the files it listed, after writing a manifest
    that holds the entries of those it read. Callers that read the files pass
    the result through `_without_replaced_files`, which decides which of
    them are read.

    Args:
        storage: Storage configuration.

    Returns:
        List of index file paths (manifests first).
    """
    index_dir = storage.index_dir_path()

    async with AsyncFilesystem() as fs:
        try:
            all_idx_files = [
                uri async for uri in fs.iter_files(index_dir, "*" + INDEX_EXTENSION)
            ]
        except FileNotFoundError:
            # Index directory doesn't exist yet
            return []

    if not all_idx_files:
        return []

    # Separate manifests from incremental files
    manifest_files = [
        f for f in all_idx_files if Path(f).name.startswith(MANIFEST_PREFIX)
    ]
    incremental_files = [
        f for f in all_idx_files if Path(f).name.startswith(INCREMENTAL_PREFIX)
    ]

    return sorted(manifest_files) + sorted(incremental_files)


async def _list_all_index_files(storage: IndexStorage) -> list[str]:
    """List ALL index files in _index/ directory.

    Unlike _discover_index_files(), this returns every .idx file whatever its
    name, used for cleanup operations like create_index().

    Args:
        storage: Storage configuration.

    Returns:
        List of all index file paths.
    """
    index_dir = storage.index_dir_path()

    async with AsyncFilesystem() as fs:
        try:
            return [
                uri async for uri in fs.iter_files(index_dir, "*" + INDEX_EXTENSION)
            ]
        except FileNotFoundError:
            return []


async def _discover_data_files(storage: IndexStorage) -> list[str]:
    """Find all .parquet data files (excluding _index/).

    Args:
        storage: Storage configuration.

    Returns:
        List of data file paths.
    """
    async with AsyncFilesystem() as fs:
        try:
            return [
                uri
                async for uri in fs.iter_files(
                    storage.location, "*.parquet", recursive=True
                )
                if f"/{INDEX_DIR}/" not in uri and f"\\{INDEX_DIR}\\" not in uri
            ]
        except FileNotFoundError:
            return []


def _write_parquet_table(
    table: pa.Table,
    path: str,
) -> None:
    """Write PyArrow table to Parquet with standard settings.

    Args:
        table: PyArrow table to write.
        path: Destination file path.
    """
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
    """Check if a file is an index file."""
    return filename.endswith(INDEX_EXTENSION)


def _generate_timestamp() -> str:
    """Generate current UTC timestamp for filenames."""
    return datetime.now(timezone.utc).strftime(TIMESTAMP_FORMAT)


def _generate_manifest_filename() -> str:
    """Generate filename for a compacted manifest file.

    Includes short UUID to ensure uniqueness when multiple compactions
    happen in the same second.
    """
    timestamp = _generate_timestamp()
    unique_id = uuid()[:8]
    return f"{MANIFEST_PREFIX}{timestamp}_{unique_id}{INDEX_EXTENSION}"


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
) -> pa.Table:
    """Read index files and deduplicate by transcript_id.

    If the same transcript_id appears in multiple index files (e.g., from
    retried inserts after partial failures, session compaction, or manifests
    written by concurrent compactions), keeps one entry: see
    `_one_row_per_transcript`.

    Args:
        conn: DuckDB connection.
        idx_files: List of index file paths.

    Returns:
        PyArrow table with deduplicated entries.
    """
    if len(idx_files) == 1:
        # Single file - no deduplication needed
        with parquet_view(conn, idx_files[0]) as source_view:
            return conn.execute(
                f"SELECT * FROM {quote_identifier(source_view)}"
            ).fetch_arrow_table()

    # Unify the schemas in one bind that reads no rows, then insert each file by
    # name with its own statement: one SQL union over every file exceeds DuckDB
    # 1.4's expression depth on large indexes, and before DuckDB 1.5.3 a
    # multi-file scan cannot read a struct column from a file that stores the
    # column as another type.
    merged_table = quote_identifier(generated_identifier("index_merge"))
    file_order = quote_identifier(generated_identifier("index_order"))
    ordered_files = sorted(idx_files)
    try:
        with parquet_view(conn, ordered_files, union_by_name=True) as source_view:
            conn.execute(
                f"CREATE TEMP TABLE {merged_table} AS "
                f"SELECT *, 0 AS {file_order} FROM {quote_identifier(source_view)} "
                "WITH NO DATA"
            )
        for order, path in enumerate(ordered_files):
            conn.execute(
                f"INSERT INTO {merged_table} BY NAME "
                f"SELECT *, ? AS {file_order} FROM read_parquet(?)",
                [order, escape_duckdb_glob(path)],
            )

        return conn.execute(
            _one_row_per_transcript(merged_table, file_order)
        ).fetch_arrow_table()
    finally:
        conn.execute(f"DROP TABLE IF EXISTS {merged_table}")


def _one_row_per_transcript(source: str, file_order: str | None = None) -> str:
    """Build a SELECT that keeps one row per transcript_id.

    Rows are ranked by `_DATA_FILE_RANK` first, not by the index file that
    carries them: a manifest written late by a concurrent compaction can hold
    an older row than a manifest written before it.

    Args:
        source: Quoted relation (or parenthesized query) holding the rows.
        file_order: Quoted column giving the position of each row's index file
            in sorted order (manifests, then incrementals by name). The later
            file wins among rows `_DATA_FILE_RANK` ranks equally: rows whose
            data files are both session-free or both not, with the same
            timestamp in their names or none in either. The column is
            dropped from the result. Without it those rows are settled by
            data file name.

    Returns:
        SQL text of the SELECT.
    """
    rows = quote_identifier(generated_identifier("index_rows"))
    repeated = quote_identifier(generated_identifier("index_repeated"))
    rank = quote_identifier(generated_identifier("index_rank"))
    tie_break = "coalesce(filename, '')" if file_order is None else file_order
    keep = "*" if file_order is None else f"* EXCLUDE ({file_order})"
    exclude = rank if file_order is None else f"{rank}, {file_order}"
    # Only transcripts listed more than once are ranked, so a large index with a
    # few repeated rows costs little more than reading it.
    return f"""
        WITH {rows} AS (SELECT * FROM {source}),
        {repeated} AS (
            SELECT transcript_id FROM {rows} GROUP BY transcript_id HAVING count(*) > 1
        )
        SELECT {keep} FROM {rows} ANTI JOIN {repeated} USING (transcript_id)
        UNION ALL BY NAME
        SELECT * EXCLUDE ({exclude}) FROM (
            SELECT *,
                   ROW_NUMBER() OVER (
                       PARTITION BY transcript_id
                       ORDER BY {_DATA_FILE_RANK}, {tie_break} DESC
                   ) AS {rank}
            FROM {rows} SEMI JOIN {repeated} USING (transcript_id)
        )
        WHERE {rank} = 1
    """


def _delete_repeated_rows(conn: duckdb.DuckDBPyConnection, table_name: str) -> None:
    """Keep one row per transcript_id in an index table, deleting the others.

    Ranks rows as `_one_row_per_transcript` does without a file order. The
    rows that stay keep the order they were read in, as they had when only
    one manifest was read, so a query with a LIMIT and no ORDER BY returns
    the same rows at every open.

    Args:
        conn: DuckDB connection.
        table_name: Name of the index table.
    """
    table = quote_identifier(table_name)
    rank = quote_identifier(generated_identifier("index_rank"))
    # Rows are deleted by DuckDB's `rowid`. A metadata column of that name, in
    # any case, would be used in its place, so it is renamed for the delete.
    named_rowid = [
        c for c in relation_columns(conn, table_name) if c.lower() == "rowid"
    ]
    renamed = quote_identifier(generated_identifier("index_rowid"))
    for column in named_rowid:
        conn.execute(
            f"ALTER TABLE {table} RENAME COLUMN {quote_identifier(column)} TO {renamed}"
        )
    try:
        conn.execute(f"""
            DELETE FROM {table} WHERE rowid IN (
                SELECT rowid FROM (
                    SELECT rowid,
                           ROW_NUMBER() OVER (
                               PARTITION BY transcript_id
                               ORDER BY {_DATA_FILE_RANK},
                                        coalesce(filename, '') DESC, rowid
                           ) AS {rank}
                    FROM {table}
                    WHERE transcript_id IN (
                        SELECT transcript_id FROM {table}
                        GROUP BY transcript_id HAVING count(*) > 1
                    )
                )
                WHERE {rank} > 1
            )
        """)
    finally:
        for column in named_rowid:
            conn.execute(
                f"ALTER TABLE {table} RENAME COLUMN {renamed} TO {quote_identifier(column)}"
            )


def _recording_replaced_files(table: pa.Table, idx_files: list[str]) -> pa.Table:
    """Mark a manifest table as replacing the index files its writer listed.

    Args:
        table: Table about to be written as a manifest.
        idx_files: Paths of the index files the manifest replaces.

    Returns:
        The table with the replaced file names in its schema metadata, which
        Parquet stores as key-value metadata.
    """
    metadata = dict(table.schema.metadata or {})
    metadata[_REPLACES_KEY.encode()] = json.dumps(
        sorted(Path(f).name for f in idx_files)
    ).encode()
    return table.replace_schema_metadata(metadata)


def _without_replaced_files(
    conn: duckdb.DuckDBPyConnection, idx_files: list[str]
) -> list[str]:
    """Drop the index files in the list that should not be read.

    A file that a manifest in the list says it replaced is dropped. It stays
    on disk when it cannot be deleted. Its entries are in the manifest that
    replaced it, unless that manifest's writer left them out: a rebuild, which
    takes its entries from the data files, or a compaction that did not read
    the file for the reason below. Reading it again is wasted work or wrong.

    Of the manifests that carry no record, only the one with the latest name
    is read. Scout versions that did not write the record read only that
    manifest, and their compactions deleted only the files they had read, so
    an older one can remain, damaged or holding rows a rebuild dropped, in a
    database that opened without error. A manifest that cannot be read as
    Parquet counts as carrying no record.

    Telling whether a manifest carries a record means reading its footer, so
    every manifest that no other replaces is opened, including the older ones
    that are then not read. One that cannot be opened at all, such as for
    lack of permission, raises unless another manifest replaces it: treating
    that as "no record" would also drop a manifest this version wrote whenever
    storage fails for a moment.

    Raises:
        duckdb.IOException: If a manifest that no other manifest replaces
            cannot be opened. Callers rediscover when it has been deleted.
        duckdb.InvalidInputException: If the record of a manifest that no
            other manifest replaces is not a JSON list of names.

    Args:
        conn: DuckDB connection.
        idx_files: Discovered index file paths.

    Returns:
        The paths to read, in their original order.
    """
    if len(idx_files) < 2:
        return idx_files
    replaced: set[str] = set()
    unrecorded: list[str] = []
    invalid: list[str] = []
    unopened: list[tuple[str, duckdb.IOException]] = []
    manifests = [f for f in idx_files if Path(f).name.startswith(MANIFEST_PREFIX)]
    # Latest name first, which is usually the latest written: a manifest names
    # every file its writer listed, so the record inside a manifest that is
    # itself replaced adds nothing and need not be fetched.
    for manifest in sorted(manifests, reverse=True):
        name = Path(manifest).name
        if name in replaced:
            continue
        try:
            records = conn.execute(
                "SELECT try(decode(value)) FROM parquet_kv_metadata(?) "
                "WHERE key = encode(?)",
                [escape_duckdb_glob(manifest), _REPLACES_KEY],
            ).fetchall()
        except duckdb.IOException as e:
            # Deleted since discovery, or not open to this user. Raised below
            # unless another manifest replaces it; the caller rediscovers
            # when the file is missing.
            unopened.append((name, e))
            continue
        except duckdb.Error as e:
            if not _is_unreadable_parquet(e):
                raise
            # Not readable as Parquet, so it counts as carrying no record. If
            # nothing below drops it, reading it raises this error again.
            records = []
        if not records:
            unrecorded.append(name)
        for (value,) in records:
            names = _replaced_names(value)
            if names is None:
                invalid.append(manifest)
            else:
                replaced.update(names)
    for name, error in unopened:
        if name not in replaced:
            raise error
    for manifest in invalid:
        if Path(manifest).name not in replaced:
            raise duckdb.InvalidInputException(
                f"Index file {pretty_path(manifest)} has an invalid "
                f"{_REPLACES_KEY} record."
            )
    unrecorded = sorted(name for name in unrecorded if name not in replaced)
    dropped = replaced.union(unrecorded[:-1])
    return [f for f in idx_files if Path(f).name not in dropped]


def _replaced_names(record: str | None) -> list[str] | None:
    """Parse the replaced-file record of a manifest.

    Args:
        record: Value stored under `_REPLACES_KEY`, or None if it is not text.

    Returns:
        The index file names the manifest replaces, or None if the record is
        not a JSON list of names.
    """
    if record is None:
        return None
    try:
        names = json.loads(record)
    except ValueError:
        return None
    if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
        return None
    return names
