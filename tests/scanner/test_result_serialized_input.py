"""`SerializedTranscript` passes its column values through unchanged."""

from __future__ import annotations

import pytest
from inspect_scout._scanner.result import (
    ReferenceTranscript,
    Result,
    ResultReport,
    SerializedTranscript,
    _serialize_input,
)


@pytest.mark.parametrize(
    ("value", "expected_data"),
    [
        pytest.param(
            SerializedTranscript(
                input_json=bytearray(b'{"transcript_id":"t1","events":[]}'),
                input_data_json=bytearray(b'{"messages":[],"calls":[]}'),
            ),
            b'{"messages":[],"calls":[]}',
            id="with-input-data",
        ),
        pytest.param(
            SerializedTranscript(input_json=bytearray(b'{"transcript_id":"t1"}')),
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
        SerializedTranscript(input_json=bytearray(b"{}"), nope=1)  # type: ignore[call-arg]


def test_reference_input_produces_reference_columns() -> None:
    report = ResultReport(
        input_type="transcript",
        input_ids=["t1"],
        input=ReferenceTranscript(
            source_uri="s3://bucket/log.eval",
            transcript_id="t1",
            content_json='{"messages": "all", "events": null, "timeline": null}',
        ),
        result=Result(value=True),
        validation=None,
        error=None,
        events=[],
        model_usage={},
    )
    columns = report.to_df_columns()
    assert columns["input"] is None
    assert columns["input_data"] is None
    assert columns["input_storage"] == "reference"
    assert (
        columns["input_content"]
        == '{"messages": "all", "events": null, "timeline": null}'
    )


def test_inline_input_marks_storage_inline() -> None:
    report = ResultReport(
        input_type="transcript",
        input_ids=["t1"],
        input=SerializedTranscript(input_json=bytearray(b"{}"), input_data_json=None),
        result=Result(value=True),
        validation=None,
        error=None,
        events=[],
        model_usage={},
    )
    columns = report.to_df_columns()
    assert columns["input_storage"] == "inline"
    assert columns["input_content"] is None
