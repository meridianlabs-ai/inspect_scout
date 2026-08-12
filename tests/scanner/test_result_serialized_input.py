"""`SerializedTranscript` passes its column values through unchanged."""

from __future__ import annotations

import pytest
from inspect_scout._scanner.result import SerializedTranscript, _serialize_input


@pytest.mark.parametrize(
    ("value", "expected_data"),
    [
        pytest.param(
            SerializedTranscript(
                input_json=b'{"transcript_id":"t1","events":[]}',
                input_data_json=b'{"messages":[],"calls":[]}',
            ),
            b'{"messages":[],"calls":[]}',
            id="with-input-data",
        ),
        pytest.param(
            SerializedTranscript(input_json=b'{"transcript_id":"t1"}'),
            None,
            id="input-data-absent",
        ),
    ],
)
def test_serialized_transcript_passes_values_through(
    value: SerializedTranscript, expected_data: bytes | None
) -> None:
    input_json, input_data_json = _serialize_input(value, "transcript", pool_dedup=True)
    assert input_json == value.input_json
    assert input_data_json == expected_data


def test_serialized_transcript_rejects_unknown_fields() -> None:
    with pytest.raises(ValueError):
        SerializedTranscript(input_json=b"{}", nope=1)  # type: ignore[call-arg]
