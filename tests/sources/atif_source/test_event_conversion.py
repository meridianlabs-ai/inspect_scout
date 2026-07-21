"""Tests for ATIF event conversion (events.py)."""

# ruff: noqa: E402  (harbor is an optional dep; imports follow importorskip)

from pathlib import Path

import pytest

pytest.importorskip("harbor")

from harbor.models.trajectories import (
    Agent,
    ContentPart,
    Metrics,
    Observation,
    ObservationResult,
    Step,
    SubagentTrajectoryRef,
    ToolCall,
    Trajectory,
)
from harbor.models.trajectories.content import ImageSource
from inspect_ai.event import (
    CompactionEvent,
    ModelEvent,
    SpanBeginEvent,
    SpanEndEvent,
)
from inspect_ai.model import (
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageTool,
    ChatMessageUser,
    ContentImage,
    ContentReasoning,
    ContentText,
)
from inspect_scout.sources._atif.events import (
    _extract_content_blocks,
    _image_as_data_uri,
    _parse_timestamp,
    step_to_messages,
    to_compaction_event,
    to_model_event,
)
from inspect_scout.sources._atif.transcripts import _create_subagent_span_events

from tests.sources.atif_source.helpers import write_trajectory

# Minimal valid 1×1 transparent PNG (used by image tests).
_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf"
    b"\xc0\xf0\x1f\x00\x05\x00\x01\xff\xa8\xd0\xc3\xb2\x00\x00\x00\x00IEND"
    b"\xaeB`\x82"
)


class TestModelEventConversion:
    """Tests for to_model_event()."""

    def test_with_metrics(self) -> None:
        """Step with metrics → ModelEvent with sentinel fields."""
        step = Step(
            step_id=1,
            source="agent",
            message="Hello there!",
            model_name="gpt-4",
            metrics=Metrics(prompt_tokens=100, completion_tokens=50, cost_usd=0.001),
        )
        msg = ChatMessageAssistant(content="Hello there!")

        result = to_model_event(step, prior_messages=[], new_messages=[msg])

        assert result is not None
        assert result.model == "gpt-4"
        assert result.tools == []
        assert result.tool_choice == "auto"
        assert result.output.usage is not None
        assert result.output.usage.input_tokens == 100
        assert result.output.usage.output_tokens == 50
        assert result.output.usage.total_tokens == 150
        assert result.output.metadata == {"atif_synthesized": True}

    def test_no_metrics(self) -> None:
        """No `Step.metrics` → returns None (no real LLM call)."""
        step = Step(step_id=1, source="agent", message="hi")
        msg = ChatMessageAssistant(content="hi")
        assert to_model_event(step, prior_messages=[], new_messages=[msg]) is None

    def test_no_assistant_msg(self) -> None:
        """No `ChatMessageAssistant` in `new_messages` → returns None."""
        step = Step(
            step_id=1,
            source="agent",
            message="x",
            metrics=Metrics(prompt_tokens=10, completion_tokens=5),
        )
        assert to_model_event(step, prior_messages=[], new_messages=[]) is None

    def test_cached_tokens_not_double_counted(self) -> None:
        """Cached tokens are excluded from `input_tokens` (harbor bundles them in)."""
        step = Step(
            step_id=1,
            source="agent",
            message="ok",
            model_name="gpt-4",
            metrics=Metrics(
                prompt_tokens=1000, completion_tokens=100, cached_tokens=800
            ),
        )
        result = to_model_event(
            step,
            prior_messages=[],
            new_messages=[ChatMessageAssistant(content="ok")],
        )
        assert result is not None
        usage = result.output.usage
        assert usage is not None
        assert usage.input_tokens == 200  # 1000 prompt - 800 cached
        assert usage.input_tokens_cache_read == 800
        assert usage.total_tokens == 1100  # 1000 + 100


class TestCompactionEventConversion:
    """Tests for to_compaction_event()."""

    def test_preserves_context_management_in_metadata(self) -> None:
        """ATIF `context_management` is kept in `metadata`; `type` stays default 'summary'."""
        step = Step(
            step_id=1,
            source="system",
            message="(compacted)",
            extra={"context_management": {"type": "compaction", "boundary": "replace"}},
        )
        result = to_compaction_event(step)
        assert isinstance(result, CompactionEvent)
        assert result.source == "atif"
        # ATIF's vocabulary isn't mapped onto inspect_ai's disjoint enum; the
        # original type/boundary are preserved in metadata instead.
        assert result.type == "summary"
        assert result.metadata == {"type": "compaction", "boundary": "replace"}

    def test_handles_missing_extra(self) -> None:
        """No `context_management` → default `type='summary'`, no tokens, no metadata."""
        step = Step(step_id=1, source="system", message="x")
        result = to_compaction_event(step)
        assert result.type == "summary"
        assert result.tokens_before is None
        assert result.tokens_after is None
        assert result.metadata is None


class TestStepToMessages:
    """Tests for step_to_messages()."""

    def test_user_source(self) -> None:
        """Step with `source='user'` → single ChatMessageUser."""
        step = Step(step_id=1, source="user", message="Hello")
        [msg] = step_to_messages(step, tool_call_funcs={})
        assert isinstance(msg, ChatMessageUser)
        assert msg.content == "Hello"

    def test_system_source(self) -> None:
        """Step with `source='system'` → single ChatMessageSystem."""
        step = Step(step_id=1, source="system", message="you are a bot")
        [msg] = step_to_messages(step, tool_call_funcs={})
        assert isinstance(msg, ChatMessageSystem)
        assert msg.content == "you are a bot"

    def test_agent_source(self) -> None:
        """Step with `source='agent'` → single ChatMessageAssistant w/ model."""
        step = Step(step_id=1, source="agent", message="ok!", model_name="gpt-4")
        [msg] = step_to_messages(step, tool_call_funcs={})
        assert isinstance(msg, ChatMessageAssistant)
        assert msg.content == "ok!"
        assert msg.model == "gpt-4"

    def test_with_tool_calls(self) -> None:
        """Step with tool_calls → ChatMessageAssistant.tool_calls populated."""
        step = Step(
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
        )
        [msg] = step_to_messages(step, tool_call_funcs={})
        assert isinstance(msg, ChatMessageAssistant)
        assert msg.tool_calls is not None
        assert msg.tool_calls[0].id == "tool_1"
        assert msg.tool_calls[0].function == "run_code"

    def test_with_observation(self) -> None:
        """Step with observation.results[] → ChatMessageTool per result."""
        step = Step(
            step_id=1,
            source="agent",
            message="",
            observation=Observation(
                results=[ObservationResult(source_call_id="tool_1", content="2")]
            ),
        )
        msgs = step_to_messages(step, tool_call_funcs={"tool_1": "run_code"})
        assert len(msgs) == 2  # ChatMessageAssistant + ChatMessageTool
        tool_msg = msgs[1]
        assert isinstance(tool_msg, ChatMessageTool)
        assert tool_msg.tool_call_id == "tool_1"
        assert tool_msg.function == "run_code"
        assert tool_msg.content == "2"


class TestExtractContentBlocks:
    """Tests for _extract_content_blocks()."""

    def test_str_returns_str(self) -> None:
        """Plain string + no reasoning → string unchanged."""
        assert _extract_content_blocks("Hello") == "Hello"

    def test_str_with_reasoning_returns_multipart(self) -> None:
        """String + reasoning → list with ContentReasoning prepended."""
        result = _extract_content_blocks(
            "answer", reasoning="Let me reason about this..."
        )
        assert isinstance(result, list)
        assert isinstance(result[0], ContentReasoning)
        assert result[0].reasoning == "Let me reason about this..."
        assert isinstance(result[1], ContentText)
        assert result[1].text == "answer"

    def test_multipart_text(self) -> None:
        """List of text ContentParts → list of ContentText."""
        parts = [
            ContentPart(type="text", text="first"),
            ContentPart(type="text", text="second"),
        ]
        result = _extract_content_blocks(parts)
        assert isinstance(result, list)
        assert all(isinstance(b, ContentText) for b in result)
        assert [b.text for b in result] == ["first", "second"]  # type: ignore[union-attr]

    def test_with_image_data_uri(self, tmp_path: Path) -> None:
        """Image ContentPart → ContentImage with base64 data URI."""
        (tmp_path / "images").mkdir()
        (tmp_path / "images" / "cat.png").write_bytes(_PNG_BYTES)
        parent_path = tmp_path / "trajectory.json"

        parts = [
            ContentPart(type="text", text="see this:"),
            ContentPart(
                type="image",
                source=ImageSource(media_type="image/png", path="images/cat.png"),
            ),
        ]
        result = _extract_content_blocks(parts, parent_path=parent_path)

        assert isinstance(result, list)
        assert isinstance(result[0], ContentText)
        assert isinstance(result[1], ContentImage)
        assert result[1].image.startswith("data:image/png;base64,")

    def test_missing_image_file(self, tmp_path: Path) -> None:
        """Image referencing missing file → skipped, only text part remains."""
        parent_path = tmp_path / "trajectory.json"
        parts = [
            ContentPart(type="text", text="see this:"),
            ContentPart(
                type="image",
                source=ImageSource(media_type="image/png", path="images/missing.png"),
            ),
        ]
        result = _extract_content_blocks(parts, parent_path=parent_path)
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], ContentText)


class TestImageAsDataUri:
    """Tests for _image_as_data_uri()."""

    def test_reads_and_encodes(self, tmp_path: Path) -> None:
        """Valid image path → base64 data URI."""
        (tmp_path / "images").mkdir()
        (tmp_path / "images" / "cat.png").write_bytes(_PNG_BYTES)
        parent_path = tmp_path / "trajectory.json"

        src = ImageSource(media_type="image/png", path="images/cat.png")
        data_uri = _image_as_data_uri(src, parent_path)
        assert data_uri is not None
        assert data_uri.startswith("data:image/png;base64,")

    def test_without_parent_returns_none(self) -> None:
        """No `parent_path` → returns None (can't resolve relative path)."""
        src = ImageSource(media_type="image/png", path="images/cat.png")
        assert _image_as_data_uri(src, parent_path=None) is None

    def test_path_escaping_trajectory_dir_returns_none(self, tmp_path: Path) -> None:
        """Both escape vectors — `../` traversal and absolute path — are refused.

        `secret.txt` exists and is readable, so a pass proves the containment check
        refuses *before* reading, not that the read merely failed.
        """
        secret = tmp_path / "secret.txt"
        secret.write_bytes(b"secret")
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        parent_path = run_dir / "trajectory.json"  # trajectory dir = run_dir/
        for bad_path in ("../secret.txt", str(secret)):
            src = ImageSource(media_type="image/png", path=bad_path)
            assert _image_as_data_uri(src, parent_path) is None


class TestCreateSubagentSpanEvents:
    """Tests for _create_subagent_span_events()."""

    def test_inlines_events_wrapped_in_agent_span(self, tmp_path: Path) -> None:
        """Subagent ref → SpanBegin + inner events + SpanEnd."""
        subagent_trajectory = Trajectory(
            session_id="sub-1",
            agent=Agent(name="reviewer", version="0.1.0"),
            steps=[
                Step(
                    step_id=1,
                    source="agent",
                    message="reviewed",
                    model_name="gpt-4",
                    metrics=Metrics(prompt_tokens=10, completion_tokens=5),
                ),
            ],
        )
        sub_path = tmp_path / "sub.json"
        write_trajectory(sub_path, subagent_trajectory)
        parent_path = tmp_path / "parent.json"

        ref = SubagentTrajectoryRef(session_id="sub-1", trajectory_path="sub.json")
        events = _create_subagent_span_events(ref, parent_path=parent_path, max_depth=5)

        span_begins = [e for e in events if isinstance(e, SpanBeginEvent)]
        span_ends = [e for e in events if isinstance(e, SpanEndEvent)]
        assert len(span_begins) == 1
        assert len(span_ends) == 1
        assert span_begins[0].id == span_ends[0].id
        assert span_begins[0].type == "agent"

        # Subagent's ModelEvent appears between the begin and end markers.
        inner = events[1:-1]
        assert any(isinstance(e, ModelEvent) for e in inner)

    def test_span_name_uses_subagent_agent_name(self, tmp_path: Path) -> None:
        """Subagent's `agent.name` → SpanBeginEvent.name."""
        subagent_trajectory = Trajectory(
            session_id="sub-1",
            agent=Agent(name="reviewer", version="0.1.0"),
            steps=[Step(step_id=1, source="user", message="x")],
        )
        write_trajectory(tmp_path / "sub.json", subagent_trajectory)
        parent_path = tmp_path / "parent.json"

        ref = SubagentTrajectoryRef(session_id="sub-1", trajectory_path="sub.json")
        events = _create_subagent_span_events(ref, parent_path=parent_path, max_depth=5)

        span_begin = next(e for e in events if isinstance(e, SpanBeginEvent))
        assert span_begin.name == "reviewer"

    def test_span_timestamps_from_subagent_steps(self, tmp_path: Path) -> None:
        """Span endpoints derive from the subagent's step timestamps, not now().

        Guards against `total_time` corruption: a `utcnow()` span end on a
        historical trajectory would stretch the span to import time.
        """
        subagent_trajectory = Trajectory(
            session_id="sub-1",
            agent=Agent(name="reviewer", version="0.1.0"),
            steps=[
                Step(
                    step_id=1,
                    source="agent",
                    message="first",
                    model_name="gpt-4",
                    metrics=Metrics(prompt_tokens=10, completion_tokens=5),
                    timestamp="2026-01-01T00:00:00Z",
                ),
                Step(
                    step_id=2,
                    source="agent",
                    message="last",
                    model_name="gpt-4",
                    metrics=Metrics(prompt_tokens=10, completion_tokens=5),
                    timestamp="2026-01-01T00:05:00Z",
                ),
            ],
        )
        write_trajectory(tmp_path / "sub.json", subagent_trajectory)
        parent_path = tmp_path / "parent.json"

        ref = SubagentTrajectoryRef(session_id="sub-1", trajectory_path="sub.json")
        events = _create_subagent_span_events(ref, parent_path=parent_path, max_depth=5)

        span_begin = next(e for e in events if isinstance(e, SpanBeginEvent))
        span_end = next(e for e in events if isinstance(e, SpanEndEvent))
        assert span_begin.timestamp == _parse_timestamp("2026-01-01T00:00:00Z")
        assert span_end.timestamp == _parse_timestamp("2026-01-01T00:05:00Z")

    def test_inner_events_are_reparented_to_span(self, tmp_path: Path) -> None:
        """Inner subagent events → span_id set to new agent span's id."""
        subagent_trajectory = Trajectory(
            session_id="sub-1",
            agent=Agent(name="reviewer", version="0.1.0"),
            steps=[
                Step(
                    step_id=1,
                    source="agent",
                    message="ran",
                    model_name="gpt-4",
                    metrics=Metrics(prompt_tokens=10, completion_tokens=5),
                ),
            ],
        )
        write_trajectory(tmp_path / "sub.json", subagent_trajectory)
        parent_path = tmp_path / "parent.json"

        ref = SubagentTrajectoryRef(session_id="sub-1", trajectory_path="sub.json")
        events = _create_subagent_span_events(ref, parent_path=parent_path, max_depth=5)

        span_begin = next(e for e in events if isinstance(e, SpanBeginEvent))
        inner_model_event = next(e for e in events if isinstance(e, ModelEvent))
        assert inner_model_event.span_id == span_begin.id

    def test_missing_subagent_file_emits_empty_span(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Missing subagent file → empty span shell + warning log."""
        parent_path = tmp_path / "parent.json"
        ref = SubagentTrajectoryRef(
            session_id="missing", trajectory_path="does-not-exist.json"
        )

        import logging

        with caplog.at_level(logging.WARNING):
            events = _create_subagent_span_events(
                ref, parent_path=parent_path, max_depth=5
            )

        span_begins = [e for e in events if isinstance(e, SpanBeginEvent)]
        span_ends = [e for e in events if isinstance(e, SpanEndEvent)]
        assert len(span_begins) == 1
        assert len(span_ends) == 1
        # No inner events between begin and end.
        assert events[1:-1] == []
        assert any("not loadable" in r.message for r in caplog.records)

    def test_max_depth_zero(self, tmp_path: Path) -> None:
        """Depth-exceeded refs → empty span shells silently."""
        parent_path = tmp_path / "parent.json"
        ref = SubagentTrajectoryRef(session_id="x", trajectory_path="sub.json")

        # max_depth=0 → silent empty shell (no file read attempted)
        events = _create_subagent_span_events(ref, parent_path=parent_path, max_depth=0)

        assert len(events) == 2  # span_begin + span_end, nothing in between
        assert isinstance(events[0], SpanBeginEvent)
        assert isinstance(events[1], SpanEndEvent)

    def test_span_ids_unique_for_pathonly_refs(self, tmp_path: Path) -> None:
        """Path-only refs (no session_id) get distinct span ids, not all `agent-None`."""
        for i in range(2):
            write_trajectory(
                tmp_path / f"sub-{i}.json",
                Trajectory(
                    session_id=f"sub-{i}",
                    agent=Agent(name=f"r{i}", version="0.1.0"),
                    steps=[Step(step_id=1, source="user", message="x")],
                ),
            )
        parent_path = tmp_path / "parent.json"
        span_ids: list[str] = []
        for i in range(2):
            ref = SubagentTrajectoryRef(
                trajectory_path=f"sub-{i}.json"
            )  # no session_id
            events = _create_subagent_span_events(
                ref, parent_path=parent_path, max_depth=5
            )
            span_ids += [e.id for e in events if isinstance(e, SpanBeginEvent)]
        assert len(span_ids) == 2
        assert len(set(span_ids)) == 2  # distinct — old `agent-{session_id}` collided
