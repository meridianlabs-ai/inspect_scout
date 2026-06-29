"""ATIF transcript import functionality.

This module provides functions to import transcripts from ATIF
trajectory.json files into an Inspect Scout transcript database.

ATIF files are produced by Harbor's installed agents (claude_code, codex,
goose, opencode, openhands, gemini_cli, mini_swe_agent, swe_agent,
terminus_2) — one `trajectory.json` per run. Subagent trajectories live
in sibling files referenced via `subagent_trajectory_ref.trajectory_path`.
"""

from __future__ import annotations

from datetime import datetime
from logging import getLogger
from os import PathLike
from pathlib import Path
from typing import TYPE_CHECKING, Any, AsyncIterator

from inspect_ai.event import (
    Event,
    ModelEvent,
    SpanBeginEvent,
    SpanEndEvent,
    timeline_build,
)
from inspect_ai.model import ChatMessage, stable_message_ids
from pydantic import ValidationError

from .client import (
    ATIF_SOURCE_TYPE,
    discover_trajectory_files,
    import_trajectory_model,
)
from .events import (
    _parse_timestamp,
    step_to_messages,
    to_compaction_event,
    to_model_event,
    utcnow,
)

if TYPE_CHECKING:
    from harbor.models.trajectories import SubagentTrajectoryRef, Trajectory

    from inspect_scout import Transcript

logger = getLogger(__name__)


async def atif(
    path: str | PathLike[str] | None = None,
    session_id: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    limit: int | None = None,
) -> AsyncIterator["Transcript"]:
    """Read transcripts from ATIF JSON files.

    Args:
        path: Path to a directory containing trajectory.json files, or a
            specific trajectory file. If None, no files are discovered
            (no default location)
        session_id: Specific session ID to import
        from_time: Only fetch trajectories modified on or after this time
        to_time: Only fetch trajectories modified before this time
        limit: Maximum number of transcripts to yield

    Yields:
        Transcript objects ready for insertion into transcript database
    """
    trajectory_model = import_trajectory_model()

    trajectory_files = list(
        discover_trajectory_files(path=path, from_time=from_time, to_time=to_time)
    )
    if not trajectory_files:
        logger.info("No ATIF trajectory files found")
        return

    # Parse every discovered file once, up front. We need all subagent
    # references before yielding anything: a subagent file may sort ahead of
    # its parent in mtime order, and subagent trajectories are inlined into
    # their parent's span (see `_create_subagent_span_events`), so they must
    # not also be yielded as standalone transcripts (which would double-index
    # their events). Assumed layout: a parent trajectory and the subagent
    # files it references live in the same directory tree.
    parsed: list[tuple[Path, "Trajectory"]] = []
    subagent_paths: set[Path] = set()
    for f in trajectory_files:
        try:
            trajectory = trajectory_model.model_validate_json(f.read_text())
        except (OSError, ValidationError) as e:
            logger.warning("Skipping non-ATIF or unreadable file %s: %s", f, e)
            continue
        parsed.append((f, trajectory))
        subagent_paths |= _subagent_ref_paths(trajectory, parent_path=f)

    count = 0
    for f, trajectory in parsed:
        if limit is not None and count >= limit:
            return

        if f.resolve() in subagent_paths:
            # Inlined as a span inside its parent; don't double-index.
            continue

        if session_id is not None and trajectory.session_id != session_id:
            continue

        yield _create_transcript(trajectory, source_uri=str(f))
        count += 1


def _subagent_ref_paths(
    trajectory: "Trajectory",
    parent_path: Path,
) -> set[Path]:
    """Collect resolved paths of subagent trajectories referenced by a parent.

    Used to skip files that are inlined into a parent's span so they are not
    also yielded as standalone transcripts.
    """
    paths: set[Path] = set()
    for step in trajectory.steps:
        if step.observation is None:
            continue
        for result in step.observation.results:
            for ref in result.subagent_trajectory_ref or []:
                if ref.trajectory_path:
                    paths.add((parent_path.parent / ref.trajectory_path).resolve())
    return paths


def _create_transcript(
    trajectory: "Trajectory",
    source_uri: str | None = None,
    *,
    max_depth: int = 5,
) -> "Transcript":
    """Create a Transcript from a Harbor Trajectory.

    Args:
        trajectory: A validated ATIF Trajectory
        source_uri: URI pointing to the trajectory's on-disk location, also
            used as the anchor for resolving relative subagent
            trajectory_path values
        max_depth: Recursion bound for inlining subagent trajectories

    Returns:
        Transcript object
    """
    from inspect_scout import Transcript

    parent_path: Path | None = Path(source_uri) if source_uri else None

    # Pre-scan tool_calls so observations can resolve `function` from
    # `source_call_id` regardless of whether the calling step came earlier
    # in the same trajectory or in a continuation.
    tool_call_funcs: dict[str, str] = {}
    for step in trajectory.steps:
        if step.tool_calls:
            for tc in step.tool_calls:
                tool_call_funcs[tc.tool_call_id] = tc.function_name

    # Convert steps to messages and events
    messages: list[ChatMessage] = []
    events: list[Event] = []
    has_copied_context = False

    for step in trajectory.steps:
        if step.is_copied_context:
            has_copied_context = True

        if (
            step.source == "system"
            and step.extra
            and "context_management" in step.extra
        ):
            # Compaction step → emit CompactionEvent in lieu of a system
            # message. Subagent inlining still runs below — terminus_2's
            # summarization-handoff step carries `subagent_trajectory_ref`
            # pointing to the subagents that did the summarization.
            #
            # KNOWN LIMITATION: ATIF RFC 0001 §VII says that after a
            # `boundary="replace"` compaction, a subsequent step's effective
            # input context is the boundary's observation content + later
            # turns only, not the pre-boundary steps. We currently keep
            # accumulating `messages` across the boundary, so a synthesized
            # `ModelEvent.input` for any post-boundary step would include
            # pre-compaction turns. Harbor's current fixtures place the
            # compaction step last (no post-boundary step), so this is not yet
            # observable; faithful reconstruction is left as a follow-up.
            events.append(to_compaction_event(step))
        else:
            new_msgs = step_to_messages(step, tool_call_funcs, parent_path=parent_path)
            # Synthesize a ModelEvent BEFORE adding the assistant message to
            # the running history, so `event.input` reflects what the model
            # actually saw. `to_model_event` returns None for steps without
            # metrics (no real LLM call).
            if step.source == "agent":
                event = to_model_event(
                    step,
                    prior_messages=messages,
                    new_messages=new_msgs,
                )
                if event is not None:
                    events.append(event)
            messages.extend(new_msgs)

        # Subagent inlining: when this step's observations carry
        # `subagent_trajectory_ref` entries, recursively convert each
        # referenced trajectory and inline its events wrapped in a
        # `SpanBeginEvent`(type="agent") / `SpanEndEvent` pair.
        if step.observation is not None and parent_path is not None:
            for result in step.observation.results:
                if not result.subagent_trajectory_ref:
                    continue
                for ref in result.subagent_trajectory_ref:
                    events.extend(
                        _create_subagent_span_events(
                            ref,
                            parent_path=parent_path,
                            max_depth=max_depth,
                        )
                    )

    # Apply stable message IDs
    apply_ids = stable_message_ids()
    for evt in events:
        if isinstance(evt, ModelEvent):
            apply_ids(evt)
    apply_ids(messages)

    # Extract metadata
    metadata: dict[str, Any] = {
        "schema_version": trajectory.schema_version,
    }
    if trajectory.continued_trajectory_ref:
        metadata["continued_trajectory_ref"] = trajectory.continued_trajectory_ref
    if has_copied_context:
        metadata["has_copied_context"] = True
    if trajectory.notes:
        metadata["notes"] = trajectory.notes

    # Token totals
    total_tokens: int | None = None
    if trajectory.final_metrics is not None:
        prompt = trajectory.final_metrics.total_prompt_tokens or 0
        completion = trajectory.final_metrics.total_completion_tokens or 0
        total = prompt + completion
        total_tokens = total if total > 0 else None

    # Date (from first step timestamp)
    first_timestamp = trajectory.steps[0].timestamp if trajectory.steps else None

    # Total time (wall clock minus idle gaps, derived from event timeline)
    total_time: float | None = None
    if events:
        timeline = timeline_build(events)
        root = timeline.root
        wall_clock = (root.end_time() - root.start_time()).total_seconds()
        total_time = wall_clock - root.idle_time()

    # Generate transcript ID. `source_uri` (the on-disk path) is always set on
    # the real import path and is unique per file, so the `"unknown"` fallback
    # is only reachable for an in-memory trajectory with no ids and no uri.
    transcript_id = (
        trajectory.session_id or trajectory.trajectory_id or source_uri or "unknown"
    )
    return Transcript(
        transcript_id=transcript_id,
        source_type=ATIF_SOURCE_TYPE,
        source_id=transcript_id,
        source_uri=source_uri,
        date=first_timestamp,
        agent=trajectory.agent.name,
        model=trajectory.agent.model_name,
        message_count=len(messages),
        total_time=total_time if total_time and total_time > 0 else None,
        total_tokens=total_tokens,
        messages=messages,
        events=events,
        metadata=metadata,
    )


def _trajectory_time_bounds(
    trajectory: "Trajectory",
) -> tuple[datetime | None, datetime | None]:
    """Return the (earliest, latest) parsed step timestamps of a trajectory."""
    timestamps: list[datetime] = []
    for step in trajectory.steps:
        ts = _parse_timestamp(step.timestamp)
        if ts is not None:
            timestamps.append(ts)
    if not timestamps:
        return None, None
    return min(timestamps), max(timestamps)


def _create_subagent_span_events(
    ref: "SubagentTrajectoryRef",
    parent_path: Path,
    max_depth: int,
) -> list[Event]:
    """Create the span structure for a subagent.

    Follows Inspect's pattern with agent events inside the span:

      SpanBeginEvent(type="agent", name="terminus_2")
        [subagent events...]
      SpanEndEvent

    Args:
        ref: The subagent trajectory reference
        parent_path: Path to the parent trajectory file, for resolving the
            relative ref.trajectory_path
        max_depth: Maximum depth for loading nested subagent events
            (0 = no loading)

    Returns:
        List of events in correct order
    """
    agent_events: list[Event] = []
    agent_span_id = f"agent-{ref.session_id}"
    agent_name: str = ref.session_id or "subagent"
    # Span endpoints default to import time only when no real timestamps are
    # available; otherwise we derive them from the subagent's own steps so the
    # span sits in the historical run window (a `utcnow()` end would stretch
    # the span to import time and corrupt `total_time`).
    begin_ts = utcnow()
    end_ts = begin_ts

    if max_depth <= 0:
        pass
    elif ref.trajectory_path is None:
        logger.warning(
            "ATIF subagent ref has no trajectory_path; emitting empty span: %s",
            ref.session_id,
        )
    else:
        sub_path = (parent_path.parent / ref.trajectory_path).resolve()
        trajectory_model = import_trajectory_model()
        try:
            subagent_trajectory = trajectory_model.model_validate_json(
                sub_path.read_text()
            )
        except (OSError, ValidationError) as e:
            logger.warning("ATIF subagent file not loadable %s: %s", sub_path, e)
        else:
            agent_name = subagent_trajectory.agent.name or agent_name
            sub_begin, sub_end = _trajectory_time_bounds(subagent_trajectory)
            if sub_begin is not None:
                begin_ts = sub_begin
            if sub_end is not None:
                end_ts = sub_end
            sub_transcript = _create_transcript(
                subagent_trajectory,
                source_uri=str(sub_path),
                max_depth=max_depth - 1,
            )
            # Re-parent top-level items so event_tree() nests them
            # under the agent span
            agent_events = list(sub_transcript.events)
            for evt in agent_events:
                if isinstance(evt, SpanBeginEvent):
                    if evt.parent_id is None:
                        evt.parent_id = agent_span_id
                elif not isinstance(evt, SpanEndEvent):
                    if evt.span_id is None:
                        evt.span_id = agent_span_id

    span_begin = SpanBeginEvent(
        id=agent_span_id,
        name=agent_name,
        type="agent",
        timestamp=begin_ts,
    )
    span_end = SpanEndEvent(id=agent_span_id, timestamp=end_ts)
    return [span_begin, *agent_events, span_end]
