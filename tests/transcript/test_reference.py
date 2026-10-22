"""Tests for reading the transcript a reference-mode result row points at."""

import math
import shutil
import zipfile
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

import pytest
from inspect_ai._util.async_zip import AsyncZipReader
from inspect_ai.log import (
    read_eval_log_async,
    read_eval_log_sample_summaries,
    write_eval_log_async,
)
from inspect_ai.model import ChatMessageUser
from inspect_scout._transcript import reference
from inspect_scout._transcript.eval_log import EvalLogTranscriptsView
from inspect_scout._transcript.reference import (
    InputReference,
    InputReferenceUnavailable,
    read_referenced_transcript,
)
from inspect_scout._transcript.types import TranscriptContent

EVAL_LOG = (
    Path(__file__).parent.parent
    / "recorder"
    / "logs"
    / "2025-11-07T10-59-47-05-00_websearch-addition-problem_LqPDntDnkk4h2fSqQ8i6CE.eval"
)
SAMPLE = read_eval_log_sample_summaries(str(EVAL_LOG))[0]
assert SAMPLE.uuid is not None
SAMPLE_UUID = SAMPLE.uuid
SAMPLE_MEMBER = f"samples/{SAMPLE.id}_epoch_{SAMPLE.epoch}.json"


def _ref(
    content: TranscriptContent | None = None, transcript_id: str = SAMPLE_UUID
) -> InputReference:
    return InputReference(
        transcript_id=transcript_id,
        transcript_source_uri=str(EVAL_LOG),
        transcript_task_id=str(SAMPLE.id),
        transcript_task_repeat=SAMPLE.epoch,
        content=content,
    )


async def _rewrite(path: Path, edit: Any) -> None:
    log = await read_eval_log_async(str(path))
    assert log.samples
    edit(log.samples[0])
    await write_eval_log_async(log, str(path))


def _drop_member(path: Path, member: str) -> None:
    with zipfile.ZipFile(EVAL_LOG) as src, zipfile.ZipFile(path, "w") as dst:
        for item in src.infolist():
            if item.filename != member:
                dst.writestr(item, src.read(item))


@pytest.fixture
def log_copy(tmp_path: Path) -> Path:
    return Path(shutil.copy(EVAL_LOG, tmp_path / EVAL_LOG.name))


@pytest.mark.asyncio
async def test_reads_the_same_messages_and_events_as_the_index_reader() -> None:
    content = TranscriptContent(messages="all", events="all")
    async with EvalLogTranscriptsView(str(EVAL_LOG)) as view:
        info = [i async for i in view.select()][0]
        expected = await view.read(info, content)

    transcript = await read_referenced_transcript(str(EVAL_LOG), _ref(content))

    assert transcript.transcript_id == SAMPLE_UUID
    assert transcript.messages == expected.messages
    assert transcript.events == expected.events


@pytest.mark.asyncio
async def test_applies_the_recorded_content_filters() -> None:
    transcript = await read_referenced_transcript(
        str(EVAL_LOG), _ref(TranscriptContent(messages=["user"], events=None))
    )
    assert transcript.messages
    assert all(m.role == "user" for m in transcript.messages)
    assert transcript.events == []


@pytest.mark.asyncio
async def test_no_content_filters_reads_full_content() -> None:
    transcript = await read_referenced_transcript(str(EVAL_LOG), _ref())
    assert len(transcript.messages) == 2
    assert len(transcript.events) == 17


@pytest.mark.asyncio
async def test_sample_moved_within_the_log_resolves_by_uuid(log_copy: Path) -> None:
    def move(sample: Any) -> None:
        sample.id = "moved"

    await _rewrite(log_copy, move)

    transcript = await read_referenced_transcript(str(log_copy), _ref())

    assert transcript.task_id == "moved"
    assert transcript.messages


@pytest.mark.parametrize(
    ("make_location", "transcript_id"),
    [
        pytest.param(
            lambda tmp: str(tmp / "missing.eval"), SAMPLE_UUID, id="missing-file"
        ),
        pytest.param(lambda tmp: str(EVAL_LOG), "not-in-this-log", id="unknown-uuid"),
    ],
)
@pytest.mark.asyncio
async def test_not_found(
    tmp_path: Path, make_location: Callable[[Path], str], transcript_id: str
) -> None:
    location = make_location(tmp_path)
    with pytest.raises(InputReferenceUnavailable) as ex:
        await read_referenced_transcript(location, _ref(transcript_id=transcript_id))
    assert ex.value.reason == "not_found"
    assert location not in ex.value.message


@pytest.mark.asyncio
async def test_unreadable_log_is_unavailable(tmp_path: Path) -> None:
    location = tmp_path / "corrupt.eval"
    location.write_bytes(b"not a zip file")
    with pytest.raises(InputReferenceUnavailable) as ex:
        await read_referenced_transcript(str(location), _ref())
    assert ex.value.reason == "unavailable"
    assert str(location) not in ex.value.message


@pytest.mark.asyncio
async def test_over_cap_is_too_large_without_reading_the_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse_samples(method: str) -> None:
        real = getattr(AsyncZipReader, method)

        async def guarded(self: AsyncZipReader, member: Any) -> Any:
            name = member if isinstance(member, str) else member.filename
            assert not name.startswith("samples/"), "the sample body was read"
            return await real(self, member)

        monkeypatch.setattr(AsyncZipReader, method, guarded)

    for method in ("open_member", "open_member_raw", "read_member_fully"):
        refuse_samples(method)

    with pytest.raises(InputReferenceUnavailable) as ex:
        await read_referenced_transcript(str(EVAL_LOG), _ref(), max_bytes=100)
    assert ex.value.reason == "too_large"
    assert ex.value.message == (
        "The sample is 0.0 MiB, over this server's 0.0 MiB limit for referenced inputs."
    )


@pytest.mark.asyncio
async def test_understated_directory_size_cannot_bypass_the_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real = AsyncZipReader.get_member_entry

    async def understate(self: AsyncZipReader, name: str) -> Any:
        entry = await real(self, name)
        if name.startswith("samples/"):
            assert entry.uncompressed_size > 100
            return replace(entry, uncompressed_size=1)
        return entry

    monkeypatch.setattr(AsyncZipReader, "get_member_entry", understate)

    with pytest.raises(InputReferenceUnavailable) as ex:
        await read_referenced_transcript(str(EVAL_LOG), _ref(), max_bytes=100)
    assert ex.value.reason == "too_large"


@pytest.mark.parametrize(
    "dropped",
    [
        pytest.param(None, id="summaries-json"),
        pytest.param("summaries.json", id="journal-summaries"),
    ],
)
@pytest.mark.asyncio
async def test_oversized_sample_index_is_too_large(
    monkeypatch: pytest.MonkeyPatch, log_copy: Path, dropped: str | None
) -> None:
    if dropped:
        _drop_member(log_copy, dropped)
    monkeypatch.setattr(reference, "SUMMARIES_MAX_BYTES", 100)

    async def refuse(location: str) -> Any:
        raise AssertionError("the summaries were read")

    monkeypatch.setattr(reference, "read_eval_log_sample_summaries_async", refuse)

    with pytest.raises(InputReferenceUnavailable) as ex:
        await read_referenced_transcript(str(log_copy), _ref())
    assert ex.value.reason == "too_large"
    assert ex.value.message == (
        "This log's sample index is too large to look up referenced inputs."
    )


@pytest.mark.asyncio
async def test_summary_without_its_sample_member_is_not_found(
    log_copy: Path, caplog: pytest.LogCaptureFixture
) -> None:
    # A log still being written can list a sample before its member exists.
    _drop_member(log_copy, SAMPLE_MEMBER)

    with pytest.raises(InputReferenceUnavailable) as ex:
        await read_referenced_transcript(str(log_copy), _ref())

    assert ex.value.reason == "not_found"
    assert "Unable to read referenced transcript" not in caplog.text


@pytest.mark.asyncio
async def test_sample_with_nan_resolves_under_the_cap(log_copy: Path) -> None:
    def add_nan(sample: Any) -> None:
        sample.metadata["ratio"] = float("nan")

    await _rewrite(log_copy, add_nan)
    with zipfile.ZipFile(log_copy) as zf:
        # NaN is not JSON, so the streaming parse fails and the reader falls
        # back to a full parse.
        assert b"NaN" in zf.read(SAMPLE_MEMBER)
        size = zf.getinfo(SAMPLE_MEMBER).file_size

    transcript = await read_referenced_transcript(str(log_copy), _ref(), max_bytes=size)

    assert math.isnan(transcript.metadata["sample_metadata"]["ratio"])
    assert len(transcript.messages) == 2


@pytest.mark.asyncio
async def test_log_rewritten_in_place_is_read_fresh(log_copy: Path) -> None:
    content = TranscriptContent(messages="all", events=None)
    before = await read_referenced_transcript(str(log_copy), _ref(content))

    def prepend_message(sample: Any) -> None:
        sample.messages.insert(0, ChatMessageUser(content="edited " * 500))

    await _rewrite(log_copy, prepend_message)
    after = await read_referenced_transcript(str(log_copy), _ref(content))

    assert len(after.messages) == len(before.messages) + 1
    assert after.messages[0].text.startswith("edited")


@pytest.mark.asyncio
async def test_non_eval_location_reads_through_the_index() -> None:
    transcript = await read_referenced_transcript(
        str(EVAL_LOG.parent), _ref(TranscriptContent(messages="all"))
    )
    assert transcript.transcript_id == SAMPLE_UUID
    assert len(transcript.messages) == 2


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        pytest.param(
            {
                "transcript_id": "t1",
                "transcript_source_uri": "s3://b/l.eval",
                "transcript_task_id": "3",
                "transcript_task_repeat": 2,
                "input_content": '{"messages": "all", "events": null}',
            },
            InputReference(
                transcript_id="t1",
                transcript_source_uri="s3://b/l.eval",
                transcript_task_id="3",
                transcript_task_repeat=2,
                content=TranscriptContent(messages="all"),
            ),
            id="full",
        ),
        pytest.param(
            {"transcript_id": "t1", "input_content": float("nan")},
            InputReference(
                transcript_id="t1",
                transcript_source_uri=None,
                transcript_task_id=None,
                transcript_task_repeat=None,
                content=None,
            ),
            id="pandas-null-content",
        ),
    ],
)
def test_from_row(row: dict[str, Any], expected: InputReference) -> None:
    assert InputReference.from_row(row) == expected


@pytest.mark.parametrize(
    ("row", "reason"),
    [
        pytest.param({"input_content": None}, "not_found", id="no-transcript-id"),
        pytest.param(
            {"transcript_id": "t1", "input_content": "{not json"},
            "unavailable",
            id="bad-content",
        ),
    ],
)
def test_from_row_rejects(row: dict[str, Any], reason: str) -> None:
    with pytest.raises(InputReferenceUnavailable) as ex:
        InputReference.from_row(row)
    assert ex.value.reason == reason
