"""Disk spools for streaming transcript parses.

Spool files come from ``tempfile.TemporaryFile`` so the OS reclaims them when
the fd closes and a crash cannot leak them: POSIX unlinks at creation, Windows
opens with ``O_TEMPORARY``. Positional access seeks under a per-spool lock
rather than using ``os.pread``/``os.pwrite``, which are POSIX-only; the lock
keeps the seek and the read/write atomic so concurrent iterators still never
interfere via the shared file position.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import IO, Any, Iterator

SpoolKey = tuple[str, int] | str


def _read_at(fd: int, lock: threading.Lock, length: int, offset: int) -> bytes:
    """Read up to ``length`` bytes from ``offset`` (portable ``os.pread``)."""
    with lock:
        os.lseek(fd, offset, os.SEEK_SET)
        data = os.read(fd, length)
        # Regular-file reads normally satisfy the request outright; loop only
        # for the short-read case so the common path stays copy-free.
        while len(data) < length:
            chunk = os.read(fd, length - len(data))
            if not chunk:
                break
            data += chunk
    return data


def _write_at(fd: int, lock: threading.Lock, data: bytes, offset: int) -> None:
    """Write all of ``data`` at ``offset`` (portable ``os.pwrite``)."""
    with lock:
        os.lseek(fd, offset, os.SEEK_SET)
        view = memoryview(data)
        while view:
            view = view[os.write(fd, view) :]


def _open_spool_file(dir: Path, suffix: str) -> IO[bytes]:
    """Open an auto-deleting, unbuffered spool file.

    Unbuffered because all access goes through the raw fd via ``_read_at`` /
    ``_write_at``; a buffer on the object would never be consulted.
    """
    return tempfile.TemporaryFile(
        mode="w+b", buffering=0, dir=dir, prefix="scout-spool-", suffix=suffix
    )


class BlobSpool:
    """Append-only spool with an in-memory offset index.

    Keys are attachment ids (str) or positional pool entries
    ((pool_name, index)) -- pool refs are half-open ranges so pool
    items must be positionally addressable.
    """

    def __init__(self, dir: Path) -> None:
        self._file: IO[bytes] | None = _open_spool_file(dir, ".blob")
        self._fd: int | None = self._file.fileno()
        self._lock = threading.Lock()
        self._index: dict[SpoolKey, tuple[int, int]] = {}
        self._pool_counts: dict[str, int] = {}
        self._write_offset = 0

    def put(self, key: SpoolKey, value: str) -> None:
        if self._fd is None:
            raise ValueError("spool is closed")
        data = value.encode("utf-8")
        _write_at(self._fd, self._lock, data, self._write_offset)
        self._index[key] = (self._write_offset, len(data))
        self._write_offset += len(data)
        if isinstance(key, tuple):
            pool_name, _ = key
            self._pool_counts[pool_name] = self._pool_counts.get(pool_name, 0) + 1

    def get(self, key: SpoolKey) -> str | None:
        if self._fd is None:
            raise ValueError("spool is closed")
        entry = self._index.get(key)
        if entry is None:
            return None
        offset, length = entry
        return _read_at(self._fd, self._lock, length, offset).decode("utf-8")

    def pool_len(self, pool_name: str) -> int:
        return self._pool_counts.get(pool_name, 0)

    def close(self) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None
            self._fd = None


class ItemSpool:
    """JSONL spool of dicts supporting multiple concurrent iterations."""

    def __init__(self, dir: Path) -> None:
        self._file: IO[bytes] | None = _open_spool_file(dir, ".jsonl")
        self._fd: int | None = self._file.fileno()
        self._lock = threading.Lock()
        self._write_offset = 0
        self._count = 0

    def append(self, item: dict[str, Any]) -> None:
        if self._fd is None:
            raise ValueError("spool is closed")
        line = json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n"
        data = line.encode("utf-8")
        _write_at(self._fd, self._lock, data, self._write_offset)
        self._write_offset += len(data)
        self._count += 1

    def __len__(self) -> int:
        return self._count

    def items(self) -> Iterator[dict[str, Any]]:
        if self._fd is None:
            raise ValueError("spool is closed")
        end = self._write_offset
        offset = 0
        buffer = b""
        chunk_size = 256 * 1024
        while offset < end or b"\n" in buffer:
            newline = buffer.find(b"\n")
            if newline == -1:
                read_len = min(chunk_size, end - offset)
                if read_len <= 0:
                    break
                if self._fd is None:
                    raise ValueError("spool is closed")
                buffer += _read_at(self._fd, self._lock, read_len, offset)
                offset += read_len
                continue
            line, buffer = buffer[:newline], buffer[newline + 1 :]
            yield json.loads(line)

    def close(self) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None
            self._fd = None
