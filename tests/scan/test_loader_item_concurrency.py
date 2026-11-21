"""Loader items of one transcript scan in parallel, as units of the worker pool.

Concurrency is proven with barriers (an item waits until a given number of
items are in flight), not with wall-clock limits. Every wait is bounded by
`_TIMEOUT`, so a barrier that cannot open fails the test and does not hang it.
"""

import asyncio
import json
import os
from collections import defaultdict
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from typing import Any, cast

import anyio
import pandas as pd
import pytest
from inspect_ai._util.error import PrerequisiteError
from inspect_ai.model import ChatMessageUser, GenerateConfig, get_model
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
from inspect_scout._concurrency.common import (
    ParseFunctionResult,
    ParseJob,
    ScannerJob,
)
from inspect_scout._concurrency.single_process import single_process_strategy
from inspect_scout._scan import _scan_one
from inspect_scout._scanner.result import ResultReport
from inspect_scout._scanresults import scan_results_df
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.transcripts import TranscriptsReader
from inspect_scout._transcript.types import Transcript, TranscriptInfo

from tests.helpers import temp_active_scans_store

_TIMEOUT = 20
_ITEMS = 8


@dataclass
class _Items:
    """What one transcript's items did."""

    in_flight: int = 0
    max_in_flight: int = 0
    log: list[tuple[str, int]] = field(default_factory=list)

    def indices(self, event: str) -> list[int]:
        return [i for e, i in self.log if e == event]


@dataclass
class _Tracker:
    """Tracks items per transcript, in the scanner's process.

    Multi-process tests read what it saw through the scanner's result values.
    """

    items: defaultdict[str, _Items] = field(default_factory=lambda: defaultdict(_Items))
    loader_raised: bool = False
    _condition: anyio.Condition | None = None

    @property
    def condition(self) -> anyio.Condition:
        # Created on first use, inside the scanner process's event loop.
        if self._condition is None:
            self._condition = anyio.Condition()
        return self._condition

    async def changed(self, update: Callable[[], None]) -> None:
        async with self.condition:
            update()
            self.condition.notify_all()

    async def wait_until(self, predicate: Callable[[], bool]) -> None:
        with anyio.fail_after(_TIMEOUT):
            async with self.condition:
                while not predicate():
                    await self.condition.wait()

    async def enter(self, key: str, index: int) -> None:
        def update() -> None:
            items = self.items[key]
            items.in_flight += 1
            items.max_in_flight = max(items.max_in_flight, items.in_flight)
            items.log.append(("start", index))

        await self.changed(update)

    async def exit(self, key: str, index: int) -> None:
        def update() -> None:
            items = self.items[key]
            items.in_flight -= 1
            items.log.append(("end", index))

        await self.changed(update)


ItemWait = Callable[[_Tracker, str, int], Awaitable[None]]


def _parse(message: ChatMessageUser) -> tuple[str, int]:
    """Messages are named '<transcript id>-<item index>'."""
    key, index = message.text.rsplit("-", 1)
    return key, int(index)


async def _no_wait(tracker: _Tracker, key: str, index: int) -> None:
    await anyio.lowlevel.checkpoint()


def _wait_for_in_flight(count: int) -> ItemWait:
    """Hold each item until `count` items of its transcript are in flight."""

    async def wait(tracker: _Tracker, key: str, index: int) -> None:
        items = tracker.items[key]
        await tracker.wait_until(lambda: items.in_flight >= count)

    return wait


async def _finish_in_reverse(tracker: _Tracker, key: str, index: int) -> None:
    """Hold each item until all items started and every later item finished."""
    items = tracker.items[key]
    await tracker.wait_until(
        lambda: (
            len(items.indices("start")) == _ITEMS
            and set(range(index + 1, _ITEMS)) <= set(items.indices("end"))
        )
    )


def _tracked_scan(
    tracker: _Tracker,
    wait: ItemWait,
    raise_on: dict[int, BaseException] | None,
    generate: bool,
) -> Scanner[ChatMessageUser]:
    """Record entry and exit, and wait as told.

    The value is the max in flight seen, or with `generate`, the item's text
    and the model's reply (the same whatever ran alongside it). The metadata
    holds the scanner's process id.
    """

    async def scan_message(message: ChatMessageUser) -> Result:
        key, index = _parse(message)
        await tracker.enter(key, index)
        await wait(tracker, key, index)
        if raise_on and index in raise_on:
            raise raise_on[index]
        value = (
            f"{message.text}: {(await get_model().generate([message])).completion}"
            if generate
            else tracker.items[key].max_in_flight
        )
        await tracker.exit(key, index)
        return Result(
            value=value, explanation=str(index), metadata={"pid": os.getpid()}
        )

    return scan_message


@scanner(name="tracked", messages=["user"])
def _tracked_scanner(
    tracker: _Tracker,
    wait: ItemWait = _no_wait,
    raise_on: dict[int, BaseException] | None = None,
) -> Scanner[ChatMessageUser]:
    """Typed on one message, so the implicit loader yields one item per message."""
    return _tracked_scan(tracker, wait, raise_on, generate=False)


@loader(name="message_loader", messages=["user"])
def _message_loader() -> Loader[ChatMessageUser]:
    async def load(transcript: Transcript) -> AsyncIterator[ChatMessageUser]:
        for message in transcript.messages:
            assert isinstance(message, ChatMessageUser)
            yield message

    return load


@scanner(name="tracked_custom_loader", loader=_message_loader())
def _tracked_custom_loader_scanner(
    tracker: _Tracker, wait: ItemWait = _no_wait
) -> Scanner[ChatMessageUser]:
    return _tracked_scan(tracker, wait, None, generate=False)


@loader(name="generating_loader", messages=["user"])
def _generating_loader() -> Loader[ChatMessageUser]:
    """Make one model call before yielding each message."""

    async def load(transcript: Transcript) -> AsyncIterator[ChatMessageUser]:
        for message in transcript.messages:
            assert isinstance(message, ChatMessageUser)
            await get_model().generate([message])
            yield message

    return load


@scanner(name="tracked_generating", loader=_generating_loader())
def _tracked_generating_scanner(
    tracker: _Tracker, wait: ItemWait = _no_wait
) -> Scanner[ChatMessageUser]:
    """Like `tracked`, plus one model call in the loader and one in the scan."""
    return _tracked_scan(tracker, wait, None, generate=True)


def _transcript(key: str, items: int = _ITEMS) -> Transcript:
    return Transcript(
        transcript_id=key,
        source_type="test",
        source_id="source-0",
        source_uri=f"test://{key}",
        messages=[
            ChatMessageUser(id=f"{key}-{i}", content=f"{key}-{i}") for i in range(items)
        ],
        events=[],
    )


def _insert(db_path: Path, transcripts: list[Transcript]) -> None:
    async def insert() -> None:
        async with transcripts_db(str(db_path)) as db:
            await db.insert(transcripts)

    db_path.mkdir(parents=True)
    asyncio.run(insert())


def _scan_df(
    tmp_path: Path,
    scanner: Scanner[Any],
    keys: list[str],
    *,
    max_transcripts: int | None = None,
    max_processes: int = 1,
    expect_errors: bool = False,
) -> pd.DataFrame:
    db_path = tmp_path / "transcripts"
    _insert(db_path, [_transcript(key) for key in keys])
    status = scan(
        scanners={"s": scanner},
        transcripts=transcripts_from(str(db_path)),
        scans=str(tmp_path / "scans"),
        model="mockllm/model",
        max_transcripts=max_transcripts,
        max_processes=max_processes,
        display="none",
    )
    assert status.complete != expect_errors
    assert status.location is not None
    df = scan_results_df(status.location, scanner="s", exclude_columns=[]).scanners["s"]
    if not expect_errors:
        assert df["scan_error"].isna().all()
    return df


def _indices(df: pd.DataFrame) -> list[int]:
    return sorted(int(e) for e in df["explanation"].dropna())


# Items in parallel


@pytest.mark.parametrize("scanner_factory", ["message_typed", "custom_loader"])
def test_items_of_one_transcript_scan_in_parallel(
    tmp_path: Path, scanner_factory: str
) -> None:
    """One transcript and one scanner use the whole worker pool.

    A scanner typed on one `ChatMessage` scans its messages in parallel, as
    does a scanner with a custom loader.
    """
    tracker = _Tracker()
    wait = _wait_for_in_flight(_ITEMS)
    df = _scan_df(
        tmp_path,
        _tracked_scanner(tracker, wait)
        if scanner_factory == "message_typed"
        else _tracked_custom_loader_scanner(tracker, wait),
        ["t"],
    )
    assert tracker.items["t"].max_in_flight == _ITEMS
    assert _indices(df) == list(range(_ITEMS))


def test_items_in_flight_limited_by_max_transcripts(tmp_path: Path) -> None:
    tracker = _Tracker()
    df = _scan_df(tmp_path, _tracked_scanner(tracker), ["t"], max_transcripts=3)
    assert tracker.items["t"].max_in_flight <= 3
    assert _indices(df) == list(range(_ITEMS))


def test_items_scan_in_parallel_in_each_process(tmp_path: Path) -> None:
    """A transcript's items scan in the process that read it.

    Two processes and two transcripts. Each process has 16 workers, so both
    barriers can open even if one process gets both transcripts.
    """
    df = _scan_df(
        tmp_path,
        _tracked_scanner(_Tracker(), _wait_for_in_flight(_ITEMS)),
        ["a", "b"],
        max_transcripts=32,
        max_processes=2,
    )
    assert len(df) == 2 * _ITEMS
    df["pid"] = [json.loads(m)["pid"] for m in df["metadata"]]
    peaks = df.groupby("transcript_id")["value"].max().to_dict()
    pids = df.groupby("transcript_id")["pid"].unique().to_dict()
    print(f"peak in flight per transcript: {peaks}, pids: {pids}")
    assert peaks == {"a": _ITEMS, "b": _ITEMS}
    # each transcript's items stay in one child process
    assert all(len(p) == 1 and p[0] != os.getpid() for p in pids.values())


# Errors


def test_item_error_is_an_error_row_and_other_items_go_on(tmp_path: Path) -> None:
    df = _scan_df(
        tmp_path,
        _tracked_scanner(_Tracker(), raise_on={3: ValueError("item 3")}),
        ["t"],
        expect_errors=True,
    )
    errors = df[df["scan_error"].notna()]
    assert len(df) == _ITEMS
    assert len(errors) == 1
    assert "item 3" in errors["scan_error"].iloc[0]
    assert _indices(df) == [i for i in range(_ITEMS) if i != 3]


def test_fail_on_error_gives_an_interrupted_scan(tmp_path: Path) -> None:
    db_path = tmp_path / "transcripts"
    _insert(db_path, [_transcript("t")])
    status = scan(
        scanners={"s": _tracked_scanner(_Tracker(), raise_on={3: ValueError("x")})},
        transcripts=transcripts_from(str(db_path)),
        scans=str(tmp_path / "scans"),
        model="mockllm/model",
        fail_on_error=True,
        display="none",
    )
    assert not status.complete


def test_bare_cancelled_error_from_a_scanner_gives_an_interrupted_scan(
    tmp_path: Path,
) -> None:
    """A bare `CancelledError` from a scanner must not mark the scan complete."""
    db_path = tmp_path / "transcripts"
    _insert(db_path, [_transcript("t")])
    status = scan(
        scanners={
            "s": _tracked_scanner(_Tracker(), raise_on={3: asyncio.CancelledError()})
        },
        transcripts=transcripts_from(str(db_path)),
        scans=str(tmp_path / "scans"),
        model="mockllm/model",
        display="none",
    )
    assert not status.complete


@asynccontextmanager
async def _reader_cm() -> AsyncIterator[TranscriptsReader]:
    yield cast(TranscriptsReader, None)  # never dereferenced: parse is a stub


async def _run_strategy(scanner: Scanner[Any], *, fail_on_error: bool) -> None:
    """Run the real `_scan_one` items of one job through the strategy."""
    job = ScannerJob(
        union_transcript=_transcript("t"), scanner=scanner, scanner_name="s"
    )

    async def parse_jobs() -> AsyncIterator[ParseJob]:
        yield ParseJob(transcript_info=job.transcript_info, scanner_indices={0})

    async def parse_function(
        parse_job: ParseJob, reader: TranscriptsReader
    ) -> ParseFunctionResult:
        return True, job

    async def record_results(
        info: TranscriptInfo, scanner_name: str, results: list[ResultReport]
    ) -> None:
        pass

    with anyio.fail_after(_TIMEOUT):
        await single_process_strategy(task_count=_ITEMS)(
            parse_jobs=parse_jobs(),
            parse_function=parse_function,
            scan_function=partial(_scan_one, fail_on_error=fail_on_error),
            record_results=record_results,
            update_metrics=lambda _: None,
            reader_cm_factory=_reader_cm,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exception,fail_on_error",
    [(ValueError("item 3"), True), (PrerequisiteError("item 3"), False)],
)
async def test_item_failure_raises_bare_exception_from_strategy(
    exception: Exception, fail_on_error: bool
) -> None:
    tracker = _Tracker()
    with pytest.raises(type(exception)) as raised:
        await _run_strategy(
            _tracked_scanner(
                tracker, _wait_for_in_flight(_ITEMS), raise_on={3: exception}
            ),
            fail_on_error=fail_on_error,
        )
    assert raised.value is exception


def test_loader_error_keeps_earlier_rows_and_adds_one_error_row(
    tmp_path: Path,
) -> None:
    tracker = _Tracker()

    @loader(messages=["user"])
    def raises_after_4() -> Loader[ChatMessageUser]:
        async def load(transcript: Transcript) -> AsyncIterator[ChatMessageUser]:
            for message in transcript.messages[:4]:
                assert isinstance(message, ChatMessageUser)
                yield message
            await tracker.wait_until(lambda: tracker.items["t"].in_flight == 4)
            await tracker.changed(lambda: setattr(tracker, "loader_raised", True))
            raise RuntimeError("loader broke")

        return load

    @scanner(loader=raises_after_4())
    def finishes_after_loader_error() -> Scanner[ChatMessageUser]:
        async def wait(tracker: _Tracker, key: str, index: int) -> None:
            await tracker.wait_until(lambda: tracker.loader_raised)

        return _tracked_scan(tracker, wait, None, generate=False)

    df = _scan_df(tmp_path, finishes_after_loader_error(), ["t"], expect_errors=True)
    assert _indices(df) == [0, 1, 2, 3]
    errors = df[df["scan_error"].notna()]
    assert len(errors) == 1
    assert "loader broke" in errors["scan_error"].iloc[0]


def test_item_with_no_input_ids_records_nothing(tmp_path: Path) -> None:
    @loader(messages=["user"])
    def empty_middle_item() -> Loader[list[ChatMessageUser]]:
        async def load(
            transcript: Transcript,
        ) -> AsyncIterator[list[ChatMessageUser]]:
            for i, message in enumerate(transcript.messages[:3]):
                assert isinstance(message, ChatMessageUser)
                yield [] if i == 1 else [message]

        return load

    @scanner(loader=empty_middle_item())
    def first_message() -> Scanner[list[ChatMessageUser]]:
        async def scan_messages(messages: list[ChatMessageUser]) -> Result:
            return Result(value=messages[0].text)

        return scan_messages

    df = _scan_df(tmp_path, first_message(), ["t"])
    assert sorted(df["value"]) == ["t-0", "t-2"]


# Resume


@scanner(name="resume_items", messages=["user"])
def _fails_until_marker(marker: str) -> Scanner[ChatMessageUser]:
    async def scan_message(message: ChatMessageUser) -> Result:
        _, index = _parse(message)
        if index == _ITEMS - 1 and not Path(marker).exists():
            raise PrerequisiteError("interrupt the scan")
        return Result(value=index)

    return scan_message


def test_interrupted_job_runs_again_whole_on_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A job writes its rows only when it finishes, so resume has no partial rows."""
    monkeypatch.setenv("SCOUT_SCANBUFFER_DIR", str(tmp_path / "buffer"))
    marker = tmp_path / "recovered"
    db_path = tmp_path / "transcripts"
    _insert(db_path, [_transcript("t")])
    with temp_active_scans_store():
        interrupted = scan(
            scanners={"s": _fails_until_marker(str(marker))},
            transcripts=transcripts_from(str(db_path)),
            scans=str(tmp_path / "scans"),
            display="none",
        )
        assert not interrupted.complete
        assert interrupted.location is not None
        assert "s" not in scan_results_df(interrupted.location).scanners
        marker.touch()
        resumed = scan_resume(interrupted.location, display="none")
    assert resumed.complete
    assert resumed.location is not None
    df = scan_results_df(resumed.location, scanner="s").scanners["s"]
    assert sorted(df["value"].astype(int)) == list(range(_ITEMS))


# Results do not depend on item parallelism


def _model_events(events_json: str) -> list[str]:
    """The input text of each model call in a report's events."""
    return [
        e["input"][0]["content"]
        for e in json.loads(events_json)
        if e["event"] == "model"
    ]


def test_events_and_usage_per_item_when_items_finish_in_reverse(
    tmp_path: Path,
) -> None:
    tracker = _Tracker()
    df = _scan_df(
        tmp_path, _tracked_generating_scanner(tracker, _finish_in_reverse), ["t"]
    )
    assert tracker.items["t"].indices("end") == list(reversed(range(_ITEMS)))
    df = df.sort_values("explanation", key=lambda s: s.astype(int))
    assert df["explanation"].tolist() == [str(i) for i in range(_ITEMS)]
    # Each row holds its own loader call and scan call, nothing else.
    assert [_model_events(e) for e in df["scan_events"]] == [
        [f"t-{i}", f"t-{i}"] for i in range(_ITEMS)
    ]
    tokens = df["scan_total_tokens"].tolist()
    assert tokens[0] > 0
    assert tokens == [tokens[0]] * _ITEMS


_VOLATILE_KEYS = {
    "uuid",
    "id",
    "span_id",
    "parent_id",
    "timestamp",
    "working_start",
    "working_time",
    "completed",
    "time",
    # the generate config, which holds max_connections itself
    "config",
}


def _stable(value: Any) -> Any:
    """Drop ids and timings so two runs of the same scan compare equal."""
    if isinstance(value, dict):
        return {k: _stable(v) for k, v in value.items() if k not in _VOLATILE_KEYS}
    if isinstance(value, list):
        return [_stable(v) for v in value]
    return value


def test_same_rows_at_max_transcripts_1_and_n(tmp_path: Path) -> None:
    def rows(max_transcripts: int, tracker: _Tracker) -> list[dict[str, Any]]:
        # At N, hold items so all 8 overlap and finish in reverse.
        wait = _no_wait if max_transcripts == 1 else _finish_in_reverse
        df = _scan_df(
            tmp_path / str(max_transcripts),
            _tracked_generating_scanner(tracker, wait),
            ["t"],
            max_transcripts=max_transcripts,
        )
        return sorted(
            (
                {
                    "input_ids": row["input_ids"],
                    "value": row["value"],
                    "explanation": row["explanation"],
                    "model_usage": json.loads(row["scan_model_usage"]),
                    "events": _stable(json.loads(row["scan_events"])),
                }
                for _, row in df.iterrows()
            ),
            key=lambda row: int(row["explanation"]),
        )

    sequential_tracker = _Tracker()
    sequential = rows(1, sequential_tracker)
    assert len(sequential) == _ITEMS
    assert sequential_tracker.items["t"].max_in_flight == 1
    assert sequential[0]["value"].startswith("t-0: ")
    parallel_tracker = _Tracker()
    assert rows(_ITEMS, parallel_tracker) == sequential
    assert parallel_tracker.items["t"].max_in_flight == _ITEMS


# Multi-process stress


@dataclass
class _ThreadUse:
    """Peak use of AnyIO's default thread limiter, in the scanner's process."""

    peak: int = 0
    total: int = 0


@scanner(name="thread_stress", messages=["user"])
def _thread_stress_scanner(
    use: _ThreadUse, interrupt_after: int | None
) -> Scanner[ChatMessageUser]:
    """Two model calls per item. With `max_connections=1`, items wait in threads."""

    async def scan_message(message: ChatMessageUser) -> Result:
        model = get_model()
        await model.generate([message])
        limiter = anyio.to_thread.current_default_thread_limiter()
        use.peak = max(use.peak, int(limiter.borrowed_tokens))
        use.total = int(limiter.total_tokens)
        if interrupt_after is not None and use.peak >= interrupt_after:
            raise PrerequisiteError("interrupt while threads are in use")
        await model.generate([message])
        return Result(value=use.peak, metadata={"total": use.total})

    return scan_message


@pytest.mark.parametrize("interrupt", [False, True])
def test_model_call_waiters_can_fill_the_thread_limiter(
    tmp_path: Path, interrupt: bool
) -> None:
    """One child process with more waiting items than AnyIO's thread limit.

    Each wait for the cross-process model semaphore holds a thread. The scan
    must still complete, and an interrupt must still stop it.
    """
    items = 60
    db_path = tmp_path / "transcripts"
    _insert(db_path, [_transcript("big", items), _transcript("small", 1)])
    status = scan(
        scanners={"s": _thread_stress_scanner(_ThreadUse(), 40 if interrupt else None)},
        transcripts=transcripts_from(str(db_path)),
        scans=str(tmp_path / "scans"),
        model="mockllm/model",
        model_config=GenerateConfig(max_connections=1),
        max_transcripts=2 * items,
        max_processes=2,
        display="none",
    )
    assert status.location is not None
    if interrupt:
        assert not status.complete
        return
    assert status.complete
    df = scan_results_df(status.location, scanner="s").scanners["s"]
    assert len(df) == items + 1
    total = json.loads(df["metadata"].iloc[0])["total"]
    peak = int(df["value"].max())
    print(f"thread limiter peak {peak} of {total}")
    assert peak == total
