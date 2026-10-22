"""Condensed model events: a scanner can ask for `input_refs` and the pool."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Iterator, Literal

import pytest
from inspect_ai import Task, eval
from inspect_ai.event import (
    CompactionEvent,
    Event,
    ModelEvent,
    SpanBeginEvent,
    SpanEndEvent,
    Timeline,
    TimelineSpan,
    ToolEvent,
    _pool,
    timeline_build,
    timeline_dump,
)
from inspect_ai.log import condense_events, expand_events, read_eval_log, write_eval_log
from inspect_ai.model import (
    ChatCompletionChoice,
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageTool,
    ChatMessageUser,
    GenerateConfig,
    ModelCall,
    ModelOutput,
)
from inspect_ai.model._chat_message import ChatMessageBase
from inspect_ai.tool import ToolCall
from inspect_scout import (
    Loader,
    Result,
    Scanner,
    loader,
    scan,
    scan_results_df,
    scanner,
)
from inspect_scout._scanner.result import ResultReport
from inspect_scout._scanner.scorer import as_scorer
from inspect_scout._transcript.database.factory import transcripts_db
from inspect_scout._transcript.eval_log import EvalLogTranscriptsView
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.handle import (
    MaterializedTranscriptHandle,
    TranscriptHandle,
)
from inspect_scout._transcript.types import Transcript, TranscriptContent
from inspect_scout._transcript.util import (
    PooledInput,
    build_timeline,
    filter_transcript,
    union_transcript_contents,
)
from inspect_scout._util import constants as constants_mod

from .fixtures_agentic import agentic_events

BASE_LOG = (
    Path(__file__).parent.parent
    / "recorder"
    / "logs"
    / "2025-11-07T10-59-47-05-00_websearch-addition-problem_LqPDntDnkk4h2fSqQ8i6CE.eval"
)

EXPANDED = TranscriptContent(messages="all", events="all")
CONDENSED = TranscriptContent(messages="all", events="all", condensed=True)


def _conversation(
    turns: int,
    *,
    varied: bool = False,
    bridge_every_turn: bool = False,
    duplicate_uuid: bool = False,
) -> tuple[list[ChatMessage], list[Event]]:
    """An agent loop of `turns` model calls, each re-sending the conversation.

    Every turn makes two parallel tool calls, and a compaction halfway
    through restarts the conversation from a summary, so the inputs grow
    with the turn count as a real run's do.

    `varied` adds what else `timeline_build` reads inputs for: turns without
    tool calls, cache-warmup calls, sub-agent spans with their own system
    prompt, and three bridged `agent-<call id>` spans whose results the next
    call's input carries. `bridge_every_turn` bridges every tool-calling
    turn instead. `duplicate_uuid` gives the first tool event the first model
    event's uuid, as an edited log can.
    """
    system = ChatMessageSystem(content="You are a careful agent.")
    conversation: list[ChatMessage] = [
        system,
        ChatMessageUser(content="Probe the system."),
    ]
    bridged = (
        set(range(turns))
        if bridge_every_turn
        else {2, turns // 2 + 2, turns - 2}
        if varied
        else set()
    )
    events: list[Event] = []
    for turn in range(turns):
        if turn == turns // 2:
            events.append(CompactionEvent(type="summary"))
            conversation = [
                conversation[0],
                ChatMessageUser(content=f"Summary of turns 0 to {turn - 1}."),
            ]
        if varied and turn % 7 == 1:
            events.append(
                _model_event([system, ChatMessageUser(content="warm")], max_tokens=1)
            )
        if varied and turn % 5 == 3:
            reply = ChatMessageAssistant(content=f"Thinking at turn {turn}.")
            events.append(_model_event(list(conversation), output=reply))
            conversation.extend([reply, ChatMessageUser(content="Continue.")])
            continue
        calls = [
            ToolCall(id=f"call-{turn}-{i}", function="probe", arguments={"i": i})
            for i in range(2)
        ]
        assistant = ChatMessageAssistant(content=f"Turn {turn}.", tool_calls=calls)
        events.append(
            ModelEvent(
                model="mockllm/model",
                input=list(conversation),
                tools=[],
                tool_choice="auto",
                config=GenerateConfig(),
                output=ModelOutput(
                    model="mockllm/model",
                    choices=[
                        ChatCompletionChoice(
                            message=assistant, stop_reason="tool_calls"
                        )
                    ],
                ),
                call=ModelCall(
                    request={
                        "messages": [
                            message.model_dump(mode="json", exclude_none=True)
                            for message in conversation
                        ]
                    },
                    response={},
                ),
            )
        )
        conversation.append(assistant)
        if varied and turn % 6 == 4:
            events.extend(_sub_agent(f"research-{turn}", "You are a researcher."))
        if turn in bridged:
            events.extend(_sub_agent(f"agent-{calls[0].id}", "You are a helper."))
        for call in calls:
            result = f"{call.id} found nothing."
            events.append(
                ToolEvent(
                    id=call.id,
                    function=call.function,
                    arguments=call.arguments,
                    result=result,
                )
            )
            conversation.append(
                ChatMessageTool(
                    content=result, tool_call_id=call.id, function=call.function
                )
            )
    if duplicate_uuid:
        model = next(e for e in events if isinstance(e, ModelEvent))
        tool = next(e for e in events if isinstance(e, ToolEvent))
        tool.uuid = model.uuid
    return conversation, events


def _model_event(
    input: list[ChatMessage],
    *,
    output: ChatMessageAssistant | None = None,
    max_tokens: int | None = None,
    span_id: str | None = None,
) -> ModelEvent:
    return ModelEvent(
        span_id=span_id,
        model="mockllm/model",
        input=input,
        tools=[],
        tool_choice="auto",
        config=GenerateConfig(max_tokens=max_tokens),
        output=ModelOutput(
            model="mockllm/model",
            choices=[
                ChatCompletionChoice(
                    message=output or ChatMessageAssistant(content="ok"),
                    stop_reason="stop",
                )
            ],
        ),
    )


def _sub_agent(span_id: str, system_prompt: str) -> list[Event]:
    """An agent span holding one call with its own system prompt."""
    return [
        SpanBeginEvent(id=span_id, name="helper", type="agent", span_id=span_id),
        _model_event(
            [
                ChatMessageSystem(content=system_prompt),
                ChatMessageUser(content=f"Help with {span_id}."),
            ],
            output=ChatMessageAssistant(content=f"{span_id} answered."),
            span_id=span_id,
        ),
        SpanEndEvent(id=span_id, span_id=span_id),
    ]


def _write_log(
    directory: Path,
    turns: int,
    *,
    format: Literal["eval", "json"] = "eval",
    varied: bool = False,
    duplicate_uuid: bool = False,
) -> Path:
    """A log holding one sample of `turns` turns, with no stored timeline.

    `.eval` logs pool inputs on write; inspect_ai serves `.json` logs to
    Scout with every input expanded.
    """
    log = read_eval_log(str(BASE_LOG))
    assert log.samples
    sample = log.samples[0]
    sample.messages, sample.events = _conversation(
        turns, varied=varied, duplicate_uuid=duplicate_uuid
    )
    sample.timelines = None
    log.samples = [sample]
    directory.mkdir(parents=True, exist_ok=True)
    # `.json` logs are found by their standard file name
    path = directory / BASE_LOG.with_suffix(f".{format}").name
    write_eval_log(log, str(path))
    return path


async def _read(log: Path, content: TranscriptContent) -> Transcript:
    async with EvalLogTranscriptsView(str(log)) as view:
        info = [info async for info in view.select()][0]
        return await view.read(info, content)


def _dumps(events: list[Event]) -> list[dict[str, Any]]:
    return [event.model_dump() for event in events]


class _Decodes:
    """Counts chat messages built by validation, wherever they are nested."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.count = 0
        post_init = ChatMessageBase.model_post_init

        def counting(message: ChatMessageBase, context: Any) -> None:
            self.count += 1
            post_init(message, context)

        monkeypatch.setattr(ChatMessageBase, "model_post_init", counting)


class _ExpandedSlots:
    """Counts messages placed into inputs or requests by inspect_ai's pool expansion."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.count = 0
        expand_refs = _pool._expand_refs

        def counting(refs: Any, pool: Any) -> Any:
            expanded = expand_refs(refs, pool)
            self.count += len(expanded)
            return expanded

        monkeypatch.setattr(_pool, "_expand_refs", counting)


@scanner(messages="all", events="all", condensed=True, supports_streaming=True)
def condensed_scanner() -> Scanner[Transcript]:
    async def scan_transcript(transcript: Transcript | TranscriptHandle) -> Result:
        # a handle has no pool, so a condensed scan is never handed one
        assert isinstance(transcript, Transcript)
        assert transcript.events_data is not None
        model_events = [e for e in transcript.events if isinstance(e, ModelEvent)]
        assert all(e.input == [] and e.input_refs for e in model_events)
        return Result(value=len(transcript.events_data["messages"]))

    return scan_transcript


def test_condensed_scan_decodes_each_pooled_message_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Decodes grow with the log, not with the sum of the inputs.

    The spool threshold is zero, so an expanded read would take the spooled
    path, which decodes each pooled message again for every event sending it.
    """
    monkeypatch.setattr(constants_mod, "SPOOL_THRESHOLD_BYTES", 0)
    decodes = _Decodes(monkeypatch)
    counts: dict[int, int] = {}
    for turns in (20, 40):
        log = _write_log(tmp_path / f"logs-{turns}", turns)
        decodes.count = 0
        status = scan(
            scanners=[condensed_scanner()],
            transcripts=transcripts_from(log),
            scans=str(tmp_path / f"scans-{turns}"),
            max_processes=1,
            display="none",
        )
        assert status.complete
        counts[turns] = decodes.count

    # each turn adds a few messages and re-sends the whole conversation, so
    # decoding each event's input would quadruple from 20 to 40 turns
    assert counts[40] <= 2.2 * counts[20], counts


@pytest.mark.asyncio
async def test_condensed_read_decodes_each_pooled_message_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A read decodes the sample's messages, each pool row, and each output."""
    log = _write_log(tmp_path, 30)
    decodes = _Decodes(monkeypatch)
    expanded = _ExpandedSlots(monkeypatch)
    async with EvalLogTranscriptsView(str(log)) as view:
        info = [info async for info in view.select()][0]
        decodes.count = 0
        transcript = await view.read(info, CONDENSED)

    assert expanded.count == 0
    assert transcript.events_data is not None
    model_events = [e for e in transcript.events if isinstance(e, ModelEvent)]
    assert decodes.count == (
        len(transcript.messages)
        + len(transcript.events_data["messages"])
        + len(model_events)
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("format", ["eval", "json"])
@pytest.mark.parametrize(
    "content",
    [
        CONDENSED,
        TranscriptContent(events=["model"], condensed=True),
        TranscriptContent(messages="all", events="all", timeline=True, condensed=True),
    ],
    ids=["all", "model-events", "timeline"],
)
async def test_condensed_read_expands_to_the_expanded_read(
    tmp_path: Path, content: TranscriptContent, format: Literal["eval", "json"]
) -> None:
    """`expand_events` over a condensed read gives the events read expanded."""
    log = _write_log(tmp_path, 12, format=format)
    expanded_content = TranscriptContent(
        messages=content.messages, events=content.events, timeline=content.timeline
    )
    expanded = await _read(log, expanded_content)
    condensed = await _read(log, content)

    assert condensed.events_data is not None
    assert expanded.events_data is None
    model_events = [e for e in condensed.events if isinstance(e, ModelEvent)]
    assert model_events and all(
        e.input == [] and e.input_refs and e.call and e.call.call_refs
        for e in model_events
    )
    assert _dumps(expand_events(condensed.events, condensed.events_data)) == _dumps(
        expanded.events
    )
    assert condensed.messages == expanded.messages
    # timelines cite the events the scanner receives, at the same positions
    assert [_positions(t, condensed.events) for t in condensed.timelines] == [
        _positions(t, expanded.events) for t in expanded.timelines
    ]


def _with_nested(events: list[Event]) -> list[Event]:
    """Events and those nested in tool-spawned agents."""
    return [
        nested
        for event in events
        for nested in [
            event,
            *(_with_nested(event.events) if isinstance(event, ToolEvent) else []),
        ]
    ]


def _timeline_events(span: TimelineSpan) -> list[Event]:
    events: list[Event] = []
    for item in span.content:
        if isinstance(item, TimelineSpan):
            events.extend(_timeline_events(item))
        else:
            events.append(item.event)
    for branch in span.branches:
        events.extend(_timeline_events(branch))
    return events


def _positions(timeline: Timeline, events: list[Event]) -> list[int]:
    """Where each event a timeline cites sits among `events` (nested included).

    Raises KeyError for a cited event that is not one of `events`.
    """
    index = {id(event): i for i, event in enumerate(_with_nested(events))}
    return [index[id(event)] for event in _timeline_events(timeline.root)]


@pytest.mark.asyncio
async def test_condensed_read_from_parquet_database(tmp_path: Path) -> None:
    """A transcript database serves condensed events like an eval log."""
    log = _write_log(tmp_path / "logs", 12)
    db_dir = tmp_path / "db"
    async with transcripts_db(str(db_dir)) as db:
        await db.insert(transcripts_from(log))
    expanded_from_log = await _read(log, EXPANDED)

    transcripts = transcripts_from(str(db_dir))
    async with transcripts.reader() as reader:
        info = [info async for info in reader.index()][0]
        condensed = await reader.read(info, CONDENSED)
        expanded = await reader.read(info, EXPANDED)

    assert condensed.events_data is not None
    assert all(
        e.input == [] and e.input_refs
        for e in condensed.events
        if isinstance(e, ModelEvent)
    )
    assert _dumps(expand_events(condensed.events, condensed.events_data)) == _dumps(
        expanded.events
    )
    assert _dumps(expanded.events) == _dumps(expanded_from_log.events)


@pytest.mark.parametrize("duplicate_uuid", [False, True], ids=["", "duplicate-uuid"])
@pytest.mark.parametrize(
    "condensed",
    [CONDENSED, TranscriptContent(events=["tool"], condensed=True)],
    ids=["beside-all", "beside-tool-events"],
)
@pytest.mark.parametrize(
    "sibling",
    [
        EXPANDED,
        TranscriptContent(events=["model"]),
        TranscriptContent(messages="all", events="all", timeline=True),
        # model events only through the timeline: the read drops them from
        # the flat list after building it
        TranscriptContent(events=["tool"], timeline=True),
    ],
    ids=["all", "model-events", "timeline", "tool-events-with-timeline"],
)
@pytest.mark.asyncio
async def test_a_scanner_that_does_not_ask_sees_events_as_before(
    tmp_path: Path,
    sibling: TranscriptContent,
    condensed: TranscriptContent,
    duplicate_uuid: bool,
) -> None:
    """Sharing a read with a condensed scanner leaves a sibling's events unchanged."""
    log = _write_log(tmp_path, 12, varied=True, duplicate_uuid=duplicate_uuid)
    alone = filter_transcript(await _read(log, sibling), sibling)
    union = union_transcript_contents([sibling, condensed])
    shared = filter_transcript(await _read(log, union), sibling)

    assert shared.events_data is None
    assert _dumps(shared.events) == _dumps(alone.events)
    assert shared.messages == alone.messages
    assert [t.model_dump() for t in shared.timelines] == [
        t.model_dump() for t in alone.timelines
    ]
    # what each timeline cites, inputs included, in order
    assert [_dumps(_timeline_events(t.root)) for t in shared.timelines] == [
        _dumps(_timeline_events(t.root)) for t in alone.timelines
    ]


def test_condensed_from_an_inline_transcript() -> None:
    """A transcript built with inline inputs is condensed for a condensed scanner."""
    messages, events = _conversation(6)
    transcript = Transcript(transcript_id="t", messages=messages, events=events)
    condensed = filter_transcript(transcript, CONDENSED)

    assert condensed.events_data is not None
    assert all(
        e.input == [] and e.input_refs
        for e in condensed.events
        if isinstance(e, ModelEvent)
    )
    assert _dumps(expand_events(condensed.events, condensed.events_data)) == _dumps(
        events
    )


def test_condensed_requires_a_transcript_scanner() -> None:
    @scanner(events=["model"], condensed=True)
    def model_event_scanner() -> Scanner[ModelEvent]:
        async def scan_event(event: ModelEvent) -> Result:
            return Result(value=True)

        return scan_event

    with pytest.raises(ValueError, match="requires a scanner that takes a Transcript"):
        model_event_scanner()


def test_a_scan_with_a_condensed_sibling_gives_other_scanners_the_same_events(
    tmp_path: Path,
) -> None:
    """A plain scanner sees the same events alone and beside a condensed one."""
    log = _write_log(tmp_path / "logs", 12)
    seen: list[list[dict[str, Any]]] = []

    @scanner(name="plain_scanner", messages="all", events="all")
    def plain_scanner() -> Scanner[Transcript]:
        async def scan_transcript(transcript: Transcript) -> Result:
            assert transcript.events_data is None
            seen.append(_dumps(transcript.events))
            return Result(value=True)

        return scan_transcript

    for run, scanners in enumerate(
        [[plain_scanner()], [plain_scanner(), condensed_scanner()]]
    ):
        status = scan(
            scanners=scanners,
            transcripts=transcripts_from(log),
            scans=str(tmp_path / f"scans-{run}"),
            max_processes=1,
            display="none",
        )
        assert status.complete

    assert len(seen) == 2
    assert seen[0] == seen[1]


def test_a_condensed_scanners_recorded_input_expands_like_any_other(
    tmp_path: Path,
) -> None:
    """The results' `input` column carries the condensed transcript's own pool."""
    log = _write_log(tmp_path / "logs", 12)

    @scanner(name="plain_scanner", messages="all", events="all")
    def plain_scanner() -> Scanner[Transcript]:
        async def scan_transcript(transcript: Transcript) -> Result:
            return Result(value=True)

        return scan_transcript

    status = scan(
        scanners=[plain_scanner(), condensed_scanner()],
        transcripts=transcripts_from(log),
        scans=str(tmp_path / "scans"),
        max_processes=1,
        display="none",
    )
    assert status.complete

    results = scan_results_df(status.location, exclude_columns=[]).scanners
    plain, condensed = (
        json.loads(results[name]["input"].iloc[0])
        for name in ("plain_scanner", "condensed_scanner")
    )
    assert all(e.get("input_refs") is None for e in condensed["events"])
    assert any(e.get("input") for e in condensed["events"])
    assert condensed["events"] == plain["events"]


@loader(events="all")
def transcript_loader() -> Loader[Transcript]:
    async def load(transcript: Transcript) -> AsyncIterator[Transcript]:
        yield transcript

    return load


@loader(events="all")
def model_event_loader() -> Loader[ModelEvent]:
    async def load(transcript: Transcript) -> AsyncIterator[ModelEvent]:
        for event in transcript.events:
            if isinstance(event, ModelEvent):
                yield event

    return load


@pytest.mark.parametrize(
    "custom_loader",
    [transcript_loader, model_event_loader],
    ids=["transcript", "events"],
)
def test_a_custom_loader_beside_a_condensed_scanner_sees_events_as_before(
    tmp_path: Path, custom_loader: Callable[[], Loader[Transcript | ModelEvent]]
) -> None:
    """A custom loader that did not ask gets expanded events and no pool."""
    log = _write_log(tmp_path / "logs", 12)
    seen: list[list[dict[str, Any]]] = []

    @scanner(name="custom_loader_scanner", loader=custom_loader())
    def custom_loader_scanner() -> Scanner[Transcript | ModelEvent]:
        async def scan_input(input: Transcript | ModelEvent) -> Result:
            if isinstance(input, Transcript):
                assert input.events_data is None
                seen.append(_dumps(input.events))
            else:
                seen.append(_dumps([input]))
            return Result(value=True)

        return scan_input

    runs: list[list[list[dict[str, Any]]]] = []
    scanner_sets: list[list[Scanner[Any]]] = [
        [custom_loader_scanner()],
        [custom_loader_scanner(), condensed_scanner()],
    ]
    for run, scanners in enumerate(scanner_sets):
        seen.clear()
        status = scan(
            scanners=scanners,
            transcripts=transcripts_from(log),
            scans=str(tmp_path / f"scans-{run}"),
            max_processes=1,
            display="none",
        )
        assert status.complete
        runs.append(list(seen))

    assert runs[0] and runs[0] == runs[1]
    model_inputs = [
        e["input"] for events in runs[1] for e in events if e["event"] == "model"
    ]
    assert model_inputs and all(model_inputs)


def _bridge_and_warmup_events() -> list[Event]:
    """The two classifications that read beyond a call's system prompt.

    A bridged sub-agent's result is read from the next call's input, and a
    cache-warmup call is recognised by its last user message.
    """
    system = ChatMessageSystem(content="You are a careful agent.")
    user = ChatMessageUser(content="Probe the system.")
    call = ToolCall(id="call-bridge", function="helper", arguments={})
    first = ChatMessageAssistant(content="Delegating.", tool_calls=[call])
    result = ChatMessageTool(
        content="The helper's answer.", tool_call_id=call.id, function="helper"
    )

    def model(
        input: list[ChatMessage], text: str, max_tokens: int | None = None
    ) -> ModelEvent:
        return ModelEvent(
            model="mockllm/model",
            input=input,
            tools=[],
            tool_choice="auto",
            config=GenerateConfig(max_tokens=max_tokens),
            output=ModelOutput.from_content(model="mockllm/model", content=text),
        )

    span = "agent-call-bridge"
    return [
        model([system, ChatMessageUser(content="warm")], "ok", max_tokens=1),
        model([system, user], "Delegating."),
        SpanBeginEvent(id=span, name="helper", type="agent", span_id=span),
        model(
            [ChatMessageSystem(content="You are a helper."), user],
            "The helper's answer.",
        ),
        SpanEndEvent(id=span, span_id=span),
        model([system, user, first, result], "Done."),
    ]


@pytest.mark.parametrize(
    "events",
    [
        _conversation(12)[1],
        _conversation(30, varied=True)[1],
        _conversation(12, varied=True, duplicate_uuid=True)[1],
        agentic_events(),
        _bridge_and_warmup_events(),
    ],
    ids=["conversation", "varied", "duplicate-uuid", "agentic", "bridge-and-warmup"],
)
def test_a_timeline_built_from_condensed_events_equals_the_expanded_build(
    events: list[Event],
) -> None:
    condensed, events_data = condense_events(events)
    built = build_timeline(condensed, events_data)
    expected = timeline_build(events)

    assert timeline_dump(built) == timeline_dump(expected)
    assert _positions(built, condensed) == _positions(expected, events)


@pytest.mark.asyncio
async def test_condensed_read_with_a_built_timeline_does_linear_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Building a timeline over a condensed read expands no input.

    Counts messages decoded, message slots expanded by inspect_ai's pool
    resolution, and messages read through pooled-input views, at n and 2n
    turns of a log with no stored timeline. The log has every kind of call
    `timeline_build` reads inputs for (see `_conversation(varied=True)`).
    """
    decodes = _Decodes(monkeypatch)
    expanded = _ExpandedSlots(monkeypatch)
    work = {"viewed": 0}

    def counting(view: Any) -> Any:
        def wrapped(self: PooledInput) -> Iterator[ChatMessage]:
            for message in view(self):
                work["viewed"] += 1
                yield message

        return wrapped

    monkeypatch.setattr(PooledInput, "__iter__", counting(PooledInput.__iter__))
    monkeypatch.setattr(PooledInput, "__reversed__", counting(PooledInput.__reversed__))

    content = TranscriptContent(
        messages="all", events="all", timeline=True, condensed=True
    )
    counts: dict[int, dict[str, int]] = {}
    for turns in (20, 40):
        log = _write_log(tmp_path / f"logs-{turns}", turns, varied=True)
        async with EvalLogTranscriptsView(str(log)) as view:
            info = [info async for info in view.select()][0]
            decodes.count = expanded.count = work["viewed"] = 0
            transcript = await view.read(info, content)
        assert transcript.timelines
        assert transcript.events_data is not None
        counts[turns] = {
            "decodes": decodes.count,
            "expanded": expanded.count,
            **work,
        }

    for counted in ("decodes", "viewed"):
        assert counts[40][counted] <= 2.2 * counts[20][counted], counts
    assert counts[20]["expanded"] == counts[40]["expanded"] == 0, counts


def test_a_condensed_scanner_as_a_scorer_gets_condensed_events() -> None:
    task = Task(scorer=as_scorer(condensed_scanner()))
    log = eval(tasks=task, model="mockllm/model", display="none")[0]

    assert log.status == "success"
    assert log.samples and log.samples[0].scores
    (score,) = log.samples[0].scores.values()
    # the scanner asserts it got refs and a pool; its value is the pool's size
    assert isinstance(score.value, int) and score.value > 0


@pytest.mark.asyncio
async def test_a_condensed_input_recorded_without_pooling_is_expanded(
    tmp_path: Path,
) -> None:
    log = _write_log(tmp_path, 6)
    condensed = await _read(log, CONDENSED)
    expanded = await _read(log, EXPANDED)
    report = ResultReport(
        input_type="transcript",
        input_ids=[condensed.transcript_id],
        input=condensed,
        result=Result(value=True),
        validation=None,
        error=None,
        events=[],
        model_usage={},
    )

    columns = report.to_df_columns(pool_dedup=False)

    assert columns["input_data"] is None
    input_json = columns["input"]
    assert isinstance(input_json, (bytes, bytearray))
    recorded = Transcript.model_validate_json(input_json)
    assert _dumps(recorded.events) == _dumps(expanded.events)


@pytest.mark.asyncio
async def test_opening_a_large_transcript_condensed_materializes_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The spool expands inputs as it replays, so condensed opens skip it."""
    monkeypatch.setattr(constants_mod, "SPOOL_THRESHOLD_BYTES", 0)
    log = _write_log(tmp_path, 6)
    async with EvalLogTranscriptsView(str(log)) as view:
        info = [info async for info in view.select()][0]
        async with await view.open(info, CONDENSED) as handle:
            assert isinstance(handle, MaterializedTranscriptHandle)
            transcript = await handle.load()

    assert transcript.events_data is not None
    assert all(
        e.input == [] and e.input_refs
        for e in transcript.events
        if isinstance(e, ModelEvent)
    )


def test_a_scan_expands_a_condensed_read_once_and_isolates_each_pool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Plain scanners share one expansion; no scanner can rearrange another's pool.

    The condensed lead runs first and reverses its pool in place.
    """
    log = _write_log(tmp_path / "logs", 12)
    expanded = _ExpandedSlots(monkeypatch)
    first_inputs: list[str] = []
    first_pool_rows: list[str] = []

    @scanner(name="pool_reverser", messages="all", events="all", condensed=True)
    def pool_reverser() -> Scanner[Transcript]:
        async def scan_transcript(transcript: Transcript) -> Result:
            assert transcript.events_data is not None
            transcript.events_data["messages"].reverse()
            return Result(value=True)

        return scan_transcript

    @scanner(name="pool_reader", messages="all", events="all", condensed=True)
    def pool_reader() -> Scanner[Transcript]:
        async def scan_transcript(transcript: Transcript) -> Result:
            assert transcript.events_data is not None
            first_pool_rows.append(transcript.events_data["messages"][0].text)
            return Result(value=True)

        return scan_transcript

    @scanner(name="plain_reader", messages="all", events="all")
    def plain_reader() -> Scanner[Transcript]:
        async def scan_transcript(transcript: Transcript) -> Result:
            model = next(e for e in transcript.events if isinstance(e, ModelEvent))
            first_inputs.append(model.input[0].text)
            return Result(value=True)

        return scan_transcript

    def run(name: str, scanners: list[Scanner[Any]]) -> int:
        expanded.count = 0
        status = scan(
            scanners=scanners,
            transcripts=transcripts_from(log),
            scans=str(tmp_path / name),
            max_processes=1,
            display="none",
        )
        assert status.complete
        return expanded.count

    plain_only = run("plain", [plain_reader(), plain_reader()])
    mixed = run(
        "mixed", [pool_reverser(), pool_reader(), plain_reader(), plain_reader()]
    )

    assert plain_only > 0 and mixed == plain_only
    assert first_inputs == ["You are a careful agent."] * 4
    assert first_pool_rows == ["You are a careful agent."]


def test_a_pooled_input_equals_the_expanded_input() -> None:
    _, events = _conversation(6)
    condensed, events_data = condense_events(events)
    pool = events_data["messages"]
    for original, event in zip(events, condensed, strict=True):
        if isinstance(event, ModelEvent):
            assert isinstance(original, ModelEvent) and event.input_refs is not None
            view = PooledInput(event.input_refs, pool)
            assert view == original.input and list(view) == original.input
            assert list(reversed(view)) == original.input[::-1]
            assert view[-1] == original.input[-1]
            assert view != original.input[:-1]


def test_bridged_sub_agents_on_every_turn_cost_what_inspect_ai_timeline_build_costs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pins a known quadratic walk in inspect_ai's `timeline_build`.

    For each bridged `agent-<call id>` span, `_extract_agent_results`
    (inspect_ai/event/_timeline.py) scans the next call's whole input for the
    tool result, so with a bridge on every turn the messages it reads grow
    with the square of the turns. The expanded build reads the same messages;
    the fix belongs in inspect_ai (an index of tool results built once,
    queued for R7 PR 6). These counts are pinned so that fix shows up here as
    a change: update them, and expect them to grow linearly.
    """
    viewed = {"count": 0}

    def counting(view: Any) -> Any:
        def wrapped(self: PooledInput) -> Iterator[ChatMessage]:
            for message in view(self):
                viewed["count"] += 1
                yield message

        return wrapped

    monkeypatch.setattr(PooledInput, "__iter__", counting(PooledInput.__iter__))
    monkeypatch.setattr(PooledInput, "__reversed__", counting(PooledInput.__reversed__))

    counts: dict[int, int] = {}
    for turns in (20, 40):
        events = _conversation(turns, bridge_every_turn=True)[1]
        condensed, events_data = condense_events(events)
        viewed["count"] = 0
        built = build_timeline(condensed, events_data)
        counts[turns] = viewed["count"]
        assert timeline_dump(built) == timeline_dump(timeline_build(events))

    assert counts == {20: 483, 40: 1868}


@scanner(name="messages_only", messages="all")
def messages_only() -> Scanner[Transcript]:
    async def scan_transcript(transcript: Transcript) -> Result:
        assert transcript.events == [] and transcript.events_data is None
        return Result(value=len(transcript.messages))

    return scan_transcript


def test_siblings_that_want_no_model_events_expand_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Messages-only and tool-events-only siblings keep a condensed scan linear."""
    expanded = _ExpandedSlots(monkeypatch)
    decodes = _Decodes(monkeypatch)
    tool_events: dict[str, list[dict[str, Any]]] = {}

    @scanner(name="tool_events_only", events=["tool"])
    def tool_events_only() -> Scanner[Transcript]:
        async def scan_transcript(transcript: Transcript) -> Result:
            assert transcript.events_data is None
            assert all(isinstance(e, ToolEvent) for e in transcript.events)
            tool_events[run_name] = _dumps(transcript.events)
            return Result(value=len(transcript.events))

        return scan_transcript

    counts: dict[int, dict[str, int]] = {}
    run_name = ""
    for turns in (20, 40):
        log = _write_log(tmp_path / f"logs-{turns}", turns)
        for run_name, scanners in (
            (f"alone-{turns}", [tool_events_only()]),
            (
                f"mixed-{turns}",
                [condensed_scanner(), messages_only(), tool_events_only()],
            ),
        ):
            expanded.count = decodes.count = 0
            status = scan(
                scanners=scanners,
                transcripts=transcripts_from(log),
                scans=str(tmp_path / run_name),
                max_processes=1,
                display="none",
            )
            assert status.complete
        counts[turns] = {"expanded": expanded.count, "decodes": decodes.count}

    assert counts[20]["expanded"] == counts[40]["expanded"] == 0, counts
    assert counts[40]["decodes"] <= 2.2 * counts[20]["decodes"], counts
    for turns in (20, 40):
        assert tool_events[f"mixed-{turns}"] == tool_events[f"alone-{turns}"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content",
    [
        TranscriptContent(messages="all"),
        TranscriptContent(events=["tool"]),
        TranscriptContent(events=["tool"], timeline=["tool"]),
    ],
    ids=["messages", "tool-events", "tool-timeline"],
)
async def test_filtering_a_condensed_read_expands_only_what_is_kept(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, content: TranscriptContent
) -> None:
    log = _write_log(tmp_path, 12)
    union = union_transcript_contents(
        [content, TranscriptContent(events="all", timeline=True, condensed=True)]
    )
    shared = await _read(log, union)
    alone = filter_transcript(await _read(log, content), content)
    expanded = _ExpandedSlots(monkeypatch)

    filtered = filter_transcript(shared, content)

    assert expanded.count == 0
    assert filtered.events_data is None
    assert _dumps(filtered.events) == _dumps(alone.events)
    assert [t.model_dump() for t in filtered.timelines] == [
        t.model_dump() for t in alone.timelines
    ]


def test_a_plain_timeline_scanner_beside_a_condensed_one_keeps_its_timeline_inputs(
    tmp_path: Path,
) -> None:
    """Model events reached only through a timeline are expanded for a plain scanner."""
    log = _write_log(tmp_path / "logs", 6)
    seen: dict[str, list[tuple[int, Any]]] = {}

    @scanner(name="timeline_tools", events=["tool"], timeline=True)
    def timeline_tools() -> Scanner[Transcript]:
        async def scan_transcript(transcript: Transcript) -> Result:
            assert transcript.events_data is None
            seen[run_name] = [
                (len(event.input), event.input_refs)
                for timeline in transcript.timelines
                for event in _timeline_events(timeline.root)
                if isinstance(event, ModelEvent)
            ]
            return Result(value=True)

        return scan_transcript

    @scanner(name="condensed_tools", events=["tool"], condensed=True)
    def condensed_tools() -> Scanner[Transcript]:
        async def scan_transcript(transcript: Transcript) -> Result:
            assert transcript.events_data is not None
            return Result(value=True)

        return scan_transcript

    run_name = ""
    for run_name, scanners in (
        ("alone", [timeline_tools()]),
        ("mixed", [condensed_tools(), timeline_tools()]),
    ):
        status = scan(
            scanners=scanners,
            transcripts=transcripts_from(log),
            scans=str(tmp_path / run_name),
            max_processes=1,
            display="none",
        )
        assert status.complete

    assert seen["alone"] and all(size > 0 for size, _ in seen["alone"])
    assert seen["mixed"] == seen["alone"]


def test_condensing_an_inline_transcript_condenses_what_its_timelines_cite() -> None:
    _, events = _conversation(6)
    transcript = Transcript(
        transcript_id="t", events=events, timelines=[timeline_build(events)]
    )
    content = TranscriptContent(events=["tool"], timeline=True, condensed=True)

    condensed = filter_transcript(transcript, content)

    assert condensed.events_data is not None
    (timeline,) = condensed.timelines
    cited = _timeline_events(timeline.root)
    model_events = [e for e in cited if isinstance(e, ModelEvent)]
    assert model_events and all(e.input == [] and e.input_refs for e in model_events)
    (original,) = transcript.timelines
    assert _dumps(expand_events(cited, condensed.events_data)) == _dumps(
        _timeline_events(original.root)
    )


@loader(events="all", condensed=True)
def condensed_loader() -> Loader[Transcript]:
    async def load(transcript: Transcript) -> AsyncIterator[Transcript]:
        yield transcript

    return load


@scanner(events="all", loader=condensed_loader())
def scanner_with_a_condensed_loader() -> Scanner[Transcript]:
    async def scan_transcript(transcript: Transcript) -> Result:
        assert transcript.events_data is not None
        return Result(value=len(transcript.events_data["messages"]))

    return scan_transcript


def test_a_scorer_honours_a_custom_loaders_condensed_setting() -> None:
    task = Task(scorer=as_scorer(scanner_with_a_condensed_loader()))
    log = eval(tasks=task, model="mockllm/model", display="none")[0]

    assert log.status == "success"
    assert log.samples and log.samples[0].scores
    (score,) = log.samples[0].scores.values()
    assert isinstance(score.value, int) and score.value > 0


def test_condensing_leaves_events_nested_in_tool_spawned_agents_as_they_are() -> None:
    """Timelines keep citing the nested events the tool events hold."""
    events = agentic_events()
    transcript = Transcript(
        transcript_id="t", events=events, timelines=[timeline_build(events)]
    )
    content = TranscriptContent(events="all", timeline=True, condensed=True)

    condensed = filter_transcript(transcript, content)

    held = {id(event) for event in _with_nested(condensed.events)}
    (timeline,) = condensed.timelines
    assert all(id(event) in held for event in _timeline_events(timeline.root))
