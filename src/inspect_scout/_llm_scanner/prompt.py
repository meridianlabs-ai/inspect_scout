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

    instructions: str
    """Scanner instructions."""

    explanation: str = DEFAULT_EXPLANATION_TEXT
    """Prompt the model to explain its answer and to include messages indexes. This variable is used in the generation of the default {answer_prompt}."""

    template: str = DEFAULT_SCANNER_TEMPLATE
    """Overall template for scanner prompt.

    The scanner template may use the following variables:

    - {messages} (transcript messsage history as string)
    - {answer_prompt} (prompt the model for a specific type of answer and explanation ).
    """
