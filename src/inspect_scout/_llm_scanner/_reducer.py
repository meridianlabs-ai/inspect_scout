"""Result aggregation for multi-segment scanning.

Provides :class:`ResultReducer` with standard reducers (mean, any, union, etc.)
and a factory for LLM-based reduction, plus helpers for default reducer
dispatch and resultset detection.
"""

import builtins
import statistics
from collections.abc import Awaitable, Callable
from typing import get_args, get_origin

from inspect_ai.model import ChatMessage, ChatMessageSystem, ChatMessageUser, Model
from pydantic import BaseModel, JsonValue

from .._scanner.result import Reference, Result
from .generate import generate_answer
from .types import AnswerMultiLabel, AnswerSpec, AnswerStructured


def _numeric_values(results: list[Result]) -> list[float]:
    """Extract numeric values from results, skipping non-numeric."""
    values: list[float] = []
    for r in results:
        if isinstance(r.value, int | float) and not isinstance(r.value, bool):
            values.append(float(r.value))
    return values


def _merge_explanations(results: list[Result]) -> str | None:
    """Concatenate non-None explanations with segment markers."""
    parts: list[str] = []
    for i, r in enumerate(results):
        if r.explanation is not None:
            parts.append(f"[Segment {i + 1}]\n{r.explanation}")
    return "\n\n".join(parts) if parts else None


def _merge_metadata(results: list[Result]) -> dict[str, object] | None:
    """Shallow-merge all metadata dicts (later segments override)."""
    merged: dict[str, object] = {}
    for r in results:
        if r.metadata is not None:
            merged.update(r.metadata)
    return merged if merged else None


def _merge_references(results: list[Result]) -> list[Reference]:
    """Combine all references, deduplicated by (type, id)."""
    seen: set[tuple[str, str]] = set()
    refs: list[Reference] = []
    for r in results:
        for ref in r.references:
            key = (ref.type, ref.id)
            if key not in seen:
                seen.add(key)
                refs.append(ref)
    return refs


def _build_result(
    results: list[Result],
    *,
    value: JsonValue,
    answer: str | None,
) -> Result:
    """Build a reduced Result with merged auxiliary fields."""
    return Result(
        value=value,
        answer=answer,
        explanation=_merge_explanations(results),
        metadata=_merge_metadata(results),
        references=_merge_references(results),
    )


class ResultReducer:
    """Standard reducers for aggregating multi-segment scan results.

    Each static method is an async reducer with signature
    ``(list[Result]) -> Result``. The :meth:`llm` factory returns a
    reducer that uses an LLM to synthesize results.
    """

    @staticmethod
    async def mean(results: list[Result]) -> Result:
        """Arithmetic mean of numeric values."""
        values = _numeric_values(results)
        if not values:
            return results[-1]
        computed = statistics.mean(values)
        return _build_result(results, value=computed, answer=str(computed))

    @staticmethod
    async def median(results: list[Result]) -> Result:
        """Median of numeric values."""
        values = _numeric_values(results)
        if not values:
            return results[-1]
        computed = statistics.median(values)
        return _build_result(results, value=computed, answer=str(computed))

    @staticmethod
    async def mode(results: list[Result]) -> Result:
        """Mode (most common) of numeric values."""
        values = _numeric_values(results)
        if not values:
            return results[-1]
        computed = statistics.mode(values)
        return _build_result(results, value=computed, answer=str(computed))

    @staticmethod
    async def max(results: list[Result]) -> Result:
        """Maximum of numeric values."""
        values = _numeric_values(results)
        if not values:
            return results[-1]
        computed = builtins.max(values)
        return _build_result(results, value=computed, answer=str(computed))

    @staticmethod
    async def min(results: list[Result]) -> Result:
        """Minimum of numeric values."""
        values = _numeric_values(results)
        if not values:
            return results[-1]
        computed = builtins.min(values)
        return _build_result(results, value=computed, answer=str(computed))

    @staticmethod
    async def any(results: list[Result]) -> Result:
        """Boolean OR — True if any result is True."""
        value = builtins.any(r.value is True for r in results)
        answer = "Yes" if value else "No"
        return _build_result(results, value=value, answer=answer)

    @staticmethod
    async def union(results: list[Result]) -> Result:
        """Union of list values, deduplicated, preserving order."""
        seen: set[str] = set()
        combined: list[str] = []
        for r in results:
            if isinstance(r.value, list):
                for item in r.value:
                    s = str(item)
                    if s not in seen:
                        seen.add(s)
                        combined.append(s)
        answer = ", ".join(combined) if combined else None
        return _build_result(results, value=list(combined), answer=answer)

    @staticmethod
    async def last(results: list[Result]) -> Result:
        """Return the last result with merged auxiliary fields."""
        last_result = results[-1]
        return _build_result(
            results,
            value=last_result.value,
            answer=last_result.answer,
        )

    @staticmethod
    def llm(
        model: str | Model | None = None,
        prompt: str | None = None,
    ) -> Callable[[list[Result]], Awaitable[Result]]:
        """Factory that returns an LLM-based reducer.

        The returned reducer formats all segment results into a prompt
        and asks the model to synthesize the best answer.

        Args:
            model: Model to use for synthesis. Defaults to the
                default model.
            prompt: Custom synthesis prompt template. If None, uses
                a default template.

        Returns:
            An async reducer function.
        """

        async def reducer(results: list[Result]) -> Result:
            segments_text = _format_segments_for_llm(results)
            synthesis_prompt = prompt or _DEFAULT_SYNTHESIS_PROMPT

            messages: list[ChatMessage] = [
                ChatMessageSystem(content=_SYNTHESIS_SYSTEM_PROMPT),
                ChatMessageUser(content=f"{synthesis_prompt}\n\n{segments_text}"),
            ]

            result = await generate_answer(
                messages,
                answer="string",
                model=model,
            )

            return _build_result(
                results,
                value=result.value,
                answer=result.answer,
            )

        return reducer


_SYNTHESIS_SYSTEM_PROMPT = """\
You are an expert analyst synthesizing results from a multi-segment transcript analysis. \
Your task is to combine per-segment findings into a single coherent answer. \
Be concise and focus on the overall assessment rather than restating each segment."""

_DEFAULT_SYNTHESIS_PROMPT = """\
The following are results from analyzing different segments of a conversation transcript. \
Each segment was analyzed independently. Please synthesize these into a single best answer.

Provide your synthesis reasoning, then give your final answer on a line starting with "ANSWER:"."""


def _format_segments_for_llm(results: list[Result]) -> str:
    """Format segment results for the LLM synthesis prompt."""
    parts: list[str] = []
    for i, r in enumerate(results):
        lines = [f"--- Segment {i + 1} ---"]
        if r.answer is not None:
            lines.append(f"Answer: {r.answer}")
        lines.append(f"Value: {r.value}")
        if r.explanation is not None:
            lines.append(f"Explanation: {r.explanation}")
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def is_resultset_answer(answer: AnswerSpec) -> bool:
    """Check if the answer spec produces a resultset (list of models)."""
    if isinstance(answer, AnswerStructured):
        origin = get_origin(answer.type)
        if origin is list:
            args = get_args(answer.type)
            if args and isinstance(args[0], type) and issubclass(args[0], BaseModel):
                return True
        return False
    return False


def default_reducer(
    answer: AnswerSpec,
) -> Callable[[list[Result]], Awaitable[Result]]:
    """Return the default reducer for the given answer spec.

    Args:
        answer: The answer specification.

    Returns:
        An async reducer function.
    """
    match answer:
        case "boolean":
            return ResultReducer.any
        case "numeric":
            return ResultReducer.mean
        case "string":
            return ResultReducer.last
        case list():
            return ResultReducer.last
        case AnswerMultiLabel():
            return ResultReducer.union
        case AnswerStructured():
            return ResultReducer.last
        case _:
            return ResultReducer.last
