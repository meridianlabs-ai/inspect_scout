from typing import Any, Awaitable, Callable, Literal, overload

from inspect_ai.model import (
    Model,
    get_model,
)
from inspect_ai.scorer import ValueToFloat
from jinja2 import Environment

from inspect_scout._llm_scanner.structured import structured_generate, structured_schema
from inspect_scout._util.jinja import StrictOnUseUndefined
from inspect_scout._util.refusal import generate_retry_refusals

from .._scanner.extract import MessagesPreprocessor, messages_as_str
from .._scanner.result import Result
from .._scanner.scanner import SCANNER_NAME_ATTR, Scanner, scanner
from .._transcript.types import Transcript
from .answer import Answer, answer_from_argument
from .prompt import DEFAULT_SCANNER_TEMPLATE
from .types import AnswerMultiLabel, AnswerStructured


@overload
def llm_scanner(
    *,
    question: str | Callable[[Transcript], Awaitable[str]],
    answer: Literal["boolean", "numeric", "string"]
    | list[str]
    | AnswerMultiLabel
    | AnswerStructured,
    template: str | None = None,
    template_variables: dict[str, Any]
    | Callable[[Transcript], dict[str, Any]]
    | None = None,
    preprocessor: MessagesPreprocessor[Transcript] | None = None,
    model: str | Model | None = None,
    retry_refusals: bool | int = 3,
    name: str | None = None,
) -> Scanner[Transcript]: ...


@overload
def llm_scanner(
    *,
    question: None = None,
    answer: Literal["boolean", "numeric", "string"]
    | list[str]
    | AnswerMultiLabel
    | AnswerStructured,
    template: str,
    template_variables: dict[str, Any]
    | Callable[[Transcript], dict[str, Any]]
    | None = None,
    preprocessor: MessagesPreprocessor[Transcript] | None = None,
    model: str | Model | None = None,
    retry_refusals: bool | int = 3,
    name: str | None = None,
) -> Scanner[Transcript]: ...


@scanner(messages="all")
def llm_scanner(
    *,
    question: str | Callable[[Transcript], Awaitable[str]] | None = None,
    answer: Literal["boolean", "numeric", "string"]
    | list[str]
    | AnswerMultiLabel
    | AnswerStructured,
    value_to_float: ValueToFloat | None = None,
    template: str | None = None,
    template_variables: dict[str, Any]
    | Callable[[Transcript], dict[str, Any]]
    | None = None,
    preprocessor: MessagesPreprocessor[Transcript] | None = None,
    model: str | Model | None = None,
    retry_refusals: bool | int = 3,
    name: str | None = None,
) -> Scanner[Transcript]:
    """Create a scanner that uses an LLM to scan transcripts.

    This scanner presents a conversation transcript to an LLM along with a custom prompt and answer specification, enabling automated analysis of conversations for specific patterns, behaviors, or outcomes.

    Args:
        question: Question for the scanner to answer.
            Can be a static string (e.g., "Did the assistant refuse the request?") or a function that takes a Transcript and returns an string for dynamic questions based on transcript content. Can be omitted if you provide a custom template.
        answer: Specification of the answer format.
            Pass "boolean", "numeric", or "string" for a simple answer; pass `list[str]` for a set of labels; or pass `MultiLabels` for multi-classification.
        value_to_float: Optional function to convert the answer value to a float.
        template: Overall template for scanner prompt.
            The scanner template should include the following variables:
                - {{ question }} (question for the model to answer)
                - {{ messages }} (transcript message history as string)
                - {{ answer_prompt }} (prompt for a specific type of answer).
                - {{ answer_format }} (instructions on how to format the answer)
            In addition, scanner templates can bind to any data within
            `Transcript.metadata` (e.g. {{ metadata.score }})
        template_variables: Additional variables to make available in the template.
            Optionally takes a function which receives the current `Transcript` which
            can return variables.
        preprocessor: Transform conversation messages before analysis.
            Controls exclusion of system messages, reasoning tokens, and tool calls. Defaults to removing system messages.
        model: Optional model specification.
            Can be a model name string or `Mode`l instance. If None, uses the default model
        retry_refusals: Retry model refusals. Pass an `int` for number of retries (defaults to 3). Pass `False` to not retry refusals. If the limit of refusals is exceeded then a `RuntimeError` is raised.
        name: Scanner name.
            Use this to assign a name when passing `llm_scanner()` directly to `scan()` rather than delegating to it from another scanner.

    Returns:
        A `Scanner` function that analyzes Transcript instances and returns `Results` based on the LLM's assessment according to the specified prompt and answer format
    """
    if template is None:
        template = DEFAULT_SCANNER_TEMPLATE
    resolved_answer = answer_from_argument(answer)

    # resolve retry_refusals
    retry_refusals = (
        retry_refusals
        if isinstance(retry_refusals, int)
        else 3
        if retry_refusals is True
        else 0
    )

    async def scan(transcript: Transcript) -> Result:
        messages_str, extract_references = await messages_as_str(
            transcript,
            preprocessor=preprocessor,
            include_ids=True,
        )

        resolved_prompt = await render_scanner_prompt(
            template=template,
            template_variables=template_variables,
            transcript=transcript,
            messages=messages_str,
            question=question,
            answer=resolved_answer,
        )

        # do a structured generate if this is AnswerStructured
        if isinstance(answer, AnswerStructured):
            value, _, model_output = await structured_generate(
                input=resolved_prompt,
                schema=structured_schema(answer),
                answer_tool=answer.answer_tool,
                model=model,
                max_attempts=answer.max_attempts,
                retry_refusals=retry_refusals,
            )
            # if we failed to extract then return value=None
            if value is None:
                return Result(value=None, answer=model_output.completion)

        # otherwise do a normal generate
        else:
            model_output = await generate_retry_refusals(
                get_model(model),
                resolved_prompt,
                tools=[],
                tool_choice=None,
                config=None,
                retry_refusals=retry_refusals,
            )

        # resolve answer
        return resolved_answer.result_for_answer(
            model_output, extract_references, value_to_float
        )

    # set name for collection by @scanner if specified
    if name is not None:
        setattr(scan, SCANNER_NAME_ATTR, name)

    return scan


async def render_scanner_prompt(
    *,
    template: str,
    template_variables: dict[str, Any]
    | Callable[[Transcript], dict[str, Any]]
    | None = None,
    transcript: Transcript,
    messages: str,
    question: str | Callable[[Transcript], Awaitable[str]] | None,
    answer: Answer,
) -> str:
    """Render a scanner prompt template with the provided variables.

    Args:
        template: Jinja2 template string for the scanner prompt.
        template_variables: Additional variables
        transcript: Transcript to extract variables from.
        messages: Formatted conversation messages string.
        question: Question for the scanner to answer. Can be a static string
            or a callable that takes a Transcript and returns an awaitable string.
        answer: Answer object containing prompt and format strings.

    Returns:
        Rendered prompt string with all variables substituted.
    """
    # resolve variables
    template_variables = template_variables or {}
    if callable(template_variables):
        template_variables = template_variables(transcript)

    return (
        Environment(undefined=StrictOnUseUndefined)
        .from_string(template)
        .render(
            messages=messages,
            question=question
            if isinstance(question, str | None)
            else await question(transcript),
            answer_prompt=answer.prompt,
            answer_format=answer.format,
            date=transcript.date,
            task_set=transcript.task_set,
            task_id=transcript.task_id,
            task_repeat=transcript.task_repeat,
            agent=transcript.agent,
            agent_args=transcript.agent_args,
            model=transcript.model,
            model_options=transcript.model_options,
            score=transcript.score,
            success=transcript.success,
            total_time=transcript.total_time,
            total_tokens=transcript.total_tokens,
            error=transcript.error,
            limit=transcript.limit,
            metadata=transcript.metadata
            # backward compatibility for existing templates
            # TODO: remove this once users have updated
            | {
                "task_name": transcript.task_set,
                "score": transcript.score,
                "model": transcript.model,
                "solver": transcript.agent,
                "error": transcript.error,
                "limit": transcript.limit,
            },
            **template_variables,
        )
    )
