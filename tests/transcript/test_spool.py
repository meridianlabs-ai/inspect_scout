"""Tests for spool primitives."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from inspect_scout._transcript.json.spool import BlobSpool, ItemSpool


def test_blob_spool_roundtrip(tmp_path: Path) -> None:
    spool = BlobSpool(tmp_path)
    try:
        spool.put("att1", "hello world")
        spool.put(("message_pool", 0), json.dumps({"role": "user"}))
        spool.put(("message_pool", 1), json.dumps({"role": "assistant"}))
        assert spool.get("att1") == "hello world"
        assert json.loads(spool.get(("message_pool", 1)) or "") == {"role": "assistant"}
        assert spool.get("missing") is None
        assert spool.pool_len("message_pool") == 2
        assert spool.pool_len("call_pool") == 0
    finally:
        spool.close()


def test_blob_spool_unicode(tmp_path: Path) -> None:
    spool = BlobSpool(tmp_path)
    try:
        spool.put("u", "héllo — ünïcode 你好")
        assert spool.get("u") == "héllo — ünïcode 你好"
    finally:
        spool.close()


def test_blob_spool_no_file_left_behind(tmp_path: Path) -> None:
    spool = BlobSpool(tmp_path)
    spool.put("k", "v")
    spool.close()
    assert list(tmp_path.iterdir()) == []  # unlinked on creation (POSIX)


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


def test_close_idempotent(tmp_path: Path) -> None:
    spool = BlobSpool(tmp_path)
    spool.close()
    spool.close()
    ispool = ItemSpool(tmp_path)
    ispool.close()
    ispool.close()


def test_blob_spool_closed_guards_raise(tmp_path: Path) -> None:
    spool = BlobSpool(tmp_path)
    spool.put("k", "v")
    spool.close()
    with pytest.raises(ValueError, match="closed"):
        spool.put("k2", "v2")
    with pytest.raises(ValueError, match="closed"):
        spool.get("k")


def test_item_spool_closed_guards_raise(tmp_path: Path) -> None:
    spool = ItemSpool(tmp_path)
    spool.append({"n": 0})
    spool.close()
    with pytest.raises(ValueError, match="closed"):
        spool.append({"n": 1})
    with pytest.raises(ValueError, match="closed"):
        list(spool.items())


def test_item_spool_closed_mid_iteration_raises(tmp_path: Path) -> None:
    """Closing between internal chunk-reads must also raise.

    Not just resuming from an already-buffered chunk: items() reads in
    256KiB chunks; pad each item so the first chunk read
    yields exactly one item's worth of buffer, forcing a second internal
    pread (which re-checks self._fd) to fetch the next item.
    """
    # Sized so the JSONL line (with trailing newline) for item 0 is exactly
    # one 256KiB chunk -- item 0 is fully satisfied by the first pread, and
    # fetching item 1 requires a second pread that re-checks self._fd.
    chunk_size = 256 * 1024
    prefix_len = len(json.dumps({"n": 0, "pad": ""}, separators=(",", ":"))) + 1
    padded = "x" * (chunk_size - prefix_len)
    spool = ItemSpool(tmp_path)
    spool.append({"n": 0, "pad": padded})
    spool.append({"n": 1})
    it = spool.items()
    assert next(it) == {"n": 0, "pad": padded}
    spool.close()
    with pytest.raises(ValueError, match="closed"):
        next(it)
