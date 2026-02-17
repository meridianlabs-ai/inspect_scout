"""Tests for scan_segments parallel execution."""

from collections.abc import AsyncIterator

import anyio
import pytest
from inspect_scout._llm_scanner._parallel import scan_segments
from inspect_scout._scanner.result import Result, as_resultset
from inspect_scout._transcript.messages import MessagesSegment


async def _segments(*texts: str) -> AsyncIterator[MessagesSegment]:
    """Create an async iterator of MessagesSegment from text strings."""
    for i, text in enumerate(texts):
        yield MessagesSegment(messages=[], text=text, segment=i)


@pytest.mark.anyio
async def test_single_segment() -> None:
    """Single segment returns a one-element list."""

    async def scan_fn(seg: MessagesSegment) -> Result:
        return Result(value=seg.text, answer=seg.text)

    results = await scan_segments(_segments("hello"), scan_fn)
    assert len(results) == 1
    assert results[0].value == "hello"


@pytest.mark.anyio
async def test_multiple_segments_in_order() -> None:
    """Results are returned in segment order regardless of completion order."""

    async def scan_fn(seg: MessagesSegment) -> Result:
        # Earlier segments take longer to complete
        delay = 0.1 if seg.text == "first" else 0.0
        await anyio.sleep(delay)
        return Result(value=seg.text, answer=seg.text)

    results = await scan_segments(_segments("first", "second", "third"), scan_fn)
    assert [r.value for r in results] == ["first", "second", "third"]


@pytest.mark.anyio
async def test_empty_segments() -> None:
    """Empty iterator returns empty list."""

    async def scan_fn(seg: MessagesSegment) -> Result:
        raise AssertionError("should not be called")

    results = await scan_segments(_segments(), scan_fn)
    assert results == []


@pytest.mark.anyio
async def test_error_propagates() -> None:
    """Exception in scan_fn propagates as the original exception type."""

    async def scan_fn(seg: MessagesSegment) -> Result:
        raise RuntimeError("scan failed")

    with pytest.raises(RuntimeError, match="scan failed"):
        await scan_segments(_segments("a"), scan_fn)


@pytest.mark.anyio
async def test_concurrent_execution() -> None:
    """Multiple segments execute concurrently, not sequentially."""
    timestamps: list[float] = []

    async def scan_fn(seg: MessagesSegment) -> Result:
        timestamps.append(anyio.current_time())
        await anyio.sleep(0.1)
        return Result(value=seg.text, answer=seg.text)

    await scan_segments(_segments("a", "b", "c"), scan_fn)

    # All three should start within a small window (concurrent),
    # not 0.1s apart (sequential)
    assert len(timestamps) == 3
    assert max(timestamps) - min(timestamps) < 0.05


@pytest.mark.anyio
async def test_resultset_flattening() -> None:
    """Resultset Results from structured answers are flattened."""

    async def scan_fn(seg: MessagesSegment) -> Result:
        if seg.text == "multi":
            return as_resultset(
                [
                    Result(value="a", answer="A"),
                    Result(value="b", answer="B"),
                ]
            )
        return Result(value="plain", answer="P")

    results = await scan_segments(_segments("plain", "multi"), scan_fn)
    assert len(results) == 3
    assert results[0].value == "plain"
    assert results[1].value == "a"
    assert results[2].value == "b"
