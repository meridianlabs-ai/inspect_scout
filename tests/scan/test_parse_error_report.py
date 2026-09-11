from inspect_scout._concurrency.common import ParseJob
from inspect_scout._scan import _reports_for_parse_error
from inspect_scout._transcript.types import Transcript, TranscriptInfo


def test_parse_error_report_carries_full_transcript_info() -> None:
    """The placeholder `input` of a parse-error report keeps every info field.

    The placeholder is built from the job's `TranscriptInfo` field by field, so
    a field added to the model goes missing from error reports until it is
    added to that copy too.
    """
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
