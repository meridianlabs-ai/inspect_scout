"""Tests that summary resets on new scan init but preserves on resume."""

from pathlib import Path

import pytest

from inspect_scout._recorder.buffer import RecorderBuffer
from inspect_scout._scanspec import ScanSpec, ScannerSpec


def _make_spec(scanners: list[str]) -> ScanSpec:
    """Create a minimal ScanSpec for testing."""
    return ScanSpec(
        scan_name="test",
        scanners={s: ScannerSpec(name=s) for s in scanners},
    )


def _persist_summary(buf: RecorderBuffer) -> None:
    """Write the buffer's in-memory summary to disk."""
    summary_path = buf._buffer_dir / "_summary.json"
    with open(str(summary_path), "w") as f:
        f.write(buf._scan_summary.model_dump_json(indent=2))


class TestSummaryResetOnInit:
    """Summary should reset on init, not accumulate across runs."""

    def test_new_init_resets_summary(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Creating a new RecorderBuffer with reset=True should start fresh."""
        monkeypatch.setenv("SCOUT_SCANBUFFER_DIR", str(tmp_path))
        spec = _make_spec(["s"])
        buf1 = RecorderBuffer("test_location", spec, reset=True)
        assert buf1.scan_summary().scanners["s"].scans == 0

        buf1._scan_summary.scanners["s"].scans = 10
        buf1._scan_summary.scanners["s"].results = 50
        _persist_summary(buf1)

        # Second run with reset=True: should start fresh
        buf2 = RecorderBuffer("test_location", spec, reset=True)
        assert buf2.scan_summary().scanners["s"].scans == 0
        assert buf2.scan_summary().scanners["s"].results == 0

    def test_resume_preserves_summary(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Creating a RecorderBuffer with reset=False should load existing summary."""
        monkeypatch.setenv("SCOUT_SCANBUFFER_DIR", str(tmp_path))
        spec = _make_spec(["s"])
        buf1 = RecorderBuffer("test_location", spec, reset=True)
        buf1._scan_summary.scanners["s"].scans = 10
        buf1._scan_summary.scanners["s"].results = 50
        _persist_summary(buf1)

        # Resume (reset=False): should load existing counts
        buf2 = RecorderBuffer("test_location", spec, reset=False)
        assert buf2.scan_summary().scanners["s"].scans == 10
        assert buf2.scan_summary().scanners["s"].results == 50

    def test_reset_truncates_errors(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """reset=True should truncate the error file."""
        monkeypatch.setenv("SCOUT_SCANBUFFER_DIR", str(tmp_path))
        spec = _make_spec(["s"])
        buf1 = RecorderBuffer("test_location", spec, reset=True)

        # Write a fake error
        with open(str(buf1._error_file), "w") as f:
            f.write('{"error": "test"}\n')

        # reset=True should truncate
        buf2 = RecorderBuffer("test_location", spec, reset=True)
        assert buf2._error_file.read_text() == ""

    def test_resume_preserves_errors(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """reset=False should preserve the error file."""
        monkeypatch.setenv("SCOUT_SCANBUFFER_DIR", str(tmp_path))
        spec = _make_spec(["s"])
        buf1 = RecorderBuffer("test_location", spec, reset=True)

        error_content = '{"error": "test"}\n'
        with open(str(buf1._error_file), "w") as f:
            f.write(error_content)

        # resume (reset=False): should preserve errors
        buf2 = RecorderBuffer("test_location", spec, reset=False)
        assert buf2._error_file.read_text() == error_content
