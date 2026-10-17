import copy
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any, Literal, TypedDict, cast

from inspect_ai._util.error import PrerequisiteError
from inspect_ai.model import CachePolicy, Model, get_model
from inspect_ai.scorer import ValueToFloat
from pydantic import JsonValue

from .._llm_scanner._llm_scanner import llm_scanner
from .._llm_scanner.types import AnswerSpec
from .._scanner.extract import MessagesPreprocessor, as_messages_preprocessor
from .._scanner.redact import RedactMode, redacting_preprocessor
from .._scanner.result import Result, as_resultset
from .._scanner.scanner import (
    SCANNER_NAME_ATTR,
    Scanner,
    mark_streaming_support,
    scanner,
)
from .._transcript.types import Transcript
from ._jev_scanner import jev_scanner


class JevOptions(TypedDict, total=False):
    """`jev_scanner()` arguments for the Jev stage of `cascade_scanner()`."""

    model: str | Model
    model_role: str
    threshold: float
    references: bool | Literal["all"]
    long_context: bool
    cache: bool | CachePolicy
    context_window: int
    compaction: Literal["all", "last"] | int
    depth: int
    nonce: str
    template_variables: dict[str, Any] | Callable[[Transcript], dict[str, Any]]
    value_to_float: ValueToFloat
    reducer: Callable[[list[Result]], Awaitable[Result]]


class LlmOptions(TypedDict, total=False):
    """`llm_scanner()` arguments for the LLM stage of `cascade_scanner()`."""

    model: str | Model
    model_role: str
    template: str | tuple[str, str]
    template_variables: dict[str, Any] | Callable[[Transcript], dict[str, Any]]
    cache: bool | CachePolicy
    retry_refusals: bool | int
    context_window: int
    compaction: Literal["all", "last"] | int
    depth: int
    nonce: str
    value_to_float: ValueToFloat
    reducer: Callable[[list[Result]], Awaitable[Result]]


class EscalateRules(TypedDict, total=False):
    """`cascade_scanner()` escalation rules; any matching rule escalates."""

    p_between: Sequence[float]
    """``[lo, hi]``: a yes/no probability (in any segment) within the range."""

    positive: bool
    """A boolean yes, or a non-empty multi-label answer."""

    labels: Sequence[str]
    """The chosen label (or one of the multi-labels) is one of these."""

    confidence_below: float
    """A choice or score confidence below this."""


_DEFAULT_ESCALATE: EscalateRules = {
    "p_between": (0.2, 0.8),
    "positive": True,
    "confidence_below": 0.5,
}

_ESCALATE_KEYS = {"p_between", "positive", "labels", "confidence_below"}


@scanner(messages="all")
def cascade_scanner(
    *,
    question: str | Callable[[Transcript], Awaitable[str]],
    answer: AnswerSpec,
    criteria: Mapping[str, str] | None = None,
    rubric: Sequence[str] | None = None,
    jev: JevOptions | None = None,
    llm: LlmOptions | Literal[False] | None = None,
    escalate: EscalateRules | None = None,
    preprocessor: MessagesPreprocessor[Transcript] | None = None,
    redact: RedactMode | Literal[False] = "keys",
    name: str | None = None,
) -> Scanner[Transcript]:
    """Scan with Jev first, and escalate uncertain or positive cases to an LLM.

    Jev answers every transcript quickly and cheaply; transcripts matching
    the ``escalate`` rules are re-scanned with `llm_scanner()`, whose result
    (with free-text explanation) is returned instead. Both stages use the
    same question, answer type, preprocessor, and redaction.

    Args:
        question: Question for the scanner to answer.
        answer: Answer type (see `jev_scanner()` for the supported types).
        criteria: Jev criteria (see `jev_scanner()`).
        rubric: Rubric for ``answer="numeric"`` (see `jev_scanner()`).
        jev: Extra `jev_scanner()` arguments (e.g. ``model``, ``threshold``,
            ``references``).
        llm: Extra `llm_scanner()` arguments (e.g. ``model``, ``model_role``,
            ``template``); ``None`` (the default) uses the default model. Pass
            ``False`` for review-queue mode: no LLM is called, and transcripts
            that would escalate are flagged with ``metadata["needs_review"]``.
        escalate: Escalation rules (see `EscalateRules`; plain data, so cascades
            work from YAML jobs and resume). Defaults to
            ``{"p_between": [0.2, 0.8], "positive": True, "confidence_below": 0.5}``;
            tune per scanner with validation data.
        preprocessor: Transform conversation messages before analysis (both stages):
            a `MessagesPreprocessor`, or a dict of its options as in scan job YAML.
        redact: Redact secrets before sending messages to either stage (see
            `jev_scanner()`).
        name: Scanner name.

    Returns:
        A `Scanner` whose results carry ``metadata["cascade"]`` with the
        deciding stage, the escalation reasons, and the Jev result.

    Raises:
        ValueError: If ``jev``/``llm`` repeat the shared arguments, or
            ``escalate`` has unknown keys.
    """
    rules = cast(
        dict[str, Any],
        copy.deepcopy(dict(_DEFAULT_ESCALATE if escalate is None else escalate)),
    )
    if unknown := set(rules) - _ESCALATE_KEYS:
        raise ValueError(f"Unknown escalate rules: {sorted(unknown)}")
    _check_escalate(rules)
    shared = {
        "question",
        "answer",
        "preprocessor",
        "redact",
        "name",
        "criteria",
        "rubric",
    }
    # Content filters would only apply to one stage's inner scan, not to what
    # Scout loads for the cascade, so the stages could see different content.
    unsupported = {"content", "timeline"}
    for stage, kwargs in (("jev", jev or {}), ("llm", llm or {})):
        if repeated := shared & set(kwargs):
            raise ValueError(
                f"{stage}= must not repeat shared arguments: {sorted(repeated)}"
            )
        if blocked := unsupported & set(kwargs):
            raise ValueError(
                f"cascade_scanner does not support {stage}={sorted(blocked)}."
            )

    jev_scan = jev_scanner(
        question=question,
        answer=answer,
        criteria=criteria,
        rubric=rubric,
        preprocessor=preprocessor,
        redact=redact,
        **(jev or JevOptions()),
    )
    llm_kwargs: LlmOptions | None = None if llm is False else (llm or LlmOptions())
    llm_scan = (
        None
        if llm_kwargs is None
        else llm_scanner(
            question=_llm_question(question, answer, criteria, rubric),
            answer=answer,
            preprocessor=cast(
                MessagesPreprocessor[Transcript] | None,
                redacting_preprocessor(as_messages_preprocessor(preprocessor), redact),
            ),
            **llm_kwargs,
        )
    )

    async def scan(transcript: Transcript) -> Result:
        if llm_kwargs is not None:
            # Resolve the LLM first, so a missing key or model fails before any
            # Jev tokens are spent.
            try:
                get_model(llm_kwargs.get("model"), role=llm_kwargs.get("model_role"))
            except ValueError as ex:
                raise PrerequisiteError(
                    f"cascade_scanner could not resolve its LLM ({ex}). Pass "
                    'llm={"model": ...}, set a default model, or use llm=False.'
                ) from ex
        jev_result = _as_result(await jev_scan(transcript))
        reasons = escalation_reasons(jev_result, rules)
        cascade: dict[str, JsonValue] = {
            "escalation_reasons": list[JsonValue](reasons),
            "jev": cast(
                JsonValue, jev_result.model_dump(mode="json", exclude={"uuid"})
            ),
        }
        if not reasons:
            return _with_metadata(
                jev_result, {"cascade": {**cascade, "decided_by": "jev"}}
            )
        if llm_scan is None:
            return _with_metadata(
                jev_result,
                {"cascade": {**cascade, "decided_by": "jev"}, "needs_review": True},
            )
        llm_result = _as_result(await llm_scan(transcript))
        return _with_metadata(llm_result, {"cascade": {**cascade, "decided_by": "llm"}})

    if name is not None:
        setattr(scan, SCANNER_NAME_ATTR, name)
    mark_streaming_support(scan, False)
    return scan


def escalation_reasons(result: Result, rules: Mapping[str, Any]) -> list[str]:
    """Which escalation rules a Jev result matches (empty: Jev decides).

    Multi-segment results are checked per segment (``metadata["segments"]``).
    """
    if result.type == "resultset" and isinstance(result.value, list):
        # Multi-span timeline scans: escalate if any span matches a rule.
        reasons: list[str] = []
        for item in result.value:
            if isinstance(item, dict):
                for reason in escalation_reasons(Result.model_validate(item), rules):
                    if reason not in reasons:
                        reasons.append(reason)
        return reasons

    metadata = result.metadata or {}
    segments = cast(list[dict[str, Any]], metadata.get("segments") or [metadata])
    reasons = []

    if (bounds := rules.get("p_between")) is not None:
        lo, hi = float(bounds[0]), float(bounds[1])
        if any(
            lo <= p <= hi
            for segment in segments
            for p in _yes_no_probabilities(segment)
        ):
            reasons.append("p_between")
    if rules.get("positive") and (
        result.value is True
        # a boolean whose value was converted by value_to_float
        or (result.answer == "Yes" and any("p" in segment for segment in segments))
        or (isinstance(result.value, list) and len(result.value) > 0)
    ):
        reasons.append("positive")
    if (labels := rules.get("labels")) and (
        result.answer in labels
        or (isinstance(result.value, list) and any(v in labels for v in result.value))
    ):
        reasons.append("labels")
    if (floor := rules.get("confidence_below")) is not None and any(
        c < float(floor) for segment in segments for c in _confidences(segment)
    ):
        reasons.append("confidence_below")
    return reasons


def _yes_no_probabilities(segment: Mapping[str, Any]) -> list[float]:
    if "p" in segment:
        return [float(segment["p"])]
    if "threshold" in segment and isinstance(segment.get("probabilities"), dict):
        return [float(p) for p in segment["probabilities"].values()]  # multi-label
    fields = segment.get("fields")
    if isinstance(fields, dict):
        return [
            float(f["p"]) for f in fields.values() if isinstance(f, dict) and "p" in f
        ]
    return []


def _confidences(segment: Mapping[str, Any]) -> list[float]:
    if "confidence" in segment:
        return [float(segment["confidence"])]
    fields = segment.get("fields")
    if isinstance(fields, dict):
        return [
            float(f["confidence"])
            for f in fields.values()
            if isinstance(f, dict) and "confidence" in f
        ]
    return []


def _with_metadata(result: Result, extra: dict[str, JsonValue]) -> Result:
    return result.model_copy(update={"metadata": {**(result.metadata or {}), **extra}})


def _as_result(result: Result | list[Result]) -> Result:
    return as_resultset(result) if isinstance(result, list) else result


def _llm_question(
    question: str | Callable[[Transcript], Awaitable[str]],
    answer: AnswerSpec,
    criteria: Mapping[str, str] | None,
    rubric: Sequence[str] | None,
) -> str | Callable[[Transcript], Awaitable[str]]:
    """The LLM stage's question, carrying Jev's criteria and rubric.

    Without them the stages would answer on different terms (e.g. an LLM
    "numeric" answer on its own scale instead of the rubric's levels).
    """
    guidance = _criteria_guidance(answer, criteria, rubric)
    if not guidance:
        return question
    if isinstance(question, str):
        return f"{question}\n\n{guidance}"
    question_fn = question

    async def with_guidance(transcript: Transcript) -> str:
        return f"{await question_fn(transcript)}\n\n{guidance}"

    return with_guidance


def _criteria_guidance(
    answer: AnswerSpec,
    criteria: Mapping[str, str] | None,
    rubric: Sequence[str] | None,
) -> str:
    lines: list[str] = []
    if answer == "numeric" and rubric:
        lines.append(f"Answer with a number from 0 to {len(rubric) - 1} on this scale:")
        lines += [f"{i}: {level}" for i, level in enumerate(rubric)]
    elif answer == "boolean" and criteria:
        if desc := criteria.get("true"):
            lines.append(f"Answer yes if: {desc}")
        if desc := criteria.get("false"):
            lines.append(f"Answer no if: {desc}")
    elif criteria:
        lines.append("Label meanings:")
        lines += [f"- {label}: {desc}" for label, desc in criteria.items()]
    return "\n".join(lines)


def _check_escalate(rules: Mapping[str, Any]) -> None:
    """Validate escalation rule values when the scanner is built."""
    if (bounds := rules.get("p_between")) is not None:
        if (
            not isinstance(bounds, list | tuple)
            or len(bounds) != 2
            or not all(isinstance(b, int | float) for b in bounds)
            or not 0 <= bounds[0] <= bounds[1] <= 1
        ):
            raise ValueError(
                "escalate p_between must be [lo, hi] with 0 <= lo <= hi <= 1."
            )
    if "positive" in rules and not isinstance(rules["positive"], bool):
        raise ValueError("escalate positive must be true or false.")
    if (labels := rules.get("labels")) is not None and (
        not isinstance(labels, list | tuple)
        or not all(isinstance(x, str) for x in labels)
    ):
        raise ValueError("escalate labels must be a list of label strings.")
    if (floor := rules.get("confidence_below")) is not None and (
        not isinstance(floor, int | float) or not 0 <= floor <= 1
    ):
        raise ValueError("escalate confidence_below must be a number between 0 and 1.")
