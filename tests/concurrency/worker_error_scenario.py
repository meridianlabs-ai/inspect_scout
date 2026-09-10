"""Local SDK error fixture run in an isolated process by the #616 regressions.

Keep runtime Transcript annotations: Scout's implicit loader uses class identity.
"""

import argparse
import asyncio
import io
import json
import multiprocessing
import os
from contextlib import redirect_stdout
from pathlib import Path

from inspect_ai.model import ChatMessageUser
from inspect_scout import Result, Scanner, scan, scanner, transcripts_db
from inspect_scout._scanresults import scan_results_df
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.types import Transcript
from inspect_scout.aio import scan_async

from tests.helpers import temp_active_scans_store


def _raise_provider_error(provider: str) -> None:
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


def _error_scanner(provider: str, attempts: Path) -> Scanner[Transcript]:
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
            if transcript.transcript_id == "failing":
                _raise_provider_error(provider)
            return Result(value="ok")

        return scan_transcript

    return factory()


def run_scenario(
    root: Path, provider: str, fail_on_error: bool, max_processes: int, api: str
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
                    for transcript_id in ("failing", "successful")
                ]
            )

    asyncio.run(insert())
    parent_output = io.StringIO()
    with temp_active_scans_store(), redirect_stdout(parent_output):
        if api == "sync":
            status = scan(
                scanners=[_error_scanner(provider, attempts)],
                transcripts=transcripts_from(str(db_path)),
                scans=str(root / "scans"),
                model="mockllm/model",
                max_processes=max_processes,
                max_transcripts=2,
                fail_on_error=fail_on_error,
                display="plain",
            )
        else:
            status = asyncio.run(
                scan_async(
                    scanners=[_error_scanner(provider, attempts)],
                    transcripts=transcripts_from(str(db_path)),
                    scans=str(root / "scans"),
                    model="mockllm/model",
                    max_processes=max_processes,
                    max_transcripts=2,
                    fail_on_error=fail_on_error,
                )
            )

    # Read the persisted status as well as the return value. Fatal exceptions
    # belong to the interruption display; Status.errors contains job errors.
    results = scan_results_df(status.location)
    frame = results.scanners.get("worker_error_616")
    report = {
        "api": api,
        "parent_pid": os.getpid(),
        "complete": status.complete,
        "persisted_complete": results.complete,
        "errors": [error.model_dump() for error in results.errors],
        "values": frame["value"].dropna().tolist() if frame is not None else [],
        "attempts": [
            json.loads(path.read_text()) for path in sorted(attempts.glob("*.json"))
        ],
        "parent_display": parent_output.getvalue(),
    }
    (root / "report.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--provider", choices=("anthropic", "openai"), required=True)
    parser.add_argument("--fail-on-error", action="store_true")
    parser.add_argument("--max-processes", type=int, required=True)
    parser.add_argument("--api", choices=("sync", "async"), default="async")
    args = parser.parse_args()
    run_scenario(
        args.root, args.provider, args.fail_on_error, args.max_processes, args.api
    )
