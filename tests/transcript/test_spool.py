"""Tests for spool primitives."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import pytest
from inspect_scout._transcript.json.spool import BlobSpool, ByteSpool, ItemSpool


@pytest.mark.parametrize(
    "value",
    ["hello world", "héllo — ünïcode 你好", ""],
    ids=["ascii", "unicode", "empty"],
)
def test_blob_spool_roundtrip(value: str, tmp_path: Path) -> None:
    spool = BlobSpool(tmp_path)
    try:
        spool.put("att1", value)
        spool.put(("message_pool", 0), json.dumps({"role": "user"}))
        spool.put(("message_pool", 1), json.dumps({"role": "assistant"}))
        assert spool.get("att1") == value
        assert json.loads(spool.get(("message_pool", 1)) or "") == {"role": "assistant"}
        assert spool.get("missing") is None
        assert spool.pool_len("message_pool") == 2
        assert spool.pool_len("call_pool") == 0
    finally:
        spool.close()


def test_blob_spool_no_file_left_behind(tmp_path: Path) -> None:
    spool = BlobSpool(tmp_path)
    spool.put("k", "v")
    spool.close()
    assert list(tmp_path.iterdir()) == []  # deleted when the fd closes


def test_item_spool_reiterable(tmp_path: Path) -> None:
    spool = ItemSpool(tmp_path)
    try:
        items: list[dict[str, Any]] = [
            {"role": "user", "content": "a"},
            {"role": "assistant", "content": "b"},
        ]
        for item in items:
            spool.append(item)
        assert len(spool) == 2
        assert list(spool.items()) == items
        assert list(spool.items()) == items  # second iteration identical
    finally:
        spool.close()


@pytest.mark.parametrize(
    "char_count",
    [1, 90_000, 400_000],
    ids=["single-chunk", "spans-chunks", "spans-many-chunks"],
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


def test_item_spool_many_items_per_chunk(tmp_path: Path) -> None:
    """Many items inside one internal chunk are all yielded, in order."""
    spool = ItemSpool(tmp_path)
    try:
        items: list[dict[str, Any]] = [{"n": i} for i in range(5_000)]
        for item in items:
            spool.append(item)
        assert list(spool.items()) == items
    finally:
        spool.close()


def test_item_spool_interleaved_iterations(tmp_path: Path) -> None:
    spool = ItemSpool(tmp_path)
    try:
        for i in range(3):
            spool.append({"n": i})
        it1 = spool.items()
        it2 = spool.items()
        assert next(it1) == {"n": 0}
        assert next(it2) == {"n": 0}
        assert next(it1) == {"n": 1}
        assert list(it2) == [{"n": 1}, {"n": 2}]
    finally:
        spool.close()


def _populated_blob_spool(tmp_path: Path) -> BlobSpool:
    spool = BlobSpool(tmp_path)
    spool.put("k", "v")
    return spool


def _populated_item_spool(tmp_path: Path) -> ItemSpool:
    spool = ItemSpool(tmp_path)
    spool.append({"n": 0})
    return spool


def _populated_byte_spool(tmp_path: Path) -> ByteSpool:
    spool = ByteSpool(tmp_path)
    spool.write(b"{}")
    return spool


@pytest.mark.parametrize(
    "factory,operations",
    [
        pytest.param(
            _populated_blob_spool,
            [lambda s: s.put("k2", "v2"), lambda s: s.get("k")],
            id="blob",
        ),
        pytest.param(
            _populated_item_spool,
            [lambda s: s.append({"n": 1}), lambda s: list(s.items())],
            id="item",
        ),
        pytest.param(
            _populated_byte_spool,
            [
                lambda s: s.write(b"x"),
                lambda s: s.read(),
                lambda s: list(s.chunks()),
            ],
            id="byte",
        ),
    ],
)
def test_spool_closed_lifecycle(
    factory: Callable[[Path], Any],
    operations: list[Callable[[Any], Any]],
    tmp_path: Path,
) -> None:
    """After close(), every operation raises; close() itself is idempotent."""
    spool = factory(tmp_path)
    spool.close()
    spool.close()  # idempotent
    for operation in operations:
        with pytest.raises(ValueError, match="closed"):
            operation(spool)


def test_item_spool_closed_mid_iteration_raises(tmp_path: Path) -> None:
    """Closing between internal chunk-reads must also raise.

    Not just resuming from an already-buffered chunk: items() reads in
    bounded internal chunks, so spool enough data (~1MB across many items)
    that the iterator cannot have buffered everything after yielding the
    first item -- resuming it must perform another internal read, which
    re-checks that the spool is still open.
    """
    padding = "x" * 10_000
    n_items = 110  # ~1.1MB total, well past any single internal chunk read
    spool = ItemSpool(tmp_path)
    for i in range(n_items):
        spool.append({"n": i, "pad": padding})
    it = spool.items()
    assert next(it) == {"n": 0, "pad": padding}
    spool.close()
    with pytest.raises(ValueError, match="closed"):
        while True:
            next(it)


@pytest.mark.parametrize(
    "size",
    [0, 1, 2, 1024 * 1024 - 1, 1024 * 1024, 1024 * 1024 + 1, 3 * 1024 * 1024 + 7],
    ids=[
        "empty",
        "one-byte",
        "empty-object",
        "one-below-chunk",
        "exactly-one-chunk",
        "one-above-chunk",
        "several-chunks",
    ],
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


def test_byte_spool_is_reiterable(tmp_path: Path) -> None:
    spool = ByteSpool(tmp_path)
    try:
        spool.write(b'{"k":"v"}')
        assert b"".join(spool.chunks()) == b'{"k":"v"}'
        assert b"".join(spool.chunks()) == b'{"k":"v"}'  # second pass identical
    finally:
        spool.close()


def test_byte_spool_no_file_left_behind(tmp_path: Path) -> None:
    spool = ByteSpool(tmp_path)
    spool.write(b"payload")
    spool.close()
    assert list(tmp_path.iterdir()) == []  # deleted when the fd closes
