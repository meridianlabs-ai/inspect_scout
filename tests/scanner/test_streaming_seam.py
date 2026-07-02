"""Tests for the streaming scanner seam: input plumbing and dispatch."""

from pathlib import Path

import pytest
from inspect_scout import scanner
from inspect_scout._concurrency.common import ScannerJob
from inspect_scout._scan import _scan_one
from inspect_scout._scanner.result import Result, _serialize_input
from inspect_scout._scanner.scanner import SCANNER_ACCEPTS_HANDLE_ATTR
from inspect_scout._scanner.util import get_input_type_and_ids
from inspect_scout._transcript.handle import MaterializedTranscriptHandle
from inspect_scout._transcript.types import Transcript, TranscriptInfo


def test_input_type_for_transcript_info() -> None:
    info = TranscriptInfo(transcript_id="t1")
    assert get_input_type_and_ids(info) == ("transcript_handle", ["t1"])


def test_serialize_input_info_only() -> None:
    info = TranscriptInfo(transcript_id="t1", source_id="e1")
    input_json, input_data = _serialize_input(
        info, "transcript_handle", pool_dedup=True
    )
    assert input_data is None
    assert '"transcript_id":"t1"' in input_json.replace(" ", "")
    assert "messages" not in input_json  # no content fields serialized


@scanner(messages="all", events="all")
def _handle_scanner() -> "object":  # type: ignore[no-untyped-def]
    async def scan(transcript: Transcript) -> Result:
        return Result(value="ok")

    setattr(scan, SCANNER_ACCEPTS_HANDLE_ATTR, True)
    return scan


@scanner(messages="all", events="all")
def _plain_scanner() -> "object":  # type: ignore[no-untyped-def]
    async def scan(transcript: Transcript) -> Result:
        return Result(value="ok")

    return scan


@pytest.mark.asyncio
async def test_scan_one_with_handle_scanner(tmp_path: Path) -> None:
    """A handle-accepting scanner receives the handle and results record info-only."""
    info = TranscriptInfo(transcript_id="t1")
    transcript = Transcript(transcript_id="t1", messages=[], events=[], metadata={})

    async def load_fn() -> Transcript:
        return transcript

    handle = MaterializedTranscriptHandle(load_fn, info)

    s = _handle_scanner()
    job = ScannerJob(union_transcript=handle, scanner=s, scanner_name="hs")
    reports = await _scan_one(job, validation=None, fail_on_error=True)
    assert len(reports) == 1
    assert reports[0].input_type == "transcript_handle"
    assert reports[0].input == info  # info only, no content


@pytest.mark.asyncio
async def test_scan_one_stream_error_contained(tmp_path: Path) -> None:
    """Errors raised during handle iteration produce an Error report, not a crash."""
    info = TranscriptInfo(transcript_id="t1")

    async def failing_load() -> Transcript:
        raise ValueError("corrupt sample JSON")

    handle = MaterializedTranscriptHandle(failing_load, info)

    s = _plain_scanner()
    job = ScannerJob(union_transcript=handle, scanner=s, scanner_name="ps")
    reports = await _scan_one(job, validation=None, fail_on_error=False)
    assert len(reports) == 1
    assert reports[0].error is not None
    assert "corrupt sample JSON" in reports[0].error.error


@pytest.mark.asyncio
async def test_scan_one_on_complete_awaited_once_per_job(tmp_path: Path) -> None:
    """The shared handle is closed exactly once, after the last (lead + follower) job.

    Simulates the completion counter created by `_parse_function`: a lead with
    one follower, each `ScannerJob` carrying the same `on_complete` closure.
    Running `_scan_one` on the lead then the follower must decrement to zero
    and close the handle exactly once.
    """
    info = TranscriptInfo(transcript_id="t1")
    transcript = Transcript(transcript_id="t1", messages=[], events=[], metadata={})

    close_count = 0

    class SpyHandle(MaterializedTranscriptHandle):
        async def aclose(self) -> None:
            nonlocal close_count
            close_count += 1
            await super().aclose()

    async def load_fn() -> Transcript:
        return transcript

    handle = SpyHandle(load_fn, info)

    # Mirror _parse_function's completion counter: 1 lead + 1 follower.
    remaining = 2

    async def on_job_complete() -> None:
        nonlocal remaining
        remaining -= 1
        if remaining == 0:
            await handle.aclose()

    lead = ScannerJob(
        union_transcript=handle,
        scanner=_handle_scanner(),
        scanner_name="lead",
        on_complete=on_job_complete,
    )
    follower = ScannerJob(
        union_transcript=handle,
        scanner=_handle_scanner(),
        scanner_name="follower",
        on_complete=on_job_complete,
    )

    await _scan_one(lead, validation=None, fail_on_error=True)
    assert close_count == 0  # lead done, follower still pending

    await _scan_one(follower, validation=None, fail_on_error=True)
    assert remaining == 0
    assert close_count == 1  # closed exactly once after the last job
