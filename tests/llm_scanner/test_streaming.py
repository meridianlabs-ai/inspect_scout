"""Tests for llm_scanner streaming: handle input, bounded concurrency, ordering.

Covers ``llm_scanner``'s streaming segmentation:

- A ``TranscriptHandle`` input produces a Result equivalent to a
  ``Transcript`` input over the same content.
- The ``SCANNER_SUPPORTS_STREAMING_ATTR`` capability attr is set only when
  streaming can work without the full transcript (static config), and not
  when a callable ``question``/``template_variables`` or event/timeline
  content would force materialization.
- Segment scanning is bounded by ``_SEGMENT_CONCURRENCY`` (no more than N
  ``generate`` calls in flight at once).
- Segment order is preserved through reduction.
"""

from __future__ import annotations

from typing import cast

import anyio
import pytest
from inspect_ai.model import (
    ChatMessage,
    ChatMessageUser,
    GenerateConfig,
    Model,
    ModelOutput,
    get_model,
)
from inspect_ai.tool import ToolChoice, ToolInfo
from inspect_scout import llm_scanner
from inspect_scout._llm_scanner import _llm_scanner as llm_scanner_mod
from inspect_scout._scanner.result import Result
from inspect_scout._scanner.scanner import SCANNER_SUPPORTS_STREAMING_ATTR, Scanner
from inspect_scout._transcript.handle import MaterializedTranscriptHandle
from inspect_scout._transcript.types import (
    Transcript,
    TranscriptContent,
    TranscriptInfo,
)


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


def _handle_for(transcript: Transcript) -> MaterializedTranscriptHandle:
    async def load_fn() -> Transcript:
        return transcript

    info = TranscriptInfo(
        **transcript.model_dump(exclude={"messages", "events", "timelines"})
    )
    return MaterializedTranscriptHandle(load_fn, info)


async def _scan(
    scan_fn: Scanner[Transcript], input: Transcript | MaterializedTranscriptHandle
) -> Result:
    # The public scanner type is Scanner[Transcript]; llm_scanner's scan also
    # accepts a TranscriptHandle at runtime (streaming path). The scan returns
    # a single Result for these single-/multi-segment reduced scans.
    out = await scan_fn(cast(Transcript, input))
    assert isinstance(out, Result)
    return out


# ---------------------------------------------------------------------------
# (a) handle input equivalence
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_handle_input_equivalent_to_transcript_input() -> None:
    """Scanning a handle yields the same Result as scanning the Transcript."""
    transcript = _make_transcript(3)

    def capture(
        input_msgs: list[ChatMessage],
        tools: list[ToolInfo],
        tool_choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput:
        return ModelOutput.from_content(
            model="mockllm",
            content="Reasoning.\n\nANSWER: yes",
            stop_reason="stop",
        )

    mock_model = get_model("mockllm/model", custom_outputs=capture, memoize=False)

    scan_fn = llm_scanner(
        question="Is this helpful?",
        answer="boolean",
        model=mock_model,
    )

    result_transcript = await _scan(scan_fn, transcript)
    result_handle = await _scan(scan_fn, _handle_for(transcript))

    assert result_handle.value == result_transcript.value
    assert result_handle.answer == result_transcript.answer


# ---------------------------------------------------------------------------
# (b) capability attr gating
# ---------------------------------------------------------------------------


def test_static_config_sets_handle_attr() -> None:
    scan_fn = llm_scanner(question="static?", answer="boolean")
    assert getattr(scan_fn, SCANNER_SUPPORTS_STREAMING_ATTR, False) is True


def test_callable_question_does_not_set_handle_attr() -> None:
    async def question(_t: Transcript) -> str:
        return "dynamic?"

    scan_fn = llm_scanner(question=question, answer="boolean")
    assert getattr(scan_fn, SCANNER_SUPPORTS_STREAMING_ATTR, False) is False


def test_callable_template_variables_does_not_set_handle_attr() -> None:
    def template_variables(_t: Transcript) -> dict[str, object]:
        return {"extra": 1}

    scan_fn = llm_scanner(
        question="static?",
        answer="boolean",
        template_variables=template_variables,
    )
    assert getattr(scan_fn, SCANNER_SUPPORTS_STREAMING_ATTR, False) is False


def test_timeline_does_not_set_handle_attr() -> None:
    scan_fn = llm_scanner(question="static?", answer="boolean", timeline="agent")
    assert getattr(scan_fn, SCANNER_SUPPORTS_STREAMING_ATTR, False) is False


def test_content_with_events_sets_handle_attr() -> None:
    # Events content is streaming-eligible (consumed via
    # stream_timeline_messages on the handle path), so a static config with
    # events content still opts in to streaming.
    scan_fn = llm_scanner(
        question="static?",
        answer="boolean",
        content=TranscriptContent(events="all"),
    )
    assert getattr(scan_fn, SCANNER_SUPPORTS_STREAMING_ATTR, False) is True


def test_content_with_timeline_does_not_set_handle_attr() -> None:
    # A timeline content filter still forces materialization (named-timeline
    # selection and timeline extraction need the full transcript).
    scan_fn = llm_scanner(
        question="static?",
        answer="boolean",
        content=TranscriptContent(timeline="all"),
    )
    assert getattr(scan_fn, SCANNER_SUPPORTS_STREAMING_ATTR, False) is False


def test_content_messages_only_still_sets_handle_attr() -> None:
    scan_fn = llm_scanner(
        question="static?",
        answer="boolean",
        content=TranscriptContent(messages="all"),
    )
    assert getattr(scan_fn, SCANNER_SUPPORTS_STREAMING_ATTR, False) is True


# ---------------------------------------------------------------------------
# (c) bounded concurrency
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_bounded_segment_concurrency(monkeypatch: pytest.MonkeyPatch) -> None:
    """No more than _SEGMENT_CONCURRENCY generate calls run concurrently."""
    monkeypatch.setattr(llm_scanner_mod, "_SEGMENT_CONCURRENCY", 2)

    transcript = _make_transcript(12, words=80)

    in_flight = 0
    peak = 0

    async def custom(
        input_msgs: list[ChatMessage],
        tools: list[ToolInfo],
        tool_choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput:
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        try:
            # Yield control so overlapping calls can accumulate.
            await anyio.sleep(0.01)
        finally:
            in_flight -= 1
        return ModelOutput.from_content(
            model="mockllm",
            content="Reasoning.\n\nANSWER: yes",
            stop_reason="stop",
        )

    mock_model = get_model("mockllm/model", custom_outputs=custom, memoize=False)

    scan_fn = llm_scanner(
        question="Is this helpful?",
        answer="boolean",
        model=mock_model,
        # Force multiple small segments (yields 6 with this padding).
        context_window=400,
    )

    await _scan(scan_fn, _handle_for(transcript))

    assert peak > 1, "test should exercise concurrency (multiple segments in flight)"
    assert peak <= 2, f"peak in-flight {peak} exceeded _SEGMENT_CONCURRENCY=2"


@pytest.mark.anyio
async def test_bounded_segment_concurrency_materialized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Transcript (materialized) path is also bounded."""
    monkeypatch.setattr(llm_scanner_mod, "_SEGMENT_CONCURRENCY", 2)

    transcript = _make_transcript(12, words=80)

    in_flight = 0
    peak = 0

    async def custom(
        input_msgs: list[ChatMessage],
        tools: list[ToolInfo],
        tool_choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput:
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        try:
            await anyio.sleep(0.01)
        finally:
            in_flight -= 1
        return ModelOutput.from_content(
            model="mockllm",
            content="Reasoning.\n\nANSWER: yes",
            stop_reason="stop",
        )

    mock_model = get_model("mockllm/model", custom_outputs=custom, memoize=False)

    scan_fn = llm_scanner(
        question="Is this helpful?",
        answer="boolean",
        model=mock_model,
        context_window=400,
    )

    await _scan(scan_fn, transcript)

    assert peak > 1, "test should exercise concurrency (multiple segments in flight)"
    assert peak <= 2, f"peak in-flight {peak} exceeded _SEGMENT_CONCURRENCY=2"


# ---------------------------------------------------------------------------
# (d) segment order preserved through reduction
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_segment_order_preserved_in_reduction() -> None:
    """Segment order survives concurrent scanning + reduction.

    Each segment's mock answer encodes the message index it contains. With a
    string answer the default reducer concatenates per-segment explanations
    in order; asserting the merged explanation preserves ascending order
    verifies the sort-by-index step.
    """
    n = 8
    transcript = _make_transcript(n, words=80)

    async def custom(
        input_msgs: list[ChatMessage],
        tools: list[ToolInfo],
        tool_choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput:
        # Recover the message index embedded in the rendered prompt so each
        # segment's answer is distinguishable and order-checkable.
        text = "\n".join(m.text for m in input_msgs)
        idx = -1
        for i in range(n):
            if f"message number {i}" in text:
                idx = i
                break
        # Sleep longer for earlier segments so they COMPLETE last — forcing
        # out-of-order task completion. Only the sort-by-index step can then
        # restore ascending order for the reducer.
        await anyio.sleep(0.02 * (n - idx))
        return ModelOutput.from_content(
            model="mockllm",
            content=f"Segment covering index {idx}.\n\nANSWER: seg{idx}",
            stop_reason="stop",
        )

    mock_model = get_model("mockllm/model", custom_outputs=custom, memoize=False)

    scan_fn = llm_scanner(
        question="What is here?",
        answer="string",
        model=mock_model,
        context_window=400,
        # Use a reducer that just records order so we don't depend on an LLM.
        reducer=_recording_reducer,
    )

    await _scan(scan_fn, _handle_for(transcript))

    assert _recorded_order, "reducer should have received multiple segments"
    # Extract the leading index from each recorded answer ("seg0", "seg3", ...)
    indices = [int(ans.removeprefix("seg")) for ans in _recorded_order]
    assert indices == sorted(indices), f"segment order not preserved: {indices}"


# ---------------------------------------------------------------------------
# (e) events content: handle path via stream_timeline_messages
# ---------------------------------------------------------------------------


def _handle_for_transcript(transcript: Transcript) -> MaterializedTranscriptHandle:
    """Build a MaterializedTranscriptHandle for an arbitrary transcript."""

    async def load_fn() -> Transcript:
        return transcript

    info = TranscriptInfo(
        **transcript.model_dump(exclude={"messages", "events", "timelines"})
    )
    return MaterializedTranscriptHandle(load_fn, info)


def _yes_model() -> Model:
    def capture(
        input_msgs: list[ChatMessage],
        tools: list[ToolInfo],
        tool_choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput:
        return ModelOutput.from_content(
            model="mockllm",
            content="Reasoning.\n\nANSWER: yes",
            stop_reason="stop",
        )

    return get_model("mockllm/model", custom_outputs=capture, memoize=False)


@pytest.mark.anyio
async def test_handle_events_scan_equals_transcript_scan() -> None:
    """An events-content handle scan equals the materialized Transcript scan.

    The agentic fixture carries events (no top-level messages). Scanning it
    through a handle routes to ``stream_timeline_messages`` (two-pass event
    streaming); scanning the same ``Transcript`` routes to the materialized
    ``transcript_messages`` path. Both must produce the same Result.
    """
    from tests.transcript.fixtures_agentic import agentic_transcript

    transcript = agentic_transcript()

    scan_fn = llm_scanner(
        question="Did the agent use tools?",
        answer="boolean",
        model=_yes_model(),
        content=TranscriptContent(events="all"),
    )

    result_transcript = await _scan(scan_fn, transcript)
    result_handle = await _scan(scan_fn, _handle_for_transcript(transcript))

    assert result_handle.value == result_transcript.value
    assert result_handle.answer == result_transcript.answer
    assert result_handle.explanation == result_transcript.explanation


@pytest.mark.anyio
async def test_stub_unsupported_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    """A _StubSkeletonUnsupported during streaming falls back to materialized.

    Monkeypatching ``needed_model_event_uuids`` to raise
    ``_StubSkeletonUnsupported`` forces the handle events path to abort; the
    scanner must recover by materializing the transcript and produce the same
    Result the fully materialized path would.
    """
    from inspect_scout._transcript import timeline_stream
    from inspect_scout._transcript.timeline_stream import _StubSkeletonUnsupported

    from tests.transcript.fixtures_agentic import agentic_transcript

    transcript = agentic_transcript()

    scan_fn = llm_scanner(
        question="Did the agent use tools?",
        answer="boolean",
        model=_yes_model(),
        content=TranscriptContent(events="all"),
    )

    # Baseline: fully materialized Result.
    expected = await _scan(scan_fn, transcript)

    def _raise(*_args: object, **_kwargs: object) -> set[str]:
        raise _StubSkeletonUnsupported("forced for test")

    monkeypatch.setattr(timeline_stream, "needed_model_event_uuids", _raise)

    fallback = await _scan(scan_fn, _handle_for_transcript(transcript))

    assert fallback.value == expected.value
    assert fallback.answer == expected.answer
    assert fallback.explanation == expected.explanation


_recorded_order: list[str] = []


async def _recording_reducer(results: list[Result]) -> Result:
    _recorded_order.clear()
    for r in results:
        _recorded_order.append(str(r.answer))
    return results[0]
