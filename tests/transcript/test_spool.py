"""Tests for spool primitives."""

from __future__ import annotations

import errno
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest
from inspect_scout._transcript.json import spool as spool_mod
from inspect_scout._transcript.json.spool import ByteSpool, ItemSpool


@pytest.mark.parametrize(
    "char_count",
    [90_000, 400_000],
    ids=["spans-chunks", "spans-many-chunks"],
)
def test_item_spool_item_spanning_internal_chunks(
    char_count: int, tmp_path: Path
) -> None:
    """Items larger than the internal read chunk reassemble byte-exactly.

    Uses 3-byte characters so that multi-byte sequences straddle the internal
    chunk boundaries (which are powers of two): assembly works on raw bytes and
    must not decode a partial chunk.
    """
    spool = ItemSpool(tmp_path)
    try:
        big = {"pad": "你" * char_count}
        following = {"n": 1}
        spool.append(big)
        spool.append(following)
        assert list(spool.items()) == [big, following]
    finally:
        spool.close()


@pytest.mark.parametrize(
    "size",
    [0, 1024 * 1024 - 1, 1024 * 1024, 1024 * 1024 + 1],
    ids=["empty", "one-below-chunk", "exactly-one-chunk", "one-above-chunk"],
)
def test_byte_spool_roundtrips_across_chunk_boundaries(
    size: int, tmp_path: Path
) -> None:
    """Ragged writes reassemble byte-exactly, however they land in chunks.

    `chunks()` slices at fixed offsets rather than at value boundaries, so the
    sizes either side of a chunk are the interesting ones.
    """
    payload = bytes(range(256)) * (size // 256) + bytes(range(size % 256))
    spool = ByteSpool(tmp_path)
    try:
        for start in range(0, len(payload), 7919):  # a prime, so writes stay ragged
            spool.write(payload[start : start + 7919])

        assert len(spool) == len(payload)
        assert spool.read() == payload
        assert b"".join(spool.chunks()) == payload
        assert b"".join(spool.chunks(chunk_size=4096)) == payload
        assert all(len(chunk) <= 4096 for chunk in spool.chunks(chunk_size=4096))
    finally:
        spool.close()


def test_byte_spool_concurrent_first_reads_agree(tmp_path: Path) -> None:
    """Readers racing to read freshly written bytes all get the whole value."""
    payload = bytes(range(256)) * 1000
    spool = ByteSpool(tmp_path)
    try:
        for start in range(0, len(payload), 100):
            spool.write(payload[start : start + 100])
        barrier = threading.Barrier(8)

        def read() -> bytes:
            barrier.wait()
            return bytes(spool.read())

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: read(), range(8)))
        assert results == [payload] * 8
    finally:
        spool.close()


def test_byte_spool_close_keeps_a_failed_flush_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A batch write that fails surfaces its own error, not one from close().

    Cleanup paths close the spool while that error, and its traceback, are
    still live.
    """

    def disk_full(fd: int, data: memoryview) -> int:
        raise OSError(errno.ENOSPC, os.strerror(errno.ENOSPC))

    spool = ByteSpool(tmp_path)
    spool.write(b"batched")
    monkeypatch.setattr(
        spool_mod, "os", SimpleNamespace(**{**vars(os), "write": disk_full})
    )
    with pytest.raises(OSError) as raised:
        try:
            spool.read()
        except BaseException:
            spool.close()
            raise
    assert raised.value.errno == errno.ENOSPC
