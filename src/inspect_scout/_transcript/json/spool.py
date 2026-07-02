"""Disk spools for streaming transcript parses.

Spool files are created inside the task files cache dir and unlinked
immediately after open (POSIX), so crash leaks are impossible; the data
lives until the fd is closed. Reads use os.pread so concurrent iterators
never interfere via shared file position.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterator

SpoolKey = tuple[str, int] | str


class BlobSpool:
    """Append-only spool with an in-memory offset index.

    Keys are attachment ids (str) or positional pool entries
    ((pool_name, index)) -- pool refs are half-open ranges so pool
    items must be positionally addressable.
    """

    def __init__(self, dir: Path) -> None:
        fd, path = tempfile.mkstemp(dir=dir, prefix="scout-spool-", suffix=".blob")
        os.unlink(path)
        self._fd: int | None = fd
        self._index: dict[SpoolKey, tuple[int, int]] = {}
        self._pool_counts: dict[str, int] = {}
        self._write_offset = 0

    def put(self, key: SpoolKey, value: str) -> None:
        assert self._fd is not None
        data = value.encode("utf-8")
        os.pwrite(self._fd, data, self._write_offset)
        self._index[key] = (self._write_offset, len(data))
        self._write_offset += len(data)
        if isinstance(key, tuple):
            pool_name, _ = key
            self._pool_counts[pool_name] = self._pool_counts.get(pool_name, 0) + 1

    def get(self, key: SpoolKey) -> str | None:
        assert self._fd is not None
        entry = self._index.get(key)
        if entry is None:
            return None
        offset, length = entry
        return os.pread(self._fd, length, offset).decode("utf-8")

    def pool_len(self, pool_name: str) -> int:
        return self._pool_counts.get(pool_name, 0)

    def close(self) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None


class ItemSpool:
    """JSONL spool of dicts supporting multiple concurrent iterations."""

    def __init__(self, dir: Path) -> None:
        fd, path = tempfile.mkstemp(dir=dir, prefix="scout-spool-", suffix=".jsonl")
        os.unlink(path)
        self._fd: int | None = fd
        self._write_offset = 0
        self._count = 0

    def append(self, item: dict[str, Any]) -> None:
        assert self._fd is not None
        line = json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n"
        data = line.encode("utf-8")
        os.pwrite(self._fd, data, self._write_offset)
        self._write_offset += len(data)
        self._count += 1

    def __len__(self) -> int:
        return self._count

    def items(self) -> Iterator[dict[str, Any]]:
        assert self._fd is not None
        fd = self._fd
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
                buffer += os.pread(fd, read_len, offset)
                offset += read_len
                continue
            line, buffer = buffer[:newline], buffer[newline + 1 :]
            yield json.loads(line)

    def close(self) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
