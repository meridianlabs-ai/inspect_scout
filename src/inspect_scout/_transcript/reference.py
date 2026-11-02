"""Reading the transcript a reference-mode result row points at."""

import functools
import io
import json
import zlib
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from logging import getLogger
from typing import Any, Literal, Mapping, cast

import zstandard
from inspect_ai._util.async_zip import (
    AsyncZipReader,
    CentralDirectory,
    _parse_central_directory,
)
from inspect_ai._util.asyncfiles import AsyncFilesystem, ObjectChangedError
from inspect_ai._util.constants import DESERIALIZING
from inspect_ai._util.zip_common import ZipCompressionMethod, ZipEntry
from inspect_ai.analysis._dataframe.extract import auto_id
from inspect_ai.log import EvalSpec

from .eval_log import EVAL_LOG_SOURCE_TYPE, _resolve_timelines_and_filter_events
from .json.load_filtered import SampleIdentity, load_filtered_transcript
from .types import Transcript, TranscriptContent, TranscriptInfo
from .util import filter_transcript

logger = getLogger(__name__)

SUMMARIES_MAX_BYTES = 64 * 1024 * 1024
"""Largest sample index read to find a referenced sample, counted decompressed.

The index (`summaries.json`) is parsed whole, so it is bounded whatever
`max_bytes` is. The same bound applies to the log header read for a sample
without a uuid.
"""

CENTRAL_DIRECTORY_MAX_BYTES = 8 * 1024 * 1024
"""Largest zip central directory read to find a log's members."""

_DECOMPRESS_CHUNK = 1024 * 1024
# inspect writes zstd at level 3, which uses a 2 MiB window.
_ZSTD_MAX_WINDOW = 8 * 1024 * 1024

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
    location: str,
    ref: InputReference,
    *,
    max_bytes: int | None = None,
    attachments: dict[str, str] | None = None,
) -> Transcript:
    """Read the transcript `ref` points at from the `.eval` log at `location`.

    The sample is read from the member the row names, or found by uuid in the
    log's sample index when that member is missing, over `max_bytes` or holds
    another sample. Nothing is cached across calls, so a log rewritten in
    place is read fresh.

    Args:
        location: An `.eval` log.
        ref: The reference to resolve.
        max_bytes: Largest sample to read, counted decompressed. The central
            directory and sample index are bounded regardless.
        attachments: When given, attachment references are left in place
            and the attachments they name are added to it.

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
        return await _read_eval_sample(location, ref, content, max_bytes, attachments)
    except InputReferenceUnavailable:
        raise
    except FileNotFoundError as ex:
        raise _not_found() from ex
    except ObjectChangedError as ex:
        logger.warning("Log %s changed while it was being read", location)
        raise InputReferenceUnavailable(
            "unavailable", "The log changed while it was being read; try again."
        ) from ex
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
    attachments: dict[str, str] | None,
) -> Transcript:
    async with AsyncFilesystem() as fs:
        # A plain AsyncZipReader: the caching subclass keeps central
        # directories process-wide by filename, which goes stale when a log
        # is rewritten in place.
        cd = await _central_directory(fs, location)
        zip_reader = AsyncZipReader(fs, location, central_directory=cd)
        # The row names the sample's member, so read it directly. Only a
        # member that is missing, holds another sample (one moved, or re-run),
        # or is over the cap needs the sample index, which is read whole.
        transcript = None
        missed = _not_found()
        if (
            ref.transcript_task_id is not None
            and ref.transcript_task_repeat is not None
        ):
            try:
                transcript = await _read_sample(
                    zip_reader,
                    cd,
                    ref,
                    content,
                    max_bytes,
                    attachments,
                    ref.transcript_task_id,
                    ref.transcript_task_repeat,
                )
            except InputReferenceUnavailable as ex:
                missed = ex
        if transcript is None:
            # A log still being written has no index yet, but only appends,
            # so its sample can only be in the member the row names.
            index = cd.entry("summaries.json")
            if index is None:
                raise missed
            summary = await _find_summary(zip_reader, cd, index, ref.transcript_id)
            transcript = await _read_sample(
                zip_reader,
                cd,
                ref,
                content,
                max_bytes,
                attachments,
                summary.get("id"),
                summary.get("epoch"),
            )
    # Copy mode passes the transcript through the scanner's loader, whose
    # `filter_transcript` also filters timelines stored in the log.
    return filter_transcript(
        _resolve_timelines_and_filter_events(transcript, content), content
    )


async def _read_sample(
    zip_reader: AsyncZipReader,
    cd: CentralDirectory,
    ref: InputReference,
    content: TranscriptContent,
    max_bytes: int | None,
    attachments: dict[str, str] | None,
    sample_id: Any,
    epoch: Any,
) -> Transcript:
    """The transcript of the sample `ref` names, read from its member.

    Its body must be that sample, whichever way the member was found: a
    summary can be stale or disagree with its member.
    """
    entry = cd.entry(f"samples/{sample_id}_epoch_{epoch}.json")
    if entry is None:
        raise _not_found()
    if max_bytes is not None and entry.uncompressed_size > max_bytes:
        raise input_too_large(max_bytes)
    info = TranscriptInfo(
        transcript_id=ref.transcript_id,
        source_type=EVAL_LOG_SOURCE_TYPE,
        source_uri=ref.transcript_source_uri,
        task_id=str(sample_id),
        task_repeat=epoch,
    )
    identity: list[SampleIdentity] = []
    found: dict[str, str] = {}
    load = functools.partial(
        load_filtered_transcript,
        t=info,
        messages=content.messages,
        # Timelines resolve against all events, as in `EvalLogTranscriptsView.read`.
        events="all" if content.timeline is not None else content.events,
        metadata=content.metadata is not False,
        on_identity=identity.append,
        on_attachments=found.update if attachments is not None else None,
    )
    if max_bytes is None:
        async with await zip_reader.open_member(entry) as member:
            transcript = await load(member)
    else:
        data = await _read_member(
            zip_reader, entry, max_bytes, lambda: input_too_large(max_bytes)
        )
        transcript = await load(io.BytesIO(data))
    if not identity or not await _is_referenced_sample(
        zip_reader, cd, ref.transcript_id, identity[0], sample_id, epoch
    ):
        raise _not_found()
    if attachments is not None:
        attachments.update(found)
    return transcript


async def _is_referenced_sample(
    zip_reader: AsyncZipReader,
    cd: CentralDirectory,
    transcript_id: str,
    body: SampleIdentity,
    sample_id: Any,
    epoch: Any,
) -> bool:
    # The body must be the member's own sample, and that sample the row's.
    if str(body.id) != str(sample_id) or body.epoch != epoch:
        return False
    if body.uuid:
        return bool(body.uuid == transcript_id)
    # Scout identifies a sample without a uuid by an id derived from the
    # eval's id, as inspect's sample dataframes do.
    eval_id = await _eval_id(zip_reader, cd)
    return auto_id(eval_id, f"{body.id}_{body.epoch}") == transcript_id


class _CappedReads:
    """Filesystem view that refuses a range read past `CENTRAL_DIRECTORY_MAX_BYTES`."""

    def __init__(self, fs: AsyncFilesystem) -> None:
        self._fs = fs

    async def read_file_bytes_fully(
        self, filename: str, start: int, end: int, **kwargs: Any
    ) -> bytes:
        if end - start > CENTRAL_DIRECTORY_MAX_BYTES:
            raise _index_too_large()
        return await self._fs.read_file_bytes_fully(filename, start, end, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._fs, name)


async def _central_directory(fs: AsyncFilesystem, location: str) -> CentralDirectory:
    # The end records come from a fixed-size suffix read, so the directory is
    # the parse's only large range read.
    view = cast(AsyncFilesystem, _CappedReads(fs))
    return await _parse_central_directory(view, location, pin_version=True)


async def _find_summary(
    zip_reader: AsyncZipReader,
    cd: CentralDirectory,
    index: ZipEntry,
    transcript_id: str,
) -> dict[str, Any]:
    # Like inspect's reader, a later summary supersedes an earlier one for the
    # same sample (a re-run of a requeued sample).
    # Keyed as the member name is, so ids 1 and "1" are one sample.
    latest: dict[tuple[str, Any], dict[str, Any]] = {}
    data = await _read_member(zip_reader, index, SUMMARIES_MAX_BYTES, _index_too_large)
    for summary in _json_list(data):
        latest[(str(summary.get("id")), summary.get("epoch"))] = summary
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


async def _eval_id(zip_reader: AsyncZipReader, cd: CentralDirectory) -> str:
    # As inspect reads a log: the finished header, else the journal's start.
    entry = cd.entry("header.json") or cd.entry("_journal/start.json")
    if entry is None:
        raise _not_found()
    header = json.loads(
        await _read_member(zip_reader, entry, SUMMARIES_MAX_BYTES, _index_too_large)
    )
    # Validated as inspect reads a log, which derives a stable eval_id when
    # it is missing or empty.
    return EvalSpec.model_validate(
        header["eval"], context={DESERIALIZING: True}
    ).eval_id


def _json_list(data: bytes) -> list[dict[str, Any]]:
    value = json.loads(data)
    if not isinstance(value, list):
        raise ValueError("expected a JSON list of sample summaries")
    return [item for item in value if isinstance(item, dict)]


async def _read_member(
    zip_reader: AsyncZipReader,
    entry: ZipEntry,
    limit: int,
    too_large: Callable[[], InputReferenceUnavailable],
) -> bytes:
    """A whole member, failing once more than `limit` bytes are decompressed."""
    # Compressed data is never more than slightly larger than what it
    # decompresses to, so a member compressed past the limit cannot fit under it.
    if entry.compressed_size > limit + limit // 64 + 1024:
        raise too_large()
    data = bytearray()
    async with await zip_reader.open_member_raw(entry) as raw:
        async for chunk in raw:
            data += chunk
    out = bytearray()
    for chunk in _decompressed(bytes(data), entry.compression_method):
        out += chunk
        if len(out) > limit:
            raise too_large()
    return bytes(out)


def _decompressed(data: bytes, method: int) -> Iterator[bytes]:
    """Decompress a zip member's data in chunks of at most `_DECOMPRESS_CHUNK` bytes.

    The directory's sizes are attacker-controlled and inspect's decompressors
    have no output limit, so a small member could otherwise expand without
    bound before any check runs. A zstd frame also declares the window its
    decoder allocates, so that is capped at `_ZSTD_MAX_WINDOW`.
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
        with zstandard.ZstdDecompressor(max_window_size=_ZSTD_MAX_WINDOW).stream_reader(
            data, read_across_frames=True
        ) as reader:
            while chunk := reader.read(_DECOMPRESS_CHUNK):
                yield chunk
    else:
        raise NotImplementedError(f"Unsupported zip compression method: {method}")


def _index_too_large() -> InputReferenceUnavailable:
    return InputReferenceUnavailable(
        "too_large",
        "This log's sample index is too large to look up referenced inputs.",
    )


def _not_found() -> InputReferenceUnavailable:
    return InputReferenceUnavailable(
        "not_found", "The referenced transcript was not found in its source."
    )
