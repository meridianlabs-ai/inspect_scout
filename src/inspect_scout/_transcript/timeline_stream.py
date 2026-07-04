"""Two-pass streaming timeline message extraction over a `TranscriptHandle`.

Design context: see
``docs/superpowers/specs/2026-07-03-streaming-events-scanning-design.md``.

The streaming events path builds a "skeleton" event list by streaming a
``TranscriptHandle`` once and replacing bulk-content events with stripped
stand-ins ("stubs"). The unmodified ``timeline_build`` classifier then runs
on the skeleton exactly as it would on the materialized transcript, to
determine span structure and which spans/regions are scannable. A second
pass later re-streams the handle and substitutes back the *full* events
that pass 1 determined are actually needed (see
``inspect_ai.event._timeline.timeline_build`` for the classifier itself).
``stream_timeline_messages`` is the end-to-end entry point orchestrating
both passes and yielding the same ``TimelineMessages`` segments
``timeline_messages`` would yield over a fully materialized transcript.

For this to work, stubs must preserve every signal the classifier reads:

- ``uuid`` / ``span_id`` / timestamps: identity and positioning.
- For ``ModelEvent``: the system prompt (read by
  ``_get_system_prompt_for_event``, ``_timeline.py:1124``) and whether the
  event has tool calls (read by ``_has_tool_calls``, ``_timeline.py:1143``).
  ``_is_single_turn`` (``_timeline.py:1280``) counts direct ModelEvents and
  ToolEvents per span, which is why stubbing never collapses or drops
  events -- one stub per original event, always. The warmup/cache-priming
  signal read by ``_is_warmup_call`` (``_timeline.py:1240``) --
  ``config.max_tokens <= 1`` plus a single-word trailing ``ChatMessageUser``
  content -- is preserved by retaining that trailing user message (truncated
  to its first whitespace-separated token) when ``max_tokens <= 1``, so
  ``_wrap_utility_events`` classifies warmup calls as utility spans
  identically on the stub and materialized paths.
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
    from inspect_scout._transcript.interleave import EventsSpec


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

    When `event.config.max_tokens <= 1`, the last `ChatMessageUser` from
    `event.input` is also retained (appended after the system messages so
    it stays the trailing user message the classifier finds). This
    preserves the signal `_is_warmup_call` (`_timeline.py:1240`) reads: it
    scans `reversed(event.input)` for the first `ChatMessageUser` and, for
    string content, tests `len(content.split()) <= 1`. To avoid retaining
    bulk while keeping that predicate's result identical, string content is
    truncated to its first whitespace-separated token (empty string when the
    content is empty/whitespace-only). Non-string (list) content is dropped,
    matching `_is_warmup_call`'s own behaviour of returning `False` for
    non-string user content -- so a stubbed list-content user message would
    never have qualified as a warmup call anyway.

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
                stub_input.append(msg.model_copy(update={"content": interned_content}))

    # Retain the warmup signal for `_is_warmup_call` (max_tokens <= 1 plus a
    # single-word trailing user message). Append the last ChatMessageUser
    # after the system messages so it remains the trailing user message the
    # classifier finds when scanning `reversed(input)`. Keep up to TWO
    # whitespace tokens: the classifier tests `len(content.split()) <= 1`,
    # so two tokens preserve the single-vs-multi-word distinction in BOTH
    # directions (a one-token truncation would flip multi-word judge calls
    # into false warmups) while still stripping bulk.
    if event.config.max_tokens is not None and event.config.max_tokens <= 1:
        for msg in reversed(event.input):
            if isinstance(msg, ChatMessageUser):
                if isinstance(msg.content, str):
                    tokens = msg.content.split()
                    truncated = " ".join(tokens[:2])
                    stub_input.append(msg.model_copy(update={"content": truncated}))
                # Non-string user content never qualifies as a warmup call
                # (`_is_warmup_call` returns False for it), so it is dropped.
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


def _output_only_model_event(event: ModelEvent) -> ModelEvent:
    """Return a copy of `event` retaining only its first-choice output message.

    Used for `ModelEvent`s pass 1 determined are NOT needed to build the
    scanned thread (i.e. not in `needed_model_event_uuids`'s result) when
    `events` interleaving is enabled. `_AnchorWalk.add`
    (`_transcript/interleave.py`) still needs every off-thread
    `ModelEvent`'s `output.choices[0].message` to render it as a
    `[E#] MODEL (BRANCH):` entry, or to recognize its id as a member of the
    untruncated `compaction="all"` thread when deciding it is actually a
    compaction-pruned turn that should stay hidden instead (see
    `_AnchorWalk`'s `excluded_ids`). Nothing else is retained: `input`,
    `tools`, and any output choice beyond the first are dropped, so pass 2
    never holds more than one rendered output message per off-thread
    `ModelEvent` -- never its (potentially huge) input.

    Args:
        event: A full (non-stubbed) `ModelEvent` from pass 2's stream.

    Returns:
        A `model_copy` of `event` with only the first output choice kept
        and input/tools removed.
    """
    output = event.output
    kept_choices = output.choices[:1] if output.choices else []
    return event.model_copy(
        update={
            "input": [],
            "input_refs": None,
            "tools": [],
            "call": None,
            "output": output.model_copy(update={"choices": kept_choices}),
        }
    )


def _collect_pass2_model_events(
    event: Event,
    needed: set[str],
    full_by_uuid: dict[str, ModelEvent],
    offthread_by_uuid: dict[str, ModelEvent] | None,
) -> None:
    """Recursively collect full and off-thread-output `ModelEvent`s from `event`.

    Recurses into `ToolEvent.events` so nested tool-spawned-agent
    ModelEvents (e.g. inside a handoff tool's `.events`) are found too --
    they never appear at the top level of a handle's flat event stream.

    Populates two accumulators from a single pass-2 walk:

    - `full_by_uuid`: every `ModelEvent` whose uuid is in `needed`, kept in
      full -- the content the scanned thread's message reconstruction
      reads. The (possibly large) `ToolEvent` payload a nested match was
      found inside is not kept beyond this call.
    - `offthread_by_uuid` (only populated when not `None`, i.e. when
      `events` interleaving is enabled): every OTHER `ModelEvent`, reduced
      via `_output_only_model_event` to just its rendered output message
      -- bounded, since only the output (never the input) is retained.
      `None` skips this collection entirely, matching `events=None`'s
      byte-identical-to-before behavior.

    Args:
        event: A full (non-stubbed) event from pass 2's stream.
        needed: uuids selected by ``needed_model_event_uuids`` in pass 1.
        full_by_uuid: Accumulator mapping uuid -> full `ModelEvent`,
            updated in place.
        offthread_by_uuid: Accumulator mapping uuid -> output-only
            `ModelEvent` for off-thread events, updated in place, or
            `None` to skip this collection.
    """
    if isinstance(event, ModelEvent):
        if event.uuid is not None:
            if event.uuid in needed:
                full_by_uuid[event.uuid] = event
            elif offthread_by_uuid is not None:
                offthread_by_uuid[event.uuid] = _output_only_model_event(event)
    elif isinstance(event, ToolEvent) and event.events:
        for nested in event.events:
            _collect_pass2_model_events(nested, needed, full_by_uuid, offthread_by_uuid)


def _substitute_full_events(
    span: TimelineSpan, full_by_uuid: dict[str, ModelEvent]
) -> None:
    """In-place: replace stub `ModelEvent`s in `span`'s tree with full ones.

    Walks `span.content` (recursing into nested `TimelineSpan`s) and
    `span.branches`, and for every `TimelineEvent` node wrapping a
    `ModelEvent` whose uuid is a key of `full_by_uuid`, mutates
    `node.event` to the full event. This reaches nested tool-spawned-agent
    `ModelEvent`s too, since `inspect_ai`'s tree builder expands a
    `ToolEvent` with nested `.events` into a nested `TimelineSpan` whose
    `content` holds `TimelineEvent` nodes for each nested event (see
    ``inspect_ai.event._timeline._event_to_node``).

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
    events: EventsSpec | None = None,
) -> AsyncIterator[TimelineMessages]:
    """Yield timeline message segments by streaming a `TranscriptHandle` twice.

    Pass 1 streams `handle.events()` once, stubbing bulk `ModelEvent`/
    `ToolEvent` content (`stub_event`) while preserving every signal
    `inspect_ai`'s timeline classifier reads, then builds the timeline from
    the stub skeleton and determines exactly which `ModelEvent`s the
    scanning path (`span_messages`, via `timeline_messages`) actually reads
    (`needed_model_event_uuids`).

    Pass 2 re-streams `handle.events()` (the multi-shot contract:
    `TranscriptHandle.events()` may be called more than once) and collects
    the full, un-stubbed `ModelEvent`s whose uuid was selected in pass 1
    (recursing into `ToolEvent.events` for tool-spawned agents). Those full
    events are substituted in place into the stub skeleton, which is then
    handed to the unmodified `timeline_messages` to yield message segments
    -- identical to running `timeline_messages` on a fully materialized
    transcript, but never holding more than one pass's events plus the
    (stubbed) skeleton in memory at once.

    Args:
        handle: Multi-shot streaming access to the transcript's events.
        messages_as_str: Rendering function from `message_numbering()`.
        model: The model used for scanning (for `count_tokens()`).
        context_window: Override for the model's context window size.
        compaction: How to handle compaction boundaries.
        depth: Maximum nesting level of scannable spans to process.
        prompt_reserve: Context-window allowance for prompt scaffolding.
        events: Which non-message event types to interleave into each
            span's message thread, forwarded to `timeline_messages()`
            (`"all"`, a list of event types, or `None` to disable
            interleaving). When set, span-external events (events outside
            any scannable span's direct content) are collected from the
            substituted skeleton via `collect_span_external()` and
            forwarded alongside `events`. This path never prunes `scorers`
            spans (see the module-level note in `stream_timeline_messages`'
            implementation), so the collection source matches
            `transcript_messages(..., include_scorers=True)`'s semantics: a
            `scorers` span with a direct `ModelEvent` is walked as an
            ordinary scannable span (its own events splice into its own
            thread) and is excluded from external collection to avoid
            double-rendering its score; a `scorers` span without one is
            never walked by `_walk_spans` and its events are collected
            externally instead. `events=None` (default) is byte-identical
            to behavior before this parameter existed. When `events` is
            not `None`, pass 2 additionally retains, for every `ModelEvent`
            not selected by `needed_model_event_uuids`, ONLY its rendered
            output message (`_output_only_model_event`) -- never its input
            -- so off-thread outputs (forks, or turns a non-`"all"`
            `compaction` pruned) render identically to the materialized
            path instead of appearing as empty `MODEL (BRANCH)` stubs.
            Memory: one output message per off-thread `ModelEvent`, in
            addition to the (already bounded) `needed` set.

    Yields:
        `TimelineMessages` segments, identical to calling `timeline_messages`
        on the fully materialized transcript's built timeline with the same
        `events` value.

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
    # Populated only when `events` interleaving is enabled: off-thread
    # ModelEvents' output messages, so part-A's branch-entry rendering (and
    # Job 1's compaction-pruned/fork discriminator) sees real content
    # instead of empty stubs, without retaining off-thread inputs.
    offthread_by_uuid: dict[str, ModelEvent] | None = {} if events is not None else None
    async for ev in handle.events():
        _collect_pass2_model_events(ev, needed, full_by_uuid, offthread_by_uuid)

    missing = needed - full_by_uuid.keys()
    if missing:
        raise _StubSkeletonUnsupported(
            "pass 2 did not find a full event for every uuid selected in "
            f"pass 1 (missing {sorted(missing)!r}); this indicates "
            "handle.events() returned different content across its two "
            "calls, violating the TranscriptHandle multi-shot contract"
        )

    _substitute_full_events(tree.root, full_by_uuid)
    if offthread_by_uuid:
        _substitute_full_events(tree.root, offthread_by_uuid)

    span_external: dict[str, list[tuple[str, str]]] | None = None
    if events is not None:
        # `stream_timeline_messages` never prunes `scorers` spans before
        # handing the tree to `timeline_messages` (unlike
        # `transcript_messages`'s default `include_scorers=False`, which
        # prunes them after collecting their events here). So the
        # collection source below mirrors
        # `transcript_messages(..., include_scorers=True)`'s: filter out
        # only `scorers` spans that have a direct `ModelEvent` (those are
        # walked normally by `timeline_messages` and splice their own
        # events via `span_interleaved_messages`; collecting them here too
        # would double-render their score). A `scorers` span without a
        # direct `ModelEvent` is never walked by `_walk_spans` regardless,
        # so it must stay in the collection source or its events (e.g. the
        # final `ScoreEvent`) would be silently lost.
        from inspect_ai.event import timeline_filter

        from inspect_scout._transcript.interleave import (
            _span_has_direct_model_event,
            collect_span_external,
        )

        collection_source = timeline_filter(
            tree,
            lambda s: (
                not (s.span_type == "scorers" and _span_has_direct_model_event(s))
            ),
        )
        span_external = collect_span_external(collection_source, events, depth=depth)

    async for seg in timeline_messages(
        tree,
        messages_as_str=messages_as_str,
        model=model,
        context_window=context_window,
        compaction=compaction,
        depth=depth,
        prompt_reserve=prompt_reserve,
        events=events,
        span_external=span_external,
    ):
        yield seg
