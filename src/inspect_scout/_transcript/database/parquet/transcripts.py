"""DuckDB/Parquet-backed transcript database implementation."""

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
from upath import UPath

from inspect_scout._display._display import display
from inspect_scout._scanspec import ScanTranscripts
from inspect_scout._transcript.database.factory import transcripts_from_db_snapshot
from inspect_scout._transcript.types import RESERVED_COLUMNS
from inspect_scout._transcript.util import LazyJSONDict
from inspect_scout._util.filesystem import ensure_filesystem_dependencies

from ...._query import Query
from ...._query.sql import SQLDialect
from ...json.load_filtered import load_filtered_transcript
from ...transcripts import (
    Transcripts,
    TranscriptsReader,
)
from ...types import Transcript, TranscriptContent, TranscriptInfo
from ..database import TranscriptsDB
from ..reader import TranscriptsViewReader
from .encryption import (
    ENCRYPTION_KEY_ENV,
    ENCRYPTION_KEY_NAME,
    get_encryption_key_from_env,
    validate_encryption_key,
)
from .index import (
    _discover_index_files,
    append_index,
    compact_index,
    create_index,
    init_index_table,
)
from .migration import migrate_view
from .types import IndexStorage

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
        query: Query | None = None,
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
        self._location = location
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

        # State (initialized in connect)
        self._conn: duckdb.DuckDBPyConnection | None = None
        self._fs: AsyncFilesystem | None = None
        self._index_storage: IndexStorage | None = None
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

            # Disable progress bar (shows up during S3/HTTP operations)
            self._conn.execute("SET enable_progress_bar=false")

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

        # Initialize index storage for index operations
        self._index_storage = await IndexStorage.create(
            location=self._location,
            fs=self._fs,
            key=get_encryption_key_from_env(),
        )

        # Discover and register Parquet files
        await self._create_transcripts_table()

    @override
    async def disconnect(self) -> None:
        """Close DuckDB connection and cleanup resources."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

        if self._fs is not None:
            await self._fs.close()
            self._fs = None

    @override
    async def insert(
        self,
        transcripts: Iterable[Transcript]
        | AsyncIterable[Transcript]
        | Transcripts
        | pa.RecordBatchReader,
    ) -> None:
        """Insert transcripts, writing one Parquet file per batch.

        Transcript ids that are already in the database are not inserted.
        Each batch write also creates a corresponding index file. After all
        inserts complete, index files are compacted.

        Args:
            transcripts: Transcripts to insert (iterable, async iterable, source,
                or PyArrow RecordBatchReader for efficient Arrow-native insertion).
        """
        assert self._conn is not None
        assert self._index_storage is not None

        # if we don't yet have a list of transcript ids then query for one
        if len(self._transcript_ids) == 0:
            cursor = self._conn.execute("SELECT transcript_id FROM transcript_index")
            column_names = [desc[0] for desc in cursor.description]
            for cursor_row in cursor.fetchall():
                row_dict = dict(zip(column_names, cursor_row, strict=True))
                self._transcript_ids.add(row_dict["transcript_id"])

        # Check if index exists - if not but data exists, build index first
        idx_files = await _discover_index_files(self._index_storage)
        if not idx_files and len(self._transcript_ids) > 0:
            # Existing data but no index - build index from existing parquet files
            await create_index(self._conn, self._index_storage)

        # two insert codepaths, one for arrow batch, one for transcripts
        if isinstance(transcripts, pa.RecordBatchReader):
            await self._insert_from_record_batch_reader(transcripts)
        else:
            await self._insert_from_transcripts(transcripts)

        # refresh the view
        await self._create_transcripts_table()

        # Best-effort compaction - merge index files
        try:
            await compact_index(self._conn, self._index_storage)
        except Exception as e:
            logger.warning(f"Index compaction failed (data is consistent): {e}")

    @override
    async def select(self, query: Query | None = None) -> AsyncIterator[TranscriptInfo]:
        """Query transcripts matching query.

        Args:
            query: Query with where/limit/shuffle/order_by criteria.

        Yields:
            TranscriptInfo instances (metadata only, no content).
        """
        assert self._conn is not None
        query = query or Query()

        # Merge order_by from init query if not in runtime query
        effective_query = query
        if not query.order_by and self._query and self._query.order_by:
            effective_query = Query(
                where=query.where,
                limit=query.limit,
                shuffle=query.shuffle,
                order_by=self._query.order_by,
            )

        # Build SQL suffix using Query
        suffix, params, register_shuffle = effective_query.to_sql_suffix(
            SQLDialect.DUCKDB, shuffle_column="transcript_id"
        )
        if register_shuffle:
            register_shuffle(self._conn)

        # Note: transcripts table already excludes messages/events, so just SELECT *
        sql = f"SELECT * FROM transcripts{suffix}"

        # Execute query and fetch all results immediately.
        # IMPORTANT: We must fetchall() before yielding because DuckDB cursors are
        # invalidated when other queries are executed on the same connection. Since
        # callers may execute read() queries between yields, we need to materialize
        # results upfront. This is safe because we're only fetching metadata (not
        # messages/events content), which has a small memory footprint per row.
        cursor = self._conn.execute(sql, params)
        column_names = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        for row in rows:
            row_dict = dict(zip(column_names, row, strict=True))

            # Extract reserved fields (optional fields use .get() for missing columns)
            transcript_id = row_dict["transcript_id"]
            transcript_source_type = row_dict.get("source_type")
            transcript_source_id = row_dict.get("source_id")
            transcript_source_uri = row_dict.get("source_uri")
            transcript_filename = row_dict["filename"]
            transcript_date = row_dict.get("date")
            transcript_task_set = row_dict.get("task_set")
            transcript_task_id = row_dict.get("task_id")
            transcript_task_repeat = row_dict.get("task_repeat")
            transcript_agent = row_dict.get("agent")
            transcript_agent_args = row_dict.get("agent_args")
            transcript_model = row_dict.get("model")
            transcript_model_options = row_dict.get("model_options")
            transcript_score = row_dict.get("score")
            transcript_success = row_dict.get("success")
            transcript_total_time = row_dict.get("total_time")
            transcript_total_tokens = row_dict.get("total_tokens")
            transcript_error = row_dict.get("error")
            transcript_limit = row_dict.get("limit")

            # resolve json
            if transcript_agent_args is not None:
                transcript_agent_args = json.loads(transcript_agent_args)
            if transcript_model_options is not None:
                transcript_model_options = json.loads(transcript_model_options)
            if isinstance(transcript_score, str) and (
                transcript_score.startswith("{") or transcript_score.startswith("[")
            ):
                transcript_score = json.loads(transcript_score)

            # Reconstruct metadata from all non-reserved columns
            # Use LazyJSONDict to defer JSON parsing until values are accessed
            metadata_dict = {
                col: value
                for col, value in row_dict.items()
                if col not in RESERVED_COLUMNS and value is not None
            }
            lazy_metadata = LazyJSONDict(metadata_dict)

            # Use normal constructor for type validation/coercion, then inject
            # LazyJSONDict for metadata for lazy parsing behavior
            info = ParquetTranscriptInfo(
                transcript_id=transcript_id,
                source_type=transcript_source_type,
                source_id=transcript_source_id,
                source_uri=transcript_source_uri,
                date=transcript_date,
                task_set=transcript_task_set,
                task_id=transcript_task_id,
                task_repeat=transcript_task_repeat,
                agent=transcript_agent,
                agent_args=transcript_agent_args,
                model=transcript_model,
                model_options=transcript_model_options,
                score=transcript_score,
                success=transcript_success,
                total_time=transcript_total_time,
                total_tokens=transcript_total_tokens,
                error=transcript_error,
                limit=transcript_limit,
                metadata={},
                filename=transcript_filename,
            )
            object.__setattr__(info, "metadata", lazy_metadata)
            yield info

    @override
    async def count(self, query: Query | None = None) -> int:
        assert self._conn is not None
        query = query or Query()
        # For count, only WHERE matters (ignore limit/shuffle/order_by)
        count_query = Query(where=query.where)
        suffix, params, _ = count_query.to_sql_suffix(SQLDialect.DUCKDB)
        sql = f"SELECT COUNT(*) FROM transcripts{suffix}"
        result = self._conn.execute(sql, params).fetchone()
        assert result is not None
        return int(result[0])

    @override
    async def transcript_ids(self, query: Query | None = None) -> dict[str, str | None]:
        """Get transcript IDs matching query.

        Optimized implementation that queries directly from the index table
        when no WHERE conditions are specified, avoiding Parquet file access.

        Args:
            query: Query with where/limit/shuffle/order_by criteria.

        Returns:
            Dict of transcript IDs and parquet filenames
        """
        assert self._conn is not None
        query = query or Query()

        if not query.where:
            # No conditions - query index table directly (faster, in-memory)
            # Build a query for the index table (only shuffle/limit/order_by matter)
            index_query = Query(
                limit=query.limit,
                shuffle=query.shuffle,
                order_by=query.order_by,
            )
            suffix, params, register_shuffle = index_query.to_sql_suffix(
                SQLDialect.DUCKDB, shuffle_column="transcript_id"
            )
            if register_shuffle:
                register_shuffle(self._conn)

            sql = f"SELECT transcript_id, filename FROM transcript_index{suffix}"
            result = self._conn.execute(sql, params).fetchall()
            return {row[0]: row[1] for row in result}
        else:
            # Has conditions - need to query VIEW for metadata filtering
            transcript_ids: dict[str, str | None] = {}
            async for info in self.select(query):
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

        def transcript_no_content() -> Transcript:
            return Transcript.model_construct(
                transcript_id=t.transcript_id,
                source_type=t.source_type,
                source_id=t.source_id,
                source_uri=t.source_uri,
                date=t.date,
                task_set=t.task_set,
                task_id=t.task_id,
                task_repeat=t.task_repeat,
                agent=t.agent,
                agent_args=t.agent_args,
                model=t.model,
                model_options=t.model_options,
                score=t.score,
                success=t.success,
                total_time=t.total_time,
                total_tokens=t.total_tokens,
                error=t.error,
                limit=t.limit,
                metadata=t.metadata,
            )

        with trace_action(
            logger, "Scout Parquet Read", f"Reading from {t.transcript_id}"
        ):
            # Determine which columns we need to read
            need_messages = content.messages is not None
            need_events = content.events is not None

            if not need_messages and not need_events:
                # No content needed - use model_construct to preserve LazyJSONDict
                return transcript_no_content()

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
                return transcript_no_content()

            # Now read content from just that specific file (targeted I/O)
            # This avoids scanning all files - only reads from the one file containing this transcript
            # The index stores relative filenames, so we need to construct the full path
            relative_filename = filename_result[0]
            full_path = self._full_parquet_path(relative_filename)

            # Try optimistic read first (fast path for files with all columns)
            enc_config = self._read_parquet_encryption_config()
            try:
                sql = f"SELECT {', '.join(columns)} FROM read_parquet(?, union_by_name=true{enc_config}) WHERE transcript_id = ?"
                result = self._conn.execute(
                    sql, [full_path, t.transcript_id]
                ).fetchone()
                columns_read = columns  # All requested columns were available
            except duckdb.BinderException:
                # Column doesn't exist - check which ones are available (cached)
                available = self._get_available_content_columns(full_path)
                columns_read = [c for c in columns if c in available]

                if not columns_read:
                    # No content columns available - return empty content
                    return transcript_no_content()

                # Retry with only available columns
                sql = f"SELECT {', '.join(columns_read)} FROM read_parquet(?, union_by_name=true{enc_config}) WHERE transcript_id = ?"
                result = self._conn.execute(
                    sql, [full_path, t.transcript_id]
                ).fetchone()

            if not result:
                # Transcript not found - use model_construct to preserve LazyJSONDict
                return transcript_no_content()

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
        transcripts: Iterable[Transcript] | AsyncIterable[Transcript] | Transcripts,
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
            "date": transcript.date,
            "task_set": transcript.task_set,
            "task_id": transcript.task_id,
            "task_repeat": transcript.task_repeat,
            "agent": transcript.agent,
            "agent_args": json.dumps(transcript.agent_args)
            if transcript.agent_args is not None
            else None,
            "model": transcript.model,
            "model_options": json.dumps(transcript.model_options)
            if transcript.model_options is not None
            else None,
            "score": (
                json.dumps(transcript.score)
                if isinstance(transcript.score, (dict, list))
                else (str(transcript.score) if transcript.score is not None else None)
            ),
            "success": transcript.success,
            "total_time": transcript.total_time,
            "total_tokens": transcript.total_tokens,
            "error": transcript.error,
            "limit": transcript.limit,
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

        # Check optional string columns
        optional_string_columns = [
            "source_type",
            "source_id",
            "source_uri",
            "date",
            "task_set",
            "task_id",
            "agent",
            "agent_args",
            "model",
            "model_options",
            "score",
            "error",
            "limit",
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

        # Check optional bool/numeric columns
        if "success" in schema.names:
            col_type = schema.field("success").type
            if col_type != pa.bool_():
                raise ValueError(f"'success' column must be bool type, got {col_type}")

        if "total_time" in schema.names:
            col_type = schema.field("total_time").type
            if not pa.types.is_floating(col_type):
                raise ValueError(
                    f"'total_time' column must be float type, got {col_type}"
                )

        optional_int_columns = ["task_repeat", "total_tokens"]
        for col in optional_int_columns:
            if col in schema.names:
                col_type = schema.field(col).type
                if not pa.types.is_integer(col_type):
                    raise ValueError(
                        f"'{col}' column must be integer type, got {col_type}"
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
        optional_string_columns = [
            "source_type",
            "source_id",
            "source_uri",
            "date",
            "task_set",
            "task_id",
            "agent",
            "agent_args",
            "model",
            "model_options",
            "error",
            "limit",
            "messages",
            "events",
        ]
        for col in optional_string_columns:
            if col not in table.column_names:
                null_array = pa.nulls(len(table), type=pa.string())
                table = table.append_column(col, null_array)

        # Optional bool/numeric columns
        if "success" not in table.column_names:
            table = table.append_column(
                "success", pa.nulls(len(table), type=pa.bool_())
            )
        if "total_time" not in table.column_names:
            table = table.append_column(
                "total_time", pa.nulls(len(table), type=pa.float64())
            )
        if "task_repeat" not in table.column_names:
            table = table.append_column(
                "task_repeat", pa.nulls(len(table), type=pa.int64())
            )
        if "total_tokens" not in table.column_names:
            table = table.append_column(
                "total_tokens", pa.nulls(len(table), type=pa.int64())
            )

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
        """Write accumulated Arrow batches to a new Parquet file and index.

        Concatenates batches into a single table and writes with same
        compression settings as _write_parquet_batch. Also writes corresponding
        index file. If index write fails, the parquet file is deleted.

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
            parquet_path: str
            if self._location.startswith("s3://"):
                parquet_path = f"{self._location.rstrip('/')}/{filename}"

                # For S3, write to temp file then upload
                with tempfile.NamedTemporaryFile(
                    suffix=".parquet", delete=False
                ) as tmp_file:
                    tmp_path = tmp_file.name

                try:
                    # Write to temporary file
                    self._write_parquet_file(table, tmp_path)

                    # Upload to S3
                    assert self._fs is not None
                    await self._fs.write_file(parquet_path, Path(tmp_path).read_bytes())
                finally:
                    # Clean up temp file
                    Path(tmp_path).unlink(missing_ok=True)
            else:
                # Local file system
                output_path = Path(self._location) / filename
                output_path.parent.mkdir(parents=True, exist_ok=True)
                parquet_path = output_path.as_posix()

                self._write_parquet_file(table, parquet_path)

            # Write index file for this batch
            await self._write_index_for_batch(table, parquet_path, filename)

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
            ("date", pa.string()),
            ("task_set", pa.string()),
            ("task_id", pa.string()),
            ("task_repeat", pa.int64()),
            ("agent", pa.string()),
            ("agent_args", pa.string()),
            ("model", pa.string()),
            ("model_options", pa.string()),
            ("score", pa.string()),
            ("success", pa.bool_()),
            ("total_time", pa.float64()),
            ("total_tokens", pa.int64()),
            ("error", pa.string()),
            ("limit", pa.string()),
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
        """Write a batch of pre-serialized rows to a new Parquet file and index.

        Writes parquet data file first, then writes corresponding index file.
        If index write fails, the parquet file is deleted and the error is raised.

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
            parquet_path: str
            if self._location.startswith("s3://"):
                parquet_path = f"{self._location.rstrip('/')}/{filename}"

                # For S3, write to temp file then upload
                with tempfile.NamedTemporaryFile(
                    suffix=".parquet", delete=False
                ) as tmp_file:
                    tmp_path = tmp_file.name

                try:
                    # Write to temporary file
                    self._write_parquet_file(table, tmp_path)

                    # Upload to S3
                    assert self._fs is not None
                    await self._fs.write_file(parquet_path, Path(tmp_path).read_bytes())
                finally:
                    # Clean up temp file
                    Path(tmp_path).unlink(missing_ok=True)
            else:
                # Local file system
                output_path = Path(self._location) / filename
                output_path.parent.mkdir(parents=True, exist_ok=True)
                parquet_path = output_path.as_posix()

                self._write_parquet_file(table, parquet_path)

            # Write index file for this batch
            await self._write_index_for_batch(table, parquet_path, filename)

    async def _create_transcripts_table(self) -> None:
        """Create DuckDB structures for querying transcripts.

        Creates:
        - transcript_index TABLE: For filename lookups in read()
        - transcripts TABLE or VIEW: For metadata queries in select()/count()

        The implementation depends on whether index files exist:
        - With index: Creates TABLEs from index files (fast, in-memory)
        - Without index: Creates VIEW over parquet files (lazy, memory-efficient)

        Query methods always use `transcripts` and don't need to know the difference.
        """
        assert self._conn is not None

        with trace_action(logger, "Scout Parquet Index", f"Indexing {self._location}"):
            # Drop existing structures
            # DuckDB is type-strict: DROP TABLE IF EXISTS fails on VIEW and vice versa
            # Use try/except to handle both cases
            self._conn.execute("DROP TABLE IF EXISTS transcript_index")
            try:
                self._conn.execute("DROP TABLE IF EXISTS transcripts")
            except duckdb.CatalogException:
                pass
            try:
                self._conn.execute("DROP VIEW IF EXISTS transcripts")
            except duckdb.CatalogException:
                pass

            # Decision point: use index files if available, otherwise scan parquet
            idx_files: list[str] = []
            if self._index_storage is not None:
                idx_files = await _discover_index_files(self._index_storage)

            if idx_files:
                await self._init_from_index()
            else:
                await self._init_from_parquet()

    async def _init_from_index(self) -> None:
        """Initialize from index files (fast path).

        Creates:
        - transcript_index TABLE with all metadata from index files
        - transcripts TABLE (copy of transcript_index for uniform query interface)

        This is the fast path used when index files exist. All metadata is loaded
        into memory for fast queries.
        """
        assert self._conn is not None
        assert self._index_storage is not None

        # Load index files into transcript_index table
        row_count = await init_index_table(self._conn, self._index_storage)

        if row_count == 0:
            self._create_empty_structures()
            return

        # Create index for fast lookups
        self._conn.execute(
            "CREATE INDEX idx_transcript_id ON transcript_index(transcript_id)"
        )

        # Create transcripts TABLE as copy of transcript_index
        # This provides uniform query interface (both paths create 'transcripts')
        self._conn.execute("""
            CREATE TABLE transcripts AS SELECT * FROM transcript_index
        """)

        # Apply pre-filter query if provided (rare case)
        if self._query and (
            self._query.where or self._query.shuffle or self._query.limit
        ):
            self._apply_query_filter_to_tables()

    async def _init_from_parquet(self) -> None:
        """Initialize from parquet files (legacy/slow path).

        Creates:
        - transcript_index TABLE with (transcript_id, filename) for read() lookups
        - transcripts VIEW over parquet for memory-efficient metadata queries

        This is the legacy path used when no index files exist. It's memory-efficient
        because the VIEW queries parquet on-demand rather than loading into memory.
        """
        assert self._conn is not None

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

        # Create transcript_index table (id + filename only)
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

        # Create transcripts VIEW for memory-efficient metadata queries
        self._create_transcripts_view(pattern)

    def _apply_query_filter_to_tables(self) -> None:
        """Apply pre-filter query to in-memory tables (indexed path only).

        When a pre-filter query is provided at connect time, filters the
        transcript_index and transcripts tables to match. This is a rare case
        used when the caller wants to work with a subset of transcripts.
        """
        assert self._conn is not None
        assert self._query is not None

        # Build SQL suffix using Query
        suffix, params, register_shuffle = self._query.to_sql_suffix(
            SQLDialect.DUCKDB, shuffle_column="transcript_id"
        )
        if register_shuffle:
            register_shuffle(self._conn)

        filter_sql = f"SELECT * FROM transcript_index{suffix}"

        # Create filtered version in temp table first, then swap
        self._conn.execute("DROP TABLE IF EXISTS transcript_index_filtered")
        self._conn.execute(
            f"CREATE TABLE transcript_index_filtered AS {filter_sql}", params
        )

        # Replace transcript_index with filtered version
        self._conn.execute("DROP TABLE transcript_index")
        self._conn.execute(
            "ALTER TABLE transcript_index_filtered RENAME TO transcript_index"
        )
        self._conn.execute(
            "CREATE INDEX idx_transcript_id ON transcript_index(transcript_id)"
        )

        # Replace transcripts with filtered version
        self._conn.execute("DROP TABLE transcripts")
        self._conn.execute("""
            CREATE TABLE transcripts AS SELECT * FROM transcript_index
        """)

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
                ''::VARCHAR AS source_uri,
                ''::VARCHAR AS date,
                ''::VARCHAR AS task_set,
                ''::VARCHAR AS task_id,
                1::BIGINT AS task_repeat,
                ''::VARCHAR AS agent,
                ''::VARCHAR AS agent_args,
                ''::VARCHAR AS model,
                ''::VARCHAR AS model_options,
                FALSE::BOOLEAN AS success,
                0.0::DOUBLE AS total_time,
                0::BIGINT AS total_tokens,
                ''::VARCHAR AS error,
                ''::VARCHAR AS limit,
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
        base_sql = f"""
            SELECT transcript_id, filename
            FROM read_parquet({pattern}, union_by_name=true, filename=true{enc_config})
        """

        # Apply pre-filter query if provided
        params: list[Any] = []
        if self._query:
            suffix, params, register_shuffle = self._query.to_sql_suffix(
                SQLDialect.DUCKDB, shuffle_column="transcript_id"
            )
            if register_shuffle:
                register_shuffle(self._conn)
            base_sql += suffix

        index_sql = f"CREATE TABLE transcript_index AS {base_sql}"
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

        # migrate view for databases imported from eval_log
        migrate_view(self._conn, "transcripts")

    async def _discover_parquet_files(self) -> list[str]:
        """Discover all Parquet files in location.

        Returns:
            List of file paths (local or S3 URIs).
        """
        assert self._location is not None
        if self._is_s3() or self._is_hf():
            assert self._fs is not None

            # List all files recursively (returns list of FileInfo objects)
            fs = filesystem(self._location)
            all_files = fs.ls(self._location, recursive=True)
            # Filter for transcript parquet files
            files = []
            for f in all_files:
                name = f.name
                if name.endswith(".parquet"):
                    files.append(name)
            return files
        else:
            location_path = UPath(self._location)
            if not location_path.exists():
                location_path.mkdir(parents=True, exist_ok=True)
                return []

            # Recursively discover all transcript parquet files
            return [
                str(p) for p in location_path.glob(f"**/{PARQUET_TRANSCRIPTS_GLOB}")
            ]

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

    def _index_filename_for_parquet(self, parquet_filename: str) -> str:
        """Generate index filename matching parquet file's timestamp/uuid.

        Args:
            parquet_filename: Name of the parquet file (e.g., transcripts_20250101T120000_abc123.parquet)

        Returns:
            Index filename (e.g., index_20250101T120000_abc123.idx or .enc.idx if encrypted)
        """
        assert self._index_storage is not None
        # Extract timestamp_uuid from: transcripts_20250101T120000_abc123.parquet
        # or transcripts_20250101T120000_abc123.enc.parquet
        base = Path(parquet_filename).stem  # transcripts_20250101T120000_abc123
        if base.endswith(".enc"):
            base = base[:-4]  # Remove .enc suffix
        # Remove "transcripts_" prefix, keep timestamp_uuid
        timestamp_uuid = base.replace("transcripts_", "", 1)
        ext = self._index_storage.index_extension()
        return f"index_{timestamp_uuid}{ext}"

    def _build_index_table(self, table: pa.Table, parquet_filename: str) -> pa.Table:
        """Build index table from data table (excludes messages/events, adds filename).

        Args:
            table: PyArrow table with full transcript data.
            parquet_filename: Filename of the parquet file (relative to database location).

        Returns:
            Index table with metadata columns and filename.
        """
        # Get columns to keep (exclude messages and events)
        columns_to_keep = [
            name for name in table.column_names if name not in ("messages", "events")
        ]

        # Select only metadata columns
        index_table = table.select(columns_to_keep)

        # Add filename column (just the filename, not full path)
        filename_array = pa.array([parquet_filename] * len(table), type=pa.string())
        index_table = index_table.append_column("filename", filename_array)

        return index_table

    async def _write_index_for_batch(
        self, table: pa.Table, parquet_path: str, parquet_filename: str
    ) -> None:
        """Write index file for a batch, deleting parquet on failure.

        Args:
            table: PyArrow table with full transcript data.
            parquet_path: Full path to the parquet file (for cleanup on failure).
            parquet_filename: Parquet filename (for index and deriving index filename).

        Raises:
            RuntimeError: If index write fails (parquet file is deleted first).
        """
        assert self._index_storage is not None
        try:
            index_table = self._build_index_table(table, parquet_filename)
            index_filename = self._index_filename_for_parquet(parquet_filename)
            await append_index(index_table, self._index_storage, index_filename)
        except Exception as e:
            # Index write failed - delete parquet file and re-raise
            self._delete_file(parquet_path)
            raise RuntimeError(
                f"Failed to write index for {parquet_filename}: {e}"
            ) from e

    def _delete_file(self, path: str) -> None:
        """Delete a file (local or remote).

        Args:
            path: Path to the file to delete.
        """
        if self._is_s3() or self._is_hf():
            assert self._location is not None
            fs = filesystem(self._location)
            fs.rm(path)
        else:
            Path(path).unlink(missing_ok=True)

    def _as_async_iterator(
        self,
        transcripts: Iterable[Transcript] | AsyncIterable[Transcript] | Transcripts,
    ) -> AsyncIterator[Transcript]:
        """Convert various transcript sources to async iterator.

        Args:
            transcripts: Transcripts from various sources (iterable, async iterable,
                Transcripts object).

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

        # Unexpected type
        else:
            raise NotImplementedError(
                f"Unable to insert transcripts from type {type(transcripts)}"
            )

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

    def _full_parquet_path(self, filename: str) -> str:
        """Convert a filename from the index to a full path.

        The index stores filenames relative to the database location.
        This method constructs the full path by joining the location
        with the relative filename.

        For backwards compatibility with older indexes that stored absolute
        paths or paths that already include the location prefix (due to a
        previous bug), this returns such paths unchanged.

        Args:
            filename: Path from index (relative like 'data/file.parquet' or
                     absolute like '/path/to/file.parquet' or 's3://...')

        Returns:
            Full path suitable for read_parquet.
        """
        # Check if already absolute (Unix path, Windows path, or URI)
        if filename.startswith("/") or "://" in filename:
            return filename

        # Relative path - prepend location
        assert self._location is not None
        location = self._location.rstrip("/")

        # Backward compat: check if filename already starts with location prefix
        # (handles databases created before the fix where full path was stored)
        location_prefix = location + "/"
        if filename.startswith(location_prefix):
            return filename

        return f"{location}/{filename}"

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
        return TranscriptsViewReader(db, self._location, self._query.where)

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
