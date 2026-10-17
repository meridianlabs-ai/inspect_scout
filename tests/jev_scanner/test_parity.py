"""jev_scanner results have llm_scanner's value shapes for equivalent answers."""

from typing import Any, Literal

import pytest
from inspect_ai.model import ChatMessageUser, ModelOutput, get_model
from inspect_ai.tool import ToolCall
from inspect_scout import (
    AnswerMultiLabel,
    AnswerSpec,
    AnswerStructured,
    Result,
    jev_scanner,
    llm_scanner,
)
from inspect_scout._transcript.types import Transcript
from pydantic import BaseModel, Field

LABELS = ["slow", "wrong", "rude"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "answer,llm_reply,jev_text,jev_kwargs",
    [
        ("boolean", "ANSWER: yes", "DESTROY", {}),
        (LABELS, "ANSWER: B", "CHOOSE:wrong", {}),
        (AnswerMultiLabel(labels=LABELS), "ANSWER: A, C", "LABEL:slow LABEL:rude", {}),
        ("numeric", "ANSWER: 2", "SCORE:2", {"rubric": ["none", "some", "severe"]}),
    ],
    ids=["boolean", "labels", "multilabel", "numeric"],
)
async def test_value_and_answer_shapes_match(
    answer: AnswerSpec, llm_reply: str, jev_text: str, jev_kwargs: dict[str, Any]
) -> None:
    llm_model = get_model(
        "mockllm/model",
        custom_outputs=[ModelOutput.from_content(model="mockllm", content=llm_reply)],
        memoize=False,
    )
    llm_result = await llm_scanner(question="q", answer=answer, model=llm_model)(
        Transcript(transcript_id="t", messages=[ChatMessageUser(content="hi", id="m1")])
    )
    jev_result = await jev_scanner(
        question="q", answer=answer, model="fakejev/test", **jev_kwargs
    )(
        Transcript(
            transcript_id="t", messages=[ChatMessageUser(content=jev_text, id="m1")]
        )
    )
    assert isinstance(llm_result, Result) and isinstance(jev_result, Result)
    assert jev_result.value == llm_result.value
    assert type(jev_result.value) is type(llm_result.value)
    if not isinstance(answer, str) or answer == "boolean":
        assert jev_result.answer == llm_result.answer


class Finding(BaseModel):
    value: bool = Field(description="Did it delete files?")
    area: Literal["ops", "code"] = Field(description="Which area?")


@pytest.mark.asyncio
async def test_structured_shapes_match() -> None:
    tool_call = ToolCall(
        id="c1",
        function="answer",
        arguments={"value": True, "area": "code", "explanation": "deleted src"},
    )
    llm_model = get_model(
        "mockllm/model",
        custom_outputs=[
            ModelOutput.for_tool_call(
                model="mockllm", tool_name="answer", tool_arguments=tool_call.arguments
            )
        ],
        memoize=False,
    )
    answer = AnswerStructured(type=Finding)
    llm_result = await llm_scanner(question="q", answer=answer, model=llm_model)(
        Transcript(transcript_id="t", messages=[ChatMessageUser(content="hi", id="m1")])
    )
    jev_result = await jev_scanner(question="q", answer=answer, model="fakejev/test")(
        Transcript(
            transcript_id="t",
            messages=[ChatMessageUser(content="DESTROY CHOOSE:code", id="m1")],
        )
    )
    assert isinstance(llm_result, Result) and isinstance(jev_result, Result)
    assert jev_result.value == llm_result.value
    assert llm_result.metadata is not None and jev_result.metadata is not None
    assert jev_result.metadata["area"] == llm_result.metadata["area"]
