"""Resumes on different machines agree on recorded results and outstanding errors.

Each machine has its own local buffer; the scan location is shared.
"""

from pathlib import Path

import pytest
from inspect_ai.model import ChatMessageUser
from inspect_scout import Result, scan_results_df
from inspect_scout._recorder.file import FileRecorder
from inspect_scout._recorder.recorder import Status
from inspect_scout._scanner.result import Error, ResultReport
from inspect_scout._scanspec import ScannerSpec, ScanSpec
from inspect_scout._transcript.types import TranscriptInfo

SCANNER = "test"


def _transcript(transcript_id: str) -> TranscriptInfo:
    return TranscriptInfo(
        transcript_id=transcript_id,
        source_type="test",
        source_id="src",
        source_uri=f"test://{transcript_id}",
    )


async def _record(
    recorder: FileRecorder, transcript_id: str, value: int | None
) -> None:
    """Record a success with `value`, or an error when `value` is None."""
    error = (
        Error(
            transcript_id=transcript_id,
            scanner=SCANNER,
            error=f"{transcript_id} failed",
            traceback="",
            refusal=False,
        )
        if value is None
        else None
    )
    await recorder.record(
        _transcript(transcript_id),
        SCANNER,
        [
            ResultReport(
                input_type="message",
                input_ids=[],
                input=ChatMessageUser(content=""),
                result=None if value is None else Result(value=value),
                validation=None,
                error=error,
                events=[],
                model_usage={},
            )
        ],
        None,
    )


class _Machines:
    def __init__(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._tmp_path = tmp_path
        self._monkeypatch = monkeypatch

    def use(self, machine: str) -> None:
        self._monkeypatch.setenv(
            "SCOUT_SCANBUFFER_DIR", str(self._tmp_path / f"machine-{machine}")
        )

    async def resume(self, machine: str, location: str) -> FileRecorder:
        self.use(machine)
        recorder = FileRecorder()
        await recorder.resume(location)
        return recorder


async def _start(machines: _Machines, tmp_path: Path) -> FileRecorder:
    machines.use("A")
    recorder = FileRecorder()
    await recorder.init(
        ScanSpec(scan_name="reconcile", scanners={SCANNER: ScannerSpec(name="test")}),
        str(tmp_path / "scans"),
    )
    return recorder


def _synced_values(status: Status) -> dict[str, list[object]]:
    df = scan_results_df(status.location).scanners[SCANNER]
    values: dict[str, list[object]] = {}
    for transcript_id, value in zip(df["transcript_id"], df["value"], strict=True):
        values.setdefault(transcript_id, []).append(value)
    return values


def _failed(errors: list[Error]) -> list[str]:
    return sorted(e.transcript_id for e in errors)


@pytest.mark.asyncio
async def test_synced_success_replaces_stale_buffered_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    machines = _Machines(tmp_path, monkeypatch)
    a = await _start(machines, tmp_path)
    location = await a.location()
    await _record(a, "t1", None)
    await FileRecorder.sync(location, complete=False)

    b = await machines.resume("B", location)
    assert not await b.is_recorded("t1", SCANNER)
    await _record(b, "t1", 1)
    await FileRecorder.sync(location, complete=False)

    # A's buffer still holds its error for t1
    a = await machines.resume("A", location)
    assert await a.is_recorded("t1", SCANNER)
    assert not await a.errors()
    status = await FileRecorder.sync(location, complete=False)
    assert _synced_values(status) == {"t1": [1]}
    assert not status.errors


@pytest.mark.asyncio
@pytest.mark.parametrize("machine", ["A", "B"], ids=["same", "fresh"])
async def test_outstanding_errors_survive_partial_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, machine: str
) -> None:
    machines = _Machines(tmp_path, monkeypatch)
    a = await _start(machines, tmp_path)
    location = await a.location()
    await _record(a, "f1", None)
    await _record(a, "f2", None)
    await _record(a, "ok", 1)
    status = await FileRecorder.sync(location, complete=False)
    assert _failed(status.errors) == ["f1", "f2"]

    # retry only f1, then stop (an interrupted resume)
    resumed = await machines.resume(machine, location)
    assert _failed(await resumed.errors()) == ["f1", "f2"]
    await _record(resumed, "f1", 1)
    assert _failed(await resumed.errors()) == ["f2"]
    status = await FileRecorder.sync(location, complete=False)
    assert _failed(status.errors) == ["f2"]

    # resume again, on this machine and on another one
    for again in (machine, "C"):
        resumed = await machines.resume(again, location)
        assert _failed(await resumed.errors()) == ["f2"]
        assert await resumed.is_recorded("f1", SCANNER)
        assert not await resumed.is_recorded("f2", SCANNER)
        status = await FileRecorder.sync(location, complete=False)
        assert _failed(status.errors) == ["f2"]

    # a failed retry replaces f2's error rather than adding to it
    await _record(resumed, "f2", None)
    assert _failed(await resumed.errors()) == ["f2"]
    await _record(resumed, "f2", 2)
    status = await FileRecorder.sync(location, complete=True)
    assert not status.errors
    assert _synced_values(status) == {"f1": [1], "f2": [2], "ok": [1]}
