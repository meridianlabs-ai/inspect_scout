"""Completed loader items survive interruption before the loader finishes (#662)."""

import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path

import anyio
import pyarrow.parquet as pq
import pytest
from inspect_ai._util.error import PrerequisiteError
from inspect_ai.model import ChatMessage, ChatMessageUser
from inspect_scout import (
    Loader,
    Result,
    Scanner,
    loader,
    scan,
    scan_resume,
    scanner,
    transcripts_db,
)
from inspect_scout._scanresults import scan_results_df
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.types import Transcript


@loader(messages="all")
def checkpoint_loader() -> Loader[ChatMessage]:
    async def load(transcript: Transcript) -> AsyncIterator[ChatMessage]:
        skip_file = transcript.metadata.get("skip_file")
        if isinstance(skip_file, str) and Path(skip_file).exists():
            return
        for message in transcript.messages:
            yield message

    return load


@scanner(loader=checkpoint_loader())
def checkpoint_scanner(continue_file: str) -> Scanner[ChatMessage]:
    async def scan_message(message: ChatMessage) -> Result:
        if message.text == "second" and not Path(continue_file).exists():
            raise PrerequisiteError("interrupt after the first completed item")
        return Result(value=message.text)

    return scan_message


@scanner(messages="all")
def visible_checkpoint_scanner(scans: str) -> Scanner[ChatMessage]:
    async def scan_message(message: ChatMessage) -> Result:
        visible = 0
        if message.text == "second":
            with anyio.fail_after(15):
                while not visible:
                    for parquet in Path(scans).glob("scan_id=*/checkpoint.parquet"):
                        visible = pq.read_table(parquet).num_rows
                    if not visible:
                        await anyio.sleep(0.01)
        return Result(value=message.text, metadata={"visible": visible})

    return scan_message


async def _insert_transcripts(db_path: Path, skip_file: Path | None = None) -> None:
    async with transcripts_db(str(db_path)) as db:
        await db.insert(
            [
                Transcript(
                    transcript_id=f"checkpoint-{i}",
                    metadata={"skip_file": str(skip_file)} if skip_file else {},
                    messages=[
                        ChatMessageUser(content=text, id=f"message-{i}-{text}")
                        for text in ["first", "second"]
                    ],
                )
                for i in range(2)
            ]
        )


@pytest.mark.parametrize("max_processes", [1, 2])
@pytest.mark.parametrize("skip_on_resume", [False, True])
def test_loader_results_survive_interruption_and_resume(
    tmp_path: Path, max_processes: int, skip_on_resume: bool
) -> None:
    db_path = tmp_path / "db"
    continue_file = tmp_path / "continue"
    asyncio.run(_insert_transcripts(db_path, continue_file if skip_on_resume else None))
    status = scan(
        scanners={"checkpoint": checkpoint_scanner(str(continue_file))},
        transcripts=transcripts_from(str(db_path)),
        scans=str(tmp_path / "scans"),
        max_processes=max_processes,
        max_transcripts=1,
        display="none",
    )
    assert not status.complete
    assert status.location is not None
    partial = scan_results_df(status.location).scanners
    assert "checkpoint" in partial, "completed loader items were lost"
    assert partial["checkpoint"]["value"].tolist()
    assert set(partial["checkpoint"]["value"]) == {"first"}
    assert status.summary.scanners["checkpoint"].scans == 0

    continue_file.touch()
    resumed = scan_resume(status.location, display="none")
    assert resumed.complete
    results = scan_results_df(status.location).scanners["checkpoint"]
    if skip_on_resume:
        assert results.empty, "empty retry left earlier partial results visible"
    else:
        assert len(results) == 4
        assert sorted(json.loads(ids)[0] for ids in results["input_ids"]) == sorted(
            f"message-{i}-{text}" for i in range(2) for text in ["first", "second"]
        )
    assert resumed.summary.scanners["checkpoint"].scans == 2


@pytest.mark.parametrize("max_processes", [1, 2])
def test_results_buffer_syncs_before_loader_completion(
    tmp_path: Path, max_processes: int
) -> None:
    """A loader's next item can see a prior item's periodically synced result."""
    db_path = tmp_path / "db"
    scans = tmp_path / "scans"
    asyncio.run(_insert_transcripts(db_path))
    status = scan(
        scanners={"checkpoint": visible_checkpoint_scanner(str(scans))},
        transcripts=transcripts_from(str(db_path)),
        scans=str(scans),
        max_processes=max_processes,
        max_transcripts=1,
        results_buffer=1,
        display="none",
    )
    assert status.complete
    assert status.location is not None
    results = scan_results_df(status.location).scanners["checkpoint"]
    assert len(results) == 4
    for _, row in results.iterrows():
        if row["value"] == "second":
            assert json.loads(row["metadata"])["visible"] > 0
    assert status.summary.scanners["checkpoint"].scans == 2
