from typing import NamedTuple

DEFAULT_SCANNER_TEMPLATE = """
Here is an LLM conversation between a user and an assistant:

===================================
{messages}
===================================

{answer_prompt}
"""

DEFAULT_EXPLANATION_TEXT = (
    "Your response should include an explanation of your assessment. It should include "
    "the message id's (e.g. '[M2]') to clarify which message(s) you are referring "
    "to."
)


class LLMScannerPrompt(NamedTuple):
    """Prompt for scanner."""

    question: str
    """Question for the scanner to answer."""

    explanation: str = DEFAULT_EXPLANATION_TEXT
    """Prompt the model to explain its answer and to include messages indexes. This variable is used in the generation of the default {answer_prompt}."""

    template: str = DEFAULT_SCANNER_TEMPLATE
    """Overall template for scanner prompt.

    The scanner template may use the following variables:

    - {messages} (transcript message history as string)
    - {answer_prompt} (prompt the model for a specific type of answer and explanation ).
    """


BOOL_ANSWER_TEMPLATE = (
    "Answer the following yes or no question: {question}\n\n"
    "{explanation_text}\n\n"
    "The last line of your response should be of the following format:\n"
    "'ANSWER: xxx' (without quotes) where xxx is the numeric value."
)

NUMBER_ANSWER_TEMPLATE = (
    "Answer the following numeric question: {question}\n\n"
    "{explanation_text}\n\n"
    "The last line of your response should be of the following format:\n"
    "'ANSWER: xxx' (without quotes) where xxx is the numeric value."
)

LABELS_ANSWER_TEMPLATE = (
    "Answer the following multiple choice question: {{question}}\n\n"
    "{formatted_choices}\n\n"
    "{{explanation_text}}\n\n"
    "The last line of your response should be of the following format:\n"
    "'ANSWER: $LETTER' (without quotes) where LETTER is one of {letters}."
)

LABELS_ANSWER_TEMPLATE_MULTI = (
    "Answer the following multiple choice question: {{question}}\n\n"
    "{formatted_choices}\n\n"
    "{{explanation_text}}\n\n"
    "The last line of your response should be of the following format:\n"
    "'ANSWER: $LETTERS' (without quotes) where LETTERS is a comma-separated list of letters from {letters}."
)

STR_ANSWER_TEMPLATE = (
    "Answer the following question: {question}\n\n"
    "{explanation_text}\n\n"
    "The last line of your response should be of the following format:\n"
    "'ANSWER: $TEXT' (without quotes) where TEXT is your answer."
)
