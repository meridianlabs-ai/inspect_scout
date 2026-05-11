"""Tests for the EvalSample → Transcript builders in `_transcript/eval_log.py`.

`transcript_info_from_eval_sample` / `transcript_from_eval_sample` are
consumed by inspect_ai's per-sample scan dispatch. These tests pin the
field mappings and the small set of fallback behaviors they implement.
"""

from typing import Any

from inspect_ai._util.error import EvalError
from inspect_ai.event import ModelEvent
from inspect_ai.log import EvalSample
from inspect_ai.model import ChatMessageUser, GenerateConfig, ModelOutput
from inspect_ai.scorer import Score
from inspect_scout._transcript.eval_log import (
    EVAL_LOG_SOURCE_TYPE,
    transcript_from_eval_sample,
    transcript_info_from_eval_sample,
)

# --- helpers ---------------------------------------------------------------


def _make_eval_sample(**overrides: Any) -> EvalSample:
    """Build an `EvalSample` with sensible defaults; overrides win."""
    defaults: dict[str, Any] = {
        "id": 1,
        "epoch": 0,
        "input": "hi",
        "target": "hi",
        "messages": [ChatMessageUser(content="hi")],
        "metadata": {"a": 1},
    }
    defaults.update(overrides)
    return EvalSample(**defaults)


# --- transcript_info_from_eval_sample --------------------------------------


def test_info_populates_all_top_level_fields() -> None:
    """Direct field copy: id → task_id, epoch → task_repeat, etc."""
    # use a timezone-naive offset form since pydantic normalizes the trailing
    # 'Z' to '+00:00' on round-trip — easier to assert equality this way
    sample = _make_eval_sample(
        id="sample-7",
        epoch=3,
        uuid="tid-abc",
        started_at="2025-01-01T00:00:00+00:00",
        completed_at="2025-01-01T00:01:00+00:00",
        total_time=42.0,
        messages=[ChatMessageUser(content="a"), ChatMessageUser(content="b")],
        metadata={"k": "v"},
    )
    info = transcript_info_from_eval_sample(
        sample,
        eval_id="eval-1",
        log_location="/path/to/log.eval",
        model="mockllm/eval-model",
    )
    assert info.transcript_id == "tid-abc"
    assert info.source_type == EVAL_LOG_SOURCE_TYPE
    assert info.source_id == "eval-1"
    assert info.source_uri == "/path/to/log.eval"
    assert info.date == "2025-01-01T00:01:00+00:00"  # completed_at wins
    assert info.task_id == "sample-7"
    assert info.task_repeat == 3
    assert info.model == "mockllm/eval-model"
    assert info.message_count == 2
    assert info.total_time == 42.0
    assert info.metadata == {"k": "v"}


def test_info_falls_back_to_started_at_when_no_completed_at() -> None:
    """`date` prefers `completed_at` but falls back to `started_at`."""
    sample = _make_eval_sample(
        started_at="2025-01-01T00:00:00+00:00",
        completed_at=None,
    )
    info = transcript_info_from_eval_sample(
        sample, eval_id="e", log_location=None, model=None
    )
    assert info.date == "2025-01-01T00:00:00+00:00"


def test_info_uses_auto_sample_id_when_uuid_missing() -> None:
    """Without `sample.uuid`, the id derives deterministically from (eval_id, sample.id, epoch).

    Matches how `samples_df` / scout's offline reader compute transcript_id
    for unflattened logs — so a record produced here cross-references the
    same transcript when that log is later read back.
    """
    from inspect_ai.analysis._dataframe.samples.extract import auto_sample_id

    sample = _make_eval_sample(id=42, epoch=1, uuid=None)
    info = transcript_info_from_eval_sample(
        sample, eval_id="e1", log_location=None, model=None
    )
    expected = auto_sample_id("e1", sample)
    assert info.transcript_id == expected


def test_info_score_with_single_scorer() -> None:
    sample = _make_eval_sample(scores={"acc": Score(value=0.75)})
    info = transcript_info_from_eval_sample(
        sample, eval_id="e", log_location=None, model=None
    )
    assert info.score == 0.75
    assert info.success is True  # 0.75 > 0


def test_info_score_picks_first_with_multiple_scorers() -> None:
    """Scout's `sample_score` returns the *first* score with multiple scorers.

    Aligned with scout's offline reader convention (so the live and stored
    parquet columns agree). This differs from inspect_ai's previous local
    `_score_value` which returned None when there were multiple scorers.
    """
    sample = _make_eval_sample(
        scores={
            "first": Score(value=0.5),
            "second": Score(value=0.0),
        },
    )
    info = transcript_info_from_eval_sample(
        sample, eval_id="e", log_location=None, model=None
    )
    assert info.score == 0.5


def test_info_score_unwraps_dict_with_value_key() -> None:
    """A nested `{"value": ..., ...}` score is flattened to the inner value."""
    sample = _make_eval_sample(
        scores={"acc": Score(value={"value": 1, "answer": "A"})},
    )
    info = transcript_info_from_eval_sample(
        sample, eval_id="e", log_location=None, model=None
    )
    assert info.score == 1


def test_info_success_from_score_metadata_overrides_value() -> None:
    """A score that explicitly carries `metadata['success']` wins over the value-derived success."""
    sample = _make_eval_sample(
        scores={"acc": Score(value=0.0, metadata={"success": True})},
    )
    info = transcript_info_from_eval_sample(
        sample, eval_id="e", log_location=None, model=None
    )
    assert info.success is True


def test_info_success_none_for_unscored_sample() -> None:
    sample = _make_eval_sample(scores=None)
    info = transcript_info_from_eval_sample(
        sample, eval_id="e", log_location=None, model=None
    )
    assert info.score is None
    assert info.success is None


def test_info_extracts_error_message() -> None:
    err = EvalError(message="boom", traceback="t", traceback_ansi="ta")
    sample = _make_eval_sample(error=err)
    info = transcript_info_from_eval_sample(
        sample, eval_id="e", log_location=None, model=None
    )
    assert info.error == "boom"


def test_info_metadata_is_a_copy() -> None:
    """`metadata=dict(...)` returns a fresh dict so mutating the info can't leak back into the sample."""
    sample_metadata = {"k": "v"}
    sample = _make_eval_sample(metadata=sample_metadata)
    info = transcript_info_from_eval_sample(
        sample, eval_id="e", log_location=None, model=None
    )
    info.metadata["k"] = "mutated"
    assert sample_metadata == {"k": "v"}


# --- transcript_from_eval_sample -------------------------------------------


def test_transcript_attaches_messages_events_timelines() -> None:
    msgs = [ChatMessageUser(content="a"), ChatMessageUser(content="b")]
    sample = _make_eval_sample(messages=msgs, events=[], timelines=None)
    t = transcript_from_eval_sample(sample, eval_id="e", log_location=None, model=None)
    assert list(t.messages) == msgs
    assert list(t.events) == []
    assert list(t.timelines) == []


def test_transcript_synthesizes_timeline_from_events_when_no_timelines() -> None:
    """If `timelines` is empty but `events` is non-empty, a timeline is derived via `timeline_build` so scanners that operate on timelines still see something to scan."""
    ev = ModelEvent(
        model="m",
        input=[],
        tools=[],
        tool_choice="auto",
        config=GenerateConfig(),
        output=ModelOutput.from_content("m", "ok"),
    )
    sample = _make_eval_sample(events=[ev], timelines=None)
    t = transcript_from_eval_sample(sample, eval_id="e", log_location=None, model=None)
    assert len(t.timelines) == 1


def test_transcript_keeps_stored_timelines_unchanged() -> None:
    """When `timelines` is already on the sample, it's passed through untouched (no event-derived synthesis)."""
    from inspect_ai.event import Timeline, TimelineSpan

    stored = [
        Timeline(name="t1", description="d", root=TimelineSpan(id="r", name="root"))
    ]
    sample = _make_eval_sample(events=[], timelines=stored)
    t = transcript_from_eval_sample(sample, eval_id="e", log_location=None, model=None)
    assert list(t.timelines) == stored
