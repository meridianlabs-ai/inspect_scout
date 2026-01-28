"""Database integration tests for Logfire transcripts.

Tests the full pipeline: fetch ALL transcripts from Logfire project,
insert into ParquetTranscriptsDB, and verify round-trip preserves all data.

This is a comprehensive end-to-end test that validates the complete flow
from Logfire API to persisted database and back.
"""

from pathlib import Path
from typing import Any

import pytest
from inspect_ai.event import ModelEvent, SpanBeginEvent, SpanEndEvent, ToolEvent
from inspect_scout._query import Query
from inspect_scout._transcript.database.parquet import ParquetTranscriptsDB
from inspect_scout._transcript.types import TranscriptContent

from tests.sources.logfire_source.bootstrap import OPTIONAL_TRACES, REQUIRED_TRACES
from tests.sources.logfire_source.conftest import skip_if_no_logfire

# =============================================================================
# End-to-End Database Round-Trip Test
# =============================================================================


@skip_if_no_logfire
@pytest.mark.asyncio
async def test_logfire_full_project_db_roundtrip(tmp_path: Path) -> None:
    """Fetch ALL transcripts from Logfire, write to DB, verify round-trip.

    This comprehensive test validates the complete pipeline:
    1. Fetch all scout-test traces from Logfire project
    2. Insert all transcripts into ParquetTranscriptsDB
    3. Query DB and verify each transcript is present
    4. Read full content and verify messages/events preserved

    Expected traces (from bootstrap.py):
    - OpenAI traces: simple, tools, multiturn
    - Anthropic traces: simple, tools, multiturn
    - Google GenAI: simple (optional)
    - Pydantic AI: simple, tools, openai-multiturn, anthropic-multiturn, google-multiturn
    """
    from inspect_scout.sources._logfire import logfire

    # -------------------------------------------------------------------------
    # Step 1: Fetch all transcripts from Logfire
    # -------------------------------------------------------------------------
    transcripts: list[Any] = []
    async for transcript in logfire(
        filter="span_name LIKE 'scout-test-%'",
    ):
        transcripts.append(transcript)

    # Verify we got transcripts
    assert len(transcripts) > 0, (
        "No transcripts found with span_name LIKE 'scout-test-%'. "
        "Run bootstrap first: python -m tests.sources.logfire_source.bootstrap"
    )

    # Track which expected traces we found
    expected_traces = set(REQUIRED_TRACES + OPTIONAL_TRACES)
    found_traces = {t.task_id for t in transcripts}
    missing_traces = expected_traces - found_traces

    # Report missing traces but allow test to proceed
    if missing_traces:
        print(f"Note: Missing traces (may need bootstrap): {missing_traces}")

    # We should have at least the required traces
    found_required = expected_traces & found_traces
    assert len(found_required) >= len(REQUIRED_TRACES) - 1, (
        f"Expected most required traces. Found {len(found_required)}, "
        f"expected at least {len(REQUIRED_TRACES) - 1}. Missing: {missing_traces}"
    )

    # -------------------------------------------------------------------------
    # Step 2: Insert all transcripts into database
    # -------------------------------------------------------------------------
    db_path = tmp_path / "logfire_roundtrip_db"
    db_path.mkdir(parents=True, exist_ok=True)

    db = ParquetTranscriptsDB(str(db_path))
    await db.connect()

    try:
        await db.insert(transcripts)

        # -------------------------------------------------------------------------
        # Step 3: Query DB and verify all transcripts present
        # -------------------------------------------------------------------------
        db_results = [info async for info in db.select(Query())]

        assert len(db_results) == len(transcripts), (
            f"Expected {len(transcripts)} transcripts in DB, got {len(db_results)}"
        )

        # Build lookup by transcript_id
        db_by_id = {r.transcript_id: r for r in db_results}

        for original in transcripts:
            assert original.transcript_id in db_by_id, (
                f"Transcript {original.transcript_id} not found in DB"
            )

            db_record = db_by_id[original.transcript_id]

            # Verify scalar fields preserved
            assert db_record.source_type == "logfire", (
                f"source_type mismatch for {original.transcript_id}"
            )
            assert db_record.task_id == original.task_id, (
                f"task_id mismatch for {original.transcript_id}"
            )

            # Verify source_uri preserved
            if original.source_uri:
                assert db_record.source_uri is not None, (
                    f"source_uri lost for {original.transcript_id}"
                )
                assert "logfire" in db_record.source_uri.lower(), (
                    f"source_uri invalid for {original.transcript_id}"
                )

            # Verify model preserved
            if original.model:
                assert db_record.model == original.model, (
                    f"model mismatch for {original.transcript_id}: "
                    f"expected {original.model}, got {db_record.model}"
                )

            # Verify metrics preserved
            assert db_record.message_count == original.message_count, (
                f"message_count mismatch for {original.transcript_id}"
            )
            if original.total_tokens:
                assert db_record.total_tokens == original.total_tokens, (
                    f"total_tokens mismatch for {original.transcript_id}"
                )

        # -------------------------------------------------------------------------
        # Step 4: Read full content and verify messages/events
        # -------------------------------------------------------------------------
        for original in transcripts:
            db_record = db_by_id[original.transcript_id]

            # Read full content (messages and events)
            content_spec = TranscriptContent(messages="all", events="all")
            full_record = await db.read(db_record, content_spec)

            # Verify message count matches
            assert len(full_record.messages) == len(original.messages), (
                f"Message count mismatch for {original.transcript_id}: "
                f"expected {len(original.messages)}, got {len(full_record.messages)}"
            )

            # Verify message roles preserved
            original_roles = [m.role for m in original.messages]
            db_roles = [m.role for m in full_record.messages]
            assert original_roles == db_roles, (
                f"Message roles mismatch for {original.transcript_id}: "
                f"expected {original_roles}, got {db_roles}"
            )

            # Verify event count matches
            assert len(full_record.events) == len(original.events), (
                f"Event count mismatch for {original.transcript_id}: "
                f"expected {len(original.events)}, got {len(full_record.events)}"
            )

            # Verify event types preserved
            original_event_types = [type(e).__name__ for e in original.events]
            db_event_types = [type(e).__name__ for e in full_record.events]
            assert original_event_types == db_event_types, (
                f"Event types mismatch for {original.transcript_id}: "
                f"expected {original_event_types}, got {db_event_types}"
            )

    finally:
        await db.disconnect()


@skip_if_no_logfire
@pytest.mark.asyncio
async def test_logfire_openai_traces_db_roundtrip(tmp_path: Path) -> None:
    """Test OpenAI traces survive DB round-trip.

    Verifies simple, tools, and multiturn traces.
    """
    from inspect_scout.sources._logfire import logfire

    # Fetch OpenAI traces
    openai_trace_names = [
        "scout-test-openai-simple-v2",
        "scout-test-openai-tools-v2",
        "scout-test-openai-multiturn-v2",
    ]

    transcripts: list[Any] = []
    for trace_name in openai_trace_names:
        async for transcript in logfire(
            filter=f"span_name = '{trace_name}'",
            limit=1,
        ):
            transcripts.append(transcript)
            break

    if len(transcripts) == 0:
        pytest.skip("No OpenAI traces found - run bootstrap first")

    # Insert into DB
    db_path = tmp_path / "openai_traces_db"
    db_path.mkdir(parents=True, exist_ok=True)

    db = ParquetTranscriptsDB(str(db_path))
    await db.connect()

    try:
        await db.insert(transcripts)

        # Verify round-trip
        db_results = [info async for info in db.select(Query())]
        assert len(db_results) == len(transcripts)

        # Verify each transcript has expected structure
        for db_record in db_results:
            content_spec = TranscriptContent(messages="all", events="all")
            full_record = await db.read(db_record, content_spec)

            # All traces should have ModelEvents
            model_events = [e for e in full_record.events if isinstance(e, ModelEvent)]
            assert len(model_events) >= 1, f"Expected ModelEvent in {db_record.task_id}"

            # Verify model name captured (should be OpenAI)
            assert model_events[0].model is not None, (
                f"Model name missing in {db_record.task_id}"
            )
            assert "gpt" in model_events[0].model.lower(), (
                f"Expected GPT model in {db_record.task_id}"
            )

            # Verify messages have content
            assert len(full_record.messages) >= 2, (
                f"Expected at least 2 messages in {db_record.task_id}"
            )

    finally:
        await db.disconnect()


@skip_if_no_logfire
@pytest.mark.asyncio
async def test_logfire_anthropic_traces_db_roundtrip(tmp_path: Path) -> None:
    """Test Anthropic traces survive DB round-trip."""
    from inspect_scout.sources._logfire import logfire

    # Fetch Anthropic traces
    anthropic_trace_names = [
        "scout-test-anthropic-simple-v2",
        "scout-test-anthropic-tools-v2",
        "scout-test-anthropic-multiturn-v2",
    ]

    transcripts: list[Any] = []
    for trace_name in anthropic_trace_names:
        async for transcript in logfire(
            filter=f"span_name = '{trace_name}'",
            limit=1,
        ):
            transcripts.append(transcript)
            break

    if len(transcripts) == 0:
        pytest.skip("No Anthropic traces found - run bootstrap first")

    # Insert into DB
    db_path = tmp_path / "anthropic_traces_db"
    db_path.mkdir(parents=True, exist_ok=True)

    db = ParquetTranscriptsDB(str(db_path))
    await db.connect()

    try:
        await db.insert(transcripts)

        # Verify round-trip
        db_results = [info async for info in db.select(Query())]
        assert len(db_results) == len(transcripts)

        # Verify each transcript has expected structure
        for db_record in db_results:
            content_spec = TranscriptContent(messages="all", events="all")
            full_record = await db.read(db_record, content_spec)

            # All traces should have ModelEvents
            model_events = [e for e in full_record.events if isinstance(e, ModelEvent)]
            assert len(model_events) >= 1, f"Expected ModelEvent in {db_record.task_id}"

            # Verify model name captured (should be Claude)
            assert model_events[0].model is not None, (
                f"Model name missing in {db_record.task_id}"
            )
            assert "claude" in model_events[0].model.lower(), (
                f"Expected Claude model in {db_record.task_id}"
            )

    finally:
        await db.disconnect()


@skip_if_no_logfire
@pytest.mark.asyncio
async def test_logfire_pydantic_ai_traces_db_roundtrip(tmp_path: Path) -> None:
    """Test Pydantic AI traces survive DB round-trip.

    Pydantic AI traces have hierarchical structure (agent -> LLM)
    and must preserve span relationships.
    """
    from inspect_scout.sources._logfire import logfire

    # Fetch Pydantic AI traces
    pydantic_ai_trace_names = [
        "scout-test-pydantic-ai-simple-v2",
        "scout-test-pydantic-ai-tools-v2",
        "scout-test-pydantic-ai-openai-multiturn-v2",
        "scout-test-pydantic-ai-anthropic-multiturn-v2",
    ]

    transcripts: list[Any] = []
    for trace_name in pydantic_ai_trace_names:
        async for transcript in logfire(
            filter=f"span_name = '{trace_name}'",
            limit=1,
        ):
            transcripts.append(transcript)
            break

    if len(transcripts) == 0:
        pytest.skip("No Pydantic AI traces found - run bootstrap first")

    # Insert into DB
    db_path = tmp_path / "pydantic_ai_traces_db"
    db_path.mkdir(parents=True, exist_ok=True)

    db = ParquetTranscriptsDB(str(db_path))
    await db.connect()

    try:
        await db.insert(transcripts)

        # Verify round-trip
        db_results = [info async for info in db.select(Query())]
        assert len(db_results) == len(transcripts)

        # Verify each transcript has expected structure
        for db_record in db_results:
            content_spec = TranscriptContent(messages="all", events="all")
            full_record = await db.read(db_record, content_spec)

            # Pydantic AI traces should have span events
            span_begins = [
                e for e in full_record.events if isinstance(e, SpanBeginEvent)
            ]
            span_ends = [e for e in full_record.events if isinstance(e, SpanEndEvent)]

            # May have spans from agent structure
            if span_begins:
                assert len(span_ends) >= len(span_begins), (
                    f"Unbalanced spans in {db_record.task_id}"
                )

            # Should have ModelEvents
            model_events = [e for e in full_record.events if isinstance(e, ModelEvent)]
            assert len(model_events) >= 1, f"Expected ModelEvent in {db_record.task_id}"

    finally:
        await db.disconnect()


@skip_if_no_logfire
@pytest.mark.asyncio
async def test_logfire_tool_calls_preserved(tmp_path: Path) -> None:
    """Verify tool_calls in assistant messages survive DB round-trip.

    Tool calls are complex structures that must be properly serialized
    and deserialized through the database layer.
    """
    from inspect_scout.sources._logfire import logfire

    # Fetch a trace with tool calls (OpenAI tools trace)
    transcript = None
    async for t in logfire(
        filter="span_name = 'scout-test-openai-tools-v2'",
        limit=1,
    ):
        transcript = t
        break

    if transcript is None:
        pytest.skip("OpenAI tools trace not found - run bootstrap first")

    # Find assistant message with tool_calls in original
    original_tool_call_msgs = [
        m
        for m in transcript.messages
        if m.role == "assistant" and hasattr(m, "tool_calls") and m.tool_calls
    ]
    assert len(original_tool_call_msgs) >= 1, "Test data should have tool_calls"

    original_tool_calls = original_tool_call_msgs[0].tool_calls
    assert original_tool_calls is not None
    original_tc = original_tool_calls[0]

    # Insert into DB
    db_path = tmp_path / "tool_calls_db"
    db_path.mkdir(parents=True, exist_ok=True)

    db = ParquetTranscriptsDB(str(db_path))
    await db.connect()

    try:
        await db.insert([transcript])

        # Read back
        db_results = [info async for info in db.select(Query())]
        assert len(db_results) == 1

        content_spec = TranscriptContent(messages="all", events=None)
        full_record = await db.read(db_results[0], content_spec)

        # Find assistant message with tool_calls in DB result
        db_tool_call_msgs = [
            m
            for m in full_record.messages
            if m.role == "assistant" and hasattr(m, "tool_calls") and m.tool_calls
        ]
        assert len(db_tool_call_msgs) >= 1, "tool_calls lost in DB round-trip"

        db_tool_calls = db_tool_call_msgs[0].tool_calls
        assert db_tool_calls is not None
        db_tc = db_tool_calls[0]

        # Verify tool_call structure preserved
        assert db_tc.id == original_tc.id, "tool_call id mismatch"
        assert db_tc.function == original_tc.function, "tool_call function mismatch"
        assert db_tc.arguments == original_tc.arguments, "tool_call arguments mismatch"

    finally:
        await db.disconnect()


@skip_if_no_logfire
@pytest.mark.asyncio
async def test_logfire_pydantic_ai_tool_calls_preserved(tmp_path: Path) -> None:
    """Verify tool_calls from Pydantic AI traces survive DB round-trip."""
    from inspect_scout.sources._logfire import logfire

    # Fetch Pydantic AI tools trace
    transcript = None
    async for t in logfire(
        filter="span_name = 'scout-test-pydantic-ai-tools-v2'",
        limit=1,
    ):
        transcript = t
        break

    if transcript is None:
        pytest.skip("Pydantic AI tools trace not found - run bootstrap first")

    # Find tool messages
    tool_messages = [m for m in transcript.messages if m.role == "tool"]
    assert len(tool_messages) >= 1, "Test data should have tool results"

    # Insert into DB
    db_path = tmp_path / "pydantic_ai_tool_calls_db"
    db_path.mkdir(parents=True, exist_ok=True)

    db = ParquetTranscriptsDB(str(db_path))
    await db.connect()

    try:
        await db.insert([transcript])

        # Read back
        db_results = [info async for info in db.select(Query())]
        assert len(db_results) == 1

        content_spec = TranscriptContent(messages="all", events="all")
        full_record = await db.read(db_results[0], content_spec)

        # Verify tool messages preserved
        db_tool_messages = [m for m in full_record.messages if m.role == "tool"]
        assert len(db_tool_messages) >= 1, "tool messages lost in DB round-trip"

        # Verify ToolEvents preserved
        tool_events = [e for e in full_record.events if isinstance(e, ToolEvent)]
        assert len(tool_events) >= 1, "ToolEvents lost in DB round-trip"

    finally:
        await db.disconnect()


@skip_if_no_logfire
@pytest.mark.asyncio
async def test_logfire_metadata_preserved(tmp_path: Path) -> None:
    """Verify transcript metadata survives DB round-trip."""
    from inspect_scout.sources._logfire import logfire

    # Fetch any trace
    transcript = None
    async for t in logfire(
        filter="span_name LIKE 'scout-test-%'",
        limit=1,
    ):
        transcript = t
        break

    if transcript is None:
        pytest.skip("No transcripts found - run bootstrap first")

    # Insert into DB
    db_path = tmp_path / "metadata_db"
    db_path.mkdir(parents=True, exist_ok=True)

    db = ParquetTranscriptsDB(str(db_path))
    await db.connect()

    try:
        await db.insert([transcript])

        # Read back
        db_results = [info async for info in db.select(Query())]
        assert len(db_results) == 1

        db_record = db_results[0]

        # Verify key metadata fields
        assert db_record.source_type == transcript.source_type
        assert db_record.source_id == transcript.source_id
        assert db_record.task_id == transcript.task_id
        assert db_record.model == transcript.model

        # Verify metadata dict preserved if present
        if transcript.metadata:
            assert db_record.metadata is not None, "metadata lost in round-trip"

    finally:
        await db.disconnect()


@skip_if_no_logfire
@pytest.mark.asyncio
async def test_logfire_multiturn_messages_preserved(tmp_path: Path) -> None:
    """Verify multi-turn conversations preserve all messages through DB.

    Multi-turn traces should have multiple user/assistant message pairs.
    """
    from inspect_scout.sources._logfire import logfire

    # Fetch a multi-turn trace
    transcript = None
    async for t in logfire(
        filter="span_name = 'scout-test-openai-multiturn-v2'",
        limit=1,
    ):
        transcript = t
        break

    if transcript is None:
        pytest.skip("OpenAI multiturn trace not found - run bootstrap first")

    # Count messages by role
    original_user_count = sum(1 for m in transcript.messages if m.role == "user")
    original_assistant_count = sum(
        1 for m in transcript.messages if m.role == "assistant"
    )

    # Should have multiple turns
    assert original_user_count >= 3, "Expected at least 3 user messages"
    assert original_assistant_count >= 3, "Expected at least 3 assistant messages"

    # Insert into DB
    db_path = tmp_path / "multiturn_db"
    db_path.mkdir(parents=True, exist_ok=True)

    db = ParquetTranscriptsDB(str(db_path))
    await db.connect()

    try:
        await db.insert([transcript])

        # Read back
        db_results = [info async for info in db.select(Query())]
        assert len(db_results) == 1

        content_spec = TranscriptContent(messages="all", events=None)
        full_record = await db.read(db_results[0], content_spec)

        # Verify message counts preserved
        db_user_count = sum(1 for m in full_record.messages if m.role == "user")
        db_assistant_count = sum(
            1 for m in full_record.messages if m.role == "assistant"
        )

        assert db_user_count == original_user_count, (
            f"User message count mismatch: {db_user_count} vs {original_user_count}"
        )
        assert db_assistant_count == original_assistant_count, (
            f"Assistant message count mismatch: "
            f"{db_assistant_count} vs {original_assistant_count}"
        )

    finally:
        await db.disconnect()
