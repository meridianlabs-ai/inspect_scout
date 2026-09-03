"""Antigravity CLI conversation discovery and reading utilities.

Antigravity CLI (``agy``) stores each conversation in two places under its
data root (default ``~/.gemini/antigravity-cli``):

- ``brain/<id>/.system_generated/logs/transcript_full.jsonl`` — a plaintext
  JSONL step stream (one JSON object per step). ``transcript.jsonl`` is the
  same stream with large tool results truncated; ``transcript_full`` is
  preferred. This is the import surface.
- ``conversations/<id>.db`` — SQLite whose step payloads are encrypted at
  rest. Only its ``gen_metadata`` table (clear protobuf) is read here, as a
  best-effort source of per-generation model ids and token usage.

The ``conversation_summaries.db`` index is deliberately NOT used for
discovery: it is written lazily and observed to go stale (conversations
missing entirely, stale step counts). Conversation titles are read from
``annotations/<id>.pbtxt`` when present.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from logging import getLogger
from os import PathLike
from pathlib import Path
from typing import Any, Iterator

from inspect_ai.model import ModelUsage

logger = getLogger(__name__)

ANTIGRAVITY_SOURCE_TYPE = "antigravity"

DEFAULT_ANTIGRAVITY_DIR = Path("~/.gemini/antigravity-cli")

_TRANSCRIPT_RELPATH = Path(".system_generated") / "logs"


@dataclass
class ConversationRecord:
    """A discovered Antigravity conversation."""

    conversation_id: str
    transcript_path: Path
    db_path: Path | None
    title: str | None
    mtime: float


def discover_conversations(
    path: str | PathLike[str] | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
) -> list[ConversationRecord]:
    """Discover Antigravity conversations.

    Args:
        path: Path to search. Can be:
            - None: the default ``~/.gemini/antigravity-cli`` root
            - An Antigravity data root (a directory containing ``brain/``)
            - A ``brain`` directory
            - A single conversation directory (``brain/<id>``)
        from_time: Only yield conversations whose transcript modification
            time (``st_mtime`` — not the conversation's run time, and reset
            by ``cp``/``git checkout``/rsync) is on or after this time
        to_time: Only yield conversations whose transcript modification time
            is before this time

    Returns:
        Conversation records sorted by modification time (newest first).
    """
    search_path = (
        Path(path) if path is not None else DEFAULT_ANTIGRAVITY_DIR
    ).expanduser()

    if not search_path.exists():
        logger.warning("Path does not exist: %s", search_path)
        return []

    if (search_path / "brain").is_dir():
        data_root: Path | None = search_path
        conversation_dirs = [d for d in (search_path / "brain").iterdir() if d.is_dir()]
    elif search_path.name == "brain" and search_path.is_dir():
        data_root = search_path.parent
        conversation_dirs = [d for d in search_path.iterdir() if d.is_dir()]
    elif (search_path / _TRANSCRIPT_RELPATH).is_dir():
        # A single conversation directory.
        data_root = (
            search_path.parent.parent if search_path.parent.name == "brain" else None
        )
        conversation_dirs = [search_path]
    else:
        logger.warning("Not an Antigravity data directory: %s", search_path)
        return []

    records: list[ConversationRecord] = []
    for conv_dir in conversation_dirs:
        transcript_path = _find_transcript(conv_dir)
        if transcript_path is None:
            continue
        try:
            mtime = transcript_path.stat().st_mtime
        except OSError as e:
            logger.warning("stat failed for %s: %s", transcript_path, e)
            continue
        if from_time is not None and mtime < from_time.timestamp():
            continue
        if to_time is not None and mtime >= to_time.timestamp():
            continue

        conversation_id = conv_dir.name
        db_path: Path | None = None
        title: str | None = None
        if data_root is not None:
            candidate = data_root / "conversations" / f"{conversation_id}.db"
            if candidate.is_file():
                db_path = candidate
            title = read_title(data_root, conversation_id)

        records.append(
            ConversationRecord(
                conversation_id=conversation_id,
                transcript_path=transcript_path,
                db_path=db_path,
                title=title,
                mtime=mtime,
            )
        )

    records.sort(key=lambda r: r.mtime, reverse=True)
    return records


def _find_transcript(conv_dir: Path) -> Path | None:
    """Locate a conversation's transcript, preferring the untruncated stream."""
    logs = conv_dir / _TRANSCRIPT_RELPATH
    for name in ("transcript_full.jsonl", "transcript.jsonl"):
        candidate = logs / name
        if candidate.is_file():
            return candidate
    return None


def read_jsonl_steps(path: Path) -> list[dict[str, Any]]:
    """Read all steps from a JSONL transcript.

    Args:
        path: Path to the JSONL file

    Returns:
        List of parsed JSON steps
    """
    steps: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError as e:
                logger.warning("Invalid JSON at %s:%d: %s", path, line_num, e)
                continue
            if isinstance(parsed, dict):
                steps.append(parsed)
    return steps


_TITLE_RE = re.compile(r'title\s*:\s*"((?:[^"\\]|\\.)*)"')


def read_title(data_root: Path, conversation_id: str) -> str | None:
    """Read a conversation's title from ``annotations/<id>.pbtxt`` if present.

    Titles are set via ``/rename``. The stale ``conversation_summaries.db``
    is not consulted.
    """
    annotation = data_root / "annotations" / f"{conversation_id}.pbtxt"
    if not annotation.is_file():
        return None
    try:
        text = annotation.read_text(encoding="utf-8")
    except OSError as e:
        logger.warning("Failed to read %s: %s", annotation, e)
        return None
    match = _TITLE_RE.search(text)
    return match.group(1) if match else None


@dataclass
class GenerationInfo:
    """Best-effort per-generation metadata decoded from the conversation store."""

    model: str | None
    usage: ModelUsage | None


def read_generation_metadata(db_path: Path) -> list[GenerationInfo]:
    """Decode per-generation model ids and token usage from ``gen_metadata``.

    The conversation store's step payloads are encrypted, but its
    ``gen_metadata`` table (one row per model generation, ordinal ``idx``)
    is clear protobuf without a published schema. Field paths below were
    established empirically (agy 1.1.14–1.1.19) and verified against
    parallel community reverse-engineering (antigravity-usage, MIT):

    - ``1.19`` (string): wire model id (e.g. ``claude-sonnet-4-6``)
    - ``1.4.1`` (varint): fixed prompt-prefix tokens
    - ``1.4.2`` (varint): fresh (uncached) input tokens
    - ``1.4.5`` (varint): cached input tokens
    - ``1.4.10`` / ``1.4.3`` (varint): output tokens

    Everything here is best-effort: any failure (locked db, schema drift,
    undecodable blob) degrades to an empty list or a partial record — never
    an exception. The database is opened read-only so a live CLI is never
    blocked.
    """
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            rows = conn.execute("SELECT data FROM gen_metadata ORDER BY idx").fetchall()
        finally:
            conn.close()
    except sqlite3.Error as e:
        logger.warning("Cannot read gen_metadata from %s: %s", db_path, e)
        return []

    generations: list[GenerationInfo] = []
    for (blob,) in rows:
        if not isinstance(blob, bytes):
            generations.append(GenerationInfo(model=None, usage=None))
            continue
        generations.append(_decode_generation(blob))
    return generations


def _decode_generation(blob: bytes) -> GenerationInfo:
    try:
        outer = dict(_proto_fields(blob))
        inner_bytes = outer.get(1)
        if not isinstance(inner_bytes, bytes):
            return GenerationInfo(model=None, usage=None)
        inner = dict(_proto_fields(inner_bytes))

        model: str | None = None
        model_bytes = inner.get(19)
        if isinstance(model_bytes, bytes):
            try:
                model = model_bytes.decode("utf-8")
            except UnicodeDecodeError:
                model = None

        usage: ModelUsage | None = None
        usage_bytes = inner.get(4)
        if isinstance(usage_bytes, bytes):
            fields = dict(_proto_fields(usage_bytes))
            prefix = _int_field(fields, 1)
            fresh = _int_field(fields, 2)
            cached = _int_field(fields, 5)
            output = _int_field(fields, 10)
            if output is None:
                output = _int_field(fields, 3)
            if any(v is not None for v in (prefix, fresh, cached, output)):
                input_tokens = (prefix or 0) + (fresh or 0)
                usage = ModelUsage(
                    input_tokens=input_tokens,
                    output_tokens=output or 0,
                    total_tokens=input_tokens + (cached or 0) + (output or 0),
                    input_tokens_cache_read=cached,
                )
        return GenerationInfo(model=model, usage=usage)
    except Exception as e:
        logger.warning("Failed to decode gen_metadata blob: %s", e)
        return GenerationInfo(model=None, usage=None)


def _int_field(fields: dict[int, Any], number: int) -> int | None:
    value = fields.get(number)
    return value if isinstance(value, int) else None


def _proto_fields(data: bytes) -> Iterator[tuple[int, Any]]:
    """Walk protobuf wire-format fields as ``(field_number, value)`` pairs.

    Hand-implemented from the wire-format spec
    (https://protobuf.dev/programming-guides/encoding/) rather than adding a
    protobuf dependency: the format is frozen, and with no published schema
    for ``gen_metadata`` a library would offer only this same low-level walk.

    Varints yield ``int``, length-delimited fields yield ``bytes``; 32/64-bit
    fixed fields are skipped. Raises ``ValueError`` on malformed input (the
    caller treats that as an undecodable blob).
    """
    pos = 0
    length = len(data)
    while pos < length:
        key, pos = _read_varint(data, pos)
        field_number = key >> 3
        wire_type = key & 0x7
        if wire_type == 0:
            value, pos = _read_varint(data, pos)
            yield field_number, value
        elif wire_type == 1:
            pos += 8
        elif wire_type == 2:
            size, pos = _read_varint(data, pos)
            if pos + size > length:
                raise ValueError("length-delimited field overruns buffer")
            yield field_number, data[pos : pos + size]
            pos += size
        elif wire_type == 5:
            pos += 4
        else:
            raise ValueError(f"unsupported wire type {wire_type}")


def _read_varint(data: bytes, pos: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while True:
        if pos >= len(data):
            raise ValueError("truncated varint")
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, pos
        shift += 7
        if shift > 63:
            raise ValueError("varint too long")
