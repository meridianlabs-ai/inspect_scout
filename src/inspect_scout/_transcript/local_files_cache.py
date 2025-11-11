"""Local file cache for remote transcript files.

Provides transparent caching of remote files (e.g., S3) to local disk,
with multiprocess coordination via marker files.
"""

import hashlib
import os
import shutil
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Final, Iterator

import anyio
from inspect_ai._util.asyncfiles import AsyncFilesystem
from inspect_ai._util.file import filesystem


class LocalFilesCache:
    """Cache for remote files with automatic cleanup.

    Downloads remote files to a local temporary directory for faster access.
    Coordinates concurrent downloads across processes using marker files.
    """

    MAX_CACHE_FILE_SIZE: Final[int] = 5 * 1024 * 1024 * 1024  # 5GB

    def __init__(self, cache_dir: Path) -> None:
        """Initialize cache with specified directory.

        Args:
            cache_dir: Directory to store cached files. Created immediately.
        """
        self._cache_dir = cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def cache_dir(self) -> Path:
        """Get the cache directory path."""
        return self._cache_dir

    async def resolve_remote_uri_to_local(self, fs: AsyncFilesystem, uri: str) -> str:
        """Resolve a URI to a local file path, downloading if necessary.

        If the URI is already local, returns it unchanged. If remote,
        downloads to cache (or waits for another process to finish downloading)
        and returns the cached file path.

        Args:
            fs: AsyncFilesystem instance for reading remote files.
            uri: File URI (local path or remote URL like s3://)

        Returns:
            Local file path that can be accessed directly.
        """
        if filesystem(uri).is_local():
            return uri

        # Check total cache size - skip caching if cache is full
        total_cache_size = sum(
            f.stat().st_size
            for f in self._cache_dir.iterdir()
            if f.is_file() and not f.suffix == ".downloading"
        )
        if total_cache_size > self.MAX_CACHE_FILE_SIZE:
            return uri

        # Generate unique cache filename from URI hash
        uri_hash = hashlib.sha256(uri.encode()).hexdigest()
        cache_file = self._cache_dir / uri_hash
        marker_file = cache_file.with_suffix(".downloading")

        while True:
            if cache_file.exists():
                return cache_file.as_posix()

            with _try_create_marker(marker_file) as f:
                if f is None:
                    await anyio.sleep(1)
                    continue

                # We own the marker - download to it
                try:
                    file_size = await fs.get_size(uri)
                    stream = await fs.read_file_bytes(uri, 0, file_size)
                    async for chunk in stream:
                        f.write(chunk)

                except Exception:
                    marker_file.unlink(missing_ok=True)
                    raise

            # Rename after file is closed
            marker_file.rename(cache_file)
            return cache_file.as_posix()

    def cleanup(self) -> None:
        """Delete the cache directory and all its contents."""
        if self._cache_dir.exists():
            shutil.rmtree(self._cache_dir)


@contextmanager
def _try_create_marker(marker_file: Path) -> Iterator[IO[bytes] | None]:
    """Context manager that atomically creates and opens marker file.

    Yields opened file handle if created successfully, None if already exists.
    Ensures file is closed and cleaned up on error.
    """
    try:
        fd = os.open(marker_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
        f = open(marker_file, "wb")
        try:
            yield f
        finally:
            f.close()
    except FileExistsError:
        yield None
    except Exception:
        marker_file.unlink(missing_ok=True)
        raise


def create_temp_cache() -> LocalFilesCache:
    """Create a cache with a temporary directory.

    Returns:
        LocalFilesCache: Cache instance with temp directory.
    """
    temp_dir = tempfile.mkdtemp(prefix="inspect_scout_cache_")
    return LocalFilesCache(Path(temp_dir))
