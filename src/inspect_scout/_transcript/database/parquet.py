"""DuckDB/Parquet-backed transcript database implementation."""

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Iterable

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from inspect_ai._util.asyncfiles import AsyncFilesystem
from inspect_ai._util.file import filesystem
from inspect_ai.event._event import Event
from inspect_ai.model._chat_message import ChatMessage
from pydantic import TypeAdapter
from typing_extensions import override

from ..json.load_filtered import load_filtered_transcript
from ..local_files_cache import LocalFilesCache, create_temp_cache
from ..metadata import Condition
from ..types import Transcript, TranscriptContent, TranscriptInfo
from .database import TranscriptDB

# Reserved column names that cannot be used as metadata keys
RESERVED_COLUMNS = {"id", "source_id", "source_uri", "content", "messages", "events"}

# Type adapters for parsing Union types
_chat_message_adapter: TypeAdapter[ChatMessage] = TypeAdapter(ChatMessage)
_event_adapter: TypeAdapter[Event] = TypeAdapter(Event)


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


class ParquetTranscriptDB(TranscriptDB):
    """DuckDB-based transcript database using Parquet file storage.

    Stores transcript metadata in Parquet files for efficient querying,
    with content stored as JSON strings and loaded on-demand. Supports
    S3 storage with hybrid caching strategy.
    """

    BATCH_SIZE = 1000
    """Number of transcripts to batch before writing a Parquet file."""

    def __init__(
        self,
        location: str,
        memory_limit: str = "4GB",
        cache_dir: Path | None = None,
    ) -> None:
        """Initialize Parquet transcript database.

        Args:
            location: Directory path (local or S3) containing Parquet files.
            memory_limit: DuckDB memory limit (e.g., '4GB', '8GB').
            cache_dir: Optional cache directory for S3 files. If None, creates temp cache.
        """
        super().__init__(location)
        self._memory_limit = memory_limit
        self._cache_dir = cache_dir

        # State (initialized in connect)
        self._conn: duckdb.DuckDBPyConnection | None = None
        self._fs: AsyncFilesystem | None = None
        self._cache: LocalFilesCache | None = None
        self._current_shuffle_seed: int | None = None

    @override
    async def connect(self) -> None:
        """Initialize DuckDB connection and discover Parquet files."""
        if self._conn is not None:
            return

        # Create DuckDB connection
        self._conn = duckdb.connect(":memory:")
        self._conn.execute(f"SET memory_limit='{self._memory_limit}'")

        # Install httpfs extension for S3 support
        self._conn.execute("INSTALL httpfs")
        self._conn.execute("LOAD httpfs")

        # Configure S3 credentials from environment
        if os.getenv("AWS_ACCESS_KEY_ID"):
            self._conn.execute(
                f"SET s3_access_key_id='{os.getenv('AWS_ACCESS_KEY_ID')}'"
            )
            self._conn.execute(
                f"SET s3_secret_access_key='{os.getenv('AWS_SECRET_ACCESS_KEY')}'"
            )
        if os.getenv("AWS_REGION"):
            self._conn.execute(f"SET s3_region='{os.getenv('AWS_REGION')}'")

        # Initialize filesystem and cache
        assert self._location is not None
        if self._location.startswith("s3://"):
            self._fs = AsyncFilesystem()
            self._cache = (
                LocalFilesCache(self._cache_dir)
                if self._cache_dir
                else create_temp_cache()
            )

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

        if self._cache is not None:
            self._cache.cleanup()
            self._cache = None

    @override
    async def insert(
        self, transcripts: Iterable[Transcript] | AsyncIterator[Transcript]
    ) -> None:
        """Insert transcripts, writing one Parquet file per batch.

        Args:
            transcripts: Transcripts to insert (iterable or async iterator).
        """
        if isinstance(transcripts, AsyncIterator):
            batch: list[Transcript] = []
            async for transcript in transcripts:
                batch.append(transcript)
                if len(batch) >= self.BATCH_SIZE:
                    await self._write_parquet_batch(batch)
                    batch = []
            if batch:
                await self._write_parquet_batch(batch)
        else:
            batch = []
            for transcript in transcripts:
                batch.append(transcript)
                if len(batch) >= self.BATCH_SIZE:
                    await self._write_parquet_batch(batch)
                    batch = []
            if batch:
                await self._write_parquet_batch(batch)

    @override
    async def update(
        self,
        transcripts: Iterable[tuple[str, Transcript]]
        | AsyncIterator[tuple[str, Transcript]],
    ) -> None:
        """Update transcripts by ID using read-filter-rewrite strategy.

        Args:
            transcripts: Tuples of (id, updated_transcript) to update.
        """
        assert self._conn is not None

        # Collect updates into dict
        updates_dict: dict[str, Transcript] = {}
        if isinstance(transcripts, AsyncIterator):
            async for id_, transcript in transcripts:
                updates_dict[id_] = transcript
        else:
            updates_dict = dict(transcripts)

        if not updates_dict:
            return

        # Call rewrite with update map
        await self._rewrite_parquet(update_map=updates_dict)

    @override
    async def delete(self, transcript_ids: Iterable[str]) -> None:
        """Delete transcripts by ID using read-filter-rewrite strategy.

        Args:
            transcript_ids: IDs of transcripts to delete.
        """
        assert self._conn is not None

        id_set = set(transcript_ids)
        if not id_set:
            return

        # Call rewrite with delete filter
        await self._rewrite_parquet(delete_ids=id_set)

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
        sql = f"SELECT * FROM transcripts{where_clause}"

        # Add ORDER BY for shuffle
        if shuffle:
            seed = 0 if shuffle is True else shuffle
            self._register_shuffle_function(seed)
            sql += " ORDER BY shuffle_hash(id)"

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
            transcript_id = row_dict["id"]
            transcript_source_id = row_dict["source_id"]
            transcript_source_uri = row_dict["source_uri"]

            # Reconstruct metadata from all non-reserved columns
            metadata: dict[str, Any] = {}
            for col, value in row_dict.items():
                if col not in RESERVED_COLUMNS and value is not None:
                    # Try to deserialize JSON strings back to objects/arrays
                    if isinstance(value, str):
                        try:
                            parsed = json.loads(value)
                            metadata[col] = parsed
                        except (json.JSONDecodeError, ValueError):
                            # Not JSON, keep as string
                            metadata[col] = value
                    else:
                        metadata[col] = value

            yield TranscriptInfo(
                id=transcript_id,
                source_id=transcript_source_id,
                source_uri=transcript_source_uri,
                metadata=metadata,
            )

    @override
    async def read(self, t: TranscriptInfo, content: TranscriptContent) -> Transcript:
        """Load full transcript content from Parquet.

        Args:
            t: TranscriptInfo identifying the transcript.
            content: Filter for which messages/events to load.

        Returns:
            Full Transcript with filtered content.
        """
        assert self._conn is not None

        # Query for content JSON string
        result = self._conn.execute(
            "SELECT content FROM transcripts WHERE id = ?",
            [t.id],
        ).fetchone()

        if not result or not result[0]:
            # Return transcript with no content
            return Transcript(
                id=t.id,
                source_id=t.source_id,
                source_uri=t.source_uri,
                metadata=t.metadata,
            )

        content_json_str = result[0]

        # Create async iterator from JSON bytes
        async def json_iterator() -> AsyncIterator[bytes]:
            yield content_json_str.encode("utf-8")

        # Use existing streaming parser with filtering
        return await load_filtered_transcript(
            json_iterator(),
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

        # Serialize messages and events to JSON string
        content_dict = {
            "messages": [msg.model_dump() for msg in transcript.messages],
            "events": [event.model_dump() for event in transcript.events],
        }

        # Start with reserved fields
        row: dict[str, Any] = {
            "id": transcript.id,
            "source_id": transcript.source_id,
            "source_uri": transcript.source_uri,
            "content": json.dumps(content_dict),
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
            ("id", pa.string()),
            ("source_id", pa.string()),
            ("source_uri", pa.string()),
            ("content", pa.string()),
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
            # For S3, write to temp file then upload
            import tempfile

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

        # Refresh view to include new file
        await self._create_transcripts_view()

    async def _rewrite_parquet(
        self,
        delete_ids: set[str] | None = None,
        update_map: dict[str, Transcript] | None = None,
    ) -> None:
        """Rewrite all Parquet data (for update/delete operations).

        Args:
            delete_ids: Optional set of transcript IDs to delete.
            update_map: Optional dict of {id: updated_transcript} to update.
        """
        assert self._conn is not None
        assert self._location is not None

        # Read all existing data and reconstruct transcripts
        cursor = self._conn.execute("SELECT * FROM transcripts")
        column_names = [desc[0] for desc in cursor.description]

        kept_transcripts: list[Transcript] = []

        for row in cursor.fetchall():
            row_dict = dict(zip(column_names, row, strict=True))
            transcript_id = row_dict["id"]

            # Skip if being deleted
            if delete_ids and transcript_id in delete_ids:
                continue

            # Use updated version if available
            if update_map and transcript_id in update_map:
                kept_transcripts.append(update_map[transcript_id])
                continue

            # Reconstruct from row
            # Extract metadata from non-reserved columns
            metadata: dict[str, Any] = {}
            for col, value in row_dict.items():
                if col not in RESERVED_COLUMNS and value is not None:
                    if isinstance(value, str):
                        try:
                            metadata[col] = json.loads(value)
                        except (json.JSONDecodeError, ValueError):
                            metadata[col] = value
                    else:
                        metadata[col] = value

            # Deserialize content
            content_str = row_dict.get("content")
            if content_str:
                content_dict = json.loads(content_str)
                messages = [
                    _chat_message_adapter.validate_python(msg)
                    for msg in content_dict.get("messages", [])
                ]
                events = [_event_adapter.validate_python(evt) for evt in content_dict.get("events", [])]
            else:
                messages = []
                events = []

            transcript = Transcript(
                id=row_dict["id"],
                source_id=row_dict["source_id"],
                source_uri=row_dict["source_uri"],
                metadata=metadata,
                messages=messages,
                events=events,
            )
            kept_transcripts.append(transcript)

        # Get list of old files before writing new ones
        old_file_paths = await self._discover_parquet_files()

        # Write new files FIRST (before deleting old ones to prevent data loss)
        new_file_paths: list[str] = []
        if kept_transcripts:
            for i in range(0, len(kept_transcripts), self.BATCH_SIZE):
                batch = kept_transcripts[i : i + self.BATCH_SIZE]

                # Convert to rows with flattened metadata
                rows = [self._transcript_to_row(t) for t in batch]

                # Infer schema from actual data
                schema = self._infer_schema(rows)

                # Create table
                df = pd.DataFrame(rows)
                table = pa.Table.from_pandas(df, schema=schema)

                # Generate filename
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
                file_uuid = uuid.uuid4().hex[:8]
                filename = f"transcripts_{timestamp}_{file_uuid}.parquet"

                # Write based on storage type
                if self._location.startswith("s3://"):
                    # For S3, write to temp file then upload
                    import tempfile

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
                        new_file_paths.append(s3_path)
                    finally:
                        # Clean up temp file
                        Path(tmp_path).unlink(missing_ok=True)
                else:
                    # Local file system
                    location_path = Path(self._location)
                    output_path = location_path / filename

                    pq.write_table(
                        table,
                        output_path.as_posix(),
                        compression="zstd",
                        use_dictionary=True,
                    )
                    new_file_paths.append(output_path.as_posix())

        # Only delete old files AFTER new files are successfully written
        if self._location.startswith("s3://"):
            # Delete old S3 files
            assert self._fs is not None
            for s3_path in old_file_paths:
                if s3_path.startswith("s3://") and s3_path not in new_file_paths:
                    # This is an old S3 URI, delete it
                    fs = filesystem(s3_path)
                    fs.rm(s3_path)
        else:
            # Delete old local files
            location_path = Path(self._location)
            for file_path in old_file_paths:
                if file_path not in new_file_paths:
                    Path(file_path).unlink(missing_ok=True)

        # Refresh view
        await self._create_transcripts_view()

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
                    ''::VARCHAR AS id,
                    ''::VARCHAR AS source_id,
                    ''::VARCHAR AS source_uri,
                    ''::VARCHAR AS content
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

            # List S3 files using filesystem.ls
            fs = filesystem(self._location)
            try:
                # List all files in directory (returns list of paths as strings)
                all_files = fs.ls(self._location)
                # Filter for transcript parquet files
                files = [
                    f["name"] if isinstance(f, dict) else str(f)
                    for f in all_files
                    if (
                        isinstance(f, dict)
                        and f.get("name", "").endswith(".parquet")
                        and "transcripts_" in f.get("name", "")
                    )
                    or (
                        isinstance(f, str)
                        and f.endswith(".parquet")
                        and "transcripts_" in f
                    )
                ]
            except Exception:
                # If listing fails, return empty list
                files = []

            # Try to cache files, but if cache is full, use S3 URIs directly
            file_paths = []
            for file_uri in files:
                cached_path = await self._cache.resolve_remote_uri_to_local(
                    self._fs, file_uri
                )
                # If caching failed (exceeded 5GB), cached_path == file_uri
                file_paths.append(cached_path)

            return file_paths
        else:
            # Local files
            import glob

            location_path = Path(self._location)
            if not location_path.exists():
                location_path.mkdir(parents=True, exist_ok=True)
                return []

            return list(glob.glob(str(location_path / "transcripts_*.parquet")))
