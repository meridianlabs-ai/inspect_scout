import re

from inspect_ai._util.pattern import ANSWER_PATTERN_WORD
from inspect_ai._util.text import (
    str_to_float,
    strip_numeric_punctuation,
)
from inspect_ai.model import (
    ModelOutput,
)
from inspect_ai.scorer._common import normalize_number

from inspect_scout import (
    Result,
)

from ._types import AnswerType
from ._util import extract_references


def answer_portion_template(_answer: AnswerType) -> str:
    match _answer.type:
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
