"""`SerializedTranscript` passes its column values through unchanged."""

from __future__ import annotations

from inspect_scout._scanner.result import SerializedTranscript, _serialize_input


def test_serialized_transcript_passes_values_through() -> None:
    value = SerializedTranscript(
        input_json=bytearray(b'{"transcript_id":"t1","events":[]}'),
        input_data_json=bytearray(b'{"messages":[],"calls":[]}'),
    )

    input_json, input_data_json = _serialize_input(value, "transcript", pool_dedup=True)

    assert input_json == value.input_json
    assert input_data_json == value.input_data_json
