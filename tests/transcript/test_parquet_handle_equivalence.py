"""Equivalence: streamed handle vs materialized read() on a temp parquet DB."""

from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio
from inspect_ai.event._event import Event
from inspect_ai.model._chat_message import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageUser,
)
from inspect_ai.tool._tool_call import ToolCall
from inspect_scout._transcript.database.parquet import ParquetTranscriptsDB
from inspect_scout._transcript.handle import (
    MaterializedTranscriptHandle,
    SpooledTranscriptHandle,
)
from inspect_scout._transcript.types import Transcript, TranscriptContent
from inspect_scout._util import constants as constants_mod


def _events_for(messages: list[ChatMessage]) -> list[Event]:
    from inspect_ai.event import ModelEvent
    from inspect_ai.model._generate_config import GenerateConfig
    from inspect_ai.model._model_output import ModelOutput

    return [
        ModelEvent(
            model="mockllm/model",
            input=messages,
            tools=[],
            tool_choice="auto",
            config=GenerateConfig(),
            output=ModelOutput.from_content("mockllm/model", content="done"),
        )
    ]


def _sample_transcript(id: str, *, with_events: bool = False) -> Transcript:
    messages: list[ChatMessage] = [
        ChatMessageUser(content=f"Question for {id}"),
        ChatMessageAssistant(
            content=f"Answer for {id}",
            tool_calls=[
                ToolCall(
                    id=f"call-{id}",
                    function="do_thing",
                    arguments={"x": 1},
                )
            ]
            if with_events
            else None,
        ),
    ]
    events = _events_for(messages) if with_events else []
    return Transcript(
        transcript_id=id,
        source_type="test",
        source_id=f"source-{id}",
        source_uri=f"test://{id}.json",
        metadata={"idx": id},
        messages=messages,
        events=events,
    )


CONTENTS = [
    TranscriptContent(messages="all", events=None),
    TranscriptContent(messages=None, events="all"),
    TranscriptContent(messages="all", events="all"),
]
CONTENT_IDS = ["messages-only", "events-only", "messages-and-events"]


@pytest_asyncio.fixture
async def parquet_db(tmp_path: Path) -> ParquetTranscriptsDB:
    """A connected ParquetTranscriptsDB with a couple of transcripts inserted.

    One transcript has events (with tool calls, exercising pool_dedup /
    events_data), one has messages only.
    """
    location = tmp_path / "transcripts_db"
    location.mkdir(parents=True, exist_ok=True)
    db = ParquetTranscriptsDB(str(location))
    await db.connect()
    await db.insert(
        [
            _sample_transcript("t-plain", with_events=False),
            _sample_transcript("t-with-events", with_events=True),
        ]
    )
    return db


@pytest.mark.asyncio
@pytest.mark.parametrize("content", CONTENTS, ids=CONTENT_IDS)
@pytest.mark.parametrize("transcript_id", ["t-plain", "t-with-events"])
async def test_streamed_equals_materialized(
    parquet_db: ParquetTranscriptsDB,
    content: TranscriptContent,
    transcript_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Force the spooled path regardless of content size.
    monkeypatch.setattr(constants_mod, "SPOOL_THRESHOLD_BYTES", 0)
    try:
        infos = {i.transcript_id: i async for i in parquet_db.select()}
        info = infos[transcript_id]

        materialized = await parquet_db.read(info, content)
        async with await parquet_db.open(info, content) as h:
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
        assert [m.model_dump() for m in loaded.messages] == [
            m.model_dump() for m in materialized.messages
        ]
        assert [e.model_dump() for e in loaded.events] == [
            e.model_dump() for e in materialized.events
        ]
    finally:
        await parquet_db.disconnect()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "force_zero_threshold,content,transcript_id",
    [
        pytest.param(
            # Default threshold (64MB) >> tiny fixture content.
            False,
            TranscriptContent(messages="all", events="all"),
            "t-with-events",
            id="small-content",
        ),
        pytest.param(
            # Even with threshold forced to 0, a timeline request isn't
            # messages/events-only content, so it must use the materialized path.
            True,
            TranscriptContent(messages="all", events="all", timeline="all"),
            "t-with-events",
            id="timeline-request",
        ),
        pytest.param(
            True,
            TranscriptContent(messages="all", events=None),
            "does-not-exist",
            id="unknown-transcript",
        ),
    ],
)
async def test_routing_to_materialized_handle(
    parquet_db: ParquetTranscriptsDB,
    force_zero_threshold: bool,
    content: TranscriptContent,
    transcript_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from inspect_scout._transcript.types import TranscriptInfo

    if force_zero_threshold:
        monkeypatch.setattr(constants_mod, "SPOOL_THRESHOLD_BYTES", 0)
    try:
        known = {i.transcript_id: i async for i in parquet_db.select()}
        info = known.get(transcript_id) or TranscriptInfo(
            transcript_id=transcript_id,
            source_type="test",
            source_id="source-x",
            source_uri="test://missing.json",
            metadata={},
        )
        cm = await parquet_db.open(info, content)
        async with cm as h:
            assert isinstance(h, MaterializedTranscriptHandle)
            if transcript_id not in known:
                loaded = await h.load()
                assert loaded.messages == []
    finally:
        await parquet_db.disconnect()
