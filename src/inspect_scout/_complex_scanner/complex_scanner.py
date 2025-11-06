# mypy: disable-error-code="unused-ignore"

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, RootModel

from .._llm_scanner.llm_structured_scanner import llm_structured_scanner
from .._scanner.scanner import Scanner, scanner
from .._transcript.types import Transcript
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
def complex_scanner() -> Scanner[Transcript]:
    path = Path(__file__).parent / "cheating.yml"
    with path.open("r", encoding="utf-8") as fh:
        yaml_variables = yaml.safe_load(fh) or {}

    def extra_variables(transcript: Transcript) -> dict[str, Any]:
        return yaml_variables | {
            "solution": f"HACK_SOLUTION for {transcript.id}",
        }

    return llm_structured_scanner(
        JsonResult,
        template,
        extra_variables=extra_variables,
    )
