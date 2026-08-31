"""Rendering tests.

Hazards 1-4, both anchor-steal doors, filter rules, branch positioning
(design §2/§4).
"""

from __future__ import annotations

from inspect_ai.event import (
    BranchEvent,
    ModelEvent,
    SampleLimitEvent,
    ScoreEvent,
    TimelineSpan,
    ToolEvent,
)
from inspect_ai.model import ChatMessage, ChatMessageUser, ModelOutput
from inspect_ai.scorer import Score
from inspect_scout._scanner.extract import EVENT_MARKER_KEY
from inspect_scout._transcript.interleave import (
    Compaction,
    EventsSpec,
    span_owned_messages,
)
from inspect_scout._transcript.timeline import walk_owned_spans

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
    """Owner with two cumulative turns: thread [q, a1, q2, a2]."""
    out1 = ModelOutput.from_content(model="mockllm", content="a1")
    a1 = out1.choices[0].message
    q1 = ChatMessageUser(content="task")
    ev1 = _model_event([q1], out1)
    q2 = ChatMessageUser(content="next")
    out2 = ModelOutput.from_content(model="mockllm", content="a2")
    ev2 = _model_event([q1, a1, q2], out2)
    return _span(span_id, "main", [ev1, ev2]), [ev1, ev2]


def test_hazard1_descendant_model_event_never_replaces_owner_thread() -> None:
    owner, _ = _cumulative_owner()
    sub_out = ModelOutput.from_content(model="mockllm", content="SUB-CONVO")
    sub = _span_of(
        "sub", "helper", [_model_event([ChatMessageUser(content="sq")], sub_out)]
    )
    sub = sub.model_copy(update={"utility": True})
    owner.content.append(sub)

    [rendered] = _render(owner)
    texts = _texts(rendered)
    assert "a1" in texts and "a2" in texts  # owner thread intact
    assert any("SUB-CONVO" in t for t in _marker_texts(rendered))  # marker only
    non_marker_texts = [
        t
        for m, t in zip(rendered, texts, strict=True)
        if not (m.metadata or {}).get(EVENT_MARKER_KEY)
    ]
    assert "SUB-CONVO" not in non_marker_texts


def test_hazard2a_foreign_model_event_sharing_output_id_cannot_steal_anchor() -> None:
    """The design's (sub_e, owner_e1, owner_e2) repro, now via ownership."""
    owner, (ev1, ev2) = _cumulative_owner()
    stolen_id = ev1.output.choices[0].message.id
    sub_out = ModelOutput.from_content(model="mockllm", content="a1")
    sub_out.choices[0].message.id = stolen_id  # same output id as owner turn 1
    sub = _span_of(
        "sub", "helper", [_model_event([ChatMessageUser(content="sq")], sub_out)]
    )
    sub = sub.model_copy(update={"utility": True})
    owner.content.insert(0, sub)  # foreign arrives FIRST

    [rendered] = _render(owner)
    texts = _texts(rendered)
    # Owner's genuine a1 stays ON-thread, exactly once (not stolen or
    # duplicated); the foreign copy renders separately as exactly one
    # MODEL (BRANCH) marker (never the bare "a1" -- _off_thread_model_text
    # always prefixes the marker, so the two can never collide textually).
    assert texts.count("a1") == 1  # on-thread a1, untouched
    markers = _marker_texts(rendered)
    assert len([t for t in markers if "a1" in t]) == 1


def test_hazard2b_tool_nested_model_event_cannot_steal_anchor() -> None:
    from inspect_ai.event import TimelineEvent

    owner, (ev1, ev2) = _cumulative_owner()
    stolen_id = ev2.output.choices[0].message.id
    sub_out = ModelOutput.from_content(model="mockllm", content="a2")
    sub_out.choices[0].message.id = stolen_id
    nested = _model_event([ChatMessageUser(content="nq")], sub_out)
    tool = ToolEvent.model_construct(
        event="tool", id="t1", function="f", arguments={}, result="", events=[nested]
    )
    # The agent-unset ToolEvent sits as DIRECT content between the two turns
    # (hazard 2 door b: nested events bypass any tree traversal at HEAD).
    owner.content.insert(1, TimelineEvent.model_construct(type="event", event=tool))

    [rendered] = _render(owner)
    markers = _marker_texts(rendered)
    assert len([t for t in markers if "a2" in t]) == 1  # branch marker, once
    assert _texts(rendered).count("a2") == 1  # on-thread a2, untouched


def test_hazard3_compacted_foreign_fork_output_still_renders() -> None:
    """Regression: hidden compaction-excluded id must still render.

    compaction_spans derives from OWN items only: a foreign ModelEvent whose
    output id matches a compaction-excluded id must still render (the 'hid
    another agent's genuine fork output' regression, design hazard 3).
    """
    from inspect_ai.event import CompactionEvent, TimelineEvent

    # Owner with a summary compaction: two regions, compaction="all" merges.
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

    # Foreign child whose model output DUPLICATES the pre-compaction turn's
    # id: under compaction="last" that id is excluded_ids-listed for the
    # owner, but the child's span never compacted -> must render as BRANCH.
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


def test_foreign_nonmodel_events_obey_events_filter() -> None:
    owner, _ = _cumulative_owner()
    child = _span_of(
        "c",
        "helper",
        [
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
    assert "SCORE" in markers
    assert "LIMIT" not in markers  # filtered, though foreign


def test_foreign_model_event_renders_unconditionally() -> None:
    owner, _ = _cumulative_owner()
    sub_out = ModelOutput.from_content(model="mockllm", content="FORK")
    sub = _span_of(
        "sub", "helper", [_model_event([ChatMessageUser(content="sq")], sub_out)]
    )
    sub = sub.model_copy(update={"utility": True})
    owner.content.append(sub)

    [rendered] = _render(owner, events=["score"])  # filter excludes model
    assert any("FORK" in t for t in _marker_texts(rendered))


def test_branch_splices_at_resolved_output_id_after_anchored_entries() -> None:
    owner, (ev1, ev2) = _cumulative_owner()
    anchor_id = ev1.output.choices[0].message.id
    assert anchor_id is not None
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
    alt_pos = next(i for i, t in enumerate(texts) if "ALT" in t)
    a1_pos = texts.index("a1")
    a2_pos = texts.index("a2")
    assert a1_pos < alt_pos < a2_pos  # mid-thread, not appended


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
    # "" resolves unmatched and appends at the very end (decision 5).
    assert p3 > texts.index("a2")


def test_branch_insertion_skips_leading_foreign_marker_sharing_anchor_id() -> None:
    """Second EventId->MessageId laundering site (the rendered-list scan).

    A foreign event's ``uuid`` is laundered into its rendered marker's
    ``ChatMessage.id`` (see ``EventId``'s docstring, ``_scanner/util.py``).
    When that uuid collides with a real thread message's id, resolution
    must still land on the real turn, not the marker. Here the foreign
    event arrives *before* the owner's sole turn, so its marker renders
    leading (before the whole thread): a scan over the rendered list would
    match it first at index 0 and splice the branch between the marker and
    the real thread. Occurrence-mapped resolution never looks at rendered
    entries at all, so the collision is unreachable by construction.
    """
    out = ModelOutput.from_content(model="mockllm", content="a")
    ev = _model_event([ChatMessageUser(content="q")], out)
    owner = _span("o", "main", [ev])
    anchor_id = out.choices[0].message.id
    assert anchor_id is not None

    foreign = SampleLimitEvent.model_construct(
        event="sample_limit", type="message", limit=1, message="lim"
    )
    foreign.uuid = anchor_id  # collide with the owner's own output message id
    sub = _span_of("sub", "helper", [foreign])
    sub = sub.model_copy(update={"utility": True})
    owner.content.insert(0, sub)  # foreign marker renders leading (before "q")

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
    assert is_marker[0]  # the colliding foreign marker renders leading
    assert texts[1] == "q" and texts[2] == "a"  # real thread intact, in order
    alt_pos = next(i for i, t in enumerate(texts) if "ALT" in t)
    # Thread position: appended after "a" (no thread message follows it in
    # this single-turn owner), never wedged between the leading marker and "q".
    assert alt_pos == len(texts) - 1


def test_branch_insertion_skips_trailing_foreign_marker_sharing_anchor_id() -> None:
    """Same collision, mirrored document order (companion to the leading case).

    The foreign event now arrives *after* the owner's sole turn, so its
    marker renders trailing "a" rather than leading. This shape resolved
    correctly even under the old rendered-list scan (the real message came
    first); it pins that the branch still lands after the turn AND its
    anchored entries -- the job ``spliced_position_after`` now does by
    counting them rather than by skipping over them.
    """
    out = ModelOutput.from_content(model="mockllm", content="a")
    ev = _model_event([ChatMessageUser(content="q")], out)
    owner = _span("o", "main", [ev])
    anchor_id = out.choices[0].message.id
    assert anchor_id is not None

    foreign = SampleLimitEvent.model_construct(
        event="sample_limit", type="message", limit=1, message="lim"
    )
    foreign.uuid = anchor_id  # collide with the owner's own output message id
    sub = _span_of("sub", "helper", [foreign])
    sub = sub.model_copy(update={"utility": True})
    owner.content.append(sub)  # foreign marker renders trailing (after "a")

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
    assert texts[0] == "q" and texts[1] == "a"  # real thread intact, in order
    assert is_marker[2]  # the colliding foreign marker trails "a"
    alt_pos = next(i for i, t in enumerate(texts) if "ALT" in t)
    assert alt_pos == len(texts) - 1  # after "a" AND its trailing marker


def test_branch_positions_after_output_turn_when_input_shares_its_id() -> None:
    """Cross-role duplicate: an INPUT message carrying the OUTPUT's id.

    The owner's user message and its assistant output both carry id ``X``.
    Resolution is event-level over the owner's OWN items and the design's
    id tier narrowing admits output ids and ``ToolEvent.message_id`` only
    (§4), so ``branched_from="X"`` names the model EVENT and the block must
    splice after that event's turn -- after ``a``, never between ``q`` and
    ``a``. Viewer parity: ``findEventByMessageId``'s first pass matches the
    output event (contentItems.ts:145), and only its third (input-id) pass
    could reach ``q`` -- the tier this design deliberately does not use.
    """
    out = ModelOutput.from_content(model="mockllm", content="a")
    q = ChatMessageUser(content="q")
    q.id = "X"
    out.choices[0].message.id = "X"
    owner = _span("o", "main", [_model_event([q], out)])

    alt_out = ModelOutput.from_content(model="mockllm", content="ALT")
    branch = _span_of(
        "b",
        "branch",
        [
            BranchEvent(from_anchor="X"),
            _model_event([ChatMessageUser(content="bq")], alt_out),
        ],
    )
    branch = branch.model_copy(update={"branched_from": "X"})
    owner_wrapped = owner.model_copy(update={"branches": [branch]})

    [rendered] = _render(owner_wrapped)
    texts = _texts(rendered)
    assert texts[0] == "q" and texts[1] == "a"  # thread intact, in order
    a_pos = texts.index("a")
    # The WHOLE block lands after the output turn: its BranchEvent marker
    # and its MODEL (BRANCH) entry alike.
    branch_pos = next(i for i, t in enumerate(texts) if t.startswith("BRANCH"))
    alt_pos = next(i for i, t in enumerate(texts) if "ALT" in t)
    assert a_pos < branch_pos < alt_pos


def test_branch_insertion_resolves_duplicate_real_message_id_to_first_occurrence() -> (
    None
):
    """Viewer parity: a duplicate id shared by two REAL output turns.

    No markers involved. Both occurrences are genuine model outputs, and
    each turn's own ``ModelEvent`` consumes one in document order, so the
    branch resolves to the FIRST consumed occurrence -- the same first-wins
    answer the earlier rendered-list scan gave, and the one the viewer
    gives (``findEventByMessageId`` returns its first match).
    """
    out1 = ModelOutput.from_content(model="mockllm", content="a1")
    q1 = ChatMessageUser(content="task")
    ev1 = _model_event([q1], out1)
    dup_id = out1.choices[0].message.id
    assert dup_id is not None

    q2 = ChatMessageUser(content="next")
    out2 = ModelOutput.from_content(model="mockllm", content="a2")
    out2.choices[0].message.id = dup_id  # duplicate real output id
    ev2 = _model_event([q1, out1.choices[0].message, q2], out2)
    owner = _span("o", "main", [ev1, ev2])

    alt_out = ModelOutput.from_content(model="mockllm", content="ALT")
    branch = _span_of(
        "b",
        "branch",
        [
            BranchEvent(from_anchor=dup_id),
            _model_event([ChatMessageUser(content="bq")], alt_out),
        ],
    )
    branch = branch.model_copy(update={"branched_from": dup_id})
    owner_wrapped = owner.model_copy(update={"branches": [branch]})

    [rendered] = _render(owner_wrapped)
    texts = _texts(rendered)
    alt_pos = next(i for i, t in enumerate(texts) if "ALT" in t)
    # Resolves to the FIRST occurrence (a1's), not the second (a2's).
    assert texts.index("a1") < alt_pos < texts.index("a2")
