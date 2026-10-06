"""Integration tests for the antigravity_cli() source over fixture conversations."""

from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from inspect_ai.event import (
    CompactionEvent,
    Event,
    EventTreeSpan,
    InfoEvent,
    ModelEvent,
    SpanBeginEvent,
    SpanEndEvent,
    ToolEvent,
    event_tree,
)
from inspect_ai.model import (
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageTool,
    ChatMessageUser,
)
from inspect_scout._transcript.messages import span_messages
from inspect_scout.sources import antigravity_cli

from tests.sources.antigravity_cli_source.helpers import (
    generation_blob,
    write_generation_db,
)

SIMPLE_ID = "aaaaaaaa-0000-0000-0000-000000000001"
COMPACTION_ID = "bbbbbbbb-0000-0000-0000-000000000002"
PARENT_ID = "cccccccc-0000-0000-0000-000000000003"
CHILD_ID = "dddddddd-0000-0000-0000-000000000004"
TYPED_ID = "eeeeeeee-0000-0000-0000-000000000005"
TYPED_CHILD_ID = "ffffffff-0000-0000-0000-000000000006"
TOP_LEVEL_IDS = {SIMPLE_ID, COMPACTION_ID, PARENT_ID, TYPED_ID}


@pytest.fixture
def fixtures_dir() -> Path:
    """Get the fixture data root (mirrors the on-disk Antigravity layout)."""
    return Path(__file__).parent / "fixtures" / "root"


def _agent_spans(events: list[Event]) -> list[SpanBeginEvent]:
    return [e for e in events if isinstance(e, SpanBeginEvent) and e.type == "agent"]


def _transcript_path(root: Path, conversation_id: str) -> Path:
    return (
        root
        / "brain"
        / conversation_id
        / ".system_generated"
        / "logs"
        / "transcript_full.jsonl"
    )


def _copy_fixtures(fixtures_dir: Path, tmp_path: Path) -> Path:
    """Copy the fixture root somewhere writable."""
    root = tmp_path / "root"
    shutil.copytree(fixtures_dir, root)
    return root


@pytest.mark.asyncio
async def test_top_level_excludes_subagent(fixtures_dir: Path) -> None:
    """Sub-agent conversations are not yielded at the top level."""
    transcripts = [t async for t in antigravity_cli(path=fixtures_dir)]
    ids = {t.transcript_id for t in transcripts}
    assert ids == TOP_LEVEL_IDS


@pytest.mark.asyncio
async def test_simple_conversation(fixtures_dir: Path) -> None:
    """The simple fixture round-trips: message order, model fallback, metadata."""
    transcripts = [
        t async for t in antigravity_cli(path=fixtures_dir, conversation_id=SIMPLE_ID)
    ]
    assert len(transcripts) == 1
    transcript = transcripts[0]

    # user, assistant (tool call), tool result, assistant — checkpoint 0 and
    # the malformed JSONL line are both dropped, and the tool result (whose
    # line the CLI flushed before its planner step's) is sorted back after
    # the call it pairs with
    assert transcript.message_count == 4
    assert isinstance(transcript.messages[0], ChatMessageUser)
    assert transcript.messages[0].text == "Say hello"
    assert isinstance(transcript.messages[1], ChatMessageAssistant)
    tool_message = transcript.messages[2]
    assert isinstance(tool_message, ChatMessageTool)
    assert tool_message.function == "run_command"

    model_events = [e for e in transcript.events if isinstance(e, ModelEvent)]
    assert len(model_events) == 2
    assert not any(isinstance(e, CompactionEvent) for e in transcript.events)

    # no conversations/<id>.db in fixtures: model falls back to settings chrome
    assert transcript.model == "Gemini 3.7 Flash (High)"
    assert transcript.metadata["title"] == "hello-session"
    assert transcript.total_tokens is None
    assert transcript.source_type == "antigravity_cli"
    assert transcript.date == "2026-08-21T11:23:13Z"

    # fixture steps carry real timestamps, so total_time derives from the
    # event timeline rather than falling back to import-time utcnow()
    assert transcript.total_time is not None
    assert transcript.total_time > 0


@pytest.mark.asyncio
async def test_compaction_and_resume_seam(fixtures_dir: Path) -> None:
    """A mid-conversation checkpoint → CompactionEvent; the resume seam survives."""
    transcripts = [
        t
        async for t in antigravity_cli(path=fixtures_dir, conversation_id=COMPACTION_ID)
    ]
    assert len(transcripts) == 1
    transcript = transcripts[0]

    compaction_events = [e for e in transcript.events if isinstance(e, CompactionEvent)]
    assert len(compaction_events) == 1
    assert transcript.metadata["compaction_count"] == 1

    # the checkpoint content (post-compaction context) is in the message
    # stream, matching claude_code
    assert any(
        isinstance(m, ChatMessageSystem) and "Previous Session Summary" in m.text
        for m in transcript.messages
    )

    # working_start is normalized to offsets from the first event (the
    # compaction occurs 29m55s after the first model call) — not the
    # monotonic-clock default the viewer would render as an absurd duration
    assert compaction_events[0].working_start == 1795.0
    assert all(e.working_start < 10_000 for e in transcript.events)

    # the resume seam duplicates the user request verbatim: both are preserved
    user_texts = [m.text for m in transcript.messages if isinstance(m, ChatMessageUser)]
    assert user_texts == ["Fix the bug", "Fix the bug"]

    # the generic stream-interruption error surfaces as a system message
    assert any(
        isinstance(m, ChatMessageSystem) and "stream was interrupted" in m.text
        for m in transcript.messages
    )


@pytest.mark.asyncio
async def test_compaction_model_context_all(fixtures_dir: Path) -> None:
    """compaction="all" grafts the pre-checkpoint region onto the post-checkpoint one."""
    transcripts = [
        t
        async for t in antigravity_cli(path=fixtures_dir, conversation_id=COMPACTION_ID)
    ]
    assert len(transcripts) == 1

    result = span_messages(transcripts[0].events, compaction="all")

    # each turn appears exactly once: pre-checkpoint user/assistant, then the
    # checkpoint summary and the post-checkpoint turns
    assert [m.role for m in result] == [
        "user",
        "assistant",
        "system",
        "user",
        "system",
        "assistant",
    ]
    assert result[1].text == "Working on it."
    assert "Previous Session Summary" in result[2].text
    assert result[-1].text == "Fixed."


@pytest.mark.asyncio
async def test_compaction_model_context_last(fixtures_dir: Path) -> None:
    """compaction="last" returns the checkpoint summary onward, no pre-checkpoint turns."""
    transcripts = [
        t
        async for t in antigravity_cli(path=fixtures_dir, conversation_id=COMPACTION_ID)
    ]
    assert len(transcripts) == 1

    result = span_messages(transcripts[0].events, compaction="last")

    assert [m.role for m in result] == ["system", "user", "system", "assistant"]
    assert "Previous Session Summary" in result[0].text
    assert result[-1].text == "Fixed."


@pytest.mark.asyncio
async def test_subagent_inlined_as_agent_span(fixtures_dir: Path) -> None:
    """A spawned sub-agent inlines into its parent as a named agent span."""
    transcripts = [
        t async for t in antigravity_cli(path=fixtures_dir, conversation_id=PARENT_ID)
    ]
    assert len(transcripts) == 1
    transcript = transcripts[0]

    span_begins = _agent_spans(transcript.events)
    assert len(span_begins) == 1
    assert span_begins[0].name == "Test researcher"
    assert transcript.metadata["subagent_conversation_ids"] == [CHILD_ID]

    # the child's model events are inlined between the span boundaries
    begin_index = transcript.events.index(span_begins[0])
    end_index = next(
        i
        for i, e in enumerate(transcript.events)
        if isinstance(e, SpanEndEvent) and e.id == span_begins[0].id
    )
    inlined = [
        e
        for e in transcript.events[begin_index + 1 : end_index]
        if isinstance(e, ModelEvent)
    ]
    assert len(inlined) == 2

    # ...and nest under the span in the event tree (span_id re-parenting),
    # leaving only the parent's own two model calls at the root
    tree = event_tree(transcript.events)
    [span] = [n for n in tree if isinstance(n, EventTreeSpan) and n.type == "agent"]
    assert span.name == "Test researcher"
    assert [n for n in span.children if isinstance(n, ModelEvent)] == inlined
    assert len([n for n in tree if isinstance(n, ModelEvent)]) == 2

    # child messages do not merge into the parent's message thread
    assert not any("Report sent." in (m.text or "") for m in transcript.messages)


@pytest.mark.asyncio
async def test_subagent_steps_after_final_planner_survive(fixtures_dir: Path) -> None:
    """A child's trailing tool result and error reach the timeline.

    They follow the child's last planner step, so no ModelEvent input holds
    them and the child's own message list is not kept — the tool span and
    InfoEvent inside the agent span are their only representation.
    """
    transcripts = [
        t async for t in antigravity_cli(path=fixtures_dir, conversation_id=PARENT_ID)
    ]
    assert len(transcripts) == 1
    tree = event_tree(transcripts[0].events)
    [agent] = [n for n in tree if isinstance(n, EventTreeSpan) and n.type == "agent"]

    tool_spans = [n for n in agent.children if isinstance(n, EventTreeSpan)]
    assert [s.type for s in tool_spans] == ["tool", "tool", "tool"]
    tool_events = [
        e for s in tool_spans for e in s.children if isinstance(e, ToolEvent)
    ]
    assert [e.function for e in tool_events] == [
        "list_dir",
        "grep_search",
        "send_message",
    ]
    assert isinstance(tool_events[-1].result, str)
    assert tool_events[-1].result.endswith("Message delivered")
    assert tool_events[-1].completed is not None
    assert tool_events[-1].completed.isoformat() == "2026-08-23T13:04:01+00:00"

    [error] = [n for n in agent.children if isinstance(n, InfoEvent)]
    assert error.data == (
        "Error: The stream was interrupted. Please continue the task you were "
        "working on."
    )

    # the parent's own spawn call is a tool span at the root, before the agent span
    [spawn] = [n for n in tree if isinstance(n, EventTreeSpan) and n.type == "tool"]
    assert spawn.name == "invoke_subagent"
    assert tree.index(spawn) < tree.index(agent)


@pytest.mark.asyncio
async def test_typed_tool_results(fixtures_dir: Path) -> None:
    """Typed result steps pair with their calls and trigger sub-agent inlining."""
    transcripts = [
        t async for t in antigravity_cli(path=fixtures_dir, conversation_id=TYPED_ID)
    ]
    assert len(transcripts) == 1
    transcript = transcripts[0]

    tool_messages = [m for m in transcript.messages if isinstance(m, ChatMessageTool)]
    assert [m.function for m in tool_messages] == [
        "run_command",
        "view_file",
        "invoke_subagent",
    ]
    assert tool_messages[1].text == "# Repo\nTwo packages."
    assert not any(isinstance(m, ChatMessageSystem) for m in transcript.messages)

    assert [s.name for s in _agent_spans(transcript.events)] == ["Summarizer"]
    assert transcript.metadata["subagent_conversation_ids"] == [TYPED_CHILD_ID]


def _write_transcript(root: Path, conversation_id: str, lines: list[str]) -> None:
    path = _transcript_path(root, conversation_id)
    path.parent.mkdir(parents=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.mark.asyncio
async def test_spawn_cycle_is_skipped(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A child whose spawn result names its parent is not nested into a cycle."""
    parent_id = "11111111-0000-0000-0000-000000000001"
    child_id = "22222222-0000-0000-0000-000000000002"

    def spawn(target: str) -> list[str]:
        return [
            '{"step_index":0,"source":"USER_EXPLICIT","type":"USER_INPUT",'
            '"created_at":"2026-08-25T10:00:00Z","content":"go"}',
            '{"step_index":1,"source":"MODEL","type":"PLANNER_RESPONSE",'
            '"created_at":"2026-08-25T10:00:01Z","tool_calls":[{"name":'
            '"invoke_subagent","args":{"Subagents":[{"Role":"looper"}]}}]}',
            '{"step_index":2,"source":"MODEL","type":"GENERIC",'
            '"created_at":"2026-08-25T10:00:02Z","content":"Created the following '
            f'subagents:\\n{{\\"conversationId\\": \\"{target}\\"}}"}}',
        ]

    root = tmp_path / "root"
    _write_transcript(root, parent_id, spawn(child_id))
    _write_transcript(root, child_id, spawn(parent_id))

    # each names the other, so neither is top-level: target the parent
    with caplog.at_level(logging.WARNING):
        transcripts = [
            t async for t in antigravity_cli(path=root, conversation_id=parent_id)
        ]

    assert [t.transcript_id for t in transcripts] == [parent_id]
    assert [s.id for s in _agent_spans(transcripts[0].events)] == [f"agent-{child_id}"]
    assert any("spawns an ancestor" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_ordinary_tool_output_does_not_reparent(tmp_path: Path) -> None:
    """A tool result that merely quotes a spawn result does not inline anything."""
    quoter_id = "33333333-0000-0000-0000-000000000003"
    quoted_id = "44444444-0000-0000-0000-000000000004"
    root = tmp_path / "root"
    # e.g. a run_command that greps these very logs
    _write_transcript(
        root,
        quoter_id,
        [
            '{"step_index":0,"source":"USER_EXPLICIT","type":"USER_INPUT",'
            '"created_at":"2026-08-25T10:00:00Z","content":"grep the logs"}',
            '{"step_index":1,"source":"MODEL","type":"PLANNER_RESPONSE",'
            '"created_at":"2026-08-25T10:00:01Z","tool_calls":[{"name":'
            '"run_command","args":{"CommandLine":"grep -r conversationId logs"}}]}',
            '{"step_index":2,"source":"MODEL","type":"GENERIC",'
            '"created_at":"2026-08-25T10:00:02Z","content":"Created the following '
            f'subagents:\\n{{\\"conversationId\\": \\"{quoted_id}\\"}}"}}',
        ],
    )
    _write_transcript(
        root,
        quoted_id,
        [
            '{"step_index":0,"source":"USER_EXPLICIT","type":"USER_INPUT",'
            '"created_at":"2026-08-25T11:00:00Z","content":"hi"}',
            '{"step_index":1,"source":"MODEL","type":"PLANNER_RESPONSE",'
            '"created_at":"2026-08-25T11:00:01Z","content":"hello"}',
        ],
    )

    transcripts = [t async for t in antigravity_cli(path=root)]

    assert {t.transcript_id for t in transcripts} == {quoter_id, quoted_id}
    quoter = next(t for t in transcripts if t.transcript_id == quoter_id)
    assert "subagent_conversation_ids" not in quoter.metadata
    assert _agent_spans(quoter.events) == []


def _rewrite_step(root: Path, conversation_id: str, step_index: int, line: str) -> None:
    """Replace the JSONL line for ``step_index`` with ``line``."""
    path = _transcript_path(root, conversation_id)
    marker = f'{{"step_index":{step_index},'
    lines = [
        line if raw.startswith(marker) else raw
        for raw in path.read_text(encoding="utf-8").splitlines()
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.mark.asyncio
async def test_corrupt_planner_step_leaves_attribution_unknown(
    fixtures_dir: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A result following an unparseable planner step is kept, unattributed."""
    root = _copy_fixtures(fixtures_dir, tmp_path)
    _rewrite_step(root, SIMPLE_ID, 2, '{"step_index":2,"source":"MODEL",')

    with caplog.at_level(logging.WARNING):
        transcripts = [
            t async for t in antigravity_cli(path=root, conversation_id=SIMPLE_ID)
        ]

    assert len(transcripts) == 1
    transcript = transcripts[0]
    # user, tool result (unknown call), assistant "hello"
    assert [type(m) for m in transcript.messages] == [
        ChatMessageUser,
        ChatMessageTool,
        ChatMessageAssistant,
    ]
    tool_message = transcript.messages[1]
    assert isinstance(tool_message, ChatMessageTool)
    assert tool_message.function == "unknown"
    assert tool_message.tool_call_id == "antigravity_cli_3_0"
    [tool_event] = [e for e in transcript.events if isinstance(e, ToolEvent)]
    assert tool_event.function == "unknown"
    assert isinstance(tool_event.result, str)
    assert tool_event.result.endswith("/tmp")
    # nothing was pending at the gap, so nothing is lost and nothing is logged
    assert not any("missing before" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_corrupt_tool_result_abandons_its_call(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """A call whose result line is unparseable is abandoned, not paired later."""
    root = _copy_fixtures(fixtures_dir, tmp_path)
    _rewrite_step(root, SIMPLE_ID, 3, '{"step_index":3,"source":"MODEL",')

    transcripts = [
        t async for t in antigravity_cli(path=root, conversation_id=SIMPLE_ID)
    ]

    assert len(transcripts) == 1
    transcript = transcripts[0]
    assert not any(isinstance(m, ChatMessageTool) for m in transcript.messages)
    [tool_event] = [e for e in transcript.events if isinstance(e, ToolEvent)]
    assert tool_event.function == "run_command"
    assert tool_event.result == ""
    model_events = [e for e in transcript.events if isinstance(e, ModelEvent)]
    assert len(model_events) == 2


@pytest.mark.asyncio
async def test_conversation_id_can_target_subagent(fixtures_dir: Path) -> None:
    """Passing a child's conversation_id imports it standalone."""
    transcripts = [
        t async for t in antigravity_cli(path=fixtures_dir, conversation_id=CHILD_ID)
    ]
    assert len(transcripts) == 1
    assert transcripts[0].transcript_id == CHILD_ID


@pytest.mark.asyncio
async def test_limit_truncates_yield(fixtures_dir: Path) -> None:
    """`limit` stops yielding after N transcripts."""
    transcripts = [t async for t in antigravity_cli(path=fixtures_dir, limit=1)]
    assert len(transcripts) == 1


def _backdate(root: Path, conversation_id: str) -> None:
    """Freshen every transcript's mtime, then backdate one by an hour.

    copytree preserves checkout-era mtimes, so the freshen step makes the
    backdated transcript the only one older than a 30-minute window.
    """
    for transcript_path in root.glob("brain/*/.system_generated/logs/*.jsonl"):
        os.utime(transcript_path)
    old_time = (datetime.now() - timedelta(hours=1)).timestamp()
    os.utime(_transcript_path(root, conversation_id), (old_time, old_time))


@pytest.mark.asyncio
async def test_from_time_filters_by_mtime(fixtures_dir: Path, tmp_path: Path) -> None:
    """`from_time` skips conversations whose transcript mtime is older."""
    root = _copy_fixtures(fixtures_dir, tmp_path)
    _backdate(root, SIMPLE_ID)

    from_time = datetime.now() - timedelta(minutes=30)
    transcripts = [t async for t in antigravity_cli(path=root, from_time=from_time)]

    ids = {t.transcript_id for t in transcripts}
    assert ids == TOP_LEVEL_IDS - {SIMPLE_ID}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("backdated_id", "expected_ids"),
    [
        # parent in the window, child outside: the child is still inlined
        (CHILD_ID, TOP_LEVEL_IDS),
        # child in the window, parent outside: the child is still withheld
        (PARENT_ID, TOP_LEVEL_IDS - {PARENT_ID}),
    ],
)
async def test_time_window_does_not_split_subagents(
    fixtures_dir: Path, tmp_path: Path, backdated_id: str, expected_ids: set[str]
) -> None:
    """Sub-agent linkage is resolved outside the time window."""
    root = _copy_fixtures(fixtures_dir, tmp_path)
    _backdate(root, backdated_id)

    from_time = datetime.now() - timedelta(minutes=30)
    transcripts = [t async for t in antigravity_cli(path=root, from_time=from_time)]

    assert {t.transcript_id for t in transcripts} == expected_ids
    parent = next((t for t in transcripts if t.transcript_id == PARENT_ID), None)
    if parent is not None:
        assert [s.name for s in _agent_spans(parent.events)] == ["Test researcher"]


@pytest.mark.asyncio
async def test_nonexistent_path_yields_nothing(tmp_path: Path) -> None:
    """A path that doesn't exist yields zero transcripts (logged, not raised)."""
    transcripts = [t async for t in antigravity_cli(path=tmp_path / "missing")]
    assert transcripts == []


@pytest.mark.asyncio
async def test_nonexistent_conversation_id_warns(
    fixtures_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A conversation_id matching nothing yields zero transcripts and warns."""
    with caplog.at_level(logging.WARNING):
        transcripts = [
            t
            async for t in antigravity_cli(
                path=fixtures_dir,
                conversation_id="99999999-0000-0000-0000-000000000009",
            )
        ]
    assert transcripts == []
    assert any("matched no conversations" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_undecodable_transcript_is_skipped(
    fixtures_dir: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Non-UTF-8 bytes in one transcript skip that conversation, not the import."""
    root = _copy_fixtures(fixtures_dir, tmp_path)
    _transcript_path(root, SIMPLE_ID).write_bytes(b"\xff\xfe not utf-8\n")

    with caplog.at_level(logging.WARNING):
        transcripts = [t async for t in antigravity_cli(path=root)]

    assert {t.transcript_id for t in transcripts} == TOP_LEVEL_IDS - {SIMPLE_ID}
    assert any("Skipping unreadable file" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_undecodable_annotation_omits_title(
    fixtures_dir: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Non-UTF-8 bytes in an annotation file drop that title, not the import."""
    root = _copy_fixtures(fixtures_dir, tmp_path)
    (root / "annotations" / f"{SIMPLE_ID}.pbtxt").write_bytes(b"\xff\xfe not utf-8\n")

    with caplog.at_level(logging.WARNING):
        transcripts = [t async for t in antigravity_cli(path=root)]

    assert {t.transcript_id for t in transcripts} == TOP_LEVEL_IDS
    simple = next(t for t in transcripts if t.transcript_id == SIMPLE_ID)
    assert "title" not in simple.metadata
    assert any("Failed to read" in r.message for r in caplog.records)


@pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses directory permissions")
@pytest.mark.asyncio
async def test_unreadable_conversation_dir_is_skipped(
    fixtures_dir: Path, tmp_path: Path
) -> None:
    """An unreadable conversation directory skips that conversation, not the import."""
    root = _copy_fixtures(fixtures_dir, tmp_path)
    conv_dir = root / "brain" / SIMPLE_ID
    conv_dir.chmod(0o000)
    try:
        transcripts = [t async for t in antigravity_cli(path=root)]
    finally:
        conv_dir.chmod(0o755)

    assert {t.transcript_id for t in transcripts} == TOP_LEVEL_IDS - {SIMPLE_ID}


@pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses directory permissions")
@pytest.mark.asyncio
async def test_unreadable_brain_dir_yields_nothing(
    fixtures_dir: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """An unreadable brain/ directory yields zero transcripts (logged, not raised)."""
    root = _copy_fixtures(fixtures_dir, tmp_path)
    brain = root / "brain"
    brain.chmod(0o000)
    try:
        with caplog.at_level(logging.WARNING):
            transcripts = [t async for t in antigravity_cli(path=root)]
    finally:
        brain.chmod(0o755)

    assert transcripts == []
    assert any("Cannot list" in r.message for r in caplog.records)


def _root_with_generation_db(fixtures_dir: Path, tmp_path: Path) -> Path:
    """Copy the fixture root and add a gen_metadata db for the simple fixture."""
    root = tmp_path / "root"
    shutil.copytree(fixtures_dir, root)
    # one row per PLANNER_RESPONSE step (the simple fixture has two)
    write_generation_db(
        root / "conversations" / f"{SIMPLE_ID}.db",
        [
            generation_blob(
                "gemini-test", prefix=1000, fresh=100, cached=30, output=20
            ),
            generation_blob("gemini-test", prefix=1000, fresh=10, cached=150, output=5),
        ],
    )
    return root


@pytest.mark.asyncio
async def test_model_extraction(fixtures_dir: Path, tmp_path: Path) -> None:
    """Wire model id from generation metadata wins over the settings chrome."""
    root = _root_with_generation_db(fixtures_dir, tmp_path)
    transcripts = [
        t async for t in antigravity_cli(path=root, conversation_id=SIMPLE_ID)
    ]
    assert len(transcripts) == 1
    assert transcripts[0].model == "gemini-test"


@pytest.mark.asyncio
async def test_token_counting(fixtures_dir: Path, tmp_path: Path) -> None:
    """`total_tokens` sums the decoded per-generation usage."""
    root = _root_with_generation_db(fixtures_dir, tmp_path)
    transcripts = [
        t async for t in antigravity_cli(path=root, conversation_id=SIMPLE_ID)
    ]
    assert len(transcripts) == 1
    transcript = transcripts[0]

    # totals: (1000+100+30+20) + (1000+10+150+5)
    assert transcript.total_tokens == 2315

    model_events = [e for e in transcript.events if isinstance(e, ModelEvent)]
    usage = model_events[0].output.usage
    assert usage is not None
    assert usage.input_tokens == 1100
    assert usage.input_tokens_cache_read == 30
    assert usage.output_tokens == 20
    assert usage.total_tokens == 1150
