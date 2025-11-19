"""DuckDB/Parquet-backed transcript database implementation."""

import glob
import hashlib
import json
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Iterable, cast

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from inspect_ai._util.asyncfiles import AsyncFilesystem
from inspect_ai._util.file import basename, filesystem
from typing_extensions import override

from inspect_scout._transcript.database.reader import TranscriptsDBReader
from inspect_scout._transcript.transcripts import Transcripts, TranscriptsReader
from inspect_scout._transcript.types import RESERVED_COLUMNS

from ..json.load_filtered import load_filtered_transcript
from ..local_files_cache import LocalFilesCache, create_temp_cache
from ..metadata import Condition
from ..types import Transcript, TranscriptContent, TranscriptInfo
from .database import TranscriptsDB

PARQUET_TRANSCRIPTS_GLOB = "transcripts_*.parquet"


class ParquetTranscriptsDB(TranscriptsDB):
    """DuckDB-based transcript database using Parquet file storage.

    Stores transcript metadata in Parquet files for efficient querying,
    with content stored as JSON strings and loaded on-demand. Supports
    S3 storage with hybrid caching strategy.
    """

    def __init__(
        self,
        location: str,
        batch_size: int = 100,
    ) -> None:
        """Initialize Parquet transcript database.

        Args:
            location: Directory path (local or S3) containing Parquet files.
            cache_dir: Optional cache directory for S3 files. If None, creates temp cache.
            batch_size: Maximum number of transcripts in a parquet file.
        """
        super().__init__(location)
        self._batch_size = batch_size

        # initialize cache
        self._cache_cleanup: Callable[[], None] | None = None
        self._cache = LocalFilesCache.task_cache()
        if self._cache is None:
            self._cache = create_temp_cache()
            self._cache_cleanup = self._cache.cleanup

        # State (initialized in connect)
        self._conn: duckdb.DuckDBPyConnection | None = None
        self._fs: AsyncFilesystem | None = None
        self._current_shuffle_seed: int | None = None

    @override
    async def connect(self) -> None:
        """Initialize DuckDB connection and discover Parquet files."""
        if self._conn is not None:
            return

        # Create DuckDB connection
        self._conn = duckdb.connect(":memory:")

        # Install httpfs extension for S3 support
        self._conn.execute("INSTALL httpfs")
        self._conn.execute("LOAD httpfs")

        # Create secret that automatically picks up credentials from environment
        self._conn.execute("""
            CREATE SECRET (
                TYPE S3,
                PROVIDER credential_chain
            )
        """)

        # Enable DuckDB's HTTP/S3 caching features for better performance
        self._conn.execute("SET enable_http_metadata_cache=true")
        self._conn.execute("SET http_keep_alive=true")
        self._conn.execute("SET http_timeout=30000")  # 30 seconds

        # Initialize filesystem and cache
        assert self._location is not None
        if self._location.startswith("s3://"):
            self._fs = AsyncFilesystem()

        # Discover and register Parquet files
        await self._create_transcripts_view()

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

        if self._cache_cleanup is not None:
            self._cache_cleanup()
            self._cache_cleanup = None

    @override
    async def insert(
        self,
        transcripts: Iterable[Transcript] | AsyncIterator[Transcript] | Transcripts,
    ) -> None:
        """Insert transcripts, writing one Parquet file per batch.

        Args:
            transcripts: Transcripts to insert (iterable or async iterator).
        """
        last_source_id: str | None = None
        batch: list[Transcript] = []
        async for transcript in self._as_async_iterator(transcripts):
            # flush if the source id changed
            if last_source_id is not None:
                if transcript.source_id != last_source_id:
                    await self._write_parquet_batch(batch)
                    batch = []
            last_source_id = transcript.source_id

            # tick
            print(f"{basename(transcript.source_uri)} ({transcript.transcript_id})")

            # append to batch
            batch.append(transcript)

            # enforce batch size
            if len(batch) >= self._batch_size:
                await self._write_parquet_batch(batch)
                batch = []

        # write any leftover elements
        if batch:
            await self._write_parquet_batch(batch)

        # refresh the view
        await self._create_transcripts_view()

    @override
    async def count(
        self,
        where: list[Condition],
        limit: int | None = None,
    ) -> int:
        """Count transcripts matching conditions.

        Args:
            where: List of conditions to filter by.
            limit: Optional limit on count.

        Returns:
            Number of matching transcripts.
        """
        assert self._conn is not None

        where_clause, where_params = self._build_where_clause(where)

        if limit is not None:
            sql = f"SELECT COUNT(*) FROM (SELECT * FROM transcripts{where_clause} LIMIT ?) AS limited"
            params = where_params + [limit]
        else:
            sql = f"SELECT COUNT(*) FROM transcripts{where_clause}"
            params = where_params

        result = self._conn.execute(sql, params).fetchone()
        return result[0] if result else 0

    @override
    async def select(
        self,
        where: list[Condition],
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
        sql = f"SELECT * EXCLUDE (events, messages) FROM transcripts{where_clause}"

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

        # Execute query and yield results
        cursor = self._conn.execute(sql, params)
        column_names = [desc[0] for desc in cursor.description]

        for row in cursor.fetchall():
            row_dict = dict(zip(column_names, row, strict=True))

            # Extract reserved fields
            transcript_id = row_dict["transcript_id"]
            transcript_source_type = row_dict["source_type"]
            transcript_source_id = row_dict["source_id"]
            transcript_source_uri = row_dict["source_uri"]

            # Reconstruct metadata from all non-reserved columns
            metadata: dict[str, Any] = {}
            for col, value in row_dict.items():
                if col not in RESERVED_COLUMNS and value is not None:
                    # Try to deserialize JSON strings back to objects/arrays
                    # Only attempt parsing if string starts with JSON markers
                    if isinstance(value, str) and value and value[0] in ("{", "["):
                        try:
                            parsed = json.loads(value)
                            metadata[col] = parsed
                        except (json.JSONDecodeError, ValueError):
                            # Not valid JSON, keep as string
                            metadata[col] = value
                    else:
                        metadata[col] = value

            yield TranscriptInfo(
                transcript_id=transcript_id,
                source_type=transcript_source_type,
                source_id=transcript_source_id,
                source_uri=transcript_source_uri,
                metadata=metadata,
            )

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

        # Determine which columns we need to read
        need_messages = content.messages is not None
        need_events = content.events is not None

        if not need_messages and not need_events:
            # No content needed
            return Transcript(
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

        # Query DuckDB for the content columns
        sql = f"SELECT {', '.join(columns)} FROM transcripts WHERE transcript_id = ?"
        result = self._conn.execute(sql, [t.transcript_id]).fetchone()

        if not result:
            # Transcript not found
            return Transcript(
                transcript_id=t.transcript_id,
                source_type=t.source_type,
                source_id=t.source_id,
                source_uri=t.source_uri,
                metadata=t.metadata,
            )

        # Extract column values
        messages_json: str | None = None
        events_json: str | None = None

        col_idx = 0
        if need_messages:
            messages_json = result[col_idx]
            col_idx += 1
        if need_events:
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

    def _build_where_clause(self, where: list[Condition]) -> tuple[str, list[Any]]:
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

    async def _write_parquet_batch(self, batch: list[Transcript]) -> None:
        """Write a batch of transcripts to a new Parquet file.

        Args:
            batch: List of transcripts to write.
        """
        if not batch:
            return

        # Convert transcripts to rows with flattened metadata
        rows = [self._transcript_to_row(t) for t in batch]

        # Infer schema from actual data
        schema = self._infer_schema(rows)

        # Create DataFrame and convert to PyArrow table
        df = pd.DataFrame(rows)
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
                pq.write_table(
                    table,
                    tmp_path,
                    compression="zstd",
                    use_dictionary=True,
                )

                # Upload to S3
                s3_path = f"{self._location.rstrip('/')}/{filename}"
                assert self._fs is not None
                await self._fs.write_file(s3_path, Path(tmp_path).read_bytes())
                print(s3_path)
            finally:
                # Clean up temp file
                Path(tmp_path).unlink(missing_ok=True)
        else:
            # Local file system
            output_path = Path(self._location) / filename
            output_path.parent.mkdir(parents=True, exist_ok=True)

            pq.write_table(
                table,
                output_path.as_posix(),
                compression="zstd",
                use_dictionary=True,
            )

            print(output_path.as_posix())

    async def _create_transcripts_view(self) -> None:
        """Create or refresh DuckDB view of all Parquet files with schema union."""
        assert self._conn is not None

        # Drop existing view
        self._conn.execute("DROP VIEW IF EXISTS transcripts")

        # Discover Parquet files
        file_paths = await self._discover_parquet_files()

        if not file_paths:
            # Create empty view with minimal schema
            self._conn.execute("""
                CREATE VIEW transcripts AS
                SELECT
                    ''::VARCHAR AS transcript_id,
                    ''::VARCHAR AS source_type,
                    ''::VARCHAR AS source_id,
                    ''::VARCHAR AS source_uri,
                    ''::VARCHAR AS messages,
                    ''::VARCHAR AS events
                WHERE FALSE
            """)
            return

        # Build file list for read_parquet
        if len(file_paths) == 1:
            pattern = f"'{file_paths[0]}'"
        else:
            pattern = "[" + ", ".join(f"'{p}'" for p in file_paths) + "]"

        # Create view with schema union (DuckDB handles different schemas)
        # union_by_name=true merges columns across files with different schemas
        self._conn.execute(f"""
            CREATE VIEW transcripts AS
            SELECT * FROM read_parquet({pattern}, union_by_name=true)
        """)

    async def _discover_parquet_files(self) -> list[str]:
        """Discover all Parquet files in location.

        Returns:
            List of file paths (local or S3 URIs).
        """
        assert self._location is not None
        if self._location.startswith("s3://"):
            assert self._fs is not None
            assert self._cache is not None

            # List all files in directory (returns list of FileInfo objects)
            from inspect_ai._util.file import FileInfo

            fs = filesystem(self._location)
            all_files = fs.ls(self._location)
            # Filter for transcript parquet files
            files = []
            for f in all_files:
                # Get the file name from different possible types
                if isinstance(f, FileInfo):
                    name = f.name
                elif isinstance(f, dict):
                    name = f.get("name", "")
                elif isinstance(f, str):
                    name = f
                else:
                    continue

                # Check if it's a transcript parquet file
                if name.endswith(".parquet") and "transcripts_" in name:
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

            return list(glob.glob(str(location_path / PARQUET_TRANSCRIPTS_GLOB)))

    def _as_async_iterator(
        self,
        transcripts: Iterable[Transcript] | AsyncIterator[Transcript] | Transcripts,
    ) -> AsyncIterator[Transcript]:
        """Convert iterable or async iterator to async iterator.

        Args:
            transcripts: Either a regular iterable or async iterator.

        Returns:
            AsyncIterator over transcripts. If input is already async, returns it
            directly. Otherwise, wraps the iterable in an async generator.
        """
        # Already an async iterator - return it directly
        if hasattr(transcripts, "__anext__"):
            return cast(AsyncIterator[Transcript], transcripts)

        # Transcripts, yield an iterator that reads them fully
        elif isinstance(transcripts, Transcripts):

            async def _iter() -> AsyncIterator[Transcript]:
                async with transcripts.reader() as tr:
                    async for t in tr.index():
                        yield await tr.read(
                            t, content=TranscriptContent(messages="all", events="all")
                        )

            return _iter()

        # ordinary iterator
        else:

            async def _iter() -> AsyncIterator[Transcript]:
                for transcript in transcripts:
                    yield transcript

            return _iter()


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

    @override
    def reader(self) -> TranscriptsReader:
        """Get a reader for querying transcripts.

        Returns:
            TranscriptsReader configured with current query parameters.
        """
        db = ParquetTranscriptsDB(self._location)
        return TranscriptsDBReader(db, self._query)


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
