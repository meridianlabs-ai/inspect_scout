"""Pooled storage keeps each input message's ID."""

import json
from datetime import datetime
from pathlib import Path

import pytest
from inspect_ai.event import Event, ModelEvent
from inspect_ai.log import expand_events
from inspect_ai.model import ChatMessage, ChatMessageUser, GenerateConfig, ModelOutput
from inspect_scout._scanner.result import Result, ResultReport
from inspect_scout._transcript.condense import condense_events
from inspect_scout._transcript.database.parquet import ParquetTranscriptsDB
from inspect_scout._transcript.types import Transcript, TranscriptContent


def _call(uuid: str, input: list[ChatMessage]) -> ModelEvent:
    return ModelEvent(
        model="m",
        input=input,
        tools=[],
        tool_choice="auto",
        config=GenerateConfig(),
        output=ModelOutput(),
        timestamp=datetime(2026, 1, 1),
        uuid=uuid,
    )


def _transcript() -> Transcript:
    """Two calls sending equal text as two different messages."""
    human_b = ChatMessageUser(content="same", id="human-b")
    return Transcript(
        transcript_id="t1",
        source_type="test",
        source_id="s1",
        source_uri="test://uri",
        messages=[human_b],
        messages_from=["b"],
        events=[
            _call("a", [ChatMessageUser(content="same", id="human-a")]),
            _call("b", [human_b]),
        ],
    )


def _input_ids(events: list[Event]) -> list[list[str | None]]:
    return [
        [message.id for message in event.input]
        for event in events
        if isinstance(event, ModelEvent)
    ]


@pytest.mark.asyncio
async def test_stored_transcript_keeps_input_message_ids(tmp_path: Path) -> None:
    db = ParquetTranscriptsDB(str(tmp_path))
    await db.connect()
    try:
        await db.insert([_transcript()])
        [info] = [info async for info in db.select()]
        stored = await db.read(info, TranscriptContent(messages="all", events="all"))
    finally:
        await db.disconnect()

    assert _input_ids(stored.events) == [["human-a"], ["human-b"]]
    assert [m.id for m in stored.messages] == ["human-b"]


def test_scanned_transcript_input_keeps_message_ids() -> None:
    report = ResultReport(
        input_type="transcript",
        input_ids=["t1"],
        input=_transcript(),
        result=Result(value="yes"),
        validation=None,
        error=None,
        events=[],
        model_usage={},
    )

    columns = report.to_df_columns(pool_dedup=True)

    input_json, input_data = columns["input"], columns["input_data"]
    assert isinstance(input_json, (bytes, bytearray))
    assert isinstance(input_data, (bytes, bytearray))
    events = json.loads(input_json)["events"]
    expanded = expand_events(json.dumps(events), input_data.decode())
    assert _input_ids(expanded) == [["human-a"], ["human-b"]]


def test_a_message_sent_again_is_pooled_once() -> None:
    hello = ChatMessageUser(content="hello", id="hello")
    events: list[Event] = [
        _call("a", [hello]),
        _call("b", [hello, ChatMessageUser(content="more", id="more")]),
        _call("c", [ChatMessageUser(content="hello", id="hello")]),
    ]

    condensed, data = condense_events(events)

    assert [m.id for m in data["messages"]] == ["hello", "more"]
    assert _input_ids(expand_events(condensed, data)) == [
        ["hello"],
        ["hello", "more"],
        ["hello"],
    ]
