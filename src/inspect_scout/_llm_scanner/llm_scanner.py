from functools import reduce
from typing import Literal

from inspect_ai.model import (
    ChatMessage,
    Model,
    get_model,
)
from pydantic import JsonValue

from .._scanner.result import Result
from .._scanner.scanner import Scanner, scanner
from .._scanner.util import _message_id
from .._transcript.types import Transcript
from .answer import answer_portion_template, result_for_answer
from .extract import message_as_str
from .prompt import LLMScannerPrompt
from .types import LLMScannerAnswer, LLMScannerLabels, LLMScannerMessages


@scanner(messages="all")
def llm_scanner(
    *,
    prompt: str | LLMScannerPrompt,
    answer: Literal["bool", "number", "str"] | LLMScannerLabels,
    messages: LLMScannerMessages | None = None,
    model: str | Model | None = None,
) -> Scanner[Transcript]:
    """Create a scanner that uses an LLM to scan transcripts.

    This scanner presents a conversation transcript to an LLM along with a custom prompt and answer specification, enabling automated analysis of conversations for specific patterns, behaviors, or outcomes.

    Args:
        prompt: The prompt to provide to the scanner LLM about
            what to analyze in the conversation (e.g., "Did the assistant refuse the request?"). Pass a `str` to just provide top level instructions; Pass `ScannerPrompt` for further customization.
        answer: Specification of the expected answer format.
            Pass "bool", "number", or "str for simple answer
            of `LLMScannerLabels` for classification.
        template: Optional template for formatting the prompt.
            Must include {messages} and {answer_prompt} placeholders. Defaults to DEFAULT_SCANNER_TEMPLATE
        messages: Filter conversation messages before analysis.
            Controls exclusion of system messages, reasoning tokens, and tool calls. Defaults to filtering system messages.
        model: Optional model specification. Can be a model
            name string or Model instance. If None, uses the default model

    Returns:
        A Scanner function that analyzes Transcript instances and returns Results based on the LLM's assessment according to the specified prompt and answer format
    """
    if messages is None:
        messages = LLMScannerMessages()
    if isinstance(prompt, str):
        prompt = LLMScannerPrompt(instructions=prompt)
    if isinstance(answer, str):
        resolved_answer = LLMScannerAnswer(type=answer)
    else:
        resolved_answer = LLMScannerAnswer(
            type="labels", labels=answer.labels, multi_classification=answer.multiple
        )

    async def scan(transcript: Transcript) -> Result:
        variables = _variables_for_transcript(transcript)

        answer_prompt = answer_portion_template(resolved_answer).format(
            prompt=prompt.template, explanation_text=prompt.explanation, **variables
        )

        messages_str, message_id_map = _messages_with_ids(transcript.messages, messages)

        resolved_prompt = prompt.template.format(
            messages=messages_str,
            prompt=prompt.template,
            answer_prompt=answer_prompt,
            **variables,
        )

        model_output = await get_model(model).generate(resolved_prompt)
        return result_for_answer(resolved_answer, model_output, message_id_map)

    return scan


def _variables_for_transcript(transcript: Transcript) -> dict[str, JsonValue]:
    variables = dict(transcript.variables)
    # remove builtins to avoid conflicts
    variables.pop("prompt", None)
    variables.pop("explanation_text", None)
    variables.pop("messages", None)
    variables.pop("answer_prompt", None)
    # add scores
    variables["score"] = transcript.score or ""
    variables = variables | {
        f"score_{name}": value for name, value in transcript.scores.items()
    }
    return variables


def _messages_with_ids(
    messages: list[ChatMessage], preprocessor: LLMScannerMessages
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
