"""Reusable answer generation and parsing for scanning pipelines.

Provides :func:`parse_answer` for extracting a :class:`Result` from a
:class:`ModelOutput`, and :func:`generate_answer` for driving LLM
generation with optional parsing — usable independently of
:func:`llm_scanner`.
"""

from collections.abc import Callable
from typing import Literal, overload

from inspect_ai.model import (
    ChatMessage,
    Model,
    ModelOutput,
    get_model,
)
from inspect_ai.scorer import ValueToFloat

from .._scanner.result import Reference, Result
from .._util.refusal import generate_retry_refusals
from .answer import answer_from_argument
from .structured import structured_generate, structured_schema
from .types import AnswerSpec, AnswerStructured


def parse_answer(
    output: ModelOutput,
    answer: AnswerSpec,
    extract_references: Callable[[str], list[Reference]],
    value_to_float: ValueToFloat | None = None,
) -> Result:
    """Parse a model output into a Result using the answer specification.

    Delegates to the answer type's parsing logic. This is a pure
    function — no LLM call is made.

    Args:
        output: The model's response to parse.
        answer: Answer specification (``"boolean"``, ``"numeric"``,
            ``"string"``, ``list[str]``, or :class:`AnswerStructured`).
        extract_references: Function to extract ``[M1]``-style references
            from the explanation text.
        value_to_float: Optional function to convert the parsed value
            to a float.

    Returns:
        A Result with value, answer, explanation, and references.
    """
    resolved = answer_from_argument(answer)
    return resolved.result_for_answer(output, extract_references, value_to_float)


@overload
async def generate_answer(
    prompt: str | list[ChatMessage],
    answer: AnswerSpec,
    *,
    model: str | Model | None = None,
    retry_refusals: int = 3,
    parse: Literal[True] = True,
    extract_references: Callable[[str], list[Reference]] | None = None,
    value_to_float: ValueToFloat | None = None,
) -> Result: ...


@overload
async def generate_answer(
    prompt: str | list[ChatMessage],
    answer: AnswerSpec,
    *,
    model: str | Model | None = None,
    retry_refusals: int = 3,
    parse: Literal[False],
) -> ModelOutput: ...


async def generate_answer(
    prompt: str | list[ChatMessage],
    answer: AnswerSpec,
    *,
    model: str | Model | None = None,
    retry_refusals: int = 3,
    parse: bool = True,
    extract_references: Callable[[str], list[Reference]] | None = None,
    value_to_float: ValueToFloat | None = None,
) -> Result | ModelOutput:
    """Generate a model response, optionally parsing it into a Result.

    Dispatches to the appropriate generation strategy based on the answer
    type: tool-based structured generation for :class:`AnswerStructured`,
    standard text generation with refusal retry for all other types.

    Args:
        prompt: The scanning prompt (string or message list).
        answer: Answer specification (``"boolean"``, ``"numeric"``,
            ``"string"``, ``list[str]``, or :class:`AnswerStructured`).
            Determines both the generation strategy and (when parsing)
            how to extract the result.
        model: Model to use for generation. Can be a model name string
            or ``Model`` instance. If ``None``, uses the default model.
        retry_refusals: Number of times to retry on model refusals
            (``stop_reason == "content_filter"``).
        parse: When ``True`` (default), parse the model output into a
            :class:`Result`. When ``False``, return the raw
            :class:`ModelOutput`.
        extract_references: Function to extract ``[M1]``-style references
            from the explanation text. Only used when ``parse=True``.
            Defaults to a no-op that returns no references.
        value_to_float: Optional function to convert the parsed value
            to a float. Only used when ``parse=True``.

    Returns:
        A :class:`Result` when ``parse=True``, or a :class:`ModelOutput`
        when ``parse=False``.
    """
    resolved_answer = answer_from_argument(answer)

    if isinstance(answer, AnswerStructured):
        value, _, model_output = await structured_generate(
            input=prompt,
            schema=structured_schema(answer),
            answer_tool=answer.answer_tool,
            model=model,
            max_attempts=answer.max_attempts,
            retry_refusals=retry_refusals,
        )
        if value is None and parse:
            return Result(value=None, answer=model_output.completion)
    else:
        model_output = await generate_retry_refusals(
            get_model(model),
            prompt,
            tools=[],
            tool_choice=None,
            config=None,
            retry_refusals=retry_refusals,
        )

    if not parse:
        return model_output

    refs_fn = extract_references or _no_references
    return resolved_answer.result_for_answer(model_output, refs_fn, value_to_float)


def _no_references(_text: str) -> list[Reference]:
    return []
