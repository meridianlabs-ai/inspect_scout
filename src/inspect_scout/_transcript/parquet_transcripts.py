"""Parquet-backed transcript collection implementation."""

from pathlib import Path

from typing_extensions import override

from .database.parquet import ParquetTranscriptDB
from .database.reader import TranscriptsDBReader
from .transcripts import Transcripts, TranscriptsReader


class ParquetTranscripts(Transcripts):
    """Collection of transcripts stored in Parquet files.

    Provides efficient querying of transcript metadata using DuckDB,
    with content loaded on-demand from JSON strings stored in Parquet.
    """

    def __init__(
        self,
        location: str,
        memory_limit: str = "4GB",
        cache_dir: Path | None = None,
    ) -> None:
        """Initialize Parquet transcript collection.

        Args:
            location: Directory path (local or S3) containing Parquet files.
            memory_limit: DuckDB memory limit (e.g., '4GB', '8GB').
            cache_dir: Optional cache directory for S3 files.
        """
        super().__init__()
        self._location = location
        self._memory_limit = memory_limit
        self._cache_dir = cache_dir
        self._db: ParquetTranscriptDB | None = None

    @override
    def reader(self) -> TranscriptsReader:
        """Get a reader for querying transcripts.

        Returns:
            TranscriptsReader configured with current query parameters.
        """
        if self._db is None:
            self._db = ParquetTranscriptDB(
                self._location,
                memory_limit=self._memory_limit,
                cache_dir=self._cache_dir,
            )
        return TranscriptsDBReader(self._db, None, self._query)


def transcripts_from_parquet(
    location: str,
    memory_limit: str = "4GB",
    cache_dir: Path | None = None,
) -> Transcripts:
    """Create transcript collection from Parquet files.

    Args:
        location: Directory path (local or S3) containing Parquet files.
        memory_limit: DuckDB memory limit (e.g., '4GB', '8GB'). Defaults to '4GB'.
        cache_dir: Optional cache directory for S3 files. If None, creates temp cache.

    Returns:
        Transcripts collection for querying and scanning.

    Example:
        ```python
        from inspect_scout import transcripts_from_parquet, metadata as m

        # Load from local directory
        transcripts = transcripts_from_parquet("./transcript_db")

        # Load from S3
        transcripts = transcripts_from_parquet("s3://bucket/transcript_db")

        # Filter by metadata
        transcripts = transcripts.where(m.model == "gpt-4")
        transcripts = transcripts.limit(100)
        ```
    """
    return ParquetTranscripts(
        location=location,
        memory_limit=memory_limit,
        cache_dir=cache_dir,
    )
