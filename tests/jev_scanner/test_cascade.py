"""cascade_scanner: Jev first, escalating to llm_scanner by declarative rules."""

from typing import Any

import pytest
from inspect_ai._util.error import PrerequisiteError
from inspect_ai.model import ChatMessage, ChatMessageUser, ModelOutput, get_model
from inspect_scout import Result, cascade_scanner
from inspect_scout._jev_scanner._cascade import escalation_reasons
from inspect_scout._jev_scanner._provider import JevRequest
from inspect_scout._transcript.types import Transcript


def transcript(text: str) -> Transcript:
    return Transcript(
        transcript_id="t1", messages=[ChatMessageUser(content=text, id="m1")]
    )


def mock_llm() -> Any:
    return get_model(
        "mockllm/model",
        custom_outputs=[
            ModelOutput.from_content(
                model="mockllm", content="It deleted [M1].\n\nANSWER: yes"
            )
        ],
        memoize=False,
    )


async def run(text: str, **kwargs: Any) -> Result:
    result = await cascade_scanner(
        question="Destructive?",
        answer="boolean",
        jev={"model": "fakejev/test"},
        **kwargs,
    )(transcript(text))
    assert isinstance(result, Result)
    return result


@pytest.mark.asyncio
async def test_jev_decides_confident_negatives() -> None:
    result = await run("all good", llm={"model": mock_llm()})
    assert result.value is False
    assert result.metadata is not None
    assert result.metadata["cascade"]["decided_by"] == "jev"
    assert result.metadata["cascade"]["escalation_reasons"] == []


@pytest.mark.asyncio
async def test_positive_escalates_to_llm() -> None:
    result = await run("DESTROY", llm={"model": mock_llm()})
    assert result.value is True
    assert result.explanation is not None and "It deleted" in result.explanation
    assert result.metadata is not None
    cascade = result.metadata["cascade"]
    assert cascade["decided_by"] == "llm"
    assert cascade["escalation_reasons"] == ["positive"]
    assert cascade["jev"]["value"] is True


@pytest.mark.asyncio
async def test_review_queue_mode_flags_without_calling_an_llm() -> None:
    result = await run("DESTROY", llm=False)
    assert result.metadata is not None
    assert result.metadata["needs_review"] is True
    assert result.metadata["cascade"]["decided_by"] == "jev"


@pytest.mark.asyncio
async def test_missing_llm_key_fails_before_jev(
    monkeypatch: pytest.MonkeyPatch, jev_requests: list[JevRequest]
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(PrerequisiteError, match="ANTHROPIC_API_KEY"):
        await run("DESTROY", llm={"model": "anthropic/claude-haiku-4-5-20251001"})
    assert jev_requests == []


@pytest.mark.asyncio
async def test_no_default_llm_is_a_prerequisite_error(
    monkeypatch: pytest.MonkeyPatch, jev_requests: list[JevRequest]
) -> None:
    monkeypatch.delenv("INSPECT_EVAL_MODEL", raising=False)
    with pytest.raises(PrerequisiteError, match="llm=False"):
        await run("DESTROY")
    assert jev_requests == []


@pytest.mark.asyncio
async def test_llm_stage_gets_rubric_and_criteria() -> None:
    prompts: list[str] = []

    async def capture(
        input: list[ChatMessage], tools: Any, tool_choice: Any, config: Any
    ) -> ModelOutput:
        prompts.append("\n".join(m.text for m in input))
        return ModelOutput.from_content(model="mockllm", content="ANSWER: 2")

    llm_model = get_model("mockllm/model", custom_outputs=capture, memoize=False)
    result = await cascade_scanner(
        question="How severe?",
        answer="numeric",
        rubric=["none", "low", "high"],
        jev={"model": "fakejev/test"},
        llm={"model": llm_model},
        escalate={"confidence_below": 1.0},
    )(transcript("SCORE:2"))
    assert isinstance(result, Result) and result.value == 2.0
    assert "Answer with a number from 0 to 2" in prompts[0]
    assert "2: high" in prompts[0]


@pytest.mark.parametrize(
    "result,rules,reasons",
    [
        (Result(value=True, metadata={"p": 0.9}), {"positive": True}, ["positive"]),
        (
            Result(value=False, metadata={"p": 0.4}),
            {"p_between": [0.2, 0.8]},
            ["p_between"],
        ),
        (Result(value=False, metadata={"p": 0.1}), {"p_between": [0.2, 0.8]}, []),
        (
            Result(
                value=False, metadata={"p": 0.1, "segments": [{"p": 0.1}, {"p": 0.5}]}
            ),
            {"p_between": [0.2, 0.8]},
            ["p_between"],
        ),
        (
            Result(value="C", answer="other", metadata={"confidence": 0.9}),
            {"labels": ["other"]},
            ["labels"],
        ),
        (
            Result(value="A", answer="x", metadata={"confidence": 0.3}),
            {"confidence_below": 0.5},
            ["confidence_below"],
        ),
        (
            Result(
                value=["a"], metadata={"probabilities": {"a": 0.9}, "threshold": 0.5}
            ),
            {"positive": True},
            ["positive"],
        ),
        (
            Result(value=1.0, answer="Yes", metadata={"p": 0.9}),
            {"positive": True},
            ["positive"],
        ),
        (
            Result(value="A", answer="Yes", metadata={"confidence": 0.9}),
            {"positive": True},
            [],
        ),
        (
            Result(value=["other", "slow"], answer="A, B"),
            {"labels": ["other"]},
            ["labels"],
        ),
    ],
)
def test_escalation_rules(
    result: Result, rules: dict[str, Any], reasons: list[str]
) -> None:
    assert escalation_reasons(result, rules) == reasons


@pytest.mark.parametrize(
    "kwargs,message",
    [
        ({"escalate": {"sometimes": True}}, "Unknown escalate rules"),
        ({"jev": {"question": "other"}}, "must not repeat"),
        ({"llm": {"answer": "numeric"}}, "must not repeat"),
        ({"jev": {"criteria": {"true": "x"}}}, "must not repeat"),
        ({"jev": {"timeline": "main"}}, "does not support"),
        ({"jev": {"rubric": ["a", "b"]}}, "must not repeat"),
        ({"escalate": {"p_between": 0.5}}, "p_between"),
        ({"escalate": {"labels": "other"}}, "labels"),
    ],
)
def test_invalid_configuration(kwargs: dict[str, Any], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        cascade_scanner(question="q", answer="boolean", **kwargs)
