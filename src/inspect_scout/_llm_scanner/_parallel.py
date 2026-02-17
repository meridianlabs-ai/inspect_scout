"""Parallel segment scanning with result flattening."""

import sys
from collections.abc import AsyncIterator, Awaitable, Callable

import anyio
from inspect_ai.util._anyio import inner_exception

if sys.version_info < (3, 11):
    from exceptiongroup import ExceptionGroup

from .._scanner.result import Result
from .._transcript.messages import MessagesSegment


async def scan_segments(
    segments: AsyncIterator[MessagesSegment],
    scan_fn: Callable[[MessagesSegment], Awaitable[Result]],
) -> list[Result]:
    """Scan segments in parallel, returning results in segment order.

    Iterates segments sequentially (message numbering requires ordered
    rendering) and spawns a parallel task for each segment's scan.
    The model's internal connection semaphore handles rate limiting.

    Any resultset Results (from structured answers with ``result_set=True``)
    are flattened into individual Results to prevent nesting when the
    framework wraps the returned list with ``as_resultset()``.

    Args:
        segments: Async iterator of pre-rendered segments (e.g., from
            ``transcript_messages()``).
        scan_fn: Async function that scans a single segment and returns
            a Result.

    Returns:
        Flattened results in segment order.
    """
    results: dict[int, Result] = {}

    async def run_scan(index: int, segment: MessagesSegment) -> None:
        results[index] = await scan_fn(segment)

    try:
        async with anyio.create_task_group() as tg:
            index = 0
            async for segment in segments:
                tg.start_soon(run_scan, index, segment)
                index += 1
    except ExceptionGroup as eg:
        # Unwrap exception groups so callers see the original error
        # (e.g., RuntimeError from refusal retries) rather than an opaque
        # ExceptionGroup wrapper.
        raise inner_exception(eg) from eg

    ordered = [results[i] for i in sorted(results)]
    return _flatten_results(ordered)


def _flatten_results(results: list[Result]) -> list[Result]:
    """Flatten any resultset Results into individual Results.

    When structured answers with result_set=True are used across
    multiple segments, each segment produces a Result(type="resultset").
    This function unrolls them so the caller can re-compose a single
    flat resultset, preventing nesting.
    """
    flat: list[Result] = []
    for r in results:
        if r.type == "resultset" and isinstance(r.value, list):
            for item in r.value:
                if isinstance(item, Result):
                    flat.append(item)
                else:
                    flat.append(Result.model_validate(item))
        else:
            flat.append(r)
    return flat
