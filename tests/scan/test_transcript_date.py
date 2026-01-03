"""Tests for transcript_date column in scan results."""

from pathlib import Path

import pytest
from inspect_ai.model import ModelOutput
from inspect_scout import (
    Result,
    Scanner,
    scan,
    scanner,
    transcripts_db,
    transcripts_from,
)
from inspect_scout._scanresults import scan_results_df
from inspect_scout._transcript.types import Transcript

# Test data location
TEST_LOGS_DIR = Path(__file__).parent.parent / "recorder" / "logs"


@scanner(name="simple_date_test_scanner", messages="all")
def simple_scanner_factory() -> Scanner[Transcript]:
    """Scanner that returns simple values for testing."""

    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(
            value=True,
            explanation=f"Scanned transcript {transcript.transcript_id[:8]}",
        )

    return scan_transcript


@pytest.mark.asyncio
async def test_transcript_date_in_results(tmp_path: Path) -> None:
    """Test that transcript_date column is populated in scan results.

    This test verifies:
    1. Transcript database created from eval logs has a 'date' column populated
    2. Scan results database has a 'transcript_date' column populated
    """
    # Step 1: Create transcript database from eval logs
    db_location = tmp_path / "transcript_db"
    db_location.mkdir(parents=True, exist_ok=True)

    async with transcripts_db(str(db_location)) as db:
        await db.insert(transcripts_from(str(TEST_LOGS_DIR)))

    # Step 2: Verify transcript db has 'date' column populated
    transcripts = transcripts_from(str(db_location))
    dates_found: list[str | None] = []

    async with transcripts.reader() as reader:
        async for info in reader.index():
            dates_found.append(info.date)

    # Verify we have transcripts and at least some have dates
    assert len(dates_found) > 0, "Should have transcripts in the database"
    non_null_dates = [d for d in dates_found if d is not None]
    assert len(non_null_dates) > 0, (
        "At least some transcripts should have dates populated"
    )

    # Step 3: Run a scan on the transcript database
    mock_responses = [
        ModelOutput.from_content(
            model="mockllm",
            content="Test response.\n\nANSWER: yes",
        )
        for _ in range(len(dates_found))
    ]

    results_location = tmp_path / "scan_results"

    status = scan(
        scanners=[simple_scanner_factory()],
        transcripts=transcripts,
        results=str(results_location),
        max_processes=1,
        model="mockllm/model",
        model_args={"custom_outputs": mock_responses},
    )

    assert status.complete, "Scan should complete successfully"
    assert status.location is not None, "Scan should have a results location"

    # Step 4: Verify results database has 'transcript_date' column
    results = scan_results_df(status.location, scanner="simple_date_test_scanner")
    scanner_df = results.scanners["simple_date_test_scanner"]

    # Check that transcript_date column exists
    assert "transcript_date" in scanner_df.columns, (
        "Results should have 'transcript_date' column"
    )

    # Check that transcript_date has values (at least some non-null)
    transcript_dates = scanner_df["transcript_date"].tolist()
    non_null_result_dates = [d for d in transcript_dates if d is not None]
    assert len(non_null_result_dates) > 0, (
        "At least some results should have transcript_date populated"
    )
