import json
from typing import Any, Callable, Type

from inspect_ai.model import GenerateConfig, Model, ResponseSchema, get_model
from inspect_ai.util import json_schema
from jinja2 import Environment

from .._scanner.extract import ContentPreprocessor, messages_as_str
from .._scanner.result import Result
from .._scanner.scanner import SCANNER_NAME_ATTR, Scanner, scanner
from .._transcript.types import Transcript
from .._util.jinja import StrictOnUseUndefined


@scanner(messages="all")
def llm_structured_scanner(
    json_type: Type[Any],
    template: str,
    *,
    extra_variables: dict[str, Any]
    | Callable[[Transcript], dict[str, Any]]
    | None = None,
    content_preprocessor: ContentPreprocessor | None = None,
    model: str | Model | None = None,
    name: str | None = None,
) -> Scanner[Transcript]:
    """Create a scanner that uses an LLM with structured output to scan transcripts.

    This scanner presents a conversation transcript to an LLM along with a custom
    prompt template, using JSON schema to enforce structured output matching the
    specified type. This enables reliable extraction of structured data from
    conversation analysis.

    Args:
        json_type: Python type for structured output. The type is converted to JSON
            schema and enforced via the model's structured output API.
        template: Jinja2 template for scanner prompt.
            The template has access to:
              - {{ messages }} (transcript message history as string)
              - {{ transcript }} (full Transcript object)
              - Any variables provided via `extra_variables`
        extra_variables: Additional template variables. Can be a dict or a function
            that takes a Transcript and returns a dict for dynamic variables based on
            transcript content.
        content_preprocessor: Filter conversation messages before analysis.
            Controls exclusion of system messages, reasoning tokens, and tool calls.
            Defaults to filtering system messages.
        model: Optional model specification. Can be a model
            name string or Model instance. If None, uses the default model
        name: Scanner name (use this to assign a name when passing
            `llm_structured_scanner()` directly to `scan()` rather than delegating to
            it from another scanner).

    Returns:
        A Scanner function that analyzes Transcript instances and returns Results
            containing structured data matching the specified json_type.
    """
    config = GenerateConfig(
        response_schema=ResponseSchema(
            name="JsonResult", json_schema=json_schema(json_type)
        )
    )

    async def scan(transcript: Transcript) -> Result:
        messages_str, extract_references = await messages_as_str(
            transcript.messages,
            content_preprocessor=content_preprocessor,
            include_ids=True,
        )

        prompt = _render_prompt(
            template, extra_variables or {}, messages_str, transcript
        )

        model_output = await get_model(model).generate(prompt, config=config)

        value = json.loads(model_output.completion)

        return Result(
            value=value,
            answer=model_output.completion,
            references=extract_references(model_output.completion),
        )

    # set name for collection by @scanner if specified
    if name is not None:
        setattr(scan, SCANNER_NAME_ATTR, name)

    return scan


def _render_prompt(
    template: str,
    extra_variables: dict[str, Any] | Callable[[Transcript], dict[str, Any]],
    messages: str,
    transcript: Transcript,
) -> str:
    return (
        Environment(undefined=StrictOnUseUndefined)
        .from_string(template)
        .render(
            messages=messages,
            transcript=transcript,
            **(
                extra_variables
                if isinstance(extra_variables, dict)
                else extra_variables(transcript)
            ),
        )
    )
