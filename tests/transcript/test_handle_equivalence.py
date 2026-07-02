"""Equivalence: streamed handle vs materialized read() on real eval logs."""

from __future__ import annotations

from pathlib import Path

import pytest
from inspect_scout._transcript.eval_log import EvalLogTranscriptsView
from inspect_scout._transcript.types import TranscriptContent
from inspect_scout._util import constants as constants_mod

LOGS_DIR = Path(__file__).parent.parent / "recorder" / "logs"
LOGS = sorted(LOGS_DIR.glob("*.eval"))

CONTENTS = [
    TranscriptContent(messages="all", events=None),
    TranscriptContent(messages=["assistant"], events=None),
    TranscriptContent(messages="all", events="all"),
    TranscriptContent(messages=None, events=["model"]),
]


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
    monkeypatch.setattr(constants_mod, "STREAMING_THRESHOLD_BYTES", 0)
    view = EvalLogTranscriptsView(str(log))
    await view.connect()
    try:
        infos = [i async for i in view.select()]
        assert infos
        info = infos[0]
        materialized = await view.read(info, content)
        async with await view.open(info, content) as h:
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
async def test_small_file_uses_materialized_handle() -> None:
    # default threshold (64MB) >> fixture size -> MaterializedTranscriptHandle
    from inspect_scout._transcript.handle import MaterializedTranscriptHandle

    view = EvalLogTranscriptsView(str(LOGS[0]))
    await view.connect()
    try:
        infos = [i async for i in view.select()]
        cm = await view.open(infos[0], TranscriptContent(messages="all", events=None))
        async with cm as h:
            assert isinstance(h, MaterializedTranscriptHandle)
    finally:
        await view.disconnect()


# None of the fixture logs in tests/recorder/logs/ contain an `events_data`
# pool (verified: all four only have the legacy top-level `attachments`
# dict with no `message_pool`/`call_pool`/`events_data` keys). Pool
# resolution during streaming replay (attachment refs inside pool items,
# range-encoded refs, and the consolidated `events_data` schema) is already
# covered at the `stream_parse_to_spool`/`replay_*` level by Task 3's tests
# (tests/transcript/test_stream_parse.py). We do not duplicate that here.
