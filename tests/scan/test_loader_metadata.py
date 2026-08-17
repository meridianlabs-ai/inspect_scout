"""Tests for surfacing loader-item metadata on scan result rows."""

import json
import tempfile
from pathlib import Path
from typing import Any, AsyncIterator

from inspect_scout import Result, Scanner, loader, scan, scanner
from inspect_scout._scanner.loader import Loader
from inspect_scout._scanresults import scan_results_df
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.types import Transcript

LOGS_DIR = Path(__file__).parent.parent.parent / "examples" / "scanner" / "logs"

# pin the scanned transcript to one with non-empty source metadata so the
# no-leak assertion below cannot pass vacuously
POPULARITY_LOG = (
    LOGS_DIR / "2025-09-23T08-09-58-04-00_popularity_DN2wbX2ZvACsBpjwptzBRo.eval"
)


@loader(name="item_metadata_loader", messages="all")
def item_metadata_loader_factory() -> Loader[Transcript]:
    """Loader that yields synthetic per-item transcripts with item metadata."""

    async def load(transcript: Transcript) -> AsyncIterator[Transcript]:
        for i in range(2):
            yield transcript.model_copy(
                update={"metadata": {"provenance": f"item-{i}", "shared": "loader"}}
            )

    return load


@scanner(name="merged_metadata_scanner", loader=item_metadata_loader_factory())
def merged_metadata_scanner_factory() -> Scanner[Transcript]:
    """Scanner that authors metadata overlapping the loader item metadata."""

    async def scan_item(transcript: Transcript) -> Result:
        return Result(value=True, metadata={"shared": "scanner", "scanner_only": 1})

    return scan_item


@scanner(name="loader_only_metadata_scanner", loader=item_metadata_loader_factory())
def loader_only_metadata_scanner_factory() -> Scanner[Transcript]:
    """Scanner that authors no metadata of its own."""

    async def scan_item(transcript: Transcript) -> Result:
        return Result(value=True)

    return scan_item


@scanner(name="resultset_metadata_scanner", loader=item_metadata_loader_factory())
def resultset_metadata_scanner_factory() -> Scanner[Transcript]:
    """Scanner that returns a list of results (recorded as a resultset)."""

    async def scan_item(transcript: Transcript) -> list[Result]:
        return [
            Result(value=1, label="a", metadata={"shared": "scanner"}),
            Result(value=2, label="b"),
        ]

    return scan_item


@scanner(name="default_loader_scanner", messages="all")
def default_loader_scanner_factory() -> Scanner[Transcript]:
    """Scanner using the default (identity) loader, authoring no metadata."""

    async def scan_transcript(transcript: Transcript) -> Result:
        return Result(value=True)

    return scan_transcript


def _metadata_rows(location: str, scanner_name: str) -> list[dict[str, Any]]:
    results = scan_results_df(location, scanner=scanner_name)
    df = results.scanners[scanner_name]
    return [json.loads(m) for m in df["metadata"].tolist()]


def test_loader_item_metadata_on_result_rows() -> None:
    """Loader-item metadata is merged into result metadata (scanner keys win)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        status = scan(
            scanners=[
                merged_metadata_scanner_factory(),
                loader_only_metadata_scanner_factory(),
                resultset_metadata_scanner_factory(),
                default_loader_scanner_factory(),
            ],
            transcripts=transcripts_from(str(POPULARITY_LOG)),
            scans=tmpdir,
            limit=1,
        )
        assert status.complete
        assert status.location is not None

        # scanner-authored keys win over loader item keys; both are present
        merged = _metadata_rows(status.location, "merged_metadata_scanner")
        assert sorted(merged, key=lambda m: str(m["provenance"])) == [
            {"provenance": "item-0", "shared": "scanner", "scanner_only": 1},
            {"provenance": "item-1", "shared": "scanner", "scanner_only": 1},
        ]

        # loader item metadata surfaces even when the scanner authors none
        loader_only = _metadata_rows(status.location, "loader_only_metadata_scanner")
        assert sorted(loader_only, key=lambda m: str(m["provenance"])) == [
            {"provenance": "item-0", "shared": "loader"},
            {"provenance": "item-1", "shared": "loader"},
        ]

        # results within a resultset each carry the merged metadata, surfaced
        # by resultset expansion as flattened metadata.<key> columns
        results = scan_results_df(status.location, scanner="resultset_metadata_scanner")
        df = results.scanners["resultset_metadata_scanner"]
        rows = sorted(
            (
                (row["metadata.provenance"], row["label"], row["metadata.shared"])
                for _, row in df.iterrows()
            ),
        )
        assert rows == [
            ("item-0", "a", "scanner"),
            ("item-0", "b", "loader"),
            ("item-1", "a", "scanner"),
            ("item-1", "b", "loader"),
        ]

        # default loaders pass the source transcript through: its metadata is
        # already surfaced as transcript_metadata and must not leak into the
        # result metadata column
        results = scan_results_df(status.location, scanner="default_loader_scanner")
        df = results.scanners["default_loader_scanner"]
        transcript_metadata = df["transcript_metadata"].iloc[0]
        if isinstance(transcript_metadata, str):
            transcript_metadata = json.loads(transcript_metadata)
        assert transcript_metadata, (
            "scanned transcript must have source metadata for this test to be "
            "meaningful"
        )
        assert [json.loads(m) for m in df["metadata"]] == [{}]
