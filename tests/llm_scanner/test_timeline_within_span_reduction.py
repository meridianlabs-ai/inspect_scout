"""Integration tests for issue #431: within-span chunk reduction for timeline scans.

When a single timeline span's messages exceed ``context_window``, the
scanner splits them across multiple segments and produces one Result per
segment. Those per-chunk Results must be reduced into one Result per span
before being packed into a resultset; cross-span attribution stays in the
resultset.
"""

from __future__ import annotations

from typing import Any, cast

import pytest
from inspect_ai.event import ModelEvent, Timeline, TimelineEvent, TimelineSpan
from inspect_ai.model import (
    ChatMessageUser,
    ModelOutput,
    get_model,
)
from inspect_scout import llm_scanner
from inspect_scout._scanner.result import Result
from inspect_scout._transcript.types import Transcript

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _model_event(
    *,
    input_texts: list[str],
    output_text: str | None,
    uuid: str,
) -> ModelEvent:
    """Build a ModelEvent whose extracted messages are input + output."""
    input_messages = [ChatMessageUser(content=text) for text in input_texts]
    if output_text is not None:
        output = ModelOutput.from_content(model="mockllm", content=output_text)
    else:
        output = ModelOutput.model_construct(model="mockllm", choices=[])
    return ModelEvent.model_construct(
        event="model",
        uuid=uuid,
        model="mockllm",
        input=input_messages,
        output=output,
        role="assistant",
    )


def _scannable_span(
    *,
    span_id: str,
    name: str,
    events: list[ModelEvent],
) -> TimelineSpan:
    return TimelineSpan(
        id=span_id,
        name=name,
        span_type="agent",
        content=[TimelineEvent.model_construct(type="event", event=e) for e in events],
    )


def _transcript_with_spans(spans: list[TimelineSpan]) -> Transcript:
    """Wrap spans in a root container span + Timeline + Transcript."""
    root = TimelineSpan(
        id="root",
        name="Transcript",
        span_type=None,
        content=list(spans),
    )
    timeline = Timeline(name="Default", description="", root=root)
    return Transcript(
        transcript_id="test",
        timelines=[timeline],
    )


def _yes_no_outputs(answers: list[str]) -> list[ModelOutput]:
    return [
        ModelOutput.from_content(
            model="mockllm",
            content=f"Reasoning here.\n\nANSWER: {a}",
            stop_reason="stop",
        )
        for a in answers
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_single_span_multi_chunk_reduces_to_single_result() -> None:
    """One span with messages chunked across segments -> single Result."""
    span = _scannable_span(
        span_id="span-a",
        name="agent",
        events=[
            _model_event(
                input_texts=["first user msg"], output_text="asst reply", uuid="m1"
            ),
        ],
    )
    transcript = _transcript_with_spans([span])

    # context_window=1 forces each rendered message into its own segment
    # (2 messages -> 2 segments). Prime 2 distinct answers.
    mock_model = get_model(
        "mockllm/model",
        custom_outputs=_yes_no_outputs(["no", "yes"]),
        memoize=False,
    )
    scan_fn = llm_scanner(
        question="Is this helpful?",
        answer="boolean",
        model=mock_model,
        context_window=1,
    )

    out = await scan_fn(transcript)

    # Single-span shortcut: returned directly, not wrapped in a resultset.
    assert isinstance(out, Result)
    assert out.type != "resultset"
    # ResultReducer.any: True if any chunk said yes.
    assert out.value is True


@pytest.mark.anyio
async def test_multi_span_one_chunked_returns_resultset() -> None:
    """Two spans, only the first is chunked: resultset with one entry per span."""
    chunked_span = _scannable_span(
        span_id="span-a",
        name="agent-a",
        events=[
            _model_event(
                input_texts=["user msg a"], output_text="asst reply a", uuid="ma"
            ),
        ],
    )
    # Span B: empty input, output only -> exactly one extracted message -> 1 segment
    single_chunk_span = _scannable_span(
        span_id="span-b",
        name="agent-b",
        events=[
            _model_event(input_texts=[], output_text="asst reply b", uuid="mb"),
        ],
    )
    transcript = _transcript_with_spans([chunked_span, single_chunk_span])

    # Span A produces 2 segments (no, yes) -> reduced to True via .any
    # Span B produces 1 segment (no) -> passes through as False
    mock_model = get_model(
        "mockllm/model",
        custom_outputs=_yes_no_outputs(["no", "yes", "no"]),
        memoize=False,
    )
    scan_fn = llm_scanner(
        question="Is this helpful?",
        answer="boolean",
        model=mock_model,
        context_window=1,
    )

    out = await scan_fn(transcript)

    assert isinstance(out, Result)
    assert out.type == "resultset"
    assert isinstance(out.value, list)
    entries = cast(list[dict[str, Any]], out.value)
    assert len(entries) == 2
    assert entries[0]["value"] is True  # reduced from chunked span A
    assert entries[1]["value"] is False  # passthrough single-chunk span B


@pytest.mark.anyio
async def test_custom_reducer_invoked_on_timeline_scans() -> None:
    """Custom reducer fires once per multi-chunk span (previously ignored on timelines)."""
    span = _scannable_span(
        span_id="span-a",
        name="agent",
        events=[
            _model_event(
                input_texts=["first user msg"], output_text="asst reply", uuid="m1"
            ),
        ],
    )
    transcript = _transcript_with_spans([span])

    calls: list[list[Result]] = []

    async def recording_reducer(group: list[Result]) -> Result:
        calls.append(list(group))
        # Behave like ResultReducer.any so the test can also check the value
        any_true = any(r.value is True for r in group)
        return Result(value=any_true, answer="yes" if any_true else "no")

    mock_model = get_model(
        "mockllm/model",
        custom_outputs=_yes_no_outputs(["no", "yes"]),
        memoize=False,
    )
    scan_fn = llm_scanner(
        question="Is this helpful?",
        answer="boolean",
        model=mock_model,
        context_window=1,
        reducer=recording_reducer,
    )

    out = await scan_fn(transcript)

    # Reducer was called exactly once with both chunks (used to be silently
    # bypassed on timeline scans).
    assert len(calls) == 1
    assert len(calls[0]) == 2
    chunk_values = sorted(cast(bool, r.value) for r in calls[0])
    assert chunk_values == [False, True]
    # And the single-span shortcut still applies: not a resultset.
    assert isinstance(out, Result)
    assert out.type != "resultset"
    assert out.value is True
