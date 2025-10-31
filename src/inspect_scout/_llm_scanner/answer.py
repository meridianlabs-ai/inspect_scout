import re
from typing import Literal, Protocol, Sequence

from inspect_ai._util.pattern import ANSWER_PATTERN_WORD
from inspect_ai._util.text import (
    str_to_float,
    strip_numeric_punctuation,
)
from inspect_ai.model import (
    ModelOutput,
)
from inspect_ai.scorer._common import normalize_number

from inspect_scout._llm_scanner.types import LLMScannerLabels

from .._scanner.result import Result
from .prompt import BOOL_ANSWER_TEMPLATE, LABELS_ANSWER_TEMPLATE, NUMBER_ANSWER_TEMPLATE
from .util import extract_references


class Answer(Protocol):
    """Protocol for LLM scanner answer types."""

    def answer_portion_template(self) -> str:
        """Return the answer template string."""
        ...

    def result_for_answer(
        self, output: ModelOutput, message_id_map: list[str]
    ) -> Result:
        """Extract and return the result from model output."""
        ...


def answer_from_argument(
    answer: Literal["bool", "number", "str"] | LLMScannerLabels,
) -> Answer:
    if isinstance(answer, str):
        match answer:
            case "bool":
                return _BoolAnswer()
            case "number":
                return _NumberAnswer()
            case "str":
                return _StrAnswer()
            case _:
                raise ValueError(f"Invalid answer type: {answer}")
    else:
        return LabelsAnswer(labels=answer.labels, multi_classification=answer.multiple)


class _BoolAnswer(Answer):
    """Answer implementation for yes/no questions."""

    def answer_portion_template(self) -> str:
        return BOOL_ANSWER_TEMPLATE

    def result_for_answer(
        self, output: ModelOutput, message_id_map: list[str]
    ) -> Result:
        match = re.search(ANSWER_PATTERN_WORD, output.completion, re.IGNORECASE)

        if match:
            answer = match.group(1).lower()
            explanation = output.completion[: match.start()].strip()
            references = extract_references(explanation, message_id_map)

            # Use a match instead of if/else so that answers other than yes or no flow
            # to the bottom.
            match answer:
                case "yes":
                    return Result(
                        value=True,
                        answer="Yes",
                        explanation=explanation,
                        references=references,
                    )
                case "no":
                    return Result(
                        value=False,
                        answer="No",
                        explanation=explanation,
                        references=references,
                    )

        return Result(value=False, explanation=output.completion)


class _NumberAnswer(Answer):
    """Answer implementation for numeric questions."""

    def answer_portion_template(self) -> str:
        return NUMBER_ANSWER_TEMPLATE

    def result_for_answer(
        self, output: ModelOutput, message_id_map: list[str]
    ) -> Result:
        match = re.search(ANSWER_PATTERN_WORD, output.completion)

        if match:
            answer = _safe_str_to_float(match.group(1))

            if answer is not None:
                explanation = output.completion[: match.start()].strip()
                references = extract_references(explanation, message_id_map)

                return Result(
                    value=answer,
                    # TODO: I'm not sure when it makes sense to provide answer
                    # answer="Yes",
                    explanation=explanation,
                    references=references,
                )

        return Result(value=False, explanation=output.completion)


class LabelsAnswer(Answer):
    """Answer implementation for multiple choice questions."""

    def __init__(self, labels: list[str], multi_classification: bool = False) -> None:
        self.labels = labels
        self.multi_classification = multi_classification

    def answer_portion_template(self) -> str:
        if not self.labels:
            raise ValueError("Must have labels")
        formatted_choices, letters = _answer_options(self.labels)
        return LABELS_ANSWER_TEMPLATE.format(
            formatted_choices=formatted_choices, letters=letters
        )

    def result_for_answer(
        self, output: ModelOutput, message_id_map: list[str]
    ) -> Result:
        if not self.labels:
            raise ValueError("Must have labels")
        match = re.search(ANSWER_PATTERN_WORD, output.completion, re.IGNORECASE)

        if match:
            answer_letter = match.group(1).upper()
            explanation = output.completion[: match.start()].strip()
            references = extract_references(explanation, message_id_map)

            # Generate valid characters for all labels
            valid_characters = [_answer_character(i) for i in range(len(self.labels))]

            # Find if the answer matches any valid character
            if answer_letter in valid_characters:
                index = valid_characters.index(answer_letter)
                return Result(
                    value=answer_letter,
                    answer=self.labels[index],
                    explanation=explanation,
                    references=references,
                )

        return Result(value=None, explanation=output.completion)


class _StrAnswer(Answer):
    """Answer implementation for free-text questions (not yet implemented)."""

    def answer_portion_template(self) -> str:
        raise NotImplementedError("Support for 'str' not yet implemented")

    def result_for_answer(
        self, _output: ModelOutput, _message_id_map: list[str]
    ) -> Result:
        raise NotImplementedError("Support for 'str' not yet implemented")


def _safe_str_to_float(maybe_numeric: str) -> float | None:
    try:
        maybe_numeric = strip_numeric_punctuation(maybe_numeric)
        maybe_numeric = normalize_number(maybe_numeric)
        return str_to_float(maybe_numeric)
    except ValueError:
        return None


def _answer_options(choices: Sequence[str]) -> tuple[str, str]:
    r"""
    Returns the `choices` formatted as a multiple choice question, e.g.:

    ["choice 1", "choice 2", "choice 3"] ->
        ("A) choice 1\nB) choice 2\nC) choice 3", "A,B,C"])
    """
    characters = [_answer_character(i) for i in range(len(choices))]
    formatted = "\n".join(
        [f"{char}) {choice}" for char, choice in zip(characters, choices, strict=True)]
    )
    return (formatted, ",".join(characters))


def _answer_character(index: int) -> str:
    r"""
    Helper to go from array index to char, for example:

        0 -> 'A', 1 -> 'B', etc
    """
    return chr(ord("A") + index) if index < 26 else str(index - 25)
