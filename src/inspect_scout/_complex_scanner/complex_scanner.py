# mypy: disable-error-code="unused-ignore"
import json
from pathlib import Path

import yaml
from inspect_ai.model import GenerateConfig, Model, ResponseSchema, get_model
from inspect_ai.util import json_schema
from jinja2 import Environment
from pydantic import BaseModel, RootModel

from .._scanner.extract import messages_as_str
from .._scanner.result import Result
from .._scanner.scanner import Scanner, scanner
from .._transcript.types import Transcript
from .._util.jinja import StrictOnUseUndefined
from .template import template  # type: ignore


class CategoryResult(BaseModel):
    confidence: int
    """your confidence from 1 - 10 as an int"""
    reasoning: str
    """A few sentences explaining your reasoning for assigning the score(s) to this instance, including relevant quotations from the assistant's messages and the most relevant rationale or example from the rubric above that supports this score."""
    message_numbers: list[str]
    """[list of relevant message ids, as a list of strs (e.g. ["[M2]", "[M13]"])]"""
    modifiers: dict[str, int]
    """modifier_id: confidence from 1 - 10 as an int"""


class JsonResult(RootModel[dict[str, CategoryResult]]):
    pass


@scanner(messages="all")
def complex_scanner(
    model: str | Model | None = None,
) -> Scanner[Transcript]:
    config = GenerateConfig(
        response_schema=ResponseSchema(
            name="JsonResult", json_schema=json_schema(JsonResult)
        )
    )

    async def execute(transcript: Transcript) -> Result:
        messages_str, extract_references = await messages_as_str(
            transcript.messages, include_ids=True
        )

        model_output = await get_model(model).generate(
            _render_prompt(messages_str, transcript), config=config
        )

        try:
            value = json.loads(model_output.completion)
        except json.JSONDecodeError:
            print(f"JSONDecodeError decoding '{model_output.completion}'")
            raise

        # TODO: This isn't quite right yet, but...
        return Result(
            value=value,
            answer=model_output.completion,
            references=extract_references(model_output.completion),
        )

    return execute


def _render_prompt(messages: str, transcript: Transcript) -> str:
    path = Path(__file__).parent / "cheating.yml"
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    rendered = (
        Environment(undefined=StrictOnUseUndefined)
        .from_string(template)
        .render(
            sample_name=transcript.metadata["id"] or "unknown",
            user_request=transcript.metadata["input"],
            solution="HACK_SOLUTION",
            total_n_messages=len(transcript.messages),
            target_answer=transcript.metadata["target"],
            final_submission=(
                transcript.messages[-1].text if transcript.messages else "unknown"
            ),
            task_success=transcript.score,
            transcript=messages,
            **data,
        )
    )
    return rendered
