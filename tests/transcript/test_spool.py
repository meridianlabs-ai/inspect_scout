"""Tests for spool primitives."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from inspect_scout._transcript.json.spool import BlobSpool, ItemSpool


def test_blob_spool_roundtrip(tmp_path: Path) -> None:
    spool = BlobSpool(tmp_path)
    try:
        spool.put("att1", "hello world")
        spool.put(("message_pool", 0), json.dumps({"role": "user"}))
        spool.put(("message_pool", 1), json.dumps({"role": "assistant"}))
        assert spool.get("att1") == "hello world"
        assert json.loads(spool.get(("message_pool", 1)) or "") == {
            "role": "assistant"
        }
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
