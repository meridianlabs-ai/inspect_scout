"""jev_scanner on timeline (multi-span) and streaming transcript inputs."""

from pathlib import Path
from typing import cast

import pytest
from inspect_ai.event import ModelEvent, Timeline, TimelineEvent, TimelineSpan
from inspect_ai.model import ChatMessageUser, ModelOutput
from inspect_scout import Result, cascade_scanner, jev_scanner
from inspect_scout._transcript.handle import SpooledTranscriptHandle
from inspect_scout._transcript.types import Transcript

from tests.llm_scanner.test_streaming import _spooled_handle_for, _spy_on_load


def _span(span_id: str, text: str) -> TimelineSpan:
    event = ModelEvent.model_construct(
        event="model",
        uuid=f"{span_id}-event",
        model="mockllm",
        input=[ChatMessageUser(content=text)],
        output=ModelOutput.from_content(model="mockllm", content="ok"),
        role="assistant",
    )
    return TimelineSpan(
        id=span_id,
        name=span_id,
        span_type="agent",
        content=[TimelineEvent.model_construct(type="event", event=event)],
    )


def _two_span_transcript() -> Transcript:
    root = TimelineSpan(
        id="root",
        name="Transcript",
        span_type=None,
        content=[_span("a", "DESTROY everything"), _span("b", "all fine")],
    )
    return Transcript(
        transcript_id="timeline",
        timelines=[Timeline(name="Default", description="", root=root)],
    )


@pytest.mark.asyncio
async def test_multi_span_timeline_returns_a_resultset_per_span() -> None:
    result = await jev_scanner(
        question="Destructive?",
        answer="boolean",
        model="fakejev/test",
        value_to_float=lambda v: 1.0 if v else 0.0,
    )(_two_span_transcript())
    assert isinstance(result, Result) and result.type == "resultset"
    assert isinstance(result.value, list)
    values = [item["value"] for item in result.value if isinstance(item, dict)]
    assert values == [1.0, 0.0]


@pytest.mark.asyncio
async def test_cascade_escalates_when_any_span_matches() -> None:
    result = await cascade_scanner(
        question="Destructive?",
        answer="boolean",
        jev={"model": "fakejev/test"},
        llm=False,
    )(_two_span_transcript())
    assert isinstance(result, Result) and result.metadata is not None
    assert result.metadata["needs_review"] is True
    assert result.metadata["cascade"]["escalation_reasons"] == ["positive"]


@pytest.mark.asyncio
async def test_spooled_handle_is_streamed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    loads = _spy_on_load(monkeypatch, SpooledTranscriptHandle)
    transcript = Transcript(
        transcript_id="stream",
        messages=[
            ChatMessageUser(content="clean up", id="m0"),
            ChatMessageUser(content="rm -rf src DESTROY", id="m1"),
        ],
    )
    handle = _spooled_handle_for(transcript, tmp_path)
    result = await jev_scanner(
        question="Destructive?", answer="boolean", model="fakejev/test"
    )(cast(Transcript, handle))
    assert isinstance(result, Result)
    assert result.value is True
    assert [r.id for r in result.references] == ["m1"]
    assert loads == []
