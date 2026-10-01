"""Seeded flat-event-list generator + brute-force ownership reference.

The generator emits the *flat event list* shape (what `timeline_build`
consumes), so the same corpus drives both the per-span timeline path and
the flat driver (oracle 2).
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
                nested.append(
                    _model_event(ids, sub_thread, f"{label}-nested{i}", span_id=None)
                )
                if rng.random() < 0.5:  # doubly-nested tool-in-tool
                    inner: list[Event] = [
                        _model_event(
                            ids,
                            [ChatMessageUser(content="iq")],
                            f"{label}-inner{i}",
                            span_id=None,
                        )
                    ]
                    nested.append(_tool(ids, None, inner, message_id=None))
                # agent-unset ToolEvent: stays a leaf in the tree
                events.append(_tool(ids, sid, nested, message_id=thread[-1].id))
        return thread

    def branch(parent_sid: str, anchor: str | None, label: str) -> None:
        # Mirrors timeline_branch's emitter: a span whose first event is a
        # BranchEvent. timeline_build only groups span_type="branch" spans
        # into .branches.
        sid = begin(f"branch-{label}", "branch", parent_sid)
        events.append(
            BranchEvent.model_construct(
                event="branch",
                uuid=ids.next("u"),
                span_id=sid,
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
        events.append(
            _model_event(ids, main_thread, "main-after-util", span_id=main_sid)
        )
    elif shape < 0.6:
        # branch: anchored to the last main output, or "" (no anchor)
        anchor = main_thread[-1].id if rng.random() < 0.7 else None
        branch(main_sid, anchor, "b1")
        if rng.random() < 0.5:  # grouped duplicate branched_from
            branch(main_sid, anchor, "b2")
    end(main_sid, root_sid)

    # Root-level events after main's span ends: timeline_build homes them as
    # orphans ahead of everything else, while the flat driver places them
    # after main's last message, so they also gate `flat_comparable`.
    has_root_level_trailing = rng.random() < 0.5
    if has_root_level_trailing:
        events.append(_score(ids, root_sid))
        events.append(
            SampleLimitEvent.model_construct(
                event="sample_limit",
                uuid=ids.next("u"),
                span_id=root_sid,
                type="message",
                limit=10,
                message="limit",
            )
        )
    end(root_sid, None)

    if rng.random() < 0.6:
        # Top-level scorers sibling of solvers, as Inspect emits it: the flat
        # driver only recognises top-level scorers by name. timeline_build
        # flattens a top-level scorers subtree, so the nested grader's
        # ModelEvent becomes a direct event of the scorers span; the other
        # half has no ModelEvent at all.
        sc_sid = begin("scorers", "scorers", None)
        if rng.random() < 0.5:
            grader_sid = begin("grader", "agent", sc_sid)
            gthread: list[ChatMessage] = [ChatMessageUser(content="grade this")]
            events.append(
                _model_event(ids, gthread, "grader assessment", span_id=grader_sid)
            )
            events.append(_info(ids, "GRADER-INFO", grader_sid))
            end(grader_sid, sc_sid)
        else:
            events.append(_info(ids, "grader-info-no-model", sc_sid))
        events.append(_score(ids, sc_sid))
        end(sc_sid, None)

    # Oracle 2's precondition: main's linear thread is the only non-grader
    # conversation (no nested walked span, no branches) and no root-level
    # trailing events.
    flat_comparable = 0.25 <= shape < 0.45 and not has_root_level_trailing
    messages: list[ChatMessage] = list(main_thread) if flat_comparable else []
    return GeneratedTranscript(events, messages, flat_comparable)


# --- brute-force ownership reference (oracle 3) -----------------------------


def _walked_pre_order(
    span: TimelineSpan,
    *,
    depth: int | None,
    include_scorers: bool,
    _in_scorers: bool = False,
    _scannable_depth: int = 0,
) -> Iterator[TimelineSpan]:
    """Pre-order walked spans, never entering .branches."""
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
                item,
                depth=depth,
                include_scorers=include_scorers,
                _in_scorers=in_scorers,
                _scannable_depth=next_depth,
            )


def _document_events(
    span: TimelineSpan,
    *,
    include_scorers: bool,
    _in_scorers: bool = False,
    _chain: tuple[str, ...] = (),
) -> Iterator[tuple[Event, tuple[str, ...], bool, bool]]:
    """(event, ancestor-chain innermost-last, is_branch, is_direct) in doc order.

    Recurses into ``ToolEvent.events`` (yielded with ``is_direct=False``) and
    ``.branches``. With include_scorers=False only the scorers subtree's
    ModelEvents are dropped; its other events still render.
    """
    in_scorers = _in_scorers or span.span_type == "scorers"
    suppress_models = in_scorers and not include_scorers
    chain = _chain + (span.id,)

    def flat(event: Event, *, direct: bool = True) -> Iterator[tuple[Event, bool]]:
        if not (suppress_models and isinstance(event, ModelEvent)):
            yield event, direct
        if isinstance(event, ToolEvent):
            for nested in event.events:
                yield from flat(nested, direct=False)

    # Branches before content: a span's branches take the owner in force at
    # the span's start, before its content can start a nested walked span
    # and move tier-2 `latest` (mirrors walk_owned_spans).
    for b in span.branches:
        # Replay cut: from the first direct BranchEvent on; a branch with none
        # contributes everything.
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
        for e, c, _, is_direct in _document_events(
            live, include_scorers=include_scorers, _in_scorers=in_scorers, _chain=chain
        ):
            yield e, c, True, is_direct
    for item in span.content:
        if isinstance(item, TimelineEvent):
            for e, is_direct in flat(item.event):
                yield e, chain, False, is_direct
        else:
            yield from _document_events(
                item,
                include_scorers=include_scorers,
                _in_scorers=in_scorers,
                _chain=chain,
            )


def all_event_uuids(root: TimelineSpan, *, include_scorers: bool) -> list[str]:
    return [
        e.uuid
        for e, _, _, _ in _document_events(root, include_scorers=include_scorers)
        if e.uuid is not None
    ]


def branch_event_uuids(root: TimelineSpan) -> set[str]:
    return {
        e.uuid
        for e, _, is_branch, _ in _document_events(root, include_scorers=True)
        if is_branch and e.uuid is not None
    }


def expected_owners(
    root: TimelineSpan, *, depth: int | None, include_scorers: bool
) -> dict[str, str]:
    """Uuid -> owner span id; "" = orphan. Slow and obviously correct."""
    walked = list(_walked_pre_order(root, depth=depth, include_scorers=include_scorers))
    walked_ids = [s.id for s in walked]
    owners: dict[str, str] = {}
    latest = ""  # tier 2: latest-STARTING walked span; "" until one starts
    started: set[str] = set()
    for event, chain, _is_branch, _is_direct in _document_events(
        root, include_scorers=include_scorers
    ):
        # Tier 1: nearest enclosing walked ancestor. A branch event's chain
        # passes through the span carrying .branches, so branches ride it.
        enclosing = [sid for sid in chain if sid in walked_ids]
        owner = enclosing[-1] if enclosing else latest  # tier 2 (or "" = tier 3)
        # `latest` moves on first touch only: after a nested walked span ends,
        # the outer span tier-1-owns its later events, but the nested span is
        # still the latest to have started.
        for sid in chain:
            if sid in walked_ids and sid not in started:
                started.add(sid)
                latest = sid
        if event.uuid is not None:
            owners[event.uuid] = owner
    # Tier-3 orphans preceding the first walked span lead it.
    if walked_ids:
        owners = {u: (walked_ids[0] if o == "" else o) for u, o in owners.items()}
    return owners


def expected_anchor_message_ids(
    root: TimelineSpan, *, depth: int | None, include_scorers: bool
) -> dict[str, str | None]:
    """Uuid -> output id of the owner's last preceding own ModelEvent.

    None when the event leads the owner's thread. Branch events are absent
    (they position by branched_from). Only sound for compaction-free trees.
    """
    owners = expected_owners(root, depth=depth, include_scorers=include_scorers)
    walked_ids = {
        s.id
        for s in _walked_pre_order(root, depth=depth, include_scorers=include_scorers)
    }
    last_model_output: dict[str, str | None] = {sid: None for sid in walked_ids}
    anchors: dict[str, str | None] = {}
    for event, chain, is_branch, is_direct in _document_events(
        root, include_scorers=include_scorers
    ):
        if is_branch or event.uuid is None:
            continue
        owner = owners[event.uuid]
        anchors[event.uuid] = last_model_output.get(owner)
        # Only a ModelEvent directly in the owner span is own. One from a
        # non-walked descendant (e.g. "sub" collapsed into "main" at depth=1)
        # is foreign: its output is never on the owner's thread.
        if is_direct and chain[-1] == owner and isinstance(event, ModelEvent):
            mid = event.output.choices[0].message.id
            if mid is not None:
                last_model_output[owner] = mid
    return anchors
