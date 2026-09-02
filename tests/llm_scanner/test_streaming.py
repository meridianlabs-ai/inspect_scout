"""Tests for llm_scanner streaming: handle input, capability gating, fallback.

Bounded segment concurrency and segment-order-through-reduction are covered
in ``test_segment_concurrency.py``.
"""

from __future__ import annotations

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


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("make_transcript", "scanner_kwargs", "min_prompts"),
    [
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
            id="template-reads-transcript-info",
        ),
        # events="all" over a transcript that has no events: the materialized
        # path falls through to the messages segmenter, so the streaming path
        # must too rather than reducing over zero segments.
        pytest.param(
            lambda: _make_transcript(3),
            {"content": TranscriptContent(events="all")},
            1,
            id="events-requested-but-absent",
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
    """SCANNER_SUPPORTS_STREAMING_ATTR is set only for streaming-safe configs."""
    call_kwargs: dict[str, Any] = {"question": "static?", "answer": "boolean"} | kwargs
    scan_fn = llm_scanner(**call_kwargs)
    assert getattr(scan_fn, SCANNER_SUPPORTS_STREAMING_ATTR, False) is expected


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
