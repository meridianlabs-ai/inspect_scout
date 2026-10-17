"""Map Scout answer specs to Jev questions, and Jev answers back to `llm_scanner`-shaped values."""

import enum
import math
import types
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, Protocol, Union, cast, get_args, get_origin

from inspect_ai.scorer import Value, ValueToFloat
from pydantic import BaseModel, JsonValue

from .._llm_scanner.answer import _answer_character
from .._llm_scanner.structured import get_field_by_name_or_alias
from .._llm_scanner.types import AnswerMultiLabel, AnswerSpec, AnswerStructured

JevQuestion = dict[str, Any]
"""A Jev question in wire form (``{"type": "noul" | "choice" | "score", ...}``)."""

JevAnswers = Mapping[str, Mapping[str, Any]]
"""Jev answers in wire form, keyed by question name."""

MAX_CHOICE_OPTIONS = 255
"""Jev's limit on options per choice question."""


@dataclass(frozen=True)
class MappedAnswer:
    """A Jev answer mapped onto Scout's `Result` fields for one answer spec."""

    value: JsonValue
    answer: str | None
    summary: str
    """First sentence of the explanation (evidence citations are appended)."""
    positive: bool
    """Whether the answer warrants citing evidence (e.g. a boolean ``True``)."""
    metadata: dict[str, JsonValue]
    evidence_target: str
    """What evidence questions ask for, e.g. "for the answer: refused"."""
    label: str | None = None


class AnswerMapper(Protocol):
    """Translates one Scout answer spec to and from Jev questions."""

    @property
    def evidence_with_answer(self) -> bool:
        """Whether evidence can be asked alongside the answer.

        True only when the evidence target does not depend on the answer (a
        boolean asks for evidence "that the answer is yes"); otherwise evidence
        is asked in a follow-up request naming the chosen answer.
        """
        ...

    def questions(self, question: str) -> dict[str, JevQuestion]:
        """Jev questions that answer `question`."""
        ...

    def map(self, answers: JevAnswers) -> MappedAnswer:
        """Map Jev answers (to `questions()`) to Scout result fields."""
        ...


def answer_mapper(
    answer: AnswerSpec,
    *,
    criteria: Mapping[str, str] | None,
    rubric: Sequence[str] | None,
    threshold: float,
    value_to_float: ValueToFloat | None,
) -> AnswerMapper:
    """Create the mapper for `answer`.

    `value_to_float` is only validated here: it is applied to the final
    (reduced) value by the scanner, so reducers see raw values.

    Raises:
        ValueError: If `answer` (or its options) cannot be answered by Jev,
            which returns probabilities over fixed options and no free text.
    """
    if not 0.0 <= threshold <= 1.0:
        raise ValueError(f"threshold must be between 0 and 1 (got {threshold}).")
    match answer:
        case "boolean":
            return _BooleanMapper(_noul_criteria(criteria), threshold)
        case "numeric":
            if rubric is None or not 2 <= len(rubric) <= 10:
                raise ValueError(
                    'jev_scanner(answer="numeric") requires a rubric of 2-10 ordered '
                    "level descriptions, e.g. rubric=['none', 'minor', 'severe']."
                )
            return _NumericMapper(list(rubric))
        case "string":
            raise ValueError(_needs_llm('answer="string"'))
        case list():
            _check_labels(answer, criteria)
            return _LabelsMapper(list(answer), dict(criteria or {}))
        case AnswerMultiLabel():
            if value_to_float is not None:
                raise ValueError(
                    "value_to_float is not supported for multi-label answers."
                )
            _check_labels(answer.labels, criteria)
            return _MultiLabelMapper(
                list(answer.labels), dict(criteria or {}), answer.allow_none, threshold
            )
        case AnswerStructured():
            return _StructuredMapper(answer.type, threshold)
        case _:
            raise ValueError(f"Unsupported answer spec for jev_scanner: {answer!r}")


def _needs_llm(what: str) -> str:
    return (
        f"jev_scanner does not support {what}: Jev returns probabilities over fixed "
        "options and cannot write free text. Use llm_scanner() (requires a "
        "generative model) or cascade_scanner()."
    )


def _noul_criteria(criteria: Mapping[str, str] | None) -> dict[str, str] | None:
    if criteria is None:
        return None
    unknown = set(criteria) - {"true", "false"}
    if unknown:
        raise ValueError(
            "criteria for a boolean answer may only have 'true' and 'false' keys "
            f"(got {sorted(unknown)})."
        )
    return dict(criteria)


def _check_labels(labels: Sequence[str], criteria: Mapping[str, str] | None) -> None:
    _check_options([str(label) for label in labels], "labels")
    unknown = set(criteria or {}) - set(labels)
    if unknown:
        raise ValueError(f"criteria keys must be labels (unknown: {sorted(unknown)}).")


def _check_options(options: Sequence[str], what: str) -> None:
    if not options:
        raise ValueError(f"At least one option is required for {what}.")
    if len(set(options)) != len(options):
        raise ValueError(f"{what.capitalize()} must be unique (as text).")
    if len(options) > MAX_CHOICE_OPTIONS:
        raise ValueError(
            f"Jev supports at most {MAX_CHOICE_OPTIONS} options for {what} (got {len(options)})."
        )


def _level(score: float) -> int:
    """Nearest rubric level, rounding halves up (``round()`` rounds them to even)."""
    return math.floor(score + 0.5)


def apply_value_to_float(
    value: JsonValue, value_to_float: ValueToFloat | None
) -> JsonValue:
    """Apply `value_to_float` to a final result value (if given)."""
    return value_to_float(cast(Value, value)) if value_to_float is not None else value


@dataclass(frozen=True)
class _BooleanMapper:
    criteria: dict[str, str] | None
    threshold: float
    evidence_with_answer: bool = True

    def questions(self, question: str) -> dict[str, JevQuestion]:
        noul: JevQuestion = {"type": "noul", "instructions": question}
        if self.criteria:
            noul["criteria"] = self.criteria
        return {"answer": noul}

    def map(self, answers: JevAnswers) -> MappedAnswer:
        p = float(answers["answer"]["noul"])
        yes = p >= self.threshold
        summary = f"{'Yes' if yes else 'No'} (p={p:.2f})."
        if self.criteria and (desc := self.criteria.get("true" if yes else "false")):
            summary = f"{summary} {desc}"
        return MappedAnswer(
            value=yes,
            answer="Yes" if yes else "No",
            summary=summary,
            positive=yes,
            metadata={"p": p, "threshold": self.threshold},
            evidence_target="that the answer is yes",
        )


@dataclass(frozen=True)
class _NumericMapper:
    rubric: list[str]
    evidence_with_answer: bool = False

    def questions(self, question: str) -> dict[str, JevQuestion]:
        return {
            "answer": {
                "type": "score",
                "instructions": question,
                "criteria": self.rubric,
            }
        }

    def map(self, answers: JevAnswers) -> MappedAnswer:
        a = answers["answer"]
        score = float(a["score"])
        level = self.rubric[min(len(self.rubric) - 1, max(0, _level(score)))]
        probabilities = {str(k): float(v) for k, v in a["probabilities"].items()}
        return MappedAnswer(
            value=score,
            answer=str(score),
            evidence_target=f"for the rating: {level}",
            summary=f"Score {score:.2f} of {len(self.rubric) - 1} "
            f"(confidence {float(a['confidence']):.2f}): {level}.",
            # The lowest level means "none": there is nothing to cite.
            positive=_level(score) > 0,
            metadata={
                "probabilities": dict(probabilities),
                "confidence": float(a["confidence"]),
            },
        )


@dataclass(frozen=True)
class _LabelsMapper:
    labels: list[str]
    descriptions: dict[str, str]
    evidence_with_answer: bool = False

    def questions(self, question: str) -> dict[str, JevQuestion]:
        return {
            "answer": {
                "type": "choice",
                "instructions": question,
                "criteria": {
                    label: self.descriptions.get(label) for label in self.labels
                },
            }
        }

    def map(self, answers: JevAnswers) -> MappedAnswer:
        a = answers["answer"]
        label = str(a["choice"])
        letter = _answer_character(self.labels.index(label))
        confidence = float(a["confidence"])
        probabilities = {str(k): float(v) for k, v in a["probabilities"].items()}
        summary = f"{label} (p={probabilities.get(label, 0.0):.2f}, confidence {confidence:.2f})."
        if desc := self.descriptions.get(label):
            summary = f"{summary} {desc}"
        return MappedAnswer(
            value=letter,
            answer=label,
            evidence_target=f"for the answer: {label}",
            summary=summary,
            positive=True,
            metadata={"probabilities": dict(probabilities), "confidence": confidence},
        )


@dataclass(frozen=True)
class _MultiLabelMapper:
    labels: list[str]
    descriptions: dict[str, str]
    allow_none: bool
    threshold: float
    evidence_with_answer: bool = False

    def questions(self, question: str) -> dict[str, JevQuestion]:
        questions: dict[str, JevQuestion] = {}
        for i, label in enumerate(self.labels):
            noul: JevQuestion = {
                "type": "noul",
                "instructions": f"{question}\n\nDoes this label apply? {label}",
            }
            if desc := self.descriptions.get(label):
                noul["criteria"] = {"true": desc}
            questions[f"label_{i}"] = noul
        return questions

    def map(self, answers: JevAnswers) -> MappedAnswer:
        ps = [float(answers[f"label_{i}"]["noul"]) for i in range(len(self.labels))]
        selected = [i for i, p in enumerate(ps) if p >= self.threshold]
        if not selected and not self.allow_none:
            # Like llm_scanner without allow_none: at least one label applies.
            selected = [max(range(len(ps)), key=ps.__getitem__)]
        chosen = [self.labels[i] for i in selected]
        summary = (
            "Labels: "
            + ", ".join(f"{self.labels[i]} (p={ps[i]:.2f})" for i in selected)
            + "."
            if selected
            else "No labels apply."
        )
        return MappedAnswer(
            value=list[JsonValue](chosen),
            answer=", ".join(_answer_character(i) for i in selected)
            if selected
            else "NONE",
            summary=summary,
            positive=bool(selected),
            evidence_target="for the labels: " + "; ".join(chosen),
            metadata={
                "probabilities": {
                    label: p for label, p in zip(self.labels, ps, strict=True)
                },
                "threshold": self.threshold,
            },
        )


@dataclass(frozen=True)
class _StructuredField:
    name: str
    kind: Literal["bool", "choice", "score"]
    options: list[Any]
    description: str


class _StructuredMapper:
    """Structured answers whose fields are booleans, `Literal`s, or enums."""

    evidence_with_answer = False

    def __init__(self, answer_type: type[Any], threshold: float) -> None:
        if get_origin(answer_type) is list or not (
            isinstance(answer_type, type) and issubclass(answer_type, BaseModel)
        ):
            raise ValueError(_needs_llm("list (resultset) structured answers"))
        self.type: type[BaseModel] = answer_type
        self.threshold = threshold
        self.explanation_field: str | None = None
        self.fields: list[_StructuredField] = []
        for name, info in answer_type.model_fields.items():
            if name == "explanation" or info.alias == "explanation":
                if info.annotation is not str:
                    raise ValueError("A structured 'explanation' field must be a str.")
                self.explanation_field = name
                continue
            if not info.description:
                raise ValueError(
                    f"Field '{name}' of {answer_type.__name__} needs a description "
                    "(it becomes the Jev question)."
                )
            extra = info.json_schema_extra
            rubric = extra.get("rubric") if isinstance(extra, dict) else None
            self.fields.append(
                _structured_field(name, info.annotation, info.description, rubric)
            )
        if not self.fields:
            raise ValueError(f"{answer_type.__name__} has no answerable fields.")

    def questions(self, question: str) -> dict[str, JevQuestion]:
        questions: dict[str, JevQuestion] = {}
        for field in self.fields:
            instructions = f"{question}\n\n{field.description}"
            if field.kind == "bool":
                questions[f"field_{field.name}"] = {
                    "type": "noul",
                    "instructions": instructions,
                }
            elif field.kind == "score":
                questions[f"field_{field.name}"] = {
                    "type": "score",
                    "instructions": instructions,
                    "criteria": field.options,
                }
            else:
                questions[f"field_{field.name}"] = {
                    "type": "choice",
                    "instructions": instructions,
                    "criteria": {str(option): None for option in field.options},
                }
        return questions

    def map(self, answers: JevAnswers) -> MappedAnswer:
        values: dict[str, Any] = {}
        details: dict[str, JsonValue] = {}
        parts: list[str] = []
        for field in self.fields:
            a = answers[f"field_{field.name}"]
            if field.kind == "bool":
                p = float(a["noul"])
                values[field.name] = p >= self.threshold
                details[field.name] = {"p": p}
                parts.append(f"{field.name}={values[field.name]} (p={p:.2f})")
            elif field.kind == "score":
                score = float(a["score"])
                values[field.name] = min(len(field.options) - 1, max(0, _level(score)))
                details[field.name] = {
                    "score": score,
                    "confidence": float(a["confidence"]),
                }
                parts.append(f"{field.name}={values[field.name]} (score {score:.2f})")
            else:
                choice = str(a["choice"])
                values[field.name] = next(o for o in field.options if str(o) == choice)
                details[field.name] = {
                    "probabilities": {
                        str(k): float(v) for k, v in a["probabilities"].items()
                    },
                    "confidence": float(a["confidence"]),
                }
                parts.append(
                    f"{field.name}={choice} (confidence {float(a['confidence']):.2f})"
                )
        summary = "; ".join(parts) + "."
        if self.explanation_field:
            values[self.explanation_field] = summary
        obj = self.type.model_validate(values, by_name=True)

        # Mirror llm_scanner's structured_result(): value/label fields are
        # lifted out; remaining fields become metadata when a value field exists.
        exclude: set[str] = (
            {self.explanation_field} if self.explanation_field else set()
        )
        label_field, label_value = get_field_by_name_or_alias(obj, "label")
        if label_field:
            exclude.add(label_field)
        value_field, value_field_value = get_field_by_name_or_alias(obj, "value")
        value: JsonValue
        result_metadata: dict[str, JsonValue] = {"fields": details}
        if value_field:
            exclude.add(value_field)
            value = value_field_value
            result_metadata.update(
                {
                    k: v
                    for k, v in obj.model_dump(mode="json").items()
                    if k not in exclude
                }
            )
        else:
            value = obj.model_dump(mode="json", exclude=exclude)
        return MappedAnswer(
            value=value,
            answer=None,
            summary=summary,
            positive=True,
            metadata=result_metadata,
            evidence_target=f"for the answer: {summary}",
            label=str(label_value) if label_value is not None else None,
        )


def _structured_field(
    name: str, annotation: Any, description: str, rubric: Any
) -> _StructuredField:
    if annotation is bool:
        return _StructuredField(name, "bool", [True, False], description)
    if annotation is int and rubric is not None:
        if not isinstance(rubric, list) or not 2 <= len(rubric) <= 10:
            raise ValueError(
                f"Field '{name}': a rubric must be a list of 2-10 level descriptions."
            )
        return _StructuredField(
            name, "score", [str(level) for level in rubric], description
        )
    options: list[Any] | None = None
    if get_origin(annotation) is Literal:
        options = list(get_args(annotation))
    elif isinstance(annotation, type) and issubclass(annotation, enum.Enum):
        options = [m.value for m in annotation]
    if options is not None:
        _check_options([str(o) for o in options], f"field '{name}'")
        return _StructuredField(name, "choice", options, description)
    if get_origin(annotation) in (Union, types.UnionType):
        raise ValueError(
            f"Field '{name}': optional/union fields are not supported by jev_scanner."
        )
    raise ValueError(
        _needs_llm(
            f"structured field '{name}' of type {annotation!r} (use bool, Literal, an "
            "Enum, or int with json_schema_extra={'rubric': [...]})"
        )
    )
