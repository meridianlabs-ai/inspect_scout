from typing import Any, Awaitable, Callable, Literal, cast, overload

from inspect_ai.model import (
    ChatMessage,
    Model,
    get_model,
)
from inspect_ai.scorer import ValueToFloat
from jinja2 import Environment

from inspect_scout._util.jinja import StrictOnUseUndefined

from .._scanner.extract import MessagesPreprocessor, message_numbering
from .._scanner.result import Result, as_resultset
from .._scanner.scanner import (
    SCANNER_CONTENT_ATTR,
    SCANNER_NAME_ATTR,
    Scanner,
    scanner,
)
from .._transcript.messages import transcript_messages
from .._transcript.types import Transcript, TranscriptContent
from ._reducer import default_reducer, is_resultset_answer
from .answer import Answer, answer_from_argument
from .generate import generate_answer
from .prompt import DEFAULT_SCANNER_TEMPLATE
from .types import AnswerSpec


@overload
def llm_scanner(
    *,
    question: str | Callable[[Transcript], Awaitable[str]],
    answer: AnswerSpec,
    value_to_float: ValueToFloat | None = None,
    template: str | None = None,
    template_variables: dict[str, Any]
    | Callable[[Transcript], dict[str, Any]]
    | None = None,
    preprocessor: MessagesPreprocessor[Transcript] | None = None,
    model: str | Model | None = None,
    model_role: str | None = None,
    retry_refusals: bool | int = 3,
    name: str | None = None,
    content: TranscriptContent | None = None,
    context_window: int | None = None,
    compaction: Literal["all", "last"] | int = "all",
    depth: int | None = None,
    reducer: Callable[[list[Result]], Awaitable[Result]] | None = None,
) -> Scanner[Transcript]: ...


@overload
def llm_scanner(
    *,
    question: None = None,
    answer: AnswerSpec,
    value_to_float: ValueToFloat | None = None,
    template: str,
    template_variables: dict[str, Any]
    | Callable[[Transcript], dict[str, Any]]
    | None = None,
    preprocessor: MessagesPreprocessor[Transcript] | None = None,
    model: str | Model | None = None,
    model_role: str | None = None,
    retry_refusals: bool | int = 3,
    name: str | None = None,
    content: TranscriptContent | None = None,
    context_window: int | None = None,
    compaction: Literal["all", "last"] | int = "all",
    depth: int | None = None,
    reducer: Callable[[list[Result]], Awaitable[Result]] | None = None,
) -> Scanner[Transcript]: ...


@scanner(messages="all")
def llm_scanner(
    *,
    question: str | Callable[[Transcript], Awaitable[str]] | None = None,
    answer: AnswerSpec,
    value_to_float: ValueToFloat | None = None,
    template: str | None = None,
    template_variables: dict[str, Any]
    | Callable[[Transcript], dict[str, Any]]
    | None = None,
    preprocessor: MessagesPreprocessor[Transcript] | None = None,
    model: str | Model | None = None,
    model_role: str | None = None,
    retry_refusals: bool | int = 3,
    name: str | None = None,
    content: TranscriptContent | None = None,
    context_window: int | None = None,
    compaction: Literal["all", "last"] | int = "all",
    depth: int | None = None,
    reducer: Callable[[list[Result]], Awaitable[Result]] | None = None,
) -> Scanner[Transcript]:
    """Create a scanner that uses an LLM to scan transcripts.

    This scanner presents a conversation transcript to an LLM along with a
    custom prompt and answer specification, enabling automated analysis of
    conversations for specific patterns, behaviors, or outcomes.

    Messages are extracted via ``transcript_messages()``, which automatically
    selects the best strategy (timelines → events → raw messages) and respects
    context window limits. Each segment is scanned independently with globally
    unique message numbering (``[M1]``, ``[M2]``, ...) across all segments.

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
            Controls exclusion of system messages, reasoning tokens, and tool calls.
            Defaults to removing system messages. Note: custom ``transform``
            functions that accept a ``Transcript`` are not supported when
            ``context_window`` or timeline scanning produces multiple segments,
            as the transform receives ``list[ChatMessage]`` per segment.
        model: Optional model specification.
            Can be a model name string or ``Model`` instance. If None, uses the default model.
        model_role: Optional model role for role-based model resolution.
            When set, the model is resolved via ``get_model(model, role=model_role)``
            at scan time, allowing deferred role resolution when roles are not yet
            available at scanner construction time.
        retry_refusals: Retry model refusals. Pass an ``int`` for number of retries (defaults to 3). Pass ``False`` to not retry refusals. If the limit of refusals is exceeded then a ``RuntimeError`` is raised.
        name: Scanner name.
            Use this to assign a name when passing ``llm_scanner()`` directly to ``scan()`` rather than delegating to it from another scanner.
        content: Override the transcript content filters for this scanner.
            For example, ``TranscriptContent(timeline=True)`` requests timeline
            data so the scanner can process span-level segments.
        context_window: Override the model's context window size for chunking.
            When set, transcripts exceeding this limit are split into multiple
            segments, each scanned independently.
        compaction: How to handle compaction boundaries when extracting
            messages from events. ``"all"`` (default) scans all compaction
            segments; ``"last"`` scans only the most recent.
        depth: Maximum depth of the span tree to process when timelines
            are present. ``None`` (default) processes all depths. Ignored
            for events-only or messages-only transcripts.
        reducer: Custom reducer for aggregating multi-segment results.
            Accepts any ``Callable[[list[Result]], Awaitable[Result]]``.
            If None, uses a default reducer based on the answer type
            (e.g., ``ResultReducer.any`` for boolean, ``ResultReducer.mean``
            for numeric). Standard reducers are available on
            :class:`ResultReducer`. Timeline and resultset answers bypass
            reduction and return a resultset.

    Returns:
        A ``Scanner`` function that analyzes Transcript instances and returns
        ``Result`` (single segment) or ``list[Result]`` (multiple segments).
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
        # Resolve the model once — defers role resolution to scan time
        resolved_model = get_model(model, role=model_role)

        # Shared numbering scope across all segments
        messages_as_str_fn, extract_references = message_numbering(
            preprocessor=cast(
                MessagesPreprocessor[list[ChatMessage]] | None, preprocessor
            ),
        )

        results: list[Result] = []
        async for segment in transcript_messages(
            transcript,
            messages_as_str=messages_as_str_fn,
            model=resolved_model,
            context_window=context_window,
            compaction=compaction,
            depth=depth,
        ):
            prompt = await render_scanner_prompt(
                template=template,
                template_variables=template_variables,
                transcript=transcript,
                messages=segment.text,
                question=question,
                answer=resolved_answer,
            )
            results.append(
                await generate_answer(
                    prompt,
                    answer,
                    model=resolved_model,
                    retry_refusals=retry_refusals,
                    extract_references=extract_references,
                    value_to_float=value_to_float,
                )
            )

        # single result
        if len(results) == 1:
            return results[0]

        # scenarios where resultset is the natural/expected return type
        elif bool(transcript.timelines) or is_resultset_answer(answer):
            return as_resultset(results)

        # otherwise reduce
        else:
            effective_reducer = reducer or default_reducer(answer)
            return await effective_reducer(results)

    # set name for collection by @scanner if specified
    if name is not None:
        setattr(scan, SCANNER_NAME_ATTR, name)

    # set content override for @scanner to merge into ScannerConfig
    if content is not None:
        setattr(scan, SCANNER_CONTENT_ATTR, content)

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
            message_count=transcript.message_count,
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
