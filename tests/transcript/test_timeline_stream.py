"""Tests for the streaming events skeleton (timeline_stream)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import pytest
from inspect_ai.event import (
    AnchorEvent,
    BranchEvent,
    Event,
    ModelEvent,
    ScoreEvent,
    SpanBeginEvent,
    SpanEndEvent,
    TimelineEvent,
    ToolEvent,
    timeline_build,
)
from inspect_ai.event._timeline import (
    _get_system_prompt_for_event,
    _has_tool_calls,
)
from inspect_ai.model import (
    ChatMessageSystem,
    ChatMessageUser,
    GenerateConfig,
    ModelOutput,
)
from inspect_ai.scorer import Score
from inspect_scout._scanner.extract import message_numbering
from inspect_scout._transcript.handle import MaterializedTranscriptHandle
from inspect_scout._transcript.interleave import EventsSpec
from inspect_scout._transcript.messages import transcript_messages
from inspect_scout._transcript.timeline import (
    _ORPHAN_SPAN_ID,
    TimelineMessages,
    TimelineSpan,
    walk_owned_spans,
)
from inspect_scout._transcript.timeline_stream import stream_timeline_messages
from inspect_scout._transcript.types import Transcript, TranscriptInfo

from tests.transcript.fixtures_agentic import (
    _model_event,
    agentic_events,
    agentic_transcript,
)


def _collect_utility(span: TimelineSpan) -> list[TimelineSpan]:
    """Recursively collect every utility-classified span in the tree."""
    utility: list[TimelineSpan] = []
    if span.utility:
        utility.append(span)
    for item in span.content:
        if isinstance(item, TimelineSpan):
            utility.extend(_collect_utility(item))
    return utility


def _span_model_event_uuids(span: TimelineSpan) -> list[str | None]:
    """Return the uuids of ModelEvents directly in `span.content` (not nested)."""
    uuids: list[str | None] = []
    for item in span.content:
        if isinstance(item, TimelineEvent) and isinstance(item.event, ModelEvent):
            uuids.append(item.event.uuid)
    return uuids


def _last_model_event(events: list[Event]) -> ModelEvent:
    for event in reversed(events):
        if isinstance(event, ModelEvent):
            return event
    raise AssertionError("fixture contains no ModelEvent")


def test_stub_tree_matches_full_tree_structure() -> None:
    """Stubbing must strip bulk content without changing span shape.

    Building the timeline from stubbed events yields the same scannable span
    names, utility classification, and per-span direct-ModelEvent uuid
    sequence as building it from the full events -- including
    "handoff_agent", the ToolEvent-with-nested-`.events` tool-spawned agent,
    whose nested ModelEvents would vanish if `_stub_tool_event` emptied
    `.events` instead of recursively stubbing it.
    """
    from inspect_scout._transcript.timeline_stream import _PromptInterner, stub_event

    events = agentic_events(big_payload="z" * 100_000)
    interner = _PromptInterner()
    stubbed_events: list[Event] = [stub_event(e, interner) for e in events]

    full_tree = timeline_build(events)
    stub_tree = timeline_build(stubbed_events)

    full_spans = [o.span for o in walk_owned_spans(full_tree.root)]
    stub_spans = [o.span for o in walk_owned_spans(stub_tree.root)]

    full_names = [s.name for s in full_spans]
    stub_names = [s.name for s in stub_spans]
    assert stub_names == full_names
    assert "handoff_agent" in full_names

    full_utility = _collect_utility(full_tree.root)
    stub_utility = _collect_utility(stub_tree.root)
    assert [s.name for s in stub_utility] == [s.name for s in full_utility]

    for full_span, stub_span in zip(full_spans, stub_spans, strict=True):
        assert full_span.utility == stub_span.utility
        assert _span_model_event_uuids(stub_span) == _span_model_event_uuids(full_span)

    # The nested ModelEvents inside handoff-tool's `.events` must survive
    # stubbing with distinct uuids.
    handoff_span = next(s for s in stub_spans if s.name == "handoff_agent")
    assert _span_model_event_uuids(handoff_span) == ["evt-handoff-1", "evt-handoff-2"]

    # The point of stubbing: bulk payloads (ModelEvent outputs, ToolEvent
    # arguments/results, and both nested inside `ToolEvent.events`) are gone.
    assert not any("z" * 1000 in e.model_dump_json() for e in stubbed_events)


@pytest.mark.parametrize(
    ("trailing_user_content", "expected_warmup"),
    [
        pytest.param("warmup", True, id="warmup"),
        pytest.param("Is the answer correct? Reply yes or no.", False, id="judge"),
    ],
)
def test_stub_preserves_warmup_signal(
    trailing_user_content: str, expected_warmup: bool
) -> None:
    """Stubbing a max_tokens=1 ``ModelEvent`` must preserve its warmup verdict.

    ``_is_warmup_call``'s verdict (True for a single-word trailing user turn,
    False for a multi-word judge/classifier call) and the other per-event
    signals ``_wrap_utility_events`` reads must survive stubbing, while bulk
    user content is still stripped.

    (A full ``timeline_build`` over a warmup span is not exercised here: it
    hits an upstream ``inspect_ai`` unbounded-recursion bug identically on
    both the stub and materialized paths, so this asserts at the classifier
    boundary instead.)
    """
    from inspect_ai.event._timeline import _is_warmup_call
    from inspect_ai.model import ChatMessageUser, GenerateConfig
    from inspect_scout._transcript.timeline_stream import _PromptInterner, stub_event

    base = _last_model_event(agentic_events())
    event = base.model_copy(
        update={
            "uuid": "evt-warmup-local",
            "input": [
                ChatMessageSystem(content="MAIN"),
                ChatMessageUser(content="bulk conversation " + "w" * 100_000),
                ChatMessageUser(content=trailing_user_content),
            ],
            "config": GenerateConfig(max_tokens=1),
        }
    )
    # Sanity: the classifier's pre-stub verdict matches the expectation.
    assert _is_warmup_call(event) is expected_warmup

    stub = stub_event(event, _PromptInterner())
    assert isinstance(stub, ModelEvent)

    # The three per-event signals `_wrap_utility_events` reads are preserved.
    assert _is_warmup_call(stub) is expected_warmup
    assert _get_system_prompt_for_event(stub) == _get_system_prompt_for_event(event)
    assert _has_tool_calls(stub) == _has_tool_calls(event)
    # Bulk stripped: the 100KB user turn must not survive stubbing.
    assert "w" * 1000 not in stub.model_dump_json()


def test_selection_uuidless_raises() -> None:
    """A selected ModelEvent with no uuid must fail loudly.

    Pass 2 targets full events by uuid, so silently skipping one would leave a
    stub in the rendered output the scanner model reads.
    """
    from inspect_scout._transcript.timeline_stream import (
        _StubSkeletonUnsupported,
        needed_model_event_uuids,
    )

    events = agentic_events()
    target = _last_model_event(events)
    events = [e.model_copy(update={"uuid": None}) if e is target else e for e in events]
    tree = timeline_build(events)
    with pytest.raises(_StubSkeletonUnsupported):
        needed_model_event_uuids(
            tree.root, compaction="last", depth=None, include_scorers=False
        )


def _info(transcript: Transcript) -> TranscriptInfo:
    return TranscriptInfo(transcript_id=transcript.transcript_id)


def _scrub_agent_result(obj: Any) -> Any:
    """Recursively null out `agent_result` fields in a `model_dump()` tree.

    Isolates the one accepted fidelity loss (see `timeline_stream`'s module
    docstring) so span-tree equality checks can pin "no other divergence".
    """
    if isinstance(obj, dict):
        return {
            key: None if key == "agent_result" else _scrub_agent_result(value)
            for key, value in obj.items()
        }
    if isinstance(obj, list):
        return [_scrub_agent_result(item) for item in obj]
    return obj


@pytest.mark.asyncio
@pytest.mark.parametrize("compaction", ["all", "last", 2])
@pytest.mark.parametrize("depth", [None, 1])
async def test_stream_equals_materialized_segments(
    compaction: Literal["all", "last"] | int, depth: int | None
) -> None:
    """Streamed and materialized extraction agree on messages and span structure.

    Two assertions for two properties. The `messages_str` equality is the
    content guard: it is what fails if an unsubstituted stub ever reaches
    rendered output. The span-dump equality is the structure guard. They are
    not redundant -- dropping one pass-2 substitution fails the first and
    leaves the second green, because `TimelineEvent` serializes its event as
    a bare uuid.
    """
    from inspect_scout._scanner.extract import message_numbering
    from inspect_scout._transcript.handle import MaterializedTranscriptHandle
    from inspect_scout._transcript.messages import transcript_messages
    from inspect_scout._transcript.timeline import TimelineMessages
    from inspect_scout._transcript.timeline_stream import stream_timeline_messages

    transcript = agentic_transcript()

    async def load() -> Transcript:
        return transcript

    handle = MaterializedTranscriptHandle(load, _info(transcript))

    def numbering() -> Any:  # fresh numbering scope per path
        return message_numbering()[0]

    streamed_segments = [
        seg
        async for seg in stream_timeline_messages(
            handle,
            messages_as_str=numbering(),
            model="mockllm/model",
            compaction=compaction,
            depth=depth,
        )
    ]
    materialized_segments: list[TimelineMessages] = []
    async for seg in transcript_messages(
        transcript,
        messages_as_str=numbering(),
        model="mockllm/model",
        compaction=compaction,
        depth=depth,
    ):
        assert isinstance(seg, TimelineMessages)
        materialized_segments.append(seg)
    streamed = [(seg.span.id, seg.messages_str) for seg in streamed_segments]
    materialized = [(seg.span.id, seg.messages_str) for seg in materialized_segments]
    assert streamed == materialized

    # Span structure, not payloads: `TimelineEvent` serializes its event as a
    # bare uuid, so this pins per-span event identity and ordering. Payload
    # divergence is caught by the `messages_str` equality above. `agent_result`
    # is a span field, hence the scrub (see timeline_stream's module docstring).
    for s_seg, m_seg in zip(streamed_segments, materialized_segments, strict=True):
        assert _scrub_agent_result(s_seg.span.model_dump()) == _scrub_agent_result(
            m_seg.span.model_dump()
        )


LOGS_DIR = Path(__file__).parent.parent / "recorder" / "logs"
LOGS = sorted(LOGS_DIR.glob("*.eval"))
assert LOGS, f"no .eval fixtures found in {LOGS_DIR}"


@pytest.mark.asyncio
@pytest.mark.parametrize("events", [None, "all"])
@pytest.mark.parametrize("include_scorers", [False, True])
@pytest.mark.parametrize("log", LOGS, ids=[log.name for log in LOGS])
async def test_stream_equals_materialized_segments_eval_logs(
    log: Path,
    include_scorers: bool,
    events: EventsSpec | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fidelity over real `.eval` fixtures, forced through the spooled path.

    These fixtures carry a `scorers` span, so this is also what pins the
    streaming path to `transcript_messages`' scorer exclusion -- without it
    the grader's rubric, expert answer included, reaches the scanner model.
    """
    from inspect_scout._scanner.extract import message_numbering
    from inspect_scout._transcript.eval_log import EvalLogTranscriptsView
    from inspect_scout._transcript.handle import SpooledTranscriptHandle
    from inspect_scout._transcript.messages import transcript_messages
    from inspect_scout._transcript.timeline import TimelineMessages
    from inspect_scout._transcript.timeline_stream import stream_timeline_messages
    from inspect_scout._transcript.types import TranscriptContent
    from inspect_scout._util import constants as constants_mod

    monkeypatch.setattr(constants_mod, "SPOOL_THRESHOLD_BYTES", 0)
    content = TranscriptContent(events="all")

    view = EvalLogTranscriptsView(str(log))
    await view.connect()
    try:
        infos = [i async for i in view.select()]
        assert infos
        info = infos[0]
        materialized = await view.read(info, content)

        def numbering() -> Any:  # fresh numbering scope per path
            return message_numbering()[0]

        async with await view.open(info, content) as handle:
            assert isinstance(handle, SpooledTranscriptHandle)
            streamed_segments = [
                seg
                async for seg in stream_timeline_messages(
                    handle,
                    messages_as_str=numbering(),
                    model="mockllm/model",
                    compaction="all",
                    depth=None,
                    include_scorers=include_scorers,
                    events=events,
                )
            ]
        materialized_segments: list[TimelineMessages] = []
        async for seg in transcript_messages(
            materialized,
            messages_as_str=numbering(),
            model="mockllm/model",
            compaction="all",
            depth=None,
            include_scorers=include_scorers,
            events=events,
        ):
            assert isinstance(seg, TimelineMessages)
            materialized_segments.append(seg)
        streamed = [(seg.span.id, seg.messages_str) for seg in streamed_segments]
        materialized_tuples = [
            (seg.span.id, seg.messages_str) for seg in materialized_segments
        ]
        assert streamed  # non-vacuous: the fixture must yield >=1 segment
        assert streamed == materialized_tuples
        for s_seg, m_seg in zip(streamed_segments, materialized_segments, strict=True):
            assert _scrub_agent_result(s_seg.span.model_dump()) == _scrub_agent_result(
                m_seg.span.model_dump()
            )
    finally:
        await view.disconnect()


@pytest.mark.parametrize(
    ("events_spec", "raises"),
    [
        pytest.param("all", True, id="interleaving-on-raises"),
        pytest.param(None, False, id="interleaving-off-unaffected"),
    ],
)
def test_uuidless_offthread_model_event_falls_back(
    events_spec: str | None, raises: bool
) -> None:
    """A uuid-less off-thread ModelEvent must not silently vanish.

    Pass 2 targets events by uuid, so one without a uuid can be neither
    substituted nor rendered -- it stayed an empty stub and disappeared from
    streaming output while `interleave_events` rendered it as a branch entry.
    Raising hands the scan to the materialized fallback instead.

    With interleaving off, off-thread outputs are never rendered, so dropping
    the event is correct and must not force materialization.
    """
    from inspect_scout._transcript.timeline_stream import (
        _collect_pass2_model_events,
        _StubSkeletonUnsupported,
    )

    fork = _model_event(
        label="fork",
        system_prompt="sys",
        output_text="FORK",
        span_id=None,
    ).model_copy(update={"uuid": None})
    offthread: dict[str, ModelEvent] | None = {} if events_spec is not None else None

    if raises:
        with pytest.raises(_StubSkeletonUnsupported):
            _collect_pass2_model_events(fork, frozenset(), {}, offthread)
    else:
        _collect_pass2_model_events(fork, frozenset(), {}, offthread)


def test_uuidless_offthread_empty_output_does_not_force_fallback() -> None:
    """An unrenderable off-thread output must not trigger materialization.

    The fallback exists so branch content is not silently lost. An output that
    renders to nothing is lost either way, so falling back would materialize a
    whole sample to produce byte-identical text.
    """
    from inspect_scout._transcript.timeline_stream import _collect_pass2_model_events

    # No choices at all (e.g. a call that errored): renders to nothing, unlike
    # an empty completion, which still renders a "MODEL (BRANCH):" header.
    empty = (
        _model_event(label="empty", system_prompt="sys", output_text="x", span_id=None)
        .model_copy(update={"uuid": None})
        .model_copy(update={"output": ModelOutput(model="m", choices=[])})
    )
    offthread: dict[str, ModelEvent] = {}
    _collect_pass2_model_events(empty, frozenset(), {}, offthread)
    assert offthread == {}


async def _both_paths(
    events_list: list[Event], *, include_scorers: bool = False
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """(span.id, messages_str) segments from the streaming and materialized paths.

    Each side gets its own fresh message numbering.
    """
    from inspect_ai.model import get_model

    async def _load() -> Transcript:
        return Transcript(transcript_id="t-both", events=list(events_list))

    handle = MaterializedTranscriptHandle(_load, TranscriptInfo(transcript_id="t-both"))
    msgs_as_str, _ = message_numbering()
    streamed = [
        (seg.span.id, seg.messages_str)
        async for seg in stream_timeline_messages(
            handle,
            messages_as_str=msgs_as_str,
            model=get_model("mockllm/model"),
            context_window=100_000,
            events="all",
            include_scorers=include_scorers,
        )
    ]
    msgs_as_str2, _ = message_numbering()
    materialized: list[tuple[str, str]] = []
    async for seg in transcript_messages(
        Transcript(transcript_id="t-both-m", events=list(events_list)),
        messages_as_str=msgs_as_str2,
        model=get_model("mockllm/model"),
        context_window=100_000,
        events="all",
        include_scorers=include_scorers,
    ):
        assert isinstance(seg, TimelineMessages)
        materialized.append((seg.span.id, seg.messages_str))
    return streamed, materialized


@pytest.mark.anyio
async def test_nested_nonagent_tool_model_event_renders_same_text_both_paths() -> None:
    """Streaming requirement 3 (design §2): _substitute_full_events must recurse.

    Must recurse into ToolEvent.events, or streamed renders empty MODEL (BRANCH).
    """
    from tests.transcript.tree_gen import CORPUS_SEEDS, generate

    seed = next(
        s
        for s in CORPUS_SEEDS
        if any(isinstance(e, ToolEvent) and e.events for e in generate(s).events)
    )
    streamed, materialized = await _both_paths(generate(seed).events)
    # The nested model text must genuinely render (not equal-empty on both).
    assert any("-nested" in text for _, text in streamed)
    assert streamed == materialized


def _input_anchor_branch_events() -> list[Event]:
    """Owner thread [q(id='IN'), a1]; branch anchored to the INPUT id."""
    q = ChatMessageUser(content="task")
    q.id = "IN"
    out = ModelOutput.from_content(model="mockllm", content="a1")
    out.choices[0].message.id = "OUT"
    alt = ModelOutput.from_content(model="mockllm", content="BRANCH-ALT")
    return [
        SpanBeginEvent.model_construct(
            event="span_begin",
            uuid="u-b1",
            id="main",
            span_id=None,
            parent_id=None,
            type="agent",
            name="main",
        ),
        ModelEvent.model_construct(
            event="model",
            uuid="u-main",
            span_id="main",
            model="mockllm",
            input=[q],
            output=out,
            role="assistant",
            config=GenerateConfig(),
        ),
        SpanBeginEvent.model_construct(
            event="span_begin",
            uuid="u-b2",
            id="br",
            span_id="main",
            parent_id="main",
            type="branch",
            name="fork",
        ),
        BranchEvent.model_construct(
            event="branch",
            uuid="u-be",
            span_id="br",
            from_anchor="IN",
        ),
        ModelEvent.model_construct(
            event="model",
            uuid="u-alt",
            span_id="br",
            model="mockllm",
            input=[ChatMessageUser(content="bq")],
            output=alt,
            role="assistant",
            config=GenerateConfig(),
        ),
        SpanEndEvent.model_construct(
            event="span_end",
            uuid="u-e2",
            id="br",
            span_id="main",
        ),
        SpanEndEvent.model_construct(
            event="span_end",
            uuid="u-e1",
            id="main",
            span_id=None,
        ),
    ]


@pytest.mark.anyio
async def test_branch_resolution_never_uses_input_ids() -> None:
    """The id-tier narrowing (design §4): branched_from matching only an INPUT id.

    Resolves unmatched -> appends, identically on both paths (the stub
    strips input ids; the viewer's input tier is a path streaming cannot
    reach, so neither path may use it).
    """
    streamed, materialized = await _both_paths(_input_anchor_branch_events())
    assert streamed == materialized
    _, text = streamed[0]
    assert "BRANCH-ALT" in text
    assert text.index("BRANCH-ALT") > text.index("a1")  # appended, not spliced


@pytest.mark.anyio
async def test_orphan_sentinel_id_is_stable_across_paths() -> None:
    score_only: list[Event] = [
        ScoreEvent.model_construct(
            event="score",
            uuid="u-s1",
            span_id=None,
            score=Score(value=1.0),
            scorer="s",
        )
    ]
    streamed, materialized = await _both_paths(score_only)
    assert streamed == materialized
    assert [sid for sid, _ in streamed] == [_ORPHAN_SPAN_ID]


@pytest.mark.anyio
async def test_branch_splices_at_anchor_event_both_paths() -> None:
    """A branch keyed on an `AnchorEvent` id splices mid-thread on both paths.

    Anchors are unstubbed, so the streamed walk must resolve them exactly as
    the materialized one does rather than appending the branch.
    """
    events = _input_anchor_branch_events()
    first_turn = events[1]
    assert isinstance(first_turn, ModelEvent)
    second = ModelOutput.from_content(model="mockllm", content="a2")
    second_turn = ModelEvent.model_construct(
        event="model",
        uuid="u-main-2",
        span_id="main",
        model="mockllm",
        input=[
            *first_turn.input,
            first_turn.output.message,
            ChatMessageUser(content="q2"),
        ],
        output=second,
        role="assistant",
        config=GenerateConfig(),
    )
    branch_event = events[3]
    assert isinstance(branch_event, BranchEvent)
    anchored = [
        events[0],
        events[1],
        AnchorEvent.model_construct(
            event="anchor", uuid="u-anc", span_id="main", anchor_id="ANC"
        ),
        second_turn,
        events[2],
        branch_event.model_copy(update={"from_anchor": "ANC"}),
        *events[4:],
    ]
    streamed, materialized = await _both_paths(anchored)
    assert streamed == materialized
    _, text = streamed[0]
    assert text.index("a1") < text.index("BRANCH-ALT") < text.index("a2")


@pytest.mark.anyio
async def test_legacy_raw_dict_tool_subevents_both_paths() -> None:
    """Pre-deprecation `ToolEvent.events` dicts must not crash either path."""
    tool_event = ToolEvent.model_validate(
        {
            "event": "tool",
            "uuid": "u-tool",
            "span_id": "main",
            "id": "call-1",
            "function": "f",
            "arguments": {},
            "result": "ok",
            "events": [{"event": "info", "data": "legacy", "uuid": None}],
        }
    )
    assert isinstance(tool_event.events[0], dict)
    events = _input_anchor_branch_events()
    streamed, materialized = await _both_paths([*events[:2], tool_event, *events[2:]])
    assert streamed == materialized
