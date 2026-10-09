"""Shared builders for the Antigravity source tests."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def varint(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def varint_field(number: int, value: int) -> bytes:
    return varint(number << 3) + varint(value)


def len_field(number: int, payload: bytes) -> bytes:
    return varint((number << 3) | 2) + varint(len(payload)) + payload


def generation_blob(
    model: str, prefix: int, fresh: int, cached: int, output: int
) -> bytes:
    """Build a ``gen_metadata`` blob with the empirically-established field paths."""
    usage = (
        varint_field(1, prefix)
        + varint_field(2, fresh)
        + varint_field(5, cached)
        + varint_field(10, output)
    )
    inner = len_field(4, usage) + len_field(19, model.encode("utf-8"))
    return len_field(1, inner)


def write_generation_db(db_path: Path, blobs: list[bytes]) -> None:
    """Create a ``conversations/<id>.db`` with the given ``gen_metadata`` rows."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "CREATE TABLE gen_metadata (idx integer, data blob, "
            "size integer NOT NULL DEFAULT 0, PRIMARY KEY (idx))"
        )
        for idx, blob in enumerate(blobs):
            conn.execute(
                "INSERT INTO gen_metadata (idx, data) VALUES (?, ?)", (idx, blob)
            )
        conn.commit()
    finally:
        conn.close()
