"""Tests for llm_scanner streaming: handle input, capability gating, fallback.

Bounded segment concurrency and segment-order-through-reduction are covered
in ``test_segment_concurrency.py``.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
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
from inspect_scout._llm_scanner._llm_scanner import _must_materialize
from inspect_scout._scanner.result import Result
from inspect_scout._scanner.scanner import Scanner, streaming_support_of
from inspect_scout._transcript.handle import (
    MaterializedTranscriptHandle,
    SpooledTranscriptHandle,
    TranscriptHandle,
)
from inspect_scout._transcript.json.stream_parse import (
    StreamParseResult,
    stream_parse_to_spool,
)
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


def _spooled_handle_for(
    transcript: Transcript, spool_dir: Path
) -> SpooledTranscriptHandle:
    """A SpooledTranscriptHandle over `transcript`, so the streaming path is exercised."""
    sample = {
        "id": transcript.transcript_id,
        "messages": [m.model_dump(mode="json") for m in transcript.messages],
        "events": [e.model_dump(mode="json") for e in transcript.events],
    }
    data = json.dumps(sample).encode()
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
        assert load_calls, "expected the empty-segments fallback to load the handle"
    else:
        assert not load_calls, "streamed scan materialized the handle"
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
