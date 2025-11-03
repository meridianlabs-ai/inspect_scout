DEFAULT_SCANNER_TEMPLATE = """
Here is an LLM conversation between a user and an assistant:

===================================
{{ messages }}
===================================

{{ answer_prompt }}: {{ question }}

Your response should include an explanation of your assessment. It should include
the message id's (e.g. '[M2]') to clarify which message(s) you are referring
to.

The last line of your response should be of the following format:

{answer_format}
"""

BOOL_ANSWER_PROMPT = "Answer the following yes or no question"
BOOL_ANSWER_FORMAT = "'ANSWER: $VALUE' (without quotes) where $VALUE is yes or no."

NUMBER_ANSWER_PROMPT = "Answer the following numeric question"
NUMBER_ANSWER_FORMAT = (
    "'ANSWER: $NUMBER' (without quotes) where $NUMBER is the numeric value."
)

LABELS_ANSWER_PROMPT = "Answer the following multiple choice question"
LABELS_ANSWER_FORMAT_SINGLE = (
    "'ANSWER: $LETTER' (without quotes) where $LETTER is one of {{ letters }}."
)
LABELS_ANSWER_FORMAT_MULTI = "'ANSWER: $LETTERS' (without quotes) where $LETTERS is a comma-separated list of letters from {{ letters }}."

STR_ANSWER_PROMPT = "Answer the following question"
STR_ANSWER_FORMAT = "'ANSWER: $TEXT' (without quotes) where $TEXT is your answer."
