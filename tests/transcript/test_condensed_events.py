"""Condensed model events: a scanner can ask for `input_refs` and the pool."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Iterator

import pytest
from inspect_ai.event import (
    CompactionEvent,
    Event,
    ModelEvent,
    SpanBeginEvent,
    SpanEndEvent,
    ToolEvent,
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
from inspect_scout._transcript.database.factory import transcripts_db
from inspect_scout._transcript.eval_log import EvalLogTranscriptsView
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.handle import TranscriptHandle
from inspect_scout._transcript.types import Transcript, TranscriptContent
from inspect_scout._transcript.util import (
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


def _conversation(turns: int) -> tuple[list[ChatMessage], list[Event]]:
    """An agent loop of `turns` model calls, each re-sending the conversation.

    Every turn makes two parallel tool calls, and a compaction halfway
    through restarts the conversation from a summary, so the inputs grow
    with the turn count as a real run's do.
    """
    conversation: list[ChatMessage] = [
        ChatMessageSystem(content="You are a careful agent."),
        ChatMessageUser(content="Probe the system."),
    ]
    events: list[Event] = []
    for turn in range(turns):
        if turn == turns // 2:
            events.append(CompactionEvent(type="summary"))
            conversation = [
                conversation[0],
                ChatMessageUser(content=f"Summary of turns 0 to {turn - 1}."),
            ]
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
    return conversation, events


def _write_log(directory: Path, turns: int) -> Path:
    """An `.eval` log holding one sample of `turns` turns (pooled on write)."""
    log = read_eval_log(str(BASE_LOG))
    assert log.samples
    sample = log.samples[0]
    sample.messages, sample.events = _conversation(turns)
    sample.timelines = None
    log.samples = [sample]
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"turns-{turns}.eval"
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
    async with EvalLogTranscriptsView(str(log)) as view:
        info = [info async for info in view.select()][0]
        decodes.count = 0
        transcript = await view.read(info, CONDENSED)

    assert transcript.events_data is not None
    model_events = [e for e in transcript.events if isinstance(e, ModelEvent)]
    assert decodes.count == (
        len(transcript.messages)
        + len(transcript.events_data["messages"])
        + len(model_events)
    )


@pytest.mark.asyncio
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
    tmp_path: Path, content: TranscriptContent
) -> None:
    """`expand_events` over a condensed read gives the events read expanded."""
    log = _write_log(tmp_path, 12)
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
    # timelines bind to the events the scanner receives
    assert len(condensed.timelines) == len(expanded.timelines)
    for timeline in condensed.timelines:
        bound = {id(event) for event in condensed.events}
        assert all(id(event) in bound for event in _timeline_events(timeline.root))


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


def _timeline_events(node: Any) -> list[Event]:
    events: list[Event] = []
    for item in getattr(node, "content", []):
        if item.type == "event":
            events.append(item.event)
        else:
            events.extend(_timeline_events(item))
    return events


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


@pytest.mark.parametrize(
    "sibling",
    [
        EXPANDED,
        TranscriptContent(events=["model"]),
        TranscriptContent(messages="all", events="all", timeline=True),
    ],
    ids=["all", "model-events", "timeline"],
)
@pytest.mark.asyncio
async def test_a_scanner_that_does_not_ask_sees_events_as_before(
    tmp_path: Path, sibling: TranscriptContent
) -> None:
    """Sharing a read with a condensed scanner leaves a sibling's events unchanged."""
    log = _write_log(tmp_path, 12)
    alone = filter_transcript(await _read(log, sibling), sibling)
    union = union_transcript_contents([sibling, CONDENSED])
    shared = filter_transcript(await _read(log, union), sibling)

    assert shared.events_data is None
    assert _dumps(shared.events) == _dumps(alone.events)
    assert shared.messages == alone.messages
    assert [t.model_dump() for t in shared.timelines] == [
        t.model_dump() for t in alone.timelines
    ]
    for timeline in shared.timelines:
        bound = {id(event) for event in shared.events}
        assert all(id(event) in bound for event in _timeline_events(timeline.root))


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
        agentic_events(),
        _bridge_and_warmup_events(),
    ],
    ids=["conversation", "agentic", "bridge-and-warmup"],
)
def test_a_timeline_built_from_condensed_events_equals_the_expanded_build(
    events: list[Event],
) -> None:
    condensed, events_data = condense_events(events)
    built = build_timeline(condensed, events_data)

    assert timeline_dump(built) == timeline_dump(timeline_build(events))
    bound = {id(event) for event in _with_nested(condensed)}
    assert all(id(event) in bound for event in _timeline_events(built.root))


@pytest.mark.asyncio
async def test_condensed_read_with_a_built_timeline_does_linear_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Building a timeline over a condensed read expands no input.

    Counts messages decoded, message slots expanded by inspect_ai's pool
    resolution, and messages read through pooled-input views, at n and 2n
    turns of a log with no stored timeline.
    """
    from inspect_ai.event import _pool
    from inspect_scout._transcript import util

    decodes = _Decodes(monkeypatch)
    work = {"expanded": 0, "viewed": 0}

    expand_refs = _pool._expand_refs

    def counting_expand_refs(refs: Any, pool: Any) -> Any:
        expanded = expand_refs(refs, pool)
        work["expanded"] += len(expanded)
        return expanded

    monkeypatch.setattr(_pool, "_expand_refs", counting_expand_refs)

    def counting(view: Any) -> Any:
        def wrapped(self: util.PooledInput) -> Iterator[ChatMessage]:
            for message in view(self):
                work["viewed"] += 1
                yield message

        return wrapped

    monkeypatch.setattr(
        util.PooledInput, "__iter__", counting(util.PooledInput.__iter__)
    )
    monkeypatch.setattr(
        util.PooledInput, "__reversed__", counting(util.PooledInput.__reversed__)
    )

    content = TranscriptContent(
        messages="all", events="all", timeline=True, condensed=True
    )
    counts: dict[int, dict[str, int]] = {}
    for turns in (20, 40):
        log = _write_log(tmp_path / f"logs-{turns}", turns)
        async with EvalLogTranscriptsView(str(log)) as view:
            info = [info async for info in view.select()][0]
            decodes.count = 0
            work.update(expanded=0, viewed=0)
            transcript = await view.read(info, content)
        assert transcript.timelines
        assert transcript.events_data is not None
        counts[turns] = {"decodes": decodes.count, **work}

    for counted in ("decodes", "viewed"):
        assert counts[40][counted] <= 2.2 * counts[20][counted], counts
    assert counts[20]["expanded"] == counts[40]["expanded"] == 0, counts
