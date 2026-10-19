import tempfile
from pathlib import Path

import pandas as pd
import pytest
from inspect_ai.model._chat_message import ChatMessage, ChatMessageUser
from inspect_scout import (
    Result,
    Scanner,
    ValidationCase,
    ValidationSet,
    scan,
    scanner,
    transcripts_db,
)
from inspect_scout._scanresults import scan_results_df
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.types import Transcript


def create_two_message_transcript(transcript_id: str) -> Transcript:
    """A transcript with two messages: one that validates, one that errors."""
    return Transcript(
        transcript_id=transcript_id,
        source_type="test",
        source_id="source-0",
        source_uri="test://uri/0",
        messages=[
            ChatMessageUser(id="msg-ok", content="Test message 0"),
            ChatMessageUser(id="msg-error", content="Test message 1"),
        ],
        events=[],
    )


@scanner(name="attribution_scanner", messages="all")
def attribution_scanner_factory() -> Scanner[ChatMessage]:
    """Scanner that validates cleanly on the first message and raises on the second."""

    async def scan_message(message: ChatMessage) -> Result:
        if message.id == "msg-error":
            raise RuntimeError("boom")
        return Result(value=True)

    return scan_message


@pytest.mark.asyncio
async def test_error_item_does_not_inherit_previous_validation() -> None:
    """An item that errors must not report the previous item's validation.

    `validation_result` was bound outside the loop (only reassigned on a
    successful scan), so a raise on item 2 left item 1's validation result in
    place for the recorded Error row.
    """
    transcript = create_two_message_transcript("attribution")
    validation = ValidationSet(cases=[ValidationCase(id="msg-ok", target=True)])

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "transcripts_db"
        scans_path = Path(tmpdir) / "scans"

        async with transcripts_db(str(db_path)) as db:
            await db.insert([transcript])

        status = scan(
            scanners=[attribution_scanner_factory()],
            transcripts=transcripts_from(str(db_path)),
            scans=str(scans_path),
            validation={"attribution_scanner": validation},
            max_processes=1,
            display="none",
        )

        assert status.location is not None

        results = scan_results_df(status.location, scanner="attribution_scanner")
        rows = results.scanners["attribution_scanner"]

        error_row = rows[rows["scan_error"].notna()].iloc[0]
        ok_row = rows[rows["scan_error"].isna()].iloc[0]
        assert pd.isna(error_row["validation_result"])
        assert not pd.isna(ok_row["validation_result"])
