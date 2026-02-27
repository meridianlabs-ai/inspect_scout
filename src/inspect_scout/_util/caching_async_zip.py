"""AsyncZipReader subclass with global central-directory cache."""

from __future__ import annotations

import anyio
from inspect_ai._util.async_zip import AsyncZipReader, CentralDirectory

_cache: dict[str, CentralDirectory] = {}
_filename_locks: dict[str, anyio.Lock] = {}
_locks_lock = anyio.Lock()


class CachingAsyncZipReader(AsyncZipReader):
    """AsyncZipReader with process-wide central-directory cache.

    Multiple reader instances hitting the same file share one parsed
    central directory, avoiding redundant reads (especially for S3).
    """

    async def entries(self) -> CentralDirectory:
        filename = self._filename
        if (cd := _cache.get(filename)) is not None:
            self._central_directory = cd
            return cd

        async with _locks_lock:
            if filename not in _filename_locks:
                _filename_locks[filename] = anyio.Lock()
            lock = _filename_locks[filename]

        async with lock:
            if (cd := _cache.get(filename)) is not None:
                self._central_directory = cd
                return cd
            cd = await super().entries()
            _cache[filename] = cd
            return cd
