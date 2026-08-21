"""`ResultReport` input storage columns: inline copy vs. transcript reference."""

from __future__ import annotations

import pytest
from inspect_ai.model import ChatMessageUser
from inspect_scout._scanner.result import (
    ReferenceTranscript,
    Result,
    ResultReport,
    SerializedTranscript,
)
from inspect_scout._transcript.types import Transcript


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


def test_parent_side_backstop_degrades_oversized_transcript(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from inspect_scout._util import constants as constants_mod

    monkeypatch.setattr(constants_mod, "RECORD_CELL_MAX_BYTES", 100)
    transcript = Transcript(
        transcript_id="t-big",
        source_uri="file:///log.eval",
        metadata={},
        messages=[ChatMessageUser(content="x" * 500)],
        events=[],
    )
    report = ResultReport(
        input_type="transcript",
        input_ids=["t-big"],
        input=transcript,
        result=Result(value=True),
        validation=None,
        error=None,
        events=[],
        model_usage={},
    )
    columns = report.to_df_columns()
    assert columns["input"] is None
    assert columns["input_storage"] == "reference"
    assert columns["input_content"] is None


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
