"""Tests for eval log sample reading in eval_log.py."""

from pathlib import Path

from inspect_scout._transcript.eval_log import _read_samples

LOGS_DIR = Path(__file__).parent.parent / "recorder" / "logs"
LOG_1 = LOGS_DIR / "2025-09-23T08-09-58-04-00_popularity_DN2wbX2ZvACsBpjwptzBRo.eval"


def test_read_samples_sets_transcript_id() -> None:
    """The samples frame carries transcript_id derived from sample_id."""
    df = _read_samples([LOG_1.as_posix()])
    assert not df.empty
    assert df["transcript_id"].tolist() == df["sample_id"].tolist()
