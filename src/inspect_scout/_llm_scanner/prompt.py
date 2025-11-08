DEFAULT_SCANNER_TEMPLATE = """
Here is an LLM conversation between a user and an assistant:

[BEGIN CONVERSATION]
===================================
{{ messages }}
===================================
[END CONVERSATION]

{{ answer_prompt }}

{{ question }}

Your response should include an explanation of your assessment. It should include
the message id's (e.g. '[M2]') to clarify which message(s) you are referring
to.

{{answer_format}}
"""


ANSWER_FORMAT_PREAMBLE = (
    "The last line of your response should be of the following format:\n\n"
)

BOOL_ANSWER_PROMPT = (
    "Answer the following yes or no question about the conversation above:"
)
BOOL_ANSWER_FORMAT = (
    ANSWER_FORMAT_PREAMBLE
    + "'ANSWER: $VALUE' (without quotes) where $VALUE is yes or no."
)

NUMBER_ANSWER_PROMPT = (
    "Answer the following numeric question about the conversation above:"
)
NUMBER_ANSWER_FORMAT = (
    ANSWER_FORMAT_PREAMBLE
    + "'ANSWER: $NUMBER' (without quotes) where $NUMBER is the numeric value."
)

LABELS_ANSWER_PROMPT = (
    "Answer the following multiple choice question about the conversation above:"
)
LABELS_ANSWER_FORMAT_SINGLE = (
    ANSWER_FORMAT_PREAMBLE
    + "'ANSWER: $LETTER' (without quotes) where $LETTER is one of {{ letters }}."
)
LABELS_ANSWER_FORMAT_MULTI = (
    ANSWER_FORMAT_PREAMBLE
    + "'ANSWER: $LETTERS' (without quotes) where $LETTERS is a comma-separated list of letters from {{ letters }}."
)

STR_ANSWER_PROMPT = "Answer the following question about the conversation above:"
STR_ANSWER_FORMAT = (
    ANSWER_FORMAT_PREAMBLE
    + "'ANSWER: $TEXT' (without quotes) where $TEXT is your answer."
)
