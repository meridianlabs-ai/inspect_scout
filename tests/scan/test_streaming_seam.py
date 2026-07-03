"""Tests for the streaming scanner seam: input plumbing and dispatch."""

from pathlib import Path
from typing import Any, cast

import pytest
from inspect_scout import scanner
from inspect_scout._concurrency.common import ScannerJob
from inspect_scout._scan import _content_for_scanner, _scan_one, _streaming_eligible
from inspect_scout._scanner.result import Result, _serialize_input
from inspect_scout._scanner.scanner import SCANNER_SUPPORTS_STREAMING_ATTR, Scanner
from inspect_scout._scanner.util import get_input_type_and_ids
from inspect_scout._transcript.handle import MaterializedTranscriptHandle
from inspect_scout._transcript.types import Transcript, TranscriptInfo
from inspect_scout._transcript.util import union_transcript_contents


def test_input_type_for_transcript_info() -> None:
    info = TranscriptInfo(transcript_id="t1")
    assert get_input_type_and_ids(info) == ("transcript_info", ["t1"])


def test_serialize_input_info_only() -> None:
    info = TranscriptInfo(transcript_id="t1", source_id="e1")
    input_json, input_data = _serialize_input(info, "transcript_info", pool_dedup=True)
    assert input_data is None
    assert '"transcript_id":"t1"' in input_json.replace(" ", "")
    assert "messages" not in input_json  # no content fields serialized


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


@pytest.mark.asyncio
async def test_scan_one_with_handle_scanner(tmp_path: Path) -> None:
    """A handle-accepting scanner receives the handle and results record info-only."""
    info = TranscriptInfo(transcript_id="t1")
    transcript = Transcript(transcript_id="t1", messages=[], events=[], metadata={})

    async def load_fn() -> Transcript:
        return transcript

    handle = MaterializedTranscriptHandle(load_fn, info)

    s = _handle_scanner()
    job = ScannerJob(union_transcript=handle, scanner=s, scanner_name="hs")
    reports = await _scan_one(job, validation=None, fail_on_error=True)
    assert len(reports) == 1
    assert reports[0].input_type == "transcript_info"
    assert reports[0].input == info  # info only, no content


@pytest.mark.asyncio
async def test_scan_one_stream_error_contained(tmp_path: Path) -> None:
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
async def test_scan_one_on_complete_awaited_once_per_job(tmp_path: Path) -> None:
    """The shared handle is closed exactly once, after the last (lead + follower) job.

    Simulates the completion counter created by `_parse_function`: a lead with
    one follower, each `ScannerJob` carrying the same `on_complete` closure.
    Running `_scan_one` on the lead then the follower must decrement to zero
    and close the handle exactly once.
    """
    info = TranscriptInfo(transcript_id="t1")
    transcript = Transcript(transcript_id="t1", messages=[], events=[], metadata={})

    close_count = 0

    class SpyHandle(MaterializedTranscriptHandle):
        async def aclose(self) -> None:
            nonlocal close_count
            close_count += 1
            await super().aclose()

    async def load_fn() -> Transcript:
        return transcript

    handle = SpyHandle(load_fn, info)

    # Mirror _parse_function's completion counter: 1 lead + 1 follower.
    remaining = 2

    async def on_job_complete() -> None:
        nonlocal remaining
        remaining -= 1
        if remaining == 0:
            await handle.aclose()

    lead = ScannerJob(
        union_transcript=handle,
        scanner=_handle_scanner(),
        scanner_name="lead",
        on_complete=on_job_complete,
    )
    follower = ScannerJob(
        union_transcript=handle,
        scanner=_handle_scanner(),
        scanner_name="follower",
        on_complete=on_job_complete,
    )

    await _scan_one(lead, validation=None, fail_on_error=True)
    assert close_count == 0  # lead done, follower still pending

    await _scan_one(follower, validation=None, fail_on_error=True)
    assert remaining == 0
    assert close_count == 1  # closed exactly once after the last job


def _make_handle_scanner(messages: Any) -> Scanner[Any]:
    """Build a handle-accepting scanner with the given `messages` content filter."""

    @scanner(messages=messages)
    def factory() -> Scanner[Transcript]:
        async def scan(transcript: Transcript) -> Result:
            return Result(value="ok")

        setattr(scan, SCANNER_SUPPORTS_STREAMING_ATTR, True)
        return scan

    return cast(Scanner[Any], factory())


def test_streaming_eligible_true_when_both_scanners_want_all() -> None:
    s1 = _make_handle_scanner("all")
    s2 = _make_handle_scanner("all")
    union_content = union_transcript_contents(
        [_content_for_scanner(s1), _content_for_scanner(s2)]
    )
    assert _streaming_eligible([s1, s2], union_content) is True


def test_streaming_eligible_true_when_message_filters_match_ignoring_order() -> None:
    s1 = _make_handle_scanner(["user", "assistant"])
    s2 = _make_handle_scanner(["assistant", "user"])
    union_content = union_transcript_contents(
        [_content_for_scanner(s1), _content_for_scanner(s2)]
    )
    assert union_content.messages is not None
    assert set(union_content.messages) == {"user", "assistant"}
    assert _streaming_eligible([s1, s2], union_content) is True


def test_streaming_eligible_false_when_scanner_narrower_than_union() -> None:
    narrow = _make_handle_scanner(["user"])
    wide = _make_handle_scanner(["user", "assistant"])
    union_content = union_transcript_contents(
        [_content_for_scanner(narrow), _content_for_scanner(wide)]
    )
    assert _streaming_eligible([narrow, wide], union_content) is False


def test_streaming_eligible_false_when_any_scanner_wants_events_or_timeline() -> None:
    s1 = _make_handle_scanner("all")

    @scanner(messages="all", events="all")
    def events_factory() -> Scanner[Transcript]:
        async def scan(transcript: Transcript) -> Result:
            return Result(value="ok")

        setattr(scan, SCANNER_SUPPORTS_STREAMING_ATTR, True)
        return scan

    s2 = cast(Scanner[Any], events_factory())
    union_content = union_transcript_contents(
        [_content_for_scanner(s1), _content_for_scanner(s2)]
    )
    assert union_content.events is not None
    assert _streaming_eligible([s1, s2], union_content) is False
