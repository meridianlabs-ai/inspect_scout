"""Resumes on different machines agree on recorded results and errors.

Each machine has its own local buffer; the scan location is shared.
"""

import secrets
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from inspect_ai._util.file import file, filesystem
from inspect_ai.model import ChatMessageUser
from inspect_scout import Result, scan_results_df
from inspect_scout._recorder import buffer as buffer_module
from inspect_scout._recorder.buffer import RecorderBuffer
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
                input_ids=[transcript_id],
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


async def _start(
    machines: _Machines, tmp_path: Path, machine: str = "A", scans: str = "scans"
) -> FileRecorder:
    machines.use(machine)
    recorder = FileRecorder()
    await recorder.init(
        ScanSpec(scan_name="reconcile", scanners={SCANNER: ScannerSpec(name="test")}),
        str(tmp_path / scans),
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


async def _record_error(recorder: FileRecorder, transcript_id: str, text: str) -> None:
    error = Error(
        transcript_id=transcript_id,
        scanner=SCANNER,
        error=text,
        traceback="",
        refusal=False,
    )
    report = ResultReport(
        input_type="message",
        input_ids=[transcript_id],
        input=ChatMessageUser(content=""),
        result=None,
        validation=None,
        error=error,
        events=[],
        model_usage={},
    )
    await recorder.record(_transcript(transcript_id), SCANNER, [report], None)


@pytest.mark.asyncio
async def test_retries_keep_only_each_transcripts_latest_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    machines = _Machines(tmp_path, monkeypatch)
    a = await _start(machines, tmp_path)
    location = await a.location()
    ids = [f"t{i}" for i in range(6)]
    for transcript_id in ids:
        await _record_error(a, transcript_id, "first")
    await FileRecorder.sync(location, complete=False)

    # enough retries that replaced errors are dropped part way through
    resumed = await machines.resume("A", location)
    for round in ("second", "third"):
        for transcript_id in ids[:4]:
            await _record_error(resumed, transcript_id, round)
    await _record(resumed, "t4", 1)
    expected = {"t0": "third", "t1": "third", "t2": "third", "t3": "third"}
    expected["t5"] = "first"

    for errors in (
        await resumed.errors(),
        (await FileRecorder.status(location)).errors,
        (await FileRecorder.sync(location, complete=False)).errors,
    ):
        assert {e.transcript_id: e.error for e in errors} == expected
        assert len(errors) == len(expected)


@pytest.mark.asyncio
@pytest.mark.parametrize("reader", ["sync", "attach"])
async def test_new_process_drops_errors_replaced_before_a_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reader: str
) -> None:
    machines = _Machines(tmp_path, monkeypatch)
    a = await _start(machines, tmp_path)
    location = await a.location()
    ids = [f"t{i}" for i in range(6)]
    for transcript_id in ids:
        await _record_error(a, transcript_id, "first")
    await FileRecorder.sync(location, complete=False)
    resumed = await machines.resume("A", location)
    await _record(resumed, "t0", 1)
    await _record_error(resumed, "t1", "second")
    error_file = RecorderBuffer.buffer_dir(location) / "_errors.jsonl"
    assert '"replaced": true' in error_file.read_text()

    # a new process knows nothing of what this one replaced
    monkeypatch.setattr(buffer_module, "_buffer_states", {})
    if reader == "sync":
        errors = (await FileRecorder.sync(location, complete=True)).errors
    else:
        attached = FileRecorder()
        await attached.attach(location)
        errors = await attached.errors()
    assert sorted((e.transcript_id, e.error) for e in errors) == [
        ("t1", "second"),
        *((transcript_id, "first") for transcript_id in ids[2:]),
    ]


@pytest.mark.asyncio
async def test_interrupted_retry_never_restores_the_error_it_replaced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    machines = _Machines(tmp_path, monkeypatch)
    a = await _start(machines, tmp_path)
    location = await a.location()
    await _record_error(a, "t1", "first")
    await FileRecorder.sync(location, complete=False)
    resumed = await machines.resume("A", location)
    await resumed.record(
        _transcript("t1"),
        SCANNER,
        [
            ResultReport(
                input_type="message",
                input_ids=["t1"],
                input=ChatMessageUser(content=""),
                result=None,
                validation=None,
                error=Error(
                    transcript_id="t1",
                    scanner=SCANNER,
                    error=text,
                    traceback="",
                    refusal=False,
                ),
                events=[],
                model_usage={},
            )
            for text in ("second-a", "second-b")
        ],
        None,
    )

    # the retry stopped part way through writing its new errors
    error_file = RecorderBuffer.buffer_dir(location) / "_errors.jsonl"
    error_file.write_text("".join(error_file.read_text().splitlines(True)[:-1]))
    monkeypatch.setattr(buffer_module, "_buffer_states", {})
    status = await FileRecorder.sync(location, complete=True)
    assert [e.error for e in status.errors] == ["second-a"]


@pytest.mark.asyncio
async def test_retry_stopped_before_its_errors_are_replaced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Results are written before errors; a stop in between must not mislead."""
    machines = _Machines(tmp_path, monkeypatch)
    a = await _start(machines, tmp_path)
    location = await a.location()
    await _record(a, "ok", 1)
    await _record(a, "f1", None)
    await FileRecorder.sync(location, complete=False)

    resumed = await machines.resume("A", location)

    def stop(*args: object) -> None:
        raise KeyboardInterrupt

    with monkeypatch.context() as m:
        m.setattr(RecorderBuffer, "_replace_errors", stop)
        with pytest.raises(KeyboardInterrupt):
            await _record(resumed, "f1", 1)

    for _ in range(2):
        resumed = await machines.resume("A", location)
        assert await resumed.is_recorded("f1", SCANNER)
        assert not await resumed.errors()
    status = await FileRecorder.sync(location, complete=True)
    assert not status.errors


@pytest.mark.asyncio
async def test_resume_reads_only_needed_columns_through_fsspec(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Results PyArrow can't read natively (memory://, az://) aren't read whole."""
    monkeypatch.setenv("SCOUT_SCANBUFFER_DIR", str(tmp_path / "buffer"))
    recorder = FileRecorder()
    await recorder.init(
        ScanSpec(scan_name="fsspec", scanners={SCANNER: ScannerSpec(name="test")}),
        "memory://scans",
    )
    location = await recorder.location()
    results = f"{location}/{SCANNER}.parquet"
    try:
        rows = 2_000
        table = pa.table(
            {
                "transcript_id": [f"t{i}" for i in range(rows)],
                "value": [str(float(i % 2)) for i in range(rows)],
                "value_type": ["number"] * rows,
                "scan_error": pa.nulls(rows, pa.string()),
                # a column resume never needs, holding nearly all the bytes
                "scan_events": [secrets.token_hex(1_000) for _ in range(rows)],
            }
        )
        with file(results, "wb") as f:
            pq.write_table(table, f, row_group_size=500, compression="none")
        size = filesystem(results).info(results).size
        with file(results, "rb") as f:
            memory_file = type(f)

        read = 0
        original = memory_file.read

        def counting_read(self: Any, n: int = -1) -> bytes:
            nonlocal read
            data = original(self, n)
            read += len(data)
            return data

        monkeypatch.setattr(memory_file, "read", counting_read)
        monkeypatch.setenv("SCOUT_SCANBUFFER_DIR", str(tmp_path / "fresh-buffer"))
        resumed = FileRecorder()
        await resumed.resume(location)
        assert await resumed.is_recorded("t1", SCANNER)
        values = [
            v
            async for v in resumed.recorded_values(
                SCANNER, [f"t{i}" for i in range(rows)]
            )
        ]
        assert values == [float(i % 2) for i in range(rows)]
        assert 0 < read < size / 10
    finally:
        filesystem(location).rm(location, recursive=True)
