"""Two-pass streaming timeline message extraction over a `TranscriptHandle`.

Design context: see
``docs/superpowers/specs/2026-07-03-streaming-events-scanning-design.md``.

Pass 1 streams the handle once, replacing bulk-content events with stripped
stand-ins ("stubs"), and runs the unmodified ``timeline_build`` classifier on
the resulting skeleton to determine span structure and which events the
scanning path actually reads. Pass 2 re-streams the handle and substitutes
the *full* events back in. ``stream_timeline_messages`` orchestrates both and
yields the same ``TimelineMessages`` segments as running over a fully
materialized transcript.

Stubs must preserve every signal the classifier reads, so ``stub_event`` and
its helpers keep uuids/span_ids/timestamps, system prompts, tool-call
presence, warmup signals, and agent-span fields; see those functions for the
per-field details. One stub per original event, always (the classifier counts
ModelEvents/ToolEvents per span).

Accepted display-only fidelity loss: ``_extract_agent_results``' bridge flow
reads the *next* ModelEvent's ``input``, which our stub reduces to system
messages, so ``TimelineSpan.agent_result`` may not populate. It is not read
by ``_walk_spans`` or ``span_messages`` -- the two functions the scanning
path depends on.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, AsyncIterator, Literal

from inspect_ai.event import (
    CompactionEvent,
    Event,
    ModelEvent,
    TimelineEvent,
    TimelineSpan,
    ToolEvent,
    timeline_build,
)
from inspect_ai.model import ChatMessageSystem, ChatMessageUser, ContentText, Model

from inspect_scout._transcript.timeline import (
    TimelineMessages,
    _walk_spans,
    timeline_messages,
)

if TYPE_CHECKING:
    from inspect_scout._scanner.extract import MessagesAsStr
    from inspect_scout._transcript.handle import TranscriptHandle


class _StubSkeletonUnsupported(Exception):
    """Transcript cannot be faithfully represented by a stub skeleton.

    Raised for events lacking a ``uuid``, which cannot be targeted for
    full-event substitution in pass 2.
    """


class _PromptInterner:
    """Dict-backed interner for system-prompt strings.

    Agentic transcripts repeat the same system prompt across many
    ``ModelEvent``s; interning keeps one copy per distinct prompt in the stub
    skeleton instead of one per event.
    """

    def __init__(self) -> None:
        self._pool: dict[str, str] = {}

    def intern(self, s: str) -> str:
        """Return a canonical instance for `s`, storing it on first sight."""
        existing = self._pool.get(s)
        if existing is not None:
            return existing
        self._pool[s] = s
        return s


def _stub_model_event(event: ModelEvent, interner: _PromptInterner) -> ModelEvent:
    """Return a stripped copy of `event` preserving classification signals.

    Keeps `uuid`, `span_id`, timestamps, `input` reduced to its
    `ChatMessageSystem` entries (content interned), and `output` reduced to
    the first choice's message with `tool_calls` kept (arguments emptied) so
    `_has_tool_calls` still reads correctly. When `config.max_tokens <= 1`,
    the trailing `ChatMessageUser` is also retained (truncated) to preserve
    the `_is_warmup_call` signal; see the inline note below.

    Args:
        event: The `ModelEvent` to stub.
        interner: Interner used to dedupe system-prompt content strings.

    Returns:
        A `model_copy` of `event` with bulk content removed.
    """
    stub_input: list[ChatMessageSystem | ChatMessageUser] = []
    for msg in event.input:
        if isinstance(msg, ChatMessageSystem):
            if isinstance(msg.content, str):
                stub_input.append(
                    msg.model_copy(update={"content": interner.intern(msg.content)})
                )
            else:
                # `_get_system_prompt_for_event` reads each part's `.text`;
                # intern `ContentText` parts, keep other (already-small) parts.
                interned_content = [
                    part.model_copy(update={"text": interner.intern(part.text)})
                    if isinstance(part, ContentText)
                    else part
                    for part in msg.content
                ]
                stub_input.append(msg.model_copy(update={"content": interned_content}))

    # Retain the warmup signal `_is_warmup_call` reads (max_tokens <= 1 plus a
    # single-word trailing user message). Append the last ChatMessageUser after
    # the system messages so it stays the trailing message found when scanning
    # `reversed(input)`. Keep up to TWO whitespace tokens: the classifier tests
    # `len(content.split()) <= 1`, so two tokens preserve the single-vs-multi-
    # word distinction in BOTH directions (a one-token truncation would flip
    # multi-word judge calls into false warmups) while still stripping bulk.
    if event.config.max_tokens is not None and event.config.max_tokens <= 1:
        for msg in reversed(event.input):
            if isinstance(msg, ChatMessageUser):
                if isinstance(msg.content, str):
                    tokens = msg.content.split()
                    truncated = " ".join(tokens[:2])
                    stub_input.append(msg.model_copy(update={"content": truncated}))
                # Non-string user content never qualifies as a warmup call.
                break

    if event.output.choices:
        first_choice = event.output.choices[0]
        stub_tool_calls = (
            [
                dataclasses.replace(call, arguments={})
                for call in first_choice.message.tool_calls
            ]
            if first_choice.message.tool_calls
            else first_choice.message.tool_calls
        )
        stub_message = first_choice.message.model_copy(
            update={"content": "", "tool_calls": stub_tool_calls}
        )
        stub_choices = [first_choice.model_copy(update={"message": stub_message})]
    else:
        stub_choices = []
    stub_output = event.output.model_copy(
        update={"choices": stub_choices, "completion": ""}
    )

    return event.model_copy(
        update={
            "input": stub_input,
            "input_refs": None,
            "tools": [],
            "call": None,
            "output": stub_output,
        }
    )


def _stub_tool_event(event: ToolEvent, interner: _PromptInterner) -> ToolEvent:
    """Return a stripped copy of `event` preserving classification signals.

    Keeps everything except `arguments`, `result`, and `view` (the bulk
    payload). `agent`, `agent_span_id`, `function`, and `id` are preserved
    unchanged for `_is_agent_span` / `_extract_agent_results`.

    `events` is NOT emptied but recursively stubbed: `inspect_ai` expands a
    `ToolEvent` with `.agent` set and non-empty `.events` into a nested
    `TimelineSpan`, so emptying it would collapse that span and hide its
    `ModelEvent`s from pass-1 selection.

    Args:
        event: The `ToolEvent` to stub.
        interner: Interner for nested `ModelEvent` system-prompt strings.

    Returns:
        A `model_copy` of `event` with bulk content removed.
    """
    return event.model_copy(
        update={
            "arguments": {},
            "result": "",
            "events": [stub_event(e, interner) for e in event.events],
            "view": None,
        }
    )


def stub_event(event: Event, interner: _PromptInterner) -> Event:
    """Return a bulk-content-stripped stand-in for `event`.

    `ModelEvent` and `ToolEvent` are reduced to the fields the classifier
    reads (see module docstring); every other event type is already small and
    returned unchanged.

    Args:
        event: The event to stub.
        interner: Interner for `ModelEvent` system-prompt strings.

    Returns:
        The (possibly stripped) event. Always preserves `uuid` and `span_id`
        so pass 2 can substitute full events back in by uuid.
    """
    if isinstance(event, ModelEvent):
        return _stub_model_event(event, interner)
    if isinstance(event, ToolEvent):
        return _stub_tool_event(event, interner)
    return event


def _require_uuid(event: ModelEvent) -> str:
    """Return `event.uuid`, or raise `_StubSkeletonUnsupported` if absent.

    Pass 2 targets selected events by uuid, so a selected ModelEvent lacking
    one fails loudly rather than silently dropping its content.
    """
    if event.uuid is None:
        raise _StubSkeletonUnsupported(
            "selected ModelEvent has no uuid; cannot target it for pass-2 substitution"
        )
    return event.uuid


def _needed_uuids_for_span(
    span_events: list[Event],
    *,
    compaction: Literal["all", "last"] | int,
) -> set[str]:
    """Select the ModelEvents whose content `span_messages` reads for one span.

    Mirrors `span_messages` (`_transcript/messages.py`) in merge mode, so the
    returned set is exactly the ModelEvents whose ``input``/``output`` that
    function touches for ``compaction``. Any change to `span_messages`' kept-
    region logic must be mirrored here.

    Args:
        span_events: A span's DIRECT events, in order (non-Model/Compaction
            events are ignored, as in ``span_messages``).
        compaction: Same semantics as ``span_messages``' parameter.

    Returns:
        The set of selected ModelEvent uuids. Raises
        ``_StubSkeletonUnsupported`` if any selected ModelEvent lacks a uuid.
    """
    model_events = [e for e in span_events if isinstance(e, ModelEvent)]
    if not model_events:
        return set()

    n: int | None
    if compaction == "last":
        n = 1
    elif compaction == "all":
        n = None
    else:
        n = compaction

    if n == 1:
        return {_require_uuid(model_events[-1])}

    # Slice to the last n regions. The CompactionEvent at cut_index is
    # INCLUDED in the slice, matching span_messages.
    events = span_events
    if n is not None:
        compaction_indices = [
            i for i, event in enumerate(events) if isinstance(event, CompactionEvent)
        ]
        num_regions = len(compaction_indices) + 1
        if n < num_regions:
            cut_index = compaction_indices[-(n)]
            events = events[cut_index:]

    # Replay the merge loop, collecting the ModelEvents whose content is read.
    needed: set[str] = set()
    current: list[ModelEvent] = []
    pending_trim_pre: ModelEvent | None = None

    for event in events:
        if isinstance(event, ModelEvent):
            if pending_trim_pre is not None:
                # `_trim_prefix` reads both the pre-trim event's and this first
                # post-trim event's input at this consumption point.
                needed.add(_require_uuid(pending_trim_pre))
                needed.add(_require_uuid(event))
                pending_trim_pre = None
            current.append(event)
        elif isinstance(event, CompactionEvent):
            if event.type == "summary":
                if current:
                    needed.add(_require_uuid(current[-1]))
                current = []
            elif event.type == "trim":
                if current:
                    # Needed only if a later ModelEvent consumes it (mirrors
                    # span_messages' pending_trim_pre_input logic).
                    pending_trim_pre = current[-1]
                current = []
            # edit: transparent, keep accumulating.

    if current:
        needed.add(_require_uuid(current[-1]))

    return needed


def needed_model_event_uuids(
    root: TimelineSpan,
    *,
    compaction: Literal["all", "last"] | int,
    depth: int | None,
) -> set[str]:
    """Select every ModelEvent whose content the scanning path reads.

    Walks scannable spans like ``timeline_messages`` and, per span, mirrors
    ``span_messages``' kept-region logic over the span's direct events. The
    union across spans is the set of events whose full content pass 2 must
    substitute back into the stub skeleton.

    Args:
        root: Root ``TimelineSpan`` of the built (stub) timeline.
        compaction: Compaction strategy (``"all"``, ``"last"``, or an int N).
        depth: Scannable-span nesting limit (``None`` = unlimited).

    Returns:
        The set of selected ModelEvent uuids across all scannable spans.

    Raises:
        _StubSkeletonUnsupported: If any selected ModelEvent lacks a uuid.
    """
    needed: set[str] = set()
    for span in _walk_spans(root, depth=depth):
        span_events = [
            item.event for item in span.content if isinstance(item, TimelineEvent)
        ]
        needed |= _needed_uuids_for_span(span_events, compaction=compaction)
    return needed


def _collect_needed_model_events(
    event: Event, needed: set[str], out: dict[str, ModelEvent]
) -> None:
    """Recursively collect full `ModelEvent`s from `event` whose uuid is needed.

    Recurses into `ToolEvent.events` so nested tool-spawned-agent ModelEvents
    are found too -- they never appear at the top level of a handle's flat
    event stream. Only the matched `ModelEvent`s are retained (not their
    enclosing `ToolEvent` payload).

    Args:
        event: A full (non-stubbed) event from pass 2's stream.
        needed: uuids selected by ``needed_model_event_uuids`` in pass 1.
        out: Accumulator mapping uuid -> full `ModelEvent`, updated in place.
    """
    if isinstance(event, ModelEvent):
        if event.uuid is not None and event.uuid in needed:
            out[event.uuid] = event
    elif isinstance(event, ToolEvent) and event.events:
        for nested in event.events:
            _collect_needed_model_events(nested, needed, out)


def _substitute_full_events(
    span: TimelineSpan, full_by_uuid: dict[str, ModelEvent]
) -> None:
    """In-place: replace stub `ModelEvent`s in `span`'s tree with full ones.

    Walks `span.content` (recursing into nested `TimelineSpan`s) and
    `span.branches`, replacing every `TimelineEvent` wrapping a `ModelEvent`
    whose uuid is in `full_by_uuid`. Reaches nested tool-spawned-agent events
    too, since the tree builder expands such `ToolEvent`s into nested spans.

    Args:
        span: A (sub)tree of the stub skeleton to mutate in place.
        full_by_uuid: Full `ModelEvent`s collected in pass 2, by uuid.
    """
    for item in span.content:
        if isinstance(item, TimelineEvent):
            event = item.event
            if isinstance(event, ModelEvent) and event.uuid in full_by_uuid:
                item.event = full_by_uuid[event.uuid]
        else:
            _substitute_full_events(item, full_by_uuid)
    for branch in span.branches:
        _substitute_full_events(branch, full_by_uuid)


async def stream_timeline_messages(
    handle: TranscriptHandle,
    *,
    messages_as_str: MessagesAsStr,
    model: Model | str | None = None,
    context_window: int | None = None,
    compaction: Literal["all", "last"] | int = "all",
    depth: int | None = None,
    prompt_reserve: int | float = 0.2,
) -> AsyncIterator[TimelineMessages]:
    """Yield timeline message segments by streaming a `TranscriptHandle` twice.

    Pass 1 builds a stub skeleton and selects which `ModelEvent`s the scanning
    path reads; pass 2 re-streams the handle, substitutes those full events
    back in, and hands the skeleton to `timeline_messages`. The result is
    identical to running `timeline_messages` on a fully materialized
    transcript, without ever holding more than one pass's events plus the stub
    skeleton in memory. See the module docstring for the full design.

    Args:
        handle: Multi-shot streaming access to the transcript's events.
        messages_as_str: Rendering function from `message_numbering()`.
        model: The model used for scanning (for `count_tokens()`).
        context_window: Override for the model's context window size.
        compaction: How to handle compaction boundaries.
        depth: Maximum nesting level of scannable spans to process.
        prompt_reserve: Context-window allowance for prompt scaffolding.

    Yields:
        `TimelineMessages` segments, identical to calling `timeline_messages`
        on the fully materialized transcript's built timeline.

    Raises:
        _StubSkeletonUnsupported: If pass 1 selects a `ModelEvent` lacking a
            uuid (see `needed_model_event_uuids`), or if pass 2's stream
            does not contain a full event for every uuid pass 1 selected
            (a multi-shot contract violation: `handle.events()` returned
            different content across the two calls).
    """
    interner = _PromptInterner()
    stubs: list[Event] = [stub_event(ev, interner) async for ev in handle.events()]
    tree = timeline_build(stubs)

    needed = needed_model_event_uuids(tree.root, compaction=compaction, depth=depth)

    full_by_uuid: dict[str, ModelEvent] = {}
    async for ev in handle.events():
        _collect_needed_model_events(ev, needed, full_by_uuid)

    missing = needed - full_by_uuid.keys()
    if missing:
        raise _StubSkeletonUnsupported(
            "pass 2 did not find a full event for every uuid selected in "
            f"pass 1 (missing {sorted(missing)!r}); this indicates "
            "handle.events() returned different content across its two "
            "calls, violating the TranscriptHandle multi-shot contract"
        )

    _substitute_full_events(tree.root, full_by_uuid)

    async for seg in timeline_messages(
        tree,
        messages_as_str=messages_as_str,
        model=model,
        context_window=context_window,
        compaction=compaction,
        depth=depth,
        prompt_reserve=prompt_reserve,
    ):
        yield seg
