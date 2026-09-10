"""Local SDK error fixture run in an isolated process by the #616 regressions.

Keep runtime Transcript annotations: Scout's implicit loader uses class identity.
"""

import argparse
import asyncio
import io
import json
import multiprocessing
import os
import signal
from collections.abc import AsyncIterator
from contextlib import ExitStack, asynccontextmanager, redirect_stdout
from multiprocessing.queues import Queue
from pathlib import Path
from typing import Any
from unittest.mock import patch

import anyio
import inspect_scout
import psutil
from anyio.abc import TaskGroup
from inspect_ai._util.error import PrerequisiteError
from inspect_ai.model import ChatMessageUser
from inspect_ai.util import concurrency
from inspect_scout import Result, Scanner, scan, scanner, transcripts_db
from inspect_scout._concurrency import multi_process
from inspect_scout._concurrency._mp_semaphore import MPConcurrencySemaphore
from inspect_scout._concurrency._mp_shutdown import shutdown_subprocesses
from inspect_scout._recorder.recorder import Status
from inspect_scout._scanresults import scan_results_df
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.types import Transcript
from inspect_scout.aio import scan_async

from tests.helpers import temp_active_scans_store


def _raise_provider_error(provider: str) -> None:
    if provider == "generic":
        raise ValueError("generic worker failure fixture")
    if provider == "prerequisite":
        raise PrerequisiteError("prerequisite worker failure fixture")

    import anthropic
    import httpx2
    import openai

    response = httpx2.Response(
        529 if provider == "anthropic" else 429,
        request=httpx2.Request("POST", "https://example.invalid/issue-616"),
        headers={"request-id": "req_scout_616", "x-request-id": "req_scout_616"},
    )
    error_type = (
        anthropic.APIStatusError if provider == "anthropic" else openai.APIStatusError
    )
    raise error_type("scout worker failure fixture", response=response, body=None)


def _error_scanner(provider: str, attempts: Path, mode: str) -> Scanner[Transcript]:
    @scanner(name="worker_error_616", messages="all")
    def factory() -> Scanner[Transcript]:
        async def scan_transcript(transcript: Transcript) -> Result:
            (attempts / f"{transcript.transcript_id}.json").write_text(
                json.dumps(
                    {
                        "pid": os.getpid(),
                        "start_method": multiprocessing.get_start_method(),
                        "transcript_id": transcript.transcript_id,
                    }
                )
            )
            if mode in ("cancel", "interrupt"):
                await anyio.sleep_forever()
            if mode in ("multiple", "pressure"):
                with anyio.fail_after(20):
                    while len(list(attempts.glob("*.json"))) < 2:
                        await anyio.sleep(0.02)
                raise RuntimeError(
                    f"simultaneous worker failure: {transcript.transcript_id}"
                )
            if transcript.transcript_id == "failing" and mode not in (
                "cleanup",
                "keyboard_cleanup",
                "collector",
            ):
                _raise_provider_error(provider)
            return Result(value="ok")

        return scan_transcript

    return factory()


def run_scenario(
    root: Path,
    provider: str,
    fail_on_error: bool,
    max_processes: int,
    api: str,
    mode: str = "normal",
) -> None:
    attempts = root / "attempts"
    attempts.mkdir()
    db_path = root / "db"

    async def insert() -> None:
        async with transcripts_db(str(db_path)) as db:
            await db.insert(
                [
                    Transcript(
                        transcript_id=transcript_id,
                        source_type="test",
                        source_id="issue-616",
                        source_uri=f"test://{transcript_id}",
                        messages=[ChatMessageUser(content="local fixture")],
                        events=[],
                    )
                    for transcript_id in (
                        ["failing", "successful"]
                        + (
                            [f"queued-{i}" for i in range(100)]
                            if mode == "pressure"
                            else []
                        )
                    )
                ]
            )

    asyncio.run(insert())
    parent_output = io.StringIO()
    original_sigint = signal.getsignal(signal.SIGINT)
    completed_status: Status | None = None
    native_interrupt = False

    async def run_async() -> Status:
        async def capture_scan() -> Status:
            nonlocal completed_status
            completed_status = await scan_async(
                scanners=[_error_scanner(provider, attempts, mode)],
                transcripts=transcripts_from(str(db_path)),
                scans=str(root / "scans"),
                model="mockllm/model",
                max_processes=max_processes,
                max_transcripts=2,
                fail_on_error=fail_on_error,
            )
            return completed_status

        task = asyncio.create_task(capture_scan())
        if mode in ("cancel", "interrupt"):
            with anyio.fail_after(20):
                while len(list(attempts.glob("*.json"))) < 2:
                    await anyio.sleep(0.02)
            if mode == "interrupt":
                os.kill(os.getpid(), signal.SIGINT)
            else:
                task.cancel()
        return await task

    with (
        temp_active_scans_store(),
        redirect_stdout(parent_output),
        ExitStack() as stack,
    ):
        if mode == "pressure":
            stack.enter_context(
                patch.object(multi_process, "PARSE_JOB_PREFETCH_SIZE", 1)
            )
            stack.enter_context(
                patch.object(multi_process, "UPSTREAM_QUEUE_MAXSIZE", 1)
            )

        if mode in (
            "cleanup",
            "primary_cleanup",
            "cancel",
            "interrupt",
            "keyboard_cleanup",
        ):

            async def secondary_failure(*args: Any, **kwargs: Any) -> Exception | None:
                failure = await shutdown_subprocesses(*args, **kwargs)
                return failure or OSError("cleanup failure fixture")

            stack.enter_context(
                patch.object(multi_process, "shutdown_subprocesses", secondary_failure)
            )

        if mode == "keyboard_cleanup":

            @asynccontextmanager
            async def interrupted_group() -> AsyncIterator[TaskGroup]:
                async with anyio.create_task_group() as group:
                    yield group
                raise KeyboardInterrupt()

            stack.enter_context(
                patch.object(multi_process, "create_task_group", interrupted_group)
            )

        if mode == "collector":
            original_get = Queue.get

            def broken_get(
                queue: "Queue[Any]", block: bool = True, timeout: float | None = None
            ) -> Any:
                if block:
                    raise OSError("collector read failure fixture")
                return original_get(queue, block, timeout)

            stack.enter_context(patch.object(Queue, "get", broken_get))

        if api == "sync":
            status = scan(
                scanners=[_error_scanner(provider, attempts, mode)],
                transcripts=transcripts_from(str(db_path)),
                scans=str(root / "scans"),
                model="mockllm/model",
                max_processes=max_processes,
                max_transcripts=2,
                fail_on_error=fail_on_error,
                display="plain",
            )
        else:
            try:
                status = asyncio.run(run_async())
            except KeyboardInterrupt:
                # Python 3.10's runner raises SIGINT directly, then cancels and
                # awaits its remaining tasks. Audit their completed cleanup
                # before preserving the native interrupt exit below.
                if completed_status is None:
                    raise
                status = completed_status
                native_interrupt = True

    async def registry_restored() -> bool:
        async with concurrency("after-worker-error", 1) as semaphore:
            return not isinstance(semaphore, MPConcurrencySemaphore)

    attempted = [
        json.loads(path.read_text()) for path in sorted(attempts.glob("*.json"))
    ]
    workers = []
    for pid in {attempt["pid"] for attempt in attempted} - {os.getpid()}:
        try:
            workers.append(psutil.Process(pid))
        except psutil.NoSuchProcess:
            pass
    _, alive = psutil.wait_procs(workers, timeout=5)

    # Read the persisted status as well as the return value. Fatal exceptions
    # belong to the interruption display; Status.errors contains job errors.
    results = scan_results_df(status.location)
    frame = results.scanners.get("worker_error_616")
    report = {
        "native_interrupt": native_interrupt,
        "scout_source": inspect_scout.__file__,
        "api": api,
        "parent_pid": os.getpid(),
        "complete": status.complete,
        "persisted_complete": results.complete,
        "errors": [error.model_dump() for error in results.errors],
        "values": frame["value"].dropna().tolist() if frame is not None else [],
        "attempts": attempted,
        "worker_pids_still_alive": [worker.pid for worker in alive],
        "registry_restored": asyncio.run(registry_restored()),
        "sigint_restored": signal.getsignal(signal.SIGINT) == original_sigint,
        "strategy_active": multi_process._active,
        "parent_display": parent_output.getvalue(),
    }
    (root / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    if native_interrupt:
        raise KeyboardInterrupt()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument(
        "--provider",
        choices=("anthropic", "openai", "generic", "prerequisite"),
        required=True,
    )
    parser.add_argument("--fail-on-error", action="store_true")
    parser.add_argument("--max-processes", type=int, required=True)
    parser.add_argument("--api", choices=("sync", "async"), default="async")
    parser.add_argument("--mode", default="normal")
    args = parser.parse_args()
    run_scenario(
        args.root,
        args.provider,
        args.fail_on_error,
        args.max_processes,
        args.api,
        args.mode,
    )
