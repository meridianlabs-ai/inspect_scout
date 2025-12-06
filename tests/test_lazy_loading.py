"""Tests for lazy loading behavior of ScanResultsDF."""

import tempfile
from collections.abc import Mapping
from pathlib import Path

import pandas as pd
from inspect_ai.model import ModelOutput
from inspect_scout import Result, Scanner, scan, scanner
from inspect_scout._recorder.file import LazyScannerMapping
from inspect_scout._scanresults import scan_results_df
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.types import Transcript

# Test data location
LOGS_DIR = Path(__file__).parent.parent / "examples" / "scanner" / "logs"


def test_lazy_scanner_mapping_defers_loading() -> None:
    """Verify that LazyScannerMapping doesn't load until access."""
    load_count = 0

    def tracking_loader(name: str) -> pd.DataFrame:
        nonlocal load_count
        load_count += 1
        return pd.DataFrame({"col": [1, 2, 3]})

    # Create mapping - should NOT load anything
    mapping = LazyScannerMapping(
        scanner_names=["scanner_a", "scanner_b"],
        loader=tracking_loader,
    )
    assert load_count == 0, "Loader called during construction"

    # Iterate keys - should NOT load
    _ = list(mapping.keys())
    assert load_count == 0, "Loader called during keys()"

    # Check length - should NOT load
    _ = len(mapping)
    assert load_count == 0, "Loader called during len()"

    # Check containment - should NOT load
    _ = "scanner_a" in mapping
    assert load_count == 0, "Loader called during 'in' check"

    # Access a key - NOW it should load
    _ = mapping["scanner_a"]
    assert load_count == 1, "Loader not called on access"

    # Access again - should load again (no caching)
    _ = mapping["scanner_a"]
    assert load_count == 2, "Loader should be called again (no caching)"


@scanner(name="lazy_test_scanner", messages="all")
def lazy_test_scanner_factory() -> Scanner[Transcript]:
    """Simple scanner for testing lazy loading."""

    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(
            value=True,
            explanation=f"Scanned {transcript.transcript_id[:8]}",
        )

    return scan_transcript


def test_lazy_loading_scanners() -> None:
    """Verify that scanners uses lazy loading via LazyScannerMapping."""
    mock_responses = [
        ModelOutput.from_content(model="mockllm", content="Test response"),
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[lazy_test_scanner_factory()],
            transcripts=transcripts_from(LOGS_DIR),
            results=tmpdir,
            limit=2,
            max_processes=1,
            model="mockllm/model",
            model_args={"custom_outputs": mock_responses},
        )

        results = scan_results_df(status.location)

        # Verify it's a Mapping (not dict) using LazyScannerMapping
        assert isinstance(results.scanners, Mapping)
        assert isinstance(results.scanners, LazyScannerMapping)
        assert not isinstance(results.scanners, dict)

        # Verify iteration/keys work without loading DataFrames
        assert len(results.scanners) == 1
        assert list(results.scanners.keys()) == ["lazy_test_scanner"]
        assert "lazy_test_scanner" in results.scanners

        # Verify accessing returns a proper DataFrame
        df = results.scanners["lazy_test_scanner"]
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "value" in df.columns
