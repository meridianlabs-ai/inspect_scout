"""Type definitions for parquet index module."""

from dataclasses import dataclass
from pathlib import Path

from inspect_ai._util.asyncfiles import AsyncFilesystem
from inspect_ai._util.error import PrerequisiteError
from inspect_ai._util.file import filesystem

# Index directory and file patterns
INDEX_DIR = "_index"
INCREMENTAL_PREFIX = "index_"
MANIFEST_PREFIX = "_manifest_"
INDEX_EXTENSION = ".idx"
ENCRYPTED_INDEX_EXTENSION = ".enc.idx"

# Timestamp format used in filenames (must sort correctly as strings)
TIMESTAMP_FORMAT = "%Y%m%dT%H%M%S"


@dataclass
class IndexStorage:
    """Storage configuration for index operations.

    Use the async `create()` classmethod to construct with automatic
    encryption detection from existing files.

    Example:
        storage = await IndexStorage.create(location="/path/to/db")
        # storage.is_encrypted is correctly set based on existing files
    """

    location: str
    fs: AsyncFilesystem | None = None
    is_encrypted: bool = False
    encryption_key: str | None = None

    @classmethod
    async def create(
        cls,
        location: str,
        fs: AsyncFilesystem | None = None,
        key: str | None = None,
    ) -> "IndexStorage":
        """Create IndexStorage with encryption status auto-detected.

        Checks index files first, then data files if no index exists.
        If encrypted files are detected, validates that the encryption key
        is available (either passed directly or from environment).

        Args:
            location: Path to the database directory.
            fs: Optional async filesystem for remote storage.
            key: Optional encryption key. If not provided and encrypted files
                are detected, falls back to SCOUT_DB_ENCRYPTION_KEY env var.

        Returns:
            Configured IndexStorage with is_encrypted set appropriately.

        Raises:
            ValueError: If files have mixed encryption status, or if
                encrypted files exist but no encryption key is available.
        """
        # Import here to avoid circular imports
        from .encryption import ENCRYPTION_KEY_ENV, get_encryption_key_from_env

        storage = cls(location=location, fs=fs, is_encrypted=False)
        is_encrypted = await storage._detect_encryption()

        if is_encrypted:
            # Use provided key or fall back to environment
            resolved_key = key if key is not None else get_encryption_key_from_env()
            if not resolved_key:
                raise PrerequisiteError(
                    "Encrypted files detected but no encryption key provided. "
                    f"Pass key parameter or set {ENCRYPTION_KEY_ENV} environment variable."
                )
        else:
            resolved_key = None

        return cls(
            location=location,
            fs=fs,
            is_encrypted=is_encrypted,
            encryption_key=resolved_key,
        )

    def is_remote(self) -> bool:
        """Check if storage location is remote (S3 or HuggingFace)."""
        return self.location.startswith("s3://") or self.location.startswith("hf://")

    def index_dir_path(self) -> str:
        """Get path to the _index directory."""
        return f"{self.location.rstrip('/')}/{INDEX_DIR}"

    def index_extension(self) -> str:
        """Get the appropriate index file extension based on encryption status."""
        return ENCRYPTED_INDEX_EXTENSION if self.is_encrypted else INDEX_EXTENSION

    async def _detect_encryption(self) -> bool:
        """Detect encryption status from existing files."""
        # Import here to avoid circular imports
        from .encryption import (
            _check_data_encryption_status,
            _check_index_encryption_status,
        )
        from .index import _discover_data_files_internal, _is_index_file

        # First check index files
        index_dir = self.index_dir_path()

        if self.is_remote():
            fs = filesystem(self.location)
            try:
                all_files = fs.ls(index_dir, recursive=False)
                idx_files = [f.name for f in all_files if _is_index_file(f.name)]
            except FileNotFoundError:
                idx_files = []
        else:
            index_path = Path(index_dir)
            if index_path.exists():
                idx_files = [str(p) for p in index_path.glob("*" + INDEX_EXTENSION)]
            else:
                idx_files = []

        # Check index file encryption status
        is_encrypted = _check_index_encryption_status(idx_files)

        # If no index files, check data files
        if is_encrypted is None:
            data_files = await _discover_data_files_internal(self)
            is_encrypted = _check_data_encryption_status(data_files)

        # Default to False if no files exist
        return is_encrypted if is_encrypted is not None else False


@dataclass
class CompactionResult:
    """Result of a compaction operation."""

    index_files_merged: int
    index_files_deleted: int
    new_index_path: str
