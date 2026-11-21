"""Loader items of one transcript are scanned in parallel, up to `max_connections`.

Concurrency is proven with barriers (an item waits until a given number of
items are in flight) rather than wall-clock timing. Every wait is bounded by
`_TIMEOUT`, so a barrier that can't open fails the test instead of hanging.
"""

import asyncio
import json
from collections import defaultdict
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import anyio
import pandas as pd
import pytest
from inspect_ai._util.error import PrerequisiteError
from inspect_ai.model import ChatMessageUser, GenerateConfig, get_model
from inspect_scout import Loader, Result, Scanner, loader, scan, scanner, transcripts_db
from inspect_scout._concurrency.common import ScannerJob
from inspect_scout._scan import _scan_one
from inspect_scout._scanner.result import ResultReport
from inspect_scout._scanner.scanner import mark_streaming_support
from inspect_scout._scanresults import scan_results_df
from inspect_scout._transcript.factory import transcripts_from
from inspect_scout._transcript.handle import MaterializedTranscriptHandle
from inspect_scout._transcript.types import Transcript, TranscriptInfo

_TIMEOUT = 20
_ITEMS = 8


@dataclass
class _Items:
    """What one transcript's items did, in order."""

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
    """Hold each item until `count` items are in flight, or all have started."""

    async def wait(tracker: _Tracker, key: str, index: int) -> None:
        items = tracker.items[key]
        await tracker.wait_until(
            lambda: items.in_flight >= count or len(items.indices("start")) == _ITEMS
        )

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
    """Record entry/exit and wait as told.

    The value is the max in flight seen, or with `generate`, the item's text
    and the model's reply (the same whatever ran alongside it).
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
        return Result(value=value, explanation=str(index))

    return scan_message


@scanner(name="tracked", messages=["user"])
def _tracked_scanner(
    tracker: _Tracker,
    wait: ItemWait = _no_wait,
    raise_on: dict[int, BaseException] | None = None,
) -> Scanner[ChatMessageUser]:
    return _tracked_scan(tracker, wait, raise_on, generate=False)


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


def _transcript(key: str) -> Transcript:
    return Transcript(
        transcript_id=key,
        source_type="test",
        source_id="source-0",
        source_uri=f"test://{key}",
        messages=[
            ChatMessageUser(id=f"{key}-{i}", content=f"{key}-{i}")
            for i in range(_ITEMS)
        ],
        events=[],
    )


async def _scan_items(
    scanner: Scanner[Any], max_items: int, *, fail_on_error: bool = True
) -> list[ResultReport]:
    job = ScannerJob(
        union_transcript=_transcript("t"), scanner=scanner, scanner_name="s"
    )
    with anyio.fail_after(_TIMEOUT):
        return await _scan_one(job, max_items=max_items, fail_on_error=fail_on_error)


def _indices(reports: list[ResultReport]) -> list[int | None]:
    return [int(r.result.explanation or "") if r.result else None for r in reports]


@pytest.mark.asyncio
async def test_items_run_concurrently() -> None:
    tracker = _Tracker()
    reports = await _scan_items(
        _tracked_scanner(tracker, _wait_for_in_flight(_ITEMS)), max_items=_ITEMS
    )
    assert tracker.items["t"].max_in_flight == _ITEMS
    assert _indices(reports) == list(range(_ITEMS))


@pytest.mark.asyncio
async def test_reports_in_loader_order_when_items_finish_in_reverse() -> None:
    tracker = _Tracker()
    reports = await _scan_items(
        _tracked_scanner(tracker, _finish_in_reverse), max_items=_ITEMS
    )
    assert tracker.items["t"].indices("end") == list(reversed(range(_ITEMS)))
    assert _indices(reports) == list(range(_ITEMS))


@pytest.mark.asyncio
async def test_item_error_recorded_others_continue() -> None:
    tracker = _Tracker()
    reports = await _scan_items(
        _tracked_scanner(
            tracker, _wait_for_in_flight(_ITEMS), raise_on={3: ValueError("item 3")}
        ),
        max_items=_ITEMS,
        fail_on_error=False,
    )
    assert [r.error is not None for r in reports] == [i == 3 for i in range(_ITEMS)]
    assert reports[3].error is not None
    assert "item 3" in reports[3].error.error
    assert _indices(reports) == [None if i == 3 else i for i in range(_ITEMS)]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exception,fail_on_error",
    [
        (ValueError("item 3"), True),
        (PrerequisiteError("item 3"), False),
        (asyncio.CancelledError(), False),
    ],
)
async def test_item_failure_raises_bare_exception(
    exception: BaseException, fail_on_error: bool
) -> None:
    tracker = _Tracker()
    with pytest.raises(type(exception)) as raised:
        await _scan_items(
            _tracked_scanner(
                tracker, _wait_for_in_flight(_ITEMS), raise_on={3: exception}
            ),
            max_items=_ITEMS,
            fail_on_error=fail_on_error,
        )
    assert raised.value is exception


@pytest.mark.asyncio
async def test_loader_error_keeps_items_in_flight() -> None:
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

    reports = await _scan_items(
        finishes_after_loader_error(), max_items=_ITEMS, fail_on_error=False
    )
    assert _indices(reports) == [0, 1, 2, 3, None]
    assert reports[4].error is not None
    assert "loader broke" in reports[4].error.error


@pytest.mark.asyncio
async def test_skipped_item_frees_its_slot() -> None:
    """An empty item records nothing; with one slot, a leak would hang the scan."""

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

    reports = await _scan_items(first_message(), max_items=1)
    assert [r.result.value for r in reports if r.result] == ["t-0", "t-2"]
    assert len(reports) == 2


# End-to-end through `scan()`


def _scan_df(
    tmp_path: Path,
    scanner: Scanner[Any],
    keys: list[str],
    *,
    max_connections: int | None = None,
    max_processes: int = 1,
) -> pd.DataFrame:
    db_path = tmp_path / "transcripts"
    db_path.mkdir(parents=True)

    async def insert() -> None:
        async with transcripts_db(str(db_path)) as db:
            await db.insert([_transcript(key) for key in keys])

    asyncio.run(insert())
    status = scan(
        scanners={"s": scanner},
        transcripts=transcripts_from(str(db_path)),
        scans=str(tmp_path / "scans"),
        model="mockllm/model",
        model_config=GenerateConfig(max_connections=max_connections),
        max_processes=max_processes,
        display="none",
    )
    assert status.complete
    assert status.location is not None
    df = scan_results_df(status.location, scanner="s", exclude_columns=[]).scanners["s"]
    assert df["scan_error"].isna().all()
    return df


def test_items_run_concurrently_multi_process(tmp_path: Path) -> None:
    """Each worker process fans out its transcript's items.

    Two transcripts, since a single scan always runs in one process.
    """
    df = _scan_df(
        tmp_path,
        _tracked_scanner(_Tracker(), _wait_for_in_flight(_ITEMS)),
        ["a", "b"],
        max_processes=2,
    )
    assert len(df) == 2 * _ITEMS
    assert (df["value"] == _ITEMS).all()


def test_items_in_flight_capped_at_max_connections(tmp_path: Path) -> None:
    tracker = _Tracker()
    _scan_df(
        tmp_path,
        _tracked_scanner(tracker, _wait_for_in_flight(3)),
        ["t"],
        max_connections=3,
    )
    assert tracker.items["t"].max_in_flight == 3


def test_max_connections_1_scans_items_one_at_a_time_in_loader_order(
    tmp_path: Path,
) -> None:
    tracker = _Tracker()
    df = _scan_df(tmp_path, _tracked_scanner(tracker), ["t"], max_connections=1)
    assert tracker.items["t"].log == [
        (event, i) for i in range(_ITEMS) for event in ("start", "end")
    ]
    assert df["explanation"].tolist() == [str(i) for i in range(_ITEMS)]


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
    df = _scan_df(
        tmp_path,
        _tracked_generating_scanner(_Tracker(), _finish_in_reverse),
        ["t"],
    )
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


def test_same_results_at_max_connections_1_and_n(tmp_path: Path) -> None:
    def rows(max_connections: int, tracker: _Tracker) -> list[dict[str, Any]]:
        # At N, hold items so all 8 overlap and finish in reverse.
        wait = _no_wait if max_connections == 1 else _finish_in_reverse
        df = _scan_df(
            tmp_path / str(max_connections),
            _tracked_generating_scanner(tracker, wait),
            ["t"],
            max_connections=max_connections,
        )
        return [
            {
                "input_ids": row["input_ids"],
                "value": row["value"],
                "explanation": row["explanation"],
                "model_usage": json.loads(row["scan_model_usage"]),
                "events": _stable(json.loads(row["scan_events"])),
            }
            for _, row in df.iterrows()
        ]

    sequential = rows(1, _Tracker())
    assert len(sequential) == _ITEMS
    assert sequential[0]["value"].startswith("t-0: ")
    parallel_tracker = _Tracker()
    assert rows(_ITEMS, parallel_tracker) == sequential
    assert parallel_tracker.items["t"].max_in_flight == _ITEMS


@pytest.mark.asyncio
async def test_cancellation_reading_handle_back_for_record_propagates() -> None:
    """The scan succeeds, then reading the streamed transcript back cancels."""

    async def load() -> Transcript:
        raise asyncio.CancelledError()

    @scanner(messages="all", events="all")
    def handle_scanner() -> Scanner[Transcript]:
        async def scan_transcript(transcript: Transcript) -> Result:
            return Result(value="ok")

        mark_streaming_support(scan_transcript, True)
        return scan_transcript

    job = ScannerJob(
        union_transcript=MaterializedTranscriptHandle(
            load, TranscriptInfo(transcript_id="t")
        ),
        scanner=handle_scanner(),
        scanner_name="s",
    )
    with pytest.raises(asyncio.CancelledError), anyio.fail_after(_TIMEOUT):
        await _scan_one(job, max_items=_ITEMS, fail_on_error=False)
