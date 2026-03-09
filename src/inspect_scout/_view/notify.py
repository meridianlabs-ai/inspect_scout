import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator
from urllib.parse import urlparse

import anyio
from fastapi import FastAPI
from inspect_ai._util.vscode import vscode_workspace_id
from inspect_ai._view.notify import view_last_eval_time

from inspect_scout._transcript.eval_log import EvalLogTranscriptsView
from inspect_scout._util.appdirs import scout_data_dir
from inspect_scout._view.invalidationTopics import InvalidationTopic, notify_topics

# lightweight tracking of when the last scan completed
# this enables the scout client to poll for changes frequently
# (e.g. every 1 second) with very minimal overhead.


@asynccontextmanager
async def notify_lifespan(_app: FastAPI) -> AsyncIterator[None]:
    file_times: dict[str, int] = {
        "last_scan": view_last_scan_time(),
        "last_eval": view_last_eval_time(),
    }

    async def notify_worker() -> None:
        while True:
            # sleep between checks
            await anyio.sleep(5)

            # invalidation topics
            invalidations: list[InvalidationTopic] = []

            # clear eval cache if an eval has completed recently
            last_eval_time = view_last_eval_time()
            if last_eval_time > file_times["last_eval"]:
                file_times["last_eval"] = last_eval_time
                EvalLogTranscriptsView.clear_cache()
                invalidations.append("transcripts")

            # clear scan cache if a scan has completed recently
            last_scan_time = view_last_scan_time()
            if last_scan_time > file_times["last_scan"]:
                file_times["last_scan"] = last_scan_time
                invalidations.append("scans")

            if len(invalidations):
                await notify_topics(invalidations)

    async with anyio.create_task_group() as tg:
        tg.start_soon(notify_worker)
        try:
            yield
        finally:
            tg.cancel_scope.cancel()


def view_notify_scan(location: str) -> None:
    # do not do this when running under pytest
    if os.environ.get("PYTEST_VERSION", None) is not None:
        return

    file = view_last_scan_file()
    with open(file, "w", encoding="utf-8") as f:
        if not urlparse(location).scheme:
            location = Path(location).absolute().as_posix()

        # Construct a payload with context for the last eval
        payload = {
            "location": location,
        }
        workspace_id = vscode_workspace_id()
        if workspace_id:
            payload["workspace_id"] = workspace_id

        # Serialize the payload and write it to the signal file
        payload_json = json.dumps(payload, indent=2)
        f.write(payload_json)


def view_last_scan_time() -> int:
    file = view_last_scan_file()
    if file.exists():
        return int(file.stat().st_mtime * 1000)
    else:
        return 0


def view_data_dir() -> Path:
    return scout_data_dir("view")


def view_last_scan_file() -> Path:
    return view_data_dir() / "last-scan"
