# mypy: disable-error-code="unused-ignore"
import json
from pathlib import Path

import yaml
from inspect_ai.model import Model, get_model
from jinja2 import Environment

from .._scanner.extract import messages_as_str
from .._scanner.result import Result
from .._scanner.scanner import Scanner, scanner
from .._transcript.types import Transcript
from .._util.jinja import StrictOnUseUndefined
from .template import template  # type: ignore


@scanner(messages="all")
def complex_scanner(
    model: str | Model | None = None,
) -> Scanner[Transcript]:
    async def execute(transcript: Transcript) -> Result:
        messages_str, extract_references = await messages_as_str(
            transcript.messages, include_ids=True
        )

        model_output = await get_model(model).generate(
            _render_prompt(messages_str, transcript)
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
