"""Tests for ResultReducer and reducer dispatch."""

from unittest.mock import AsyncMock, patch

import pytest
from inspect_ai.model import ChatMessageSystem, ChatMessageUser
from inspect_scout._llm_scanner._reducer import (
    _SYNTHESIS_SYSTEM_PROMPT,
    ResultReducer,
    default_reducer,
    is_resultset_answer,
)
from inspect_scout._llm_scanner.types import AnswerMultiLabel, AnswerStructured
from inspect_scout._scanner.result import Reference, Result
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Numeric reducers
# ---------------------------------------------------------------------------


class TestMean:
    @pytest.mark.anyio
    async def test_mean(self) -> None:
        results = [
            Result(value=2.0, answer="2.0"),
            Result(value=4.0, answer="4.0"),
            Result(value=6.0, answer="6.0"),
        ]
        r = await ResultReducer.mean(results)
        assert r.value == 4.0
        assert r.answer == "4.0"

    @pytest.mark.anyio
    async def test_mean_integers(self) -> None:
        results = [Result(value=3, answer="3"), Result(value=5, answer="5")]
        r = await ResultReducer.mean(results)
        assert r.value == 4.0


class TestMedian:
    @pytest.mark.anyio
    async def test_median(self) -> None:
        results = [
            Result(value=1.0, answer="1"),
            Result(value=5.0, answer="5"),
            Result(value=10.0, answer="10"),
        ]
        r = await ResultReducer.median(results)
        assert r.value == 5.0

    @pytest.mark.anyio
    async def test_median_even(self) -> None:
        results = [
            Result(value=1.0, answer="1"),
            Result(value=3.0, answer="3"),
            Result(value=5.0, answer="5"),
            Result(value=7.0, answer="7"),
        ]
        r = await ResultReducer.median(results)
        assert r.value == 4.0


class TestMode:
    @pytest.mark.anyio
    async def test_mode(self) -> None:
        results = [
            Result(value=3.0, answer="3"),
            Result(value=3.0, answer="3"),
            Result(value=5.0, answer="5"),
        ]
        r = await ResultReducer.mode(results)
        assert r.value == 3.0


class TestMax:
    @pytest.mark.anyio
    async def test_max(self) -> None:
        results = [
            Result(value=1.0, answer="1"),
            Result(value=9.0, answer="9"),
            Result(value=5.0, answer="5"),
        ]
        r = await ResultReducer.max(results)
        assert r.value == 9.0


class TestMin:
    @pytest.mark.anyio
    async def test_min(self) -> None:
        results = [
            Result(value=1.0, answer="1"),
            Result(value=9.0, answer="9"),
            Result(value=5.0, answer="5"),
        ]
        r = await ResultReducer.min(results)
        assert r.value == 1.0


# ---------------------------------------------------------------------------
# Boolean reducer
# ---------------------------------------------------------------------------


class TestAny:
    @pytest.mark.anyio
    async def test_any_all_false(self) -> None:
        results = [
            Result(value=False, answer="No"),
            Result(value=False, answer="No"),
        ]
        r = await ResultReducer.any(results)
        assert r.value is False
        assert r.answer == "No"

    @pytest.mark.anyio
    async def test_any_one_true(self) -> None:
        results = [
            Result(value=False, answer="No"),
            Result(value=True, answer="Yes"),
            Result(value=False, answer="No"),
        ]
        r = await ResultReducer.any(results)
        assert r.value is True
        assert r.answer == "Yes"


# ---------------------------------------------------------------------------
# Multi-value reducer
# ---------------------------------------------------------------------------


class TestUnion:
    @pytest.mark.anyio
    async def test_union_labels(self) -> None:
        results = [
            Result(value=["A", "B"], answer="A, B"),
            Result(value=["B", "C"], answer="B, C"),
        ]
        r = await ResultReducer.union(results)
        assert r.value == ["A", "B", "C"]
        assert r.answer == "A, B, C"

    @pytest.mark.anyio
    async def test_union_deduplication(self) -> None:
        results = [
            Result(value=["X", "Y"], answer="X, Y"),
            Result(value=["X", "Y"], answer="X, Y"),
        ]
        r = await ResultReducer.union(results)
        assert r.value == ["X", "Y"]

    @pytest.mark.anyio
    async def test_union_preserves_order(self) -> None:
        results = [
            Result(value=["C", "A"], answer="C, A"),
            Result(value=["B", "A"], answer="B, A"),
        ]
        r = await ResultReducer.union(results)
        assert r.value == ["C", "A", "B"]


# ---------------------------------------------------------------------------
# Last reducer
# ---------------------------------------------------------------------------


class TestLast:
    @pytest.mark.anyio
    async def test_last(self) -> None:
        results = [
            Result(value="first", answer="first"),
            Result(value="second", answer="second"),
            Result(value="third", answer="third"),
        ]
        r = await ResultReducer.last(results)
        assert r.value == "third"
        assert r.answer == "third"


# ---------------------------------------------------------------------------
# Field merging
# ---------------------------------------------------------------------------


class TestFieldUnion:
    @pytest.mark.anyio
    async def test_field_union_explanations(self) -> None:
        results = [
            Result(value=True, answer="Yes", explanation="Reason A"),
            Result(value=True, answer="Yes", explanation="Reason B"),
        ]
        r = await ResultReducer.any(results)
        assert r.explanation is not None
        assert "[Segment 1]" in r.explanation
        assert "Reason A" in r.explanation
        assert "[Segment 2]" in r.explanation
        assert "Reason B" in r.explanation

    @pytest.mark.anyio
    async def test_field_union_explanations_skips_none(self) -> None:
        results = [
            Result(value=True, answer="Yes", explanation=None),
            Result(value=True, answer="Yes", explanation="Only reason"),
        ]
        r = await ResultReducer.any(results)
        assert r.explanation is not None
        assert "[Segment 2]" in r.explanation
        assert "Only reason" in r.explanation
        assert "[Segment 1]" not in r.explanation

    @pytest.mark.anyio
    async def test_field_union_metadata(self) -> None:
        results = [
            Result(value=1.0, answer="1", metadata={"a": 1, "b": 2}),
            Result(value=2.0, answer="2", metadata={"b": 3, "c": 4}),
        ]
        r = await ResultReducer.mean(results)
        assert r.metadata == {"a": 1, "b": 3, "c": 4}

    @pytest.mark.anyio
    async def test_field_union_metadata_none(self) -> None:
        results = [
            Result(value=1.0, answer="1"),
            Result(value=2.0, answer="2"),
        ]
        r = await ResultReducer.mean(results)
        assert r.metadata is None

    @pytest.mark.anyio
    async def test_field_union_references(self) -> None:
        ref1 = Reference(type="message", id="m1", cite="[M1]")
        ref2 = Reference(type="message", id="m2", cite="[M2]")
        ref3 = Reference(type="message", id="m1", cite="[M1]")  # duplicate
        results = [
            Result(value=True, answer="Yes", references=[ref1, ref2]),
            Result(value=True, answer="Yes", references=[ref3]),
        ]
        r = await ResultReducer.any(results)
        assert len(r.references) == 2
        assert r.references[0].id == "m1"
        assert r.references[1].id == "m2"


# ---------------------------------------------------------------------------
# Default reducer dispatch
# ---------------------------------------------------------------------------


class TestDefaultReducer:
    def test_boolean(self) -> None:
        assert default_reducer("boolean") is ResultReducer.any

    def test_numeric(self) -> None:
        assert default_reducer("numeric") is ResultReducer.mean

    def test_string(self) -> None:
        assert default_reducer("string") is ResultReducer.last

    def test_labels(self) -> None:
        assert default_reducer(["A", "B", "C"]) is ResultReducer.last

    def test_multi_label(self) -> None:
        assert (
            default_reducer(AnswerMultiLabel(labels=["X", "Y"])) is ResultReducer.union
        )

    def test_structured(self) -> None:
        class M(BaseModel):
            x: int

        assert default_reducer(AnswerStructured(type=M)) is ResultReducer.last


# ---------------------------------------------------------------------------
# is_resultset_answer
# ---------------------------------------------------------------------------


class TestIsResultsetAnswer:
    def test_simple_types_are_not_resultset(self) -> None:
        assert is_resultset_answer("boolean") is False
        assert is_resultset_answer("numeric") is False
        assert is_resultset_answer("string") is False

    def test_labels_not_resultset(self) -> None:
        assert is_resultset_answer(["A", "B"]) is False

    def test_structured_single_not_resultset(self) -> None:
        class M(BaseModel):
            x: int

        assert is_resultset_answer(AnswerStructured(type=M)) is False

    def test_structured_list_is_resultset(self) -> None:
        class M(BaseModel):
            x: int

        assert is_resultset_answer(AnswerStructured(type=list[M])) is True


# ---------------------------------------------------------------------------
# LLM synthesis reducer
# ---------------------------------------------------------------------------


class TestLlmReducer:
    @pytest.mark.anyio
    @patch(
        "inspect_scout._llm_scanner._reducer.generate_answer", new_callable=AsyncMock
    )
    async def test_llm_reducer_synthesizes(self, mock_generate: AsyncMock) -> None:
        """LLM reducer calls generate_answer and merges segment fields."""
        mock_generate.return_value = Result(
            value="synthesized answer",
            answer="synthesized answer",
            explanation="LLM synthesis reasoning",
        )

        ref1 = Reference(type="message", id="m1", cite="[M1]")
        ref2 = Reference(type="message", id="m2", cite="[M2]")
        segment_results = [
            Result(
                value="partial A",
                answer="partial A",
                explanation="Reason A",
                metadata={"key_a": 1},
                references=[ref1],
            ),
            Result(
                value="partial B",
                answer="partial B",
                explanation="Reason B",
                metadata={"key_b": 2},
                references=[ref2],
            ),
        ]

        reducer = ResultReducer.llm()
        result = await reducer(segment_results)

        # Value/answer come from the LLM synthesis
        assert result.value == "synthesized answer"
        assert result.answer == "synthesized answer"

        # Explanation comes from merged segments, not the LLM's reasoning
        assert result.explanation is not None
        assert "Reason A" in result.explanation
        assert "Reason B" in result.explanation
        assert "[Segment 1]" in result.explanation
        assert "[Segment 2]" in result.explanation
        assert "LLM synthesis reasoning" not in result.explanation

        # Metadata and references are merged from segments
        assert result.metadata == {"key_a": 1, "key_b": 2}
        assert len(result.references) == 2

    @pytest.mark.anyio
    @patch(
        "inspect_scout._llm_scanner._reducer.generate_answer", new_callable=AsyncMock
    )
    async def test_llm_reducer_passes_system_message(
        self, mock_generate: AsyncMock
    ) -> None:
        """LLM reducer sends a system message and user message."""
        mock_generate.return_value = Result(value="answer", answer="answer")

        segment_results = [
            Result(value="seg1", answer="seg1", explanation="Reason"),
        ]

        reducer = ResultReducer.llm()
        await reducer(segment_results)

        # Verify generate_answer was called with a message list
        call_args = mock_generate.call_args
        messages = call_args.args[0]
        assert len(messages) == 2
        assert isinstance(messages[0], ChatMessageSystem)
        assert messages[0].content == _SYNTHESIS_SYSTEM_PROMPT
        assert isinstance(messages[1], ChatMessageUser)
        assert "Segment 1" in messages[1].content

        # Verify answer type is "string"
        assert call_args.kwargs["answer"] == "string"

    @pytest.mark.anyio
    @patch(
        "inspect_scout._llm_scanner._reducer.generate_answer", new_callable=AsyncMock
    )
    async def test_llm_reducer_custom_prompt(self, mock_generate: AsyncMock) -> None:
        """LLM reducer uses custom prompt when provided."""
        mock_generate.return_value = Result(value="answer", answer="answer")

        segment_results = [
            Result(value="seg1", answer="seg1"),
        ]

        custom_prompt = "Custom synthesis instructions."
        reducer = ResultReducer.llm(prompt=custom_prompt)
        await reducer(segment_results)

        messages = mock_generate.call_args.args[0]
        user_content = messages[1].content
        assert custom_prompt in user_content
