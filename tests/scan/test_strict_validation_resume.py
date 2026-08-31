"""Strict validation coverage across a resumed scan.

A resumed scan skips work recorded by the earlier attempt, so the cases those
transcripts matched are only visible in the accumulated scan summary. Strict
coverage has to count them, otherwise resuming a scan would report cases as
unmatched purely because they were validated before the interruption.
"""

from pathlib import Path

import pytest
from inspect_scout import Result, Scanner, ValidationCase, ValidationSet, scanner
from inspect_scout._scan import top_level_sync_init
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.types import Transcript
from inspect_scout.aio import scan_async, scan_resume_async

from tests.helpers import temp_active_scans_store

LOGS_DIR = Path(__file__).parent.parent / "recorder" / "logs"

# transcripts the scanner should fail on, set by the test to make the first
# attempt end with errors (and so leave work for the resumed attempt)
_failing_transcript_ids: set[str] = set()


@scanner(name="failing_once_scanner", messages="all")
def failing_once_scanner() -> Scanner[Transcript]:
    async def scan_transcript(transcript: Transcript) -> Result:
        if transcript.transcript_id in _failing_transcript_ids:
            raise RuntimeError("scanner failed for this transcript")
        return Result(value=True)

    return scan_transcript


@pytest.mark.asyncio
async def test_strict_validation_counts_cases_validated_before_resume(
    tmp_path: Path,
) -> None:
    top_level_sync_init("none")

    transcripts = transcripts_from(LOGS_DIR)
    async with transcripts.reader() as tr:
        transcript_ids = [info.transcript_id async for info in tr.index()][:2]

    validation = ValidationSet(
        cases=[
            ValidationCase(id=transcript_id, target=True)
            for transcript_id in transcript_ids
        ],
        strict=True,
    )

    _failing_transcript_ids.clear()
    _failing_transcript_ids.add(transcript_ids[1])
    with temp_active_scans_store():
        try:
            status = await scan_async(
                scanners=[failing_once_scanner()],
                transcripts=transcripts,
                validation=validation,
                scans=str(tmp_path),
                limit=2,
                max_processes=1,
            )
            assert not status.complete, (
                "scan with a failing scanner should not complete"
            )
            # only the transcript that succeeded was validated
            first_validation = status.summary["failing_once_scanner"].validation
            assert first_validation is not None
            assert [str(entry.id) for entry in first_validation.entries] == [
                transcript_ids[0]
            ]
        finally:
            _failing_transcript_ids.clear()

        # the resumed attempt only re-scans the transcript that failed, so the
        # case validated by the first attempt must come from the scan summary
        status = await scan_resume_async(status.location)

    assert status.complete
    scanner_validation = status.summary["failing_once_scanner"].validation
    assert scanner_validation is not None
    assert sorted(str(entry.id) for entry in scanner_validation.entries) == sorted(
        transcript_ids
    )
