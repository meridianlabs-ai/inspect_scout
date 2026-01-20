"""Tests for ScanJob.from_config."""

from inspect_scout._scanjob import ScanJob
from inspect_scout._scanjob_config import ScanJobConfig


def test_from_config_with_none_transcripts() -> None:
    """ScanJob.from_config should handle None transcripts without UnboundLocalError."""
    config = ScanJobConfig(
        scanners={},
        transcripts=None,
    )
    job = ScanJob.from_config(config)
    assert job.transcripts is None
