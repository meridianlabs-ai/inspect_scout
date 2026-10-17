import json
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, NamedTuple, cast

from inspect_ai._util.error import PrerequisiteError
from inspect_ai.model import (
    CachePolicy,
    GenerateConfig,
    Model,
    get_model,
)
from inspect_ai.scorer import ValueToFloat
from pydantic import JsonValue

from .._llm_scanner._pipeline import resolve_scan_source, scan_transcript_segments
from .._llm_scanner._reducer import default_reducer, uses_default_model
from .._llm_scanner.types import AnswerSpec
from .._scanner.extract import (
    ExtractReferences,
    MessagesPreprocessor,
    as_messages_preprocessor,
    check_nonce,
    message_numbering,
)
from .._scanner.redact import RedactMode, redact_value, redacting_preprocessor
from .._scanner.result import Result
from .._scanner.scanner import (
    SCANNER_CONTENT_ATTR,
    SCANNER_NAME_ATTR,
    SCANNER_TIMELINE_NEEDED_ATTR,
    Scanner,
    mark_streaming_support,
    scanner,
)
from .._transcript.handle import TranscriptHandle
from .._transcript.messages import _effective_segment_budget
from .._transcript.types import Transcript, TranscriptContent
from ._answers import (
    AnswerMapper,
    JevAnswers,
    JevQuestion,
    answer_mapper,
    apply_value_to_float,
)
from ._provider import JEV_PROVIDER_ATTR, JevInputTooLongError, JevRequest
from ._references import (
    EVIDENCE_RESERVE,
    MAX_EVIDENCE_ROUNDS,
    Evidence,
    best_evidence,
    evidence_requests,
    segment_labels,
)

DEFAULT_JEV_MODEL = "typesafe/jev-1.13.0"
"""Default Jev model: a pinned version, so probability thresholds stay valid."""

LONG_CONTEXT_WINDOW = 250_000
"""Default segment budget (tokens) with Jev's long-context mode."""

STANDARD_CONTEXT_WINDOW = 28_000
"""Default segment budget (tokens) without long-context mode (Jev allows 32k per question)."""

_TRANSCRIPT_NOTE = "Messages are labelled [M#] followed by the role."


@scanner(messages="all")
def jev_scanner(
    *,
    question: str | Callable[[Transcript], Awaitable[str]],
    answer: AnswerSpec,
    criteria: Mapping[str, str] | None = None,
    rubric: Sequence[str] | None = None,
    threshold: float = 0.5,
    references: bool | Literal["all"] = True,
    value_to_float: ValueToFloat | None = None,
    template_variables: dict[str, Any]
    | Callable[[Transcript], dict[str, Any]]
    | None = None,
    preprocessor: MessagesPreprocessor[Transcript] | None = None,
    redact: RedactMode | Literal[False] = "keys",
    model: str | Model | None = None,
    model_role: str | None = None,
    cache: bool | CachePolicy | None = None,
    long_context: bool = True,
    name: str | None = None,
    content: TranscriptContent | None = None,
    context_window: int | None = None,
    timeline: str | None = None,
    compaction: Literal["all", "last"] | int = "all",
    depth: int | None = None,
    reducer: Callable[[list[Result]], Awaitable[Result]] | None = None,
    nonce: str | None = None,
) -> Scanner[Transcript]:
    """Create a scanner that classifies transcripts with a TypeSafe Jev model.

    Jev is a fast, low-cost classification model that returns calibrated
    probabilities rather than generated text. `jev_scanner()` mirrors
    `llm_scanner()` (same segmentation, message numbering, references,
    and result shapes) but asks Jev instead of a generative model.

    Requires the `typesafe-sdk` package and a `TYPESAFE_API_KEY`. No
    generative model is needed.

    Args:
        question: Question for the scanner to answer: a string, or an async
            function of the transcript returning one.
        answer: Answer type: ``"boolean"``, ``"numeric"`` (requires ``rubric``),
            a list of labels, `AnswerMultiLabel`, or `AnswerStructured` with
            boolean / `Literal` / enum fields. ``"string"`` and resultset
            answers need free text and are not supported.
        criteria: Descriptions sent to Jev with the question: ``{"true": ...,
            "false": ...}`` for a boolean answer, or ``{label: description}``
            for labels. Recommended: explicit criteria sharpen answers.
        rubric: Ordered descriptions of score levels (2-10, lowest first) for
            ``answer="numeric"``; the value is the expected score.
        threshold: Probability at or above which a yes/no (boolean, multi-label,
            or structured boolean field) counts as yes.
        references: Cite evidence messages: ``True`` cites the single best
            message per segment, ``"all"`` cites every matching message (one
            extra request per citation, up to 8 per segment), ``False`` cites
            none. Boolean answers cite only when the answer is yes.
        value_to_float: Optional function to convert the answer value to a float.
        template_variables: Extra context sent to Jev alongside the transcript
            (a dict, or a function of the transcript returning one).
        preprocessor: Transform conversation messages before analysis (a
            `MessagesPreprocessor`, or a dict of its options as in scan job YAML).
        redact: Redact secrets from messages before sending them: ``"keys"``
            (default) removes keys and credentials, ``"all"`` also removes email
            addresses, ``False`` sends messages unchanged.
        model: Jev model, e.g. ``"typesafe/jev-1.13.0"`` (the default).
        model_role: Optional model role for role-based model resolution.
        cache: Cache Jev responses (Inspect's generate cache): ``True`` or a
            `CachePolicy`. Jev is not exactly deterministic, so caching makes
            re-runs reproducible.
        long_context: Use Jev's long-context mode (up to ~262k tokens per
            request). When ``False``, segments are limited to ~28k tokens.
        name: Scanner name.
        content: Override the transcript content filters for this scanner.
        context_window: Override the segment budget (tokens). With references on,
            about 8k tokens are reserved for evidence questions, so the budget
            must be larger than that.
        timeline: Name of the timeline to extract messages from (e.g. a
            stored ``"target"`` timeline). Setting it loads timelines, so no
            ``content`` override is needed.
        compaction: How to handle compaction boundaries.
        depth: Maximum nesting level of timeline spans to scan.
        reducer: Custom reducer for multi-segment results. `ResultReducer.llm()`
            needs an explicit ``model`` (it would otherwise use the default model).
        nonce: Message header nonce (see `llm_scanner()`).

    Returns:
        A `Scanner` that returns a `Result` per transcript (or a resultset for
        multi-span timelines).

    Raises:
        ValueError: If the answer spec, criteria, rubric, or reducer cannot be
            answered by Jev.
    """
    check_nonce(nonce)
    if references not in (True, False, "all"):
        raise ValueError(
            f'references must be True, False, or "all" (got {references!r}).'
        )
    budget = context_window or (
        LONG_CONTEXT_WINDOW if long_context else STANDARD_CONTEXT_WINDOW
    )
    if references and budget <= EVIDENCE_RESERVE:
        raise ValueError(
            f"context_window must exceed {EVIDENCE_RESERVE} tokens (reserved for "
            "evidence questions) when references are on."
        )
    mapper = answer_mapper(
        answer,
        criteria=criteria,
        rubric=rubric,
        threshold=threshold,
        value_to_float=value_to_float,
    )
    if reducer is not None and uses_default_model(reducer):
        raise ValueError(
            "jev_scanner cannot use ResultReducer.llm() without a model: it would "
            "use the default (generative) model. Pass ResultReducer.llm(model=...), "
            "use another ResultReducer, or llm_scanner()/cascade_scanner()."
        )
    segment_reducer = _with_segment_metadata(
        reducer or default_reducer(answer), aggregate_p=reducer is None
    )
    effective_preprocessor = redacting_preprocessor(
        as_messages_preprocessor(preprocessor), redact
    )
    content_has_events = content is not None and content.events is not None
    full_transcript_needed = (
        callable(question)
        or callable(template_variables)
        or timeline is not None
        or (content is not None and content.timeline is not None)
    )
    generate_config = (
        GenerateConfig(cache=cache) if cache is not None else GenerateConfig()
    )

    async def scan(transcript: Transcript | TranscriptHandle) -> Result:
        source = await resolve_scan_source(
            transcript,
            full_transcript_needed=full_transcript_needed,
            scanner_name="jev_scanner",
        )
        resolved_model = get_model(model or DEFAULT_JEV_MODEL, role=model_role)
        if not getattr(resolved_model.api, JEV_PROVIDER_ATTR, False):
            raise PrerequisiteError(
                f"jev_scanner requires a Jev model (typesafe/<model>), got "
                f"{resolved_model}: other models would be sent Jev requests."
            )
        resolved_question = (
            question if isinstance(question, str) else await question(source.transcript)
        )
        context = (
            template_variables(source.transcript)
            if callable(template_variables)
            else template_variables
        )
        if context and redact is not False:
            context = redact_value(context, redact)
        prompt_reserve = await resolved_model.count_tokens(
            json.dumps(
                {"context": context, "questions": mapper.questions(resolved_question)},
                default=str,
            )
        ) + (EVIDENCE_RESERVE if references else 0)
        _check_budget(resolved_model, budget, prompt_reserve)

        segment = _SegmentScan(
            model=resolved_model,
            config=generate_config,
            mapper=mapper,
            question=resolved_question,
            context=cast(JsonValue, context) if context else None,
            references=references,
            long_context=long_context,
        )

        async def scan_with_budget(segment_budget: int) -> Result:
            messages_as_str, extract_refs = message_numbering(
                preprocessor=effective_preprocessor, nonce=nonce
            )

            async def scan_segment(messages_str: str) -> Result:
                return await segment.scan(messages_str, extract_refs)

            return await scan_transcript_segments(
                source,
                scan_segment=scan_segment,
                messages_as_str=messages_as_str,
                model=resolved_model,
                context_window=segment_budget,
                timeline=timeline,
                compaction=compaction,
                depth=depth,
                prompt_reserve=prompt_reserve,
                content_has_events=content_has_events,
                answer=answer,
                reducer=segment_reducer,
            )

        try:
            result = await scan_with_budget(budget)
        except JevInputTooLongError:
            # Token counts are a character estimate; if Jev still finds a
            # segment too long, re-segment once at half the budget (this
            # re-sends every segment, unless `cache` is on).
            _check_budget(resolved_model, budget // 2, prompt_reserve)
            result = await scan_with_budget(budget // 2)
        return _finalize(result, value_to_float)

    if name is not None:
        setattr(scan, SCANNER_NAME_ATTR, name)
    if content is not None:
        setattr(scan, SCANNER_CONTENT_ATTR, content)
    # Readers only return stored timelines when the content requests them, so
    # a named timeline would otherwise never be found.
    if timeline is not None:
        setattr(scan, SCANNER_TIMELINE_NEEDED_ATTR, True)
    mark_streaming_support(scan, not full_transcript_needed)

    return scan


class _JevResponse(NamedTuple):
    answers: JevAnswers
    model: str
    input_tokens: int
    seconds: float


class _Citations(NamedTuple):
    cited: list[Evidence]
    input_tokens: int
    seconds: float


@dataclass(frozen=True)
class _SegmentScan:
    """Answers one rendered segment with Jev, citing evidence messages."""

    model: Model
    config: GenerateConfig
    mapper: AnswerMapper
    question: str
    context: JsonValue
    references: bool | Literal["all"]
    long_context: bool

    async def scan(self, messages_str: str, extract_refs: ExtractReferences) -> Result:
        state: dict[str, JsonValue] = {
            "note": _TRANSCRIPT_NOTE,
            "transcript": messages_str,
        }
        if self.context:
            state["context"] = self.context
        labels = segment_labels(messages_str, extract_refs) if self.references else []

        questions = self.mapper.questions(self.question)
        first_evidence: list[dict[str, JevQuestion]] = []
        if labels and self.mapper.evidence_with_answer:
            # The evidence target is known up front ("that the answer is yes"),
            # so the first evidence request rides along with the answer.
            target = self.mapper.map(_placeholder_answers(questions)).evidence_target
            first_evidence = evidence_requests(self.question, target, labels)
            questions |= first_evidence[0]
        response = await self._ask(state, questions)
        mapped = self.mapper.map(response.answers)

        citations = _Citations([], 0, 0.0)
        if labels and mapped.positive:
            citations = await self._cite(
                state,
                labels,
                mapped.evidence_target,
                response,
                first_evidence[1:] if first_evidence else None,
            )
        cited_refs = " ".join(f"[{e.label}]" for e in citations.cited)
        explanation = mapped.summary + (
            f" Evidence: {cited_refs}" if cited_refs else ""
        )
        return Result(
            value=mapped.value,
            answer=mapped.answer,
            explanation=explanation,
            label=mapped.label,
            metadata={
                **mapped.metadata,
                "evidence": {e.label: e.probability for e in citations.cited},
                "model": response.model,
                "input_tokens": response.input_tokens + citations.input_tokens,
                "seconds": round(response.seconds + citations.seconds, 3),
                "long_context": self.long_context,
            },
            # Only the cited labels: label or criteria text may contain "[M#]".
            references=extract_refs(cited_refs),
        )

    async def _cite(
        self,
        state: dict[str, JsonValue],
        labels: list[str],
        target: str,
        first: _JevResponse,
        remaining_first: list[dict[str, JevQuestion]] | None,
    ) -> _Citations:
        """Find the best evidence message (or, with ``"all"``, every occurrence)."""
        input_tokens, seconds = 0, 0.0
        if remaining_first is None:
            # Evidence was not asked with the answer: ask now, naming the answer.
            batch = await self._ask_all(
                state, evidence_requests(self.question, target, labels)
            )
            responses = batch.responses
        else:
            batch = await self._ask_all(state, remaining_first)
            responses = [first.answers, *batch.responses]
        input_tokens += batch.input_tokens
        seconds += batch.seconds

        cited: list[Evidence] = []
        best = best_evidence(responses)
        while best is not None:
            cited.append(best)
            if self.references != "all" or len(cited) >= MAX_EVIDENCE_ROUNDS:
                break
            found = [e.label for e in cited]
            requests = evidence_requests(self.question, target, labels, exclude=found)
            if not requests:
                break
            batch = await self._ask_all(
                {**state, "already_found": list[JsonValue](found)}, requests
            )
            input_tokens += batch.input_tokens
            seconds += batch.seconds
            best = best_evidence(batch.responses)
        return _Citations(cited, input_tokens, seconds)

    async def _ask_all(
        self, state: dict[str, JsonValue], requests: list[dict[str, JevQuestion]]
    ) -> "_Batch":
        responses = [await self._ask(state, questions) for questions in requests]
        return _Batch(
            responses=[r.answers for r in responses],
            input_tokens=sum(r.input_tokens for r in responses),
            seconds=sum(r.seconds for r in responses),
        )

    async def _ask(
        self, state: dict[str, JsonValue], questions: dict[str, JevQuestion]
    ) -> _JevResponse:
        request = JevRequest(
            state=state, questions=questions, long_context=self.long_context
        )
        output = await self.model.generate(
            json.dumps(request, default=str), config=self.config
        )
        metadata = output.metadata or {}
        if "answers" not in metadata:
            raise RuntimeError(f"Model {self.model} did not return Jev answers.")
        return _JevResponse(
            answers=cast(JevAnswers, metadata["answers"]),
            model=output.model,
            input_tokens=output.usage.input_tokens if output.usage else 0,
            seconds=output.time or 0.0,
        )


class _Batch(NamedTuple):
    responses: list[JevAnswers]
    input_tokens: int
    seconds: float


def _check_budget(model: Model, budget: int, prompt_reserve: int) -> None:
    if (
        _effective_segment_budget(
            model=model, context_window=budget, prompt_reserve=prompt_reserve
        )
        <= 0
    ):
        raise PrerequisiteError(
            f"jev_scanner questions need ~{prompt_reserve} tokens, more than the "
            f"segment budget ({budget}). Increase context_window or shorten the "
            "question and context."
        )


def _placeholder_answers(questions: Mapping[str, JevQuestion]) -> JevAnswers:
    """Answers that make a boolean mapper positive, to read its evidence target."""
    return {name: {"noul": 1.0} for name in questions}


def _finalize(result: Result, value_to_float: ValueToFloat | None) -> Result:
    """Apply `value_to_float` after reduction, so reducers see raw values."""
    if value_to_float is None or result.value is None:
        return result
    if result.type == "resultset" and isinstance(result.value, list):
        items = [
            {**item, "value": apply_value_to_float(item["value"], value_to_float)}
            if isinstance(item, dict) and item.get("value") is not None
            else item
            for item in result.value
        ]
        return result.model_copy(update={"value": items})
    return result.model_copy(
        update={"value": apply_value_to_float(result.value, value_to_float)}
    )


def _with_segment_metadata(
    reducer: Callable[[list[Result]], Awaitable[Result]],
    *,
    aggregate_p: bool,
) -> Callable[[list[Result]], Awaitable[Result]]:
    """Wrap a reducer to keep per-segment metadata and aggregate key fields.

    Reducers merge metadata shallowly (the last segment wins). The reduced
    metadata is kept, per-segment metadata is added under ``segments``, and
    ``evidence`` (merged), ``input_tokens`` and ``seconds`` (summed) are
    aggregated. With the default reducer (``any`` for booleans), ``p`` is the
    maximum over segments, matching the reduced value; a custom reducer's
    ``p`` is left as it produced it.
    """

    async def reduce(results: list[Result]) -> Result:
        if not results:
            return Result(value=None, explanation="No messages to scan.")
        reduced = await reducer(results)
        segments = [r.metadata or {} for r in results]
        metadata: dict[str, Any] = dict(reduced.metadata or {})
        ps = [float(m["p"]) for m in segments if "p" in m]
        if aggregate_p and ps:
            metadata["p"] = max(ps)
        evidence: dict[str, float] = {}
        for m in segments:
            for label, p in (m.get("evidence") or {}).items():
                evidence[label] = max(p, evidence.get(label, 0.0))
        metadata["evidence"] = evidence
        metadata["input_tokens"] = sum(int(m.get("input_tokens", 0)) for m in segments)
        metadata["seconds"] = round(
            sum(float(m.get("seconds", 0.0)) for m in segments), 3
        )
        metadata["segments"] = segments
        return reduced.model_copy(update={"metadata": metadata})

    return reduce
