import re
from typing import Iterable

import pytest
from inspect_ai.event import (
    AnchorEvent,
    BranchEvent,
    CompactionEvent,
    ErrorEvent,
    EventTreeSpan,
    ModelEvent,
    ScoreEvent,
    SpanBeginEvent,
    SpanEndEvent,
    Timeline,
    TimelineEvent,
    TimelineSpan,
    ToolEvent,
    event_sequence,
    event_tree,
    timeline_build,
)
from inspect_ai.event._checkpoint import CheckpointEvent
from inspect_ai.event._event import Event
from inspect_ai.log import EvalError
from inspect_ai.model import (
    ChatMessage,
    ChatMessageUser,
    GenerateConfig,
    Model,
    ModelOutput,
    get_model,
)
from inspect_ai.scorer import Score
from inspect_ai.tool import ToolChoice, ToolInfo
from inspect_scout import llm_scanner
from inspect_scout._scanner.extract import EVENT_MARKER_KEY
from inspect_scout._scanner.result import Result
from inspect_scout._scanner.scanner import SCANNER_CONTENT_ATTR
from inspect_scout._scanner.util import _event_id
from inspect_scout._transcript.interleave import (
    INTERLEAVE_DEPENDENCIES,
    EventsOnlyInterleaveUnsupported,
    EventsSpec,
    _interleavable_text,
    interleave_events,
    scorer_span_ids,
    span_owned_messages,
)
from inspect_scout._transcript.timeline import walk_owned_spans
from inspect_scout._transcript.types import (
    EventType,
    Transcript,
    TranscriptContent,
)


def _model_event(user_text: str, output: ModelOutput) -> ModelEvent:
    return ModelEvent.model_construct(
        event="model",
        model="mockllm",
        input=[ChatMessageUser(content=user_text)],
        output=output,
        role="assistant",
        config=GenerateConfig(),
    )


def _span_model_event(question: str, answer: str, span_id: str) -> ModelEvent:
    """A ModelEvent carrying a span_id, for span-structure fixtures."""
    out = ModelOutput.from_content(model="mockllm", content=answer)
    return ModelEvent(
        span_id=span_id,
        model="mockllm",
        input=[ChatMessageUser(content=question)],
        output=out,
        role="assistant",
        tools=[],
        tool_choice="auto",
        config=GenerateConfig(),
    )


def _span(span_id: str, name: str, content: list[Event | TimelineSpan]) -> TimelineSpan:
    """Build a scannable ``TimelineSpan`` from a mix of events and nested spans."""
    items: list[TimelineEvent | TimelineSpan] = [
        item
        if isinstance(item, TimelineSpan)
        else TimelineEvent.model_construct(type="event", event=item)
        for item in content
    ]
    return TimelineSpan(id=span_id, name=name, span_type="agent", content=items)


def _rendered(messages: list[ChatMessage]) -> list[str]:
    """Message texts, with marked event entries collapsed to ``E:<heading>``."""
    return [
        f"E:{m.text.split(':')[0].strip()}"
        if m.metadata and m.metadata.get(EVENT_MARKER_KEY)
        else m.text
        for m in messages
    ]


@pytest.mark.parametrize(
    ("after_turn_1", "after_turn_2", "expected"),
    [
        pytest.param(
            [],
            ["match"],
            ["q1", "first", "q2", "second", "E:SCORE (match)"],
            id="after-last-assistant",
        ),
        pytest.param(
            ["graded"],
            [],
            ["q1", "first", "E:SCORE (graded)", "q2", "second"],
            id="mid-thread",
        ),
        pytest.param(
            [],
            ["s1", "s2"],
            ["q1", "first", "q2", "second", "E:SCORE (s1)", "E:SCORE (s2)"],
            id="multiple-on-one-anchor-keep-order",
        ),
    ],
)
def test_events_anchor_after_the_turn_they_followed(
    after_turn_1: list[str], after_turn_2: list[str], expected: list[str]
) -> None:
    """Each event splices in after the assistant turn it chronologically followed."""
    out1 = ModelOutput.from_content(model="mockllm", content="first")
    out2 = ModelOutput.from_content(model="mockllm", content="second")
    u1, u2 = ChatMessageUser(content="q1"), ChatMessageUser(content="q2")

    def scores(scorers: list[str]) -> list[Event]:
        return [
            ScoreEvent(score=Score(value="C"), target="C", scorer=s) for s in scorers
        ]

    transcript = Transcript(
        transcript_id="t",
        messages=[u1, out1.choices[0].message, u2, out2.choices[0].message],
        events=[
            _model_event("q1", out1),
            *scores(after_turn_1),
            _model_event("q2", out2),
            *scores(after_turn_2),
        ],
    )
    assert _rendered(interleave_events(transcript)) == expected


def test_no_events_returns_messages_unchanged() -> None:
    user = ChatMessageUser(content="hi")
    transcript = Transcript(transcript_id="t", messages=[user], events=[])
    assert interleave_events(transcript) == [user]


def test_duplicate_message_ids_do_not_duplicate_events() -> None:
    # Two assistant turns with identical text and no explicit ids share the
    # same fallback _message_id (md5 of text). Each event must still splice
    # after its own turn, exactly once.
    out1 = ModelOutput.from_content(model="mockllm", content="yes")
    out2 = ModelOutput.from_content(model="mockllm", content="yes")
    a1, a2 = out1.choices[0].message, out2.choices[0].message
    a1.id = None
    a2.id = None
    u1 = ChatMessageUser(content="q1", id="u1")
    u2 = ChatMessageUser(content="q2", id="u2")
    transcript = Transcript(
        transcript_id="t",
        messages=[u1, a1, u2, a2],
        events=[
            _model_event("q1", out1),
            ScoreEvent(score=Score(value=0.5), scorer="graded", intermediate=True),
            _model_event("q2", out2),
            ScoreEvent(score=Score(value="C"), target="C", scorer="match"),
        ],
    )
    result = interleave_events(transcript)
    assert len(result) == 6
    assert result[2].text.startswith("SCORE (graded)")
    assert result[5].text.startswith("SCORE (match)")
    event_count = sum(
        1 for m in result if m.metadata and m.metadata.get(EVENT_MARKER_KEY)
    )
    assert event_count == 2


def test_idless_duplicate_text_fork_steals_anchor_known_limitation() -> None:
    """Pins a KNOWN LIMITATION of the id-less text-hash fallback.

    When messages lack real ids and a fork's output text equals a later
    on-thread turn's text, the fork consumes the occurrence meant for the
    real turn (occurrence consumption is order-based, not identity-aware):
    the fork's own content vanishes and the real turn misrenders as a
    ``MODEL (BRANCH)`` entry. Inspect auto-mints message ids at
    construction and deserialization, so this input shape is only
    constructible synthetically (or by a non-Inspect importer that emits
    id-less messages). See ``_AnchorWalk``'s docstring for the escalation
    path (uuid-keyed anchoring) if such an importer appears.

    This test asserts the CURRENT (wrong-but-accepted) behavior so any
    change to it — fix or further regression — is a deliberate, visible
    decision rather than a silent one.
    """
    out1 = ModelOutput.from_content(model="mockllm", content="yes")
    fork_out = ModelOutput.from_content(model="mockllm", content="yes")
    out2 = ModelOutput.from_content(model="mockllm", content="yes")
    a1, a2 = out1.choices[0].message, out2.choices[0].message
    a1.id = None
    a2.id = None
    fork_out.choices[0].message.id = None
    u1 = ChatMessageUser(content="q1", id="u1")
    u2 = ChatMessageUser(content="q2", id="u2")
    transcript = Transcript(
        transcript_id="t",
        messages=[u1, a1, u2, a2],
        events=[
            _model_event("q1", out1),
            _model_event("FORK", fork_out),
            _model_event("q2", out2),
        ],
    )
    result = interleave_events(transcript)
    # The fork steals a2's occurrence and is itself absorbed (no entry of
    # its own); the REAL second turn's event then finds no occurrence left
    # and misrenders as a branch entry appended after a2.
    branch_entries = [
        m for m in result if m.metadata and m.metadata.get(EVENT_MARKER_KEY)
    ]
    assert len(branch_entries) == 1
    assert "MODEL (BRANCH):" in branch_entries[0].text
    # The real thread itself is still rendered intact.
    assert [m.text for m in result if m not in branch_entries] == [
        u1.text,
        a1.text,
        u2.text,
        a2.text,
    ]


def _compaction_pruned_and_fork_transcript() -> Transcript:
    """Messages-present transcript with a compaction-pruned turn and a genuine fork.

    `transcript.messages` carries only the live, post-compaction thread
    (`q2`/`a2`) -- the common shape: append-only `ModelEvent`s (including
    pre-compaction ones) in `events`, with `messages` reflecting whatever
    compaction the original run already applied.

    - `ev1`'s output (`a1`, "first") is compacted away: it IS a member of
      the untruncated `compaction="all"` reconstruction of `events` (as the
      region-1 last event) but is NOT in `transcript.messages` -- the
      compaction-pruned case. It must stay hidden, never rendered as a
      branch entry.
    - `fork_ev` is a genuine fork: same prompt as `ev1` re-asked with a
      fresh (unchained) input after the compaction boundary, whose output
      is superseded within its own region by `ev2` (the region's actual
      last event) and therefore never joins the thread at any `compaction`
      value, unlike `ev1`. It must render exactly once as a
      `[E#] MODEL (BRANCH):` entry.
    """
    out1 = ModelOutput.from_content(model="mockllm", content="first")
    ev1 = _model_event("q1", out1)
    compaction_event = CompactionEvent(type="summary")
    fork_out = ModelOutput.from_content(model="mockllm", content="forked")
    fork_ev = _model_event("q1", fork_out)
    out2 = ModelOutput.from_content(model="mockllm", content="second")
    a2 = out2.choices[0].message
    ev2 = _model_event("q2", out2)
    u2 = ChatMessageUser(content="q2")

    return Transcript(
        transcript_id="t",
        messages=[u2, a2],
        events=[ev1, compaction_event, fork_ev, ev2],
    )


def test_messages_present_hides_compaction_pruned_turn() -> None:
    """Messages-present path: compaction-pruned turn hidden, genuine fork still renders.

    Regression test: `excluded_ids` must be computed on the messages-present
    path too (the common shape), not just the events-only reconstruction
    branches of `interleave_events` -- otherwise every compacted-away turn's
    output leaks through as a spurious `[E#] MODEL (BRANCH):` entry. See
    `_compaction_pruned_and_fork_transcript`.
    """
    transcript = _compaction_pruned_and_fork_transcript()
    result = interleave_events(transcript)

    combined = "\n".join(m.text for m in result)
    assert "first" not in combined  # compaction-pruned turn stays hidden

    branch_entries = [m for m in result if "MODEL (BRANCH):" in m.text]
    assert len(branch_entries) == 1  # genuine fork renders exactly once
    assert "forked" in branch_entries[0].text

    # The live thread itself renders unaffected, exactly once each.
    non_branch_texts = [m.text for m in result if "MODEL (BRANCH):" not in m.text]
    assert non_branch_texts == ["q2", "second"]


def _scorers_span_transcript() -> Transcript:
    """Transcript whose grader model call sits in a top-level `scorers` span."""
    out = ModelOutput.from_content(model="mockllm", content="4")
    assistant = out.choices[0].message
    user = ChatMessageUser(content="2+2?")
    model_event = ModelEvent(
        span_id="span-main",
        model="mockllm",
        input=[user],
        output=out,
        role="assistant",
        tools=[],
        tool_choice="auto",
        config=GenerateConfig(),
    )
    grader_out = ModelOutput.from_content(model="mockllm", content="grader assessment")
    grader_event = ModelEvent(
        span_id="span-scorers",
        model="mockllm",
        input=[ChatMessageUser(content="grade this")],
        output=grader_out,
        role="assistant",
        tools=[],
        tool_choice="auto",
        config=GenerateConfig(),
    )
    score_event = ScoreEvent(
        span_id="span-scorers", scorer="match", score=Score(value="C")
    )
    transcript = Transcript(
        transcript_id="t",
        messages=[user, assistant],
        events=[
            SpanBeginEvent(
                id="span-main",
                parent_id=None,
                type="agent",
                name="main",
                span_id="span-main",
            ),
            model_event,
            SpanEndEvent(id="span-main", span_id="span-main"),
            SpanBeginEvent(
                id="span-scorers",
                parent_id=None,
                type="scorers",
                name="scorers",
                span_id="span-scorers",
            ),
            grader_event,
            score_event,
            SpanEndEvent(id="span-scorers", span_id="span-scorers"),
        ],
    )
    return transcript


def _event_texts(messages: Iterable[ChatMessage]) -> list[str]:
    return [m.text for m in messages if m.metadata and m.metadata.get(EVENT_MARKER_KEY)]


def test_grader_model_event_in_scorers_span_excluded() -> None:
    """A grader ModelEvent inside a top-level `scorers` span never renders.

    Mirrors the timeline-path invariant
    (`test_scorers_span_score_event_attaches_to_last_scannable_span` in
    `test_timeline_interleave.py`) on the flat `interleave_events` driver:
    grader model calls must never surface as branch entries even though,
    unlike the per-span path, there is no structural span boundary to stop
    the walk -- `scorer_span_ids` must exclude them explicitly.
    The scorer's own `ScoreEvent` is unaffected and still renders once.
    """
    event_texts = _event_texts(interleave_events(_scorers_span_transcript()))
    assert sum("MODEL (BRANCH)" in t for t in event_texts) == 0
    assert "grader assessment" not in "\n".join(event_texts)
    assert sum(t.startswith("SCORE (match)") for t in event_texts) == 1


@pytest.mark.anyio
async def test_llm_scanner_events_only_scan_shows_thread_and_scores() -> None:
    # The transcript-tab shape: content events="all", no messages loaded.
    # The judge must see the ModelEvent-derived conversation AND the score.
    out = ModelOutput.from_content(model="mockllm", content="4")
    transcript = Transcript(
        transcript_id="t",
        messages=[],
        events=[
            _model_event("2+2?", out),
            ScoreEvent(score=Score(value="C"), target="C", scorer="match"),
        ],
    )
    captured: list[str] = []
    scan = llm_scanner(
        question="Right?",
        answer="boolean",
        model=_mock_model(captured),
        events=["score"],
    )
    await scan(transcript)
    assert re.search(r"\[M1\].*2\+2\?.*\[M2\].*\[E1\] SCORE", captured[0], re.DOTALL)


def _spanless_two_agent_flat_events() -> list[Event]:
    """Events-only, multi-agent flat event list with NO span structure at all.

    Four interleaved ``ModelEvent``s (A1, B1, A2, B2, chronological) for two
    agents with no ``SpanBeginEvent``/``SpanEndEvent`` markers -- the
    "fork-heavy eval" repro shape: ``timeline_build`` wraps this into a
    single synthetic "main" span, and ``span_messages`` (with no
    ``CompactionEvent`` to bound regions) keeps only the region-last
    ``ModelEvent`` (B2) to derive the thread. B2's input carries B1's
    output (so agent B's exchange is on-thread), but neither of agent A's
    turns ever appear in B2's input -- both are off-thread.
    """
    out_a1 = ModelOutput.from_content(model="mockllm", content="agent-a-answer-1")
    out_b1 = ModelOutput.from_content(model="mockllm", content="agent-b-answer-1")
    a1 = out_a1.choices[0].message
    b1 = out_b1.choices[0].message
    out_a2 = ModelOutput.from_content(model="mockllm", content="agent-a-answer-2")
    out_b2 = ModelOutput.from_content(model="mockllm", content="agent-b-answer-2")

    model_a1 = ModelEvent.model_construct(
        event="model",
        model="mockllm",
        input=[ChatMessageUser(content="agent-a-question-1")],
        output=out_a1,
        role="assistant",
        config=GenerateConfig(),
    )
    model_b1 = ModelEvent.model_construct(
        event="model",
        model="mockllm",
        input=[ChatMessageUser(content="agent-b-question-1")],
        output=out_b1,
        role="assistant",
        config=GenerateConfig(),
    )
    model_a2 = ModelEvent.model_construct(
        event="model",
        model="mockllm",
        input=[
            ChatMessageUser(content="agent-a-question-1"),
            a1,
            ChatMessageUser(content="agent-a-question-2"),
        ],
        output=out_a2,
        role="assistant",
        config=GenerateConfig(),
    )
    model_b2 = ModelEvent.model_construct(
        event="model",
        model="mockllm",
        input=[
            ChatMessageUser(content="agent-b-question-1"),
            b1,
            ChatMessageUser(content="agent-b-question-2"),
        ],
        output=out_b2,
        role="assistant",
        config=GenerateConfig(),
    )
    return [
        model_a1,
        model_b1,
        model_a2,
        model_b2,
        ScoreEvent(scorer="match", score=Score(value="C")),
    ]


@pytest.mark.anyio
async def test_spanless_multi_agent_off_thread_agent_renders_via_branch_entries() -> (
    None
):
    # Minimal repro from the task background: a fork-heavy eval with no span
    # structure at all. Agent A's entire exchange is off-thread relative to
    # the region-last ModelEvent (agent B's second turn) that
    # `span_messages` uses to derive "the" thread. Agent A's content must
    # surface via `[E#] MODEL (BRANCH):` entries rather than being silently
    # dropped.
    transcript = Transcript(
        transcript_id="t", messages=[], events=_spanless_two_agent_flat_events()
    )

    captured: list[str] = []
    scan = llm_scanner(
        question="Right?",
        answer="boolean",
        model=_mock_model(captured),
        events=["score"],
    )
    await scan(transcript)

    combined = "\n".join(captured)
    # Agent B's exchange is on-thread as ordinary turns.
    assert "agent-b-question-1" in combined
    assert "agent-b-answer-1" in combined
    assert "agent-b-question-2" in combined
    # Agent A's off-thread outputs surface via branch entries.
    assert "MODEL (BRANCH):" in combined
    assert "agent-a-answer-1" in combined
    assert "agent-a-answer-2" in combined
    assert "SCORE" in combined


def test_interleave_filters_to_selected_event_types() -> None:
    out = ModelOutput.from_content(model="mockllm", content="ans")
    transcript = Transcript(
        transcript_id="t",
        messages=[ChatMessageUser(content="q"), out.choices[0].message],
        events=[
            _model_event("q", out),
            ScoreEvent(score=Score(value="C"), scorer="match"),
            ErrorEvent(
                error=EvalError(message="boom", traceback="", traceback_ansi="")
            ),
        ],
    )
    result = interleave_events(transcript, events=["score"])
    event_texts = [
        m.text for m in result if m.metadata and m.metadata.get(EVENT_MARKER_KEY)
    ]
    assert len(event_texts) == 1
    assert event_texts[0].startswith("SCORE")


def _mock_model(captured: list[str]) -> Model:
    def _outputs(
        input: list[ChatMessage],
        tools: list[ToolInfo],
        tool_choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput:
        captured.append(input[0].text)
        return ModelOutput.from_content(model="mockllm", content="ok\n\nANSWER: yes")

    return get_model("mockllm/model", custom_outputs=_outputs)


@pytest.mark.anyio
async def test_llm_scanner_interleaves_score() -> None:
    out = ModelOutput.from_content(model="mockllm", content="4")
    assistant = out.choices[0].message
    user = ChatMessageUser(content="2+2?")
    transcript = Transcript(
        transcript_id="t",
        messages=[user, assistant],
        events=[
            _model_event("2+2?", out),
            ScoreEvent(score=Score(value="C"), target="C", scorer="match"),
        ],
    )
    captured: list[str] = []
    scan = llm_scanner(
        question="Right?",
        answer="boolean",
        model=_mock_model(captured),
        events=["score"],
    )
    await scan(transcript)
    # Structural check only: the event renders as [E1] after both turns.
    # Exact renderer formatting is pinned by tests/transcript/test_event_text.py.
    assert re.search(r"\[M1\].*\[M2\].*\[E1\] SCORE", captured[0], re.DOTALL)


@pytest.mark.anyio
async def test_loaded_events_without_events_param_not_interleaved() -> None:
    # Loading events via content= (e.g. for template_variables use) must not
    # change the rendered prompt; interleaving requires the events= parameter.
    out = ModelOutput.from_content(model="mockllm", content="4")
    transcript = Transcript(
        transcript_id="t",
        messages=[ChatMessageUser(content="2+2?"), out.choices[0].message],
        events=[
            _model_event("2+2?", out),
            ScoreEvent(score=Score(value="C"), target="C", scorer="match"),
        ],
    )
    captured: list[str] = []
    scan = llm_scanner(
        question="Right?",
        answer="boolean",
        model=_mock_model(captured),
        content=TranscriptContent(events=["score", "model"]),
    )
    await scan(transcript)
    assert "[E1]" not in captured[0]
    assert "SCORE" not in captured[0]


@pytest.mark.parametrize(
    ("events", "content", "expected"),
    [
        pytest.param(
            ["score"],
            None,
            {"score", *INTERLEAVE_DEPENDENCIES},
            id="selected-plus-dependencies",
        ),
        pytest.param(
            ["score"],
            TranscriptContent(events=["error"]),
            {"score", "error", *INTERLEAVE_DEPENDENCIES},
            id="merges-content-events",
        ),
        pytest.param("all", None, "all", id="all"),
    ],
)
def test_events_param_extends_loaded_events(
    events: EventsSpec,
    content: TranscriptContent | None,
    expected: set[str] | str,
) -> None:
    scan = llm_scanner(question="q", answer="boolean", events=events, content=content)
    loaded = getattr(scan, SCANNER_CONTENT_ATTR).events
    assert (loaded if loaded == "all" else set(loaded)) == expected


def test_selective_load_preserves_branch_structure() -> None:
    """A selective ``events=`` load must not flatten branch spans into the thread.

    ``timeline_build`` only forms a ``TimelineSpan.branches`` entry when it
    finds a ``BranchEvent`` among the span's children. Filter ``BranchEvent``
    out and the branch's conversation is unrolled into its parent, so the
    scanner reads the branch as the main thread and demotes the real answer
    to a ``MODEL (BRANCH)`` entry.
    """
    events: list[Event] = [
        SpanBeginEvent(
            id="main", parent_id=None, type="agent", name="main", span_id="main"
        ),
        _span_model_event("main q", "MAIN ANSWER", "main"),
        SpanBeginEvent(
            id="br", parent_id="main", type="branch", name="br", span_id="br"
        ),
        BranchEvent(span_id="br"),
        _span_model_event("branch q", "BRANCH ONLY", "br"),
        SpanEndEvent(id="br", span_id="br"),
        SpanEndEvent(id="main", span_id="main"),
    ]

    scan = llm_scanner(question="q", answer="boolean", events=["score"])
    loaded = getattr(scan, SCANNER_CONTENT_ATTR).events
    survived = [e for e in events if e.event in loaded]

    owned = next(walk_owned_spans(timeline_build(survived).root))
    thread = span_owned_messages(owned, events=[], compaction="all")
    # Asserted through the real filter rather than against
    # INTERLEAVE_DEPENDENCIES: comparing the constant to itself cannot detect
    # a type missing from that constant. With the branch correctly
    # recognized, its own turn still renders -- spliced in as its own
    # MODEL (BRANCH) block -- but main's own turn stays intact and undemoted.
    assert [m.text for m in thread] == [
        "main q",
        "MAIN ANSWER",
        "MODEL (BRANCH):\nBRANCH ONLY\n",
    ]
    assert len(owned.branches) == 1


@pytest.mark.anyio
async def test_interleave_with_timeline_renders_per_span() -> None:
    # Timeline-shaped transcript + events= must not raise: each span's
    # own events render in that span's own thread, and the resultset shape
    # matches an events=None run over the same transcript.
    out_a = ModelOutput.from_content(model="mockllm", content="4")
    out_b = ModelOutput.from_content(model="mockllm", content="9")
    span_a = _span(
        "span-a",
        "agent-a",
        [
            _model_event("2+2?", out_a),
            ScoreEvent(score=Score(value="C"), scorer="match"),
        ],
    )
    span_b = _span("span-b", "agent-b", [_model_event("3+3?", out_b)])
    root = TimelineSpan(
        id="root", name="Transcript", span_type=None, content=[span_a, span_b]
    )
    transcript = Transcript(
        transcript_id="t",
        timelines=[Timeline(name="Default", description="", root=root)],
    )

    captured: list[str] = []
    scan = llm_scanner(
        question="q", answer="boolean", model=_mock_model(captured), events=["score"]
    )
    result = await scan(transcript)

    assert any("2+2?" in c for c in captured)
    assert any("3+3?" in c for c in captured)
    assert sum("[E1] SCORE" in c for c in captured) == 1

    captured_no_events: list[str] = []
    scan_no_events = llm_scanner(
        question="q", answer="boolean", model=_mock_model(captured_no_events)
    )
    result_no_events = await scan_no_events(transcript)

    assert isinstance(result, Result)
    assert isinstance(result_no_events, Result)
    assert result.type == result_no_events.type == "resultset"
    assert isinstance(result.value, list)
    assert isinstance(result_no_events.value, list)
    assert len(result.value) == len(result_no_events.value) == 2


@pytest.mark.anyio
async def test_interleave_with_timeline_depth_limit_attaches_to_parent() -> None:
    # A nested scannable child span beyond `depth` is not walked as its own
    # segment; its events are attributed to the last span that IS within
    # the depth limit (its parent), and render exactly once each.
    # The child's ModelEvent has no thread of its own to be "on" (the span
    # is never walked, so `span_owned_messages` never splices it) --
    # it renders as a `MODEL (BRANCH)` entry, ahead of the child's
    # ScoreEvent, matching document order.
    out_parent = ModelOutput.from_content(model="mockllm", content="parent-ans")
    out_child = ModelOutput.from_content(model="mockllm", content="child-ans")
    child = _span(
        "child",
        "child-agent",
        [
            _model_event("child-q", out_child),
            ScoreEvent(score=Score(value="C"), scorer="childscore"),
        ],
    )
    parent = _span(
        "parent", "parent-agent", [_model_event("parent-q", out_parent), child]
    )
    root = TimelineSpan(id="root", name="Transcript", span_type=None, content=[parent])
    transcript = Transcript(
        transcript_id="t",
        timelines=[Timeline(name="Default", description="", root=root)],
    )

    captured: list[str] = []
    scan = llm_scanner(
        question="q",
        answer="boolean",
        model=_mock_model(captured),
        events=["score"],
        depth=1,
    )
    await scan(transcript)

    # Only the parent is walked as its own segment -- the child (depth 2)
    # never gets its own scan.
    assert len(captured) == 1
    assert "parent-q" in captured[0]
    assert "child-q" not in captured[0]
    assert captured[0].count("[E1] MODEL (BRANCH):\nchild-ans") == 1
    assert captured[0].count("[E2] SCORE (childscore)") == 1


@pytest.mark.anyio
async def test_final_score_lands_in_last_chunk_when_split() -> None:
    long_text = "lorem ipsum dolor sit amet consectetur adipiscing elit sed do " * 5
    out1 = ModelOutput.from_content(
        model="mockllm", content=f"{long_text} first answer"
    )
    out2 = ModelOutput.from_content(
        model="mockllm", content=f"{long_text} second answer"
    )
    a1, a2 = out1.choices[0].message, out2.choices[0].message
    u1, u2 = (
        ChatMessageUser(content=f"{long_text} q1"),
        ChatMessageUser(content=f"{long_text} q2"),
    )
    transcript = Transcript(
        transcript_id="t",
        messages=[u1, a1, u2, a2],
        events=[
            _model_event(u1.text, out1),
            _model_event(u2.text, out2),
            ScoreEvent(score=Score(value="C"), target="C", scorer="match"),
        ],
    )
    captured: list[str] = []
    # Each turn is ~55 tokens (tiktoken o200k on the repeated lorem text), so
    # the four turns plus the score exceed one segment's budget at window=350
    # (~330 after the safety margin, minus ~180 template overhead) but fit in
    # two. Verified stable for windows 300-425; len(captured) >= 2 below fails
    # loudly if tokenization or template overhead ever shifts the boundary.
    scan = llm_scanner(
        question="Right?",
        answer="boolean",
        model=_mock_model(captured),
        context_window=350,
        events=["score"],
    )
    await scan(transcript)
    assert len(captured) >= 2
    assert sum("[E1] SCORE" in c for c in captured) == 1
    assert "[E1] SCORE" in captured[-1]


def _grader_events(*, parent_id: str | None) -> list[Event]:
    """Grader model call in a `scorers` span rooted at `parent_id`."""
    return [
        SpanBeginEvent(
            id="sc", parent_id=parent_id, type="scorers", name="scorers", span_id="sc"
        ),
        _span_model_event("grade", "GRADER SECRET", "sc"),
        SpanEndEvent(id="sc", span_id="sc"),
    ]


def _scorers_model_event_ids(events: list[Event]) -> frozenset[str]:
    """Ids of ModelEvents nested under any top-level ``scorers`` span.

    On the flat/events-only path a grader ``ModelEvent`` is just another
    item in the event list; without this exclusion it would render as a
    branch entry, breaking the invariant that scorer model calls never
    surface in scanned content. (Timeline paths handle this structurally.)

    Every top-level ``scorers`` span counts, matching ``scorer_span_ids``;
    taking only the first would leak later graders on re-scored and spliced
    checkpoint-restore transcripts. Empty if the list carries no span
    structure or no ``scorers`` span is found.
    """
    if not any(isinstance(e, (SpanBeginEvent, SpanEndEvent)) for e in events):
        return frozenset()
    tree = event_tree(events)
    scorers_spans = [
        item
        for item in tree
        if isinstance(item, EventTreeSpan) and item.name == "scorers"
    ]
    return frozenset(
        _event_id(e)
        for span in scorers_spans
        for e in event_sequence(span)
        if isinstance(e, ModelEvent)
    )


@pytest.mark.parametrize(
    "events",
    [
        pytest.param(_grader_events(parent_id=None), id="root-parent-none"),
        pytest.param(
            _grader_events(parent_id=""),
            id="root-parent-empty-string-weave-langsmith-logfire",
        ),
        pytest.param(_grader_events(parent_id="sliced-away"), id="parent-not-present"),
        pytest.param(
            [
                SpanBeginEvent(
                    id="x", parent_id=None, type="agent", name="x", span_id="x"
                ),
                *_grader_events(parent_id=None),
            ],
            id="preceding-span-unclosed",
        ),
        pytest.param(
            [
                SpanEndEvent(id="ghost", span_id="ghost"),
                *_grader_events(parent_id=None),
            ],
            id="stray-span-end-first",
        ),
        pytest.param(
            [
                _span_model_event("grade", "GRADER SECRET", "sc"),
                SpanBeginEvent(
                    id="sc",
                    parent_id=None,
                    type="scorers",
                    name="scorers",
                    span_id="sc",
                ),
                SpanEndEvent(id="sc", span_id="sc"),
            ],
            id="model-before-its-span-begin",
        ),
        pytest.param(
            [
                SpanBeginEvent(
                    id="", parent_id=None, type="scorers", name="scorers", span_id=""
                ),
                _span_model_event("q", "answer", ""),
                SpanEndEvent(id="", span_id=""),
                *_grader_events(parent_id=None),
            ],
            id="falsy-span-id-is-a-root-not-a-member",
        ),
        pytest.param(
            [
                SpanBeginEvent(
                    id="g", parent_id=None, type="scorers", name="scorers", span_id="g"
                ),
                _span_model_event("grade", "GRADER SECRET", "g"),
                SpanBeginEvent(
                    id="a", parent_id=None, type="agent", name="agent", span_id="a"
                ),
                SpanBeginEvent(
                    id="g", parent_id="a", type="agent", name="inner", span_id="g"
                ),
                SpanEndEvent(id="g", span_id="g"),
            ],
            id="reused-span-id-reachable-from-two-parents",
        ),
        pytest.param(
            [
                SpanBeginEvent(
                    id="sc",
                    parent_id=None,
                    type="scorers",
                    name="scorers",
                    span_id="sc",
                ),
                SpanBeginEvent(
                    id="in", parent_id="sc", type="agent", name="inner", span_id="in"
                ),
                _span_model_event("grade", "GRADER SECRET", "in"),
                SpanEndEvent(id="in", span_id="in"),
                SpanEndEvent(id="sc", span_id="sc"),
            ],
            id="grader-nested-one-level-deeper",
        ),
    ],
)
def test_scorer_span_ids_matches_event_tree(events: list[Event]) -> None:
    """The streaming resolver must agree with `event_tree` on every shape.

    Comparing against `_scorers_model_event_ids` -- which *is* the tree -- is
    the point. Two earlier formulations passed hand-written assertions while
    diverging from the tree on sliced transcripts, out-of-order events and the
    `parent_id=""` roots this repo's own source converters emit.
    """
    from_tree = _scorers_model_event_ids(events)
    begins = [e for e in events if isinstance(e, SpanBeginEvent)]
    grader_spans = scorer_span_ids(begins)
    from_stream = {
        _event_id(e)
        for e in events
        if isinstance(e, ModelEvent) and e.span_id in grader_spans
    }
    assert from_stream == set(from_tree)


def test_scorer_span_ids_leaves_unrelated_top_level_spans_alone() -> None:
    """A concurrently-open unrelated top-level span must not be excluded."""
    events: list[Event] = [
        SpanBeginEvent(
            id="sc", parent_id=None, type="scorers", name="scorers", span_id="sc"
        ),
        SpanBeginEvent(
            id="other", parent_id=None, type="agent", name="other", span_id="other"
        ),
        _span_model_event("main q", "MAIN ANSWER", "other"),
        SpanEndEvent(id="other", span_id="other"),
        SpanEndEvent(id="sc", span_id="sc"),
    ]
    assert "other" not in scorer_span_ids(
        [e for e in events if isinstance(e, SpanBeginEvent)]
    )


def test_scorer_span_ids_terminates_on_cyclic_parents() -> None:
    """Reused span ids can form a parent cycle; resolution must not recurse."""
    begins = [
        SpanBeginEvent(id="a", parent_id="b", type="agent", name="a", span_id="a"),
        SpanBeginEvent(id="b", parent_id="a", type="agent", name="b", span_id="b"),
    ]
    assert scorer_span_ids(begins) == frozenset()


def test_all_top_level_scorers_spans_excluded_materialized() -> None:
    """Every top-level `scorers` span is excluded, not just the first.

    Re-scoring and spliced checkpoint-restore transcripts can carry more than
    one. Taking only the first left the second grader's output rendering as a
    branch entry -- the materialized driver leaking where streaming did not.
    """

    def scorers_span(suffix: str, output: str) -> list[Event]:
        span_id = f"span-scorers-{suffix}"
        return [
            SpanBeginEvent(
                id=span_id,
                parent_id=None,
                type="scorers",
                name="scorers",
                span_id=span_id,
            ),
            _span_model_event("grade", output, span_id),
            ScoreEvent(span_id=span_id, scorer=suffix, score=Score(value="C")),
            SpanEndEvent(id=span_id, span_id=span_id),
        ]

    out = ModelOutput.from_content(model="mockllm", content="4")
    user = ChatMessageUser(content="2+2?")
    transcript = Transcript(
        transcript_id="t",
        messages=[user, out.choices[0].message],
        events=[
            SpanBeginEvent(
                id="span-main",
                parent_id=None,
                type="agent",
                name="main",
                span_id="span-main",
            ),
            _span_model_event("2+2?", "4", "span-main"),
            SpanEndEvent(id="span-main", span_id="span-main"),
            *scorers_span("one", "GRADER SECRET 1"),
            *scorers_span("two", "GRADER SECRET 2"),
        ],
    )
    entries = _event_texts(interleave_events(transcript))
    texts = "\n".join(entries)
    assert "GRADER SECRET 1" not in texts
    assert "GRADER SECRET 2" not in texts
    # Positive: both scores still render, so the assertions above cannot pass
    # merely because nothing rendered at all.
    assert sum(t.startswith("SCORE (one)") for t in entries) == 1
    assert sum(t.startswith("SCORE (two)") for t in entries) == 1


def test_selective_load_preserves_nested_tool_agent_models() -> None:
    """A sub-agent ModelEvent nested in a ToolEvent must survive the load filter.

    Drop `tool` from the loaded set and the enclosing event is gone, taking the
    nested sub-agent model with it -- the reason `tool` is a load dependency
    despite never rendering itself.
    """
    nested = _span_model_event("sub q", "SUB ANSWER", "span-main")
    tool_event = ToolEvent(
        span_id="span-main",
        id="call-1",
        function="delegate",
        arguments={},
        result="done",
        events=[nested],
    )
    scan = llm_scanner(question="q", answer="boolean", events=["score"])
    loaded = getattr(scan, SCANNER_CONTENT_ATTR).events

    survived = [e for e in [tool_event] if e.event in loaded]
    assert survived, "tool events must survive so nested sub-agent models remain"
    assert nested.uuid is not None
    assert [
        m.output.completion
        for e in survived
        for m in e.events
        if isinstance(m, ModelEvent)
    ] == ["SUB ANSWER"]


def test_branch_events_render_despite_being_a_load_dependency() -> None:
    """`branch` is in INTERLEAVE_DEPENDENCIES yet must still render.

    This is the half of the dependency/non-rendered decoupling that the
    structural-marker tests do not cover: re-deriving `_NON_INTERLEAVED` from
    `INTERLEAVE_DEPENDENCIES` would silently suppress BRANCH entries, and
    nothing else notices.
    """
    out = ModelOutput.from_content(model="mockllm", content="a1")
    transcript = Transcript(
        transcript_id="t",
        messages=[ChatMessageUser(content="q1"), out.choices[0].message],
        events=[_model_event("q1", out), BranchEvent()],
    )
    assert any(
        t.startswith("BRANCH") for t in _event_texts(interleave_events(transcript))
    )


@pytest.mark.parametrize("event_type", ["anchor", "checkpoint"])
def test_structural_markers_gated_independently_of_renderer(
    event_type: EventType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`anchor`/`checkpoint` are filter-selectable but must never render.

    `EventType` admits them, so `llm_scanner(events=["anchor"])` is spellable.
    Asserting `_interleavable_text(...) is None` alone would prove nothing --
    it is None anyway while no renderer exists. Stubbing `event_as_str` to
    return text isolates the `_NON_INTERLEAVED` gate as the thing holding
    them back, so adding a renderer later cannot silently leak them.
    """
    event = (
        AnchorEvent(anchor_id="a1")
        if event_type == "anchor"
        else CheckpointEvent.model_construct(checkpoint_id="c1")
    )
    monkeypatch.setattr(
        "inspect_scout._transcript.interleave.event_as_str",
        lambda _event: "RENDERED\n",
    )
    # Positive control: if the patch ever stops taking effect (e.g. the lookup
    # moves off interleave's module globals) this fails, instead of the
    # assertions below passing for the wrong reason.
    assert (
        _interleavable_text(ScoreEvent(score=Score(value="C")), "all") == "RENDERED\n"
    )
    assert _interleavable_text(event, "all") is None
    assert _interleavable_text(event, [event_type]) is None


def test_branch_span_events_now_render_via_ownership() -> None:
    """Inverts the retired known-gap pin: branch subtree content renders.

    The fixture's branch content is [BranchEvent, ModelEvent, ScoreEvent]:
    the BranchEvent leads, so the replay cut keeps everything, and its
    branched_from defaults to "" -> the block appends at the segment end
    (decision 5).
    """
    events: list[Event] = [
        SpanBeginEvent(
            id="main", parent_id=None, type="agent", name="main", span_id="main"
        ),
        _span_model_event("main-q", "main-answer", "main"),
        SpanBeginEvent(
            id="b1", parent_id="main", type="branch", name="alt", span_id="b1"
        ),
        BranchEvent(span_id="b1"),
        _span_model_event("alt-q", "ALT ANSWER", "b1"),
        ScoreEvent(span_id="b1", scorer="s", score=Score(value="C")),
        SpanEndEvent(id="b1", span_id="b1"),
        SpanEndEvent(id="main", span_id="main"),
    ]
    tree = timeline_build(events)

    [owned] = list(walk_owned_spans(tree.root))
    assert len(owned.branches) == 1
    assert owned.branches[0].branched_from == ""
    assert len(owned.branches[0].items) == 3


def test_scorer_span_ids_matches_event_tree_under_fuzz() -> None:
    """Differential property check over randomized span shapes.

    Hand-picked cases have now missed a divergence four separate times -- each
    formulation looked right and passed its own examples. Only comparing
    against `_scorers_model_event_ids` (which is `event_tree`) over shapes
    nobody chose has caught them. Fixed seed so failures are reproducible.
    """
    import logging
    import random

    ids = ["", "a", "b", "g"]
    names = ["scorers", "agent", "solvers"]
    parents = [None, "", "a", "b", "g", "absent"]
    rng = random.Random(20260810)

    logging.disable(logging.WARNING)  # orphan span ends warn by design
    try:
        for _ in range(2000):
            events: list[Event] = []
            for _ in range(rng.randint(1, 8)):
                roll = rng.random()
                if roll < 0.45:
                    span = rng.choice(ids)
                    events.append(
                        SpanBeginEvent(
                            id=span,
                            parent_id=rng.choice(parents),
                            type="span",
                            name=rng.choice(names),
                            span_id=span,
                        )
                    )
                elif roll < 0.65:
                    events.append(
                        SpanEndEvent(id=rng.choice(ids), span_id=rng.choice(ids))
                    )
                else:
                    events.append(_span_model_event("q", "a", rng.choice(ids)))
            try:
                from_tree = set(_scorers_model_event_ids(events))
            except RecursionError:
                continue  # upstream event_tree cycles on some reused-id shapes
            grader_spans = scorer_span_ids(
                [e for e in events if isinstance(e, SpanBeginEvent)]
            )
            from_stream = {
                _event_id(e)
                for e in events
                if isinstance(e, ModelEvent) and e.span_id in grader_spans
            }
            assert from_stream == from_tree, [
                (e.event, getattr(e, "id", None), getattr(e, "parent_id", None))
                for e in events
            ]
    finally:
        logging.disable(logging.NOTSET)


def test_selective_load_preserves_compaction_pruning() -> None:
    """A selective `events=` load must keep compaction events.

    Without them `_compaction_excluded_ids` sees no CompactionEvent, so a turn
    the run deliberately pruned resurfaces as a spurious `MODEL (BRANCH)`
    entry. The existing compaction tests feed a handle every event directly,
    so the load filter never runs and cannot catch this; asserting
    `INTERLEAVE_DEPENDENCIES <= set(loaded)` cannot either, being the constant
    compared with itself.
    """
    transcript = _compaction_pruned_and_fork_transcript()
    scan = llm_scanner(question="q", answer="boolean", events=["score"])
    loaded = getattr(scan, SCANNER_CONTENT_ATTR).events
    filtered = Transcript(
        transcript_id="t",
        messages=transcript.messages,
        events=[e for e in transcript.events if e.event in loaded],
    )
    entries = _event_texts(interleave_events(filtered, events=["score"]))
    assert not any("first" in t for t in entries), (
        "compaction-pruned turn must stay hidden"
    )


def test_events_only_transcripts_are_rejected_by_the_flat_driver() -> None:
    """Events-only reconstruction was removed, not fixed -- it must fail loudly.

    Reconstructing a message thread from events alone was dropped rather than
    repaired, so the flat driver raises instead of silently producing a
    different thread. Callers wanting events-only transcripts should go
    through the per-span timeline machinery.
    """
    out = ModelOutput.from_content(model="mockllm", content="a1")
    events_only = Transcript(
        transcript_id="t", messages=[], events=[_model_event("q1", out)]
    )

    with pytest.raises(EventsOnlyInterleaveUnsupported):
        interleave_events(events_only, "all")


def test_legacy_raw_dict_subevents_are_skipped_not_crashed() -> None:
    """A ToolEvent carrying pre-deprecation sub-events must not crash the walk.

    `ToolEvent.events` is `list[Any]` upstream and unvalidated, so logs written
    before the field was deprecated deserialize their sub-events as plain
    dicts. Both interleave recursion sites hand those straight to code typed
    `Event`; before the guard this raised
    `AttributeError: 'dict' object has no attribute 'event'`.
    """
    tool_event = ToolEvent.model_validate(
        {
            "event": "tool",
            "id": "call-1",
            "function": "f",
            "arguments": {},
            "result": "ok",
            "events": [
                {
                    "event": "info",
                    "source": None,
                    "data": "legacy",
                    "timestamp": "2024-01-01T00:00:00+00:00",
                    "working_start": 0,
                    "pending": False,
                    "metadata": None,
                    "uuid": None,
                    "span_id": None,
                }
            ],
        }
    )
    assert isinstance(tool_event.events[0], dict), "fixture must reproduce the raw dict"

    transcript = Transcript(
        transcript_id="t",
        messages=[ChatMessageUser(content="q")],
        events=[tool_event],
    )

    spliced = interleave_events(transcript, "all")

    # the legacy sub-event contributes nothing; the thread is intact
    assert [m.text for m in spliced] == ["q"]
