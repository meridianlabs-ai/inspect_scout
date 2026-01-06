import re
from typing import Callable, Literal, Protocol, Sequence

from inspect_ai._util.pattern import ANSWER_PATTERN_LINE, ANSWER_PATTERN_WORD
from inspect_ai._util.text import (
    str_to_float,
    strip_numeric_punctuation,
)
from inspect_ai.model import (
    ModelOutput,
)
from inspect_ai.scorer import ValueToFloat
from inspect_ai.scorer._common import normalize_number
from jinja2 import Template
from pydantic import JsonValue

from inspect_scout._llm_scanner.structured import structured_result
from inspect_scout._llm_scanner.types import AnswerMultiLabel, AnswerStructured

from .._scanner.result import Reference, Result
from .prompt import (
    BOOL_ANSWER_FORMAT,
    BOOL_ANSWER_PROMPT,
    LABELS_ANSWER_FORMAT_MULTI,
    LABELS_ANSWER_FORMAT_SINGLE,
    LABELS_ANSWER_PROMPT,
    NUMBER_ANSWER_FORMAT,
    NUMBER_ANSWER_PROMPT,
    STR_ANSWER_FORMAT,
    STR_ANSWER_PROMPT,
)


def _strip_markdown_formatting(text: str) -> str:
    """Strip common markdown formatting from text."""
    # Remove bold/italic: **text**, *text*, __text__, _text_
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    # Remove inline code: `text`
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text


class Answer(Protocol):
    """Protocol for LLM scanner answer types."""

    @property
    def prompt(self) -> str:
        """Return the answer prompt string."""
        ...

    @property
    def format(self) -> str:
        """Return the answer format string."""
        ...

    def result_for_answer(
        self,
        output: ModelOutput,
        extract_references: Callable[[str], list[Reference]],
        value_to_float: ValueToFloat | None = None,
    ) -> Result:
        """Extract and return the result from model output."""
        ...


def answer_from_argument(
    answer: Literal["boolean", "numeric", "string"]
    | list[str]
    | AnswerMultiLabel
    | AnswerStructured,
) -> Answer:
    match answer:
        case "boolean":
            return _BoolAnswer()
        case "numeric":
            return _NumberAnswer()
        case "string":
            return _StrAnswer()
        case list():
            return _LabelsAnswer(labels=answer)
        case AnswerMultiLabel():
            return _LabelsAnswer(labels=answer.labels, multi_classification=True)
        case AnswerStructured():
            return _StructuredAnswer(answer)
        case _:
            raise ValueError(f"Invalid answer type: {answer}")


class _BoolAnswer(Answer):
    """Answer implementation for yes/no questions."""

    @property
    def prompt(self) -> str:
        return BOOL_ANSWER_PROMPT

    @property
    def format(self) -> str:
        return BOOL_ANSWER_FORMAT

    def result_for_answer(
        self,
        output: ModelOutput,
        extract_references: Callable[[str], list[Reference]],
        value_to_float: ValueToFloat | None = None,
    ) -> Result:
        completion = _strip_markdown_formatting(output.completion)
        match = re.search(ANSWER_PATTERN_WORD, completion, re.IGNORECASE)

        if match:
            answer = match.group(1).lower()
            explanation = completion[: match.start()].strip()
            references = extract_references(explanation)

            # Use a match instead of if/else so that answers other than yes or no flow
            # to the bottom.
            match answer:
                case "yes":
                    return Result(
                        value=True if value_to_float is None else value_to_float(True),
                        answer="Yes",
                        explanation=explanation,
                        references=references,
                    )
                case "no":
                    return Result(
                        value=False
                        if value_to_float is None
                        else value_to_float(False),
                        answer="No",
                        explanation=explanation,
                        references=references,
                    )

        return Result(value=False, explanation=output.completion)


class _NumberAnswer(Answer):
    """Answer implementation for numeric questions."""

    @property
    def prompt(self) -> str:
        return NUMBER_ANSWER_PROMPT

    @property
    def format(self) -> str:
        return NUMBER_ANSWER_FORMAT

    def result_for_answer(
        self,
        output: ModelOutput,
        extract_references: Callable[[str], list[Reference]],
        value_to_float: ValueToFloat | None = None,
    ) -> Result:
        completion = _strip_markdown_formatting(output.completion)
        match = re.search(ANSWER_PATTERN_LINE, completion)

        if match:
            answer = _safe_str_to_float(match.group(1).strip())

            if answer is not None:
                explanation = completion[: match.start()].strip()
                references = extract_references(explanation)
                value = answer if value_to_float is None else value_to_float(answer)

                return Result(
                    value=value,
                    answer=str(answer),
                    explanation=explanation,
                    references=references,
                )

        return Result(value=False, explanation=completion)


class _LabelsAnswer(Answer):
    """Answer implementation for multiple choice questions."""

    def __init__(self, labels: list[str], multi_classification: bool = False) -> None:
        self.labels = labels
        self.multi_classification = multi_classification

    @property
    def prompt(self) -> str:
        return LABELS_ANSWER_PROMPT

    @property
    def format(self) -> str:
        if not self.labels:
            raise ValueError("Must have labels")
        formatted_choices, letters = _answer_options(self.labels)
        format_template = (
            LABELS_ANSWER_FORMAT_MULTI
            if self.multi_classification
            else LABELS_ANSWER_FORMAT_SINGLE
        )
        return Template(format_template).render(
            letters=letters, formatted_choices=formatted_choices
        )

    def result_for_answer(
        self,
        output: ModelOutput,
        extract_references: Callable[[str], list[Reference]],
        value_to_float: ValueToFloat | None = None,
    ) -> Result:
        if not self.labels:
            raise ValueError("Must have labels")

        if self.multi_classification and value_to_float is not None:
            raise NotImplementedError(
                "Multi-classification labels do not support value_to_float"
            )

        # For multi-classification, allow comma-separated values on the line
        pattern = (
            ANSWER_PATTERN_LINE if self.multi_classification else ANSWER_PATTERN_WORD
        )
        match = re.search(pattern, output.completion, re.IGNORECASE)

        if match:
            answer_text = match.group(1).strip()
            explanation = output.completion[: match.start()].strip()
            references = extract_references(explanation)

            # Generate valid characters for all labels
            valid_characters = [_answer_character(i) for i in range(len(self.labels))]

            if self.multi_classification:
                # Parse comma-separated letters
                answer_letters = [
                    letter.strip().upper() for letter in answer_text.split(",")
                ]

                # Filter to valid letters and deduplicate while preserving order
                seen = set()
                valid_letters = []
                for letter in answer_letters:
                    if letter in valid_characters and letter not in seen:
                        valid_letters.append(letter)
                        seen.add(letter)

                # Return result if at least one valid letter found
                if valid_letters:
                    answer_labels: JsonValue = [
                        self.labels[valid_characters.index(letter)]
                        for letter in valid_letters
                    ]
                    return Result(
                        value=answer_labels,
                        answer=answer_text,
                        explanation=explanation,
                        references=references,
                    )
            else:
                # Single classification - existing behavior
                answer_letter = answer_text.upper()
                if answer_letter in valid_characters:
                    index = valid_characters.index(answer_letter)
                    return Result(
                        value=value_to_float(answer_letter)
                        if value_to_float
                        else answer_letter,
                        answer=self.labels[index],
                        explanation=explanation,
                        references=references,
                    )

        return Result(value=None, explanation=output.completion)


class _StrAnswer(Answer):
    """Answer implementation for free-text questions."""

    @property
    def prompt(self) -> str:
        return STR_ANSWER_PROMPT

    @property
    def format(self) -> str:
        return STR_ANSWER_FORMAT

    def result_for_answer(
        self,
        output: ModelOutput,
        extract_references: Callable[[str], list[Reference]],
        value_to_float: ValueToFloat | None = None,
    ) -> Result:
        match = re.search(ANSWER_PATTERN_LINE, output.completion, re.IGNORECASE)

        if match:
            answer_text = match.group(1).strip()
            # Empty or whitespace-only answers are treated as None
            if not answer_text:
                return Result(value=None, explanation=output.completion)

            explanation = output.completion[: match.start()].strip()
            references = extract_references(explanation)

            return Result(
                value=value_to_float(answer_text) if value_to_float else answer_text,
                answer=answer_text,
                explanation=explanation,
                references=references,
            )

        return Result(value=None, explanation=output.completion)


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


class _StructuredAnswer(Answer):
    def __init__(self, answer: AnswerStructured):
        self.answer = answer

    @property
    def prompt(self) -> str:
        return Template(self.answer.answer_prompt).render(
            answer_tool=self.answer.answer_tool
        )

    @property
    def format(self) -> str:
        return Template(self.answer.answer_format).render(
            answer_tool=self.answer.answer_tool
        )

    def result_for_answer(
        self,
        output: ModelOutput,
        extract_references: Callable[[str], list[Reference]],
        value_to_float: ValueToFloat | None = None,
    ) -> Result:
        return structured_result(
            self.answer, output, extract_references, value_to_float
        )
