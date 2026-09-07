import pytest
from inspect_scout import Transcript
from inspect_scout._scanner.result import Error, ResultReport


def _error_report(refusal: bool) -> ResultReport:
    return ResultReport(
        input_type="transcript",
        input_ids=["t1"],
        input=Transcript(transcript_id="t1"),
        result=None,
        validation=None,
        error=Error(
            transcript_id="t1",
            scanner="scanner",
            error="boom",
            traceback="",
            refusal=refusal,
        ),
        events=[],
        model_usage={},
    )


@pytest.mark.parametrize(
    ("refusal", "expected"),
    [(True, "refusal"), (False, None)],
)
def test_scan_error_type_reflects_error_refusal(
    refusal: bool, expected: str | None
) -> None:
    columns = _error_report(refusal).to_df_columns()
    assert columns["scan_error_type"] == expected
