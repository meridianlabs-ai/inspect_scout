"""Two-pass streaming timeline message extraction over a `TranscriptHandle`.

Design context: see
``docs/superpowers/specs/2026-05-18-scan-result-legibility-design.md``.

Pass 1 streams the handle once, replacing bulk-content events with stripped
stand-ins ("stubs"), and runs the unmodified ``timeline_build`` classifier on
the resulting skeleton to determine span structure and which events the
scanning path actually reads. Pass 2 re-streams the handle and substitutes
the *full* events back in. ``stream_timeline_messages`` orchestrates both and
yields the same *extracted messages* -- span ids and rendered segment strings
-- as running over a fully materialized transcript. On a spooled handle each
pass also decodes only what it keeps (``stub_projection``,
``output_only_projection``).

Stubs must preserve every signal the classifier reads, so ``stub_event`` and
its helpers keep uuids/span_ids/timestamps, system prompts, tool-call
presence, warmup signals, and agent-span fields; see those functions for the
per-field details. One stub per original event, always (the classifier counts
ModelEvents/ToolEvents per span).

Accepted fidelity loss, all in the ``TimelineMessages.span`` metadata rather
than the messages:

- ``TimelineSpan.agent_result`` is unpopulated. The stub sets
  ``ToolEvent.result = ""`` and reduces ``ModelEvent.input`` to system
  messages, which is every field ``_extract_agent_results`` reads, so all
  three of its sources (tool-spawned, sibling-ToolEvent, bridge flow) come up
  empty.
- Events pass 1 did *not* select stay stubs in the returned tree: pass 2
  substitutes only the ``ModelEvent``s the message extraction reads (with
  ``events`` set, plus every other ``ModelEvent``'s output message).

Harmless for this module's callers: they consume ``span.id`` and
``messages_str``, ``agent_result`` has no reader in inspect_ai outside
``_extract_agent_results`` itself and none in scout, and these spans are
transient -- never serialized into results or sent to the viewer.
"""

from __future__ import annotations

import dataclasses
import json
from typing import TYPE_CHECKING, Any, AsyncIterator, Container, Literal

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

from inspect_scout._transcript.handle import projected_events
from inspect_scout._transcript.interleave import (
    EventsSpec,
    _off_thread_model_text,
    output_only_projection,
)
from inspect_scout._transcript.json.pool import slice_positions
from inspect_scout._transcript.json.spool import BlobSpool
from inspect_scout._transcript.json.stream_parse import EventProjection
from inspect_scout._transcript.timeline import (
    TimelineMessages,
    timeline_messages,
    walk_owned_spans,
)
from inspect_scout._util._async import aclosing_iter

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

    `stub_projection` mirrors the fields read here; change both together.
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
        # logprobs carry per-token top-k tables that can dwarf the message
        # itself, and no classifier or extractor reads them.
        stub_choices = [
            first_choice.model_copy(
                update={
                    "message": stub_message,
                    "logprobs": None,
                    "prompt_logprobs": None,
                }
            )
        ]
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


def stub_projection() -> EventProjection:
    """An `EventProjection` keeping what `_stub_model_event` reads of a ModelEvent.

    Top-level ModelEvents keep only their system-role ``input`` entries (a
    possible warmup call keeps all of them) and lose ``call`` and ``tools``.
    Caches pool roles, so use one projection per pass.
    """
    roles: dict[int, Any] = {}

    def system_entries(
        refs: list[list[int]], blobs: BlobSpool, pool_len: int
    ) -> list[Any]:
        entries: list[Any] = []
        for start, end in refs:
            for i in slice_positions(start, end, pool_len):
                if roles.get(i, "system") != "system":
                    continue  # known not to be a system message: skip unread
                raw = blobs.get(("message_pool", i))
                if raw is None:
                    continue
                entry = json.loads(raw)
                roles[i] = entry.get("role")
                if roles[i] == "system":
                    entries.append(entry)
        return entries

    def project(item: dict[str, Any], blobs: BlobSpool) -> None:
        if item.get("event") != "model":
            return
        item.pop("call", None)
        item["tools"] = []
        max_tokens = (item.get("config") or {}).get("max_tokens")
        if max_tokens is not None and max_tokens <= 1:
            return  # a possible warmup call: the stub reads its last user message
        refs = item.get("input_refs")
        pool_len = blobs.pool_len("message_pool")
        if refs and pool_len:
            del item["input_refs"]
            item["input"] = system_entries(refs, blobs, pool_len)
        else:
            item["input"] = [
                message
                for message in item.get("input") or []
                if isinstance(message, dict) and message.get("role") == "system"
            ]

    return project


def _stub_tool_event(event: ToolEvent, interner: _PromptInterner) -> ToolEvent:
    """Return a stripped copy of `event` preserving classification signals.

    Keeps everything except `arguments`, `result`, and `view` (the bulk
    payload). `agent`, `agent_span_id`, `function`, and `id` are preserved
    unchanged for `_is_agent_span` / `_extract_agent_results`.

    `events` is NOT emptied but recursively stubbed: `inspect_ai` expands a
    `ToolEvent` with `.agent` set and non-empty `.events` into a nested
    `TimelineSpan`, so emptying it would collapse that span and hide its
    `ModelEvent`s from pass-1 selection.
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
    reads (see module docstring); every other event type is returned
    unchanged. Always preserves `uuid` and `span_id` so pass 2 can substitute
    full events back in by uuid.

    Stubbing is therefore partial: over this repo's four `.eval` fixtures the
    stub skeleton retains 58-86% of the full events' serialized size, the
    balance being untouched kinds (`StateEvent.changes` and `ScoreEvent.score`
    dominate). It bounds the two kinds that grow with conversation length,
    not total memory.
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
    include_scorers: bool,
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
        include_scorers: Whether scorers spans are walked, as in
            ``walk_owned_spans``.

    Returns:
        The set of selected ModelEvent uuids across all scannable spans.

    Raises:
        _StubSkeletonUnsupported: If any selected ModelEvent lacks a uuid.
    """
    needed: set[str] = set()
    for owned in walk_owned_spans(root, depth=depth, include_scorers=include_scorers):
        span_events = [
            item.event for item in owned.span.content if isinstance(item, TimelineEvent)
        ]
        needed |= _needed_uuids_for_span(span_events, compaction=compaction)
    return needed


def _output_only_model_event(event: ModelEvent) -> ModelEvent:
    """Copy of `event` keeping only its first-choice output message.

    Enough for `_AnchorWalk` to render (or exclude) an off-thread event,
    without retaining its potentially huge `input`, `tools`, or other choices.
    `output_only_projection` mirrors the fields read here; change both together.
    """
    output = event.output
    return event.model_copy(
        update={
            "input": [],
            "input_refs": None,
            "tools": [],
            "call": None,
            "output": output.model_copy(update={"choices": output.choices[:1]}),
        }
    )


def _collect_pass2_model_events(
    event: Event,
    needed: Container[str],
    full_by_uuid: dict[str, ModelEvent],
    offthread_by_uuid: dict[str, ModelEvent] | None,
) -> None:
    """Recursively collect full and off-thread-output `ModelEvent`s from `event`.

    Recurses into `ToolEvent.events` so nested tool-spawned-agent ModelEvents
    are found too -- they never appear at the top level of a handle's flat
    event stream. A `ModelEvent` in `needed` goes to `full_by_uuid` in full;
    any other goes to `offthread_by_uuid` reduced by `_output_only_model_event`,
    unless that is None (no `events` interleaving).

    Raises:
        _StubSkeletonUnsupported: An off-thread `ModelEvent` that would render
            has no uuid, so its output could never be substituted for its stub.
    """
    if isinstance(event, ModelEvent):
        if event.uuid is not None and event.uuid in needed:
            full_by_uuid[event.uuid] = event
        elif offthread_by_uuid is not None:
            if event.uuid is not None:
                offthread_by_uuid[event.uuid] = _output_only_model_event(event)
            elif _off_thread_model_text(event):
                # An empty output renders nothing on either path, so only a
                # renderable one is worth a materialized fallback.
                raise _StubSkeletonUnsupported(
                    "off-thread ModelEvent has no uuid; cannot substitute its "
                    "output for branch-entry rendering"
                )
    elif isinstance(event, ToolEvent) and event.events:
        for nested in event.events:
            _collect_pass2_model_events(nested, needed, full_by_uuid, offthread_by_uuid)


def _substitute_in_tool_event(
    tool: ToolEvent, full_by_uuid: dict[str, ModelEvent]
) -> None:
    """In-place: replace stub `ModelEvent`s nested in `tool.events`, at any depth."""
    for i, nested in enumerate(tool.events):
        if isinstance(nested, ModelEvent) and nested.uuid in full_by_uuid:
            tool.events[i] = full_by_uuid[nested.uuid]
        elif isinstance(nested, ToolEvent):
            _substitute_in_tool_event(nested, full_by_uuid)


def _substitute_full_events(
    span: TimelineSpan, full_by_uuid: dict[str, ModelEvent]
) -> None:
    """In-place: replace stub `ModelEvent`s in `span`'s tree with full ones.

    Walks `span.content` (recursing into nested `TimelineSpan`s and into
    `ToolEvent.events` left unexpanded by the tree builder) and
    `span.branches`, replacing every `ModelEvent` whose uuid is in
    `full_by_uuid`. Branches and tool-nested events matter only to `events`
    interleaving, which renders their off-thread outputs.
    """
    for item in span.content:
        if isinstance(item, TimelineEvent):
            event = item.event
            if isinstance(event, ModelEvent) and event.uuid in full_by_uuid:
                item.event = full_by_uuid[event.uuid]
            elif isinstance(event, ToolEvent):
                _substitute_in_tool_event(event, full_by_uuid)
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
    include_scorers: bool = False,
    prompt_reserve: int | float = 0.2,
    events: EventsSpec | None = None,
) -> AsyncIterator[TimelineMessages]:
    """Yield timeline message segments by streaming a `TranscriptHandle` twice.

    Pass 1 builds a stub skeleton and selects which `ModelEvent`s the scanning
    path reads; pass 2 re-streams the handle, substitutes those full events
    back in, and hands the skeleton to `timeline_messages`. The extracted
    messages match running `timeline_messages` on a fully materialized
    transcript, without ever holding more than one pass's events plus the stub
    skeleton in memory. See the module docstring for the full design and the
    span-metadata divergences.

    Args:
        handle: Multi-shot streaming access to the transcript's events.
        messages_as_str: Rendering function from `message_numbering()`.
        model: The model used for scanning (for `count_tokens()`).
        context_window: Override for the model's context window size.
        compaction: How to handle compaction boundaries.
        depth: Maximum nesting level of scannable spans to process.
        include_scorers: Whether to include scorer events. Defaults to
            ``False``, matching ``transcript_messages()`` -- a grader's rubric
            typically contains the expected answer.
        prompt_reserve: Context-window allowance for prompt scaffolding.
        events: Which non-message event types to interleave into each span's
            thread, as in `timeline_messages()` (`None` disables it).

    Yields:
        `TimelineMessages` segments whose span ids and rendered strings match
        `transcript_messages` over the fully materialized transcript. The
        `span` metadata carries the divergences listed in the module
        docstring.

    Raises:
        _StubSkeletonUnsupported: If pass 1 selects a `ModelEvent` lacking a
            uuid (see `needed_model_event_uuids`). Raised before any segment
            is yielded, so callers may fall back to a materialized scan. Also
            raised, equally early, for a renderable off-thread `ModelEvent`
            lacking a uuid when `events` is set.
        RuntimeError: If pass 2's stream does not contain a full event for
            every uuid pass 1 selected -- `handle.events()` returned different
            content across the two calls, violating the multi-shot contract.
    """
    interner = _PromptInterner()
    stubs: list[Event] = [
        stub_event(ev, interner)
        async for ev in projected_events(handle, stub_projection())
    ]
    tree = timeline_build(stubs)

    needed = needed_model_event_uuids(
        tree.root, compaction=compaction, depth=depth, include_scorers=include_scorers
    )
    if events is not None and compaction != "all":
        # The compaction-pruned/fork discriminator rebuilds the untruncated
        # thread from region-last ModelEvents' inputs; output-only copies
        # would misrender pruned turns as forks.
        needed |= needed_model_event_uuids(
            tree.root, compaction="all", depth=depth, include_scorers=include_scorers
        )

    full_by_uuid: dict[str, ModelEvent] = {}
    offthread_by_uuid: dict[str, ModelEvent] | None = {} if events is not None else None
    async with aclosing_iter(
        projected_events(handle, output_only_projection(keep_uuids=needed))
    ) as full_events:
        async for ev in full_events:
            _collect_pass2_model_events(ev, needed, full_by_uuid, offthread_by_uuid)

    missing = needed - full_by_uuid.keys()
    if missing:
        # Not _StubSkeletonUnsupported: callers fall back to a materialized
        # scan on that, and a handle that streams different content twice
        # cannot be trusted to materialize correctly either.
        raise RuntimeError(
            "pass 2 did not find a full event for every uuid selected in "
            f"pass 1 (missing {sorted(missing)!r}); this indicates "
            "handle.events() returned different content across its two "
            "calls, violating the TranscriptHandle multi-shot contract"
        )

    _substitute_full_events(tree.root, full_by_uuid)
    if offthread_by_uuid:
        _substitute_full_events(tree.root, offthread_by_uuid)

    async for seg in timeline_messages(
        tree,
        messages_as_str=messages_as_str,
        model=model,
        context_window=context_window,
        compaction=compaction,
        depth=depth,
        prompt_reserve=prompt_reserve,
        events=events,
        include_scorers=include_scorers,
    ):
        yield seg
