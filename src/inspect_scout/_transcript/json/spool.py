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


# Linux caps a single read(2) at 0x7ffff000, so any value larger than this
# comes back short no matter what is asked for -- which is the normal case for
# the transcripts this spool exists to bound.
_READ_CAP = 0x7FFFF000


def _read_at(fd: int, lock: threading.Lock, length: int, offset: int) -> bytearray:
    """Read up to ``length`` bytes from ``offset`` (portable ``os.pread``).

    Fills one preallocated buffer rather than concatenating what each read
    returns. Above `_READ_CAP` every read is short, and appending would both
    reallocate the whole accumulated value per iteration -- quadratic, and
    briefly holding two copies of a multi-GB cell -- and defeat the bound this
    spool exists to keep.

    Returns a `bytearray` so the caller owns the buffer with no final copy;
    converting to `bytes` here would reintroduce the doubling.
    """
    buffer = bytearray(length)
    if length == 0:
        return buffer
    view = memoryview(buffer)
    filled = 0
    with lock:
        while filled < length:
            got = os.preadv(fd, [view[filled:]], offset + filled)
            if not got:
                break
            filled += got
    if filled < length:
        del view
        del buffer[filled:]
    return buffer


def _write_at(
    fd: int, lock: threading.Lock, data: bytes | bytearray | memoryview, offset: int
) -> None:
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

    def has(self, key: SpoolKey) -> bool:
        """Whether ``key`` was spooled, without reading its value."""
        return key in self._index

    def pool_len(self, pool_name: str) -> int:
        return self._pool_counts.get(pool_name, 0)

    def close(self) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None
            self._fd = None


class ByteSpool:
    """Append-only spool of raw bytes for one value, read back in chunks.

    Its own file rather than a ``BlobSpool`` entry: a value is written
    incrementally, so anything else appending to the same file in between
    would interleave with it.
    """

    def __init__(self, dir: Path) -> None:
        self._file: IO[bytes] | None = _open_spool_file(dir, ".bytes")
        self._fd: int | None = self._file.fileno()
        self._lock = threading.Lock()
        self._write_offset = 0

    def write(self, data: bytes | bytearray | memoryview) -> None:
        if self._fd is None:
            raise ValueError("spool is closed")
        _write_at(self._fd, self._lock, data, self._write_offset)
        self._write_offset += len(data)

    def __len__(self) -> int:
        return self._write_offset

    def chunks(self, chunk_size: int = 1024 * 1024) -> Iterator[bytearray]:
        """Yield the value in chunks, so it never exists whole in memory."""
        if self._fd is None:
            raise ValueError("spool is closed")
        offset = 0
        while offset < self._write_offset:
            read_len = min(chunk_size, self._write_offset - offset)
            yield _read_at(self._fd, self._lock, read_len, offset)
            offset += read_len

    def read(self) -> bytearray:
        """The whole value. Prefer ``chunks()`` when it may be large."""
        if self._fd is None:
            raise ValueError("spool is closed")
        return _read_at(self._fd, self._lock, self._write_offset, 0)

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
        # Reads a chunk at a time, tracking position with a cursor and
        # collecting the pieces of a straddling line in a list. The obvious
        # alternatives are both quadratic: growing the buffer with ``+=``
        # re-copies the whole line on every chunk (a 44MB item costs ~3.8GB of
        # copying), and re-slicing the buffer past each line re-copies the
        # remaining chunk once per line.
        if self._fd is None:
            raise ValueError("spool is closed")
        end = self._write_offset
        offset = 0
        chunk_size = 256 * 1024
        parts: list[bytes | bytearray] = []  # pieces of a line split across chunks
        buffer: bytes | bytearray = b""
        cursor = 0
        while True:
            newline = buffer.find(b"\n", cursor)
            if newline != -1:
                segment = buffer[cursor:newline]
                cursor = newline + 1
                line: bytes | bytearray
                if parts:
                    parts.append(segment)
                    line = b"".join(parts)
                    parts.clear()
                else:
                    line = segment
                yield json.loads(line)
                continue

            # no complete line left: keep the tail and read the next chunk
            if cursor < len(buffer):
                parts.append(buffer[cursor:])
            buffer = b""
            cursor = 0
            if offset >= end:
                break
            if self._fd is None:
                raise ValueError("spool is closed")
            read_len = min(chunk_size, end - offset)
            buffer = _read_at(self._fd, self._lock, read_len, offset)
            offset += read_len
            if not buffer:
                break

    def close(self) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None
            self._fd = None
