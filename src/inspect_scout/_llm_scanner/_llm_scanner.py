from typing import Awaitable, Callable, Literal

from inspect_ai.model import (
    Model,
    get_model,
)
from jinja2 import Template
from pydantic import JsonValue

from .._scanner.extract import ContentFilter, messages_as_str
from .._scanner.result import Result
from .._scanner.scanner import SCANNER_NAME_ATTR, Scanner, scanner
from .._transcript.types import Transcript
from .answer import Answer, answer_from_argument
from .prompt import DEFAULT_SCANNER_TEMPLATE
from .types import MultiLabels


@scanner(messages="all")
def llm_scanner(
    *,
    question: str | Callable[[Transcript], Awaitable[str]],
    answer: Literal["boolean", "numeric", "string"] | list[str] | MultiLabels,
    template: str | None = None,
    messages: ContentFilter | None = None,
    model: str | Model | None = None,
    name: str | None = None,
) -> Scanner[Transcript]:
    """Create a scanner that uses an LLM to scan transcripts.

    This scanner presents a conversation transcript to an LLM along with a custom
    prompt and answer specification, enabling automated analysis of conversations
    for specific patterns, behaviors, or outcomes.

    Args:
        question: Question for the scanner to answer. Can be a static string (e.g.,
            "Did the assistant refuse the request?") or a function that takes a
            Transcript and returns an string for dynamic questions based on transcript
            content.
        answer: Specification of the answer format.
            Pass "boolean", "numeric", or "string" for a simple answer; pass `list[str]`
            for a set of labels; or pass `MultiLabels` for multi-classification.
        template: Overall template for scanner prompt.
            The scanner template should include the following variables:
              - {{ question }} (question for the model to answer)
              - {{ messages }} (transcript message history as string)
              - {{ answer_prompt }} (prompt the model for a specific type of answer and explanation).
              - {{ answer_format }} (instructions on formatting for value extraction)
        messages: Filter conversation messages before analysis.
            Controls exclusion of system messages, reasoning tokens, and tool calls.
            Defaults to filtering system messages.
        model: Optional model specification. Can be a model
            name string or Model instance. If None, uses the default model
        name: Scanner name (use this to assign a name when passing `llm_scanner()`
            directly to `scan()` rather than delegating to it from another scanner).

    Returns:
        A Scanner function that analyzes Transcript instances and returns Results
            based on the LLM's assessment according to the specified prompt and answer
            format
    """
    if messages is None:
        messages = ContentFilter()
    if template is None:
        template = DEFAULT_SCANNER_TEMPLATE
    resolved_answer = answer_from_argument(answer)

    async def scan(transcript: Transcript) -> Result:
        messages_str, message_id_map = await messages_as_str(
            transcript.messages, messages, include_ids=True
        )

        resolved_prompt = await render_scanner_prompt(
            template=template,
            transcript=transcript,
            messages=messages_str,
            question=question,
            answer=resolved_answer,
        )

        model_output = await get_model(model).generate(resolved_prompt)
        return resolved_answer.result_for_answer(model_output, message_id_map)

    # set name for collection by @scanner if specified
    if name is not None:
        setattr(scan, SCANNER_NAME_ATTR, name)

    return scan


async def render_scanner_prompt(
    *,
    template: str,
    transcript: Transcript,
    messages: str,
    question: str | Callable[[Transcript], Awaitable[str]],
    answer: Answer,
) -> str:
    """Render a scanner prompt template with the provided variables.

    Args:
        template: Jinja2 template string for the scanner prompt.
        transcript: Transcript to extract variables from.
        messages: Formatted conversation messages string.
        question: Question for the scanner to answer. Can be a static string
            or a callable that takes a Transcript and returns an awaitable string.
        answer: Answer object containing prompt and format strings.

    Returns:
        Rendered prompt string with all variables substituted.
    """
    variables = _variables_for_transcript(transcript)
    return Template(template).render(
        messages=messages,
        question=question if isinstance(question, str) else await question(transcript),
        answer_prompt=answer.prompt,
        answer_format=answer.format,
        **variables,
    )


def _variables_for_transcript(transcript: Transcript) -> dict[str, JsonValue]:
    variables = dict(transcript.variables)
    # remove builtins to avoid conflicts
    variables.pop("prompt", None)
    variables.pop("explanation_text", None)
    variables.pop("messages", None)
    variables.pop("answer_prompt", None)
    # add scores
    variables["score"] = transcript.score or ""
    variables = variables | {
        f"score_{name}": value for name, value in transcript.scores.items()
    }
    return variables
