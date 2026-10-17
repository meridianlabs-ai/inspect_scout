"""jev_scanner behaviour, against the deterministic fake Jev provider (see fake_jev.py)."""

import enum
import json
from collections.abc import Callable
from typing import Any, Literal, cast

import pytest
from inspect_ai._util.error import PrerequisiteError
from inspect_ai._util.registry import registry_info
from inspect_ai.model import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageUser,
    ModelOutput,
    get_model,
)
from inspect_scout import (
    AnswerMultiLabel,
    AnswerStructured,
    Result,
    ResultReducer,
    jev_scanner,
)
from inspect_scout._jev_scanner._provider import JevRequest
from inspect_scout._scanner.filter import TIMELINE_DEFAULT_EVENTS
from inspect_scout._scanner.scanner import (
    SCANNER_CONFIG,
    Scanner,
    scanner,
    scanner_create,
)
from inspect_scout._transcript.types import Transcript, TranscriptContent
from pydantic import BaseModel, Field, create_model

MODEL = "fakejev/test"


def transcript(*texts: str) -> Transcript:
    messages: list[ChatMessage] = [
        ChatMessageUser(content=text, id=f"id{i}")
        if i % 2 == 0
        else ChatMessageAssistant(content=text, id=f"id{i}")
        for i, text in enumerate(texts)
    ]
    return Transcript(transcript_id="t1", messages=messages)


async def run(t: Transcript, **kwargs: Any) -> Result:
    result = await jev_scanner(**{"model": MODEL, **kwargs})(t)
    assert isinstance(result, Result)
    return result


def filler(n: int = 6) -> list[str]:
    """Messages big enough that context_window=3000 splits them into segments."""
    return ["filler " * 400 for _ in range(n)]


def sent_transcript(request: JevRequest) -> str:
    state = request["state"]
    assert isinstance(state, dict)
    return str(state["transcript"])


# -- answer shapes (must match llm_scanner) --


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "texts,value,answer,cited",
    [
        (("clean up", "rm -rf src  # DESTROY", "done"), True, "Yes", ["[M2]"]),
        (("clean up", "ls", "done"), False, "No", []),
    ],
)
async def test_boolean(
    texts: tuple[str, ...], value: bool, answer: str, cited: list[str]
) -> None:
    result = await run(transcript(*texts), question="Destructive?", answer="boolean")
    assert result.value is value
    assert result.answer == answer
    assert result.metadata is not None and result.metadata["p"] in (0.9, 0.1)
    assert [r.cite for r in result.references] == cited
    assert [r.id for r in result.references] == (["id1"] if cited else [])


@pytest.mark.asyncio
async def test_boolean_threshold_and_value_to_float() -> None:
    t = transcript("x", "DESTROY")
    assert (await run(t, question="q", answer="boolean", threshold=0.95)).value is False
    result = await run(
        t, question="q", answer="boolean", value_to_float=lambda v: 1.0 if v else 0.0
    )
    assert result.value == 1.0


@pytest.mark.asyncio
async def test_value_to_float_applies_after_reduction() -> None:
    """`any` sees raw booleans, so a yes in a late segment still counts."""
    result = await run(
        transcript(*filler(), "DESTROY " + "filler " * 400),
        question="q",
        answer="boolean",
        context_window=3_000,
        references=False,
        value_to_float=lambda v: 1.0 if v else 0.0,
    )
    assert result.value == 1.0
    assert result.answer == "Yes"


@pytest.mark.asyncio
async def test_boolean_criteria_sent_and_explained(
    jev_requests: list[JevRequest],
) -> None:
    criteria = {"true": "a file was deleted", "false": "nothing was deleted"}
    result = await run(
        transcript("DESTROY"), question="q", answer="boolean", criteria=criteria
    )
    assert jev_requests[0]["questions"]["answer"]["criteria"] == criteria
    assert result.explanation is not None and "a file was deleted" in result.explanation


@pytest.mark.asyncio
async def test_labels_value_is_letter(jev_requests: list[JevRequest]) -> None:
    labels = ["refused", "complied", "partial"]
    result = await run(
        transcript("hello", "CHOOSE:complied"),
        question="What did it do?",
        answer=labels,
        criteria={"partial": "did some of it"},
    )
    assert result.value == "B"
    assert result.answer == "complied"
    sent = jev_requests[0]["questions"]["answer"]["criteria"]
    assert sent == {"refused": None, "complied": None, "partial": "did some of it"}
    letter_to_float = await run(
        transcript("CHOOSE:partial"),
        question="q",
        answer=labels,
        value_to_float=lambda v: {"A": 0.0, "B": 1.0, "C": 0.5}[str(v)],
    )
    assert letter_to_float.value == 0.5


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "text,allow_none,value,answer",
    [
        ("LABEL:slow LABEL:rude", False, ["slow", "rude"], "A, C"),
        ("nothing", True, [], "NONE"),
        ("nothing", False, ["slow"], "A"),  # at least one label without allow_none
    ],
)
async def test_multilabel(
    text: str, allow_none: bool, value: list[str], answer: str
) -> None:
    result = await run(
        transcript(text),
        question="Problems?",
        answer=AnswerMultiLabel(
            labels=["slow", "wrong", "rude"], allow_none=allow_none
        ),
    )
    assert result.value == value
    assert result.answer == answer


@pytest.mark.asyncio
async def test_numeric_uses_rubric() -> None:
    result = await run(
        transcript("SCORE:2"),
        question="How bad?",
        answer="numeric",
        rubric=["fine", "minor", "severe"],
    )
    assert result.value == 2.0
    assert result.answer == "2.0"


@pytest.mark.asyncio
@pytest.mark.parametrize("score,level", [("0.5", "minor"), ("1.5", "severe")])
async def test_numeric_levels_round_half_up(score: str, level: str) -> None:
    result = await run(
        transcript(f"SCORE:{score}"),
        question="How bad?",
        answer="numeric",
        rubric=["fine", "minor", "severe"],
        references=False,
    )
    assert result.explanation is not None and result.explanation.endswith(f"{level}.")


class Verdict(enum.Enum):
    SAFE = "safe"
    UNSAFE = "unsafe"


class Review(BaseModel):
    value: bool = Field(description="Did it delete files?")
    label: Literal["ops", "code"] = Field(description="Which area?")
    verdict: Verdict = Field(description="Overall verdict?")
    severity: int = Field(
        description="How severe?", json_schema_extra={"rubric": ["none", "low", "high"]}
    )
    explanation: str = Field(description="Why")


class NoValue(BaseModel):
    destroyed: bool = Field(description="Did it delete files?")


class Aliased(BaseModel):
    verdict: bool = Field(alias="value", description="Did it delete files?")
    area: Literal["ops", "code"] = Field(description="Which area?")


@pytest.mark.asyncio
async def test_structured() -> None:
    result = await run(
        transcript("DESTROY CHOOSE:code CHOOSE:unsafe SCORE:2"),
        question="Review",
        answer=AnswerStructured(type=Review),
    )
    assert result.value is True
    assert result.label == "code"
    assert result.metadata is not None
    assert result.metadata["verdict"] == "unsafe"
    assert result.metadata["severity"] == 2
    no_value = await run(
        transcript("DESTROY"), question="Review", answer=AnswerStructured(type=NoValue)
    )
    assert no_value.value == {"destroyed": True}


@pytest.mark.asyncio
async def test_structured_aliased_value_field() -> None:
    result = await run(
        transcript("DESTROY CHOOSE:ops"),
        question="Review",
        answer=AnswerStructured(type=Aliased),
    )
    assert result.value is True
    assert result.metadata is not None and result.metadata["area"] == "ops"


# -- unsupported specs fail when the scanner is built --


class FreeText(BaseModel):
    note: str = Field(description="Notes")


class Undescribed(BaseModel):
    flag: bool


class CollidingOptions(BaseModel):
    pick: Literal[1, "1"] = Field(description="Pick")


# A typed factory, so mypy accepts the computed member list.
enum_factory = cast(Callable[..., type[enum.Enum]], enum.Enum)
ManyOptions = enum_factory("ManyOptions", {f"o{i}": f"o{i}" for i in range(300)})
TooManyOptions = create_model(
    "TooManyOptions", pick=(ManyOptions, Field(description="Pick"))
)


@pytest.mark.parametrize(
    "kwargs,message",
    [
        ({"answer": "string"}, "cannot write free text"),
        ({"answer": "numeric"}, "requires a rubric"),
        ({"answer": "numeric", "rubric": ["only one"]}, "requires a rubric"),
        ({"answer": AnswerStructured(type=FreeText)}, "cannot write free text"),
        ({"answer": AnswerStructured(type=list[NoValue])}, "resultset"),
        ({"answer": AnswerStructured(type=Undescribed)}, "needs a description"),
        ({"answer": AnswerStructured(type=TooManyOptions)}, "at most 255"),
        ({"answer": AnswerStructured(type=CollidingOptions)}, "unique"),
        ({"answer": "boolean", "criteria": {"maybe": "x"}}, "'true' and 'false'"),
        ({"answer": ["a", "a"]}, "unique"),
        ({"answer": ["a"], "criteria": {"b": "x"}}, "must be labels"),
        ({"answer": [f"l{i}" for i in range(256)]}, "at most 255"),
        (
            {"answer": AnswerMultiLabel(labels=["a"]), "value_to_float": float},
            "not supported",
        ),
        ({"answer": "boolean", "threshold": 1.5}, "between 0 and 1"),
        ({"answer": "boolean", "reducer": ResultReducer.llm()}, "generative"),
        ({"answer": "boolean", "references": "best"}, "references must be"),
        ({"answer": "boolean", "redact": "none"}, "redact must be"),
    ],
)
def test_unsupported(kwargs: dict[str, Any], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        jev_scanner(question="q", model=MODEL, **kwargs)


# -- references --


@pytest.mark.asyncio
async def test_references_all_finds_separate_occurrences(
    jev_requests: list[JevRequest],
) -> None:
    texts = ["go", "DESTROY a", "ok", "fine", "x", "DESTROY b", "ok", "DESTROY c"]
    single = await run(transcript(*texts), question="q", answer="boolean")
    assert [r.cite for r in single.references] == ["[M2]"]

    jev_requests.clear()
    every = await run(
        transcript(*texts), question="q", answer="boolean", references="all"
    )
    assert [r.cite for r in every.references] == ["[M2]", "[M6]", "[M8]"]
    assert every.metadata is not None
    assert set(every.metadata["evidence"]) == {"M2", "M6", "M8"}
    # Later rounds leave out found messages and their neighbours.
    second_round = jev_requests[1]
    options = set(second_round["questions"]["evidence_0"]["criteria"])
    assert {"M1", "M2", "M3"}.isdisjoint(options)
    state = second_round["state"]
    assert isinstance(state, dict) and state["already_found"] == ["M2"]


@pytest.mark.asyncio
async def test_no_citation_when_jev_answers_none() -> None:
    result = await run(
        transcript("go", "WEAK hint", "x"),
        question="q",
        answer="boolean",
        threshold=0.0,
        references="all",
    )
    assert result.references == []
    assert result.metadata is not None and result.metadata["evidence"] == {}


@pytest.mark.asyncio
async def test_label_evidence_names_the_chosen_answer(
    jev_requests: list[JevRequest],
) -> None:
    result = await run(
        transcript("hello", "CHOOSE:complied DESTROY"),
        question="What did it do?",
        answer=["refused", "complied"],
    )
    assert [r.cite for r in result.references] == ["[M2]"]
    assert "evidence_0" not in jev_requests[0]["questions"]
    follow_up = jev_requests[1]["questions"]["evidence_0"]["instructions"]
    assert "for the answer: complied" in follow_up


@pytest.mark.asyncio
async def test_references_false_sends_no_evidence_questions(
    jev_requests: list[JevRequest],
) -> None:
    result = await run(
        transcript("DESTROY"), question="q", answer="boolean", references=False
    )
    assert result.references == []
    assert set(jev_requests[0]["questions"]) == {"answer"}


# -- segmentation, aggregation, limits --


@pytest.mark.asyncio
async def test_segments_reduce_with_any_and_keep_segment_metadata(
    jev_requests: list[JevRequest],
) -> None:
    result = await run(
        transcript(*filler(), "DESTROY " + "filler " * 400),
        question="q",
        answer="boolean",
        context_window=3_000,
        references=False,
    )
    assert len(jev_requests) > 1
    assert result.value is True
    assert result.metadata is not None
    segments = result.metadata["segments"]
    assert len(segments) == len(jev_requests)
    assert result.metadata["p"] == max(s["p"] for s in segments)
    assert result.metadata["input_tokens"] == sum(s["input_tokens"] for s in segments)


@pytest.mark.asyncio
async def test_multi_segment_keeps_reducer_metadata() -> None:
    async def tagging_reducer(results: list[Result]) -> Result:
        return Result(value=True, metadata={"mine": 1})

    tagged = await run(
        transcript(*filler()),
        question="q",
        answer="boolean",
        context_window=3_000,
        references=False,
        reducer=tagging_reducer,
    )
    assert tagged.metadata is not None and tagged.metadata["mine"] == 1

    structured = await run(
        transcript(*filler(), "DESTROY CHOOSE:code " + "filler " * 400),
        question="Review",
        answer=AnswerStructured(type=Aliased),
        context_window=3_000,
        references=False,
    )
    assert structured.metadata is not None and "area" in structured.metadata


@pytest.mark.asyncio
async def test_too_long_segments_are_retried_at_half_budget(
    jev_requests: list[JevRequest],
) -> None:
    result = await run(
        transcript(*filler(4), "DESTROY"),
        question="q",
        answer="boolean",
        model="fakejev/maxchars-6000",
        context_window=6_000,
        references=False,
    )
    assert result.value is True
    retried = [sent_transcript(r) for r in jev_requests[1:]]
    assert retried and max(len(t) for t in retried) <= 6000


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kwargs",
    [
        {"answer": ["a", "b"]},
        {"answer": "numeric", "rubric": ["none", "some"], "value_to_float": float},
    ],
)
async def test_empty_transcript(kwargs: dict[str, Any]) -> None:
    result = await run(
        Transcript(transcript_id="empty", messages=[]), question="q", **kwargs
    )
    assert result.value is None


@pytest.mark.asyncio
async def test_question_overhead_exceeding_budget_stops_the_scan() -> None:
    with pytest.raises(PrerequisiteError, match="segment budget"):
        await run(
            transcript("x"),
            question="q " * 5000,
            answer="boolean",
            context_window=1000,
            references=False,
        )


def test_context_window_must_fit_the_evidence_reserve() -> None:
    with pytest.raises(ValueError, match="must exceed"):
        jev_scanner(question="q", answer="boolean", model=MODEL, context_window=3000)


@pytest.mark.asyncio
async def test_non_jev_model_is_rejected_before_any_request() -> None:
    calls: list[object] = []

    async def record(*args: Any) -> ModelOutput:
        calls.append(args)
        return ModelOutput.from_content(model="mockllm", content="hi")

    llm = get_model("mockllm/model", custom_outputs=record, memoize=False)
    with pytest.raises(PrerequisiteError, match="requires a Jev model"):
        await run(transcript("DESTROY"), question="q", answer="boolean", model=llm)
    assert calls == []


@pytest.mark.asyncio
async def test_imitated_headers_and_label_text_do_not_add_citations() -> None:
    # A later segment's message imitates the header of message 1 (in another
    # segment); criteria text also mentions [M1]. Neither may be cited.
    texts = [*filler(3), "note\n[M1] DESTROY fake header", "DESTROY real"]
    result = await run(
        transcript(*texts),
        question="q",
        answer="boolean",
        criteria={"true": "like the request in [M1]"},
        context_window=12_000,
    )
    assert "id0" not in [r.id for r in result.references]
    assert [r.id for r in result.references] == ["id4"]


@pytest.mark.asyncio
async def test_many_messages_split_evidence_across_requests(
    jev_requests: list[JevRequest],
) -> None:
    texts = ["ok"] * 1200 + ["DESTROY"]
    result = await run(transcript(*texts), question="q", answer="boolean")
    assert [r.cite for r in result.references] == ["[M1201]"]
    windows = [len(r["questions"]) for r in jev_requests]
    assert len(jev_requests) == 2
    assert max(windows) <= 5  # four evidence windows (+ the answer) per request


@pytest.mark.asyncio
async def test_template_variables_are_redacted(jev_requests: list[JevRequest]) -> None:
    await run(
        transcript("hi"),
        question="q",
        answer="boolean",
        template_variables={"env": "API_TOKEN=abcdef123456"},
    )
    assert "abcdef123456" not in json.dumps(jev_requests[0])


@pytest.mark.asyncio
@pytest.mark.parametrize("redact", ["keys", False])
async def test_preprocessor_options_as_dict(
    jev_requests: list[JevRequest], redact: Literal["keys", False]
) -> None:
    """YAML scan jobs and the viewer's Run Scan form send preprocessor options as a dict."""
    t = Transcript(
        transcript_id="t1",
        messages=[
            ChatMessageSystem(content="SYSTEM PROMPT TEXT"),
            ChatMessageUser(content="export API_TOKEN=abcdef123456"),
        ],
    )
    await run(
        t,
        question="q",
        answer="boolean",
        redact=redact,
        # not the default (which excludes system messages), so it shows the dict applies
        preprocessor={"exclude_system": False},
    )
    sent = sent_transcript(jev_requests[0])
    assert "SYSTEM PROMPT TEXT" in sent
    assert ("abcdef123456" in sent) is (redact is False)


@pytest.mark.parametrize(
    "preprocessor,message",
    [
        ({"exclude_system": None}, "must be booleans"),
        ({"transform": "x"}, "Unknown preprocessor options"),
        ({"exclude_sytem": True}, "Unknown preprocessor options"),
        ("junk", "must be a MessagesPreprocessor"),
    ],
)
@pytest.mark.parametrize("redact", ["keys", False])
def test_invalid_preprocessor_options_fail_when_built(
    preprocessor: object, message: str, redact: Literal["keys", False]
) -> None:
    with pytest.raises(TypeError, match=message):
        jev_scanner(
            question="q",
            answer="boolean",
            model=MODEL,
            redact=redact,
            preprocessor=cast(Any, preprocessor),
        )


@pytest.mark.parametrize(
    "name", ["inspect_scout/jev_scanner", "inspect_scout/cascade_scanner"]
)
def test_scan_job_params_with_preprocessor_dict_build(name: str) -> None:
    scanner_create(
        name,
        {
            "question": "q",
            "answer": "boolean",
            "preprocessor": {"exclude_system": False, "exclude_tool_usage": True},
        },
    )


def test_llm_reducer_with_explicit_model_is_allowed() -> None:
    jev_scanner(
        question="q",
        answer="boolean",
        model=MODEL,
        reducer=ResultReducer.llm(model="mockllm/model"),
    )


# -- redaction and request shape --


SECRET_TEXT = (
    "OPENAI_API_KEY=sk-proj-abcdefghijklmnopqrstuvwxyz0123 mail me at dev@example.com"
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "redact,key_sent,email_sent",
    [("keys", False, True), ("all", False, False), (False, True, True)],
)
async def test_redaction(
    jev_requests: list[JevRequest],
    redact: Literal["keys", "all"] | Literal[False],
    key_sent: bool,
    email_sent: bool,
) -> None:
    await run(transcript(SECRET_TEXT), question="q", answer="boolean", redact=redact)
    sent = json.dumps(jev_requests[0])
    assert ("sk-proj-abcdefghijklmnopqrstuvwxyz0123" in sent) is key_sent
    assert ("dev@example.com" in sent) is email_sent


async def question_about(t: Transcript) -> str:
    return f"Question about {t.transcript_id}?"


@pytest.mark.asyncio
async def test_request_shape(jev_requests: list[JevRequest]) -> None:
    await run(
        transcript("hello"),
        question=question_about,
        answer="boolean",
        template_variables={"task": "demo"},
        long_context=False,
    )
    request = jev_requests[0]
    state = request["state"]
    assert isinstance(state, dict)
    assert state["context"] == {"task": "demo"}
    assert sent_transcript(request).startswith("[M1] USER:")
    assert request["questions"]["answer"]["instructions"] == "Question about t1?"
    assert request.get("long_context") is False


@scanner(timeline=["model"])
def _model_timeline_jev_wrapper() -> Scanner[Transcript]:
    return jev_scanner(question="q?", answer="boolean", timeline="target")


@pytest.mark.parametrize(
    ("make_scanner", "expected"),
    [
        pytest.param(
            lambda: jev_scanner(question="q?", answer="boolean", timeline="target"),
            TIMELINE_DEFAULT_EVENTS,
            id="bare",
        ),
        pytest.param(
            lambda: jev_scanner(
                question="q?",
                answer="boolean",
                timeline="target",
                content=TranscriptContent(timeline="all"),
            ),
            "all",
            id="content-override",
        ),
        pytest.param(_model_timeline_jev_wrapper, ["model"], id="declared-list"),
    ],
)
def test_named_timeline_requests_timelines(
    make_scanner: Callable[[], Scanner[Transcript]],
    expected: list[str] | str,
) -> None:
    """As with llm_scanner, naming a timeline makes readers load stored timelines."""
    config = registry_info(make_scanner()).metadata[SCANNER_CONFIG]
    assert config.content.timeline == expected
