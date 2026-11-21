"""Resumes on different machines agree on recorded results, errors and summary.

Each machine has its own local buffer; the scan location is shared.
"""

import json
import secrets
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from inspect_ai._util.file import file, filesystem
from inspect_ai.model import ChatMessageUser, ModelUsage
from inspect_scout import Result, scan_results_df
from inspect_scout._recorder.buffer import RecorderBuffer
from inspect_scout._recorder.file import FileRecorder
from inspect_scout._recorder.recorder import Status
from inspect_scout._recorder.summary import ScannerSummary
from inspect_scout._scanner.result import Error, ResultReport, ResultValidation
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
    """Record a success with `value`, or an error when `value` is None.

    Successes carry validation and model usage, so summaries count them too.
    """
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
                validation=None
                if value is None
                else ResultValidation(target=1, valid=value == 1),
                error=error,
                events=[],
                model_usage={}
                if value is None
                else {
                    "mockllm/model": ModelUsage(
                        input_tokens=2, output_tokens=1, total_tokens=3
                    )
                },
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


async def _clean_summary(
    machines: _Machines,
    tmp_path: Path,
    outcomes: dict[str, int | None],
    again: bool = False,
) -> dict[str, Any]:
    """Summary of recording `outcomes` once each, in a scan of their own."""
    name = "clean-again" if again else "clean"
    recorder = await _start(machines, tmp_path, machine=name, scans=name)
    for transcript_id, value in outcomes.items():
        await _record(recorder, transcript_id, value)
    return _normalized((await recorder.summary()).scanners[SCANNER])


def _normalized(summary: ScannerSummary) -> dict[str, Any]:
    """`summary` with validation entries in a stable order."""
    data = summary.model_dump()
    if data["validation"] is not None:
        data["validation"]["entries"].sort(key=lambda entry: str(entry["id"]))
    return data


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


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", ["fresh", "stale", "mixed"])
async def test_resumed_summary_matches_winning_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, scenario: str
) -> None:
    machines = _Machines(tmp_path, monkeypatch)
    a = await _start(machines, tmp_path)
    location = await a.location()
    await _record(a, "t1", None)
    await _record(a, "t2", None if scenario != "fresh" else 1)
    await FileRecorder.sync(location, complete=False)
    expected: dict[str, int | None] = {"t1": None, "t2": 1}

    if scenario != "fresh":
        if scenario == "mixed":
            await _record(a, "t3", 0)  # buffered on A, never synced
        b = await machines.resume("B", location)
        await _record(b, "t1", 1)
        await _record(b, "t2", 1)
        await FileRecorder.sync(location, complete=False)
        expected = {"t1": 1, "t2": 1}
        if scenario == "mixed":
            expected["t3"] = 0

    resumed = await machines.resume("A" if scenario != "fresh" else "B", location)
    summary = (await resumed.summary()).scanners[SCANNER]
    clean = await _clean_summary(machines, tmp_path, expected)
    assert _normalized(summary) == clean
    machines.use("A" if scenario != "fresh" else "B")
    status = await FileRecorder.sync(location, complete=False)
    assert _normalized(status.summary.scanners[SCANNER]) == clean
    synced = _synced_values(status)
    assert sorted(synced) == sorted(expected)
    assert all(len(values) == 1 for values in synced.values())

    # a successful retry replaces the failure in the summary
    for transcript_id in [t for t, v in expected.items() if v is None]:
        await _record(resumed, transcript_id, 1)
        expected[transcript_id] = 1
    clean = await _clean_summary(machines, tmp_path, expected, again=True)
    assert _normalized((await resumed.summary()).scanners[SCANNER]) == clean
    machines.use("A" if scenario != "fresh" else "B")
    status = await FileRecorder.sync(location, complete=True)
    assert not status.errors
    assert _normalized(status.summary.scanners[SCANNER]) == clean


@pytest.mark.asyncio
@pytest.mark.parametrize("retry", [1, None], ids=["succeeds", "fails"])
async def test_errors_follow_results_when_recording_stops_early(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, retry: int | None
) -> None:
    """Results are written before errors; a stop in between must not mislead."""
    machines = _Machines(tmp_path, monkeypatch)
    a = await _start(machines, tmp_path)
    location = await a.location()
    await _record(a, "ok", 1)
    if retry is not None:
        await _record(a, "f1", None)  # an earlier failure, now retried
    await FileRecorder.sync(location, complete=False)

    resumed = await machines.resume("A", location)

    def stop(*args: object) -> None:
        raise KeyboardInterrupt

    with monkeypatch.context() as m:
        m.setattr(RecorderBuffer, "_replace_errors", stop)
        with pytest.raises(KeyboardInterrupt):
            await _record(resumed, "f1", retry)

    for _ in range(2):
        resumed = await machines.resume("A", location)
        assert await resumed.is_recorded("f1", SCANNER) == (retry is not None)
        assert _failed(await resumed.errors()) == ([] if retry else ["f1"])
    status = await FileRecorder.sync(location, complete=retry is not None)
    assert _failed(status.errors) == ([] if retry else ["f1"])


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
        assert (await resumed.summary()).scanners[SCANNER].scans == rows
        assert 0 < read < size / 10
    finally:
        filesystem(location).rm(location, recursive=True)


def _write_synced(location: str, rows: list[dict[str, Any]]) -> None:
    """Write `rows` as the scanner's synced results (e.g. an older layout)."""
    pq.write_table(pa.Table.from_pylist(rows), f"{location}/{SCANNER}.parquet")


def _write_synced_errors(location: str, errors: list[Error]) -> None:
    Path(location, "_errors.jsonl").write_text(
        "".join(e.model_dump_json() + "\n" for e in errors)
    )


def _row(transcript_id: str, **columns: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "transcript_id": transcript_id,
        "input_ids": json.dumps([transcript_id]),
        "value": None,
        "value_type": "null",
        "scan_error": None,
        "scan_error_traceback": None,
        "scan_total_tokens": 0,
        "scan_model_usage": "{}",
    }
    return row | columns


@pytest.mark.asyncio
@pytest.mark.parametrize("targets", [(True, False), ("yes", "no")], ids=["bool", "str"])
async def test_resume_reads_older_result_layouts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, targets: tuple[Any, Any]
) -> None:
    """Before 0.3.0: refusal as a bool column; before 0.3.41: native validation."""
    machines = _Machines(tmp_path, monkeypatch)
    location = await (await _start(machines, tmp_path)).location()
    _write_synced(
        location,
        [
            _row(
                "ok",
                value="1",
                value_type="number",
                validation_target=targets[0],
                validation_result=True,
                scan_error_refusal=None,
            ),
            _row(
                "zero",
                value="0",
                value_type="number",
                validation_target=targets[1],
                validation_result=False,
                scan_error_refusal=None,
            ),
            _row(
                "failed",
                scan_error="boom",
                scan_error_traceback="tb",
                scan_error_refusal=False,
            ),
            _row(
                "refused",
                scan_error="no",
                scan_error_traceback="tb",
                scan_error_refusal=True,
            ),
        ],
    )
    resumed = await machines.resume("B", location)
    assert await resumed.is_recorded("ok", SCANNER)
    assert not await resumed.is_recorded("failed", SCANNER)
    assert {e.transcript_id: e.refusal for e in await resumed.errors()} == {
        "failed": False,
        "refused": True,
    }
    summary = (await resumed.summary()).scanners[SCANNER]
    assert (summary.scans, summary.results, summary.errors) == (4, 1, 2)
    assert summary.validation is not None
    assert sorted(
        (str(e.id), e.target, e.valid) for e in summary.validation.entries
    ) == [("ok", targets[0], True), ("zero", targets[1], False)]
    assert [v async for v in resumed.recorded_values(SCANNER, ["ok", "zero"])] == [
        1,
        0,
    ]

    # compacting the older layout with new results keeps every transcript once
    await _record(resumed, "failed", 1)
    status = await FileRecorder.sync(location, complete=False)
    assert sorted(_synced_values(status)) == ["failed", "ok", "refused", "zero"]


@pytest.mark.asyncio
async def test_refusal_comes_from_the_matching_recorded_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """0.3.0-0.5.1 rows marked every error a refusal; the errors file didn't."""
    machines = _Machines(tmp_path, monkeypatch)
    location = await (await _start(machines, tmp_path)).location()
    _write_synced(
        location,
        [
            _row(
                t,
                scan_error=f"{t} failed",
                scan_error_traceback="tb",
                scan_error_type="refusal",
            )
            for t in ("matched", "stale", "unlisted")
        ],
    )
    _write_synced_errors(
        location,
        [
            Error(
                transcript_id="matched",
                scanner=SCANNER,
                error="matched failed",
                traceback="tb",
                refusal=False,
            ),
            # an older error for this transcript, not the one in its results
            Error(
                transcript_id="stale",
                scanner=SCANNER,
                error="earlier failure",
                traceback="tb",
                refusal=False,
            ),
        ],
    )
    resumed = await machines.resume("B", location)
    assert {e.transcript_id: (e.error, e.refusal) for e in await resumed.errors()} == {
        "matched": ("matched failed", False),
        "stale": ("stale failed", True),
        "unlisted": ("unlisted failed", True),
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("layout", ["current", "older"])
async def test_unscored_result_with_error_survives_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, layout: str
) -> None:
    """A `None` result whose transcript couldn't be read back is still unscored."""
    machines = _Machines(tmp_path, monkeypatch)
    a = await _start(machines, tmp_path)
    location = await a.location()
    await a.record(
        _transcript("t1"),
        SCANNER,
        [
            ResultReport(
                input_type="message",
                input_ids=["t1"],
                input=ChatMessageUser(content=""),
                result=Result(value=None),
                validation=None,
                error=Error(
                    transcript_id="t1",
                    scanner=SCANNER,
                    error="unreadable",
                    traceback="",
                    refusal=False,
                ),
                events=[],
                model_usage={},
            )
        ],
        None,
    )
    recorded = (await a.summary()).scanners[SCANNER]
    assert (recorded.unscored, recorded.errors) == (1, 1)
    await FileRecorder.sync(location, complete=False)
    if layout == "older":
        # files written before `scan_error_has_result` lack the column
        table = pq.read_table(f"{location}/{SCANNER}.parquet")
        _write_synced(location, table.drop(["scan_error_has_result"]).to_pylist())

    resumed = await machines.resume("B", location)
    summary = (await resumed.summary()).scanners[SCANNER]
    # an older row can't tell this from an error without a result
    assert (summary.unscored, summary.errors) == (
        (1, 1) if layout == "current" else (0, 1)
    )


@pytest.mark.asyncio
async def test_resumed_summary_is_incomplete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    machines = _Machines(tmp_path, monkeypatch)
    a = await _start(machines, tmp_path)
    location = await a.location()
    await _record(a, "t1", None)
    await FileRecorder.sync(location, complete=False)

    resumed = await machines.resume("B", location)
    assert not (await resumed.summary()).complete
    status = await FileRecorder.status(location)
    assert not status.complete and not status.summary.complete


_A = "model_a"
_B = "model_b"


def _usage(cost: float | None = None, reasoning: int | None = None) -> ModelUsage:
    return ModelUsage(
        input_tokens=2,
        output_tokens=1,
        total_tokens=3,
        reasoning_tokens=reasoning,
        total_cost=cost,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "attempts",
    [
        # failures cost 0.1 and 0.2 on model_a; the retries run on model_b
        {
            "ok": [(_B, _usage())],
            "f1": [(_A, _usage(cost=0.1)), (_B, _usage())],
            "f2": [(_A, _usage(cost=0.2)), (_B, _usage())],
        },
        # only the failure set reasoning tokens and cost on model_a
        {
            "ok": [(_A, _usage())],
            "f1": [(_A, _usage(cost=0.1, reasoning=5)), (_A, _usage())],
        },
    ],
    ids=["dropped", "none"],
)
async def test_retry_replaces_failed_model_usage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    attempts: dict[str, list[tuple[str, ModelUsage]]],
) -> None:
    async def record(
        recorder: FileRecorder,
        transcript_id: str,
        model: str,
        usage: ModelUsage,
        failed: bool,
    ) -> None:
        await recorder.record(
            _transcript(transcript_id),
            SCANNER,
            [
                ResultReport(
                    input_type="message",
                    input_ids=[transcript_id],
                    input=ChatMessageUser(content=""),
                    result=None if failed else Result(value=1),
                    validation=None,
                    error=Error(
                        transcript_id=transcript_id,
                        scanner=SCANNER,
                        error="failed",
                        traceback="",
                        refusal=False,
                    )
                    if failed
                    else None,
                    events=[],
                    model_usage={model: usage},
                )
            ],
            None,
        )

    machines = _Machines(tmp_path, monkeypatch)
    a = await _start(machines, tmp_path)
    location = await a.location()
    for transcript_id, tries in attempts.items():
        model, usage = tries[0]
        await record(a, transcript_id, model, usage, failed=len(tries) > 1)
    await FileRecorder.sync(location, complete=False)

    resumed = await machines.resume("B", location)
    for transcript_id, tries in attempts.items():
        if len(tries) > 1:
            model, usage = tries[-1]
            await record(resumed, transcript_id, model, usage, failed=False)

    clean = await _start(machines, tmp_path, machine="clean", scans="clean")
    for transcript_id, tries in attempts.items():
        model, usage = tries[-1]
        await record(clean, transcript_id, model, usage, failed=False)
    expected = (await clean.summary()).scanners[SCANNER]
    assert (await resumed.summary()).scanners[SCANNER] == expected
    machines.use("B")
    status = await FileRecorder.sync(location, complete=True)
    assert status.summary.scanners[SCANNER] == expected
