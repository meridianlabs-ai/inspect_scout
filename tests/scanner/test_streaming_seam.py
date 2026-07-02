"""Tests for the streaming scanner seam: input plumbing."""

from __future__ import annotations

from inspect_scout._scanner.result import _serialize_input
from inspect_scout._scanner.util import get_input_type_and_ids
from inspect_scout._transcript.types import TranscriptInfo


def test_input_type_for_transcript_info() -> None:
    info = TranscriptInfo(transcript_id="t1")
    assert get_input_type_and_ids(info) == ("transcript_handle", ["t1"])


def test_serialize_input_info_only() -> None:
    info = TranscriptInfo(transcript_id="t1", source_id="e1")
    input_json, input_data = _serialize_input(
        info, "transcript_handle", pool_dedup=True
    )
    assert input_data is None
    assert '"transcript_id":"t1"' in input_json.replace(" ", "")
    assert "messages" not in input_json  # no content fields serialized
