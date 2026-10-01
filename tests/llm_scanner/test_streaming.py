"""Tests for llm_scanner streaming: handle input, capability gating, fallback.

Bounded segment concurrency and segment-order-through-reduction are covered
in ``test_segment_concurrency.py``.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Callable, Iterator, cast

import pytest
from inspect_ai.event import (
    CompactionEvent,
    InfoEvent,
    ModelEvent,
    ScoreEvent,
    SpanBeginEvent,
    SpanEndEvent,
)
from inspect_ai.event._event import Event
from inspect_ai.model import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageUser,
    GenerateConfig,
    Model,
    ModelOutput,
    get_model,
)
from inspect_ai.scorer import Score
from inspect_ai.tool import ToolChoice, ToolInfo
from inspect_scout import llm_scanner
from inspect_scout._llm_scanner._llm_scanner import _must_materialize
from inspect_scout._scanner.result import Result
from inspect_scout._scanner.scanner import Scanner, streaming_support_of
from inspect_scout._transcript.handle import (
    MaterializedTranscriptHandle,
    SpooledTranscriptHandle,
    TranscriptHandle,
)
from inspect_scout._transcript.json.stream_parse import (
    EventProjection,
    StreamParseResult,
    replay_events,
    stream_parse_to_spool,
)
from inspect_scout._transcript.types import (
    Transcript,
    TranscriptContent,
    TranscriptInfo,
)

from tests.transcript.fixtures_agentic import agentic_transcript
from tests.transcript.stream_parity import sample_json


def _make_transcript(n_messages: int, *, words: int = 3) -> Transcript:
    # Pad each message with filler words so it consumes enough tokens to force
    # segmentation under a small context window, while keeping a unique
    # "message number {i}" marker for order/identity checks.
    msgs: list[ChatMessage] = [
        ChatMessageUser(
            content=f"message number {i} " + ("filler " * words), id=f"m{i}"
        )
        for i in range(n_messages)
    ]
    return Transcript(transcript_id="t", messages=msgs)


def _score_only_transcript() -> Transcript:
    """Messages with no ModelEvent behind them, so only the flat route shows them."""
    return Transcript(
        transcript_id="t",
        messages=[
            ChatMessageUser(content="2+2?", id="m0"),
            ModelOutput.from_content(model="mockllm", content="4").message,
        ],
        events=[ScoreEvent(score=Score(value="C"), target="C", scorer="match")],
    )


def _agentic_with_score_and_info() -> Transcript:
    """The agentic fixture plus a score and an info event in its first agent turn."""
    transcript = agentic_transcript()
    events = list(transcript.events)
    i, first = next((i, e) for i, e in enumerate(events) if isinstance(e, ModelEvent))
    extra: list[Event] = [
        InfoEvent(span_id=first.span_id, timestamp=first.timestamp, data="progress"),
        ScoreEvent(
            span_id=first.span_id,
            timestamp=first.timestamp,
            score=Score(value="C"),
            scorer="match",
            intermediate=True,
        ),
    ]
    return transcript.model_copy(
        update={"events": events[: i + 1] + extra + events[i + 1 :]}
    )


def _uuidless(events: list[Event]) -> list[Event]:
    """`events` as stored by a log writer that records no uuids."""
    return [e.model_copy(update={"uuid": None}) for e in events]


def _uuidless_side_call_transcript() -> Transcript:
    """A span whose off-thread side call, rendered as a branch, has no uuid."""

    def model_event(question: str, answer: str) -> ModelEvent:
        return ModelEvent(
            span_id="main",
            model="mockllm",
            input=[ChatMessageUser(content=question)],
            tools=[],
            tool_choice="none",
            config=GenerateConfig(),
            output=ModelOutput.from_content(model="mockllm", content=answer),
        )

    return Transcript(
        transcript_id="t",
        events=[
            SpanBeginEvent(
                id="main", parent_id=None, type="agent", name="main", span_id="main"
            ),
            *_uuidless([model_event("aside?", "aside")]),
            model_event("2+2?", "4"),
            SpanEndEvent(id="main", span_id="main"),
        ],
    )


def _flat_trim_transcript() -> Transcript:
    """Messages, no spans, and a trim whose region a side call ends.

    Hiding the trim's pruned turn reads the region's first ModelEvent after
    the trim and the last one before it, not the side call.
    """

    def model_event(input: list[ChatMessage], text: str, id: str) -> ModelEvent:
        output = ModelOutput.from_content(model="mockllm", content=text)
        output.choices[0].message.id = id
        return ModelEvent(
            model="mockllm",
            input=input,
            tools=[],
            tool_choice="none",
            config=GenerateConfig(),
            output=output,
        )

    u1 = ChatMessageUser(content="task", id="u1")
    a1 = ChatMessageAssistant(content="pruned turn", id="a1")
    u2 = ChatMessageUser(content="continue", id="u2")
    a2 = ChatMessageAssistant(content="second", id="a2")
    u3 = ChatMessageUser(content="more", id="u3")
    a3 = ChatMessageAssistant(content="third", id="a3")
    return Transcript(
        transcript_id="t",
        messages=[u2, a2, u3, a3],
        events=[
            model_event([u1], "pruned turn", "a1"),
            model_event([u1, a1, u2], "second", "a2"),
            CompactionEvent(type="trim"),
            model_event([u2, a2, u3], "third", "a3"),
            model_event([ChatMessageUser(content="side")], "side answer", "s1"),
            ScoreEvent(score=Score(value="C"), target="C", scorer="match"),
        ],
    )


def _spooled_handle_for(
    transcript: Transcript, spool_dir: Path, *, pooled: bool = False
) -> SpooledTranscriptHandle:
    """A SpooledTranscriptHandle over `transcript`, so the streaming path is exercised.

    ``pooled`` stores ModelEvent inputs in a pool, as inspect_ai's log writer
    does.
    """
    data = sample_json(transcript.events, messages=transcript.messages, pooled=pooled)
    info = TranscriptInfo(
        **transcript.model_dump(exclude={"messages", "events", "timelines"})
    )

    async def parse() -> StreamParseResult:
        return await stream_parse_to_spool(io.BytesIO(data), "all", "all", spool_dir)

    async def fallback() -> Transcript:
        return transcript

    return SpooledTranscriptHandle(info, parse, fallback)


async def _scan(
    scan_fn: Scanner[Transcript], input: Transcript | TranscriptHandle
) -> Result:
    # The public scanner type is Scanner[Transcript]; llm_scanner's scan also
    # accepts a TranscriptHandle at runtime (streaming path). The scan returns
    # a single Result for these single-/multi-segment reduced scans.
    out = await scan_fn(cast(Transcript, input))
    assert isinstance(out, Result)
    return out


def _spy_on_load(
    monkeypatch: pytest.MonkeyPatch, cls: type[SpooledTranscriptHandle]
) -> list[SpooledTranscriptHandle]:
    """Patch `cls.load` to record each call while still delegating to it.

    Lets a test assert whether a scan materialized a handle instead of
    streaming it (`assert not calls`) or relied on materialization
    (`assert calls`).
    """
    calls: list[SpooledTranscriptHandle] = []
    original = cls.load

    async def spy(self: SpooledTranscriptHandle) -> Transcript:
        calls.append(self)
        return await original(self)

    monkeypatch.setattr(cls, "load", spy)
    return calls


def _recording_model(recorded: list[str]) -> Model:
    """A mock model that records the full rendered prompt of each call."""

    def capture(
        input_msgs: list[ChatMessage],
        tools: list[ToolInfo],
        tool_choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput:
        recorded.append("\n".join(m.text for m in input_msgs))
        return ModelOutput.from_content(
            model="mockllm",
            content="Reasoning.\n\nANSWER: yes",
            stop_reason="stop",
        )

    return get_model("mockllm/model", custom_outputs=capture, memoize=False)


def _yes_model() -> Model:
    return _recording_model([])


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("make_transcript", "scanner_kwargs", "min_prompts", "expect_load"),
    [
        # Multiple segments: 12 padded messages under a small context window.
        pytest.param(
            lambda: _make_transcript(12, words=80),
            {"context_window": 400},
            2,
            False,
            id="messages-multi-segment",
        ),
        # Events content: the handle path routes to stream_timeline_messages
        # (two-pass event streaming); the Transcript path routes to the
        # materialized transcript_messages path. Prompts must still match.
        pytest.param(
            agentic_transcript,
            {"content": TranscriptContent(events="all")},
            2,
            False,
            id="events",
        ),
        # A template reading TranscriptInfo fields: the streaming path renders
        # against an info-only Transcript built from handle.info, which must
        # carry the same values as the materialized transcript.
        pytest.param(
            lambda: _make_transcript(3).model_copy(
                update={"model": "acme/probe", "task_id": "task-7", "agent": "react"}
            ),
            {
                "template": (
                    "Scanning {{ model }} / {{ task_id }} / {{ agent }}.\n",
                    "{{ messages }}\n{{ question }}\n{{ answer_prompt }}",
                )
            },
            1,
            False,
            id="template-reads-transcript-info",
        ),
        # events="all" over a transcript that has no events: streaming yields
        # zero segments, so scan() falls back to handle.load() rather than
        # reducing over nothing -- a deliberate, pre-existing fallback
        # distinct from the _must_materialize upfront decision this file
        # otherwise guards.
        pytest.param(
            lambda: _make_transcript(3),
            {"content": TranscriptContent(events="all")},
            1,
            True,
            id="events-requested-but-absent",
        ),
        # events= on a spanless transcript with messages: the flat
        # stream_interleave_events route, mirroring interleave_events.
        pytest.param(
            _score_only_transcript,
            {"events": ["score"]},
            1,
            False,
            id="events-param",
        ),
        # events= on a span-structured transcript: per-span interleaving via
        # stream_timeline_messages(events=...).
        pytest.param(
            agentic_transcript,
            {"events": "all"},
            2,
            False,
            id="events-param-spans",
        ),
        # The span route renders only the requested event types.
        pytest.param(
            _agentic_with_score_and_info,
            {"events": ["score"]},
            2,
            False,
            id="events-param-spans-filtered",
        ),
        # The routes below render differently, so these pin the streaming
        # router to transcript_messages' flat gate (messages, no spans).
        pytest.param(
            _score_only_transcript,
            {"events": ["score"], "content": TranscriptContent(events="all")},
            1,
            False,
            id="events-param-flat-with-content-events",
        ),
        pytest.param(
            lambda: agentic_transcript().model_copy(
                update={"messages": [ChatMessageUser(content="top level", id="t0")]}
            ),
            {"events": "all"},
            2,
            False,
            id="events-param-messages-and-spans",
        ),
        # Events stored without a uuid replay without one, as inspect_ai reads
        # them, so both stream passes see the same events. A uuid-less event
        # the prompt needs makes the scan load the transcript instead.
        pytest.param(
            _uuidless_side_call_transcript,
            {"events": "all"},
            1,
            True,
            id="events-param-uuidless-side-call",
        ),
        # A compaction makes the flat route re-read the ModelEvents its
        # exclusions come from, by stream position, uuid or not.
        pytest.param(
            _flat_trim_transcript,
            {"events": ["score"]},
            1,
            False,
            id="events-param-flat-trim",
        ),
        pytest.param(
            lambda: _flat_trim_transcript().model_copy(
                update={"events": _uuidless(_flat_trim_transcript().events)}
            ),
            {"events": ["score"]},
            1,
            False,
            id="events-param-flat-trim-uuidless",
        ),
    ],
)
async def test_handle_scan_equivalent_to_transcript_scan(
    make_transcript: Callable[[], Transcript],
    scanner_kwargs: dict[str, Any],
    min_prompts: int,
    expect_load: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Handle and Transcript inputs produce identical prompt streams + Result.

    The mock model records the full rendered prompt of every generate call,
    so any divergence between the streaming and materialized paths (e.g. a
    truncated segment) fails the prompt-sequence equality below.
    """
    transcript = make_transcript()

    recorded: list[str] = []
    scan_fn = llm_scanner(
        question="Is this helpful?",
        answer="boolean",
        model=_recording_model(recorded),
        **scanner_kwargs,
    )

    result_transcript = await _scan(scan_fn, transcript)
    prompts_transcript = list(recorded)
    recorded.clear()

    load_calls = _spy_on_load(monkeypatch, SpooledTranscriptHandle)
    result_handle = await _scan(scan_fn, _spooled_handle_for(transcript, tmp_path))
    prompts_handle = list(recorded)

    if expect_load:
        assert load_calls, "expected the scan to load the handle"
    else:
        assert not load_calls, "streamed scan materialized the handle"
    assert len(prompts_transcript) >= min_prompts
    if scanner_kwargs.get("events") == ["score"]:
        assert any("SCORE (match)" in p for p in prompts_transcript)  # non-vacuous
    assert prompts_handle == prompts_transcript
    assert result_handle.value == result_transcript.value
    assert result_handle.answer == result_transcript.answer
    assert result_handle.explanation == result_transcript.explanation


def _dynamic_template_variables(_t: Transcript) -> dict[str, Any]:
    return {"extra": 1}


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        pytest.param({}, True, id="static"),
        pytest.param(
            {"template_variables": _dynamic_template_variables},
            False,
            id="callable-template-variables",
        ),
        pytest.param({"timeline": "agent"}, False, id="timeline"),
        # Events content is streaming-eligible (consumed via
        # stream_timeline_messages on the handle path).
        pytest.param(
            {"content": TranscriptContent(events="all")}, True, id="content-events"
        ),
        # A timeline content filter still forces materialization
        # (named-timeline selection and extraction need the full transcript).
        pytest.param(
            {"content": TranscriptContent(timeline="all")}, False, id="content-timeline"
        ),
    ],
)
def test_streaming_attr_gating(kwargs: dict[str, Any], expected: bool) -> None:
    """The streaming vouch matches whether the config is streaming-safe."""
    call_kwargs: dict[str, Any] = {"question": "static?", "answer": "boolean"} | kwargs
    scan_fn = llm_scanner(**call_kwargs)
    assert streaming_support_of(scan_fn) is expected


@pytest.mark.anyio
async def test_callable_question_with_handle_materializes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A callable question given a handle receives a materialized Transcript.

    Mirrors the factory-time opt-in gating at runtime: scan() must call
    handle.load() when the question callable needs the full transcript, so
    the callable sees real messages rather than an empty info shell.
    """
    transcript = _make_transcript(3)

    seen: list[Transcript] = []

    async def question(t: Transcript) -> str:
        seen.append(t)
        return "dynamic?"

    scan_fn = llm_scanner(
        question=question,
        answer="boolean",
        model=_yes_model(),
    )

    load_calls = _spy_on_load(monkeypatch, SpooledTranscriptHandle)
    result = await _scan(scan_fn, _spooled_handle_for(transcript, tmp_path))
    assert result.answer is not None
    assert load_calls, "callable question should have materialized the handle"

    assert seen, "question callable should have been invoked"
    for t in seen:
        assert [m.id for m in t.messages] == [m.id for m in transcript.messages], (
            "question callable should receive the materialized transcript content"
        )


@pytest.mark.anyio
async def test_handle_info_may_be_a_transcript() -> None:
    """`Transcript` subclasses `TranscriptInfo`, so a handle may expose one as `info`.

    The info-only shell built for template rendering must exclude the content
    fields, or they collide with the empties it substitutes.
    """
    transcript = _make_transcript(3)

    async def load_fn() -> Transcript:
        return transcript

    scan_fn = llm_scanner(
        question="Is this helpful?", answer="boolean", model=_yes_model()
    )
    result = await _scan(scan_fn, MaterializedTranscriptHandle(load_fn, transcript))
    assert result.answer is not None


def test_materialized_handle_takes_the_batch_path() -> None:
    """A MaterializedTranscriptHandle must be load()ed rather than streamed.

    It loads everything on first use, so streaming it saves no memory and
    only serialises token counting.
    """
    info = TranscriptInfo(transcript_id="t")

    async def load_fn() -> Transcript:
        return Transcript(transcript_id="t", messages=[])

    materialized = MaterializedTranscriptHandle(load_fn, info)
    assert _must_materialize(materialized, full_transcript_needed=False) is True
    assert _must_materialize(materialized, full_transcript_needed=True) is True

    async def parse() -> StreamParseResult:
        raise AssertionError("not called")

    spooled = SpooledTranscriptHandle(info, parse, load_fn)
    assert _must_materialize(spooled, full_transcript_needed=False) is False
    assert _must_materialize(spooled, full_transcript_needed=True) is True


@pytest.mark.anyio
@pytest.mark.parametrize(
    "make_transcript",
    [
        pytest.param(agentic_transcript, id="timeline"),
        pytest.param(_score_only_transcript, id="flat"),
    ],
)
async def test_streamed_events_scan_projects_every_event_pass(
    make_transcript: Callable[[], Transcript],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every event pass of a streamed events= scan replays the spool projected.

    An unprojected pass decodes every ModelEvent's pooled input in full, so
    the scan would still render the same prompts, only slower.
    """
    projections: list[EventProjection | None] = []

    def spy(
        result: StreamParseResult, project: EventProjection | None = None
    ) -> Iterator[Event]:
        projections.append(project)
        return replay_events(result, project)

    monkeypatch.setattr("inspect_scout._transcript.handle.replay_events", spy)
    scan_fn = llm_scanner(
        question="Is this helpful?",
        answer="boolean",
        model=_yes_model(),
        events=["score"],
    )
    await _scan(scan_fn, _spooled_handle_for(make_transcript(), tmp_path, pooled=True))
    assert len(projections) >= 2
    assert None not in projections
