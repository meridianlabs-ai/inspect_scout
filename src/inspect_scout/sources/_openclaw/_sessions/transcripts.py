"""OpenClaw native session transcript import functionality.

Provides the ``openclaw`` source function: an async generator that yields
``Transcript`` objects for insertion into an Inspect Scout transcript
database. See ``design/openclaw-sessions.md``.
"""

from __future__ import annotations

from datetime import datetime
from logging import getLogger
from os import PathLike
from pathlib import Path
from typing import TYPE_CHECKING, Any, AsyncIterator

from inspect_ai.event import Event, ModelEvent, SpanBeginEvent
from inspect_ai.model import stable_message_ids

from .client import (
    OPENCLAW_SOURCE_TYPE,
    RegistryEntry,
    discover_session_files,
    entry_for_session_id,
    load_registry,
    read_session_records,
)
from .events import BuildContext, build_content
from .parse import AssistantTurn, ParsedSession, UserTurn, parse_session

if TYPE_CHECKING:
    from inspect_scout import Transcript

logger = getLogger(__name__)


async def openclaw(
    path: str | PathLike[str] | None = None,
    session_id: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    limit: int | None = None,
) -> AsyncIterator["Transcript"]:
    """Read transcripts from native OpenClaw session files.

    These are the session bundles OpenClaw itself writes under
    ``~/.openclaw/agents/<agent>/sessions/`` — one ``<sessionId>.jsonl`` per
    session plus a shared ``sessions.json`` registry. Each non-sub-agent
    session file becomes one transcript; sessions spawned as sub-agents are
    nested inside their parent transcript as agent spans (and are not yielded
    standalone). Without a ``sessions.json`` alongside the files, topology is
    unknown: every file imports as a standalone transcript.

    This is distinct from ``openclaw_telemetry_hal``, which imports the JSONL
    telemetry written by the third-party ``openclaw-telemetry-hal`` plugin.

    Args:
        path: Path to an OpenClaw root (``~/.openclaw``), an agent sessions
            directory, or a specific session ``.jsonl`` file. If None, scans
            all agents under ``~/.openclaw/agents/``.
        session_id: Specific session id to import. If this is a spawned
            sub-agent session, import it standalone.
        from_time: Only import sessions modified on or after this time.
        to_time: Only import sessions modified before this time.
        limit: Maximum number of transcripts to yield.

    Yields:
        Transcript objects ready for insertion into a transcript database.
    """
    session_files = discover_session_files(path, session_id, from_time, to_time)
    if not session_files:
        logger.info("No OpenClaw session files found")
        return

    explicit_file = path is not None and Path(path).expanduser().is_file()
    registries: dict[Path, dict[str, RegistryEntry] | None] = {}
    n = 0
    for session_file in session_files:
        directory = session_file.parent
        if directory not in registries:
            registries[directory] = load_registry(directory)
            if registries[directory] is None:
                logger.warning(
                    "No sessions.json found in %s: importing every session "
                    "file standalone (no sub-agent spans)",
                    directory,
                )
        registry = registries[directory]

        # Sub-agent sessions are nested in their parent's transcript during
        # bulk import, but an explicit file or session_id request imports that
        # session standalone.
        if not explicit_file and session_id is None and registry is not None:
            entry = entry_for_session_id(registry, session_file.stem)
            if entry is not None and entry.spawned_by:
                continue

        transcript = _process_session_file(session_file, registry)
        if transcript is not None:
            yield transcript
            n += 1
            if limit is not None and n >= limit:
                return


def _process_session_file(
    session_file: Path, registry: dict[str, RegistryEntry] | None
) -> "Transcript | None":
    """Process a single session file into a transcript (None if empty)."""
    from inspect_scout import Transcript

    raw = read_session_records(session_file)
    if not raw:
        return None
    parsed = parse_session(raw, str(session_file))

    session_id = parsed.header.session_id or session_file.stem
    if parsed.header.session_id and parsed.header.session_id != session_file.stem:
        logger.warning(
            "OpenClaw session id %s does not match file name %s; using the header id",
            parsed.header.session_id,
            session_file.name,
        )

    ctx = BuildContext(sessions_dir=session_file.parent, registry=registry)
    events, messages = build_content(parsed, ctx)
    if not messages:
        logger.info("OpenClaw session %s has no messages; skipping", session_file)
        return None

    # Stable ids across model events and the message thread (as in the
    # Claude Code and telemetry-hal importers).
    apply_ids = stable_message_ids()
    for event in events:
        if isinstance(event, ModelEvent):
            apply_ids(event)
    apply_ids(messages)

    # Billable per-call spend summed over every model call (orchestrator and
    # sub-agents): OpenClaw's totalTokens == input + output + cacheRead +
    # cacheWrite per turn, the convention shared by the other importers.
    total_tokens = sum(
        event.output.usage.total_tokens
        for event in events
        if isinstance(event, ModelEvent) and event.output.usage is not None
    )

    date = _first_message_date(parsed)
    total_time = _total_time(events, parsed)

    # Direct children only: root-thread events carry span_id=None, while a
    # nested sub-agent's SpanBeginEvent carries its parent span's id (nested
    # sub-agents appear inside their parent's span, not in this count).
    agent_spans = [
        e
        for e in events
        if isinstance(e, SpanBeginEvent) and e.type == "agent" and e.span_id is None
    ]
    entry = entry_for_session_id(registry, session_id) if registry else None

    metadata: dict[str, Any] = {
        "cwd": parsed.header.cwd,
        "session_version": parsed.header.version,
        "n_subagents": len(agent_spans),
        "subagent_session_ids": [
            sid for e in agent_spans if (sid := (e.metadata or {}).get("session_id"))
        ],
    }
    if entry is not None:
        metadata.update(
            {
                "session_key": entry.session_key,
                "parent_session_key": entry.parent_session_key,
                "label": entry.label,
                "status": entry.status,
                "channel": entry.raw.get("lastChannel"),
                "origin": entry.raw.get("origin"),
                "system_prompt_report": entry.raw.get("systemPromptReport"),
            }
        )
    metadata = {k: v for k, v in metadata.items() if v is not None}

    return Transcript(
        transcript_id=session_id,
        source_type=OPENCLAW_SOURCE_TYPE,
        source_id=session_id,
        source_uri=str(session_file),
        date=date,
        task_set=None,
        task_id=session_id,
        task_repeat=1,
        # The agent that produced the run, not the importer/format — the
        # telemetry-hal importer carries the same value.
        agent="openclaw",
        agent_args=None,
        model=parsed.model,
        model_options=None,
        score=None,
        success=None,
        message_count=len(messages),
        total_tokens=total_tokens if total_tokens > 0 else None,
        total_time=total_time if total_time and total_time > 0 else None,
        error=None,
        limit=None,
        messages=messages,
        events=events,
        metadata=metadata,
    )


def _first_message_date(parsed: ParsedSession) -> str | None:
    """The transcript's ``date``: the first actual message's timestamp.

    A leading ``model_change``/``thinking_level_change`` record (config
    bookkeeping, not a message) should not win over the first real
    ``UserTurn``/``AssistantTurn`` — falls back to the first record, then
    ``None``, when the session has no message records at all.
    """
    for record in parsed.records:
        if isinstance(record, (UserTurn, AssistantTurn)):
            return record.timestamp.isoformat()
    if parsed.records:
        return parsed.records[0].timestamp.isoformat()
    return None


def _total_time(events: list[Event], parsed: ParsedSession) -> float | None:
    """Wall clock minus idle time from the built timeline.

    Falls back to first->last record timestamps when the timeline yields no
    root content (mirrors the Claude Code importer's guard).
    """
    from inspect_ai.event import timeline_build

    timeline = timeline_build(events)
    root = timeline.root
    if root.content:
        wall_clock = (root.end_time() - root.start_time()).total_seconds()
        return wall_clock - root.idle_time()
    timestamps = [record.timestamp for record in parsed.records]
    if len(timestamps) >= 2:
        return (max(timestamps) - min(timestamps)).total_seconds()
    return None
