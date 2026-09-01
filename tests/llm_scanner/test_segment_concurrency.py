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

    await scan_fn(transcript)

    assert peak > 1, "test should exercise concurrency (multiple segments in flight)"
    assert peak <= limit, f"peak in-flight {peak} exceeded window limit={limit}"


@pytest.mark.anyio
async def test_bounded_segment_concurrency_batch_mode() -> None:
    """Batch mode (no explicit max_connections) uses _SEGMENT_WINDOW_CAP, not the provider's non-batch default.

    inspect_ai resolves batch mode's effective max_connections to
    DEFAULT_MAX_CONNECTIONS_BATCH (10_000), far above the cap -- so the window
    should reach _SEGMENT_WINDOW_CAP (16). `model.api.max_connections()` (10 for
    mockllm) is the *non-batch* provider default and must not leak into the
    window when `config.batch` is set.

    Calls `_scan_segments_bounded` directly (skipping the full scanner and any
    real `generate` call) so this isn't muddied by inspect_ai's own model-level
    connection semaphore/cache, the same concern that ruled out measuring the
    other two legs inside a mock `generate`.
    """
    model = get_model("mockllm/model", config=GenerateConfig(batch=True), memoize=False)
    assert model.api.max_connections() == 10  # sanity: would wrongly cap the window

    in_flight = 0
    peak = 0

    async def scan_segment(messages_str: str) -> Result:
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        try:
            await anyio.sleep(0.01)
        finally:
            in_flight -= 1
        return Result(value=True)

    async def source() -> AsyncIterator[tuple[str | None, str]]:
        for i in range(20):
            yield None, f"segment {i}"

    await llm_scanner_mod._scan_segments_bounded(source(), scan_segment, model)

    assert peak > 10, f"window degraded to the non-batch provider default (peak={peak})"
    assert peak <= 16


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
