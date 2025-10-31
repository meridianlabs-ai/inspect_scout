import re
from typing import Sequence

from inspect_ai._util.pattern import ANSWER_PATTERN_WORD
from inspect_ai._util.text import (
    str_to_float,
    strip_numeric_punctuation,
)
from inspect_ai.model import (
    ModelOutput,
)
from inspect_ai.scorer._common import normalize_number

from .._scanner.result import Result
from .types import AnswerType
from .util import extract_references


def answer_portion_template(answer: AnswerType) -> str:
    match answer.type:
        case "bool":
            return (
                "Answer the following yes or no question: {prompt}\n\n"
                "{explanation_text}\n\n"
                "The last line of your response should be of the following format:\n"
                "'ANSWER: xxx' (without quotes) where xxx is the numeric value."
            )
        case "number":
            return (
                "Answer the following numeric question: {prompt}\n\n"
                "{explanation_text}\n\n"
                "The last line of your response should be of the following format:\n"
                "'ANSWER: xxx' (without quotes) where xxx is the numeric value."
            )
        case "labels":
            if not answer.labels:
                raise ValueError("Must have labels")
            formatted_choices, letters = _answer_options(answer.labels)
            return (
                f"Answer the following multiple choice question: {{prompt}}\n\n"
                f"{formatted_choices}\n\n"
                f"{{explanation_text}}\n\n"
                f"The last line of your response should be of the following format:\n"
                f"'ANSWER: $LETTER' (without quotes) where LETTER is one of {letters}."
            )
        case t:
            raise NotImplementedError(f"Support for '{t}' not yet implemented")


def result_for_answer(
    _answer: AnswerType, output: ModelOutput, message_id_map: list[str]
) -> Result:
    match _answer.type:
        case "bool":
            return _bool_result(output, message_id_map)
        case "number":
            return _number_result(output, message_id_map)
        case "labels":
            if not _answer.labels:
                raise ValueError("Must have labels")
            return _labels_result(_answer.labels, output, message_id_map)
        case t:
            raise NotImplementedError(f"Support for '{t}' not yet implemented")


def _bool_result(output: ModelOutput, message_id_map: list[str]) -> Result:
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


def _labels_result(
    labels: Sequence[str], output: ModelOutput, message_id_map: list[str]
) -> Result:
    match = re.search(ANSWER_PATTERN_WORD, output.completion, re.IGNORECASE)

    if match:
        answer_letter = match.group(1).upper()
        explanation = output.completion[: match.start()].strip()
        references = extract_references(explanation, message_id_map)

        # Generate valid characters for all labels
        valid_characters = [_answer_character(i) for i in range(len(labels))]

        # Find if the answer matches any valid character
        if answer_letter in valid_characters:
            index = valid_characters.index(answer_letter)
            return Result(
                value=answer_letter,
                answer=labels[index],
                explanation=explanation,
                references=references,
            )

    return Result(value=None, explanation=output.completion)


def _number_result(output: ModelOutput, message_id_map: list[str]) -> Result:
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
