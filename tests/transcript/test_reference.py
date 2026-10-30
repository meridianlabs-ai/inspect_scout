"""Tests for reading the transcript a reference-mode result row points at."""

import json
import math
import shutil
import zipfile
import zlib
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

import pytest
import zstandard
from inspect_ai._util.async_zip import AsyncZipReader, CentralDirectory
from inspect_ai._util.asyncfiles import ObjectChangedError
from inspect_ai._util.zip_common import ZipCompressionMethod
from inspect_ai.analysis._dataframe.extract import auto_id
from inspect_ai.event import timeline_build
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
from inspect_scout._transcript.util import filter_transcript

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
    content: TranscriptContent | None = None,
    transcript_id: str = SAMPLE_UUID,
    *,
    direct: bool = True,
) -> InputReference:
    """A reference to the fixture's sample; `direct=False` names no member."""
    return InputReference(
        transcript_id=transcript_id,
        transcript_source_uri=str(EVAL_LOG),
        transcript_task_id=str(SAMPLE.id) if direct else None,
        transcript_task_repeat=SAMPLE.epoch if direct else None,
        content=content,
    )


async def _rewrite(path: Path, edit: Any) -> None:
    log = await read_eval_log_async(str(path))
    assert log.samples
    edit(log.samples[0])
    await write_eval_log_async(log, str(path))


def _drop_member(path: Path, member: str, rename: dict[str, str] | None = None) -> None:
    with zipfile.ZipFile(EVAL_LOG) as src, zipfile.ZipFile(path, "w") as dst:
        for item in src.infolist():
            if item.filename != member:
                data = src.read(item)
                item.filename = (rename or {}).get(item.filename, item.filename)
                dst.writestr(item, data)


def _understate(monkeypatch: pytest.MonkeyPatch, prefixes: tuple[str, ...]) -> None:
    """Make the central directory claim 1 byte for members under `prefixes`."""
    real = reference._central_directory

    async def understated(fs: Any, location: str) -> CentralDirectory:
        cd = await real(fs, location)
        entries = [
            replace(e, uncompressed_size=1) if e.filename.startswith(prefixes) else e
            for e in cd.entries
        ]
        return CentralDirectory(entries, cd.etag)

    monkeypatch.setattr(reference, "_central_directory", understated)


def _build_log(
    path: Path, edit: Callable[[dict[str, bytes]], None], source: Path = EVAL_LOG
) -> None:
    """Write `source`'s members, as changed by `edit`, to `path`."""
    with zipfile.ZipFile(source) as src:
        members = {item.filename: src.read(item) for item in src.infolist()}
    edit(members)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as dst:
        for name, data in members.items():
            dst.writestr(name, data)


def _edit_json(
    members: dict[str, bytes], name: str, edit: Callable[[Any], None]
) -> None:
    value = json.loads(members[name])
    edit(value)
    members[name] = json.dumps(value).encode()


def _for_summaries(members: dict[str, bytes], edit: Callable[[Any], None]) -> None:
    _edit_json(members, "summaries.json", lambda summaries: edit(summaries[0]))


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
        "The input is larger than this server's 100 bytes limit for referenced inputs."
    )


@pytest.mark.asyncio
async def test_understated_directory_size_cannot_bypass_the_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _understate(monkeypatch, ("samples/",))

    # Past the compressed-size check, so the decompressed stream is what fails.
    with pytest.raises(InputReferenceUnavailable) as ex:
        await read_referenced_transcript(str(EVAL_LOG), _ref(), max_bytes=2000)
    assert ex.value.reason == "too_large"


@pytest.mark.parametrize(
    "method",
    [
        ZipCompressionMethod.STORED,
        ZipCompressionMethod.DEFLATE,
        ZipCompressionMethod.ZSTD,
    ],
)
def test_decompression_output_is_bounded_per_chunk(
    method: ZipCompressionMethod,
) -> None:
    plain = b"\0" * (20 * reference._DECOMPRESS_CHUNK)
    if method == ZipCompressionMethod.DEFLATE:
        compressor = zlib.compressobj(wbits=-15)
        data = compressor.compress(plain) + compressor.flush()
    elif method == ZipCompressionMethod.ZSTD:
        data = zstandard.ZstdCompressor().compress(plain)
    else:
        data = plain

    chunks = list(reference._decompressed(data, method))

    assert max(len(c) for c in chunks) <= reference._DECOMPRESS_CHUNK
    assert b"".join(chunks) == plain


@pytest.mark.asyncio
async def test_oversized_sample_index_is_too_large(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(reference, "SUMMARIES_MAX_BYTES", 100)
    # What is decompressed counts, not what the directory declares.
    _understate(monkeypatch, ("summaries.json",))

    with pytest.raises(InputReferenceUnavailable) as ex:
        await read_referenced_transcript(str(EVAL_LOG), _ref(direct=False))
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
async def test_member_named_by_the_row_is_read_without_the_index(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def refuse(*args: Any) -> Any:
        raise AssertionError("the sample index was read")

    monkeypatch.setattr(reference, "_find_summary", refuse)

    transcript = await read_referenced_transcript(str(EVAL_LOG), _ref())

    assert transcript.transcript_id == SAMPLE_UUID
    assert transcript.messages


@pytest.mark.parametrize("direct", [True, False], ids=["direct", "index"])
@pytest.mark.asyncio
async def test_member_disagreeing_with_its_summary_is_not_returned(
    log_copy: Path, direct: bool
) -> None:
    # The summary claims a uuid that the member's own body doesn't carry.
    _build_log(log_copy, lambda m: _for_summaries(m, lambda s: s.update(uuid="wanted")))

    with pytest.raises(InputReferenceUnavailable) as ex:
        await read_referenced_transcript(
            str(log_copy), _ref(transcript_id="wanted", direct=direct)
        )
    assert ex.value.reason == "not_found"


@pytest.mark.asyncio
async def test_body_of_another_sample_without_uuid_is_not_returned(
    log_copy: Path,
) -> None:
    def edit(members: dict[str, bytes]) -> None:
        def other_sample(sample: Any) -> None:
            sample["id"] = 2
            sample.pop("uuid", None)

        _edit_json(members, SAMPLE_MEMBER, other_sample)
        _for_summaries(members, lambda s: s.pop("uuid", None))

    _build_log(log_copy, edit)
    log = await read_eval_log_async(str(log_copy), header_only=True)
    transcript_id = auto_id(log.eval.eval_id, f"{SAMPLE.id}_{SAMPLE.epoch}")

    with pytest.raises(InputReferenceUnavailable) as ex:
        await read_referenced_transcript(
            str(log_copy), _ref(transcript_id=transcript_id)
        )
    assert ex.value.reason == "not_found"


@pytest.mark.asyncio
async def test_direct_member_over_the_cap_falls_back_to_the_index(
    monkeypatch: pytest.MonkeyPatch, log_copy: Path
) -> None:
    # The row's coordinates name a larger, different sample whose directory
    # entry understates its size; the index finds the referenced one.
    def edit(members: dict[str, bytes]) -> None:
        other = json.loads(members[SAMPLE_MEMBER])
        other.update(id=2, uuid="other", metadata={"pad": "x" * 20_000})
        members["samples/2_epoch_1.json"] = json.dumps(other).encode()

    _build_log(log_copy, edit)
    _understate(monkeypatch, ("samples/2_",))

    transcript = await read_referenced_transcript(
        str(log_copy), replace(_ref(), transcript_task_id="2"), max_bytes=20_000
    )

    assert transcript.task_id == str(SAMPLE.id)


@pytest.mark.parametrize("start_eval_id", ["", "stale"], ids=["missing", "stale-start"])
@pytest.mark.asyncio
async def test_eval_id_is_read_as_inspect_reads_it(
    log_copy: Path, start_eval_id: str
) -> None:
    def edit(members: dict[str, bytes]) -> None:
        _edit_json(members, SAMPLE_MEMBER, lambda s: s.pop("uuid", None))
        _for_summaries(members, lambda s: s.pop("uuid", None))
        _edit_json(
            members,
            "_journal/start.json",
            lambda h: h["eval"].update(eval_id=start_eval_id),
        )
        if not start_eval_id:
            _edit_json(members, "header.json", lambda h: h["eval"].update(eval_id=""))

    _build_log(log_copy, edit)
    async with EvalLogTranscriptsView(str(log_copy)) as view:
        info = [i async for i in view.select()][0]

    transcript = await read_referenced_transcript(
        str(log_copy), _ref(transcript_id=info.transcript_id)
    )

    assert transcript.messages


@pytest.mark.asyncio
async def test_log_replaced_mid_read_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def changed(fs: Any, location: str) -> Any:
        raise ObjectChangedError(location, "etag")

    monkeypatch.setattr(reference, "_central_directory", changed)

    with pytest.raises(InputReferenceUnavailable) as ex:
        await read_referenced_transcript(str(EVAL_LOG), _ref())
    assert ex.value.reason == "unavailable"
    assert "changed" in ex.value.message


@pytest.mark.asyncio
async def test_non_eval_location_is_unavailable() -> None:
    with pytest.raises(InputReferenceUnavailable) as ex:
        await read_referenced_transcript(str(EVAL_LOG.parent), _ref())
    assert ex.value.reason == "unavailable"


@pytest.mark.asyncio
async def test_oversized_central_directory_is_too_large(
    monkeypatch: pytest.MonkeyPatch, log_copy: Path
) -> None:
    # Enough members that the directory lies outside the end-of-file read.
    _build_log(
        log_copy, lambda m: m.update({f"pad/{i:0100}": b"" for i in range(1_000)})
    )
    assert await read_referenced_transcript(str(log_copy), _ref())
    monkeypatch.setattr(reference, "CENTRAL_DIRECTORY_MAX_BYTES", 100_000)

    with pytest.raises(InputReferenceUnavailable) as ex:
        await read_referenced_transcript(str(log_copy), _ref())
    assert ex.value.reason == "too_large"


@pytest.mark.asyncio
async def test_log_being_written_reads_the_member_the_row_names(
    log_copy: Path,
) -> None:
    # Such a log has no sample index yet.
    _drop_member(log_copy, "summaries.json")

    transcript = await read_referenced_transcript(str(log_copy), _ref())
    assert transcript.transcript_id == SAMPLE_UUID

    with pytest.raises(InputReferenceUnavailable) as ex:
        await read_referenced_transcript(str(log_copy), _ref(), max_bytes=100)
    assert ex.value.reason == "too_large"


@pytest.mark.asyncio
async def test_identity_after_the_events_is_read(log_copy: Path) -> None:
    # Everything else precedes the events, so only the identity can keep a
    # messages-only read from stopping at them.
    def reorder(members: dict[str, bytes]) -> None:
        sample = json.loads(members[SAMPLE_MEMBER])
        tail = {key: sample.pop(key) for key in ("events", "id", "epoch")}
        members[SAMPLE_MEMBER] = json.dumps({**sample, **tail}).encode()

    _build_log(log_copy, reorder)

    transcript = await read_referenced_transcript(
        str(log_copy), _ref(TranscriptContent(messages="all", events=None))
    )

    assert transcript.messages


def test_zstd_window_is_capped() -> None:
    params = zstandard.ZstdCompressionParameters.from_level(3, window_log=27)
    compressor = zstandard.ZstdCompressor(compression_params=params).compressobj()
    data = compressor.compress(b"{}") + compressor.flush()

    with pytest.raises(zstandard.ZstdError):
        list(reference._decompressed(data, ZipCompressionMethod.ZSTD))


@pytest.mark.parametrize("direct", [True, False], ids=["direct", "index"])
@pytest.mark.asyncio
async def test_sample_without_uuid_resolves_by_scouts_id(
    log_copy: Path, direct: bool
) -> None:
    def drop_uuid(sample: Any) -> None:
        sample.uuid = None

    await _rewrite(log_copy, drop_uuid)
    async with EvalLogTranscriptsView(str(log_copy)) as view:
        info = [i async for i in view.select()][0]
    log = await read_eval_log_async(str(log_copy), header_only=True)
    assert info.transcript_id == auto_id(
        log.eval.eval_id, f"{SAMPLE.id}_{SAMPLE.epoch}"
    )

    transcript = await read_referenced_transcript(
        str(log_copy), _ref(transcript_id=info.transcript_id, direct=direct)
    )

    assert transcript.messages


@pytest.mark.parametrize(
    "content",
    [
        pytest.param(TranscriptContent(messages="all", events="all"), id="no-timeline"),
        pytest.param(
            TranscriptContent(messages="all", events="all", timeline=["model"]),
            id="model-timeline",
        ),
    ],
)
@pytest.mark.asyncio
async def test_stored_timelines_are_filtered_as_in_copy_mode(
    log_copy: Path, content: TranscriptContent
) -> None:
    def store_timeline(sample: Any) -> None:
        sample.timelines = [timeline_build(sample.events)]

    await _rewrite(log_copy, store_timeline)
    async with EvalLogTranscriptsView(str(log_copy)) as view:
        info = [i async for i in view.select()][0]
        # As the scanner's identity loader filters it in copy mode.
        expected = filter_transcript(await view.read(info, content), content)

    transcript = await read_referenced_transcript(str(log_copy), _ref(content))

    assert transcript.timelines == expected.timelines
    assert transcript.events == expected.events


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
