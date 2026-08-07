"""Tests for the static bundle generator (scout view bundle)."""

import json
from pathlib import Path

import pytest
import zstandard
from inspect_ai._util.path import chdir
from inspect_scout._view._bundle import (
    BUNDLE_FORMAT,
    BUNDLE_VERSION,
    _collect_column_values,
    _merge_info_into_payload,
    _sort_key,
    _write_catalog,
    bundle_view,
)
from inspect_scout._view.types import ViewConfig

LOGS_DIR = Path(__file__).parent.parent / "recorder" / "logs"


def _decompress(path: Path) -> bytes:
    return zstandard.ZstdDecompressor().decompress(
        path.read_bytes(), max_output_size=500_000_000
    )


class TestMergeInfoIntoPayload:
    def test_merges_into_object_with_keys(self) -> None:
        merged = _merge_info_into_payload(b'{"a":1}', b'{"messages":[]}')
        assert json.loads(merged) == {"info": {"a": 1}, "messages": []}

    def test_merges_into_empty_object(self) -> None:
        merged = _merge_info_into_payload(b'{"a":1}', b"  {}  ")
        assert json.loads(merged) == {"info": {"a": 1}}

    def test_rejects_non_object_payload(self) -> None:
        with pytest.raises(ValueError):
            _merge_info_into_payload(b'{"a":1}', b"[1,2]")


class TestSortKey:
    def test_orders_nulls_first_numbers_then_strings(self) -> None:
        values = ["b", None, 2, "a", 1]
        assert sorted(values, key=_sort_key) == [None, 1, 2, "a", "b"]


class TestWriteCatalog:
    def test_shards_sorted_with_stats(self, tmp_path: Path) -> None:
        rows = [
            {"transcript_id": f"t{i}", "date": f"2026-01-{i + 1:02d}", "model": "m"}
            for i in reversed(range(5))
        ]
        manifest = _write_catalog(
            rows,
            api_dir=tmp_path,
            section="transcripts",
            dir_uri="/transcripts",
            id_column="transcript_id",
            order_column="date",
            order_direction="DESC",
            shard_size=2,
        )

        assert manifest["row_count"] == 5
        assert manifest["default_order"] == {"column": "date", "direction": "DESC"}
        assert [s["row_count"] for s in manifest["shards"]] == [2, 2, 1]
        # globally sorted ascending with contiguous min/max ranges
        assert [(s["min"], s["max"]) for s in manifest["shards"]] == [
            ("2026-01-01", "2026-01-02"),
            ("2026-01-03", "2026-01-04"),
            ("2026-01-05", "2026-01-05"),
        ]
        shard0 = json.loads(_decompress(tmp_path / manifest["shards"][0]["path"]))
        assert [r["transcript_id"] for r in shard0] == ["t0", "t1"]

        columns = json.loads((tmp_path / manifest["column_values"]).read_text())
        assert columns["model"] == ["m"]

    def test_empty_catalog(self, tmp_path: Path) -> None:
        manifest = _write_catalog(
            [],
            api_dir=tmp_path,
            section="scans",
            dir_uri="/scans",
            id_column="scan_id",
            order_column="timestamp",
            order_direction="DESC",
            shard_size=2,
        )
        assert manifest["row_count"] == 0
        assert manifest["shards"] == []
        assert "column_values" not in manifest


class TestCollectColumnValues:
    def test_drops_non_scalar_and_high_cardinality_columns(self) -> None:
        rows = [
            {"model": "m1", "metadata": {"k": i}, "uuid": str(i)} for i in range(1500)
        ]
        values = _collect_column_values(rows)
        assert values["model"] == ["m1"]
        assert "metadata" not in values  # non-scalar
        assert "uuid" not in values  # cardinality > cap


@pytest.mark.asyncio
async def test_bundle_view_end_to_end(tmp_path: Path) -> None:
    """Bundle the fixture eval logs and verify the v1 layout invariants."""
    output_dir = tmp_path / "bundle"
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    with chdir(str(project_dir)):
        await bundle_view(
            config=ViewConfig(transcripts_cli=str(LOGS_DIR)),
            output_dir=output_dir,
            shard_size=100,
        )

    api = output_dir / "api"
    manifest = json.loads((api / "manifest.json").read_text())
    assert manifest["format"] == BUNDLE_FORMAT
    assert manifest["version"] == BUNDLE_VERSION

    transcripts = manifest["transcripts"]
    assert transcripts["id_column"] == "transcript_id"
    assert transcripts["default_order"] == {"column": "date", "direction": "DESC"}
    assert transcripts["row_count"] > 0
    assert (
        sum(s["row_count"] for s in transcripts["shards"]) == (transcripts["row_count"])
    )

    # shards are globally sorted ascending by date with correct stats
    all_dates: list[str] = []
    for shard in transcripts["shards"]:
        rows = json.loads(_decompress(api / shard["path"]))
        dates = [r["date"] for r in rows]
        assert shard["min"] == dates[0]
        assert shard["max"] == dates[-1]
        all_dates.extend(dates)
    assert all_dates == sorted(all_dates)

    # every catalog row has a decodable item file with info merged in
    first_shard = json.loads(_decompress(api / transcripts["shards"][0]["path"]))
    row = first_shard[0]
    item = json.loads(
        _decompress(api / "transcripts" / "items" / f"{row['transcript_id']}.json.zst")
    )
    assert item["info"]["transcript_id"] == row["transcript_id"]
    assert "messages" in item and "events" in item

    # boot tag injected before </head>
    index_html = (output_dir / "index.html").read_text()
    assert '<script id="scout_context" type="application/json">' in index_html
    assert index_html.index("scout_context") < index_html.index("</head>")

    # scans section present (empty for this fixture project)
    assert manifest["scans"]["row_count"] == 0
