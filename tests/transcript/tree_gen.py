"""Seeded flat-event-list generator + brute-force ownership reference.

The generator emits the *flat event list* shape (what `timeline_build`
consumes), so the same corpus drives the materialized path, the streaming
path (via MaterializedTranscriptHandle), and the flat driver (oracle 2).
"""

from __future__ import annotations

import random
from typing import Iterator, NamedTuple

from inspect_ai.event import (
    BranchEvent,
    Event,
    InfoEvent,
    ModelEvent,
    SampleLimitEvent,
    ScoreEvent,
    SpanBeginEvent,
    SpanEndEvent,
    TimelineEvent,
    TimelineSpan,
    ToolEvent,
)
from inspect_ai.model import ChatMessage, ChatMessageUser, GenerateConfig, ModelOutput
from inspect_ai.scorer import Score
from inspect_scout._transcript.timeline import span_is_scannable

CORPUS_SEEDS = range(200)


class GeneratedTranscript(NamedTuple):
    events: list[Event]
    messages: list[ChatMessage]
    flat_comparable: bool
    seed: int


class _Ids:
    def __init__(self, seed: int) -> None:
        self._seed = seed
        self._n = 0

    def next(self, kind: str) -> str:
        self._n += 1
        return f"{kind}{self._seed}-{self._n}"


def _model_event(
    ids: _Ids, thread: list[ChatMessage], text: str, *, span_id: str | None
) -> ModelEvent:
    out = ModelOutput.from_content(model="mockllm", content=text)
    out.choices[0].message.id = ids.next("m")
    ev = ModelEvent.model_construct(
        event="model",
        uuid=ids.next("u"),
        span_id=span_id,
        model="mockllm",
        input=list(thread),
        output=out,
        role="assistant",
        config=GenerateConfig(),
    )
    thread.append(out.choices[0].message)
    return ev


def _info(ids: _Ids, text: str, span_id: str | None) -> InfoEvent:
    return InfoEvent.model_construct(
        event="info", uuid=ids.next("u"), span_id=span_id, source=None, data=text
    )


def _score(ids: _Ids, span_id: str | None) -> ScoreEvent:
    return ScoreEvent.model_construct(
        event="score",
        uuid=ids.next("u"),
        span_id=span_id,
        score=Score(value=1.0),
        scorer="gen",
    )


def _tool(
    ids: _Ids, span_id: str | None, nested: list[Event], *, message_id: str | None
) -> ToolEvent:
    return ToolEvent.model_construct(
        event="tool",
        uuid=ids.next("u"),
        span_id=span_id,
        id=ids.next("t"),
        function="gen_tool",
        arguments={},
        result="ok",
        events=nested,
        message_id=message_id,
    )


def generate(seed: int) -> GeneratedTranscript:
    rng = random.Random(seed)
    ids = _Ids(seed)
    events: list[Event] = []

    def begin(name: str, span_type: str | None, parent: str | None) -> str:
        sid = ids.next("s")
        events.append(
            SpanBeginEvent.model_construct(
                event="span_begin",
                uuid=ids.next("u"),
                id=sid,
                span_id=parent,
                parent_id=parent,
                type=span_type,
                name=name,
            )
        )
        return sid

    def end(sid: str, parent: str | None) -> None:
        events.append(
            SpanEndEvent.model_construct(
                event="span_end", uuid=ids.next("u"), id=sid, span_id=parent
            )
        )

    def agent_turns(sid: str, n: int, label: str) -> list[ChatMessage]:
        thread: list[ChatMessage] = [ChatMessageUser(content=f"{label}-q")]
        thread[0].id = ids.next("m")
        for i in range(n):
            events.append(_model_event(ids, thread, f"{label}-a{i}", span_id=sid))
            if rng.random() < 0.4:
                events.append(_info(ids, f"{label}-info{i}", sid))
            if rng.random() < 0.3:
                nested: list[Event] = []
                sub_thread: list[ChatMessage] = [ChatMessageUser(content="nq")]
                nested.append(_model_event(ids, sub_thread, f"{label}-nested{i}", span_id=None))
                if rng.random() < 0.5:  # doubly-nested tool-in-tool
                    inner: list[Event] = [
                        _model_event(ids, [ChatMessageUser(content="iq")], f"{label}-inner{i}", span_id=None)
                    ]
                    nested.append(_tool(ids, None, inner, message_id=None))
                # agent-unset ToolEvent: stays a leaf in the tree
                events.append(_tool(ids, sid, nested, message_id=thread[-1].id))
        return thread

    def branch(parent_sid: str, anchor: str | None, label: str) -> None:
        # Mirrors timeline_branch's emitter shape: span whose first event is
        # a BranchEvent(from_anchor=...). Real emitter uses span_type="branch"
        # (event/_timeline.py:530-548) -- _process_children/_find_branch_event
        # only groups EventTreeSpan.type == "branch" runs into .branches
        # (event/_timeline.py:933-955), so the span_type here must be
        # "branch", not "agent".
        sid = begin(f"branch-{label}", "branch", parent_sid)
        events.append(
            BranchEvent.model_construct(
                event="branch", uuid=ids.next("u"), span_id=sid,
                from_anchor=anchor or "",
            )
        )
        thread: list[ChatMessage] = [ChatMessageUser(content=f"{label}-bq")]
        events.append(_model_event(ids, thread, f"{label}-balt", span_id=sid))
        end(sid, parent_sid)

    # --- compose the transcript -------------------------------------------
    root_sid = begin("solvers", "solvers", None)
    main_sid = begin("main", "agent", root_sid)
    main_thread = agent_turns(main_sid, rng.randint(1, 3), "main")

    shape = rng.random()
    if shape < 0.25:
        # nested walked sub-agent between main turns, then more main turns
        sub_sid = begin("sub", "agent", main_sid)
        agent_turns(sub_sid, 2, "sub")
        end(sub_sid, main_sid)
        events.append(_model_event(ids, main_thread, "main-late", span_id=main_sid))
    elif shape < 0.45:
        # utility-shaped non-walked child (no direct ModelEvent) with events
        util_sid = begin("helper", "agent", main_sid)
        events.append(_info(ids, "helper-info", util_sid))
        events.append(_score(ids, util_sid))
        end(util_sid, main_sid)
        events.append(_model_event(ids, main_thread, "main-after-util", span_id=main_sid))
    elif shape < 0.6:
        # branch: anchored to the last main output, or "" (no anchor)
        anchor = main_thread[-1].id if rng.random() < 0.7 else None
        branch(main_sid, anchor, "b1")
        if rng.random() < 0.5:  # grouped duplicate branched_from
            branch(main_sid, anchor, "b2")
    end(main_sid, root_sid)

    if rng.random() < 0.5:
        # root-level events between/after walked spans
        events.append(_score(ids, root_sid))
        events.append(
            SampleLimitEvent.model_construct(
                event="sample_limit", uuid=ids.next("u"), span_id=root_sid,
                type="message", limit=10, message="limit"
            )
        )
    end(root_sid, None)

    if rng.random() < 0.6:
        # TOP-LEVEL scorers section, as real Inspect logs emit it (a sibling
        # of solvers, not nested under it — the flat driver's scorer_span_ids
        # only recognises top-level-by-name scorers, and oracle 2 depends on
        # both drivers agreeing on grader exclusion for comparable shapes).
        #
        # timeline_build fully flattens a top-level scorers span's subtree
        # via event_sequence() (event/_timeline.py:481-484) -- nested spans
        # (e.g. a "grader" agent span) do NOT survive as nested TimelineSpans,
        # they dissolve into flat TimelineEvents alongside their own
        # span_begin/span_end. So a nested "grader" span with a ModelEvent
        # still leaves a *direct* ModelEvent on the flattened "scoring" span.
        # Half the time we build the "double-render" shape via a nested
        # grader span (still has a direct ModelEvent once flattened); the
        # other half we skip the ModelEvent entirely so some scorers
        # sections are genuinely without a direct model event.
        sc_sid = begin("scorers", "scorers", None)
        if rng.random() < 0.5:
            grader_sid = begin("grader", "agent", sc_sid)
            gthread: list[ChatMessage] = [ChatMessageUser(content="grade this")]
            events.append(_model_event(ids, gthread, "grader assessment", span_id=grader_sid))
            events.append(_info(ids, "GRADER-INFO", grader_sid))
            end(grader_sid, sc_sid)
        else:
            events.append(_info(ids, "grader-info-no-model", sc_sid))
        events.append(_score(ids, sc_sid))
        end(sc_sid, None)

    # Flat-comparable (oracle 2's precondition): main's single linear thread
    # is the only non-grader conversation — no nested walked span (shape <
    # 0.25 has one), no branches (0.45 <= shape < 0.6 has them).
    flat_comparable = 0.25 <= shape < 0.45
    messages: list[ChatMessage] = list(main_thread) if flat_comparable else []
    return GeneratedTranscript(events, messages, flat_comparable, seed)


# --- brute-force ownership reference (design Oracle 3) ----------------------


def _walked_pre_order(
    span: TimelineSpan,
    *,
    depth: int | None,
    include_scorers: bool,
    _in_scorers: bool = False,
    _scannable_depth: int = 0,
) -> Iterator[TimelineSpan]:
    """Pre-order walked spans, never entering .branches (design §1)."""
    if depth is not None and depth <= 0:
        return
    in_scorers = _in_scorers or span.span_type == "scorers"
    scannable = span_is_scannable(span) and not (in_scorers and not include_scorers)
    if scannable:
        next_depth = _scannable_depth + 1
        if depth is None or next_depth <= depth:
            yield span
    else:
        next_depth = _scannable_depth
    for item in span.content:
        if isinstance(item, TimelineSpan):
            yield from _walked_pre_order(
                item, depth=depth, include_scorers=include_scorers,
                _in_scorers=in_scorers, _scannable_depth=next_depth,
            )


def _document_events(
    span: TimelineSpan,
    *,
    include_scorers: bool,
    _in_scorers: bool = False,
    _chain: tuple[str, ...] = (),
) -> Iterator[tuple[Event, tuple[str, ...], bool]]:
    """(event, ancestor-span-id-chain innermost-last, is_branch) in doc order.

    Recurses into the ToolEvent.events closure (decision 6) and .branches.
    Skips scorers subtrees entirely when include_scorers=False.
    """
    in_scorers = _in_scorers or span.span_type == "scorers"
    if in_scorers and not include_scorers:
        return
    chain = _chain + (span.id,)

    def flat(event: Event) -> Iterator[Event]:
        yield event
        if isinstance(event, ToolEvent):
            for nested in event.events:
                yield from flat(nested)

    for item in span.content:
        if isinstance(item, TimelineEvent):
            for e in flat(item.event):
                yield e, chain, False
        else:
            yield from _document_events(
                item, include_scorers=include_scorers,
                _in_scorers=in_scorers, _chain=chain,
            )
    for b in span.branches:
        # Same replay-cut CONTRACT as walk_owned_spans (design §4), different
        # mechanism: splice from the first direct BranchEvent onward; a
        # branch with none contributes everything.
        cut = next(
            (
                i
                for i, item in enumerate(b.content)
                if isinstance(item, TimelineEvent)
                and isinstance(item.event, BranchEvent)
            ),
            None,
        )
        live = b if cut is None else b.model_copy(update={"content": b.content[cut:]})
        for e, c, _ in _document_events(
            live, include_scorers=include_scorers, _in_scorers=in_scorers, _chain=chain
        ):
            yield e, c, True


def all_event_uuids(
    root: TimelineSpan, *, include_scorers: bool
) -> list[str]:
    return [
        e.uuid
        for e, _, _ in _document_events(root, include_scorers=include_scorers)
        if e.uuid is not None
    ]


def branch_event_uuids(root: TimelineSpan) -> set[str]:
    return {
        e.uuid
        for e, _, is_branch in _document_events(root, include_scorers=True)
        if is_branch and e.uuid is not None
    }


def expected_owners(
    root: TimelineSpan, *, depth: int | None, include_scorers: bool
) -> dict[str, str]:
    """Uuid -> owner span id; "" = orphan. Slow and obviously correct."""
    walked = list(
        _walked_pre_order(root, depth=depth, include_scorers=include_scorers)
    )
    walked_ids = [s.id for s in walked]
    owners: dict[str, str] = {}
    latest = ""  # tier 3 until the first walked span starts
    for event, chain, _is_branch in _document_events(
        root, include_scorers=include_scorers
    ):
        # Tier 1: nearest enclosing walked ancestor (innermost wins). For a
        # branch event the chain passes through the span CARRYING .branches,
        # so this also implements §4's carriage rule. Because
        # _document_events is first-touch document order, a walked span's
        # first appearance in any chain marks its start, keeping `latest`
        # equal to "latest-starting walked span preceding the event" (tier 2).
        enclosing = [sid for sid in chain if sid in walked_ids]
        if enclosing:
            owner = enclosing[-1]
            latest = owner
        else:
            owner = latest  # tier 2 (or "" = tier 3)
        if event.uuid is not None:
            owners[event.uuid] = owner
    # Tier-3 orphans preceding the first walked span lead it (design §1/§3).
    if walked_ids:
        owners = {
            u: (walked_ids[0] if o == "" else o) for u, o in owners.items()
        }
    return owners
