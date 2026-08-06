"""`SerializedTranscript` passes its column strings through unchanged."""

from __future__ import annotations

import pytest
from inspect_scout._scanner.result import SerializedTranscript, _serialize_input


def test_serialized_transcript_passes_strings_through() -> None:
    value = SerializedTranscript(
        input_json='{"transcript_id":"t1","events":[]}',
        input_data_json='{"messages":[],"calls":[]}',
    )
    input_json, input_data_json = _serialize_input(value, "transcript", pool_dedup=True)
    assert input_json == '{"transcript_id":"t1","events":[]}'
    assert input_data_json == '{"messages":[],"calls":[]}'


def test_serialized_transcript_allows_absent_input_data() -> None:
    value = SerializedTranscript(input_json='{"transcript_id":"t1"}')
    _, input_data_json = _serialize_input(value, "transcript", pool_dedup=True)
    assert input_data_json is None


def test_serialized_transcript_rejects_unknown_fields() -> None:
    with pytest.raises(ValueError):
        SerializedTranscript(input_json="{}", nope=1)  # type: ignore[call-arg]
