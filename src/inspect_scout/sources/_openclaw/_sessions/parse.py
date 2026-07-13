"""OpenClaw native session record parsing.

Turns the raw JSONL records of one session file into a typed
:class:`ParsedSession`. Records are kept in file order (append order, hence
chronological). All schema strictness lives here: unknown record types,
unknown message roles, and divergent branches fail the import loudly rather
than silently dropping content — see ``design/openclaw-sessions.md``.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from logging import getLogger
from typing import Any, Literal

logger = getLogger(__name__)

_EPOCH = datetime.fromtimestamp(0, tz=timezone.utc)


class UnsupportedSessionError(ValueError):
    """A session file this importer cannot turn into a transcript.

    Raised for the parser's deliberate rejections — a missing/duplicate
    ``session`` header, an unknown record type or message role, a divergent
    (branched) thread tree, an assistant turn without a model, or unmappable
    content. Subclasses ``ValueError`` so existing ``except ValueError`` callers
    keep working, while a bulk directory scan can catch this narrow type to skip
    one bad file without swallowing an unrelated ``ValueError`` as if it meant
    the file was unsupported.
    """


@dataclass(frozen=True)
class SessionHeader:
    """The ``session`` record that opens every session file."""

    session_id: str
    version: int | None
    timestamp: datetime | None
    cwd: str | None


@dataclass(frozen=True)
class UserTurn:
    """A user message (``injected=True`` for runtime ``custom_message``s)."""

    content: Any
    timestamp: datetime
    injected: bool = False


@dataclass(frozen=True)
class AssistantTurn:
    """An assistant message with its per-turn model and usage."""

    content: Any
    model: str
    usage: dict[str, Any]
    timestamp: datetime
    stop_reason: str | None = None
    response_id: str | None = None


@dataclass(frozen=True)
class ToolResultMsg:
    """A ``toolResult`` message, keyed by ``toolCallId``."""

    tool_call_id: str
    tool_name: str | None
    content: Any
    is_error: bool | None
    details: dict[str, Any] | None
    timestamp: datetime


@dataclass(frozen=True)
class CompactionRecord:
    """A ``compaction`` record (context compaction with summary)."""

    summary: str | None
    first_kept_entry_id: str | None
    tokens_before: int | None
    details: dict[str, Any] | None
    from_hook: bool | None
    timestamp: datetime


@dataclass(frozen=True)
class ConfigChange:
    """A ``model_change`` or ``thinking_level_change`` record."""

    change: Literal["model_change", "thinking_level_change"]
    data: dict[str, Any]
    timestamp: datetime


SessionRecord = UserTurn | AssistantTurn | CompactionRecord | ConfigChange


@dataclass
class ParsedSession:
    """One session file, parsed: the thread records plus id-keyed tool results.

    ``records`` holds the content-bearing thread in file order; ``toolResult``
    messages are not in it — they are joined back to their calls via
    ``result_by_callid`` when events are built. ``model`` is the most recent
    assistant turn's model, seeded by ``model_change`` when no turn exists.
    """

    header: SessionHeader
    records: list[SessionRecord]
    result_by_callid: dict[str, ToolResultMsg]
    model: str | None


def parse_session(raw_records: list[dict[str, Any]], source: str) -> ParsedSession:
    """Parse one session file's raw records.

    Args:
        raw_records: Records as read by ``read_session_records`` (file order).
        source: Where the records came from, for error messages.

    Raises:
        UnsupportedSessionError: On an empty record list, a missing/duplicate
            ``session`` header, an unknown record type, an unknown message role,
            or a divergent branch (two thread records sharing a parent).
    """
    if not raw_records:
        raise UnsupportedSessionError(f"Empty OpenClaw session: {source}")
    header_rec = raw_records[0]
    if header_rec.get("type") != "session":
        raise UnsupportedSessionError(
            f"Expected a 'session' header as the first record of {source}, "
            f"got '{header_rec.get('type')}'"
        )
    header = SessionHeader(
        # An empty id is accepted here; identity fallback/cross-check (e.g. to
        # the session file's stem) is deferred to the transcripts layer.
        session_id=str(header_rec.get("id") or ""),
        version=_opt_int(header_rec.get("version")),
        timestamp=_parse_iso(header_rec.get("timestamp")),
        cwd=str(header_rec["cwd"]) if header_rec.get("cwd") else None,
    )

    records: list[SessionRecord] = []
    result_by_callid: dict[str, ToolResultMsg] = {}
    model: str | None = None
    # Divergence check: count thread records (message/compaction — not
    # leaf/custom bookkeeping) claiming each parent. >1 means the tree
    # branches, which we do not know how to linearize — fail, don't guess.
    thread_children: Counter[str] = Counter()
    last_ts = header.timestamp or _EPOCH

    for rec in raw_records[1:]:
        rtype = rec.get("type")
        ts = _parse_iso(rec.get("timestamp")) or last_ts
        last_ts = ts

        if rtype == "message":
            _count_parent(rec, thread_children)
            msg = rec.get("message") or {}
            role = msg.get("role")
            # The record-level (ISO) timestamp is the append-order log time and
            # is reliably monotonic; the message-level (epoch-ms) timestamp can
            # lag it (e.g. captured when content was generated/queued, not when
            # appended — observed on injected user messages). Record order, not
            # message time, is what "chronological" means for this stream, so
            # `ts` (record-level) is used for ordering; message-level time is
            # not currently surfaced on the parsed types.
            if role == "user":
                records.append(UserTurn(content=msg.get("content"), timestamp=ts))
            elif role == "assistant":
                turn_model = msg.get("model")
                if not turn_model:
                    raise UnsupportedSessionError(
                        f"Assistant message without a model in {source}"
                    )
                model = str(turn_model)
                _validate_assistant_content(msg.get("content"), source)
                records.append(
                    AssistantTurn(
                        content=msg.get("content"),
                        model=model,
                        usage=msg.get("usage") or {},
                        timestamp=ts,
                        stop_reason=str(msg["stopReason"])
                        if msg.get("stopReason")
                        else None,
                        response_id=str(msg["responseId"])
                        if msg.get("responseId")
                        else None,
                    )
                )
            elif role == "toolResult":
                details = msg.get("details")
                result = ToolResultMsg(
                    tool_call_id=str(msg.get("toolCallId") or ""),
                    tool_name=str(msg["toolName"]) if msg.get("toolName") else None,
                    content=msg.get("content"),
                    is_error=msg.get("isError")
                    if isinstance(msg.get("isError"), bool)
                    else None,
                    details=details if isinstance(details, dict) else None,
                    timestamp=ts,
                )
                if result.tool_call_id:
                    if result.tool_call_id in result_by_callid:
                        # Native records are append-only, so a re-emission is
                        # the authoritative final result — keep the last one.
                        logger.warning(
                            "Duplicate toolCallId '%s' in %s; keeping the last result",
                            result.tool_call_id,
                            source,
                        )
                    result_by_callid[result.tool_call_id] = result
                else:
                    # Without a toolCallId the result cannot be joined to any
                    # call — drop it, but observably.
                    logger.warning(
                        "toolResult without a toolCallId in %s; dropping it",
                        source,
                    )
            else:
                raise UnsupportedSessionError(
                    f"Unknown OpenClaw message role '{role}' in {source}"
                )
        elif rtype == "custom_message":
            records.append(
                UserTurn(content=rec.get("content"), timestamp=ts, injected=True)
            )
        elif rtype == "compaction":
            _count_parent(rec, thread_children)
            details = rec.get("details")
            records.append(
                CompactionRecord(
                    summary=str(rec["summary"]) if rec.get("summary") else None,
                    first_kept_entry_id=str(rec["firstKeptEntryId"])
                    if rec.get("firstKeptEntryId")
                    else None,
                    tokens_before=_opt_int(rec.get("tokensBefore")),
                    details=details if isinstance(details, dict) else None,
                    from_hook=rec.get("fromHook")
                    if isinstance(rec.get("fromHook"), bool)
                    else None,
                    timestamp=ts,
                )
            )
        elif rtype == "model_change":
            if model is None and rec.get("modelId"):
                model = str(rec["modelId"])
            records.append(
                ConfigChange(
                    change="model_change",
                    data={"provider": rec.get("provider"), "model": rec.get("modelId")},
                    timestamp=ts,
                )
            )
        elif rtype == "thinking_level_change":
            records.append(
                ConfigChange(
                    change="thinking_level_change",
                    data={"thinking_level": rec.get("thinkingLevel")},
                    timestamp=ts,
                )
            )
        elif rtype in ("custom", "leaf"):
            continue  # run-boundary / branch bookkeeping — no content
        elif rtype == "session":
            raise UnsupportedSessionError(
                f"Unexpected second 'session' header in {source}"
            )
        else:
            raise UnsupportedSessionError(
                f"Unknown OpenClaw session record type '{rtype}' in {source}. "
                "This importer fails on unrecognized records rather than "
                "dropping them; please report the record type."
            )

    divergent = sorted(p for p, n in thread_children.items() if n > 1)
    if divergent:
        raise UnsupportedSessionError(
            f"OpenClaw session {source} has divergent branches at parent "
            f"id(s) {divergent}; branch linearization is not supported"
        )

    return ParsedSession(
        header=header,
        records=records,
        result_by_callid=result_by_callid,
        model=model,
    )


_KNOWN_ASSISTANT_BLOCK_TYPES = {"text", "thinking", "image", "toolCall"}


def _validate_assistant_content(content: Any, source: str) -> None:
    """Fail loudly on assistant content this importer can't map.

    The ``extraction.content_blocks`` helper silently drops shapes it
    does not recognize, but the sessions design
    promises unmappable assistant content fails the import — see
    ``design/openclaw-sessions.md``. ``None`` and ``str`` content are mappable;
    any other non-list shape, any non-``str``/``dict`` block, and any unknown
    block type are not.
    """
    if content is None or isinstance(content, str):
        return
    if not isinstance(content, list):
        raise UnsupportedSessionError(
            f"Unsupported OpenClaw assistant content shape "
            f"'{type(content).__name__}' in {source}"
        )
    for block in content:
        if isinstance(block, str):
            continue
        if not isinstance(block, dict):
            raise UnsupportedSessionError(
                f"Unsupported OpenClaw assistant content block "
                f"'{type(block).__name__}' in {source}"
            )
        btype = block.get("type")
        if btype not in _KNOWN_ASSISTANT_BLOCK_TYPES:
            raise UnsupportedSessionError(
                f"Unknown OpenClaw assistant content block type '{btype}' in {source}"
            )


def _count_parent(rec: dict[str, Any], counter: Counter[str]) -> None:
    parent_id = rec.get("parentId")
    if isinstance(parent_id, str) and parent_id:
        counter[parent_id] += 1


def _opt_int(value: Any) -> int | None:
    """Coerce a bookkeeping number to ``int`` (``None`` on bad input)."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_iso(value: Any) -> datetime | None:
    """Parse a record-level ISO-8601 timestamp (returns aware UTC)."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
