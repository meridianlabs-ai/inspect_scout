"""OpenClaw telemetry-hal transcript import functionality.

Provides the ``openclaw_telemetry_hal`` source function: an async generator that
yields ``Transcript`` objects for insertion into an Inspect Scout transcript
database.
"""

from __future__ import annotations

from datetime import datetime, timezone
from logging import getLogger
from os import PathLike
from pathlib import Path
from typing import TYPE_CHECKING, Any, AsyncIterator, Iterable

import anyio.to_thread
from inspect_ai.event import ModelEvent
from inspect_ai.model import stable_message_ids

from .client import (
    OPENCLAW_TELEMETRY_HAL_SOURCE_TYPE,
    discover_telemetry_files,
    read_telemetry_events,
)
from .events import build_content
from .extraction import tokens_from_usage
from .parse import parse_telemetry

if TYPE_CHECKING:
    from inspect_scout import Transcript

logger = getLogger(__name__)


async def openclaw_telemetry_hal(
    path: str | PathLike[str],
) -> AsyncIterator["Transcript"]:
    """Read transcripts from ``openclaw-telemetry-hal`` JSONL telemetry files.

    These are the JSONL telemetry files produced by the
    https://github.com/sage-princeton/openclaw-telemetry-hal plugin (a fork of
    ``knostic/openclaw-telemetry``). The ``telemetry-hal`` fork is required: it writes full
    message/prompt content, whereas the ``knostic`` fork records metadata only
    (lengths, timing) and would import as empty-bodied transcripts.

    These are **NOT** native OpenClaw session files (the bundles under
    ``~/.openclaw/``), which are an entirely different, richer schema. Importing
    those is a separate source, not yet implemented; when it lands it will be a
    distinct entry point and ``source_type`` so the two can coexist in one
    database.

    Args:
        path: Path to a telemetry directory or a specific ``.jsonl`` file.

    Yields:
        Transcript objects ready for insertion into a transcript database.
    """
    telemetry_files = discover_telemetry_files(path)

    if not telemetry_files:
        logger.warning("No OpenClaw telemetry files found at %s", path)
        return

    for telemetry_file in telemetry_files:
        # Reading/parsing a file is synchronous and CPU-bound; run it in a
        # worker thread so it doesn't pin the event loop for the whole file (the
        # import progress display keeps refreshing). This does not make the
        # in-flight file interruptible: the worker is non-daemon and runs to
        # completion. abandon_on_cancel=True only lets this await raise promptly
        # on cancellation instead of blocking until that worker finishes.
        transcript = await anyio.to_thread.run_sync(
            _process_telemetry_file, telemetry_file, abandon_on_cancel=True
        )
        if transcript is not None:
            yield transcript


def _process_telemetry_file(telemetry_file: Path) -> "Transcript" | None:
    """Process a single OpenClaw telemetry file into a transcript.

    Args:
        telemetry_file: Path to the telemetry file.

    Returns:
        A Transcript object, or None if no transcript could be created.
    """
    return _create_transcript(read_telemetry_events(telemetry_file), telemetry_file)


def _create_transcript(
    raw_events: Iterable[dict[str, Any]],
    telemetry_file: Path,
) -> "Transcript" | None:
    """Create a Transcript from raw OpenClaw telemetry events.

    Args:
        raw_events: Raw events read from the telemetry file (consumed once). An
            empty stream (e.g. an empty file) yields no orchestrator turns and so
            returns ``None``.
        telemetry_file: Path to the source telemetry file.

    Returns:
        A Transcript object, or None if no orchestrator turns were found.
    """
    from inspect_scout import Transcript

    parse = parse_telemetry(raw_events)
    if not parse.orchestrator_turns:
        logger.warning(
            "No orchestrator turns found in %s. Make sure it is a file "
            "produced by the openclaw-telemetry-hal plugin (not a native "
            "OpenClaw session).",
            telemetry_file,
        )
        return None

    events, messages = build_content(parse)

    # Apply stable message IDs across model events and the message thread.
    apply_ids = stable_message_ids()
    for event in events:
        if isinstance(event, ModelEvent):
            apply_ids(event)
    apply_ids(messages)

    # Timing spans the conversation (user prompts + orchestrator turns).
    timestamps = sorted(
        int(t.get("timestamp") or 0)
        for t in (*parse.user_turns, *parse.orchestrator_turns)
        if t.get("timestamp")
    )
    total_time: float | None = None
    date: str | None = None
    if timestamps:
        total_time = (timestamps[-1] - timestamps[0]) / 1000.0
        date = datetime.fromtimestamp(
            timestamps[0] / 1000.0, tz=timezone.utc
        ).isoformat()

    # Identity: the sessionKey yields a session/surface id, but for the telegram
    # surface that is a chat id shared across runs (see ``session_id_from_session_key``),
    # so it is not unique per run on its own. Combine it with the run's earliest
    # event timestamp to get a re-import-stable, run-unique transcript id; fall
    # back to the session id alone, then the file stem. The bare session id stays
    # available as ``source_id``.
    first_ts = timestamps[0] if timestamps else None
    if parse.session_id and first_ts is not None:
        transcript_id = f"{parse.session_id}-{first_ts}"
    else:
        transcript_id = parse.session_id or telemetry_file.stem

    # Token total is the billable per-call spend (input + output + cache read +
    # cache write) summed over the deduped orchestrator AND sub-agent turns —
    # the same convention as the other importers (cache reads are billed on
    # every call, so they must be counted).
    total_tokens = sum(
        tokens_from_usage(t.get("usage") or {})
        for t in (
            *parse.orchestrator_turns,
            *(turn for sa in parse.subagents for turn in sa.turns),
        )
    )

    metadata = {
        "session_id": parse.session_id,
        "n_subagents": len(parse.subagents),
        "subagent_session_keys": [sa.session_key for sa in parse.subagents],
    }

    return Transcript(
        transcript_id=transcript_id,
        source_type=OPENCLAW_TELEMETRY_HAL_SOURCE_TYPE,
        source_id=parse.session_id,
        source_uri=str(telemetry_file),
        date=date,
        task_set=None,
        task_id=transcript_id,
        task_repeat=1,
        # The agent that produced the run, not the importer/format: a future
        # native-session importer would carry this same ``agent`` with a
        # different ``source_type``.
        agent="openclaw",
        agent_args=None,
        model=parse.model_name,
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
