"""Degrade-to-reference behavior of the record path."""

from __future__ import annotations

import pytest
from inspect_scout._scan import _transcript_for_record
from inspect_scout._scanner.result import ReferenceTranscript
from inspect_scout._transcript.handle import MaterializedTranscriptHandle
from inspect_scout._transcript.types import TranscriptContent, TranscriptInfo


@pytest.mark.asyncio
async def test_record_failure_degrades_to_reference() -> None:
    content = TranscriptContent(messages="all", events=None, timeline=None)
    info = TranscriptInfo(transcript_id="t1", source_uri="file:///log.eval")

    async def failing_load():  # type: ignore[no-untyped-def]
        raise RuntimeError("boom")

    handle = MaterializedTranscriptHandle(failing_load, info, content)
    report_input = await _transcript_for_record(handle, fail_on_error=False)
    assert isinstance(report_input, ReferenceTranscript)
    assert report_input.transcript_id == "t1"
    assert report_input.source_uri == "file:///log.eval"
    assert report_input.content_json == content.to_json()


@pytest.mark.asyncio
async def test_record_failure_raises_with_fail_on_error() -> None:
    content = TranscriptContent(None, None, None)
    info = TranscriptInfo(transcript_id="t1")

    async def failing_load():  # type: ignore[no-untyped-def]
        raise RuntimeError("boom")

    handle = MaterializedTranscriptHandle(failing_load, info, content)
    with pytest.raises(RuntimeError):
        await _transcript_for_record(handle, fail_on_error=True)
