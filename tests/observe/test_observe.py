"""Tests for the observe decorator and context manager."""

import tempfile
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from inspect_scout._observe import observe, observe_update
from inspect_scout._observe._observe import _build_transcript, _merge_transcript_info
from inspect_scout._observe.context import ObserveContext, current_observe_context
from inspect_scout._transcript.database.factory import transcripts_db
from inspect_scout._transcript.types import TranscriptInfo


class TestMergeTranscriptInfo:
    """Tests for _merge_transcript_info function."""

    def test_empty_merge(self) -> None:
        """Merging with no inputs creates empty TranscriptInfo."""
        result = _merge_transcript_info(None, None)
        assert result.transcript_id == ""
        assert result.task_set is None

    def test_parent_values_inherited(self) -> None:
        """Values from parent are inherited."""
        parent = TranscriptInfo(
            transcript_id="parent-id",
            task_set="parent-task-set",
            model="parent-model",
        )
        result = _merge_transcript_info(parent, None)
        assert result.task_set == "parent-task-set"
        assert result.model == "parent-model"

    def test_explicit_info_overrides_parent(self) -> None:
        """Explicit info param overrides parent values."""
        parent = TranscriptInfo(
            transcript_id="parent-id",
            task_set="parent-task-set",
            model="parent-model",
        )
        explicit = TranscriptInfo(
            transcript_id="explicit-id",
            task_set="explicit-task-set",
        )
        result = _merge_transcript_info(parent, explicit)
        # Explicit overrides
        assert result.task_set == "explicit-task-set"
        # Parent value retained when not overridden
        assert result.model == "parent-model"

    def test_kwargs_override_all(self) -> None:
        """Keyword args have highest precedence."""
        parent = TranscriptInfo(
            transcript_id="parent-id",
            task_set="parent-task-set",
        )
        explicit = TranscriptInfo(
            transcript_id="explicit-id",
            task_set="explicit-task-set",
        )
        result = _merge_transcript_info(
            parent, explicit, task_set="kwarg-task-set", model="kwarg-model"
        )
        assert result.task_set == "kwarg-task-set"
        assert result.model == "kwarg-model"


class TestObserveDecorator:
    """Tests for observe decorator usage patterns."""

    @pytest.mark.asyncio
    async def test_decorator_without_parens(self) -> None:
        """@observe without parentheses works for async functions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            @observe
            async def my_function() -> str:
                return "hello"

            # Patch the project db to use our temp db
            with patch(
                "inspect_scout._observe._observe._get_project_db", return_value=db
            ):
                result = await my_function()
                assert result == "hello"

    @pytest.mark.asyncio
    async def test_decorator_with_empty_parens(self) -> None:
        """@observe() with empty parentheses works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            @observe()
            async def my_function() -> str:
                return "world"

            with patch(
                "inspect_scout._observe._observe._get_project_db", return_value=db
            ):
                result = await my_function()
                assert result == "world"

    @pytest.mark.asyncio
    async def test_decorator_with_args(self) -> None:
        """@observe(task_set="x") with arguments works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            @observe(task_set="test-task-set", task_id="case-1")
            async def my_function() -> str:
                ctx = current_observe_context()
                assert ctx is not None
                assert ctx.info.task_set == "test-task-set"
                assert ctx.info.task_id == "case-1"
                return "test"

            with patch(
                "inspect_scout._observe._observe._get_project_db", return_value=db
            ):
                result = await my_function()
                assert result == "test"

    def test_decorator_on_sync_function_raises(self) -> None:
        """@observe on sync function raises TypeError."""
        with pytest.raises(TypeError, match="can only decorate async functions"):

            @observe  # type: ignore[arg-type]
            def sync_function() -> str:
                return "sync"


class TestObserveContextManager:
    """Tests for observe context manager usage."""

    @pytest.mark.asyncio
    async def test_context_manager_basic(self) -> None:
        """Basic context manager usage works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            with patch(
                "inspect_scout._observe._observe._get_project_db", return_value=db
            ):
                async with observe() as ctx:
                    assert isinstance(ctx, ObserveContext)
                    assert ctx.is_root is True

    @pytest.mark.asyncio
    async def test_context_manager_with_args(self) -> None:
        """Context manager with arguments works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            with patch(
                "inspect_scout._observe._observe._get_project_db", return_value=db
            ):
                async with observe(task_set="ctx-test", agent="test-agent") as ctx:
                    assert ctx.info.task_set == "ctx-test"
                    assert ctx.info.agent == "test-agent"

    @pytest.mark.asyncio
    async def test_context_manager_with_explicit_db(self) -> None:
        """Context manager with explicit db works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(db=db, task_set="explicit-db-test") as ctx:
                assert ctx.db is db
                assert ctx.info.task_set == "explicit-db-test"


class TestObserveNesting:
    """Tests for nested observe contexts."""

    @pytest.mark.asyncio
    async def test_nested_contexts(self) -> None:
        """Nested observe contexts work correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(db=db, task_set="outer", model="gpt-4") as outer_ctx:
                assert outer_ctx.is_root is True
                assert outer_ctx.info.task_set == "outer"

                async with observe(task_id="inner") as inner_ctx:
                    assert inner_ctx.is_root is False
                    # Inherits from parent
                    assert inner_ctx.info.task_set == "outer"
                    assert inner_ctx.info.model == "gpt-4"
                    # Sets its own value
                    assert inner_ctx.info.task_id == "inner"
                    # Parent reference is correct
                    assert inner_ctx.parent is outer_ctx

                # After inner exits, outer's had_children is True
                assert outer_ctx.had_children is True

    @pytest.mark.asyncio
    async def test_db_on_inner_raises(self) -> None:
        """Setting db on non-root observe logs error and continues.

        Per the design, errors in observe contexts are caught, logged as
        warnings, and saved to the transcript's error field.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            db1 = transcripts_db(tmpdir)
            db2 = transcripts_db(tmpdir + "/other")

            with patch("inspect_scout._observe._observe.logger") as mock_logger:
                async with observe(db=db1):
                    async with observe(db=db2):
                        # This line should not execute because ValueError is raised
                        # before yield, but the error is caught by outer context
                        pass

                # Verify the error was logged
                mock_logger.warning.assert_called()
                warning_msg = mock_logger.warning.call_args[0][0]
                assert "outermost observe" in warning_msg


class TestObserveUpdate:
    """Tests for observe_update function."""

    @pytest.mark.asyncio
    async def test_update_fields(self) -> None:
        """observe_update updates TranscriptInfo fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(db=db, task_set="test") as ctx:
                observe_update(score=0.95, success=True, agent="updated-agent")
                assert ctx.info.score == 0.95
                assert ctx.info.success is True
                assert ctx.info.agent == "updated-agent"

    @pytest.mark.asyncio
    async def test_update_metadata_merges(self) -> None:
        """observe_update merges metadata instead of replacing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(db=db, metadata={"key1": "value1"}) as ctx:
                observe_update(metadata={"key2": "value2"})
                assert ctx.info.metadata == {"key1": "value1", "key2": "value2"}

    def test_update_outside_context_raises(self) -> None:
        """observe_update outside observe context raises RuntimeError."""
        with pytest.raises(RuntimeError, match="outside of an observe context"):
            observe_update(score=1.0)


class TestLeafDetection:
    """Tests for implicit leaf detection."""

    @pytest.mark.asyncio
    async def test_single_observe_is_leaf(self) -> None:
        """Single observe without children is a leaf."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(db=db):
                pass

            # After exit, had_children should be False (it was a leaf)
            # Note: we can't check this directly after the context exits
            # because the context is reset. We verify through side effects.

    @pytest.mark.asyncio
    async def test_parent_not_leaf(self) -> None:
        """Parent observe with children is not a leaf."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)
            leaf_count = 0

            # Create a mock insert to count leaf writes
            original_insert = db.insert

            async def mock_insert(
                transcripts: Any,
                session_id: str | None = None,
                commit: bool = True,
            ) -> None:
                nonlocal leaf_count
                leaf_count += 1
                await original_insert(transcripts, session_id=session_id, commit=commit)

            db.insert = mock_insert  # type: ignore[method-assign]

            async with observe(db=db, task_set="parent"):
                async with observe(task_id="child1"):
                    pass
                async with observe(task_id="child2"):
                    pass

            # Should have exactly 2 leaf writes (the two children)
            assert leaf_count == 2


class TestTranscriptBuilding:
    """Tests for _build_transcript function."""

    def test_build_transcript_basic(self) -> None:
        """_build_transcript creates transcript with correct fields."""
        from inspect_ai.log._transcript import Transcript as InspectTranscript

        inspect_transcript = InspectTranscript()
        info = TranscriptInfo(
            transcript_id="",  # Will be regenerated
            task_set="test-task-set",
            model="gpt-4",
        )

        # Create a mock TranscriptsDB
        mock_db = MagicMock()

        ctx = ObserveContext(
            info=info,
            inspect_transcript=inspect_transcript,
            db=mock_db,
            is_root=True,
        )

        import time

        start_time = time.time() - 1.5  # 1.5 seconds ago

        transcript = _build_transcript(ctx, start_time, error=None)

        # Verify auto-populated fields
        assert transcript.transcript_id != ""  # Generated
        assert transcript.date is not None
        assert transcript.total_time is not None
        assert transcript.total_time >= 1.5
        assert transcript.error is None
        assert transcript.message_count == 0  # No events
        assert transcript.task_set == "test-task-set"
        assert transcript.model == "gpt-4"

    def test_build_transcript_with_error(self) -> None:
        """_build_transcript captures error."""
        from inspect_ai.log._transcript import Transcript as InspectTranscript

        inspect_transcript = InspectTranscript()
        info = TranscriptInfo(transcript_id="")

        mock_db = MagicMock()

        ctx = ObserveContext(
            info=info,
            inspect_transcript=inspect_transcript,
            db=mock_db,
            is_root=True,
        )

        import time

        start_time = time.time()

        transcript = _build_transcript(
            ctx, start_time, error=ValueError("test error message")
        )

        assert transcript.error == "test error message"


class TestCurrentObserveContext:
    """Tests for current_observe_context function."""

    def test_outside_context_returns_none(self) -> None:
        """current_observe_context returns None outside observe."""
        assert current_observe_context() is None

    @pytest.mark.asyncio
    async def test_inside_context_returns_context(self) -> None:
        """current_observe_context returns context inside observe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(db=db) as expected_ctx:
                actual_ctx = current_observe_context()
                assert actual_ctx is expected_ctx

    @pytest.mark.asyncio
    async def test_nested_returns_innermost(self) -> None:
        """current_observe_context returns innermost context when nested."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = transcripts_db(tmpdir)

            async with observe(db=db) as outer:
                assert current_observe_context() is outer

                async with observe() as inner:
                    assert current_observe_context() is inner

                # After inner exits, back to outer
                assert current_observe_context() is outer
