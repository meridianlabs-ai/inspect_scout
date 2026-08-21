"""Degrade-to-reference behavior of the record path."""

from __future__ import annotations

import pytest
from inspect_ai._util.error import PrerequisiteError
from inspect_scout import scanner
from inspect_scout._concurrency.common import ScannerJob
from inspect_scout._scan import _scan_one
from inspect_scout._scanner.result import ReferenceTranscript, Result
from inspect_scout._scanner.scanner import Scanner, mark_streaming_support
from inspect_scout._transcript.handle import MaterializedTranscriptHandle
from inspect_scout._transcript.types import (
    Transcript,
    TranscriptContent,
    TranscriptInfo,
)


@scanner(messages="all", events="all")
def _streaming_scanner() -> Scanner[Transcript]:
    async def scan(transcript: Transcript) -> Result:
        return Result(value="ok")

    mark_streaming_support(scan, True)
    return scan


def _failing_handle(
    error: Exception, content: TranscriptContent
) -> MaterializedTranscriptHandle:
    info = TranscriptInfo(transcript_id="t1", source_uri="file:///log.eval")

    async def failing_load() -> Transcript:
        raise error

    return MaterializedTranscriptHandle(failing_load, info, content)


@pytest.mark.asyncio
async def test_record_failure_degrades_to_reference() -> None:
    content = TranscriptContent(messages="all", events=None, timeline=None)
    handle = _failing_handle(RuntimeError("boom"), content)
    job = ScannerJob(
        union_transcript=handle, scanner=_streaming_scanner(), scanner_name="s"
    )
    reports = await _scan_one(job, validation=None, fail_on_error=False)
    assert len(reports) == 1
    report_input = reports[0].input
    assert isinstance(report_input, ReferenceTranscript)
    assert report_input.transcript_id == "t1"
    assert report_input.source_uri == "file:///log.eval"
    assert report_input.content_json == content.to_json()
    # The scan's value is kept; the read failure is surfaced as the row error.
    assert reports[0].result is not None
    assert reports[0].error is not None


@pytest.mark.parametrize(
    ("error", "fail_on_error"),
    [
        pytest.param(RuntimeError("boom"), True, id="fail_on_error"),
        pytest.param(PrerequisiteError("boom"), False, id="prerequisite"),
    ],
)
@pytest.mark.asyncio
async def test_record_failure_raises(error: Exception, fail_on_error: bool) -> None:
    handle = _failing_handle(error, TranscriptContent(None, None, None))
    job = ScannerJob(
        union_transcript=handle, scanner=_streaming_scanner(), scanner_name="s"
    )
    with pytest.raises(type(error)):
        await _scan_one(job, validation=None, fail_on_error=fail_on_error)
