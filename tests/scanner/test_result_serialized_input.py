"""`ResultReport` input storage columns: inline copy vs. transcript reference."""

from __future__ import annotations

import pytest
from inspect_ai.model import ChatMessageUser
from inspect_scout._scanner.result import Result, ResultReport
from inspect_scout._transcript.types import Transcript


@pytest.mark.parametrize(
    ("text", "storage"), [("x", "inline"), ("x" * 500, "reference")]
)
def test_parent_side_backstop_degrades_oversized_transcript(
    monkeypatch: pytest.MonkeyPatch, text: str, storage: str
) -> None:
    from inspect_scout._util import constants as constants_mod

    monkeypatch.setattr(constants_mod, "RECORD_CELL_MAX_BYTES", 300)
    transcript = Transcript(
        transcript_id="t1",
        source_uri="file:///log.eval",
        metadata={},
        messages=[ChatMessageUser(content=text)],
        events=[],
    )
    report = ResultReport(
        input_type="transcript",
        input_ids=["t1"],
        input=transcript,
        result=Result(value=True),
        validation=None,
        error=None,
        events=[],
        model_usage={},
    )
    columns = report.to_df_columns()
    assert columns["input_storage"] == storage
    assert (columns["input"] is None) == (storage == "reference")
    assert columns["input_content"] is None
