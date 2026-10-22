"""Reading the transcript a reference-mode result row points at."""

from collections.abc import AsyncIterable, AsyncIterator
from dataclasses import dataclass
from logging import getLogger
from typing import Any, Literal, Mapping

from inspect_ai._util.async_zip import AsyncZipReader
from inspect_ai._util.asyncfiles import AsyncFilesystem
from inspect_ai.log import read_eval_log_sample_summaries_async

from .eval_log import EVAL_LOG_SOURCE_TYPE, _resolve_timelines_and_filter_events
from .factory import transcripts_from
from .json.load_filtered import load_filtered_transcript
from .types import Transcript, TranscriptContent, TranscriptInfo

logger = getLogger(__name__)

SUMMARIES_MAX_BYTES = 64 * 1024 * 1024
"""Largest uncompressed sample index read to find a referenced sample.

The index (`summaries.json`, or the journal's summaries while a log is being
written) is parsed whole, so it is bounded whatever `max_bytes` is.
"""

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
    """Read the transcript `ref` points at from `location`.

    An `.eval` location is read with range reads of the sample's own zip
    member, located by uuid through the log's sample summaries (so a sample
    that moved within the log still resolves). Nothing is cached across
    calls, so a log rewritten in place is read fresh. Other locations go
    through the transcripts index, and `max_bytes` does not apply to them.

    The returned transcript has identity fields only (`transcript_id`,
    `source_type`, `source_uri`, `task_id`, `task_repeat`) plus the sample
    body's metadata, target and scores; eval-level metadata and the
    summary/header-derived top-level fields (model, date, score, ...) are not
    populated.

    Args:
        location: Transcripts location to read from (e.g. an `.eval` log).
        ref: The reference to resolve.
        max_bytes: Largest uncompressed sample to read.

    Raises:
        InputReferenceUnavailable: With reason `not_found`, `too_large` or
            `unavailable`.
    """
    content = ref.content or TranscriptContent(messages="all", events="all")
    try:
        if location.endswith(".eval"):
            return await _read_eval_sample(location, ref, content, max_bytes)
        async with transcripts_from(location).reader() as reader:
            async for info in reader.index():
                if info.transcript_id == ref.transcript_id:
                    return await reader.read(info, content)
        raise _not_found()
    except InputReferenceUnavailable:
        raise
    except FileNotFoundError as ex:
        raise _not_found() from ex
    except Exception as ex:
        logger.warning(
            "Unable to read referenced transcript %s", ref.transcript_id, exc_info=True
        )
        raise InputReferenceUnavailable(
            "unavailable", "The referenced transcript could not be read."
        ) from ex


async def _read_eval_sample(
    location: str,
    ref: InputReference,
    content: TranscriptContent,
    max_bytes: int | None,
) -> Transcript:
    # The summaries read shares this filesystem (and its S3 client).
    async with AsyncFilesystem() as fs:
        # A plain AsyncZipReader: the caching subclass keeps central
        # directories process-wide by filename, which goes stale when a log
        # is rewritten in place.
        zip_reader = AsyncZipReader(fs, location)
        cd = await zip_reader.entries()
        consolidated = cd.entry("summaries.json")
        summaries_size = (
            consolidated.uncompressed_size
            if consolidated is not None
            else sum(
                e.uncompressed_size
                for e in cd.entries
                if e.filename.startswith("_journal/summaries/")
            )
        )
        if summaries_size > SUMMARIES_MAX_BYTES:
            raise InputReferenceUnavailable(
                "too_large",
                "This log's sample index is too large to look up referenced inputs.",
            )

        summaries = await read_eval_log_sample_summaries_async(location)
        summary = next((s for s in summaries if s.uuid == ref.transcript_id), None)
        if summary is None:
            raise _not_found()

        try:
            entry = await zip_reader.get_member_entry(
                f"samples/{summary.id}_epoch_{summary.epoch}.json"
            )
        except KeyError as ex:
            # Summarized but not yet written, as in a log still in progress.
            raise _not_found() from ex
        if max_bytes is not None and entry.uncompressed_size > max_bytes:
            raise _too_large(entry.uncompressed_size, max_bytes)
        info = TranscriptInfo(
            transcript_id=ref.transcript_id,
            source_type=EVAL_LOG_SOURCE_TYPE,
            source_uri=ref.transcript_source_uri,
            task_id=str(summary.id),
            task_repeat=summary.epoch,
        )
        # Timelines resolve against all events, as in `EvalLogTranscriptsView.read`.
        events = "all" if content.timeline is not None else content.events
        async with await zip_reader.open_member(entry) as member:
            transcript = await load_filtered_transcript(
                _bounded(member, max_bytes),
                info,
                content.messages,
                events,
                metadata=content.metadata is not False,
            )
    return _resolve_timelines_and_filter_events(transcript, content)


def _too_large(size: int, max_bytes: int) -> InputReferenceUnavailable:
    return InputReferenceUnavailable(
        "too_large",
        f"The sample is {size / 2**20:.1f} MiB, over "
        f"this server's {max_bytes / 2**20:.1f} MiB limit for referenced "
        "inputs.",
    )


class _bounded:
    """Re-iterable view of `chunks` that fails once more than `max_bytes` are produced.

    The central directory's declared size is attacker-controlled, so the
    decompressed stream is bounded as well. Re-iterable because the JSON5
    fallback in `load_filtered_transcript` reads the stream a second time.
    """

    def __init__(self, chunks: AsyncIterable[bytes], max_bytes: int | None) -> None:
        self._chunks = chunks
        self._max_bytes = max_bytes

    async def __aiter__(self) -> AsyncIterator[bytes]:
        seen = 0
        async for chunk in self._chunks:
            seen += len(chunk)
            if self._max_bytes is not None and seen > self._max_bytes:
                raise _too_large(seen, self._max_bytes)
            yield chunk


def _not_found() -> InputReferenceUnavailable:
    return InputReferenceUnavailable(
        "not_found", "The referenced transcript was not found in its source."
    )
