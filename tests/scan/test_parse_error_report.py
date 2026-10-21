from inspect_scout._concurrency.common import ParseJob
from inspect_scout._scan import _reports_for_parse_error
from inspect_scout._transcript.types import Transcript, TranscriptInfo


def test_parse_error_report_carries_full_transcript_info() -> None:
    """The placeholder is copied from the info field by field; none may go missing."""
    info = TranscriptInfo(
        transcript_id="t1",
        source_type="test",
        source_id="source",
        source_uri="test://source",
        score="C",
        score_explanation="graded C because the tests failed",
    )

    reports = _reports_for_parse_error(
        ParseJob(info, {0}), RuntimeError("boom"), ["s1"]
    )

    assert len(reports) == 1
    placeholder = reports[0].input
    assert isinstance(placeholder, Transcript)
    assert (
        placeholder.model_dump(exclude={"messages", "events", "timelines"})
        == info.model_dump()
    )
