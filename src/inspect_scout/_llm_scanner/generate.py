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
    ChatMessageUser,
    GenerateConfig,
    Model,
    ModelOutput,
    get_model,
)
from inspect_ai.scorer import ValueToFloat
from jinja2 import Environment

from .._scanner.result import Reference, Result
from .._util.jinja import StrictOnUseUndefined
from .._util.refusal import generate_retry_refusals
from .answer import Answer, answer_from_argument
from .prompt import DEFAULT_SCANNER_TEMPLATE
from .structured import structured_generate, structured_schema
from .types import AnswerSpec, AnswerStructured, _TextualAnswerSpec


def parse_answer(
    output: ModelOutput,
    answer: AnswerSpec,
    extract_refs: Callable[[str], list[Reference]],
    value_to_float: ValueToFloat | None = None,
) -> Result:
    """Parse a model output into a Result using the answer specification.

    Delegates to the answer type's parsing logic. This is a pure
    function — no LLM call is made.

    Args:
        output: The model's response to parse.
        answer: Answer specification (``"boolean"``, ``"numeric"``,
            ``"string"``, ``list[str]``, or :class:`AnswerStructured`).
        extract_refs: Function to extract ``[M1]``-style references
            from the explanation text.
        value_to_float: Optional function to convert the parsed value
            to a float.

    Returns:
        A Result with value, answer, explanation, and references.
    """
    resolved = answer_from_argument(answer)
    return resolved.result_for_answer(output, extract_refs, value_to_float)


@overload
async def generate_answer(
    prompt: str | list[ChatMessage],
    answer: AnswerSpec,
    *,
    model: str | Model | None = None,
    config: GenerateConfig | None = None,
    retry_refusals: int = 3,
    parse: Literal[True] = True,
    extract_refs: Callable[[str], list[Reference]] | None = None,
    value_to_float: ValueToFloat | None = None,
) -> Result: ...


@overload
async def generate_answer(
    prompt: str | list[ChatMessage],
    answer: _TextualAnswerSpec,
    *,
    model: str | Model | None = None,
    config: GenerateConfig | None = None,
    retry_refusals: int = 3,
    parse: Literal[False],
) -> ModelOutput: ...


async def generate_answer(
    prompt: str | list[ChatMessage],
    answer: AnswerSpec,
    *,
    model: str | Model | None = None,
    config: GenerateConfig | None = None,
    retry_refusals: int = 3,
    parse: bool = True,
    extract_refs: Callable[[str], list[Reference]] | None = None,
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
        config: Per-call :class:`GenerateConfig` overrides (e.g. ``cache``,
            ``temperature``). For :class:`AnswerStructured` answers,
            ``parallel_tool_calls`` is always forced to ``False``.
        retry_refusals: Number of times to retry on model refusals
            (``stop_reason == "content_filter"``).
        parse: When ``True`` (default), parse the model output into a
            :class:`Result`. When ``False``, return the raw
            :class:`ModelOutput`.
        extract_refs: Function to extract ``[M1]``-style references
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
            config=config,
            max_attempts=answer.max_attempts,
            retry_refusals=retry_refusals,
        )
        if value is None:
            return Result(
                value=None,
                answer=model_output.completion,
                metadata={"stop_reason": model_output.stop_reason},
            )
        refs_fn = extract_refs or _no_references
        result = resolved_answer.result_for_answer(
            model_output, refs_fn, value_to_float
        )
        result.metadata = {
            **(result.metadata or {}),
            "stop_reason": model_output.stop_reason,
        }
        return result

    elif parse:
        return await _text_generate(
            get_model(model),
            prompt,
            resolved_answer,
            config,
            retry_refusals,
            extract_refs or _no_references,
            value_to_float,
        )
    else:
        return await generate_retry_refusals(
            get_model(model),
            prompt,
            tools=[],
            tool_choice=None,
            config=config,
            retry_refusals=retry_refusals,
        )


_TEXT_MAX_ATTEMPTS = 3


async def _text_generate(
    model: Model,
    input: str | list[ChatMessage],
    answer: Answer,
    config: GenerateConfig | None,
    retry_refusals: int,
    extract_refs: Callable[[str], list[Reference]],
    value_to_float: ValueToFloat | None,
) -> Result:
    """Generate text with retry on parse failure.

    When the model's response cannot be parsed, feeds format instructions
    back as a user message and retries, up to ``_TEXT_MAX_ATTEMPTS`` times.
    Returns a fully parsed ``Result`` (with refs, value_to_float, and
    stop_reason metadata).
    """
    messages: list[ChatMessage] = (
        [ChatMessageUser(content=input)] if isinstance(input, str) else list(input)
    )

    for attempt in range(_TEXT_MAX_ATTEMPTS):
        output = await generate_retry_refusals(
            model,
            messages,
            tools=[],
            tool_choice=None,
            config=config,
            retry_refusals=retry_refusals,
        )

        result = answer.result_for_answer(output, extract_refs, value_to_float)
        result.metadata = {
            **(result.metadata or {}),
            "stop_reason": output.stop_reason,
        }

        if result.answer is not None or attempt == _TEXT_MAX_ATTEMPTS - 1:
            return result

        # Parse failed — grow conversation with feedback
        messages.append(output.message)
        messages.append(
            ChatMessageUser(
                content=(
                    "Your response could not be parsed. "
                    "Please try again, following these instructions:\n\n"
                    f"{answer.format}"
                ),
            )
        )

    raise AssertionError("unreachable")  # loop always returns


def _no_references(_text: str) -> list[Reference]:
    return []


def scanner_prompt(
    messages: str,
    question: str,
    answer: AnswerSpec | Answer,
) -> str:
    """Render the default scanner prompt template.

    Combines the transcript messages, question, and answer type into a
    complete prompt using the standard scanner template. Use this when
    you want the default prompt structure but need control over generation
    (via ``generate_answer()``) or other scanning steps.

    For fully custom prompt templates, use ``answer_type()`` to access
    the ``.prompt`` and ``.format`` strings directly.

    Args:
        messages: Pre-formatted message string (from ``messages_as_str``
            or ``message_numbering``).
        question: Question for the scanner to answer.
        answer: Answer specification or resolved ``Answer`` object.

    Returns:
        Rendered prompt string.
    """
    resolved = answer if isinstance(answer, Answer) else answer_from_argument(answer)
    return (
        Environment(undefined=StrictOnUseUndefined)
        .from_string(DEFAULT_SCANNER_TEMPLATE)
        .render(
            messages=messages,
            question=question,
            answer_prompt=resolved.prompt,
            answer_format=resolved.format,
        )
    )
