from functools import reduce
from typing import Iterable

from inspect_ai.analysis._dataframe.extract import message_as_str
from inspect_ai.model import (
    ChatMessage,
    ChatMessageAssistant,
    Model,
    get_model,
)

from .. import Result, Scanner, scanner
from .._scanner.util import _message_id
from .._transcript.types import Transcript
from ._answer import answer_prompt_prefix_suffix, result_for_answer
from ._types import AnswerType, Preprocessor

DEFAULT_SCANNER_TEMPLATE = """
Here is an LLM conversation:

===================================
{messages}
===================================

{answer_prompt}
"""

answer_text = """
Your response should include an explanation of your assessment. It should include the message id's (e.g. '[M2]') to clarify which message(s) you are referring to. The last line of your response should be of the following format:"""


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

    answer_prefix, answer_suffix = answer_prompt_prefix_suffix(answer)

    answer_prompt = f"{answer_prefix}\n{prompt}\n{answer_text} {answer_suffix}"

    async def scan(transcript: Transcript) -> Result:
        filtered_messages = _filter_messages(transcript.messages, preprocessor)
        message_id_map = [_message_id(msg) for msg in filtered_messages]

        resolved_prompt = scanner_template.format(
            messages=_messages_with_ids(filtered_messages),
            prompt=prompt,
            answer_prompt=answer_prompt,
        )

        return result_for_answer(
            answer, await get_model(model).generate(resolved_prompt), message_id_map
        )

    return scan


def _messages_with_ids(messages: list[ChatMessage]) -> str:
    """Format messages with 1-based local message IDs prepended.

    Args:
        messages: List of chat messages to format

    Returns:
        Formatted string with each message prefixed by [Message N] where N is 1-based
    """
    return "\n".join(
        f"[M{idx}] {message_as_str(message)}"
        for idx, message in enumerate(messages, start=1)
    )


def _filter_messages(
    messages: Iterable[ChatMessage], preprocessor: Preprocessor
) -> list[ChatMessage]:
    """Filter transcript messages based on preprocessor settings."""

    def _processed_assistant_message(msg: ChatMessageAssistant) -> ChatMessageAssistant:
        filtered_content = (
            [c for c in msg.content if c.type != "reasoning"]
            if preprocessor.exclude_reasoning and isinstance(msg.content, list)
            else None
        )
        remove_tool_calls = preprocessor.exclude_tool_calls and bool(msg.tool_calls)

        if filtered_content is None and not remove_tool_calls:
            return msg

        return msg.model_copy(
            update=(
                {"content": filtered_content}
                if filtered_content is not None
                else {} | {"tool_calls": None if remove_tool_calls else {}}
            )
        )

    def process_message(
        accum: list[ChatMessage], msg: ChatMessage
    ) -> list[ChatMessage]:
        # Skip system messages if configured
        if preprocessor.exclude_system and msg.role == "system":
            return accum

        # Handle assistant messages with potential content/tool_calls filtering
        if msg.role == "assistant":
            msg = _processed_assistant_message(msg)

        return accum + [msg]

    return reduce(process_message, messages, [])
