from inspect_scout._transcript.types import TranscriptTooLargeToRecordError
from inspect_scout._util import constants


def test_too_large_to_record_error_carries_context() -> None:
    err = TranscriptTooLargeToRecordError("t1", "input", 2_100_000_001)
    assert err.transcript_id == "t1"
    assert err.cell == "input"
    assert err.size == 2_100_000_001
    assert "2,100,000,001" in str(err) or "2100000001" in str(err)
    assert str(constants.RECORD_CELL_MAX_BYTES) in str(err)
