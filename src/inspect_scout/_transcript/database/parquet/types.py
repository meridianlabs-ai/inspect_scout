"""Type definitions for parquet index module."""

from dataclasses import dataclass

from inspect_ai._util.asyncfiles import AsyncFilesystem

# Index directory and file patterns
INDEX_DIR = "_index"
INCREMENTAL_PREFIX = "index_"
MANIFEST_PREFIX = "_manifest_"
INDEX_EXTENSION = ".idx"

# Timestamp format used in filenames (must sort correctly as strings)
TIMESTAMP_FORMAT = "%Y%m%dT%H%M%S"


@dataclass
class IndexStorage:
    """Storage configuration for index operations.

    Example:
        storage = IndexStorage.create(location="/path/to/db")
    """

    location: str
    fs: AsyncFilesystem | None = None

    @classmethod
    def create(
        cls,
        location: str,
        fs: AsyncFilesystem | None = None,
    ) -> "IndexStorage":
        """Create IndexStorage.

        Args:
            location: Path to the database directory.
            fs: Optional async filesystem for remote storage.

        Returns:
            Configured IndexStorage.
        """
        return cls(location=location, fs=fs)

    def is_remote(self) -> bool:
        """Check if storage location is remote (S3 or HuggingFace)."""
        return self.location.startswith("s3://") or self.location.startswith("hf://")

    def index_dir_path(self) -> str:
        """Get path to the _index directory."""
        return f"{self.location.rstrip('/')}/{INDEX_DIR}"


@dataclass
class CompactionResult:
    """Result of a compaction operation."""

    index_files_merged: int
    index_files_deleted: int
    new_index_path: str
