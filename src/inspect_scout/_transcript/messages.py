"""Message extraction from events, with compaction boundary handling."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, overload

import anyio
from inspect_ai._util._async import tg_collect
from inspect_ai.event import (
    CompactionEvent,
    Event,
    EventTreeSpan,
    ModelEvent,
    Timeline,
    TimelineEvent,
    TimelineSpan,
    event_sequence,
    event_tree,
)
from inspect_ai.model import ChatMessage, Model, get_model
from inspect_ai.model._chat_message import ChatMessageBase
from inspect_ai.model._model_info import get_model_info
from inspect_ai.tool import ToolInfo

from inspect_scout._scanner.extract import MessagesAsStr

if TYPE_CHECKING:
    from inspect_scout._transcript.interleave import EventsSpec
    from inspect_scout._transcript.types import Transcript

DEFAULT_CONTEXT_WINDOW = 128_000
_TOKENIZER_SAFETY_MARGIN = 0.05

# ``count_tokens`` can be a network call (e.g. Anthropic's count_tokens
# endpoint), so counting each message individually floods the connection
# pool and rate limits on large transcripts. Messages are instead grouped
# into chunks targeting a small fraction of the segment budget (sized via
# a rough chars-per-token estimate), each chunk is counted with a single
# call, and only a handful of calls are in flight at once. Segments are
# then packed from whole chunks, trading a small amount of packing
# headroom (at most one chunk's worth per segment) for far fewer calls.
_COUNT_CHUNK_BUDGET_FRACTION = 0.05
_COUNT_EST_CHARS_PER_TOKEN = 4
_COUNT_MAX_CONCURRENCY = 8


def _effective_segment_budget(
    *,
    model: Model,
    context_window: int | None,
    prompt_reserve: int | float = 0.2,
) -> int:
    """Compute the token budget available for rendered messages.

    ``prompt_reserve`` controls how much of the context window is reserved
    for prompt scaffolding wrapped around the messages (e.g. a scanner
    template). A ``float`` reserves that fraction of the window; an
    ``int`` reserves that many tokens and additionally subtracts a small
    safety margin to absorb ``count_tokens`` imprecision.
    """
    if context_window is not None:
        window = context_window
    else:
        model_info = get_model_info(model)
        window = (
            model_info.input_tokens
            if model_info is not None and model_info.input_tokens is not None
            else DEFAULT_CONTEXT_WINDOW
        )

    if isinstance(prompt_reserve, float):
        return int(window * (1.0 - prompt_reserve))
    return int(window * (1.0 - _TOKENIZER_SAFETY_MARGIN)) - prompt_reserve


@dataclass(frozen=True)
class MessagesSegment:
    """A segment of rendered messages that fits within a token budget.

    Attributes:
        messages: The original ChatMessage objects in this segment.
        messages_str: Pre-rendered string from messages_as_str.
        segment: 0-based segment index, auto-increments across yields.
    """

    messages: list[ChatMessage]
    messages_str: str
    segment: int


async def segment_messages(
    source: list[ChatMessage] | list[Event] | TimelineSpan,
    *,
    messages_as_str: MessagesAsStr,
    model: Model | str | None = None,
    context_window: int | None = None,
    compaction: Literal["all", "last"] | int = "all",
    prompt_reserve: int | float = 0.2,
) -> AsyncIterator[MessagesSegment]:
    """Render messages and split them into segments that fit within a token budget.

    Renders each message individually via ``messages_as_str``, groups
    the rendered messages into chunks and counts tokens per chunk (one
    ``count_tokens`` call each, with bounded concurrency), then packs
    chunks into segments that fit within the effective budget (context
    window minus the portion reserved by ``prompt_reserve``).

    When given events or a ``TimelineSpan``, delegates to
    ``span_messages()`` to extract and merge messages (handling
    compaction boundaries), then segments the result.

    Args:
        source: A list of ChatMessage, a list of Event, or a
            TimelineSpan. Events and spans are processed via
            ``span_messages()`` first.
        messages_as_str: Rendering function from ``message_numbering()``.
            Must be called sequentially to preserve counter ordering.
        model: Model used for token counting.
        context_window: Override for context window size. If None,
            looked up via ``get_model_info(model)``.
        compaction: How to handle compaction boundaries when source
            contains events. Passed through to ``span_messages()``.
        prompt_reserve: Context-window allowance for prompt scaffolding
            wrapped around the rendered messages (e.g. a scanner
            template). A ``float`` reserves that fraction of the window;
            an ``int`` reserves that many tokens and additionally
            subtracts a small safety margin for ``count_tokens``
            imprecision. Default ``0.2`` leaves 80% of the window for
            messages.

    Yields:
        MessagesSegment instances, each fitting within the token budget.
        Segment counter increments across all yields.
    """
    # Resolve model
    model = get_model(model)

    # Resolve source to a flat message list
    if isinstance(source, TimelineSpan):
        messages = span_messages(source, compaction=compaction)
    elif source and isinstance(source[0], ChatMessageBase):
        messages = list(source)  # type: ignore[arg-type, unused-ignore]
    elif source:
        messages = span_messages(source, compaction=compaction)  # type: ignore[arg-type]
    else:
        messages = []

    if not messages:
        return

    # Compute effective budget
    effective_budget = max(
        1,
        _effective_segment_budget(
            model=model,
            context_window=context_window,
            prompt_reserve=prompt_reserve,
        ),
    )

    # Pass 1: Render each message sequentially (counter ordering matters)
    rendered: list[tuple[ChatMessage, str]] = []
    for msg in messages:
        text = await messages_as_str([msg])
        if text:  # Skip empty renders (e.g. filtered system messages)
            rendered.append((msg, text))

    if not rendered:
        return

    # Pass 2: Group messages into chunks and count tokens per chunk
    # (see _COUNT_* constants above for why counting is chunked).
    chunk_char_target = max(
        1,
        int(
            effective_budget * _COUNT_CHUNK_BUDGET_FRACTION * _COUNT_EST_CHARS_PER_TOKEN
        ),
    )
    chunks: list[list[tuple[ChatMessage, str]]] = [[]]
    chunk_chars = 0
    for msg, text in rendered:
        if chunks[-1] and chunk_chars + len(text) > chunk_char_target:
            chunks.append([])
            chunk_chars = 0
        chunks[-1].append((msg, text))
        chunk_chars += len(text)

    count_limiter = anyio.Semaphore(_COUNT_MAX_CONCURRENCY)

    async def count_chunk(text: str) -> int:
        async with count_limiter:
            return await model.count_tokens(text)

    chunk_texts = ["\n".join(text for _, text in chunk) for chunk in chunks]
    token_counts = await tg_collect(
        [lambda t=text: count_chunk(t) for text in chunk_texts]  # type: ignore[misc]
    )

    # Pass 3: Segment based on accumulated chunk token counts
    segment_counter = 0
    current_messages: list[ChatMessage] = []
    current_texts: list[str] = []
    running_tokens = 0

    for chunk, tokens in zip(chunks, token_counts, strict=True):
        if current_messages and running_tokens + tokens > effective_budget:
            yield MessagesSegment(
                messages=current_messages,
                messages_str="\n".join(current_texts),
                segment=segment_counter,
            )
            segment_counter += 1
            current_messages = []
            current_texts = []
            running_tokens = 0

        current_messages.extend(msg for msg, _ in chunk)
        current_texts.extend(text for _, text in chunk)
        running_tokens += tokens

    # Yield remaining segment
    if current_messages:
        yield MessagesSegment(
            messages=current_messages,
            messages_str="\n".join(current_texts),
            segment=segment_counter,
        )


async def stream_segment_messages(
    source: AsyncIterator[ChatMessage],
    *,
    messages_as_str: MessagesAsStr,
    model: Model | str | None = None,
    context_window: int | None = None,
    prompt_reserve: int | float = 0.2,
) -> AsyncIterator[MessagesSegment]:
    """Incrementally render and segment messages from an async iterator.

    Streaming counterpart to ``segment_messages()``: instead of requiring
    the full message list up front, consumes ``source`` one message at a
    time and yields ``MessagesSegment`` instances as soon as enough
    messages have accumulated to fill a segment. This lets callers (e.g.
    ``llm_scanner``) start processing the first segment before the rest
    of the transcript has been read.

    Messages are rendered sequentially via ``messages_as_str`` (counter
    ordering matters) and grouped into chunks up to ``chunk_char_target``
    (same sizing formula as ``segment_messages()``). Each chunk is
    counted with a single ``count_tokens`` call as soon as it closes —
    calls are serialized rather than batched with bounded concurrency,
    since chunks aren't known ahead of time.

    Args:
        source: An async iterator of ChatMessage.
        messages_as_str: Rendering function from ``message_numbering()``.
            Must be called sequentially to preserve counter ordering.
        model: Model used for token counting.
        context_window: Override for context window size. If None,
            looked up via ``get_model_info(model)``.
        prompt_reserve: Context-window allowance for prompt scaffolding
            wrapped around the rendered messages (e.g. a scanner
            template). A ``float`` reserves that fraction of the window;
            an ``int`` reserves that many tokens and additionally
            subtracts a small safety margin for ``count_tokens``
            imprecision. Default ``0.2`` leaves 80% of the window for
            messages.

    Yields:
        MessagesSegment instances, each fitting within the token budget
        (except a single chunk that alone exceeds the budget, which is
        still yielded on its own). Segment counter increments across
        all yields.
    """
    # Resolve model
    model = get_model(model)

    # Compute effective budget
    effective_budget = max(
        1,
        _effective_segment_budget(
            model=model,
            context_window=context_window,
            prompt_reserve=prompt_reserve,
        ),
    )

    chunk_char_target = max(
        1,
        int(
            effective_budget * _COUNT_CHUNK_BUDGET_FRACTION * _COUNT_EST_CHARS_PER_TOKEN
        ),
    )

    segment_counter = 0
    current_messages: list[ChatMessage] = []
    current_texts: list[str] = []
    running_tokens = 0

    pending_chunk: list[tuple[ChatMessage, str]] = []
    pending_chars = 0

    async def close_chunk() -> tuple[list[ChatMessage], list[str], int]:
        """Count tokens for the pending chunk and return its contents."""
        nonlocal pending_chunk, pending_chars
        chunk_messages = [msg for msg, _ in pending_chunk]
        chunk_texts = [text for _, text in pending_chunk]
        chunk_str = "\n".join(chunk_texts)
        tokens = await model.count_tokens(chunk_str)
        pending_chunk = []
        pending_chars = 0
        return chunk_messages, chunk_texts, tokens

    async for msg in source:
        text = await messages_as_str([msg])
        if not text:  # Skip empty renders (e.g. filtered system messages)
            continue

        if pending_chunk and pending_chars + len(text) > chunk_char_target:
            chunk_messages, chunk_texts, tokens = await close_chunk()

            if current_messages and running_tokens + tokens > effective_budget:
                yield MessagesSegment(
                    messages=current_messages,
                    messages_str="\n".join(current_texts),
                    segment=segment_counter,
                )
                segment_counter += 1
                current_messages = []
                current_texts = []
                running_tokens = 0

            current_messages.extend(chunk_messages)
            current_texts.extend(chunk_texts)
            running_tokens += tokens

        pending_chunk.append((msg, text))
        pending_chars += len(text)

    # Flush the final pending chunk
    if pending_chunk:
        chunk_messages, chunk_texts, tokens = await close_chunk()

        if current_messages and running_tokens + tokens > effective_budget:
            yield MessagesSegment(
                messages=current_messages,
                messages_str="\n".join(current_texts),
                segment=segment_counter,
            )
            segment_counter += 1
            current_messages = []
            current_texts = []
            running_tokens = 0

        current_messages.extend(chunk_messages)
        current_texts.extend(chunk_texts)
        running_tokens += tokens

    # Yield the final segment
    if current_messages:
        yield MessagesSegment(
            messages=current_messages,
            messages_str="\n".join(current_texts),
            segment=segment_counter,
        )


async def transcript_messages(
    transcript: "Transcript",
    *,
    messages_as_str: MessagesAsStr,
    model: Model | str | None = None,
    context_window: int | None = None,
    timeline: str | None = None,
    compaction: Literal["all", "last"] | int = "all",
    depth: int | None = None,
    include_scorers: bool = False,
    prompt_reserve: int | float = 0.2,
    events: EventsSpec | None = None,
) -> AsyncIterator[MessagesSegment]:
    """Yield pre-rendered message segments from a transcript.

    Automatically selects the best extraction strategy based on
    what data is available on the transcript:

    - If timelines are present, delegates to ``timeline_messages()``
    - If events are present (no timelines), delegates to
      ``segment_messages()`` with compaction handling
    - If only messages are present, delegates to ``segment_messages()``
      for context window segmentation only

    By default, scorer events are excluded from extraction. This
    applies to both the timeline path (the scorers span is pruned)
    and the events path (the scorers section is removed).

    Since ``TimelineMessages`` is structurally compatible with
    ``MessagesSegment``, callers get a uniform interface. Those needing
    span context can isinstance-check for ``TimelineMessages``.

    Args:
        transcript: The transcript to extract messages from.
        messages_as_str: Rendering function from ``message_numbering()``.
        model: The model used for scanning.
        context_window: Override for the model's context window size.
        timeline: Name of the timeline to extract from. ``None``
            (default) uses the transcript's first timeline. Raises
            ``ValueError`` if no timeline with the given name exists.
        compaction: How to handle compaction boundaries when extracting
            messages from events.
        depth: Maximum nesting level of scannable spans to process when
            timelines are present. Counts only spans that actually get
            scanned — non-scannable container and utility spans are
            transparent. ``1`` = outermost scannable spans on each
            branch; ``None`` (default) = unlimited. Ignored for
            events-only or messages-only paths.
        include_scorers: Whether to include scorer events in message
            extraction. Defaults to ``False``.
        prompt_reserve: Context-window allowance for prompt scaffolding
            wrapped around the rendered messages (e.g. a scanner
            template). A ``float`` reserves that fraction of the window;
            an ``int`` reserves that many tokens (plus a small safety
            margin). Default ``0.2`` leaves 80% of the window for
            messages. Forwarded to ``segment_messages()`` /
            ``timeline_messages()``.
        events: Which non-message event types to interleave into each
            span's message thread as marked entries (``"all"``, a
            list of event types, or ``None`` to disable interleaving).
            Only affects the timeline path. When set, span-external
            events (events outside any scannable span's direct
            content, e.g. root-level events or a pruned ``scorers``
            span's events) are collected from the unpruned timeline
            via ``collect_span_external()`` before the ``scorers``
            prune, then forwarded to ``timeline_messages()`` alongside
            ``events`` so they are spliced into the appropriate span.

    Yields:
        ``MessagesSegment`` (or ``TimelineMessages``) for each segment.

    Raises:
        ValueError: If ``timeline`` names a timeline that does not
            exist on the transcript.
    """
    if transcript.timelines or transcript.events:
        from inspect_ai.event import timeline_build, timeline_filter

        from inspect_scout._transcript.timeline import timeline_messages

        # must deal with a timeline for sane message extraction
        if transcript.timelines:
            timelines = transcript.timelines
        else:
            # build a synthetic timeline from events
            timelines = [timeline_build(transcript.events)]

        if timeline is not None:
            selected = next((t for t in timelines if t.name == timeline), None)
            if selected is None:
                raise ValueError(
                    f"Timeline '{timeline}' not found in transcript "
                    f"'{transcript.transcript_id}'. Available timelines: "
                    f"{[t.name for t in timelines]}"
                )
        else:
            selected = timelines[0]

        span_external: dict[str, list[tuple[str, str]]] | None = None
        if events is not None:
            from inspect_scout._transcript.interleave import collect_span_external

            # See collect_span_external()'s docstring for why the
            # scorers span is included here when it will be pruned
            # below (its events must be collected before they're lost)
            # but filtered out here when it will survive pruning (its
            # events are instead spliced in directly as an ordinary
            # scannable span, and collecting them here too would
            # double-render them).
            collection_source = (
                timeline_filter(selected, lambda s: s.span_type != "scorers")
                if include_scorers
                else selected
            )
            span_external = collect_span_external(collection_source, events)

        if not include_scorers:
            selected = timeline_filter(selected, lambda s: s.span_type != "scorers")

        async for timeline_seg in timeline_messages(
            selected,
            messages_as_str=messages_as_str,
            model=model,
            context_window=context_window,
            compaction=compaction,
            depth=depth,
            prompt_reserve=prompt_reserve,
            events=events,
            span_external=span_external,
        ):
            yield timeline_seg  # type: ignore[misc]
    else:
        if timeline is not None:
            raise ValueError(
                f"Timeline '{timeline}' not found in transcript "
                f"'{transcript.transcript_id}'. Transcript has no timelines."
            )
        async for seg in segment_messages(
            transcript.messages,
            messages_as_str=messages_as_str,
            model=model,
            context_window=context_window,
            prompt_reserve=prompt_reserve,
        ):
            yield seg


def _exclude_scorers(events: list[Event]) -> list[Event]:
    """Remove events belonging to the top-level scorers section.

    Uses ``event_tree()`` to find the scorers span, removes it from the
    tree, then flattens back to a sequence with ``event_sequence()``.
    """
    tree = event_tree(events)
    filtered = [
        item
        for item in tree
        if not (isinstance(item, EventTreeSpan) and item.name == "scorers")
    ]
    if len(filtered) == len(tree):
        return events  # no scorers found, return original
    return list(event_sequence(filtered))


@overload
def span_messages(
    source: Timeline | TimelineSpan | list[Event],
    *,
    compaction: Literal["all", "last"] | int = "all",
    split_compactions: Literal[False] = False,
) -> list[ChatMessage]: ...


@overload
def span_messages(
    source: Timeline | TimelineSpan | list[Event],
    *,
    compaction: Literal["all", "last"] | int = "all",
    split_compactions: Literal[True],
) -> list[list[ChatMessage]]: ...


def span_messages(
    source: Timeline | TimelineSpan | list[Event],
    *,
    compaction: Literal["all", "last"] | int = "all",
    split_compactions: bool = False,
) -> list[ChatMessage] | list[list[ChatMessage]]:
    """Extract messages from a span or event list, handling compaction.

    Filters for ``ModelEvent`` and ``CompactionEvent``, then merges
    messages into a single list based on the ``compaction`` strategy.

    Args:
        source: A ``Timeline`` (extracts ``.root``), ``TimelineSpan``
            (events extracted from its content), or a raw list of events.
            Non-Model/Compaction events are ignored.
        compaction: How to handle compaction boundaries:
            - ``"all"``: merge across boundaries for full coverage.
              Summary grafts pre + post messages. Trim prepends the
              trimmed prefix. Edit is transparent.
            - ``"last"``: ignore compaction history, return only the
              last ``ModelEvent``'s input + output.
            - ``int``: keep the last *N* compaction regions.  ``1`` is
              equivalent to ``"last"``.  If *N* exceeds the number of
              regions the result is the same as ``"all"``.
        split_compactions: When ``True``, return one inner list per
            compaction region instead of merging into a flat list.
            The ``compaction`` parameter still controls how many regions
            to keep before splitting.

    Returns:
        When ``split_compactions`` is ``False`` (default): merged message
        list. When ``True``: one ``list[ChatMessage]`` per kept region.
        Empty list if no ``ModelEvent`` is found.
    """
    # Normalize Timeline to TimelineSpan
    if isinstance(source, Timeline):
        source = source.root

    # Extract events from TimelineSpan if needed
    if isinstance(source, TimelineSpan):
        events = [
            item.event for item in source.content if isinstance(item, TimelineEvent)
        ]
    else:
        events = source

    # Filter to ModelEvents and CompactionEvents
    model_events: list[ModelEvent] = []
    for event in events:
        if isinstance(event, ModelEvent):
            model_events.append(event)

    if not model_events:
        return []

    # Normalize compaction to n: int | None
    n: int | None
    if compaction == "last":
        n = 1
    elif compaction == "all":
        n = None
    else:
        n = compaction

    # "last 1" shortcut: just return the final ModelEvent's messages
    if n == 1:
        msgs = _segment_messages(model_events[-1])
        return [msgs] if split_compactions else msgs

    # If n is specified, slice events to keep only the last n regions.
    # Regions are separated by CompactionEvents.
    if n is not None:
        compaction_indices = [
            i for i, event in enumerate(events) if isinstance(event, CompactionEvent)
        ]
        num_regions = len(compaction_indices) + 1
        if n < num_regions:
            # Keep the last n regions.  The nth-from-last region starts
            # right after the compaction event at position -(n) from the
            # end of compaction_indices.
            cut_index = compaction_indices[-(n)]
            events = events[cut_index:]

    # Split mode: return one list per compaction region
    if split_compactions:
        regions: list[list[ChatMessage]] = []
        current_model_events: list[ModelEvent] = []

        for event in events:
            if isinstance(event, ModelEvent):
                current_model_events.append(event)
            elif isinstance(event, CompactionEvent):
                if current_model_events:
                    regions.append(_segment_messages(current_model_events[-1]))
                current_model_events = []

        if current_model_events:
            regions.append(_segment_messages(current_model_events[-1]))

        return regions

    # Merge across compaction boundaries
    merged: list[ChatMessage] = []
    current_model_events_merge: list[ModelEvent] = []
    pending_trim_pre_input: list[ChatMessage] | None = None

    for event in events:
        if isinstance(event, ModelEvent):
            # If we have a pending trim, compute prefix now that we have
            # the first post-compaction ModelEvent
            if pending_trim_pre_input is not None:
                prefix = _trim_prefix(pending_trim_pre_input, list(event.input))
                merged.extend(prefix)
                pending_trim_pre_input = None

            current_model_events_merge.append(event)

        elif isinstance(event, CompactionEvent):
            if event.type == "summary":
                # Graft pre-compaction messages onto the merged list
                if current_model_events_merge:
                    merged.extend(_segment_messages(current_model_events_merge[-1]))
                current_model_events_merge = []

            elif event.type == "trim":
                # Save pre-compaction input for prefix extraction
                if current_model_events_merge:
                    pending_trim_pre_input = list(current_model_events_merge[-1].input)
                current_model_events_merge = []

            # Edit: no action, continue accumulating

    # Append final segment
    if current_model_events_merge:
        merged.extend(_segment_messages(current_model_events_merge[-1]))

    return merged


def span_tools(source: Timeline | TimelineSpan | list[Event]) -> list[ToolInfo]:
    """Extract the tool definitions that were in scope across a span.

    Companion to ``span_messages()``: where that function reconstructs
    the message history from ``ModelEvent`` inputs/outputs, this
    function reconstructs the set of tools that were declared to the
    model. Callers that want to continue or interrogate a recorded
    conversation typically need both — the messages to replay and the
    tool definitions to re-declare.

    Iterates ``ModelEvent.tools`` across the source and returns the
    union of ``ToolInfo`` definitions, deduplicated by name. When a
    tool name appears more than once (e.g. tools added or redefined
    mid-conversation), the last-seen definition wins.

    Args:
        source: A ``Timeline`` (extracts ``.root``), ``TimelineSpan``
            (events extracted from its content), or a raw list of
            events. Non-``ModelEvent`` events are ignored.

    Returns:
        Deduplicated list of ``ToolInfo`` in first-seen order, with
        each entry holding the last-seen definition for that name.
        Empty list if no ``ModelEvent`` declared any tools.
    """
    # Normalize Timeline to TimelineSpan
    if isinstance(source, Timeline):
        source = source.root

    # Extract events from TimelineSpan if needed
    if isinstance(source, TimelineSpan):
        events = [
            item.event for item in source.content if isinstance(item, TimelineEvent)
        ]
    else:
        events = source

    tools: dict[str, ToolInfo] = {}
    for event in events:
        if isinstance(event, ModelEvent):
            for tool in event.tools:
                tools[tool.name] = tool
    return list(tools.values())


def _segment_messages(model_event: ModelEvent) -> list[ChatMessage]:
    """Extract the conversation from a ModelEvent.

    Returns the model's input messages plus its output message
    (the assistant's response).

    Args:
        model_event: The ModelEvent to extract messages from.

    Returns:
        List of messages: input + output assistant message.
        Returns just the input if output is unavailable.
    """
    messages = list(model_event.input)
    if (
        model_event.output is not None
        and model_event.output.choices
        and model_event.output.choices[0].message is not None
    ):
        messages.append(model_event.output.choices[0].message)
    return messages


def _trim_prefix(
    pre_input: list[ChatMessage],
    post_input: list[ChatMessage],
) -> list[ChatMessage]:
    """Compute the messages trimmed by a trim compaction.

    Finds the overlap point between pre-compaction and post-compaction
    inputs, returning the prefix of pre-compaction messages that were
    dropped.

    Uses message ``id`` fields for matching. Falls back to content
    equality (``message.text``) when IDs don't match.

    Args:
        pre_input: Full conversation before trim compaction.
        post_input: Trimmed conversation after trim compaction.

    Returns:
        Messages from pre_input that were dropped by the trim.
        Empty list if no prefix was trimmed or inputs can't be aligned.
    """
    if not post_input or not pre_input:
        return []

    # Try matching by message id
    first_post_id = post_input[0].id
    if first_post_id is not None:
        for i, msg in enumerate(pre_input):
            if msg.id == first_post_id:
                return pre_input[:i]

    # Fall back to content equality: find the first message in pre_input
    # whose text matches the first post_input message
    first_post_text = post_input[0].text
    for i, msg in enumerate(pre_input):
        if msg.text == first_post_text and msg.role == post_input[0].role:
            return pre_input[:i]

    return []
