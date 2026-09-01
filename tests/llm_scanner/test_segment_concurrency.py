"""Tests for llm_scanner's bounded segment concurrency window.

Covers `_scan_segments_bounded`'s window sizing -- `min(model's effective
max_connections, _SEGMENT_WINDOW_CAP)` -- and that segment order survives
concurrent scanning + reduction.
"""

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
from inspect_scout._scanner.scanner import Scanner
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


async def _scan(scan_fn: Scanner[Transcript], transcript: Transcript) -> Result:
    out = await scan_fn(transcript)
    assert isinstance(out, Result)
    return out


# ---------------------------------------------------------------------------
# bounded concurrency: window = min(model max_connections, _SEGMENT_WINDOW_CAP)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("window_cap", "max_connections", "limit"),
    [
        # cap binds: model allows more connections than the cap permits.
        pytest.param(2, 10, 2, id="cap-binds"),
        # connections bind: the model allows fewer than the (much larger) cap.
        pytest.param(16, 2, 2, id="connections-bind"),
    ],
)
async def test_bounded_segment_concurrency(
    monkeypatch: pytest.MonkeyPatch,
    window_cap: int,
    max_connections: int,
    limit: int,
) -> None:
    """No more than min(_SEGMENT_WINDOW_CAP, model max_connections) segments scan concurrently."""
    monkeypatch.setattr(llm_scanner_mod, "_SEGMENT_WINDOW_CAP", window_cap)

    # Count concurrency at _scan_segments_bounded's own admission window, not
    # inside the mock `generate` call: inspect_ai's model-level connection
    # semaphore independently caps concurrent `generate` calls at
    # max_connections, which would mask an under-derived window on the
    # connections-bind leg if measured there instead.
    in_flight = 0
    peak = 0
    original_bounded = llm_scanner_mod._scan_segments_bounded

    async def counting_bounded(
        source: AsyncIterator[tuple[str | None, str]],
        scan_segment: Callable[[str], Awaitable[Result]],
        model: Model,
    ) -> list[tuple[str | None, Result]]:
        async def counted_segment(messages_str: str) -> Result:
            nonlocal in_flight, peak
            in_flight += 1
            peak = max(peak, in_flight)
            try:
                return await scan_segment(messages_str)
            finally:
                in_flight -= 1

        return await original_bounded(source, counted_segment, model)

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

    mock_model = get_model(
        "mockllm/model",
        custom_outputs=custom,
        memoize=False,
        config=GenerateConfig(max_connections=max_connections),
    )

    scan_fn = llm_scanner(
        question="Is this helpful?",
        answer="boolean",
        model=mock_model,
        # Force multiple small segments (yields 6 with this padding).
        context_window=400,
    )

    await _scan(scan_fn, transcript)

    assert peak > 1, "test should exercise concurrency (multiple segments in flight)"
    assert peak <= limit, f"peak in-flight {peak} exceeded window limit={limit}"


# ---------------------------------------------------------------------------
# segment order preserved through reduction
# ---------------------------------------------------------------------------


def _make_recording_reducer() -> tuple[
    Callable[[list[Result]], Awaitable[Result]], list[str]
]:
    """Build a reducer that records the answers it receives, in order."""
    recorded: list[str] = []

    async def reducer(results: list[Result]) -> Result:
        recorded.clear()
        recorded.extend(str(r.answer) for r in results)
        return results[0]

    return reducer, recorded


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

    reducer, recorded_order = _make_recording_reducer()
    scan_fn = llm_scanner(
        question="What is here?",
        answer="string",
        model=mock_model,
        context_window=400,
        # Use a reducer that just records order so we don't depend on an LLM.
        reducer=reducer,
    )

    await _scan(scan_fn, transcript)

    assert recorded_order, "reducer should have received multiple segments"
    # Extract the leading index from each recorded answer ("seg0", "seg3", ...)
    indices = [int(ans.removeprefix("seg")) for ans in recorded_order]
    assert indices == sorted(indices), f"segment order not preserved: {indices}"
