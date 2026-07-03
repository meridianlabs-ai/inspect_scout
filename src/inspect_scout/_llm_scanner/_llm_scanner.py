import sys
from logging import getLogger
from typing import Any, AsyncIterator, Awaitable, Callable, Literal, cast, overload

import anyio
from inspect_ai._util.content import ContentText
from inspect_ai.model import (
    CachePolicy,
    ChatMessage,
    ChatMessageUser,
    GenerateConfig,
    Model,
    get_model,
)
from inspect_ai.scorer import ValueToFloat
from jinja2 import Environment

from inspect_scout._util.jinja import StrictOnUseUndefined

from .._scanner.extract import MessagesPreprocessor, message_numbering
from .._scanner.result import Result
from .._scanner.scanner import (
    SCANNER_CONTENT_ATTR,
    SCANNER_NAME_ATTR,
    SCANNER_SUPPORTS_STREAMING_ATTR,
    Scanner,
    scanner,
)
from .._transcript.handle import (
    MaterializedTranscriptHandle,
    SpooledTranscriptHandle,
    TranscriptHandle,
)
from .._transcript.messages import (
    _effective_segment_budget,
    stream_segment_messages,
    transcript_messages,
)
from .._transcript.timeline import TimelineMessages
from .._transcript.timeline_stream import (
    _StubSkeletonUnsupported,
    stream_timeline_messages,
)
from .._transcript.types import Transcript, TranscriptContent
from ._reducer import aggregate_results
from .answer import Answer, answer_from_argument
from .generate import generate_answer
from .prompt import (
    DEFAULT_SCANNER_TEMPLATE_PREFIX,
    DEFAULT_SCANNER_TEMPLATE_SUFFIX,
)
from .types import AnswerSpec

if sys.version_info < (3, 11):
    from exceptiongroup import ExceptionGroup

logger = getLogger(__name__)

# Maximum number of segments scanned concurrently per transcript. Bounds
# in-flight model calls (and hence retained segment memory) so a single
# large transcript cannot spawn one task per segment at once.
_SEGMENT_CONCURRENCY = 4


async def _scan_segments_bounded(
    source: AsyncIterator[tuple[str | None, str]],
    scan_segment: Callable[[str], Awaitable[Result]],
) -> list[tuple[str | None, Result]]:
    """Scan segments from ``source`` with bounded concurrency, preserving order.

    ``source`` yields ``(span_id, messages_str)`` pairs lazily. At most
    ``_SEGMENT_CONCURRENCY`` segments are scanned at a time (a semaphore gates
    task spawning), so a large transcript never spawns one task per segment.
    Results are returned in segment order — reduction is order-sensitive.

    A single failing segment propagates its original exception (not the
    task-group ``ExceptionGroup``), matching the prior ``tg_collect`` behavior.
    """
    window = anyio.Semaphore(_SEGMENT_CONCURRENCY)
    indexed: list[tuple[int, str | None, Result]] = []

    async def scan_bounded(index: int, span_id: str | None, messages_str: str) -> None:
        try:
            indexed.append((index, span_id, await scan_segment(messages_str)))
        finally:
            window.release()

    try:
        async with anyio.create_task_group() as tg:
            index = 0
            async for span_id, messages_str in source:
                await window.acquire()
                tg.start_soon(scan_bounded, index, span_id, messages_str)
                index += 1
    except ExceptionGroup as ex:
        raise ex.exceptions[0] from None

    return [(span_id, r) for _, span_id, r in sorted(indexed, key=lambda t: t[0])]


@overload
def llm_scanner(
    *,
    question: str | Callable[[Transcript], Awaitable[str]],
    answer: AnswerSpec,
    value_to_float: ValueToFloat | None = None,
    template: str | tuple[str, str] | None = None,
    template_variables: dict[str, Any]
    | Callable[[Transcript], dict[str, Any]]
    | None = None,
    preprocessor: MessagesPreprocessor[Transcript] | None = None,
    model: str | Model | None = None,
    model_role: str | None = None,
    cache: bool | CachePolicy | None = None,
    retry_refusals: bool | int = 3,
    name: str | None = None,
    content: TranscriptContent | None = None,
    context_window: int | None = None,
    timeline: str | None = None,
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
    template: str | tuple[str, str],
    template_variables: dict[str, Any]
    | Callable[[Transcript], dict[str, Any]]
    | None = None,
    preprocessor: MessagesPreprocessor[Transcript] | None = None,
    model: str | Model | None = None,
    model_role: str | None = None,
    cache: bool | CachePolicy | None = None,
    retry_refusals: bool | int = 3,
    name: str | None = None,
    content: TranscriptContent | None = None,
    context_window: int | None = None,
    timeline: str | None = None,
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
    template: str | tuple[str, str] | None = None,
    template_variables: dict[str, Any]
    | Callable[[Transcript], dict[str, Any]]
    | None = None,
    preprocessor: MessagesPreprocessor[Transcript] | None = None,
    model: str | Model | None = None,
    model_role: str | None = None,
    cache: bool | CachePolicy | None = None,
    retry_refusals: bool | int = 3,
    name: str | None = None,
    content: TranscriptContent | None = None,
    context_window: int | None = None,
    timeline: str | None = None,
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
            `Transcript.metadata` (e.g. {{ metadata.score }}).

            Pass a `tuple[str, str]` of `(prefix, suffix)` to render the
            prompt as two content blocks. The first block is intended to
            hold the cacheable shared prefix (e.g. preamble + transcript
            messages); the second holds the per-scanner tail (e.g. question
            and answer format). Both templates receive the full variable
            bag. When `template` is `None` (default) or a tuple, the prompt
            is sent as a multi-block user message with `cache_prompt=True`,
            allowing prompt-cache hits across scanners that share the
            same prefix bytes for the same transcript. Passing a single
            `str` keeps the legacy single-block behavior (no caching).
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
        cache: Response caching policy for the judge model call. Pass
            ``True`` for default caching, a :class:`CachePolicy` for explicit
            expiry/scope, or ``None`` (default) for no caching. Threaded
            through to ``model.generate()`` via ``GenerateConfig.cache``.
        retry_refusals: Retry model refusals. Pass an ``int`` for number of retries (defaults to 3). Pass ``False`` to not retry refusals. If the limit of refusals is exceeded then a ``RuntimeError`` is raised.
        name: Scanner name.
            Use this to assign a name when passing ``llm_scanner()`` directly to ``scan()`` rather than delegating to it from another scanner.
        content: Override the transcript content filters for this scanner.
            For example, ``TranscriptContent(timeline=True)`` requests timeline
            data so the scanner can process span-level segments.
        context_window: Override the model's context window size for chunking.
            When set, transcripts exceeding this limit are split into multiple
            segments, each scanned independently.
        timeline: Name of the timeline to extract messages from. ``None``
            (default) uses the transcript's first timeline. Raises
            ``ValueError`` if no timeline with the given name exists.
        compaction: How to handle compaction boundaries when extracting
            messages from events. ``"all"`` (default) scans all compaction
            segments; ``"last"`` scans only the most recent.
        depth: Maximum nesting level of scannable spans to scan when
            timelines are present. ``1`` = top-level agent/solver spans;
            ``2`` = top-level plus their first scannable descendants;
            ``None`` (default) = all depths. Pure container spans (e.g.
            the synthetic root) and utility spans do not consume a
            depth level. Ignored for events-only or messages-only
            transcripts.
        reducer: Custom reducer for aggregating multi-segment results.
            Accepts any ``Callable[[list[Result]], Awaitable[Result]]``.
            If None, uses a default reducer based on the answer type
            (e.g., ``ResultReducer.any`` for boolean, ``ResultReducer.mean``
            for numeric). Standard reducers are available on
            `ResultReducer`. On timeline scans the reducer is
            applied *within* each span before the per-span Results are
            wrapped in a resultset (cross-span attribution is preserved).
            Resultset answers (e.g. ``list[Model]``) bypass reduction and
            return a resultset directly.

    Returns:
        A ``Scanner`` function that analyzes Transcript instances and returns
        ``Result`` (single segment) or ``list[Result]`` (multiple segments).
    """
    # Resolve template form once at factory time.
    # - None or tuple: structured 2-block render with cache_prompt=True.
    # - str: legacy single-block render, behavior unchanged.
    resolved_template: str | tuple[str, str]
    if template is None:
        resolved_template = (
            DEFAULT_SCANNER_TEMPLATE_PREFIX,
            DEFAULT_SCANNER_TEMPLATE_SUFFIX,
        )
    else:
        resolved_template = template

    resolved_answer = answer_from_argument(answer)

    # Whether this scanner's effective content includes events. The @scanner
    # decorator declares only messages="all"; a content override is the only
    # way events enter the effective filter. On the streaming handle path this
    # decides whether to route through stream_timeline_messages (events) or
    # stream_segment_messages (messages-only) — mirroring how the materialized
    # transcript_messages path routes on events/timeline presence.
    content_has_events = content is not None and content.events is not None

    # resolve retry_refusals
    retry_refusals = (
        retry_refusals
        if isinstance(retry_refusals, int)
        else 3
        if retry_refusals is True
        else 0
    )

    async def scan(transcript: Transcript | TranscriptHandle) -> Result:
        # A TranscriptHandle streams messages without materializing the full
        # Transcript. We narrow on the concrete handle classes (rather than the
        # @runtime_checkable protocol) because a materialized `Transcript` is
        # NOT a handle, and isinstance against the protocol only checks method
        # presence — the concrete-class check is unambiguous.
        handle: TranscriptHandle | None = (
            transcript
            if isinstance(
                transcript,
                (MaterializedTranscriptHandle, SpooledTranscriptHandle),
            )
            else None
        )

        # Streaming can only work without materializing when the full transcript
        # isn't needed for template resolution or timeline extraction. The
        # preprocessor receives per-segment message lists (see message_numbering)
        # so it is streaming-safe and does NOT force materialization.
        full_transcript_needed = (
            callable(question) or callable(template_variables) or timeline is not None
        )
        if handle is not None and full_transcript_needed:
            # Fall back to the materialized Transcript path.
            transcript = await handle.load()
            handle = None

        # Resolve the model once — defers role resolution to scan time
        resolved_model = get_model(model, role=model_role)

        # For the streaming handle path, template rendering only needs the
        # TranscriptInfo fields (+ metadata) — build a content-empty Transcript
        # to pass wherever a Transcript is structurally required.
        info_transcript: Transcript
        if handle is not None:
            info = handle.info
            info_transcript = Transcript.model_construct(
                **info.model_dump(), messages=[], events=[], timelines=[]
            )
        else:
            # transcript is a Transcript here (handle path exhausted above)
            info_transcript = cast(Transcript, transcript)

        # Shared numbering scope across all segments
        messages_as_str_fn, extract_references = message_numbering(
            preprocessor=cast(
                MessagesPreprocessor[list[ChatMessage]] | None, preprocessor
            ),
        )

        async def scan_segment(messages_str: str) -> Result:
            prompt: str | list[ChatMessage]
            call_config: GenerateConfig | None
            if isinstance(resolved_template, tuple):
                prefix_str, suffix_str = await _render_split_prompt(
                    templates=resolved_template,
                    template_variables=template_variables,
                    transcript=info_transcript,
                    messages=messages_str,
                    question=question,
                    answer=resolved_answer,
                )
                prompt = [
                    ChatMessageUser(
                        content=[
                            ContentText(text=prefix_str),
                            ContentText(text=suffix_str),
                        ]
                    )
                ]
                call_config = GenerateConfig(cache_prompt=True, cache=cache)
            else:
                prompt = await render_scanner_prompt(
                    template=resolved_template,
                    template_variables=template_variables,
                    transcript=info_transcript,
                    messages=messages_str,
                    question=question,
                    answer=resolved_answer,
                )
                call_config = GenerateConfig(cache=cache) if cache is not None else None
            return await generate_answer(
                prompt,
                answer,
                model=resolved_model,
                config=call_config,
                retry_refusals=retry_refusals,
                extract_refs=extract_references,
                value_to_float=value_to_float,
            )

        # Measure template overhead by rendering with messages="" so the
        # segmenter can subtract it from the per-segment budget. Without
        # this, a long template can push the rendered prompt past the
        # model's context window even when the messages alone fit.
        template_tokens = await _template_overhead_tokens(
            template=resolved_template,
            template_variables=template_variables,
            transcript=info_transcript,
            question=question,
            answer=resolved_answer,
            model=resolved_model,
        )
        effective_budget = _effective_segment_budget(
            model=resolved_model,
            context_window=context_window,
            prompt_reserve=template_tokens,
        )
        if effective_budget <= 0:
            raise RuntimeError(
                "Scanner template overhead exceeds the available context window "
                f"budget: template overhead={template_tokens} tokens, available "
                f"budget={effective_budget + template_tokens} tokens (after "
                "tokenizer safety margin). Increase context_window or shorten "
                "the scanner template."
            )

        # Materialized Transcript path: segments stream from transcript_messages
        # (an async generator) so only N are in flight at once. TimelineMessages
        # segments carry a span id for per-span grouping in aggregate_results.
        # Factored out so the events-streaming fallback (below) can reuse it
        # after materializing the handle.
        async def scan_materialized(source_transcript: Transcript) -> Result:
            async def materialized_source() -> AsyncIterator[tuple[str | None, str]]:
                async for seg in transcript_messages(
                    source_transcript,
                    messages_as_str=messages_as_str_fn,
                    model=resolved_model,
                    context_window=context_window,
                    timeline=timeline,
                    compaction=compaction,
                    depth=depth,
                    prompt_reserve=template_tokens,
                ):
                    span_id = seg.span.id if isinstance(seg, TimelineMessages) else None
                    yield span_id, seg.messages_str

            materialized_results = await _scan_segments_bounded(
                materialized_source(), scan_segment
            )
            return await aggregate_results(
                results=materialized_results,
                timeline=bool(source_transcript.timelines),
                answer=answer,
                reducer=reducer,
            )

        # Scan segments through a bounded concurrency window. At most
        # _SEGMENT_CONCURRENCY segments are scanned (and hence retained) at a
        # time, so a large transcript can't spawn one task per segment. The
        # segment source streams lazily on both paths, so unstarted segments
        # aren't materialized either.
        #
        # Order matters for reduction (explanation concatenation, LLM synthesis
        # prompt assembly, majority tiebreak), so each result carries its
        # segment index and is sorted back into order before aggregation.
        if handle is not None and content_has_events:
            # Streaming events path: two-pass event streaming over the handle
            # via stream_timeline_messages, yielding TimelineMessages segments
            # (span ids reused for per-span grouping, exactly like the
            # materialized timeline path).
            async def stream_timeline_source() -> AsyncIterator[tuple[str | None, str]]:
                async for seg in stream_timeline_messages(
                    handle,
                    messages_as_str=messages_as_str_fn,
                    model=resolved_model,
                    context_window=context_window,
                    compaction=compaction,
                    depth=depth,
                    prompt_reserve=template_tokens,
                ):
                    yield seg.span.id, seg.messages_str

            # The stub-skeleton streaming can surface _StubSkeletonUnsupported
            # lazily during segment iteration (uuid-less needed events, or a
            # multi-shot contract violation). The raise happens in pass 1 --
            # while building the stub skeleton and selecting needed uuids,
            # before any segment is yielded and thus before scan_segment runs --
            # so no LLM calls have been made when we catch it here. On fallback
            # we materialize the handle and run the full materialized path from
            # scratch; no scan work is duplicated.
            try:
                results = await _scan_segments_bounded(
                    stream_timeline_source(), scan_segment
                )
            except _StubSkeletonUnsupported as ex:
                logger.info(
                    "Streaming events skeleton unsupported for transcript %s "
                    "(%s); falling back to materialized scan.",
                    handle.info.transcript_id,
                    ex,
                )
                return await scan_materialized(await handle.load())
            # Mirror the materialized path's `timeline=bool(...timelines)`
            # reduction flag: the handle carries events (not named timelines),
            # so info_transcript.timelines is empty — matching how the
            # materialized events-only path (transcript with events, no
            # timelines) aggregates, so both paths produce the same Result.
            return await aggregate_results(
                results=results,
                timeline=bool(info_transcript.timelines),
                answer=answer,
                reducer=reducer,
            )

        if handle is not None:
            # Streaming handle path: messages-only, no timeline. Span id is
            # always None. Only messages_str is passed into the closure so the
            # MessagesSegment isn't retained after start_soon.
            async def stream_source() -> AsyncIterator[tuple[str | None, str]]:
                async for seg in stream_segment_messages(
                    handle.messages(),
                    messages_as_str=messages_as_str_fn,
                    model=resolved_model,
                    context_window=context_window,
                    prompt_reserve=template_tokens,
                ):
                    yield None, seg.messages_str

            results = await _scan_segments_bounded(stream_source(), scan_segment)
            return await aggregate_results(
                results=results,
                timeline=False,
                answer=answer,
                reducer=reducer,
            )

        return await scan_materialized(info_transcript)

    # set name for collection by @scanner if specified
    if name is not None:
        setattr(scan, SCANNER_NAME_ATTR, name)

    # set content override for @scanner to merge into ScannerConfig
    if content is not None:
        setattr(scan, SCANNER_CONTENT_ATTR, content)

    # Opt in to streaming handle input only when the scan can run without the
    # full transcript: no callable question/template_variables (they take a
    # Transcript) and no named-timeline extraction. Events content is now
    # streamable (the handle path consumes it via stream_timeline_messages),
    # so only a content-level `timeline` filter still forces materialization
    # (named-timeline selection needs the full transcript).
    content_forces_materialization = (
        content is not None and content.timeline is not None
    )
    if (
        not callable(question)
        and not callable(template_variables)
        and timeline is None
        and not content_forces_materialization
    ):
        setattr(scan, SCANNER_SUPPORTS_STREAMING_ATTR, True)

    return scan


async def _resolve_template_kwargs(
    *,
    template_variables: dict[str, Any] | Callable[[Transcript], dict[str, Any]] | None,
    transcript: Transcript,
    messages: str,
    question: str | Callable[[Transcript], Awaitable[str]] | None,
    answer: Answer,
) -> dict[str, Any]:
    """Resolve template kwargs once. Awaits any async question callable."""
    template_variables = template_variables or {}
    if callable(template_variables):
        template_variables = template_variables(transcript)

    return {
        "messages": messages,
        "question": question
        if isinstance(question, str | None)
        else await question(transcript),
        "answer_prompt": answer.prompt,
        "answer_format": answer.format,
        "date": transcript.date,
        "task_set": transcript.task_set,
        "task_id": transcript.task_id,
        "task_repeat": transcript.task_repeat,
        "agent": transcript.agent,
        "agent_args": transcript.agent_args,
        "model": transcript.model,
        "model_options": transcript.model_options,
        "score": transcript.score,
        "success": transcript.success,
        "message_count": transcript.message_count,
        "total_time": transcript.total_time,
        "total_tokens": transcript.total_tokens,
        "error": transcript.error,
        "limit": transcript.limit,
        # backward compatibility for existing templates
        # TODO: remove this once users have updated
        "metadata": transcript.metadata
        | {
            "task_name": transcript.task_set,
            "score": transcript.score,
            "model": transcript.model,
            "solver": transcript.agent,
            "error": transcript.error,
            "limit": transcript.limit,
        },
        **template_variables,
    }


def _render_template(template: str, kwargs: dict[str, Any]) -> str:
    # keep_trailing_newline=True preserves whitespace as written so the split
    # render ((prefix, suffix) -> two strings concatenated) produces the same
    # bytes as the combined render of `prefix + suffix`. Without it, Jinja
    # silently strips one trailing newline per render, dropping the blank
    # line between the prefix and suffix when rendered separately.
    return (
        Environment(undefined=StrictOnUseUndefined, keep_trailing_newline=True)
        .from_string(template)
        .render(**kwargs)
    )


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
    kwargs = await _resolve_template_kwargs(
        template_variables=template_variables,
        transcript=transcript,
        messages=messages,
        question=question,
        answer=answer,
    )
    return _render_template(template, kwargs)


async def _render_split_prompt(
    *,
    templates: tuple[str, str],
    template_variables: dict[str, Any] | Callable[[Transcript], dict[str, Any]] | None,
    transcript: Transcript,
    messages: str,
    question: str | Callable[[Transcript], Awaitable[str]] | None,
    answer: Answer,
) -> tuple[str, str]:
    """Render the prefix and suffix templates with a single shared kwarg resolution."""
    kwargs = await _resolve_template_kwargs(
        template_variables=template_variables,
        transcript=transcript,
        messages=messages,
        question=question,
        answer=answer,
    )
    prefix, suffix = templates
    return _render_template(prefix, kwargs), _render_template(suffix, kwargs)


async def _template_overhead_tokens(
    *,
    template: str | tuple[str, str],
    template_variables: dict[str, Any] | Callable[[Transcript], dict[str, Any]] | None,
    transcript: Transcript,
    question: str | Callable[[Transcript], Awaitable[str]] | None,
    answer: Answer,
    model: Model,
) -> int:
    """Count tokens of the rendered prompt template with no messages.

    Used by the segmenter to reserve budget for prompt scaffolding so
    the rendered prompt (template + messages) fits in the context
    window.
    """
    if isinstance(template, tuple):
        prefix_str, suffix_str = await _render_split_prompt(
            templates=template,
            template_variables=template_variables,
            transcript=transcript,
            messages="",
            question=question,
            answer=answer,
        )
        rendered = prefix_str + suffix_str
    else:
        rendered = await render_scanner_prompt(
            template=template,
            template_variables=template_variables,
            transcript=transcript,
            messages="",
            question=question,
            answer=answer,
        )
    return await model.count_tokens(rendered)
