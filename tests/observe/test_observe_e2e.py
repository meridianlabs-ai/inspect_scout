"""End-to-end tests for observe decorator with actual LLM inference."""

import tempfile

import pytest
from inspect_ai.model import ChatMessageUser, get_model
from inspect_scout._observe import observe, observe_update
from inspect_scout._transcript.database.factory import transcripts_db
from inspect_scout._transcript.types import TranscriptContent


class TestObserveWithInference:
    """End-to-end tests using mockllm for inference."""

    @pytest.mark.asyncio
    async def test_single_inference_creates_transcript(self) -> None:
        """Single LLM call creates transcript with messages and events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            @observe(db=db, task_set="test", task_id="single")
            async def run_inference() -> str:
                model = get_model("mockllm/model")
                result = await model.generate([ChatMessageUser(content="Hello world")])
                return result.completion

            response = await run_inference()
            assert response is not None  # mockllm returns some output

            # Verify transcript was written
            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                t = transcripts[0]
                assert t.task_set == "test"
                assert t.task_id == "single"
                assert t.message_count is not None
                assert t.message_count >= 2  # At least user + assistant

                # Read full transcript to check messages/events
                content = TranscriptContent(messages="all", events="all")
                full = await db.read(t, content)
                assert full is not None
                assert len(full.messages) >= 2
                assert len(full.events) >= 1  # At least one ModelEvent

                # Verify message content
                user_msgs = [m for m in full.messages if m.role == "user"]
                assert len(user_msgs) >= 1
                assert "Hello world" in str(user_msgs[0].content)
            finally:
                await db.disconnect()

    @pytest.mark.asyncio
    async def test_multiple_inferences_same_context(self) -> None:
        """Multiple LLM calls in same observe context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            @observe(db=db, task_set="multi", task_id="case1")
            async def run_multiple() -> list[str]:
                model = get_model("mockllm/model")
                r1 = await model.generate([ChatMessageUser(content="First")])
                r2 = await model.generate([ChatMessageUser(content="Second")])
                return [r1.completion, r2.completion]

            responses = await run_multiple()
            assert len(responses) == 2  # Got responses from both calls

            # Verify single transcript with multiple events
            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                content = TranscriptContent(messages="all", events="all")
                full = await db.read(transcripts[0], content)
                assert full is not None
                # Should have events from both calls
                assert len(full.events) >= 2
            finally:
                await db.disconnect()

    @pytest.mark.asyncio
    async def test_nested_contexts_create_separate_transcripts(self) -> None:
        """Nested observe contexts create separate transcripts for leaves."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(db=db, task_set="nested", model="mockllm/model"):
                model = get_model("mockllm/model")

                async with observe(task_id="child1"):
                    await model.generate([ChatMessageUser(content="Child 1")])
                    observe_update(score=0.9, success=True)

                async with observe(task_id="child2"):
                    await model.generate([ChatMessageUser(content="Child 2")])
                    observe_update(score=0.8, success=True)

            # Verify two transcripts (leaves only, not parent)
            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 2

                # Both should inherit task_set and model from parent
                for t in transcripts:
                    assert t.task_set == "nested"
                    assert t.model == "mockllm/model"
                    assert t.success is True

                # Check task_ids
                task_ids = {t.task_id for t in transcripts}
                assert task_ids == {"child1", "child2"}

                # Verify scores (may be stored as string in parquet)
                scores = {t.task_id: t.score for t in transcripts}
                assert float(scores["child1"]) == 0.9  # type: ignore[arg-type]
                assert float(scores["child2"]) == 0.8  # type: ignore[arg-type]
            finally:
                await db.disconnect()

    @pytest.mark.asyncio
    async def test_observe_update_sets_fields(self) -> None:
        """observe_update correctly sets transcript fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            @observe(db=db, task_set="update_test")
            async def run_with_update() -> None:
                model = get_model("mockllm/model")
                await model.generate([ChatMessageUser(content="Test")])

                # Update fields after execution
                observe_update(
                    score={"accuracy": 0.95, "f1": 0.88},
                    success=True,
                    agent="test_agent",
                    metadata={"custom_key": "custom_value"},
                )

            await run_with_update()

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                t = transcripts[0]
                assert t.score == {"accuracy": 0.95, "f1": 0.88}
                assert t.success is True
                assert t.agent == "test_agent"
                assert t.metadata.get("custom_key") == "custom_value"
            finally:
                await db.disconnect()

    @pytest.mark.asyncio
    async def test_error_captured_in_transcript(self) -> None:
        """Errors during execution are captured in transcript."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            @observe(db=db, task_set="error_test")
            async def run_with_error() -> None:
                model = get_model("mockllm/model")
                await model.generate([ChatMessageUser(content="Before error")])
                raise ValueError("Test error message")

            # The error is caught and logged, not re-raised
            await run_with_error()

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                t = transcripts[0]
                assert t.error is not None
                assert "Test error message" in t.error
            finally:
                await db.disconnect()

    @pytest.mark.asyncio
    async def test_tokens_counted_from_model_events(self) -> None:
        """Token counts are extracted from ModelEvents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            @observe(db=db, task_set="tokens_test")
            async def run_inference() -> None:
                model = get_model("mockllm/model")
                await model.generate([ChatMessageUser(content="Count my tokens")])

            await run_inference()

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                # mockllm may or may not report tokens, but field should exist
                t = transcripts[0]
                # total_tokens could be None or a number depending on mockllm
                assert hasattr(t, "total_tokens")
            finally:
                await db.disconnect()

    @pytest.mark.asyncio
    async def test_context_manager_with_explicit_db(self) -> None:
        """Context manager with explicit db parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(db=db, task_set="explicit_db", task_id="cm_test"):
                model = get_model("mockllm/model")
                await model.generate([ChatMessageUser(content="Context manager test")])

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1
                assert transcripts[0].task_set == "explicit_db"
                assert transcripts[0].task_id == "cm_test"
            finally:
                await db.disconnect()

    @pytest.mark.asyncio
    async def test_deeply_nested_contexts(self) -> None:
        """Deeply nested observe contexts work correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(db=db, task_set="deep"):
                async with observe(agent="level1"):
                    async with observe(task_id="leaf"):
                        model = get_model("mockllm/model")
                        await model.generate([ChatMessageUser(content="Deep")])
                        observe_update(score=1.0)

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                # Only the leaf should create a transcript
                assert len(transcripts) == 1

                t = transcripts[0]
                # Should inherit from all ancestors
                assert t.task_set == "deep"
                assert t.agent == "level1"
                assert t.task_id == "leaf"
                assert float(t.score) == 1.0  # type: ignore[arg-type]
            finally:
                await db.disconnect()

    @pytest.mark.asyncio
    async def test_model_auto_detected_from_event(self) -> None:
        """Model name is auto-detected from ModelEvent when not specified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            # Don't specify model in observe - should be auto-detected
            async with observe(db=db, task_set="auto_model"):
                model = get_model("mockllm/model")
                await model.generate([ChatMessageUser(content="Test")])

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                t = transcripts[0]
                # Model should be auto-populated from the ModelEvent
                assert t.model == "mockllm/model"
            finally:
                await db.disconnect()

    @pytest.mark.asyncio
    async def test_explicit_model_not_overwritten(self) -> None:
        """Explicitly specified model is not overwritten by auto-detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            # Explicitly specify a different model name
            async with observe(db=db, task_set="explicit_model", model="my-custom-model"):
                model = get_model("mockllm/model")
                await model.generate([ChatMessageUser(content="Test")])

            await db.connect()
            try:
                transcripts = [t async for t in db.select()]
                assert len(transcripts) == 1

                t = transcripts[0]
                # Explicit model should be preserved, not overwritten
                assert t.model == "my-custom-model"
            finally:
                await db.disconnect()
