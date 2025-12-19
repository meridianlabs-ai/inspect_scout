"""Local caching for remote index files.

This module provides caching functionality for index files stored on remote
filesystems (S3, HuggingFace). When accessing a remote database, the index
is cached locally to avoid repeated downloads.

Cache structure:
    ~/.cache/inspect_scout/index_cache/
    └── v{VERSION}/                # Version directory (bump to invalidate all caches)
        ├── <location_hash>/       # One directory per remote database
        │   └── <filenames_hash>.parquet  # Cache file (or .enc.parquet)
        └── ...

Cache invalidation:
- Bump INDEX_CACHE_VERSION to invalidate all existing caches
- Each remote location gets its own subdirectory (hash of URL)
- Cache key is a hash of sorted index filenames
- When index files change (added, removed, compacted), the hash changes
- Encrypted databases get encrypted caches (.enc.parquet)
"""

import hashlib
import os
from pathlib import Path

import duckdb

from inspect_scout._util.appdirs import scout_cache_dir

from .encryption import ENCRYPTION_KEY_NAME, setup_encryption
from .types import IndexStorage

# Cache version - bump this to invalidate all existing caches
INDEX_CACHE_VERSION = 1


def _location_cache_dir(storage: IndexStorage) -> Path:
    """Get cache directory for a specific remote location.

    Each remote database gets its own subdirectory based on a hash
    of the location URL. This ensures caches for different databases
    are isolated from each other.

    The path includes a version directory (v1, v2, etc.) so that
    bumping INDEX_CACHE_VERSION invalidates all existing caches.

    Args:
        storage: Storage configuration.

    Returns:
        Path to the location-specific cache directory.
    """
    location = storage.location.rstrip("/")
    location_hash = hashlib.sha256(location.encode()).hexdigest()[:16]
    return scout_cache_dir("index_cache") / f"v{INDEX_CACHE_VERSION}" / location_hash


def _index_cache_key(index_files: list[str]) -> str:
    """Generate cache key from index filenames.

    The key is a hash of the sorted index filenames. When index files
    change (added, removed, compacted), the hash changes and the cache
    is invalidated.

    Args:
        index_files: List of index file paths.

    Returns:
        16-character hex hash of the filenames.
    """
    filenames = sorted(Path(f).name for f in index_files)
    hash_input = "|".join(filenames)
    return hashlib.sha256(hash_input.encode()).hexdigest()[:16]


def get_index_cache_path(storage: IndexStorage, index_files: list[str]) -> Path:
    """Get path to cached index file for this location and index state.

    Args:
        storage: Storage configuration.
        index_files: List of index file paths.

    Returns:
        Path to the cache file.
    """
    cache_dir = _location_cache_dir(storage)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = _index_cache_key(index_files)
    ext = ".enc.parquet" if storage.is_encrypted else ".parquet"
    return cache_dir / f"{cache_key}{ext}"


def load_cached_index(
    conn: duckdb.DuckDBPyConnection,
    cache_path: Path,
    table_name: str,
    storage: IndexStorage,
) -> int | None:
    """Load index from local cache if it exists.

    Args:
        conn: DuckDB connection.
        cache_path: Path to the cache file.
        table_name: Name for the table to create.
        storage: Storage configuration (for encryption).

    Returns:
        Row count if cache was loaded, None if cache doesn't exist or is invalid.
    """
    if not cache_path.exists():
        return None

    try:
        enc_config = setup_encryption(conn, storage)
        conn.execute(f"""
            CREATE TABLE {table_name} AS
            SELECT * FROM read_parquet('{cache_path}'{enc_config})
        """)
        result = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
        return result[0] if result else 0
    except Exception:
        # Cache is corrupted or incompatible - will rebuild
        cache_path.unlink(missing_ok=True)
        return None


def save_index_cache(
    conn: duckdb.DuckDBPyConnection,
    cache_path: Path,
    table_name: str,
    storage: IndexStorage,
) -> None:
    """Save index table to local cache.

    Uses atomic write pattern to prevent partial cache files when multiple
    processes try to cache the same remote index simultaneously.

    Args:
        conn: DuckDB connection with the table loaded.
        cache_path: Path to write the cache file.
        table_name: Name of the table to save.
        storage: Storage configuration (for encryption).
    """
    # Skip if another process already wrote the cache while we were loading
    if cache_path.exists():
        return

    # Write to temp file first, then atomic rename
    tmp_path = cache_path.with_suffix(".tmp")

    try:
        if storage.is_encrypted:
            # Use DuckDB COPY with encryption
            conn.execute(f"""
                COPY {table_name} TO '{tmp_path}'
                (FORMAT PARQUET, COMPRESSION 'zstd',
                 ENCRYPTION_CONFIG {{footer_key: '{ENCRYPTION_KEY_NAME}'}})
            """)
        else:
            # Write unencrypted
            conn.execute(f"""
                COPY {table_name} TO '{tmp_path}'
                (FORMAT PARQUET, COMPRESSION 'zstd')
            """)

        # Atomic rename - on POSIX this atomically replaces any existing file
        os.rename(tmp_path, cache_path)
    except FileExistsError:
        # Another process wrote the cache between our exists() check and rename
        # This is fine - the cache we need is present, just clean up our temp file
        tmp_path.unlink(missing_ok=True)
    except Exception:
        # Clean up temp file on any other error
        tmp_path.unlink(missing_ok=True)
        raise
