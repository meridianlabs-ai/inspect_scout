"""Tests for the streaming events skeleton (timeline_stream)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import pytest
from inspect_ai.event import Event, ModelEvent, TimelineEvent, timeline_build
from inspect_ai.event._timeline import (
    _get_system_prompt_for_event,
    _has_tool_calls,
)
from inspect_ai.model import ChatMessageSystem
from inspect_scout._transcript.timeline import TimelineSpan, _walk_spans
from inspect_scout._transcript.types import Transcript, TranscriptInfo

from tests.transcript.fixtures_agentic import agentic_events, agentic_transcript


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

    full_spans = list(_walk_spans(full_tree.root, depth=None))
    stub_spans = list(_walk_spans(stub_tree.root, depth=None))

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
        needed_model_event_uuids(tree.root, compaction="last", depth=None)


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
@pytest.mark.parametrize("log", LOGS, ids=[log.name for log in LOGS])
async def test_stream_equals_materialized_segments_eval_logs(
    log: Path, monkeypatch: pytest.MonkeyPatch
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
                )
            ]
        materialized_segments: list[TimelineMessages] = []
        async for seg in transcript_messages(
            materialized,
            messages_as_str=numbering(),
            model="mockllm/model",
            compaction="all",
            depth=None,
        ):
            assert isinstance(seg, TimelineMessages)
            materialized_segments.append(seg)
        streamed = [(seg.span.id, seg.messages_str) for seg in streamed_segments]
        materialized_tuples = [
            (seg.span.id, seg.messages_str) for seg in materialized_segments
        ]
        assert streamed  # non-vacuous: the fixture must yield >=1 segment
        assert streamed == materialized_tuples
    finally:
        await view.disconnect()
