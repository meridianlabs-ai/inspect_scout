"""Equivalence: streamed handle vs materialized read() on real eval logs."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import Any

import pytest
from inspect_ai.event import ModelEvent, ToolEvent
from inspect_ai.log import read_eval_log, write_eval_log
from inspect_scout._transcript.eval_log import EvalLogTranscriptsView
from inspect_scout._transcript.handle import (
    MaterializedTranscriptHandle,
    SpooledTranscriptHandle,
)
from inspect_scout._transcript.json.load_filtered import load_filtered_transcript
from inspect_scout._transcript.json.stream_parse import (
    StreamParseResult,
    stream_parse_to_spool,
)
from inspect_scout._transcript.types import (
    Transcript,
    TranscriptContent,
    TranscriptInfo,
)
from inspect_scout._util import constants as constants_mod

LOGS_DIR = Path(__file__).parent.parent / "recorder" / "logs"
LOGS = sorted(LOGS_DIR.glob("*.eval"))

CONTENTS = [
    TranscriptContent(messages="all", events=None),
    TranscriptContent(messages=["assistant"], events=None),
    TranscriptContent(messages="all", events="all"),
    TranscriptContent(messages=None, events=["model"]),
]


async def _assert_streamed_equals_materialized(
    log: Path, content: TranscriptContent
) -> None:
    """Streamed handle and materialized read agree on the first transcript."""
    view = EvalLogTranscriptsView(str(log))
    await view.connect()
    try:
        infos = [i async for i in view.select()]
        assert infos
        info = infos[0]
        materialized = await view.read(info, content)
        async with await view.open(info, content) as h:
            assert isinstance(h, SpooledTranscriptHandle)
            streamed_messages = [m async for m in h.messages()]
            streamed_events = [e async for e in h.events()]
            loaded = await h.load()
        assert [m.model_dump() for m in streamed_messages] == [
            m.model_dump() for m in materialized.messages
        ]
        assert [e.model_dump() for e in streamed_events] == [
            e.model_dump() for e in materialized.events
        ]
        assert loaded.metadata == materialized.metadata
    finally:
        await view.disconnect()


@pytest.mark.asyncio
@pytest.mark.parametrize("log", LOGS, ids=[log.name for log in LOGS])
@pytest.mark.parametrize(
    "content",
    CONTENTS,
    ids=[
        "messages-all",
        "messages-assistant",
        "messages-and-events-all",
        "events-model",
    ],
)
async def test_streamed_equals_materialized(
    log: Path, content: TranscriptContent, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Force the spooled path regardless of file size
    monkeypatch.setattr(constants_mod, "SPOOL_THRESHOLD_BYTES", 0)
    await _assert_streamed_equals_materialized(log, content)


@pytest.mark.asyncio
async def test_small_file_uses_materialized_handle() -> None:
    # default threshold (64MB) >> fixture size -> MaterializedTranscriptHandle
    view = EvalLogTranscriptsView(str(LOGS[0]))
    await view.connect()
    try:
        infos = [i async for i in view.select()]
        cm = await view.open(infos[0], TranscriptContent(messages="all", events=None))
        async with cm as h:
            assert isinstance(h, MaterializedTranscriptHandle)
    finally:
        await view.disconnect()


@pytest.mark.asyncio
async def test_timeline_request_uses_materialized_handle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Even above the spool threshold (forced to 0), a timeline request needs
    # the full in-memory event set, so it must use the materialized path.
    monkeypatch.setattr(constants_mod, "SPOOL_THRESHOLD_BYTES", 0)
    view = EvalLogTranscriptsView(str(LOGS[0]))
    await view.connect()
    try:
        infos = [i async for i in view.select()]
        cm = await view.open(
            infos[0],
            TranscriptContent(messages="all", events="all", timeline="all"),
        )
        async with cm as h:
            assert isinstance(h, MaterializedTranscriptHandle)
    finally:
        await view.disconnect()


# None of the fixture logs in tests/recorder/logs/ contain an `events_data`
# pool (all four only have the legacy top-level `attachments` dict), so pool
# resolution during streaming replay is covered by the `pooled_log` fixture
# below and by test_attachment_refs_only_inside_pool_entries_resolve.


@pytest.mark.parametrize(
    "content",
    [
        TranscriptContent(messages="all", events="all"),
        TranscriptContent(messages=None, events="all"),
    ],
    ids=["messages-and-events", "events-only"],
)
@pytest.mark.asyncio
async def test_attachment_refs_only_inside_pool_entries_resolve(
    content: TranscriptContent, tmp_path: Path
) -> None:
    """A ref reachable only through a pool entry resolves on both paths.

    `attachments` precedes `events_data` in the sample, so a membership test
    while the attachments stream cannot know a pooled message will need one.
    The streamed path spools every attachment and resolved these already; the
    materialized path dropped them, leaving `attachment://<hash>` as literal
    text -- and which path runs depends only on whether the sample crosses the
    spool threshold. The events-only case matters most: with messages filtered
    out, nothing else registers the ref.
    """
    att = "a" * 32
    sample = {
        "id": "s1",
        "messages": [{"id": "m1", "role": "user", "content": "hello"}],
        "attachments": {att: "POOLED SYSTEM PROMPT"},
        "events": [
            {
                "span_id": "s1",
                "timestamp": "2022-01-01T00:00:00+00:00",
                "working_start": 0,
                "event": "model",
                "model": "m",
                "input": [],
                "input_refs": [[0, 1]],
                "output": {"model": "m", "choices": []},
                "tools": [],
                "tool_choice": "auto",
                "config": {},
            }
        ],
        "events_data": {
            "messages": [
                {"id": "p0", "role": "system", "content": f"attachment://{att}"}
            ],
            "calls": [],
        },
    }
    data = json.dumps(sample).encode()
    info = TranscriptInfo(transcript_id="t1")

    materialized = await load_filtered_transcript(
        io.BytesIO(data), info, content.messages, content.events
    )
    parsed = await stream_parse_to_spool(
        io.BytesIO(data), content.messages, content.events, tmp_path
    )

    async def parse() -> StreamParseResult:
        return parsed

    async def fallback() -> Transcript:
        raise AssertionError("fallback should not be called")

    handle = SpooledTranscriptHandle(info, parse, fallback)
    try:
        streamed = await handle.load()
    finally:
        await handle.aclose()

    def pooled_input(transcript: Transcript) -> Any:
        return transcript.events[0].model_dump()["input"]

    assert pooled_input(materialized) == pooled_input(streamed)
    assert pooled_input(materialized)[0]["content"] == "POOLED SYSTEM PROMPT"


@pytest.mark.asyncio
async def test_streamed_hydrates_nested_tool_events_materialized_does_not(
    tmp_path: Path,
) -> None:
    """Pins a known streamed/materialized divergence on nested `ToolEvent.events`.

    `ToolEvent.events` is typed `list[Any]` (a legacy field for tool-spawned
    agents; see `inspect_ai.event._tool.ToolEvent`), so `Transcript.model_validate`
    on the materialized path (`load_filtered.py`) never coerces its entries --
    they stay raw dicts. The streamed replay path validates the ones that are
    events via `_hydrate_nested_tool_events` (`stream_parse.py`), because
    consumers that walk nested events expect real `Event` instances. This
    asserts the actual (differing) behaviour of each path rather than
    equality, so a future change that silently widens or closes the gap is
    caught either way. See the PR description for why this is accepted rather
    than fixed here: hydrating is the behaviour a real consumer needs, so the
    materialized path -- not the streamed one -- is the one that's arguably
    incomplete.
    """
    nested_model_event = {
        "event": "model",
        "span_id": "s2",
        "timestamp": "2022-01-01T00:00:01+00:00",
        "working_start": 1,
        "model": "m",
        "input": [],
        "output": {"model": "m", "choices": []},
        "tools": [],
        "tool_choice": "auto",
        "config": {},
    }
    sample = {
        "id": "s1",
        "messages": [{"id": "m1", "role": "user", "content": "hello"}],
        "events": [
            {
                "event": "tool",
                "span_id": "s1",
                "timestamp": "2022-01-01T00:00:00+00:00",
                "working_start": 0,
                "id": "call1",
                "function": "run_agent",
                "arguments": {},
                "agent": "sub_agent",
                "events": [nested_model_event],
            }
        ],
    }
    data = json.dumps(sample).encode()
    info = TranscriptInfo(transcript_id="t1")

    materialized = await load_filtered_transcript(io.BytesIO(data), info, None, "all")
    parsed = await stream_parse_to_spool(io.BytesIO(data), None, "all", tmp_path)

    async def parse() -> StreamParseResult:
        return parsed

    async def fallback() -> Transcript:
        raise AssertionError("fallback should not be called")

    handle = SpooledTranscriptHandle(info, parse, fallback)
    try:
        streamed = await handle.load()
    finally:
        await handle.aclose()

    materialized_tool_event = materialized.events[0]
    streamed_tool_event = streamed.events[0]
    assert isinstance(materialized_tool_event, ToolEvent)
    assert isinstance(streamed_tool_event, ToolEvent)

    # Materialized: nested events stay raw dicts (list[Any] isn't coerced).
    assert materialized_tool_event.events == [nested_model_event]
    assert not isinstance(materialized_tool_event.events[0], ModelEvent)

    # Streamed: `_hydrate_nested_tool_events` validates them into real Events.
    assert isinstance(streamed_tool_event.events[0], ModelEvent)
    assert streamed_tool_event.events[0].model == "m"


@pytest.fixture(scope="module")
def pooled_log(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A log whose samples carry a machine-generated `events_data` pool.

    The checked-in fixtures predate pooling, so nothing else exercises the
    spool's pool branches against real `condense_sample` output. Repeating a
    message gives the condenser something to pool; `write_eval_log` condenses.
    """
    log = read_eval_log(str(LOGS[0]))
    samples = log.samples or []
    assert samples, "fixture log has no samples"
    sample = samples[0]

    repeated = list(sample.messages) * 4
    for event in sample.events:
        if isinstance(event, ModelEvent):
            event.input = repeated

    out = tmp_path_factory.mktemp("pooled") / "pooled.eval"
    write_eval_log(log, str(out))
    return out


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content",
    CONTENTS,
    ids=[
        "messages-all",
        "messages-assistant",
        "messages-and-events-all",
        "events-model",
    ],
)
async def test_streamed_equals_materialized_with_a_generated_pool(
    pooled_log: Path, content: TranscriptContent, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same equivalence, on pool-encoded events rather than inline ones.

    Pooled events reach the spool as range refs into `events_data`, so this
    exercises the ref-resolution path that inline-event fixtures never touch.
    """
    monkeypatch.setattr(constants_mod, "SPOOL_THRESHOLD_BYTES", 0)

    with zipfile.ZipFile(pooled_log) as z:
        members = [i for i in z.infolist() if i.filename.startswith("samples/")]
        assert members
        raw = json.loads(z.read(max(members, key=lambda i: i.file_size).filename))
    pool = (raw.get("events_data") or {}).get("messages") or []
    assert pool, "fixture is vacuous: the writer produced no message pool"

    await _assert_streamed_equals_materialized(pooled_log, content)


@pytest.mark.asyncio
async def test_materialized_preserves_timelines_spooled_drops_them(
    tmp_path: Path,
) -> None:
    """Pins a known streamed/materialized divergence on `Transcript.timelines`.

    `stream_parse_to_spool` skips the sample's `timelines` section entirely --
    `StreamParseResult` has no field for it -- so anything materialized from a
    spooled handle reports `timelines == []`. `load_filtered.py` resolves and
    keeps them.

    This is asserted rather than fixed because spooling the section is a
    feature change, not a carve. It is pinned in both directions so the gap
    cannot widen or close silently: `EvalLogTranscriptsView.open` routes on
    the *requested* `content.timeline`, never on whether the sample *stores*
    timelines, so a consumer that reads `.timelines` off a transcript
    recovered from a spooled handle sees an empty list with no signal that
    anything was dropped. Closing the gap should turn this test red.
    """
    event_uuid = "11111111-1111-1111-1111-111111111111"
    sample = {
        "id": "s1",
        "messages": [{"id": "m1", "role": "user", "content": "hello"}],
        "events": [
            {
                "event": "model",
                "uuid": event_uuid,
                "span_id": "s1",
                "timestamp": "2022-01-01T00:00:00+00:00",
                "working_start": 0,
                "model": "m",
                "input": [],
                "output": {"model": "m", "choices": []},
                "tools": [],
                "tool_choice": "auto",
                "config": {},
            }
        ],
        "timelines": [
            {
                "name": "default",
                "description": "the stored timeline",
                "root": {
                    "type": "span",
                    "id": "main",
                    "name": "main",
                    "span_type": "agent",
                    "content": [{"type": "event", "event": event_uuid}],
                },
            }
        ],
    }
    data = json.dumps(sample).encode()
    info = TranscriptInfo(transcript_id="t1")

    materialized = await load_filtered_transcript(io.BytesIO(data), info, "all", "all")
    parsed = await stream_parse_to_spool(io.BytesIO(data), "all", "all", tmp_path)

    async def parse() -> StreamParseResult:
        return parsed

    async def fallback() -> Transcript:
        raise AssertionError("fallback should not be called")

    handle = SpooledTranscriptHandle(info, parse, fallback)
    try:
        streamed = await handle.load()
    finally:
        await handle.aclose()

    assert [tl.name for tl in materialized.timelines] == ["default"]
    assert materialized.timelines[0].root.id == "main"
    assert streamed.timelines == []
