"""Event-stubbing primitives for the two-pass streaming events skeleton.

Design context: see
``docs/superpowers/specs/2026-07-03-streaming-events-scanning-design.md``
(pass 1 of the two-pass skeleton).

The streaming events path builds a "skeleton" event list by streaming a
``TranscriptHandle`` once and replacing bulk-content events with stripped
stand-ins ("stubs"). The unmodified ``timeline_build`` classifier then runs
on the skeleton exactly as it would on the materialized transcript, to
determine span structure and which spans/regions are scannable. A second
pass later re-streams the handle and substitutes back the *full* events
that pass 1 determined are actually needed (see
``inspect_ai.event._timeline.timeline_build`` for the classifier itself).

For this to work, stubs must preserve every signal the classifier reads:

- ``uuid`` / ``span_id`` / timestamps: identity and positioning.
- For ``ModelEvent``: the system prompt (read by
  ``_get_system_prompt_for_event``, ``_timeline.py:1124``) and whether the
  event has tool calls (read by ``_has_tool_calls``, ``_timeline.py:1143``).
  ``_is_single_turn`` (``_timeline.py:1280``) counts direct ModelEvents and
  ToolEvents per span, which is why stubbing never collapses or drops
  events -- one stub per original event, always.
- For ``ToolEvent``: ``agent`` / ``agent_span_id`` / ``function`` (read by
  ``_is_agent_span`` and ``_extract_agent_results``, ``_timeline.py:1038``).

Known, accepted fidelity loss: ``_extract_agent_results``' bridge flow
(``_timeline.py:1072-1090``) reads the *next* ModelEvent's ``input`` for a
``ChatMessageTool`` whose ``tool_call_id`` matches the agent span. Our
``ModelEvent`` stub reduces ``input`` to system messages only, so that
lookup will not find a match against a stubbed ModelEvent. This only
affects ``TimelineSpan.agent_result``, which is populated for UI display
and is not read by ``_walk_spans`` (``_transcript/timeline.py``) or
``span_messages`` (``_transcript/messages.py``) -- the two functions the
scanning path depends on. So this loss is display-only and acceptable for
the scanning skeleton.
"""

from __future__ import annotations

import dataclasses
from typing import Literal

from inspect_ai.event import (
    CompactionEvent,
    Event,
    ModelEvent,
    TimelineEvent,
    TimelineSpan,
    ToolEvent,
)
from inspect_ai.model import ChatMessageSystem, ContentText

from inspect_scout._transcript.timeline import _walk_spans


class _StubSkeletonUnsupported(Exception):
    """Raised when the transcript cannot be faithfully represented by a stub skeleton.

    Reserved for the uuid-less event fallback path (events lacking a
    ``uuid`` cannot be targeted for full-event substitution in pass 2).
    """


class _PromptInterner:
    """Dict-backed interner for system-prompt strings.

    Agentic transcripts commonly repeat the same system prompt across
    hundreds or thousands of ``ModelEvent``s. Interning ensures the stub
    skeleton retains only one copy of each distinct prompt string instead
    of one copy per event.
    """

    def __init__(self) -> None:
        self._pool: dict[str, str] = {}

    def intern(self, s: str) -> str:
        """Return a canonical instance for `s`, storing it on first sight.

        Args:
            s: The string to intern.

        Returns:
            `s` itself the first time a given value is seen; on subsequent
            calls with an equal string, the exact same instance stored
            from the first call.
        """
        existing = self._pool.get(s)
        if existing is not None:
            return existing
        self._pool[s] = s
        return s


def _stub_model_event(event: ModelEvent, interner: _PromptInterner) -> ModelEvent:
    """Return a stripped copy of `event` preserving classification signals.

    Keeps `uuid`, `span_id`, timestamps, `input` reduced to only its
    `ChatMessageSystem` entries (string content interned; list content has
    each `ContentText` part's text interned in place), and `output`
    reduced to preserve `_has_tool_calls` (first choice's message with
    `tool_calls` kept -- but with each call's `arguments` emptied, since
    `_has_tool_calls` only checks truthiness of the list -- content
    emptied; other choices dropped).

    Args:
        event: The `ModelEvent` to stub.
        interner: Interner used to dedupe system-prompt content strings.

    Returns:
        A `model_copy` of `event` with bulk content removed.
    """
    system_messages: list[ChatMessageSystem] = []
    for msg in event.input:
        if isinstance(msg, ChatMessageSystem):
            if isinstance(msg.content, str):
                system_messages.append(
                    msg.model_copy(update={"content": interner.intern(msg.content)})
                )
            else:
                # `_get_system_prompt_for_event` reads each part's `.text`
                # (only `ContentText` parts have one; other content types,
                # e.g. images, are already small relative to bulk
                # conversation content and are kept as-is). Intern each
                # `ContentText` part's text so repeated list-content
                # system prompts are deduped the same way string-content
                # ones are.
                interned_content = [
                    part.model_copy(update={"text": interner.intern(part.text)})
                    if isinstance(part, ContentText)
                    else part
                    for part in msg.content
                ]
                system_messages.append(
                    msg.model_copy(update={"content": interned_content})
                )

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
            "input": system_messages,
            "input_refs": None,
            "tools": [],
            "call": None,
            "output": stub_output,
        }
    )


def _stub_tool_event(event: ToolEvent, interner: _PromptInterner) -> ToolEvent:
    """Return a stripped copy of `event` preserving classification signals.

    Keeps everything except `arguments`, `result`, and `view`, which carry
    the bulk tool-call payload. `agent`, `agent_span_id`, `function`, and
    `id` -- read by `_is_agent_span` / `_extract_agent_results` -- are
    preserved unchanged.

    `events` is NOT emptied: `inspect_ai`'s `_event_to_node` treats a
    `ToolEvent` with both `.agent` set and non-empty `.events` as a
    tool-spawned agent, recursively expanding `.events` into a nested
    `TimelineSpan` (see `_timeline.py`'s `_event_to_node`). Emptying it
    would collapse that nested span, hiding its `ModelEvent`s from pass-1
    selection. Instead, each nested event is recursively stubbed via
    `stub_event`, which still strips bulk content (nested `ModelEvent`s
    lose their bulk input/output, nested `ToolEvent`s are stripped the
    same way, recursively) while preserving the uuids and structure the
    classifier and pass-2 substitution need.

    Args:
        event: The `ToolEvent` to stub.
        interner: Interner used to dedupe nested `ModelEvent` system-prompt
            content strings across the transcript.

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

    `ModelEvent` and `ToolEvent` are reduced to the fields the
    `inspect_ai.event._timeline` classifier reads (see module docstring).
    Every other event type is returned unchanged: they are either already
    small (`CompactionEvent`, `SpanBeginEvent`, `SpanEndEvent`,
    `BranchEvent`, `AnchorEvent`) or are positional-only w.r.t.
    classification and kept-by-default per the stubbing spec.

    Args:
        event: The event to stub.
        interner: Interner used to dedupe `ModelEvent` system-prompt
            content strings across the transcript.

    Returns:
        The (possibly stripped) event. Always preserves `uuid` and
        `span_id` so pass 2 can substitute full events back in by uuid.
    """
    if isinstance(event, ModelEvent):
        return _stub_model_event(event, interner)
    if isinstance(event, ToolEvent):
        return _stub_tool_event(event, interner)
    return event


def _require_uuid(event: ModelEvent) -> str:
    """Return `event.uuid`, or raise `_StubSkeletonUnsupported` if absent.

    A selected ModelEvent whose full content pass 2 must substitute back
    can only be targeted by uuid. An event lacking one cannot be faithfully
    represented by the stub skeleton, so selection fails loudly rather than
    silently dropping the event's content.
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

    Mirrors `span_messages` (`_transcript/messages.py`) exactly, in
    merge mode, so the returned set is precisely the ModelEvents whose
    ``input``/``output`` that function touches for ``compaction``:

    - ``"last"`` / ``n == 1``: only the span's final ModelEvent.
    - otherwise: normalize ``n``; when ``n`` is an int smaller than the
      region count, slice ``span_events`` from the same ``cut_index``
      (the CompactionEvent at that position is kept, matching
      ``messages.py``); then replay the merge loop, marking as needed the
      last pre-compaction ModelEvent grafted at each ``summary``/``trim``
      boundary, the first post-``trim`` ModelEvent whose input
      ``_trim_prefix`` reads, and the final accumulation's last ModelEvent.
      ``edit`` boundaries are transparent (they do not split a region),
      exactly as in ``span_messages``.

    Args:
        span_events: A span's DIRECT events (Model/Compaction and others),
            in order. Non-Model/Compaction events are ignored, as in
            ``span_messages``.
        compaction: Same semantics as ``span_messages``' parameter.

    Returns:
        The set of selected ModelEvent uuids. Raises
        ``_StubSkeletonUnsupported`` if any selected ModelEvent lacks a
        uuid.
    """
    model_events = [e for e in span_events if isinstance(e, ModelEvent)]
    if not model_events:
        return set()

    # Normalize compaction to n (mirrors span_messages).
    n: int | None
    if compaction == "last":
        n = 1
    elif compaction == "all":
        n = None
    else:
        n = compaction

    # "last 1" shortcut: only the final ModelEvent.
    if n == 1:
        return {_require_uuid(model_events[-1])}

    # Slice to the last n regions if n is specified (mirrors span_messages:
    # the CompactionEvent at cut_index is INCLUDED in the slice).
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
                # Pre-trim input is read by `_trim_prefix` at this consumption point.
                needed.add(_require_uuid(pending_trim_pre))
                # `_trim_prefix` reads this (first post-trim) event's input.
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
                    # Save pre-trim event; only add to needed if a later ModelEvent
                    # consumes it (mirrors span_messages' pending_trim_pre_input logic).
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

    Walks scannable spans exactly like ``timeline_messages``
    (``_walk_spans(root, depth=depth)``) and, per span, mirrors
    ``span_messages``' kept-region logic over that span's DIRECT events
    (child spans are separate walks, matching ``span_messages``' per-span
    view of ``span.content``). The union across spans is the set of
    ModelEvents whose ``input``/``output`` ``span_messages`` touches for
    the given ``compaction`` -- i.e. the events whose full content pass 2
    must substitute back into the stub skeleton.

    Note: ``span_messages`` reads no tool definitions in this path
    (``segment_messages`` -> ``span_messages`` never calls ``span_tools``,
    and the ``llm_scanner`` segment flow does not either), so ModelEvents
    selected purely to carry ``tools`` are not needed; stubs dropping
    ``tools`` is irrelevant to message reconstruction.

    Args:
        root: Root ``TimelineSpan`` of the built (stub) timeline.
        compaction: Compaction strategy, forwarded per-span to the mirror
            of ``span_messages`` (``"all"``, ``"last"``, or an int N).
        depth: Scannable-span nesting limit, forwarded to ``_walk_spans``
            (``None`` = unlimited).

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
