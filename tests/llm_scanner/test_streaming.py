"""Tests for llm_scanner streaming: handle input, ordering, and fallback.

Covers ``llm_scanner``'s streaming segmentation:

- A ``TranscriptHandle`` input produces the same prompts and Result as a
  ``Transcript`` input over the same content (messages and events paths).
- The ``SCANNER_SUPPORTS_STREAMING_ATTR`` capability attr is set only when
  streaming can work without the full transcript (static config), and not
  when a callable ``question``/``template_variables`` or timeline content
  would force materialization.
- The runtime mirror of the opt-in logic materializes the handle when a
  callable ``question`` needs the full transcript.
- A ``_StubSkeletonUnsupported`` during streaming events falls back to a
  materialized scan.

Bounded segment concurrency and segment-order-through-reduction are covered
in ``test_segment_concurrency.py``.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, cast

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
from inspect_scout._scanner.extract import MessagesPreprocessor
from inspect_scout._scanner.result import Result
from inspect_scout._scanner.scanner import SCANNER_SUPPORTS_STREAMING_ATTR, Scanner
from inspect_scout._transcript.handle import MaterializedTranscriptHandle
from inspect_scout._transcript.types import (
    Transcript,
    TranscriptContent,
    TranscriptInfo,
)

from tests.transcript.fixtures_agentic import agentic_transcript


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
    """Build a MaterializedTranscriptHandle for an arbitrary transcript."""

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


# ---------------------------------------------------------------------------
# (a) handle input equivalence
# ---------------------------------------------------------------------------


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("make_transcript", "scanner_kwargs", "min_prompts"),
    [
        # Single segment: raw messages, fits in one prompt.
        pytest.param(
            lambda: _make_transcript(3),
            {},
            1,
            id="messages-single-segment",
        ),
        # Multiple segments: 12 padded messages under a small context window.
        pytest.param(
            lambda: _make_transcript(12, words=80),
            {"context_window": 400},
            2,
            id="messages-multi-segment",
        ),
        # Events content: the handle path routes to stream_timeline_messages
        # (two-pass event streaming); the Transcript path routes to the
        # materialized transcript_messages path. Prompts must still match.
        pytest.param(
            agentic_transcript,
            {"content": TranscriptContent(events="all")},
            2,
            id="events",
        ),
    ],
)
async def test_handle_scan_equivalent_to_transcript_scan(
    make_transcript: Callable[[], Transcript],
    scanner_kwargs: dict[str, Any],
    min_prompts: int,
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

    result_handle = await _scan(scan_fn, _handle_for(transcript))
    prompts_handle = list(recorded)

    assert len(prompts_transcript) >= min_prompts
    assert prompts_handle == prompts_transcript
    assert result_handle.value == result_transcript.value
    assert result_handle.answer == result_transcript.answer
    assert result_handle.explanation == result_transcript.explanation


# ---------------------------------------------------------------------------
# (b) capability attr gating
# ---------------------------------------------------------------------------


async def _dynamic_question(_t: Transcript) -> str:
    return "dynamic?"


def _dynamic_template_variables(_t: Transcript) -> dict[str, Any]:
    return {"extra": 1}


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        pytest.param({}, True, id="static"),
        pytest.param({"question": _dynamic_question}, False, id="callable-question"),
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
        pytest.param(
            {"content": TranscriptContent(messages="all")}, True, id="content-messages"
        ),
        # A timeline content filter still forces materialization
        # (named-timeline selection and extraction need the full transcript).
        pytest.param(
            {"content": TranscriptContent(timeline="all")}, False, id="content-timeline"
        ),
        # Preprocessors receive per-segment message lists, so they stay
        # streaming-safe.
        pytest.param(
            {"preprocessor": MessagesPreprocessor[Transcript]()},
            True,
            id="preprocessor",
        ),
    ],
)
def test_streaming_attr_gating(kwargs: dict[str, Any], expected: bool) -> None:
    """SCANNER_SUPPORTS_STREAMING_ATTR is set only for streaming-safe configs."""
    call_kwargs: dict[str, Any] = {"question": "static?", "answer": "boolean"} | kwargs
    scan_fn = llm_scanner(**call_kwargs)
    assert getattr(scan_fn, SCANNER_SUPPORTS_STREAMING_ATTR, False) is expected


# ---------------------------------------------------------------------------
# (c) streaming fallback and runtime materialization
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_stub_unsupported_falls_back(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A _StubSkeletonUnsupported during streaming falls back to materialized.

    Monkeypatching ``needed_model_event_uuids`` to raise
    ``_StubSkeletonUnsupported`` forces the handle events path to abort; the
    scanner must recover by materializing the transcript and produce the same
    Result the fully materialized path would.
    """
    from inspect_scout._transcript import timeline_stream
    from inspect_scout._transcript.timeline_stream import _StubSkeletonUnsupported

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

    with caplog.at_level(
        logging.INFO, logger="inspect_scout._llm_scanner._llm_scanner"
    ):
        fallback = await _scan(scan_fn, _handle_for(transcript))

    # Positive evidence the fallback path actually ran (the monkeypatched
    # function was called and the scanner recovered).
    assert any(
        "falling back to materialized scan" in record.getMessage()
        for record in caplog.records
    ), "expected a fallback log record from the streaming events path"

    assert fallback.value == expected.value
    assert fallback.answer == expected.answer
    assert fallback.explanation == expected.explanation


@pytest.mark.anyio
async def test_callable_question_with_handle_materializes() -> None:
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

    result = await _scan(scan_fn, _handle_for(transcript))
    assert result.answer is not None

    assert seen, "question callable should have been invoked"
    for t in seen:
        assert [m.id for m in t.messages] == [m.id for m in transcript.messages], (
            "question callable should receive the materialized transcript content"
        )
