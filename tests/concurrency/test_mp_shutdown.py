"""A consumed, undecodable queue item must not bypass process teardown."""

from __future__ import annotations

import logging
import multiprocessing
from collections.abc import Callable
from multiprocessing.connection import Connection
from multiprocessing.queues import Queue
from multiprocessing.synchronize import Event
from threading import Condition
from threading import Event as ThreadEvent
from types import SimpleNamespace
from typing import cast

import pytest
from inspect_scout._concurrency._mp_common import IPCContext, ShutdownSentinel
from inspect_scout._concurrency._mp_shutdown import shutdown_subprocesses


class ReconstructionError(Exception):
    def __init__(self, message: str, *, detail: str) -> None:
        super().__init__(message)
        self.detail = detail


def _fail_reconstruction() -> None:
    raise ValueError("fixture decode failure")


class ValueErrorOnLoad:
    def __reduce__(self) -> tuple[Callable[[], None], tuple[()]]:
        return _fail_reconstruction, ()


def _flush_items(queue: Queue[object], phase: int, value_error: bool = False) -> None:
    if phase == 6:
        queue.put(None)
    queue.put(
        ValueErrorOnLoad()
        if value_error
        else ReconstructionError("worker failure", detail="required keyword")
    )
    queue.close()
    queue.join_thread()


def _wait_for_termination(ready: Event) -> None:
    ready.set()
    ThreadEvent().wait(60)


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", [2, 6])
@pytest.mark.parametrize("queue_name", ["parse_job_queue", "upstream_queue"])
@pytest.mark.parametrize("error_type", [TypeError, ValueError])
async def test_undecodable_item_finishes_shutdown(
    phase: int,
    queue_name: str,
    error_type: type[Exception],
    caplog: pytest.LogCaptureFixture,
) -> None:
    spawn = multiprocessing.get_context("spawn")
    parse_queue: Queue[object] = spawn.Queue()
    upstream_queue: Queue[object] = spawn.Queue()
    queue = parse_queue if queue_name == "parse_job_queue" else upstream_queue
    child = spawn.Process(
        target=_flush_items, args=(queue, phase, error_type is ValueError)
    )
    ctx = cast(
        IPCContext,
        SimpleNamespace(
            shutdown_condition=Condition(),
            parse_job_queue=parse_queue,
            upstream_queue=upstream_queue,
        ),
    )
    try:
        child.start()
        child.join(timeout=10)
        assert child.exitcode == 0, "fixture did not flush its queue"
        with caplog.at_level(logging.WARNING):
            failure = await shutdown_subprocesses(
                [child], ctx, lambda *_: None, ShutdownSentinel()
            )
        assert isinstance(failure, error_type)
        expected_message = (
            "detail" if error_type is TypeError else "fixture decode failure"
        )
        assert expected_message in str(failure)
        assert queue_name in caplog.text
        for closed_queue in (parse_queue, upstream_queue):
            with pytest.raises(ValueError, match="closed"):
                closed_queue.get_nowait()
        assert not child.is_alive()
    finally:
        if child.is_alive():
            child.kill()
            child.join(timeout=5)
        for item in (parse_queue, upstream_queue):
            item.close()
            item.cancel_join_thread()


@pytest.mark.asyncio
async def test_drain_failure_does_not_strand_live_worker() -> None:
    spawn = multiprocessing.get_context("spawn")
    parse_queue: Queue[object] = spawn.Queue()
    upstream_queue: Queue[object] = spawn.Queue()
    sender = spawn.Process(target=_flush_items, args=(upstream_queue, 2))
    ready = spawn.Event()
    survivor = spawn.Process(target=_wait_for_termination, args=(ready,))
    ctx = cast(
        IPCContext,
        SimpleNamespace(
            shutdown_condition=Condition(),
            parse_job_queue=parse_queue,
            upstream_queue=upstream_queue,
        ),
    )
    try:
        sender.start()
        sender.join(timeout=10)
        assert sender.exitcode == 0
        survivor.start()
        assert ready.wait(timeout=10)
        failure = await shutdown_subprocesses(
            [sender, survivor], ctx, lambda *_: None, ShutdownSentinel()
        )
        assert isinstance(failure, TypeError)
        assert not survivor.is_alive()
        assert survivor.exitcode is not None and survivor.exitcode != 0
    finally:
        for child in (sender, survivor):
            if child.is_alive():
                child.kill()
                child.join(timeout=5)
        for queue in (parse_queue, upstream_queue):
            queue.close()
            queue.cancel_join_thread()


@pytest.mark.asyncio
async def test_broken_pipe_is_reported_and_other_queue_is_closed(
    caplog: pytest.LogCaptureFixture,
) -> None:
    spawn = multiprocessing.get_context("spawn")
    parse_queue: Queue[object] = spawn.Queue()
    upstream_queue: Queue[object] = spawn.Queue()
    # Inject a real closed connection, not an exception during item decoding.
    reader = cast(Connection, vars(parse_queue)["_reader"])
    reader.close()
    ctx = cast(
        IPCContext,
        SimpleNamespace(
            shutdown_condition=Condition(),
            parse_job_queue=parse_queue,
            upstream_queue=upstream_queue,
        ),
    )
    try:
        with caplog.at_level(logging.WARNING):
            failure = await shutdown_subprocesses(
                [], ctx, lambda *_: None, ShutdownSentinel()
            )
        assert isinstance(failure, OSError)
        assert "parse_job_queue" in caplog.text
        assert "closed" in caplog.text
        for queue in (parse_queue, upstream_queue):
            with pytest.raises(ValueError, match="closed"):
                queue.get_nowait()
    finally:
        for queue in (parse_queue, upstream_queue):
            queue.close()
            queue.cancel_join_thread()


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", [2, 6])
async def test_closed_queue_is_reported_after_teardown(
    phase: int,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spawn = multiprocessing.get_context("spawn")
    parse_queue: Queue[object] = spawn.Queue()
    upstream_queue: Queue[object] = spawn.Queue()
    original_get = parse_queue.get_nowait
    calls = 0

    def close_before_read() -> object:
        nonlocal calls
        calls += 1
        if calls == (1 if phase == 2 else 2):
            parse_queue.close()
        return original_get()

    monkeypatch.setattr(parse_queue, "get_nowait", close_before_read)
    ctx = cast(
        IPCContext,
        SimpleNamespace(
            shutdown_condition=Condition(),
            parse_job_queue=parse_queue,
            upstream_queue=upstream_queue,
        ),
    )
    try:
        with caplog.at_level(logging.WARNING):
            failure = await shutdown_subprocesses(
                [], ctx, lambda *_: None, ShutdownSentinel()
            )
        assert isinstance(failure, ValueError)
        assert "closed" in str(failure)
        assert "parse_job_queue" in caplog.text
        for queue in (parse_queue, upstream_queue):
            with pytest.raises(ValueError, match="closed"):
                queue.get_nowait()
    finally:
        for queue in (parse_queue, upstream_queue):
            queue.close()
            queue.cancel_join_thread()
