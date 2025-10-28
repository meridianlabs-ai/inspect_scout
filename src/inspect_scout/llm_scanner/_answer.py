import re

from inspect_ai._util.pattern import ANSWER_PATTERN_WORD
from inspect_ai.model import (
    ModelOutput,
)

from inspect_scout import (
    Result,
)

from ._types import AnswerType
from ._util import extract_references


def answer_prompt_prefix_suffix(_answer: AnswerType) -> tuple[str, str]:
    match _answer.type:
        case "bool":
            return (
                "Answer the following yes or no question:",
                "'ANSWER: Yes' or 'ANSWER: No' (without quotes).",
            )
        case t:
            raise NotImplementedError(f"Support for '{t}' not yet implemented")


def result_for_answer(
    _answer: AnswerType, output: ModelOutput, message_id_map: list[str]
) -> Result:
    match _answer.type:
        case "bool":
            return _yes_no_result(output, message_id_map)
        case t:
            raise NotImplementedError(f"Support for '{t}' not yet implemented")


def _yes_no_result(output: ModelOutput, message_id_map: list[str]) -> Result:
    match = re.search(ANSWER_PATTERN_WORD, output.completion, re.IGNORECASE)

    if match:
        answer = match.group(1).lower()
        explanation = output.completion[: match.start()].strip()
        match answer:
            case "yes":
                references = extract_references(explanation, message_id_map)
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
                )

    return Result(value=False, explanation=output.completion)
