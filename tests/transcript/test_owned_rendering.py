"""Tests for ``span_owned_messages``."""

from __future__ import annotations

import pytest
from inspect_ai.event import (
    AnchorEvent,
    BranchEvent,
    CompactionEvent,
    ModelEvent,
    SampleLimitEvent,
    ScoreEvent,
    TimelineSpan,
)
from inspect_ai.model import ChatMessage, ChatMessageUser, ModelOutput
from inspect_ai.scorer import Score
from inspect_scout._scanner.extract import EVENT_MARKER_KEY
from inspect_scout._transcript.interleave import (
    Compaction,
    EventsSpec,
    span_owned_messages,
)
from inspect_scout._transcript.timeline import TimelineEvent, walk_owned_spans

from tests.transcript.span_builders import _model_event, _span, _span_of


def _texts(messages: list[ChatMessage]) -> list[str]:
    return [m.text for m in messages]


def _marker_texts(messages: list[ChatMessage]) -> list[str]:
    return [m.text for m in messages if (m.metadata or {}).get(EVENT_MARKER_KEY)]


def _render(
    root: TimelineSpan,
    *,
    events: EventsSpec = "all",
    compaction: Compaction = "all",
) -> list[list[ChatMessage]]:
    return [
        span_owned_messages(owned, events=events, compaction=compaction)
        for owned in walk_owned_spans(root)
    ]


def _cumulative_owner(span_id: str = "o") -> tuple[TimelineSpan, list[ModelEvent]]:
    """Owner with two cumulative turns: thread [task, a1, next, a2]."""
    out1 = ModelOutput.from_content(model="mockllm", content="a1")
    a1 = out1.choices[0].message
    q1 = ChatMessageUser(content="task")
    ev1 = _model_event([q1], out1)
    q2 = ChatMessageUser(content="next")
    out2 = ModelOutput.from_content(model="mockllm", content="a2")
    ev2 = _model_event([q1, a1, q2], out2)
    return _span(span_id, "main", [ev1, ev2]), [ev1, ev2]


def test_foreign_model_event_sharing_a_compacted_turn_id_still_renders() -> None:
    """Only the owner's own turns are hidden as compaction-pruned."""
    out1 = ModelOutput.from_content(model="mockllm", content="pre")
    ev1 = _model_event([ChatMessageUser(content="q")], out1)
    comp = CompactionEvent.model_construct(
        event="compaction", type="summary", span_id="o"
    )
    out2 = ModelOutput.from_content(model="mockllm", content="post")
    ev2 = _model_event([ChatMessageUser(content="q2")], out2)
    owner = _span("o", "main", [ev1, comp, ev2])
    for item in owner.content:
        if isinstance(item, TimelineEvent):
            item.event.span_id = "o"

    # Same id as the owner's pruned pre-compaction turn; the child never
    # compacted, so its output must still render.
    fork_out = ModelOutput.from_content(model="mockllm", content="pre")
    fork_out.choices[0].message.id = out1.choices[0].message.id
    fork_ev = _model_event([ChatMessageUser(content="fq")], fork_out)
    fork_ev.span_id = "child"
    child = _span_of("child", "helper", [fork_ev])
    child = child.model_copy(update={"utility": True})
    owner.content.append(child)

    [rendered] = _render(owner, compaction="last")
    assert any("pre" in t for t in _marker_texts(rendered)), (
        "foreign fork output was suppressed as compaction-pruned"
    )


def test_foreign_model_events_bypass_the_events_filter_but_others_obey_it() -> None:
    owner, _ = _cumulative_owner()
    fork_out = ModelOutput.from_content(model="mockllm", content="FORK")
    child = _span_of(
        "c",
        "helper",
        [
            _model_event([ChatMessageUser(content="sq")], fork_out),
            ScoreEvent(score=Score(value=1.0), scorer="s"),
            SampleLimitEvent.model_construct(
                event="sample_limit", type="message", limit=1, message="lim"
            ),
        ],
    )
    child = child.model_copy(update={"utility": True})
    owner.content.append(child)

    [rendered] = _render(owner, events=["score"])
    markers = "\n".join(_marker_texts(rendered))
    assert "FORK" in markers
    assert "SCORE" in markers
    assert "LIMIT" not in markers


def test_grouped_branches_splice_consecutively_and_empty_key_appends() -> None:
    owner, (ev1, _) = _cumulative_owner()
    anchor_id = ev1.output.choices[0].message.id
    assert anchor_id is not None

    def mk_branch(bid: str, text: str, anchor: str) -> TimelineSpan:
        out = ModelOutput.from_content(model="mockllm", content=text)
        b = _span_of(
            bid,
            "branch",
            [
                BranchEvent(from_anchor=anchor),
                _model_event([ChatMessageUser(content="bq")], out),
            ],
        )
        return b.model_copy(update={"branched_from": anchor or None})

    b1 = mk_branch("b1", "ALT1", anchor_id)
    b2 = mk_branch("b2", "ALT2", anchor_id)  # grouped duplicate key
    b3 = mk_branch("b3", "ALT3", "")  # "" -> unmatched, appends
    owner_wrapped = owner.model_copy(update={"branches": [b1, b2, b3]})

    [rendered] = _render(owner_wrapped)
    texts = _texts(rendered)
    is_marker = [bool((m.metadata or {}).get(EVENT_MARKER_KEY)) for m in rendered]
    p1 = next(i for i, t in enumerate(texts) if "ALT1" in t)
    p2 = next(i for i, t in enumerate(texts) if "ALT2" in t)
    p3 = next(i for i, t in enumerate(texts) if "ALT3" in t)
    # Grouped duplicates splice consecutively at the one resolved index: no
    # thread (non-marker) message may separate ALT1 from ALT2.
    assert p1 < p2 < texts.index("a2")
    assert all(is_marker[i] for i in range(p1, p2 + 1))
    # "" resolves unmatched and appends at the very end.
    assert p3 > texts.index("a2")


@pytest.mark.parametrize(
    ("foreign_first", "thread_at", "marker_at"), [(True, 1, 0), (False, 0, 2)]
)
def test_branch_splices_after_the_turn_and_its_entries(
    foreign_first: bool, thread_at: int, marker_at: int
) -> None:
    """The splice point counts [E#] entries that lead the thread or follow the turn."""
    out = ModelOutput.from_content(model="mockllm", content="a")
    ev = _model_event([ChatMessageUser(content="q")], out)
    owner = _span("o", "main", [ev])
    anchor_id = out.choices[0].message.id
    assert anchor_id is not None

    foreign = SampleLimitEvent.model_construct(
        event="sample_limit", type="message", limit=1, message="lim"
    )
    sub = _span_of("sub", "helper", [foreign])
    sub = sub.model_copy(update={"utility": True})
    if foreign_first:
        owner.content.insert(0, sub)
    else:
        owner.content.append(sub)

    alt_out = ModelOutput.from_content(model="mockllm", content="ALT")
    branch = _span_of(
        "b",
        "branch",
        [
            BranchEvent(from_anchor=anchor_id),
            _model_event([ChatMessageUser(content="bq")], alt_out),
        ],
    )
    branch = branch.model_copy(update={"branched_from": anchor_id})
    owner_wrapped = owner.model_copy(update={"branches": [branch]})

    [rendered] = _render(owner_wrapped)
    texts = _texts(rendered)
    is_marker = [bool((m.metadata or {}).get(EVENT_MARKER_KEY)) for m in rendered]
    assert texts[thread_at : thread_at + 2] == ["q", "a"]
    assert is_marker[marker_at]
    alt_pos = next(i for i, t in enumerate(texts) if "ALT" in t)
    assert alt_pos == len(texts) - 1


def test_branch_splices_at_an_anchor_event_not_only_a_message_id() -> None:
    """`branched_from` can name the `AnchorEvent` that `timeline_branch` emits."""
    owner, _ = _cumulative_owner()
    anchor_id = "anchor-1"
    alt_out = ModelOutput.from_content(model="mockllm", content="ALT")
    branch = _span_of(
        "b",
        "branch",
        [
            BranchEvent(from_anchor=anchor_id),
            _model_event([ChatMessageUser(content="bq")], alt_out),
        ],
    )
    branch = branch.model_copy(update={"branched_from": anchor_id})

    # the anchor sits between the two turns, as timeline_branch emits it
    content = list(owner.content)
    owner_wrapped = owner.model_copy(
        update={
            "content": [
                content[0],
                TimelineEvent(event=AnchorEvent(anchor_id=anchor_id)),
                *content[1:],
            ],
            "branches": [branch],
        }
    )

    [rendered] = _render(owner_wrapped)
    texts = _texts(rendered)
    alt_pos = next(i for i, t in enumerate(texts) if "ALT" in t)
    assert texts.index("a1") < alt_pos < texts.index("a2"), (
        "branch must splice at its anchor, not append after the last turn"
    )
