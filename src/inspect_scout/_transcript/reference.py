"""Reading the transcript a reference-mode result row points at."""

import json
import zlib
from collections.abc import AsyncIterator, Callable, Iterator
from dataclasses import dataclass
from logging import getLogger
from typing import Any, Literal, Mapping, cast

import anyio
import zstandard
from inspect_ai._util.async_zip import (
    AsyncZipReader,
    CentralDirectory,
    _find_central_directory,
    _parse_central_directory,
)
from inspect_ai._util.asyncfiles import AsyncFilesystem
from inspect_ai._util.zip_common import ZipCompressionMethod, ZipEntry
from inspect_ai.analysis._dataframe.extract import auto_id

from .eval_log import EVAL_LOG_SOURCE_TYPE, _resolve_timelines_and_filter_events
from .json.load_filtered import load_filtered_transcript
from .types import Transcript, TranscriptContent, TranscriptInfo
from .util import filter_transcript

logger = getLogger(__name__)

SUMMARIES_MAX_BYTES = 64 * 1024 * 1024
"""Largest sample index read to find a referenced sample, counted decompressed.

The index (`summaries.json`, or the journal's summaries while a log is being
written) is parsed whole, so it is bounded whatever `max_bytes` is. The same
bound applies to the log header read for a sample without a uuid.
"""

CENTRAL_DIRECTORY_MAX_BYTES = 8 * 1024 * 1024
"""Largest zip central directory read to find a log's members."""

JOURNAL_SUMMARIES_MAX_MEMBERS = 20_000
"""Most journal summary members (one per sample) read from a log being written."""

_JOURNAL_SUMMARY_MAX_BYTES = 1024 * 1024
_JOURNAL_READ_CONCURRENCY = 25
_DECOMPRESS_CHUNK = 1024 * 1024

InputReferenceReason = Literal[
    "not_resolved", "forbidden", "not_found", "too_large", "unavailable"
]
"""Why a reference row's input could not be shown."""


class InputReferenceUnavailable(Exception):
    """A reference row's input can't be resolved.

    `message` is shown to the viewer's user, so it must not name URIs,
    buckets or keys.
    """

    def __init__(self, reason: InputReferenceReason, message: str) -> None:
        super().__init__(message)
        self.reason: InputReferenceReason = reason
        self.message = message


@dataclass(frozen=True)
class InputReference:
    """The reference columns of a result row with `input_storage == "reference"`."""

    transcript_id: str
    """Sample uuid for eval-log sources."""

    transcript_source_uri: str | None
    """Source the row names. Untrusted when the host serves other users' scans."""

    transcript_task_id: str | None
    """Eval sample id."""

    transcript_task_repeat: int | None
    """Eval sample epoch."""

    content: TranscriptContent | None
    """The scanner's content filters; `None` means full content."""

    @staticmethod
    def from_row(row: Mapping[str, Any]) -> "InputReference":
        transcript_id = row.get("transcript_id")
        if not transcript_id:
            raise InputReferenceUnavailable(
                "not_found", "The result row does not identify its transcript."
            )
        # A pandas row carries a NULL as NaN, so check for a non-empty string.
        content_json = row.get("input_content")
        try:
            content = (
                TranscriptContent.from_json(content_json)
                if isinstance(content_json, str) and content_json
                else None
            )
        except (ValueError, AttributeError) as ex:
            raise InputReferenceUnavailable(
                "unavailable", "The result row's content filters could not be read."
            ) from ex
        return InputReference(
            transcript_id=str(transcript_id),
            transcript_source_uri=row.get("transcript_source_uri"),
            transcript_task_id=row.get("transcript_task_id"),
            transcript_task_repeat=row.get("transcript_task_repeat"),
            content=content,
        )


async def read_referenced_transcript(
    location: str, ref: InputReference, *, max_bytes: int | None = None
) -> Transcript:
    """Read the transcript `ref` points at from the `.eval` log at `location`.

    The sample's own zip member is read with range reads, located by uuid
    through the log's sample summaries (so a sample that moved within the log
    still resolves). Nothing is cached across calls, so a log rewritten in
    place is read fresh. The central directory and sample index are bounded
    whatever `max_bytes` is (`CENTRAL_DIRECTORY_MAX_BYTES`,
    `SUMMARIES_MAX_BYTES`), counting what is actually decompressed.

    The returned transcript has identity fields only (`transcript_id`,
    `source_type`, `source_uri`, `task_id`, `task_repeat`) plus the sample
    body's metadata, target and scores; eval-level metadata and the
    summary/header-derived top-level fields (model, date, score, ...) are not
    populated.

    Args:
        location: An `.eval` log.
        ref: The reference to resolve.
        max_bytes: Largest uncompressed sample to read, counting what is
            actually decompressed.

    Raises:
        InputReferenceUnavailable: With reason `not_found`, `too_large` or
            `unavailable`.
    """
    if not location.endswith(".eval"):
        raise InputReferenceUnavailable(
            "unavailable", "Only inputs recorded from `.eval` logs can be shown."
        )
    content = ref.content or TranscriptContent(messages="all", events="all")
    try:
        return await _read_eval_sample(location, ref, content, max_bytes)
    except InputReferenceUnavailable:
        raise
    except FileNotFoundError as ex:
        raise _not_found() from ex
    except Exception as ex:
        logger.exception("Unable to read referenced transcript %s", ref.transcript_id)
        raise InputReferenceUnavailable(
            "unavailable", "The referenced transcript could not be read."
        ) from ex


def input_too_large(max_bytes: int) -> InputReferenceUnavailable:
    """The error for an input larger than the server's `max_bytes`."""
    size = (
        f"{max_bytes / 2**20:.3g} MiB" if max_bytes >= 2**20 else f"{max_bytes:,} bytes"
    )
    return InputReferenceUnavailable(
        "too_large",
        f"The input is larger than this server's {size} limit for referenced inputs.",
    )


async def _read_eval_sample(
    location: str,
    ref: InputReference,
    content: TranscriptContent,
    max_bytes: int | None,
) -> Transcript:
    async with AsyncFilesystem() as fs:
        # A plain AsyncZipReader: the caching subclass keeps central
        # directories process-wide by filename, which goes stale when a log
        # is rewritten in place.
        cd = await _central_directory(fs, location)
        zip_reader = AsyncZipReader(fs, location, central_directory=cd)
        summary = await _find_summary(zip_reader, cd, ref.transcript_id)
        entry = cd.entry(f"samples/{summary['id']}_epoch_{summary['epoch']}.json")
        if entry is None:
            # Summarized but not yet written, as in a log still in progress.
            raise _not_found()
        if max_bytes is not None and entry.uncompressed_size > max_bytes:
            raise input_too_large(max_bytes)
        info = TranscriptInfo(
            transcript_id=ref.transcript_id,
            source_type=EVAL_LOG_SOURCE_TYPE,
            source_uri=ref.transcript_source_uri,
            task_id=str(summary["id"]),
            task_repeat=summary["epoch"],
        )
        # Timelines resolve against all events, as in `EvalLogTranscriptsView.read`.
        events = "all" if content.timeline is not None else content.events
        metadata = content.metadata is not False
        if max_bytes is None:
            async with await zip_reader.open_member(entry) as member:
                transcript = await load_filtered_transcript(
                    member, info, content.messages, events, metadata=metadata
                )
        else:
            data = await _read_compressed(
                zip_reader, entry, max_bytes, lambda: input_too_large(max_bytes)
            )
            transcript = await load_filtered_transcript(
                _BoundedMember(data, entry.compression_method, max_bytes),
                info,
                content.messages,
                events,
                metadata=metadata,
            )
    # Copy mode passes the transcript through the scanner's loader, whose
    # `filter_transcript` also filters timelines stored in the log.
    return filter_transcript(
        _resolve_timelines_and_filter_events(transcript, content), content
    )


class _OneSuffixRead:
    """Filesystem view that answers every suffix read from the first one."""

    def __init__(self, fs: AsyncFilesystem) -> None:
        self._fs = fs
        self._suffix: Any = None

    async def read_file_suffix(self, filename: str, suffix_length: int) -> Any:
        if self._suffix is None:
            self._suffix = await self._fs.read_file_suffix(filename, suffix_length)
        return self._suffix

    def __getattr__(self, name: str) -> Any:
        return getattr(self._fs, name)


async def _central_directory(fs: AsyncFilesystem, location: str) -> CentralDirectory:
    # The parse locates the directory again from the end of the file. Serving
    # both from one suffix read, with the directory read pinned to that
    # response, means the directory parsed is the one whose size was checked.
    view = cast(AsyncFilesystem, _OneSuffixRead(fs))
    found = await _find_central_directory(view, location, pin_version=True)
    if found.size > CENTRAL_DIRECTORY_MAX_BYTES:
        raise _index_too_large()
    return await _parse_central_directory(view, location, pin_version=True)


async def _find_summary(
    zip_reader: AsyncZipReader, cd: CentralDirectory, transcript_id: str
) -> dict[str, Any]:
    # Like inspect's reader, a later summary supersedes an earlier one for the
    # same sample (a re-run of a requeued sample).
    latest: dict[tuple[Any, Any], dict[str, Any]] = {}
    for summary in await _read_summaries(zip_reader, cd):
        latest[(summary.get("id"), summary.get("epoch"))] = summary
    summaries = list(latest.values())
    match = next((s for s in summaries if s.get("uuid") == transcript_id), None)
    if match is None and any(not s.get("uuid") for s in summaries):
        # Scout identifies a sample without a uuid by an id derived from the
        # eval's id, as inspect's sample dataframes do.
        eval_id = await _eval_id(zip_reader, cd)
        match = next(
            (
                s
                for s in summaries
                if not s.get("uuid")
                and auto_id(eval_id, f"{s.get('id')}_{s.get('epoch')}") == transcript_id
            ),
            None,
        )
    if match is None:
        raise _not_found()
    return match


async def _read_summaries(
    zip_reader: AsyncZipReader, cd: CentralDirectory
) -> list[dict[str, Any]]:
    consolidated = cd.entry("summaries.json")
    if consolidated is not None:
        return _json_list(
            await _read_member(
                zip_reader, consolidated, SUMMARIES_MAX_BYTES, _index_too_large
            )
        )

    # A log being written has one journal member per sample instead. Read the
    # members the directory lists rather than a count, so a sparse file name
    # cannot make the reader expect members that don't exist.
    journal = sorted(
        (
            e
            for e in cd.entries
            if e.filename.startswith("_journal/summaries/")
            and e.filename.endswith(".json")
        ),
        key=_journal_order,
    )
    if len(journal) > JOURNAL_SUMMARIES_MAX_MEMBERS:
        raise _index_too_large()
    remaining = SUMMARIES_MAX_BYTES
    per_member: list[list[dict[str, Any]]] = [[] for _ in journal]
    limiter = anyio.Semaphore(_JOURNAL_READ_CONCURRENCY)

    async def read(index: int, entry: ZipEntry) -> None:
        nonlocal remaining
        async with limiter:
            if remaining <= 0:
                raise _index_too_large()
            limit = min(_JOURNAL_SUMMARY_MAX_BYTES, remaining)
            data = await _read_member(zip_reader, entry, limit, _index_too_large)
            remaining -= len(data)
            per_member[index] = _json_list(data)

    try:
        async with anyio.create_task_group() as tg:
            for index, entry in enumerate(journal):
                tg.start_soon(read, index, entry)
    except* InputReferenceUnavailable as group:
        raise group.exceptions[0] from None
    return [summary for summaries in per_member for summary in summaries]


def _journal_order(entry: ZipEntry) -> tuple[int, int, str]:
    stem = entry.filename.rsplit("/", 1)[-1].removesuffix(".json")
    return (0, int(stem), "") if stem.isdigit() else (1, 0, stem)


async def _eval_id(zip_reader: AsyncZipReader, cd: CentralDirectory) -> str:
    entry = cd.entry("_journal/start.json") or cd.entry("header.json")
    if entry is None:
        raise _not_found()
    header = json.loads(
        await _read_member(zip_reader, entry, SUMMARIES_MAX_BYTES, _index_too_large)
    )
    return str(header["eval"]["eval_id"])


def _json_list(data: bytes) -> list[dict[str, Any]]:
    value = json.loads(data)
    if not isinstance(value, list):
        raise ValueError("expected a JSON list of sample summaries")
    return [item for item in value if isinstance(item, dict)]


async def _read_compressed(
    zip_reader: AsyncZipReader,
    entry: ZipEntry,
    limit: int,
    too_large: Callable[[], InputReferenceUnavailable],
) -> bytes:
    # Compressed data is never more than slightly larger than what it
    # decompresses to, so a member compressed past the limit cannot fit under it.
    if entry.compressed_size > limit + limit // 64 + 1024:
        raise too_large()
    data = bytearray()
    async with await zip_reader.open_member_raw(entry) as raw:
        async for chunk in raw:
            data += chunk
    return bytes(data)


async def _read_member(
    zip_reader: AsyncZipReader,
    entry: ZipEntry,
    limit: int,
    too_large: Callable[[], InputReferenceUnavailable],
) -> bytes:
    """A whole member, failing once more than `limit` bytes are decompressed."""
    data = await _read_compressed(zip_reader, entry, limit, too_large)
    out = bytearray()
    for chunk in _decompressed(data, entry.compression_method):
        out += chunk
        if len(out) > limit:
            raise too_large()
    return bytes(out)


def _decompressed(data: bytes, method: int) -> Iterator[bytes]:
    """Decompress a zip member's data in chunks of at most `_DECOMPRESS_CHUNK` bytes.

    The directory's sizes are attacker-controlled and inspect's decompressors
    have no output limit, so a small member could otherwise expand without
    bound before any check runs.
    """
    if method == ZipCompressionMethod.STORED:
        for start in range(0, len(data), _DECOMPRESS_CHUNK):
            yield data[start : start + _DECOMPRESS_CHUNK]
    elif method == ZipCompressionMethod.DEFLATE:
        decompressor = zlib.decompressobj(-15)
        pending = data
        while not decompressor.eof:
            chunk = decompressor.decompress(pending, _DECOMPRESS_CHUNK)
            pending = decompressor.unconsumed_tail
            if chunk:
                yield chunk
            elif not pending:
                break
    elif method == ZipCompressionMethod.ZSTD:
        with zstandard.ZstdDecompressor().stream_reader(
            data, read_across_frames=True
        ) as reader:
            while chunk := reader.read(_DECOMPRESS_CHUNK):
                yield chunk
    else:
        raise NotImplementedError(f"Unsupported zip compression method: {method}")


class _BoundedMember:
    """Re-iterable decompressed view of a member that fails past `max_bytes`.

    Re-iterable because the JSON5 fallback in `load_filtered_transcript` reads
    the stream a second time.
    """

    def __init__(self, data: bytes, method: int, max_bytes: int) -> None:
        self._data = data
        self._method = method
        self._max_bytes = max_bytes

    async def __aiter__(self) -> AsyncIterator[bytes]:
        seen = 0
        for chunk in _decompressed(self._data, self._method):
            seen += len(chunk)
            if seen > self._max_bytes:
                raise input_too_large(self._max_bytes)
            yield chunk


def _index_too_large() -> InputReferenceUnavailable:
    return InputReferenceUnavailable(
        "too_large",
        "This log's sample index is too large to look up referenced inputs.",
    )


def _not_found() -> InputReferenceUnavailable:
    return InputReferenceUnavailable(
        "not_found", "The referenced transcript was not found in its source."
    )
