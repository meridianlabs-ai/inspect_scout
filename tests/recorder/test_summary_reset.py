"""Tests that summary resets on new scan init but preserves on resume."""

from pathlib import Path

from inspect_scout._recorder.buffer import RecorderBuffer
from inspect_scout._recorder.summary import Summary
from inspect_scout._scanspec import ScanSpec, ScannerSpec


def _make_spec(scanners: list[str]) -> ScanSpec:
    """Create a minimal ScanSpec for testing."""
    return ScanSpec(
        scan_name="test",
        scanners={s: ScannerSpec(name=s) for s in scanners},
    )


class TestSummaryResetOnInit:
    """Summary should reset on init, not accumulate across runs."""

    def test_new_init_resets_summary(self, tmp_path: Path) -> None:
        """Creating a new RecorderBuffer with reset=True should start fresh."""
        import os

        os.environ["SCOUT_SCANBUFFER_DIR"] = str(tmp_path)
        try:
            spec = _make_spec(["s"])
            buf1 = RecorderBuffer("test_location", spec, reset=True)
            assert buf1._scan_summary.scanners["s"].scans == 0

            # Simulate recording by writing summary with counts
            buf1._scan_summary.scanners["s"].scans = 10
            buf1._scan_summary.scanners["s"].results = 50
            summary_path = buf1._buffer_dir / "_summary.json"
            with open(str(summary_path), "w") as f:
                f.write(buf1._scan_summary.model_dump_json(indent=2))

            # Second run with reset=True: should start fresh
            buf2 = RecorderBuffer("test_location", spec, reset=True)
            assert buf2._scan_summary.scanners["s"].scans == 0
            assert buf2._scan_summary.scanners["s"].results == 0
        finally:
            del os.environ["SCOUT_SCANBUFFER_DIR"]

    def test_resume_preserves_summary(self, tmp_path: Path) -> None:
        """Creating a RecorderBuffer with reset=False should load existing summary."""
        import os

        os.environ["SCOUT_SCANBUFFER_DIR"] = str(tmp_path)
        try:
            spec = _make_spec(["s"])
            buf1 = RecorderBuffer("test_location", spec, reset=True)
            buf1._scan_summary.scanners["s"].scans = 10
            buf1._scan_summary.scanners["s"].results = 50
            summary_path = buf1._buffer_dir / "_summary.json"
            with open(str(summary_path), "w") as f:
                f.write(buf1._scan_summary.model_dump_json(indent=2))

            # Resume (reset=False): should load existing counts
            buf2 = RecorderBuffer("test_location", spec, reset=False)
            assert buf2._scan_summary.scanners["s"].scans == 10
            assert buf2._scan_summary.scanners["s"].results == 50
        finally:
            del os.environ["SCOUT_SCANBUFFER_DIR"]
