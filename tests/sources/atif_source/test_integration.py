"""Integration tests for ATIF import source."""

# ruff: noqa: E402  (harbor is an optional dep; imports follow importorskip)

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest

pytest.importorskip("harbor")

from harbor.models.trajectories import (
    Agent,
    Metrics,
    Observation,
    ObservationResult,
    Step,
    SubagentTrajectoryRef,
    ToolCall,
    Trajectory,
)
from inspect_ai.event import (
    CompactionEvent,
    ModelEvent,
    SpanBeginEvent,
    SpanEndEvent,
)
from inspect_ai.model import ChatMessageAssistant, ChatMessageTool
from inspect_scout.sources import atif
from inspect_scout.sources._atif.client import ATIF_SOURCE_TYPE


@pytest.fixture
def fixtures_dir() -> Path:
    """Get the fixtures directory."""
    return Path(__file__).parent / "fixtures"


def _make_trajectory(steps: list[Step], **kwargs: object) -> Trajectory:
    return Trajectory(
        session_id="test-session",
        agent=Agent(name="test-agent", version="0.1.0"),
        steps=steps,
        **kwargs,
    )


def _write_trajectory(path: Path, trajectory: Trajectory) -> None:
    """Serialize a trajectory to JSON on disk."""
    path.write_text(trajectory.model_dump_json(exclude_none=True))


@pytest.mark.asyncio
async def test_yields_transcripts_from_fixtures_dir(fixtures_dir: Path) -> None:
    """All committed ATIF fixtures yield (covers openhands and terminus_2)."""
    count = 0
    async for transcript in atif(path=fixtures_dir):
        assert transcript.source_type == ATIF_SOURCE_TYPE
        count += 1
    assert count == 4


@pytest.mark.asyncio
async def test_yields_from_single_file_path(fixtures_dir: Path) -> None:
    """`path` accepts a path to a single trajectory file, not just a directory."""
    trajectory_file = fixtures_dir / "openhands_hello-world.trajectory.json"
    transcripts = [t async for t in atif(path=trajectory_file)]
    assert len(transcripts) == 1


@pytest.mark.asyncio
async def test_session_id_filter(fixtures_dir: Path, tmp_path: Path) -> None:
    """`session_id` filters by the trajectory's session_id field."""
    src = (fixtures_dir / "openhands_hello-world.trajectory.json").read_text()
    target = json.loads(src)
    target["session_id"] = "session-aaa"
    other = json.loads(src)
    other["session_id"] = "session-bbb"
    (tmp_path / "session-aaa.json").write_text(json.dumps(target))
    (tmp_path / "session-bbb.json").write_text(json.dumps(other))

    transcripts = [t async for t in atif(path=tmp_path, session_id="session-aaa")]
    assert len(transcripts) == 1
    assert transcripts[0].transcript_id == "session-aaa"


@pytest.mark.asyncio
async def test_limit_truncates_yield(fixtures_dir: Path) -> None:
    """`limit` stops yielding after N transcripts."""
    count = 0
    async for _transcript in atif(path=fixtures_dir, limit=2):
        count += 1
    assert count == 2


@pytest.mark.asyncio
async def test_from_time_filters_by_mtime(fixtures_dir: Path, tmp_path: Path) -> None:
    """`from_time` skips files whose mtime is older."""
    src = (fixtures_dir / "openhands_hello-world.trajectory.json").read_text()
    session_1 = tmp_path / "session_1.json"
    session_2 = tmp_path / "session_2.json"

    session_1_dict = json.loads(src)
    session_1_dict["session_id"] = "session_1"
    session_1.write_text(json.dumps(session_1_dict))

    session_2_dict = json.loads(src)
    session_2_dict["session_id"] = "session_2"
    session_2.write_text(json.dumps(session_2_dict))

    # Backdate session_1's mtime by an hour.
    old_time = (datetime.now() - timedelta(hours=1)).timestamp()
    os.utime(session_1, (old_time, old_time))

    from_time = datetime.now() - timedelta(minutes=30)
    transcripts = [t async for t in atif(path=tmp_path, from_time=from_time)]

    assert len(transcripts) == 1
    assert transcripts[0].transcript_id == "session_2"


@pytest.mark.asyncio
async def test_no_path_yields_nothing() -> None:
    """`atif()` with no path yields zero transcripts (no implicit default)."""
    transcripts = [t async for t in atif()]
    assert transcripts == []


@pytest.mark.asyncio
async def test_nonexistent_path_yields_nothing() -> None:
    """A path that doesn't exist yields zero transcripts (logged, not raised)."""
    transcripts = [t async for t in atif(path="/nonexistent/path/to/nowhere")]
    assert transcripts == []


@pytest.mark.asyncio
async def test_tool_call_and_observation_correlate_via_source_call_id(
    tmp_path: Path,
) -> None:
    """`ChatMessageTool.tool_call_id` matches the ATIF `source_call_id`."""
    trajectory = _make_trajectory(
        [
            Step(
                step_id=1,
                source="agent",
                message="Let me read that file.",
                tool_calls=[
                    ToolCall(
                        tool_call_id="tool_1",
                        function_name="run_code",
                        arguments={"code": "1 + 1"},
                    )
                ],
                observation=Observation(
                    results=[ObservationResult(source_call_id="tool_1", content="2")]
                ),
            )
        ]
    )
    path = tmp_path / "trajectory.json"
    _write_trajectory(path, trajectory)
    transcripts = [t async for t in atif(path=path)]
    assert len(transcripts) == 1
    transcript = transcripts[0]
    assistant_msg, tool_msg = transcript.messages

    assert isinstance(assistant_msg, ChatMessageAssistant)
    assert assistant_msg.tool_calls is not None
    assert assistant_msg.tool_calls[0].id == "tool_1"
    assert assistant_msg.tool_calls[0].function == "run_code"

    assert isinstance(tool_msg, ChatMessageTool)
    assert tool_msg.tool_call_id == "tool_1"
    assert tool_msg.function == "run_code"
    assert tool_msg.content == "2"


@pytest.mark.asyncio
async def test_context_management_step_emits_compaction_event(
    tmp_path: Path,
) -> None:
    """A system step with `extra.context_management` becomes `CompactionEvent`."""
    trajectory = _make_trajectory(
        [
            Step(
                step_id=1,
                source="system",
                message="Conversation compacted",
                extra={
                    "context_management": {
                        "type": "compaction",
                        "boundary": "replace",
                    }
                },
            )
        ]
    )
    path = tmp_path / "trajectory.json"
    _write_trajectory(path, trajectory)
    transcripts = [t async for t in atif(path=path)]
    assert len(transcripts) == 1
    transcript = transcripts[0]

    # The system message is replaced by a CompactionEvent.
    assert transcript.messages == []
    assert len(transcript.events) == 1
    event = transcript.events[0]
    assert isinstance(event, CompactionEvent)
    assert event.type == "summary"  # default; ATIF type/boundary go in metadata
    assert event.metadata == {"type": "compaction", "boundary": "replace"}


@pytest.mark.asyncio
async def test_context_management_step_with_subagent_refs_inlines_spans(
    tmp_path: Path,
) -> None:
    """A context_management step with `subagent_trajectory_ref` emits both a CompactionEvent and subagent span events."""  # noqa: E501
    for i in range(3):
        sub = Trajectory(
            session_id=f"sub-{i}",
            agent=Agent(name=f"summarizer-{i}", version="0.1.0"),
            steps=[Step(step_id=1, source="user", message="x")],
        )
        _write_trajectory(tmp_path / f"sub-{i}.json", sub)

    trajectory = _make_trajectory(
        [
            Step(
                step_id=1,
                source="system",
                message="Performed context summarization and handoff to continue task.",
                extra={
                    "context_management": {
                        "type": "compaction",
                        "boundary": "replace",
                    }
                },
                observation=Observation(
                    results=[
                        ObservationResult(
                            subagent_trajectory_ref=[
                                SubagentTrajectoryRef(
                                    session_id=f"sub-{i}",
                                    trajectory_path=f"sub-{i}.json",
                                )
                                for i in range(3)
                            ],
                        )
                    ]
                ),
            )
        ]
    )
    path = tmp_path / "trajectory.json"
    _write_trajectory(path, trajectory)
    transcripts = [t async for t in atif(path=path)]
    assert len(transcripts) == 1
    transcript = transcripts[0]

    # CompactionEvent followed by 3 (SpanBegin, SpanEnd) pairs.
    assert transcript.messages == []
    assert len(transcript.events) == 7
    assert isinstance(transcript.events[0], CompactionEvent)
    for i in range(3):
        assert isinstance(transcript.events[1 + 2 * i], SpanBeginEvent)
        assert isinstance(transcript.events[2 + 2 * i], SpanEndEvent)


@pytest.mark.asyncio
async def test_subagent_files_not_double_indexed(tmp_path: Path) -> None:
    """A referenced subagent file is inlined into its parent, not yielded standalone."""
    sub = Trajectory(
        session_id="sub-0",
        agent=Agent(name="reviewer", version="0.1.0"),
        steps=[Step(step_id=1, source="user", message="x")],
    )
    _write_trajectory(tmp_path / "sub-0.json", sub)

    parent = _make_trajectory(
        [
            Step(
                step_id=1,
                source="agent",
                message="delegate",
                tool_calls=[
                    ToolCall(tool_call_id="c1", function_name="Task", arguments={})
                ],
                observation=Observation(
                    results=[
                        ObservationResult(
                            source_call_id="c1",
                            content="done",
                            subagent_trajectory_ref=[
                                SubagentTrajectoryRef(
                                    session_id="sub-0", trajectory_path="sub-0.json"
                                )
                            ],
                        )
                    ]
                ),
            )
        ]
    )
    _write_trajectory(tmp_path / "parent.json", parent)

    transcripts = [t async for t in atif(path=tmp_path)]
    # Only the parent is yielded; sub-0.json is inlined as a span, not standalone.
    assert len(transcripts) == 1
    assert transcripts[0].transcript_id == "test-session"
    span_begins = [e for e in transcripts[0].events if isinstance(e, SpanBeginEvent)]
    assert len(span_begins) == 1


@pytest.mark.asyncio
async def test_is_copied_context_sets_transcript_metadata_flag(
    tmp_path: Path,
) -> None:
    """Any `Step.is_copied_context=True` sets transcript-level `has_copied_context`."""
    trajectory = _make_trajectory(
        [
            Step(step_id=1, source="user", message="hi"),
            Step(
                step_id=2,
                source="agent",
                message="from another run",
                is_copied_context=True,
            ),
        ]
    )
    path = tmp_path / "trajectory.json"
    _write_trajectory(path, trajectory)
    transcripts = [t async for t in atif(path=path)]
    assert len(transcripts) == 1
    transcript = transcripts[0]
    assert transcript.metadata["has_copied_context"] is True


@pytest.mark.asyncio
async def test_continued_trajectory_ref_preserved_in_metadata(
    tmp_path: Path,
) -> None:
    """`Trajectory.continued_trajectory_ref` is preserved in transcript metadata."""
    trajectory = _make_trajectory(
        [Step(step_id=1, source="user", message="hi")],
        continued_trajectory_ref="next.json",
    )
    path = tmp_path / "trajectory.json"
    _write_trajectory(path, trajectory)
    transcripts = [t async for t in atif(path=path)]
    assert len(transcripts) == 1
    transcript = transcripts[0]
    assert transcript.metadata["continued_trajectory_ref"] == "next.json"


@pytest.mark.asyncio
async def test_transcript_top_level_fields(tmp_path: Path) -> None:
    """Identifying fields (id, source_type, agent, source_uri) are populated."""
    trajectory = _make_trajectory([Step(step_id=1, source="user", message="hi")])
    path = tmp_path / "trajectory.json"
    _write_trajectory(path, trajectory)
    transcripts = [t async for t in atif(path=path)]
    assert len(transcripts) == 1
    transcript = transcripts[0]

    assert transcript.transcript_id == "test-session"
    assert transcript.source_type == ATIF_SOURCE_TYPE
    assert transcript.source_id == "test-session"
    assert transcript.source_uri == str(tmp_path / "trajectory.json")
    assert transcript.agent == "test-agent"
    assert transcript.message_count == 1
    assert transcript.metadata["schema_version"].startswith("ATIF-")


@pytest.mark.asyncio
async def test_model_extraction(tmp_path: Path) -> None:
    """`Transcript.model` is pulled from `trajectory.agent.model_name`."""
    trajectory = Trajectory(
        session_id="t",
        agent=Agent(name="terminus_2", version="1.0", model_name="gpt-4"),
        steps=[Step(step_id=1, source="user", message="hi")],
    )
    path = tmp_path / "trajectory.json"
    _write_trajectory(path, trajectory)
    transcripts = [t async for t in atif(path=path)]
    assert len(transcripts) == 1
    transcript = transcripts[0]
    assert transcript.model == "gpt-4"


@pytest.mark.asyncio
async def test_token_counting(tmp_path: Path) -> None:
    """`Transcript.total_tokens` sums `final_metrics.total_prompt_tokens` + completion."""
    from harbor.models.trajectories.final_metrics import FinalMetrics

    trajectory = _make_trajectory(
        [Step(step_id=1, source="user", message="hi")],
        final_metrics=FinalMetrics(
            total_prompt_tokens=100,
            total_completion_tokens=50,
        ),
    )
    path = tmp_path / "trajectory.json"
    _write_trajectory(path, trajectory)
    transcripts = [t async for t in atif(path=path)]
    assert len(transcripts) == 1
    transcript = transcripts[0]
    assert transcript.total_tokens == 150


@pytest.mark.asyncio
async def test_date_extraction(tmp_path: Path) -> None:
    """`Transcript.date` is pulled from the first step's timestamp."""
    trajectory = _make_trajectory(
        [
            Step(
                step_id=1, source="user", message="hi", timestamp="2025-11-15T10:23:45Z"
            ),
            Step(step_id=2, source="agent", message="Hello"),
        ],
    )
    path = tmp_path / "trajectory.json"
    _write_trajectory(path, trajectory)
    transcripts = [t async for t in atif(path=path)]
    assert len(transcripts) == 1
    transcript = transcripts[0]
    assert transcript.date == "2025-11-15T10:23:45Z"


@pytest.mark.asyncio
async def test_stable_message_ids_recur_across_model_events(tmp_path: Path) -> None:
    """Identical messages get the same `id` everywhere they appear."""
    trajectory = _make_trajectory(
        [
            Step(step_id=1, source="user", message="hi"),
            Step(
                step_id=2,
                source="agent",
                message="Hello",
                model_name="gpt-4",
                metrics=Metrics(prompt_tokens=10, completion_tokens=5),
            ),
            Step(
                step_id=3,
                source="agent",
                message="ok",
                model_name="gpt-4",
                metrics=Metrics(prompt_tokens=20, completion_tokens=5),
            ),
        ],
    )
    path = tmp_path / "trajectory.json"
    _write_trajectory(path, trajectory)
    transcripts = [t async for t in atif(path=path)]
    assert len(transcripts) == 1
    transcript = transcripts[0]

    # The "User: hi" message in transcript.messages should match the
    # "User: hi" message in both ModelEvent.input lists.
    user_msg = transcript.messages[0]
    model_events = [e for e in transcript.events if isinstance(e, ModelEvent)]
    assert len(model_events) == 2
    for event in model_events:
        assert event.input[0].id == user_msg.id


@pytest.mark.asyncio
async def test_multiple_subagent_refs_each_get_their_own_span(
    tmp_path: Path,
) -> None:
    """Multiple `subagent_trajectory_ref` entries produce one span per ref."""
    for i in range(3):
        sub = Trajectory(
            session_id=f"sub-{i}",
            agent=Agent(name=f"reviewer-{i}", version="0.1.0"),
            steps=[Step(step_id=1, source="user", message="x")],
        )
        _write_trajectory(tmp_path / f"sub-{i}.json", sub)

    parent = _make_trajectory(
        [
            Step(step_id=1, source="user", message="do work"),
            Step(
                step_id=2,
                source="agent",
                message="parallel delegation",
                tool_calls=[
                    ToolCall(tool_call_id="c1", function_name="Task", arguments={})
                ],
                observation=Observation(
                    results=[
                        ObservationResult(
                            source_call_id="c1",
                            content="all done",
                            subagent_trajectory_ref=[
                                SubagentTrajectoryRef(
                                    session_id=f"sub-{i}",
                                    trajectory_path=f"sub-{i}.json",
                                )
                                for i in range(3)
                            ],
                        )
                    ]
                ),
            ),
        ]
    )
    parent_path = tmp_path / "parent.json"
    _write_trajectory(parent_path, parent)

    transcripts = [t async for t in atif(path=parent_path)]
    assert len(transcripts) == 1
    [transcript] = transcripts

    span_begins = [e for e in transcript.events if isinstance(e, SpanBeginEvent)]
    assert len(span_begins) == 3
    assert {e.name for e in span_begins} == {
        "reviewer-0",
        "reviewer-1",
        "reviewer-2",
    }


@pytest.mark.asyncio
async def test_yields_subagent_spans_for_real_terminus_2_fixture(
    fixtures_dir: Path,
) -> None:
    """A real Terminus 2 run with `subagent_trajectory_ref`s yields span events."""
    trajectory_file = (
        fixtures_dir
        / "terminus_2_hello-world-context-summarization-linear-history.trajectory.json"
    )
    transcripts = [t async for t in atif(path=trajectory_file)]
    assert len(transcripts) == 1
    [transcript] = transcripts

    span_begins = [e for e in transcript.events if isinstance(e, SpanBeginEvent)]
    span_ends = [e for e in transcript.events if isinstance(e, SpanEndEvent)]
    assert len(span_begins) == 3
    assert len(span_ends) == 3
    assert all(b.type == "agent" for b in span_begins)


@pytest.mark.asyncio
async def test_real_terminus_2_fixture_emits_compaction_event(
    fixtures_dir: Path,
) -> None:
    """The real Terminus 2 fixture's summarization handoff yields a CompactionEvent."""
    trajectory_file = (
        fixtures_dir
        / "terminus_2_hello-world-context-summarization-linear-history.trajectory.json"
    )
    transcripts = [t async for t in atif(path=trajectory_file)]
    assert len(transcripts) == 1
    [transcript] = transcripts

    compactions = [e for e in transcript.events if isinstance(e, CompactionEvent)]
    assert len(compactions) == 1
    assert compactions[0].type == "summary"
    assert compactions[0].source == "atif"
    # ATIF type/boundary preserved verbatim (not mapped onto inspect_ai's enum).
    assert compactions[0].metadata == {"type": "compaction", "boundary": "replace"}


@pytest.mark.parametrize(
    "fixture_name,expected_messages,expected_model_events",
    [
        ("openhands_hello-world.trajectory.json", 7, 2),
        ("openhands_hello-world.trajectory.no_function_calling.json", 5, 2),
    ],
)
@pytest.mark.asyncio
async def test_golden_fixture_round_trips(
    fixtures_dir: Path,
    fixture_name: str,
    expected_messages: int,
    expected_model_events: int,
) -> None:
    """Real Harbor golden fixtures convert without error and yield expected counts."""
    transcripts = [t async for t in atif(path=fixtures_dir / fixture_name)]
    assert len(transcripts) == 1
    [transcript] = transcripts

    assert transcript.source_type == ATIF_SOURCE_TYPE
    assert len(transcript.messages) == expected_messages
    assert (
        sum(1 for e in transcript.events if isinstance(e, ModelEvent))
        == expected_model_events
    )
