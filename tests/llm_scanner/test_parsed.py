"""Tests for the ``parsed`` field populated by parse_answer()/generate_answer().

Complements test_parse_answer.py (which covers ``value``/``answer``
extraction): here we verify the typed ``parsed`` answer, its absence on
parse failures, and that it never leaks into serialized output.
"""

import datetime
import pickle
from typing import Any

import pytest
from inspect_ai.model import ModelOutput
from inspect_scout import AnswerMultiLabel, AnswerSpec, AnswerStructured, parse_answer
from inspect_scout._scanner.result import Reference, Result
from pydantic import BaseModel, Field, field_serializer, field_validator


def _no_refs(_text: str) -> list[Reference]:
    return []


def _output(completion: str) -> ModelOutput:
    return ModelOutput(model="test", completion=completion)


class Detection(BaseModel):
    behavior: str = Field(description="behavior observed")
    confidence: float = Field(description="confidence 0-1")


class DetectionWithExplanation(BaseModel):
    behavior: str = Field(description="behavior observed")
    explanation: str = Field(description="why")


@pytest.mark.parametrize(
    ("answer_spec", "completion", "expected_parsed"),
    [
        pytest.param("boolean", "Reason.\n\nANSWER: Yes", True, id="bool-yes"),
        pytest.param("boolean", "Reason.\n\nANSWER: No", False, id="bool-no"),
        pytest.param("numeric", "Count.\n\nANSWER: 7", 7.0, id="numeric"),
        pytest.param("string", "Why.\n\nANSWER: hello", "hello", id="string"),
        pytest.param(["cat", "dog"], "Hmm.\n\nANSWER: B", "dog", id="label-single"),
        pytest.param(
            AnswerMultiLabel(["cat", "dog"]),
            "X.\n\nANSWER: A,B",
            ["cat", "dog"],
            id="label-multi",
        ),
        pytest.param(
            AnswerMultiLabel(["cat", "dog"], allow_none=True),
            "X.\n\nANSWER: NONE",
            [],
            id="label-multi-none",
        ),
    ],
)
def test_parsed_textual(
    answer_spec: AnswerSpec, completion: str, expected_parsed: Any
) -> None:
    result = parse_answer(_output(completion), answer_spec, _no_refs)
    assert result.parsed == expected_parsed
    # pin the type too: bool/float and int/float compare equal in python
    assert type(result.parsed) is type(expected_parsed)


@pytest.mark.parametrize(
    ("answer_spec", "completion"),
    [
        pytest.param("boolean", "no marker here", id="bool"),
        pytest.param("numeric", "ANSWER: not-a-number", id="numeric"),
        pytest.param("string", "nothing", id="string"),
        pytest.param(["cat", "dog"], "Hmm.\n\nANSWER: Z", id="label-single"),
        pytest.param(
            AnswerMultiLabel(["cat", "dog"]),
            "Hmm.\n\nANSWER: Z",
            id="label-multi-invalid",
        ),
        pytest.param(
            # NONE is only a valid answer with allow_none
            AnswerMultiLabel(["cat", "dog"]),
            "Hmm.\n\nANSWER: NONE",
            id="label-multi-none-disallowed",
        ),
    ],
)
def test_parsed_none_on_parse_failure(answer_spec: AnswerSpec, completion: str) -> None:
    result = parse_answer(_output(completion), answer_spec, _no_refs)
    assert result.parsed is None


def test_parsed_unaffected_by_value_to_float() -> None:
    result = parse_answer(
        _output("Reason.\n\nANSWER: Yes"),
        "boolean",
        _no_refs,
        value_to_float=lambda v: 1.0 if v else 0.0,
    )
    assert result.value == 1.0
    assert result.parsed is True


def test_parsed_structured_is_declared_type() -> None:
    result = parse_answer(
        _output('{"behavior": "b", "confidence": 0.9, "explanation": "e"}'),
        AnswerStructured(Detection),
        _no_refs,
    )
    # exactly the declared type (not the augmented explanation subclass)
    assert type(result.parsed) is Detection
    assert result.parsed.confidence == 0.9
    assert result.explanation == "e"


def test_parsed_structured_with_non_roundtripping_serializer() -> None:
    """``parsed`` construction must not go through a serialization round trip.

    Custom field serializers whose output does not re-validate (and
    required excluded fields, below) would break a model_dump() ->
    model_validate() round trip even though the completion is valid.
    """

    class WithSerializer(BaseModel):
        when: datetime.date = Field(description="when it happened")

        @field_serializer("when")
        def _format_when(self, value: datetime.date) -> str:
            return value.strftime("%B %d, %Y")

    result = parse_answer(
        _output('{"when": "2026-01-02", "explanation": "e"}'),
        AnswerStructured(WithSerializer),
        _no_refs,
    )
    assert type(result.parsed) is WithSerializer
    assert result.parsed.when == datetime.date(2026, 1, 2)


def test_parsed_structured_with_required_excluded_field() -> None:
    class WithExcluded(BaseModel):
        shown: str = Field(description="shown")
        hidden: str = Field(exclude=True, description="hidden")

    result = parse_answer(
        _output('{"shown": "s", "hidden": "h", "explanation": "e"}'),
        AnswerStructured(WithExcluded),
        _no_refs,
    )
    assert type(result.parsed) is WithExcluded
    assert result.parsed.hidden == "h"


def test_parsed_structured_keeps_own_explanation_type() -> None:
    result = parse_answer(
        _output('{"behavior": "b", "explanation": "mine"}'),
        AnswerStructured(DetectionWithExplanation),
        _no_refs,
    )
    assert type(result.parsed) is DetectionWithExplanation
    assert result.parsed.explanation == "mine"


def test_parsed_structured_resultset() -> None:
    result = parse_answer(
        _output(
            '{"results": ['
            '{"behavior": "a", "confidence": 0.1, "explanation": "x"},'
            '{"behavior": "b", "confidence": 0.2, "explanation": "y"}]}'
        ),
        AnswerStructured(list[Detection]),
        _no_refs,
    )
    assert result.type == "resultset"
    assert [type(item) for item in result.parsed or []] == [Detection, Detection]
    assert [item.behavior for item in result.parsed or []] == ["a", "b"]


def test_parsed_structured_validators_run_once() -> None:
    """Field validators see wire-format input exactly once.

    A mode="before" validator that parses a wire format is not idempotent:
    constructing ``parsed`` from a second validation pass would crash it.
    """

    class Coords(BaseModel):
        point: list[int] = Field(description="comma separated x,y")

        @field_validator("point", mode="before")
        @classmethod
        def _parse_point(cls, value: str) -> list[int]:
            return [int(part) for part in value.split(",")]

    result = parse_answer(
        _output('{"point": "1,2", "explanation": "e"}'),
        AnswerStructured(Coords),
        _no_refs,
    )
    assert type(result.parsed) is Coords
    assert result.parsed.point == [1, 2]
    assert result.value == {"point": [1, 2]}


def test_parsed_structured_non_idempotent_validator_consistency() -> None:
    """An after-validator runs once, so parsed and value agree."""

    class Tagged(BaseModel):
        name: str = Field(description="name")

        @field_validator("name")
        @classmethod
        def _prefix(cls, value: str) -> str:
            return "prefix:" + value

    result = parse_answer(
        _output('{"name": "x", "explanation": "e"}'),
        AnswerStructured(Tagged),
        _no_refs,
    )
    assert result.parsed is not None
    assert result.parsed.name == "prefix:x"
    assert result.value == {"name": "prefix:x"}


def test_parsed_structured_post_init_runs_once_per_item() -> None:
    calls: list[int] = []

    class Counted(BaseModel):
        x: int = Field(description="x")

        def model_post_init(self, context: Any) -> None:
            calls.append(self.x)

    parse_answer(
        _output('{"x": 1, "explanation": "e"}'), AnswerStructured(Counted), _no_refs
    )
    assert calls == [1]

    calls.clear()
    parse_answer(
        _output(
            '{"results": [{"x": 1, "explanation": "a"}, {"x": 2, "explanation": "b"}]}'
        ),
        AnswerStructured(list[Counted]),
        _no_refs,
    )
    assert calls == [1, 2]


def test_structured_rejects_non_list_generic_alias() -> None:
    with pytest.raises(ValueError, match="list of BaseModel"):
        parse_answer(
            _output('{"behavior": "b", "confidence": 0.9, "explanation": "e"}'),
            AnswerStructured(tuple[Detection, ...]),
            _no_refs,
        )


def test_parsed_excluded_from_serialization() -> None:
    result = parse_answer(
        _output('{"behavior": "b", "confidence": 0.9, "explanation": "e"}'),
        AnswerStructured(Detection),
        _no_refs,
    )
    assert "parsed" not in result.model_dump()
    assert "parsed" not in result.model_dump_json()
    assert "parsed" not in Result.model_json_schema()["properties"]
    # absent on deserialization (in-memory only)
    assert Result.model_validate(result.model_dump()).parsed is None


def test_parsed_dropped_when_pickled() -> None:
    """Pickling drops parsed so results always cross process boundaries.

    Answer models are commonly defined in __main__ or a function body,
    where pickle cannot resolve their class by reference; carrying such an
    instance through the multiprocess scan queues would otherwise silently
    discard the whole result.
    """

    class LocalAnswer(BaseModel):  # not resolvable by pickle by reference
        x: int = Field(description="x")

    result = Result(value=1, answer="one", parsed=LocalAnswer(x=1))
    roundtripped = pickle.loads(pickle.dumps(result))
    assert roundtripped.parsed is None
    assert roundtripped.value == 1
    assert roundtripped.answer == "one"
    # the original is untouched
    assert result.parsed is not None
