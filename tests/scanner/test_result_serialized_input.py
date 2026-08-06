"""`SerializedTranscript` passes its column values through unchanged."""

from __future__ import annotations

import pytest
from inspect_scout._scanner.result import SerializedTranscript, _serialize_input
from inspect_scout._transcript.types import Transcript


def test_serialized_transcript_passes_values_through() -> None:
    value = SerializedTranscript(
        input_json=b'{"transcript_id":"t1","events":[]}',
        input_data_json=b'{"messages":[],"calls":[]}',
    )
    input_json, input_data_json = _serialize_input(value, "transcript", pool_dedup=True)
    assert input_json == b'{"transcript_id":"t1","events":[]}'
    assert input_data_json == b'{"messages":[],"calls":[]}'


def test_serialized_transcript_allows_absent_input_data() -> None:
    value = SerializedTranscript(input_json=b'{"transcript_id":"t1"}')
    _, input_data_json = _serialize_input(value, "transcript", pool_dedup=True)
    assert input_data_json is None


def test_serialized_transcript_rejects_unknown_fields() -> None:
    with pytest.raises(ValueError):
        SerializedTranscript(input_json=b"{}", nope=1)  # type: ignore[call-arg]


def test_materialized_input_serializes_to_bytes_too() -> None:
    """The other branches must agree, or the column mixes str with bytes."""
    input_json, input_data_json = _serialize_input(
        Transcript(transcript_id="t1", messages=[], events=[], timelines=[]),
        "transcript",
        pool_dedup=True,
    )
    assert isinstance(input_json, bytes)
    assert isinstance(input_data_json, bytes)
