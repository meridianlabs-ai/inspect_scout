"""DuckDB/Parquet-backed transcript database implementation."""

import glob
import hashlib
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from logging import getLogger
from pathlib import Path
from typing import Any, AsyncIterable, AsyncIterator, Iterable, cast

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from inspect_ai._util.asyncfiles import AsyncFilesystem
from inspect_ai._util.error import PrerequisiteError
from inspect_ai._util.file import filesystem
from inspect_ai.util import trace_action
from typing_extensions import override

from inspect_scout._display._display import display
from inspect_scout._scanspec import ScanTranscripts
from inspect_scout._transcript.database.factory import transcripts_from_db_snapshot
from inspect_scout._transcript.types import RESERVED_COLUMNS
from inspect_scout._transcript.util import LazyJSONDict
from inspect_scout._util.filesystem import ensure_filesystem_dependencies

from ..json.load_filtered import load_filtered_transcript
from ..local_files_cache import init_task_files_cache
from ..metadata import Condition
from ..transcripts import (
    Transcripts,
    TranscriptsQuery,
    TranscriptsReader,
)
from ..types import Transcript, TranscriptContent, TranscriptInfo
from .database import TranscriptsDB
from .encryption import (
    ENCRYPTION_KEY_ENV,
    ENCRYPTION_KEY_NAME,
    get_encryption_key_from_env,
    validate_encryption_key,
)
from .reader import TranscriptsDBReader
from .source import TranscriptsSource

logger = getLogger(__name__)


PARQUET_TRANSCRIPTS_GLOB = "*.parquet"


class ParquetTranscriptInfo(TranscriptInfo):
    """TranscriptInfo with parquet filename for efficient content lookup."""

    filename: str


class ParquetTranscriptsDB(TranscriptsDB):
    """DuckDB-based transcript database using Parquet file storage.

    Stores transcript metadata in Parquet files for efficient querying,
    with content stored as JSON strings and loaded on-demand. Supports
    S3 storage with hybrid caching strategy.
    """

    def __init__(
        self,
        location: str,
        target_file_size_mb: float = 100,
        row_group_size_mb: float = 32,
        query: TranscriptsQuery | None = None,
        snapshot: ScanTranscripts | None = None,
    ) -> None:
        """Initialize Parquet transcript database.

        Args:
            location: Directory path (local or S3) containing Parquet files.
            target_file_size_mb: Target size in MB for each Parquet file. Individual
                transcripts may cause files to exceed this limit. Can be fractional.
            row_group_size_mb: Target row group size in MB for Parquet files. Can be fractional.
            query: Optional query to apply during table creation for optimization.
                If provided, WHERE conditions are pushed down to Parquet scan,
                and SHUFFLE/LIMIT are applied during table creation.
                Query-time filters are additive (AND combination).
            snapshot: Snapshot info. This is a mapping of transcript_id => filename
                which we can use to avoid crawling.
        """
        super().__init__(location)
        self._target_file_size_mb = target_file_size_mb
        self._row_group_size_mb = row_group_size_mb
        self._query = query
        self._snapshot = snapshot

        # could be called in a spawed worker where there are no fs deps yet
        ensure_filesystem_dependencies(location)

        # Note: Bloom filter support for transcript_id would be beneficial for point
        # lookups, but PyArrow doesn't yet support writing bloom filters (as of v21.0.0).
        # PR #37400 is in progress: https://github.com/apache/arrow/pull/37400
        # When available, add: bloom_filter_columns=['transcript_id'] to write_table calls.

        # initialize cache
        self._cache = init_task_files_cache()

        # State (initialized in connect)
        self._conn: duckdb.DuckDBPyConnection | None = None
        self._fs: AsyncFilesystem | None = None
        self._current_shuffle_seed: int | None = None
        self._transcript_ids: set[str] = set()
        self._file_columns_cache: dict[str, set[str]] = {}
        self._parquet_pattern: str | None = None
        self._exclude_clause: str = ""
        self._is_encrypted: bool = False

    @override
    async def connect(self) -> None:
        """Initialize DuckDB connection and discover Parquet files."""
        if self._conn is not None:
            return

        with trace_action(
            logger,
            "Scout DuckDB Init",
            f"Initializing DuckDB connection for {self._location}.",
        ):
            # Create DuckDB connection
            self._conn = duckdb.connect(":memory:")

            # Enable Parquet metadata caching for better performance when querying same files
            # multiple times (e.g., SELECT for metadata, then read() for content)
            self._conn.execute("SET parquet_metadata_cache=true")

            # Initialize filesystem and cache
            assert self._location is not None
            if self._is_s3() or self._is_hf():
                # will use to enumerate files
                self._fs = AsyncFilesystem()

                # Install httpfs extension for S3 support
                self._conn.execute("INSTALL httpfs")
                self._conn.execute("LOAD httpfs")

                # Enable DuckDB's HTTP/S3 caching features for better performance
                self._conn.execute("SET enable_http_metadata_cache=true")
                self._conn.execute("SET http_keep_alive=true")
                self._conn.execute("SET http_timeout=30000")  # 30 seconds

                # auth
                if self._is_s3():
                    self._init_s3_auth()
                if self._is_hf():
                    self._init_hf_auth()

        # Discover and register Parquet files
        await self._create_transcripts_table()

    @override
    async def disconnect(self) -> None:
        """Close DuckDB connection and cleanup resources."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            self._current_shuffle_seed = None

        if self._fs is not None:
            await self._fs.close()
            self._fs = None

    @override
    async def insert(
        self,
        transcripts: Iterable[Transcript]
        | AsyncIterable[Transcript]
        | Transcripts
        | TranscriptsSource
        | pa.RecordBatchReader,
    ) -> None:
        """Insert transcripts, writing one Parquet file per batch.

        Transcript ids that are already in the database are not inserted.

        Args:
            transcripts: Transcripts to insert (iterable, async iterable, source,
                or PyArrow RecordBatchReader for efficient Arrow-native insertion).
        """
        assert self._conn is not None

        # if we don't yet have a list of transcript ids then query for one
        if len(self._transcript_ids) == 0:
            cursor = self._conn.execute("SELECT transcript_id FROM transcript_index")
            column_names = [desc[0] for desc in cursor.description]
            for cursor_row in cursor.fetchall():
                row_dict = dict(zip(column_names, cursor_row, strict=True))
                self._transcript_ids.add(row_dict["transcript_id"])

        # two insert codepaths, one for arrow batch, one for transcripts
        if isinstance(transcripts, pa.RecordBatchReader):
            await self._insert_from_record_batch_reader(transcripts)
        else:
            await self._insert_from_transcripts(transcripts)

        # refresh the view
        await self._create_transcripts_table()

    @override
    async def select(
        self,
        where: list[Condition] | None = None,
        limit: int | None = None,
        shuffle: bool | int = False,
    ) -> AsyncIterator[TranscriptInfo]:
        """Query transcripts matching conditions.

        Args:
            where: List of conditions to filter by.
            limit: Optional limit on results.
            shuffle: If True or int seed, shuffle results deterministically.

        Yields:
            TranscriptInfo instances (metadata only, no content).
        """
        assert self._conn is not None

        # Build WHERE clause
        where_clause, where_params = self._build_where_clause(where)
        # Note: transcripts table already excludes messages/events, so just SELECT *
        sql = f"SELECT * FROM transcripts{where_clause}"

        # Add ORDER BY for shuffle
        if shuffle:
            seed = 0 if shuffle is True else shuffle
            self._register_shuffle_function(seed)
            sql += " ORDER BY shuffle_hash(transcript_id)"

        # Add LIMIT
        params = where_params.copy()
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)

        # Execute query and yield results (stream rows in batches to avoid full materialization)
        cursor = self._conn.execute(sql, params)
        column_names = [desc[0] for desc in cursor.description]
        batch_size = 1000
        while True:
            rows = cursor.fetchmany(batch_size)
            if not rows:
                break
            for row in rows:
                row_dict = dict(zip(column_names, row, strict=True))

                # Extract reserved fields (optional fields use .get() for missing columns)
                transcript_id = row_dict["transcript_id"]
                transcript_source_type = row_dict.get("source_type")
                transcript_source_id = row_dict.get("source_id")
                transcript_source_uri = row_dict.get("source_uri")
                transcript_filename = row_dict.get("filename")

                # Reconstruct metadata from all non-reserved columns
                # Use LazyJSONDict to defer JSON parsing until values are accessed
                metadata_dict = {
                    col: value
                    for col, value in row_dict.items()
                    if col not in RESERVED_COLUMNS and value is not None
                }
                metadata = LazyJSONDict(metadata_dict)

                # Use model_construct to bypass Pydantic validation which would
                # convert LazyJSONDict to a plain dict, defeating lazy parsing
                yield ParquetTranscriptInfo.model_construct(
                    transcript_id=transcript_id,
                    source_type=transcript_source_type,
                    source_id=transcript_source_id,
                    source_uri=transcript_source_uri,
                    metadata=metadata,
                    filename=transcript_filename,
                )

    @override
    async def transcript_ids(
        self,
        where: list[Condition] | None = None,
        limit: int | None = None,
        shuffle: bool | int = False,
    ) -> dict[str, str | None]:
        """Get transcript IDs matching conditions.

        Optimized implementation that queries directly from the index table
        when no WHERE conditions are specified, avoiding Parquet file access.

        Args:
            where: Condition(s) to filter by.
            limit: Maximum number to return.
            shuffle: Randomly shuffle results (pass `int` for reproducible seed).

        Returns:
            Dict of transcript IDs and parquet filenames
        """
        assert self._conn is not None

        if not where:
            # No conditions - query index table directly (faster, in-memory)
            sql = "SELECT transcript_id, filename FROM transcript_index"

            # Add ORDER BY for shuffle
            if shuffle:
                seed = 0 if shuffle is True else shuffle
                self._register_shuffle_function(seed)
                sql += " ORDER BY shuffle_hash(transcript_id)"

            # Add LIMIT
            params: list[Any] = []
            if limit is not None:
                sql += " LIMIT ?"
                params.append(limit)

            result = self._conn.execute(sql, params).fetchall()
            return {row[0]: row[1] for row in result}
        else:
            # Has conditions - need to query VIEW for metadata filtering
            transcript_ids: dict[str, str | None] = {}
            async for info in self.select(where, limit, shuffle):
                parquet_info = cast(ParquetTranscriptInfo, info)
                transcript_ids[parquet_info.transcript_id] = parquet_info.filename

            return transcript_ids

    @override
    async def read(self, t: TranscriptInfo, content: TranscriptContent) -> Transcript:
        """Load full transcript content using DuckDB.

        Args:
            t: TranscriptInfo identifying the transcript.
            content: Filter for which messages/events to load.

        Returns:
            Full Transcript with filtered content.
        """
        assert self._conn is not None

        with trace_action(
            logger, "Scout Parquet Read", f"Reading from {t.transcript_id}"
        ):
            # Determine which columns we need to read
            need_messages = content.messages is not None
            need_events = content.events is not None

            if not need_messages and not need_events:
                # No content needed - use model_construct to preserve LazyJSONDict
                return Transcript.model_construct(
                    transcript_id=t.transcript_id,
                    source_type=t.source_type,
                    source_id=t.source_id,
                    source_uri=t.source_uri,
                    metadata=t.metadata,
                )

            # Build column list for SELECT
            columns = []
            if need_messages:
                columns.append("messages")
            if need_events:
                columns.append("events")

            # First, get the filename from the index table (fast indexed lookup)
            filename_result = self._conn.execute(
                "SELECT filename FROM transcript_index WHERE transcript_id = ?",
                [t.transcript_id],
            ).fetchone()

            if not filename_result:
                # Transcript not found in metadata table - use model_construct to preserve LazyJSONDict
                return Transcript.model_construct(
                    transcript_id=t.transcript_id,
                    source_type=t.source_type,
                    source_id=t.source_id,
                    source_uri=t.source_uri,
                    metadata=t.metadata,
                )

            # Now read content from just that specific file (targeted I/O)
            # This avoids scanning all files - only reads from the one file containing this transcript
            filename = filename_result[0]

            # Try optimistic read first (fast path for files with all columns)
            enc_config = self._read_parquet_encryption_config()
            try:
                sql = f"SELECT {', '.join(columns)} FROM read_parquet(?, union_by_name=true{enc_config}) WHERE transcript_id = ?"
                result = self._conn.execute(sql, [filename, t.transcript_id]).fetchone()
                columns_read = columns  # All requested columns were available
            except duckdb.BinderException:
                # Column doesn't exist - check which ones are available (cached)
                available = self._get_available_content_columns(filename)
                columns_read = [c for c in columns if c in available]

                if not columns_read:
                    # No content columns available - return empty content
                    return Transcript.model_construct(
                        transcript_id=t.transcript_id,
                        source_type=t.source_type,
                        source_id=t.source_id,
                        source_uri=t.source_uri,
                        metadata=t.metadata,
                    )

                # Retry with only available columns
                sql = f"SELECT {', '.join(columns_read)} FROM read_parquet(?, union_by_name=true{enc_config}) WHERE transcript_id = ?"
                result = self._conn.execute(sql, [filename, t.transcript_id]).fetchone()

            if not result:
                # Transcript not found - use model_construct to preserve LazyJSONDict
                return Transcript.model_construct(
                    transcript_id=t.transcript_id,
                    source_type=t.source_type,
                    source_id=t.source_id,
                    source_uri=t.source_uri,
                    metadata=t.metadata,
                )

            # Extract column values based on which columns were actually read
            messages_json: str | None = None
            events_json: str | None = None

            col_idx = 0
            if "messages" in columns_read:
                messages_json = result[col_idx]
                col_idx += 1
            if "events" in columns_read:
                events_json = result[col_idx]

            # Stream combined JSON construction
            async def stream_content_bytes() -> AsyncIterator[bytes]:
                """Stream construction of combined JSON object."""
                yield b"{"

                # Stream messages if we have them
                if messages_json:
                    yield b'"messages": '
                    # Stream the array directly in 64KB chunks
                    messages_bytes = messages_json.encode("utf-8")
                    chunk_size = 64 * 1024
                    for i in range(0, len(messages_bytes), chunk_size):
                        yield messages_bytes[i : i + chunk_size]

                # Add separator if we have both
                if messages_json and events_json:
                    yield b", "

                # Stream events if we have them
                if events_json:
                    yield b'"events": '
                    # Stream the array directly in 64KB chunks
                    events_bytes = events_json.encode("utf-8")
                    chunk_size = 64 * 1024
                    for i in range(0, len(events_bytes), chunk_size):
                        yield events_bytes[i : i + chunk_size]

                # Close the combined JSON object
                yield b"}"

            # Use existing streaming JSON parser with filtering
            return await load_filtered_transcript(
                stream_content_bytes(),
                t,
                content.messages,
                content.events,
            )

    async def _insert_from_transcripts(
        self,
        transcripts: Iterable[Transcript]
        | AsyncIterable[Transcript]
        | Transcripts
        | TranscriptsSource,
    ) -> None:
        batch: list[dict[str, Any]] = []
        current_batch_size = 0
        target_size_bytes = self._target_file_size_mb * 1024 * 1024

        with display().text_progress("Transcript", True) as progress:
            async for transcript in self._as_async_iterator(transcripts):
                progress.update(text=transcript.transcript_id)

                # Serialize once for both size calculation and writing
                row = self._transcript_to_row(transcript)
                row_size = self._estimate_row_size(row)

                # Add transcript ID for duplicate tracking
                self._transcript_ids.add(transcript.transcript_id)

                # Write batch if adding this row would exceed target size
                if (
                    current_batch_size > 0
                    and current_batch_size + row_size >= target_size_bytes
                ):
                    await self._write_parquet_batch(batch)
                    batch = []
                    current_batch_size = 0

                # Add row to batch
                batch.append(row)
                current_batch_size += row_size

            # write any leftover elements
            if batch:
                await self._write_parquet_batch(batch)

    async def _insert_from_record_batch_reader(
        self, reader: pa.RecordBatchReader
    ) -> None:
        """Insert transcripts from Arrow RecordBatchReader.

        Filters duplicates, respects file size limits, validates schema.

        Args:
            reader: PyArrow RecordBatchReader containing transcript data.
        """
        # Validate schema once
        self._validate_record_batch_schema(reader.schema)

        # Build exclude array for duplicate filtering (explicit type for empty set)
        assert self._transcript_ids is not None
        exclude_array = pa.array(self._transcript_ids, type=pa.string())

        # Batch accumulation state
        accumulated_batches: list[pa.RecordBatch] = []
        accumulated_size = 0
        target_size_bytes = self._target_file_size_mb * 1024 * 1024
        total_rows = 0

        with display().text_progress("Rows", True) as progress:
            for batch in reader:
                # Filter out duplicates
                is_duplicate = pc.is_in(
                    batch.column("transcript_id"), value_set=exclude_array
                )
                mask = pc.invert(is_duplicate)
                filtered_batch = batch.filter(mask)

                # Skip if all rows were duplicates
                if filtered_batch.num_rows == 0:
                    continue

                # Track new IDs for subsequent batches (cast is safe - schema validated)
                new_ids = cast(
                    list[str], filtered_batch.column("transcript_id").to_pylist()
                )
                self._transcript_ids.update(new_ids)
                exclude_array = pa.array(self._transcript_ids, type=pa.string())

                # Update progress
                total_rows += filtered_batch.num_rows
                progress.update(text=str(total_rows))

                # Estimate batch size
                batch_size = self._estimate_batch_size(filtered_batch)

                # Write if adding this batch would exceed target size
                if (
                    accumulated_size > 0
                    and accumulated_size + batch_size >= target_size_bytes
                ):
                    await self._write_arrow_batch(accumulated_batches)
                    accumulated_batches = []
                    accumulated_size = 0

                # Accumulate batch
                accumulated_batches.append(filtered_batch)
                accumulated_size += batch_size

            # Write remainder
            if accumulated_batches:
                await self._write_arrow_batch(accumulated_batches)

    def _register_shuffle_function(self, seed: int) -> None:
        """Register DuckDB UDF for deterministic shuffling.

        Args:
            seed: Random seed for shuffling.
        """
        assert self._conn is not None

        if self._current_shuffle_seed == seed:
            return

        def shuffle_hash(sample_id: str) -> str:
            """Compute deterministic hash for shuffling."""
            content = f"{sample_id}:{seed}"
            return hashlib.sha256(content.encode()).hexdigest()

        # Remove existing function if it exists
        try:
            self._conn.remove_function("shuffle_hash")
        except Exception:
            pass  # Function doesn't exist yet

        self._conn.create_function("shuffle_hash", shuffle_hash)
        self._current_shuffle_seed = seed

    def _build_where_clause(
        self, where: list[Condition] | None
    ) -> tuple[str, list[Any]]:
        """Build WHERE clause from conditions.

        Args:
            where: List of conditions to combine with AND.

        Returns:
            Tuple of (where_clause, parameters).
        """
        if not where:
            return "", []

        from functools import reduce

        condition = where[0] if len(where) == 1 else reduce(lambda a, b: a & b, where)
        where_sql, where_params = condition.to_sql("duckdb")
        return f" WHERE {where_sql}", where_params

    def _transcript_to_row(self, transcript: Transcript) -> dict[str, Any]:
        """Convert Transcript to Parquet row dict with flattened metadata.

        Args:
            transcript: Transcript to convert.

        Returns:
            Dict with Parquet column values.
        """
        # Validate metadata keys don't conflict with reserved names
        _validate_metadata_keys(transcript.metadata)

        # Serialize messages and events as JSON arrays
        messages_array = [msg.model_dump() for msg in transcript.messages]
        events_array = [event.model_dump() for event in transcript.events]

        # Start with reserved fields
        row: dict[str, Any] = {
            "transcript_id": transcript.transcript_id,
            "source_type": transcript.source_type,
            "source_id": transcript.source_id,
            "source_uri": transcript.source_uri,
            "messages": json.dumps(messages_array),
            "events": json.dumps(events_array),
        }

        # Flatten metadata: add each key as a column
        for key, value in transcript.metadata.items():
            if value is None:
                row[key] = None
            elif isinstance(value, (dict, list)):
                # Complex types: serialize to JSON string
                row[key] = json.dumps(value)
            elif isinstance(value, (str, int, float, bool)):
                # Scalar types: store directly
                row[key] = value
            else:
                # Unknown types: convert to string
                row[key] = str(value)

        return row

    def _estimate_row_size(self, row: dict[str, Any]) -> int:
        """Estimate size of serialized row in bytes.

        Note: Row values are already serialized by _transcript_to_row(),
        so complex types (dict/list) are JSON strings.

        Args:
            row: Row dict from _transcript_to_row().

        Returns:
            Estimated size in bytes (accounting for compression).
        """
        json_array_size = 0  # messages, events - compress very well
        other_size = 0  # metadata fields - compress modestly

        for key, value in row.items():
            if value is None:
                continue  # NULL values have minimal overhead
            elif isinstance(value, str):
                if key in ("messages", "events"):
                    json_array_size += len(value)
                else:
                    other_size += len(value)
            elif isinstance(value, bool):
                other_size += 1  # Boolean stored as 1 byte
            elif isinstance(value, (int, float)):
                other_size += 8  # 64-bit numeric types

        # JSON arrays (messages/events) compress extremely well (~25x with zstd)
        # Metadata fields compress more modestly (~5x)
        return int(json_array_size * 0.04 + other_size * 0.2)

    def _estimate_batch_size(self, batch: pa.RecordBatch) -> int:
        """Estimate size of Arrow batch in bytes.

        Estimates compressed size by applying different compression factors
        to JSON array columns (messages/events) vs other columns.

        Args:
            batch: PyArrow RecordBatch to estimate size for.

        Returns:
            Estimated size in bytes (accounting for compression).
        """
        json_array_size = 0
        other_size = 0

        for i, name in enumerate(batch.schema.names):
            col_size = batch.column(i).nbytes
            if name in ("messages", "events"):
                json_array_size += col_size
            else:
                other_size += col_size

        # JSON arrays (messages/events) compress extremely well (~25x with zstd)
        # Metadata fields compress more modestly (~5x)
        return int(json_array_size * 0.04 + other_size * 0.2)

    def _validate_record_batch_schema(self, schema: pa.Schema) -> None:
        """Validate that RecordBatch schema meets requirements.

        Requirements:
        - transcript_id column must exist and be string type
        - Optional columns (source_type, source_id, source_uri, messages, events)
          must be string type if present

        Args:
            schema: PyArrow schema to validate.

        Raises:
            ValueError: If schema doesn't meet requirements.
        """
        # Check transcript_id exists
        if "transcript_id" not in schema.names:
            raise ValueError("RecordBatch schema must contain 'transcript_id' column")

        # Check transcript_id is string type
        transcript_id_type = schema.field("transcript_id").type
        if transcript_id_type not in (pa.string(), pa.large_string()):
            raise ValueError(
                f"'transcript_id' column must be string type, got {transcript_id_type}"
            )

        # Check optional columns are string type if present
        optional_string_columns = [
            "source_type",
            "source_id",
            "source_uri",
            "messages",
            "events",
        ]
        for col in optional_string_columns:
            if col in schema.names:
                col_type = schema.field(col).type
                if col_type not in (pa.string(), pa.large_string()):
                    raise ValueError(
                        f"'{col}' column must be string type, got {col_type}"
                    )

    def _ensure_required_columns(self, table: pa.Table) -> pa.Table:
        """Add missing optional columns as null-filled string columns.

        Ensures all optional reserved columns exist in the table for
        schema consistency when writing Parquet files.

        Args:
            table: PyArrow table to normalize.

        Returns:
            Table with all optional columns present (null-filled if missing).
        """
        optional_columns = [
            "source_type",
            "source_id",
            "source_uri",
            "messages",
            "events",
        ]
        for col in optional_columns:
            if col not in table.column_names:
                null_array = pa.nulls(len(table), type=pa.string())
                table = table.append_column(col, null_array)
        return table

    def _get_available_content_columns(self, filename: str) -> set[str]:
        """Get available content columns for a file, with caching.

        Args:
            filename: Path to the Parquet file.

        Returns:
            Set of column names available in the file.
        """
        if filename not in self._file_columns_cache:
            assert self._conn is not None
            enc_config = self._read_parquet_encryption_config()
            schema_result = self._conn.execute(
                f"SELECT column_name FROM (DESCRIBE SELECT * FROM read_parquet(?{enc_config}))",
                [filename],
            ).fetchall()
            self._file_columns_cache[filename] = {row[0] for row in schema_result}
        return self._file_columns_cache[filename]

    def _write_parquet_file(self, table: pa.Table, path: str) -> None:
        """Write PyArrow table to Parquet file with standard settings.

        Args:
            table: PyArrow table to write.
            path: Destination file path.
        """
        pq.write_table(
            table,
            path,
            compression="zstd",
            use_dictionary=True,
            row_group_size=int(self._row_group_size_mb * 1024 * 1024),
            write_statistics=True,
        )

    async def _write_arrow_batch(self, batches: list[pa.RecordBatch]) -> None:
        """Write accumulated Arrow batches to a new Parquet file.

        Concatenates batches into a single table and writes with same
        compression settings as _write_parquet_batch.

        Args:
            batches: List of PyArrow RecordBatches to write.
        """
        if not batches:
            return

        with trace_action(logger, "Scout Parquet Write", "Writing Arrow batch"):
            # Concatenate batches into a single table
            table = pa.Table.from_batches(batches)

            # Ensure all required columns exist
            table = self._ensure_required_columns(table)

            # Generate filename
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
            file_uuid = uuid.uuid4().hex[:8]
            filename = f"transcripts_{timestamp}_{file_uuid}.parquet"

            # Determine output path and write Parquet file
            assert self._location is not None
            if self._location.startswith("s3://"):
                s3_path = f"{self._location.rstrip('/')}/{filename}"

                # For S3, write to temp file then upload
                with tempfile.NamedTemporaryFile(
                    suffix=".parquet", delete=False
                ) as tmp_file:
                    tmp_path = tmp_file.name

                try:
                    # Write to temporary file
                    self._write_parquet_file(table, tmp_path)

                    # Upload to S3
                    s3_path = f"{self._location.rstrip('/')}/{filename}"
                    assert self._fs is not None
                    await self._fs.write_file(s3_path, Path(tmp_path).read_bytes())
                finally:
                    # Clean up temp file
                    Path(tmp_path).unlink(missing_ok=True)
            else:
                # Local file system
                output_path = Path(self._location) / filename
                output_path.parent.mkdir(parents=True, exist_ok=True)

                self._write_parquet_file(table, output_path.as_posix())

    def _infer_schema(self, rows: list[dict[str, Any]]) -> pa.Schema:
        """Infer PyArrow schema from transcript rows.

        Reserved columns always come first with fixed types.
        Metadata columns are inferred from actual values.

        Args:
            rows: List of row dicts from _transcript_to_row().

        Returns:
            PyArrow schema for the Parquet file.
        """
        # Reserved columns with fixed types
        fields: list[tuple[str, pa.DataType]] = [
            ("transcript_id", pa.string()),
            ("source_type", pa.string()),
            ("source_id", pa.string()),
            ("source_uri", pa.string()),
            ("messages", pa.string()),
            ("events", pa.string()),
        ]

        # Discover all metadata keys across all rows
        metadata_keys: set[str] = set()
        for row in rows:
            metadata_keys.update(k for k in row.keys() if k not in RESERVED_COLUMNS)

        # Infer type for each metadata key (sorted for determinism)
        for key in sorted(metadata_keys):
            inferred_type = self._infer_column_type(key, rows)
            fields.append((key, inferred_type))

        return pa.schema(fields)

    def _infer_column_type(self, key: str, rows: list[dict[str, Any]]) -> pa.DataType:
        """Infer PyArrow type for a metadata column.

        Args:
            key: Column name to infer type for.
            rows: All rows to examine for type inference.

        Returns:
            PyArrow data type for the column.
        """
        # Collect non-null values for this key
        values = [row.get(key) for row in rows if row.get(key) is not None]

        if not values:
            return pa.string()  # All NULL → default to string

        # Determine types present
        types = {type(v) for v in values}

        # Infer appropriate PyArrow type
        if types == {str}:
            return pa.string()
        elif types == {bool}:
            return pa.bool_()
        elif types == {int}:
            return pa.int64()
        elif types == {float}:
            return pa.float64()
        elif types == {int, bool}:
            # bool is subclass of int
            return pa.int64()
        elif types <= {int, float, bool}:
            # Mix of numeric types → use float
            return pa.float64()
        else:
            # Mixed incompatible types → use string
            return pa.string()

    async def _write_parquet_batch(self, batch: list[dict[str, Any]]) -> None:
        """Write a batch of pre-serialized rows to a new Parquet file.

        Args:
            batch: List of row dicts (already serialized by _transcript_to_row).
        """
        if not batch:
            return

        with trace_action(logger, "Scout Parquet Write", "Writing transcripts batch"):
            # Infer schema from actual data
            schema = self._infer_schema(batch)

            # Create DataFrame and convert to PyArrow table
            df = pd.DataFrame(batch)
            table = pa.Table.from_pandas(df, schema=schema)

            # Generate filename
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
            file_uuid = uuid.uuid4().hex[:8]
            filename = f"transcripts_{timestamp}_{file_uuid}.parquet"

            # Determine output path and write Parquet file
            assert self._location is not None
            if self._location.startswith("s3://"):
                s3_path = f"{self._location.rstrip('/')}/{filename}"

                # For S3, write to temp file then upload
                with tempfile.NamedTemporaryFile(
                    suffix=".parquet", delete=False
                ) as tmp_file:
                    tmp_path = tmp_file.name

                try:
                    # Write to temporary file
                    self._write_parquet_file(table, tmp_path)

                    # Upload to S3
                    s3_path = f"{self._location.rstrip('/')}/{filename}"
                    assert self._fs is not None
                    await self._fs.write_file(s3_path, Path(tmp_path).read_bytes())
                finally:
                    # Clean up temp file
                    Path(tmp_path).unlink(missing_ok=True)
            else:
                # Local file system
                output_path = Path(self._location) / filename
                output_path.parent.mkdir(parents=True, exist_ok=True)

                self._write_parquet_file(table, output_path.as_posix())

    async def _create_transcripts_table(self) -> None:
        """Create or refresh DuckDB structures for querying transcripts.

        Creates two structures:
        1. transcript_index: Small table with transcript_id → filename mapping (for fast read())
        2. transcripts: VIEW over Parquet files for metadata queries (for select()/count())

        This enables:
        1. Fast indexed lookups on transcript_id for read() via index table
        2. Low memory usage (only transcript_id + filename in memory)
        3. Efficient metadata queries via VIEW with Parquet predicate pushdown
        4. Targeted file access for content reads (via filename in index table)
        """
        assert self._conn is not None

        with trace_action(logger, "Scout Parquet Index", f"Indexing {self._location}"):
            # Drop existing structures
            self._conn.execute("DROP TABLE IF EXISTS transcript_index")
            self._conn.execute("DROP VIEW IF EXISTS transcripts")

            # Get file paths - either from snapshot or by discovering parquet files
            if self._snapshot and self._snapshot.transcript_ids:
                # Fast path: extract filenames from snapshot (no crawl needed)
                file_paths = sorted(
                    {f for f in self._snapshot.transcript_ids.values() if f is not None}
                )
            else:
                # Standard path: discover parquet files
                file_paths = await self._discover_parquet_files()

            # Handle empty case
            if not file_paths:
                self._create_empty_structures()
                return

            # Setup encryption if needed
            self._setup_encryption(file_paths)

            # Build pattern for read_parquet
            pattern = self._build_parquet_pattern(file_paths)
            self._parquet_pattern = pattern

            # Infer exclude clause from first file
            self._exclude_clause = self._infer_exclude_clause(file_paths[0])

            # Create index table
            if self._snapshot and self._snapshot.transcript_ids:
                # Fast path: create directly from snapshot data
                self._create_index_from_snapshot()
            else:
                # Standard path: query parquet files
                self._create_index_from_parquet(pattern)

            # Create index on transcript_id for fast lookups
            self._conn.execute(
                "CREATE INDEX idx_transcript_id ON transcript_index(transcript_id)"
            )

            # Create VIEW for metadata queries
            self._create_transcripts_view(pattern)

    def _create_empty_structures(self) -> None:
        """Create empty transcript_index table and transcripts VIEW."""
        assert self._conn is not None
        self._conn.execute("""
            CREATE TABLE transcript_index AS
            SELECT ''::VARCHAR AS transcript_id, ''::VARCHAR AS filename
            WHERE FALSE
        """)
        self._conn.execute("""
            CREATE VIEW transcripts AS
            SELECT
                ''::VARCHAR AS transcript_id,
                ''::VARCHAR AS source_type,
                ''::VARCHAR AS source_id,
                ''::VARCHAR AS source_uri,
                ''::VARCHAR AS filename
            WHERE FALSE
        """)

    def _setup_encryption(self, file_paths: list[str]) -> None:
        """Detect and configure encryption if needed."""
        assert self._conn is not None

        # Check encryption status (validates no mixed encrypted/unencrypted)
        self._is_encrypted = self._check_encryption_status(file_paths)

        if self._is_encrypted:
            key = get_encryption_key_from_env()
            if not key:
                raise PrerequisiteError(
                    f"Encrypted database detected but no encryption key provided. "
                    f"Set the {ENCRYPTION_KEY_ENV} environment variable."
                )
            try:
                validate_encryption_key(key)
            except ValueError as e:
                raise PrerequisiteError(str(e)) from e
            self._conn.execute(
                f"PRAGMA add_parquet_key('{ENCRYPTION_KEY_NAME}', '{key}')"
            )

    def _build_parquet_pattern(self, file_paths: list[str]) -> str:
        """Build DuckDB pattern string for read_parquet."""
        if len(file_paths) == 1:
            return f"'{file_paths[0]}'"
        else:
            return "[" + ", ".join(f"'{p}'" for p in file_paths) + "]"

    def _create_index_from_snapshot(self) -> None:
        """Create transcript_index table directly from snapshot data."""
        assert self._conn is not None
        assert self._snapshot is not None

        ids = list(self._snapshot.transcript_ids.keys())
        filenames = [self._snapshot.transcript_ids[tid] for tid in ids]
        arrow_table = pa.table({"transcript_id": ids, "filename": filenames})
        self._conn.register("snapshot_data", arrow_table)
        self._conn.execute("""
            CREATE TABLE transcript_index AS
            SELECT * FROM snapshot_data
        """)
        self._conn.unregister("snapshot_data")

    def _create_index_from_parquet(self, pattern: str) -> None:
        """Create transcript_index table by querying parquet files."""
        assert self._conn is not None

        enc_config = self._read_parquet_encryption_config()
        index_sql = f"""
            CREATE TABLE transcript_index AS
            SELECT transcript_id, filename
            FROM read_parquet({pattern}, union_by_name=true, filename=true{enc_config})
        """
        params: list[Any] = []

        # Apply pre-filter query if provided
        if self._query:
            # Apply WHERE conditions
            if self._query.where:
                where_clause, where_params = self._build_where_clause(self._query.where)
                index_sql += where_clause
                params.extend(where_params)

            # Apply SHUFFLE (register UDF first)
            if self._query.shuffle:
                seed = 0 if self._query.shuffle is True else self._query.shuffle
                self._register_shuffle_function(seed)
                index_sql += " ORDER BY shuffle_hash(transcript_id)"

            # Apply LIMIT
            if self._query.limit:
                index_sql += " LIMIT ?"
                params.append(self._query.limit)

        self._conn.execute(index_sql, params)

    def _infer_exclude_clause(self, file_path: str) -> str:
        """Infer EXCLUDE clause from a single file's schema.

        Reads schema from one file (fast - only reads Parquet footer metadata)
        to determine which content columns to exclude.

        Args:
            file_path: Path to a Parquet file to sample.

        Returns:
            EXCLUDE clause string (e.g., " EXCLUDE (messages, events)") or empty string.
        """
        assert self._conn is not None

        enc_config = self._read_parquet_encryption_config()
        schema_result = self._conn.execute(
            f"SELECT column_name FROM (DESCRIBE SELECT * FROM read_parquet('{file_path}'{enc_config}))"
        ).fetchall()
        existing_columns = {row[0] for row in schema_result}
        exclude_columns = [
            col for col in ["messages", "events"] if col in existing_columns
        ]

        if exclude_columns:
            return f" EXCLUDE ({', '.join(exclude_columns)})"
        return ""

    def _infer_exclude_clause_full(self, pattern: str) -> str:
        """Infer EXCLUDE clause by scanning all files' schemas.

        Slower fallback that unions schemas from all files to handle
        cases where schema differs across files.

        Args:
            pattern: DuckDB file pattern for read_parquet.

        Returns:
            EXCLUDE clause string or empty string.
        """
        assert self._conn is not None

        enc_config = self._read_parquet_encryption_config()
        schema_result = self._conn.execute(
            f"SELECT column_name FROM (DESCRIBE SELECT * FROM read_parquet({pattern}, union_by_name=true{enc_config}))"
        ).fetchall()
        existing_columns = {row[0] for row in schema_result}
        exclude_columns = [
            col for col in ["messages", "events"] if col in existing_columns
        ]

        if exclude_columns:
            return f" EXCLUDE ({', '.join(exclude_columns)})"
        return ""

    def _create_transcripts_view(self, pattern: str) -> None:
        """Create the transcripts VIEW with appropriate EXCLUDE clause.

        Tries with exclude clause inferred from first file. If that fails
        (schema differs across files), falls back to full schema scan.

        Args:
            pattern: DuckDB file pattern for read_parquet.
        """
        assert self._conn is not None

        enc_config = self._read_parquet_encryption_config()

        # Build VIEW SQL based on whether pre-filter was applied
        def build_view_sql(exclude_clause: str) -> str:
            if self._snapshot or (
                self._query
                and (self._query.where or self._query.shuffle or self._query.limit)
            ):
                # VIEW joins with pre-filtered index table
                return f"""
                    CREATE VIEW transcripts AS
                    SELECT p.*{exclude_clause}
                    FROM read_parquet({pattern}, union_by_name=true, filename=true{enc_config}) p
                    INNER JOIN transcript_index i ON p.transcript_id = i.transcript_id
                """
            else:
                # No pre-filter - VIEW directly queries Parquet
                return f"""
                    CREATE VIEW transcripts AS
                    SELECT *{exclude_clause}
                    FROM read_parquet({pattern}, union_by_name=true, filename=true{enc_config})
                """

        # Try with exclude clause from first file (fast path)
        try:
            self._conn.execute(build_view_sql(self._exclude_clause))
        except duckdb.BinderException:
            # Schema differs across files - fall back to full scan
            self._exclude_clause = self._infer_exclude_clause_full(pattern)
            self._conn.execute(build_view_sql(self._exclude_clause))

    async def _discover_parquet_files(self) -> list[str]:
        """Discover all Parquet files in location.

        Returns:
            List of file paths (local or S3 URIs).
        """
        assert self._location is not None
        if self._is_s3() or self._is_hf():
            assert self._fs is not None
            assert self._cache is not None

            # List all files recursively (returns list of FileInfo objects)
            fs = filesystem(self._location)
            all_files = fs.ls(self._location, recursive=True)
            # Filter for transcript parquet files
            files = []
            for f in all_files:
                name = f.name
                if name.endswith(".parquet"):
                    files.append(name)

            # no caching for now (downoads block initial startup and aggregate
            # gain seems minimal)
            return files

            # Try to cache files, but if cache is full, use S3 URIs directly
            # file_paths = []
            # for file_uri in files:
            #     cached_path = await self._cache.resolve_remote_uri_to_local(
            #         self._fs, file_uri
            #     )
            #     # If caching failed (exceeded 5GB), cached_path == file_uri
            #     file_paths.append(cached_path)

            # return file_paths
        else:
            location_path = Path(self._location)
            if not location_path.exists():
                location_path.mkdir(parents=True, exist_ok=True)
                return []

            # Recursively discover all transcript parquet files
            return list(
                glob.glob(
                    str(location_path / "**" / PARQUET_TRANSCRIPTS_GLOB), recursive=True
                )
            )

    def _check_encryption_status(self, file_paths: list[str]) -> bool:
        """Check if database files are encrypted and validate consistency.

        Args:
            file_paths: List of parquet file paths.

        Returns:
            True if all files are encrypted, False if all unencrypted.

        Raises:
            ValueError: If database contains a mix of encrypted and unencrypted files.
        """
        encrypted_count = sum(1 for f in file_paths if f.endswith(".enc.parquet"))
        unencrypted_count = len(file_paths) - encrypted_count

        if encrypted_count > 0 and unencrypted_count > 0:
            raise ValueError(
                f"Database contains mixed encrypted ({encrypted_count}) and "
                f"unencrypted ({unencrypted_count}) parquet files. "
                "All files must be either encrypted or unencrypted."
            )

        return encrypted_count > 0

    def _read_parquet_encryption_config(self) -> str:
        """Get encryption config string for read_parquet calls.

        Returns:
            Empty string if not encrypted, or encryption config parameter.
        """
        if self._is_encrypted:
            return f", encryption_config={{footer_key: '{ENCRYPTION_KEY_NAME}'}}"
        return ""

    def _have_transcript(self, transcript_id: str) -> bool:
        return transcript_id in (self._transcript_ids or set())

    def _as_async_iterator(
        self,
        transcripts: Iterable[Transcript]
        | AsyncIterable[Transcript]
        | Transcripts
        | TranscriptsSource,
    ) -> AsyncIterator[Transcript]:
        """Convert various transcript sources to async iterator.

        Args:
            transcripts: Transcripts from various sources (iterable, async iterable,
                Transcripts object, or TranscriptsSource callable).

        Returns:
            AsyncIterator over transcripts, filtered to exclude already-present transcripts.
        """
        # Transcripts - read them fully using reader
        if isinstance(transcripts, Transcripts):

            async def _iter() -> AsyncIterator[Transcript]:
                async with transcripts.reader() as tr:
                    async for t in tr.index():
                        if not self._have_transcript(t.transcript_id):
                            yield await tr.read(
                                t,
                                content=TranscriptContent(messages="all", events="all"),
                            )

            return _iter()

        # AsyncIterable - iterate with async for
        elif isinstance(transcripts, AsyncIterable):

            async def _iter() -> AsyncIterator[Transcript]:
                async for transcript in transcripts:
                    if not self._have_transcript(transcript.transcript_id):
                        yield transcript

            return _iter()

        # Regular iterable (not callable) - wrap in async generator
        elif not callable(transcripts):

            async def _iter() -> AsyncIterator[Transcript]:
                for transcript in transcripts:
                    if not self._have_transcript(transcript.transcript_id):
                        yield transcript

            return _iter()

        # TranscriptsSource (callable) - call it to get AsyncIterator
        else:

            async def _iter() -> AsyncIterator[Transcript]:
                async for transcript in transcripts():
                    if not self._have_transcript(transcript.transcript_id):
                        yield transcript

            return _iter()

    def _is_s3(self) -> bool:
        return self._location is not None and self._location.startswith("s3://")

    def _init_s3_auth(self) -> None:
        assert self._conn is not None
        self._conn.execute("""
            CREATE SECRET (
                TYPE S3,
                PROVIDER credential_chain
            )
        """)

    def _is_hf(self) -> bool:
        return self._location is not None and self._location.startswith("hf://")

    def _init_hf_auth(self) -> None:
        assert self._conn is not None
        hf_token = os.environ.get("HF_TOKEN", None)
        if hf_token:
            self._conn.execute(f"""
                CREATE SECRET hf_token (
                    TYPE huggingface,
                    TOKEN '{hf_token}'
                )
            """)
        else:
            self._conn.execute("""
                CREATE SECRET hf_token (
                    TYPE huggingface,
                    PROVIDER credential_chain
                )
            """)


class ParquetTranscripts(Transcripts):
    """Collection of transcripts stored in Parquet files.

    Provides efficient querying of transcript metadata using DuckDB,
    with content loaded on-demand from JSON strings stored in Parquet.
    """

    def __init__(
        self,
        location: str,
    ) -> None:
        """Initialize Parquet transcript collection.

        Args:
            location: Directory path (local or S3) containing Parquet files.
            memory_limit: DuckDB memory limit (e.g., '4GB', '8GB').
        """
        super().__init__()
        self._location = location
        self._db: ParquetTranscriptsDB | None = None

        # ensure any filesystem depenencies
        ensure_filesystem_dependencies(location)

    @override
    def reader(self, snapshot: ScanTranscripts | None = None) -> TranscriptsReader:
        """Read the selected transcripts.

        Args:
            snapshot: An optional snapshot which provides hints to make the
                reader more efficient (e.g. by preventing a full scan to find
                transcript_id => filename mappings)
        """
        db = ParquetTranscriptsDB(self._location, query=self._query, snapshot=snapshot)
        return TranscriptsDBReader(db)

    @staticmethod
    @override
    def from_snapshot(snapshot: ScanTranscripts) -> Transcripts:
        """Restore transcripts from a snapshot."""
        return transcripts_from_db_snapshot(snapshot)


def _validate_metadata_keys(metadata: dict[str, Any]) -> None:
    """Ensure metadata doesn't use reserved column names.

    Args:
        metadata: Metadata dict to validate.

    Raises:
        ValueError: If metadata contains reserved column names.
    """
    conflicts = RESERVED_COLUMNS & metadata.keys()
    if conflicts:
        raise ValueError(
            f"Metadata keys conflict with reserved column names: {sorted(conflicts)}"
        )
