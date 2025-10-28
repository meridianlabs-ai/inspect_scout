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


def answer_portion_template(_answer: AnswerType) -> str:
    match _answer.type:
        case "bool":
            return (
                "Answer the following yes or no question: {prompt}\n\n"
                "{explanation_text}\n\n"
                "The last line of your response should be of the following format:\n"
                "'ANSWER: Yes' or 'ANSWER: No' (without quotes)."
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
