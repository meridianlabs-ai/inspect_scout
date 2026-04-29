"""Tests for ScanSpec / ScanTranscripts serialization."""

import json

from inspect_ai._util.json import to_json_str_safe
from inspect_scout._scanspec import ScanTranscripts


class TestScanTranscriptsSerialization:
    """Deprecated fields with default values must not be serialized to disk."""

    def test_default_deprecated_fields_excluded(self) -> None:
        snapshot = ScanTranscripts(
            type="database",
            location="/tmp/some/location",
            transcript_ids={"id-1": "file-1.parquet"},
        )

        data = json.loads(to_json_str_safe(snapshot))

        assert "count" not in data
        assert "fields" not in data
        assert "data" not in data

    def test_non_default_deprecated_fields_preserved(self) -> None:
        """Non-default deprecated values still serialize so legacy data round-trips."""
        snapshot = ScanTranscripts(
            type="database",
            location="/tmp/some/location",
            count=3,
            fields=[{"name": "transcript_id", "type": "string"}],
            data="transcript_id\nlegacy-000\n",
        )

        data = json.loads(to_json_str_safe(snapshot))

        assert data["count"] == 3
        assert data["fields"] == [{"name": "transcript_id", "type": "string"}]
        assert data["data"] == "transcript_id\nlegacy-000\n"

    def test_required_fields_still_serialized(self) -> None:
        snapshot = ScanTranscripts(
            type="eval_log",
            location="/tmp/logs",
            transcript_ids={"id-1": None},
        )

        data = json.loads(to_json_str_safe(snapshot))

        assert data["type"] == "eval_log"
        assert data["location"] == "/tmp/logs"
        assert data["transcript_ids"] == {"id-1": None}
