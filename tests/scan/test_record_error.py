"""A result that can't be recorded is an error for its transcript, not the scan."""

import asyncio
from pathlib import Path

import pytest
from inspect_ai.model._chat_message import ChatMessageUser
from inspect_scout import Result, Scanner, scan, scan_resume, scanner, transcripts_db
from inspect_scout._scanresults import scan_results_df
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.types import Transcript

from tests.helpers import temp_active_scans_store

UNRECORDABLE_ID = "transcript-1"


@scanner(name="int_value_scanner", messages="all")
def int_value_scanner() -> Scanner[Transcript]:
    async def scan_transcript(transcript: Transcript) -> Result:
        # Arrow's int64 can't hold 2**63, so recording this result raises
        return Result(value=2**63 if transcript.transcript_id == UNRECORDABLE_ID else 1)

    return scan_transcript


@pytest.fixture
def transcripts_dir(tmp_path: Path) -> str:
    db_path = tmp_path / "transcripts"
    db_path.mkdir()

    async def insert() -> None:
        async with transcripts_db(str(db_path)) as db:
            await db.insert(
                [
                    Transcript(
                        transcript_id=f"transcript-{i}",
                        source_type="test",
                        source_id="source",
                        source_uri=f"test://uri/{i}",
                        messages=[ChatMessageUser(content=f"message {i}")],
                        events=[],
                    )
                    for i in range(3)
                ]
            )

    asyncio.run(insert())
    return str(db_path)


def test_unrecordable_result_is_error_and_scan_continues(
    tmp_path: Path, transcripts_dir: str
) -> None:
    with temp_active_scans_store():
        status = scan(
            scanners=[int_value_scanner()],
            transcripts=transcripts_from(transcripts_dir),
            scans=str(tmp_path / "scans"),
            max_processes=1,
            display="none",
        )

        assert not status.complete
        assert [(e.transcript_id, e.scanner) for e in status.errors] == [
            (UNRECORDABLE_ID, "int_value_scanner")
        ]
        assert "too large" in status.errors[0].error
        assert "OverflowError" in status.errors[0].traceback
        summary = status.summary["int_value_scanner"]
        assert (summary.scans, summary.errors) == (3, 1)
        results = scan_results_df(status.location).scanners["int_value_scanner"]
        assert sorted(results["transcript_id"]) == ["transcript-0", "transcript-2"]

        # errors are cleared on resume, so the error recurring shows that the
        # unrecorded transcript was scanned again
        resumed = scan_resume(status.location, display="none")
        assert [e.transcript_id for e in resumed.errors] == [UNRECORDABLE_ID]


def test_unrecordable_result_with_fail_on_error_stops_scan(
    tmp_path: Path, transcripts_dir: str
) -> None:
    with temp_active_scans_store():
        status = scan(
            scanners=[int_value_scanner()],
            transcripts=transcripts_from(transcripts_dir),
            scans=str(tmp_path / "scans"),
            max_processes=1,
            display="none",
            fail_on_error=True,
        )

    # the failure interrupts the scan rather than being recorded as an error
    assert not status.complete
    assert status.errors == []
