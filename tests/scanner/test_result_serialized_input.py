"""`ResultReport` input storage columns: inline copy vs. transcript reference."""

from __future__ import annotations

from inspect_scout._scanner.result import (
    ReferenceTranscript,
    Result,
    ResultReport,
    SerializedTranscript,
)


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
        input=SerializedTranscript(
            input_json=bytearray(b"{}"), input_data_json=bytearray(b"{}")
        ),
        result=Result(value=True),
        validation=None,
        error=None,
        events=[],
        model_usage={},
    )
    columns = report.to_df_columns()
    assert columns["input_storage"] == "inline"
    assert columns["input_content"] is None
