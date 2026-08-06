"""Tests for the streaming scanner seam: input plumbing and dispatch."""

import json
from typing import Any, cast

import pytest
from inspect_scout import scanner
from inspect_scout._concurrency.common import ScannerJob
from inspect_scout._scan import _content_for_scanner, _scan_one, _streaming_eligible
from inspect_scout._scanner.result import Result, _serialize_input
from inspect_scout._scanner.scanner import SCANNER_SUPPORTS_STREAMING_ATTR, Scanner
from inspect_scout._transcript.handle import MaterializedTranscriptHandle
from inspect_scout._transcript.types import Transcript, TranscriptInfo
from inspect_scout._transcript.util import union_transcript_contents


def test_serialize_input_info_only() -> None:
    info = TranscriptInfo(transcript_id="t1", source_id="e1")
    input_json, input_data = _serialize_input(info, "transcript_info", pool_dedup=True)
    assert input_data is None
    parsed = json.loads(input_json)
    assert parsed["transcript_id"] == "t1"
    assert parsed["source_id"] == "e1"
    # info only: no content fields serialized
    assert "messages" not in parsed
    assert "events" not in parsed


@scanner(messages="all", events="all")
def _handle_scanner() -> Scanner[Transcript]:
    async def scan(transcript: Transcript) -> Result:
        return Result(value="ok")

    setattr(scan, SCANNER_SUPPORTS_STREAMING_ATTR, True)
    return scan


@scanner(messages="all", events="all")
def _plain_scanner() -> Scanner[Transcript]:
    async def scan(transcript: Transcript) -> Result:
        return Result(value="ok")

    return scan


@scanner(messages="all")
def _raising_handle_scanner() -> Scanner[Transcript]:
    async def scan(transcript: Transcript) -> Result:
        raise RuntimeError("scanner boom")

    setattr(scan, SCANNER_SUPPORTS_STREAMING_ATTR, True)
    return scan


def _materialized_handle(transcript: Transcript) -> MaterializedTranscriptHandle:
    """Build a materialized handle over an in-memory transcript."""

    async def load_fn() -> Transcript:
        return transcript

    return MaterializedTranscriptHandle(
        load_fn, TranscriptInfo(transcript_id=transcript.transcript_id)
    )


def _empty_transcript() -> Transcript:
    return Transcript(transcript_id="t1", messages=[], events=[], metadata={})


@pytest.mark.asyncio
async def test_scan_one_with_handle_scanner() -> None:
    """A handle-accepting scanner receives the handle and results record info-only."""
    handle = _materialized_handle(_empty_transcript())

    s = _handle_scanner()
    job = ScannerJob(union_transcript=handle, scanner=s, scanner_name="hs")
    reports = await _scan_one(job, validation=None, fail_on_error=True)
    assert len(reports) == 1
    assert reports[0].input_type == "transcript_info"
    assert reports[0].input == handle.info  # info only, no content


@pytest.mark.asyncio
async def test_scan_one_stream_error_contained() -> None:
    """Errors raised during handle iteration produce an Error report, not a crash."""
    info = TranscriptInfo(transcript_id="t1")

    async def failing_load() -> Transcript:
        raise ValueError("corrupt sample JSON")

    handle = MaterializedTranscriptHandle(failing_load, info)

    s = _plain_scanner()
    job = ScannerJob(union_transcript=handle, scanner=s, scanner_name="ps")
    reports = await _scan_one(job, validation=None, fail_on_error=False)
    assert len(reports) == 1
    assert reports[0].error is not None
    assert "corrupt sample JSON" in reports[0].error.error


@pytest.mark.asyncio
async def test_scan_one_awaits_on_complete_once() -> None:
    """`_scan_one` awaits `job.on_complete` exactly once per job."""
    handle = _materialized_handle(_empty_transcript())

    complete_calls = 0

    async def on_job_complete() -> None:
        nonlocal complete_calls
        complete_calls += 1

    job = ScannerJob(
        union_transcript=handle,
        scanner=_handle_scanner(),
        scanner_name="s",
        on_complete=on_job_complete,
    )

    await _scan_one(job, validation=None, fail_on_error=True)
    assert complete_calls == 1


@pytest.mark.asyncio
async def test_scan_one_awaits_on_complete_when_scanner_raises() -> None:
    """`on_complete` still fires (finally) when the scanner raises with fail_on_error."""
    handle = _materialized_handle(_empty_transcript())

    complete_calls = 0

    async def on_job_complete() -> None:
        nonlocal complete_calls
        complete_calls += 1

    job = ScannerJob(
        union_transcript=handle,
        scanner=_raising_handle_scanner(),
        scanner_name="s",
        on_complete=on_job_complete,
    )

    with pytest.raises(RuntimeError, match="scanner boom"):
        await _scan_one(job, validation=None, fail_on_error=True)
    assert complete_calls == 1


def _scanner_with(
    messages: Any = None, events: Any = None, timeline: Any = None
) -> Scanner[Any]:
    """Build a handle-accepting scanner with the given content filters."""

    @scanner(messages=messages, events=events, timeline=timeline)
    def factory() -> Scanner[Transcript]:
        async def scan(transcript: Transcript) -> Result:
            return Result(value="ok")

        setattr(scan, SCANNER_SUPPORTS_STREAMING_ATTR, True)
        return scan

    return cast(Scanner[Any], factory())


@pytest.mark.parametrize(
    ("filters", "expected"),
    [
        pytest.param(
            [{"messages": "all"}, {"messages": "all"}],
            True,
            id="messages_all",
        ),
        pytest.param(
            [
                {"messages": ["user", "assistant"]},
                {"messages": ["assistant", "user"]},
            ],
            True,
            id="messages_order",
        ),
        pytest.param(
            [{"messages": ["user"]}, {"messages": ["user", "assistant"]}],
            False,
            id="messages_narrower",
        ),
        pytest.param(
            [{"messages": "all"}, {"messages": "all", "events": "all"}],
            False,
            id="events_none_vs_all",
        ),
        pytest.param(
            [
                {
                    "messages": "all",
                    "events": ["model", "compaction", "span_begin", "span_end"],
                },
                {
                    "messages": "all",
                    "events": ["span_end", "span_begin", "compaction", "model"],
                },
            ],
            True,
            id="events_order",
        ),
        pytest.param(
            [
                {"messages": "all", "events": ["model"]},
                {
                    "messages": "all",
                    "events": ["model", "compaction", "span_begin", "span_end"],
                },
            ],
            False,
            id="events_narrower",
        ),
        pytest.param(
            [
                {"messages": "all", "events": "all"},
                {"messages": "all", "events": "all"},
            ],
            True,
            id="events_all",
        ),
        pytest.param(
            [{"messages": "all"}],
            True,
            id="single_scanner",
        ),
        pytest.param(
            [
                {"messages": "all", "timeline": "all"},
                {"messages": "all", "timeline": "all"},
            ],
            False,
            id="timeline_both",
        ),
        pytest.param(
            [{"messages": "all", "timeline": "all"}, {"messages": "all"}],
            False,
            id="timeline_one",
        ),
    ],
)
def test_streaming_eligible(filters: list[dict[str, Any]], expected: bool) -> None:
    """Scanners can share a union-filtered handle only when each filter equals the union."""
    scanners = [_scanner_with(**f) for f in filters]
    union_content = union_transcript_contents(
        [_content_for_scanner(s) for s in scanners]
    )
    assert _streaming_eligible(scanners, union_content) is expected
