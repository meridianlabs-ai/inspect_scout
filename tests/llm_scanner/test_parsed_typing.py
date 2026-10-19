"""Static guards for the typed generate_answer()/parse_answer() overloads.

``assert_type()`` is verified by mypy (which runs over tests/) and is a
no-op at runtime, so these calls double as smoke tests of the overloads'
runtime dispatch.
"""

from typing import Any

from inspect_ai.model import ModelOutput
from inspect_scout import AnswerMultiLabel, AnswerSpec, AnswerStructured, parse_answer
from inspect_scout._scanner.result import Reference, Result
from pydantic import BaseModel, Field
from typing_extensions import assert_type


class Detection(BaseModel):
    behavior: str = Field(description="behavior observed")
    explanation: str = Field(description="why")


def _no_refs(_text: str) -> list[Reference]:
    return []


def _output(completion: str) -> ModelOutput:
    return ModelOutput(model="test", completion=completion)


def test_overload_types() -> None:
    text = _output("Reason.\n\nANSWER: Yes")
    detection = _output('{"behavior": "b", "explanation": "e"}')
    detections = _output('{"results": [{"behavior": "b", "explanation": "e"}]}')

    result_bool = parse_answer(text, "boolean", _no_refs)
    assert_type(result_bool, Result[bool])
    assert_type(result_bool.parsed, bool | None)

    assert_type(
        parse_answer(_output("R.\n\nANSWER: 1"), "numeric", _no_refs), Result[float]
    )
    assert_type(
        parse_answer(_output("R.\n\nANSWER: x"), "string", _no_refs), Result[str]
    )
    assert_type(parse_answer(text, ["yes", "no"], _no_refs), Result[str])
    assert_type(
        parse_answer(text, AnswerMultiLabel(["yes", "no"]), _no_refs),
        Result[list[str]],
    )

    result_detection = parse_answer(detection, AnswerStructured(Detection), _no_refs)
    assert_type(result_detection, Result[Detection])
    assert_type(result_detection.parsed, Detection | None)

    result_detections = parse_answer(
        detections, AnswerStructured(list[Detection]), _no_refs
    )
    assert_type(result_detections, Result[list[Detection]])

    # a union-typed spec falls back to Result[Any], and typed results are
    # assignable wherever a bare Result is expected
    assert_type(parse_answer(text, _union_spec(), _no_refs), Result[Any])
    bare: Result = result_detection
    assert bare.parsed is not None


def _union_spec() -> AnswerSpec:
    return "boolean"
