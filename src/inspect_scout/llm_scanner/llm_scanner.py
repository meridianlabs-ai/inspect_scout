from functools import reduce

from inspect_ai.model import (
    ChatMessage,
    Model,
    get_model,
)

from .. import Result, Scanner, scanner
from .._scanner.util import _message_id
from .._transcript.types import Transcript
from ._answer import answer_portion_template, result_for_answer
from ._extract import message_as_str
from ._types import AnswerType, Preprocessor

DEFAULT_SCANNER_TEMPLATE = """
Here is an LLM conversation:

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

# class ScannerPrompt(NamedTuple):
#     prompt: str
#     answer_prompt:
#     scanner_template: str | None = None


@scanner(messages="all")
def llm_scanner(
    prompt: str,
    answer: AnswerType,
    scanner_template: str | None = None,
    model: str | Model | None = None,
    preprocessor: Preprocessor | None = None,
) -> Scanner[Transcript]:
    """Create a scanner that uses an LLM to scan transcripts.

    This scanner presents a conversation transcript to an LLM along with a custom
    prompt and answer specification, enabling automated analysis of conversations
    for specific patterns, behaviors, or outcomes.

    Args:
        prompt: The question or instruction to provide to the scanner LLM about
            what to analyze in the conversation (e.g., "Did the assistant refuse
            the request?")
        answer: Specification of the expected answer format - can be a string for
            direct answers, a list of strings for classification, or bool for yes/no questions
        scanner_template: Optional custom template for formatting the prompt. Must
            include {messages} and {answer_prompt} placeholders. Defaults to DEFAULT_SCANNER_TEMPLATE
        model: Optional model specification - can be a model name string or Model
            instance. If None, uses the default model
        preprocessor: Optional Preprocessor to filter conversation messages before
            analysis. Controls exclusion of system messages, reasoning tokens, and
            tool calls. Defaults to no filtering

    Returns:
        A Scanner function that analyzes Transcript instances and returns Results based
        on the LLM's assessment according to the specified prompt and answer format
    """
    if preprocessor is None:
        preprocessor = Preprocessor()
    if scanner_template is None:
        scanner_template = DEFAULT_SCANNER_TEMPLATE
    explanation_text = DEFAULT_EXPLANATION_TEXT

    answer_prompt = answer_portion_template(answer).format(
        prompt=prompt, explanation_text=explanation_text
    )

    async def scan(transcript: Transcript) -> Result:
        messages_str, message_id_map = _messages_with_ids(
            transcript.messages, preprocessor
        )

        resolved_prompt = scanner_template.format(
            messages=messages_str,
            prompt=prompt,
            answer_prompt=answer_prompt,
        )

        model_output = await get_model(model).generate(resolved_prompt)
        return result_for_answer(answer, model_output, message_id_map)

    return scan


def _messages_with_ids(
    messages: list[ChatMessage], preprocessor: Preprocessor
) -> tuple[str, list[str]]:
    """Format messages with 1-based local message IDs prepended.

    Args:
        messages: List of chat messages to format
        preprocessor: Preprocessor settings for filtering messages

    Returns:
        Tuple of (formatted string with [MN] prefixes, list of message IDs for non-excluded messages)
    """

    def reduce_message(
        acc: tuple[list[str], list[str]], message: ChatMessage
    ) -> tuple[list[str], list[str]]:
        formatted_messages, message_id_map = acc
        if (
            msg_str := message_as_str(
                message,
                exclude_tool_usage=preprocessor.exclude_tool_usage,
                exclude_reasoning=preprocessor.exclude_reasoning,
                exclude_system=preprocessor.exclude_system,
            )
        ) is not None:
            message_id_map.append(_message_id(message))
            formatted_messages.append(f"[M{len(message_id_map)}] {msg_str}")
        return formatted_messages, message_id_map

    formatted_messages, message_id_map = reduce(
        reduce_message, messages, (list[str](), list[str]())
    )

    return "\n".join(formatted_messages), message_id_map
