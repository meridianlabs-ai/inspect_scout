from pathlib import Path

import yaml
from jinja2 import Environment

from inspect_scout import (
    Result,
    Scanner,
    scanner,
)
from inspect_scout._complex_scanner.template import template
from inspect_scout._transcript.types import Transcript
from inspect_scout._util.jinja import StrictOnUseUndefined


@scanner(messages="all")
def complex_scanner() -> Scanner[Transcript]:
    async def execute(transcript: Transcript) -> Result:
        prompt = _render_prompt(transcript)
        print(prompt)
        return Result(value=0)

    return execute


def _render_prompt(transcript: Transcript) -> str:
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
            transcript="this will be the messages_as_str output",
            **data,
        )
    )
    return rendered
