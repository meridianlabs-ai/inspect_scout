"""Tests for llm_scanner's bounded segment concurrency window."""

from __future__ import annotations

from typing import AsyncIterator, Awaitable, Callable

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
from inspect_scout._transcript.messages import MessagesSegment
from inspect_scout._transcript.types import Transcript


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


# -- bounded concurrency tests --


@pytest.mark.anyio
async def test_bounded_segment_concurrency(monkeypatch: pytest.MonkeyPatch) -> None:
    """No more than _SEGMENT_WINDOW_CAP segments are scanned concurrently."""
    monkeypatch.setattr(llm_scanner_mod, "_SEGMENT_WINDOW_CAP", 2)

    # Count concurrency at _scan_segments_bounded's own admission window, not
    # inside the mock `generate` call: inspect_ai's model-level connection
    # semaphore independently caps concurrent `generate` calls, which would
    # mask a window that admits too many segments if measured there instead.
    in_flight = 0
    peak = 0
    original_bounded = llm_scanner_mod._scan_segments_bounded

    async def counting_bounded(
        segments: AsyncIterator[MessagesSegment],
        scan_segment: Callable[[str], Awaitable[Result]],
    ) -> list[tuple[str | None, Result]]:
        async def counted_segment(messages_str: str) -> Result:
            nonlocal in_flight, peak
            in_flight += 1
            peak = max(peak, in_flight)
            try:
                return await scan_segment(messages_str)
            finally:
                in_flight -= 1

        return await original_bounded(segments, counted_segment)

    monkeypatch.setattr(llm_scanner_mod, "_scan_segments_bounded", counting_bounded)

    transcript = _make_transcript(12, words=80)

    async def custom(
        input_msgs: list[ChatMessage],
        tools: list[ToolInfo],
        tool_choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput:
        # Yield control so overlapping calls can accumulate.
        await anyio.sleep(0.01)
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

    await scan_fn(transcript)

    assert peak > 1, "test should exercise concurrency (multiple segments in flight)"
    assert peak <= 2, f"peak in-flight {peak} exceeded the window cap"


@pytest.mark.anyio
async def test_segment_window_admits_before_pulling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A window slot is taken before the next segment is pulled off the source.

    Pulling first would render (and hold) one segment string beyond the cap.
    """
    monkeypatch.setattr(llm_scanner_mod, "_SEGMENT_WINDOW_CAP", 2)

    pulled = 0
    completed = 0

    async def segments() -> AsyncIterator[MessagesSegment]:
        nonlocal pulled
        for i in range(6):
            pulled += 1
            yield MessagesSegment(messages=[], messages_str=f"seg {i}", segment=i)

    async def scan_segment(messages_str: str) -> Result:
        nonlocal completed
        await anyio.sleep(0.01)
        assert pulled <= completed + 2, (
            f"pulled {pulled} segments with {completed} scanned and a cap of 2"
        )
        completed += 1
        return Result(value=True)

    await llm_scanner_mod._scan_segments_bounded(segments(), scan_segment)

    assert pulled == 6


# -- segment order tests --


@pytest.mark.anyio
async def test_segment_order_preserved_in_reduction() -> None:
    """Segment order survives concurrent scanning + reduction.

    Each segment's mock answer encodes the message index it contains. The
    recording reducer captures per-segment answers in the order it receives
    them; asserting that order is ascending verifies the sort-by-index step.
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
        # Sleep longer for earlier segments so they COMPLETE last -- forcing
        # out-of-order task completion. Only the sort-by-index step can then
        # restore ascending order for the reducer.
        await anyio.sleep(0.02 * (n - idx))
        return ModelOutput.from_content(
            model="mockllm",
            content=f"Segment covering index {idx}.\n\nANSWER: seg{idx}",
            stop_reason="stop",
        )

    mock_model: Model = get_model("mockllm/model", custom_outputs=custom, memoize=False)

    recorded_order: list[str] = []

    async def reducer(results: list[Result]) -> Result:
        recorded_order.clear()
        recorded_order.extend(str(r.answer) for r in results)
        return results[0]

    scan_fn = llm_scanner(
        question="What is here?",
        answer="string",
        model=mock_model,
        context_window=400,
        # Use a reducer that just records order so we don't depend on an LLM.
        reducer=reducer,
    )

    await scan_fn(transcript)

    assert recorded_order, "reducer should have received multiple segments"
    indices = [int(ans.removeprefix("seg")) for ans in recorded_order]
    assert indices == sorted(indices), f"segment order not preserved: {indices}"
