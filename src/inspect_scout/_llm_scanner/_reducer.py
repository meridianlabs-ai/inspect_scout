"""Result aggregation for multi-segment scanning.

Provides :class:`ResultReducer` with standard reducers (mean, any, union, etc.)
and a factory for LLM-based reduction, plus helpers for default reducer
dispatch and resultset detection.
"""

import builtins
import statistics
from collections.abc import Awaitable, Callable
from typing import cast, get_args, get_origin

from inspect_ai.model import ChatMessage, ChatMessageSystem, ChatMessageUser, Model
from pydantic import BaseModel, JsonValue

from .._scanner.result import Reference, Result, as_resultset
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
    async def majority(results: list[Result]) -> Result:
        """Most common value, with last-result tiebreaker.

        Counts occurrences of each ``value`` across results. If there is
        a unique winner it is used; otherwise the last result's value
        breaks the tie. The ``answer`` is taken from the matching result.
        """
        counts: dict[str, int] = {}
        for r in results:
            key = str(r.value)
            counts[key] = counts.get(key, 0) + 1

        max_count = builtins.max(counts.values())
        winners = [v for v, c in counts.items() if c == max_count]

        if len(winners) == 1:
            winning_key = winners[0]
        else:
            # Tiebreak: pick the last result whose value is among the winners
            winning_key = winners[0]  # fallback
            for r in reversed(results):
                if str(r.value) in winners:
                    winning_key = str(r.value)
                    break

        # Find the last result whose value matches the winner
        matched = results[-1]  # fallback
        for r in reversed(results):
            if str(r.value) == winning_key:
                matched = r
                break

        return _build_result(results, value=matched.value, answer=matched.answer)

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

            # Prefer the synthesized reasoning (everything before "ANSWER:"
            # in the LLM's completion) over a raw concat of segment
            # explanations — the LLM was explicitly asked for it. Fall back
            # to the concat only if the synthesis didn't produce reasoning
            # (e.g. a custom `prompt=` that doesn't elicit one).
            return Result(
                value=result.value,
                answer=result.answer,
                explanation=result.explanation or _merge_explanations(results),
                metadata=_merge_metadata(results),
                references=_merge_references(results),
            )

        return reducer


_SYNTHESIS_SYSTEM_PROMPT = """\
You are an expert analyst synthesizing results from a multi-segment transcript analysis. \
Your task is to combine per-segment findings into a single coherent answer. \
Be concise and focus on the overall assessment rather than restating each segment.

Preserve any message citations of the form [M1], [M2], ... exactly as they appear \
in the per-segment explanations so the reader can trace claims back to specific \
messages. Do not invent new citations."""

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


async def reduce_timeline_results(
    results: list[tuple[str, Result]],
    reducer: Callable[[list[Result]], Awaitable[Result]],
) -> Result:
    """Group timeline scan results by span id and reduce within-span chunks.

    Each tuple is ``(span_id, result)`` in walk order. Spans that produced
    multiple chunks are collapsed via ``reducer``; single-chunk spans pass
    through unchanged. If the walk produced exactly one span, that span's
    Result is returned directly. Otherwise the per-span Results are wrapped
    in a resultset to preserve cross-span attribution.
    """
    by_span: dict[str, list[Result]] = {}
    span_order: list[str] = []
    for span_id, result in results:
        if span_id not in by_span:
            span_order.append(span_id)
            by_span[span_id] = []
        by_span[span_id].append(result)

    per_span: list[Result] = []
    for sid in span_order:
        group = by_span[sid]
        per_span.append(group[0] if len(group) == 1 else await reducer(group))

    if len(per_span) == 1:
        return per_span[0]
    return as_resultset(per_span)


async def aggregate_results(
    *,
    results: list[tuple[str | None, Result]],
    timeline: bool,
    answer: AnswerSpec,
    reducer: Callable[[list[Result]], Awaitable[Result]] | None,
) -> Result:
    """Aggregate per-segment scanner results into one final Result.

    Decision table on ``(timeline, is_resultset_answer(answer))``:

    - ``len(results) == 1``    → return that Result (no aggregation).
    - ``(True,  False)``       → :func:`reduce_timeline_results`: group
      chunks by span and reduce within span; wrap multiple spans in a
      resultset.
    - ``(_,     True)``        → :func:`as_resultset`: the answer is
      inherently a list of findings, so each segment stays an entry.
    - ``(False, False)``       → collapse all segments to one Result via
      ``reducer or default_reducer(answer)``.

    Args:
        results: ``(span_id, Result)`` pairs in walk order. ``span_id`` is
            ``None`` on non-timeline paths and a string on timeline paths.
        timeline: Whether the scan produced timeline-aware segments.
        answer: The answer specification, used to pick the default reducer
            and to detect resultset-shaped answers.
        reducer: Optional caller-supplied reducer. When ``None``,
            :func:`default_reducer` is used.
    """
    if len(results) == 1:
        return results[0][1]

    flat = [r for _, r in results]

    if timeline and not is_resultset_answer(answer):
        effective_reducer = reducer or default_reducer(answer)
        return await reduce_timeline_results(
            cast(list[tuple[str, Result]], results),
            effective_reducer,
        )

    if is_resultset_answer(answer):
        return as_resultset(flat)

    effective_reducer = reducer or default_reducer(answer)
    return await effective_reducer(flat)


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
            return ResultReducer.llm()
        case list():
            return ResultReducer.majority
        case AnswerMultiLabel():
            return ResultReducer.union
        case AnswerStructured():
            return ResultReducer.last
        case _:
            return ResultReducer.last
